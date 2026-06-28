---
type: Concept
title: Authoring executions
description: How to create and manage executions in Python — ExecutionConfiguration, the context manager, working directory layout, metadata auto-generation, and dry run mode.
---

# Authoring executions

## Creating and Managing Executions

Execution records are created and managed by the **Execution** class in the Python API, or by the MCP execution lifecycle tools. Unlike `ExecutionRecord` (read-only lookup), the `Execution` class is the active object that drives the data flow described above:

- Creates the execution record in the catalog
- Manages the local working directory
- Downloads input datasets and assets
- Stages output files for upload
- Transitions status (start, stop, fail)
- Uploads outputs to the catalog

In Python, `Execution` is used through a context manager:

```python
with ml.create_execution(config) as exe:
    # exe is an Execution object — manages the full lifecycle
    ...
```

MCP exposes read-only execution observation (`deriva_ml_get_execution`, `deriva_ml_list_executions`, `deriva_ml_find_workflow_executions`, `deriva_ml_get_lineage`, `deriva_ml_list_execution_children`, `deriva_ml_list_execution_parents`). Execution authorship — creating an execution, starting work, staging outputs, committing — lives in user-local Python via the bundled `scripts/` templates. The committed script's git URL + checksum is the workflow's reproducibility anchor.

## ExecutionConfiguration

In the Python API, `ExecutionConfiguration` specifies everything needed to create an execution:

```python
from deriva_ml import ExecutionConfiguration

config = ExecutionConfiguration(
    workflow=workflow,                   # Required: Workflow object
    datasets=["2-ABC1"],                # Optional: input dataset RIDs
    assets=["2-DEF2"],                  # Optional: input asset RIDs or AssetSpec objects
    description="Train CNN on batch 1", # Optional: execution description (supports Markdown)
)
```

- **workflow**: A `Workflow` object from `create_workflow` or `lookup_workflow_by_url`. Required.
- **datasets**: List of dataset RID strings. These become the execution's input datasets.
- **assets**: List of asset RID strings or `AssetSpec` objects. Use `AssetSpec(rid="...", cache=True)` for large assets that should be cached locally across executions.
- **description**: Human-readable description. Supports Markdown for rich formatting in the Chaise UI.
- **config_choices**: Dict of Hydra config group selections (auto-populated by `deriva-ml-run`).

The bundled execution templates handle workflow setup inline: each template calls `ml.create_workflow(name=..., workflow_type=..., description=...)` before opening the execution context, then passes the resulting Workflow object to `create_execution(config, workflow=workflow, ...)`.

## The Execution Context Manager

The canonical Python pattern uses a `with` block:

```python
with ml.create_execution(config, workflow=workflow, dry_run=False) as exe:
    # On enter: creates execution record, sets status to Running.
    # Datasets specified in config are auto-downloaded.
    for dataset in exe.datasets:
        dataset.restructure_assets(...)  # DatasetBag objects
    # ... do work, stage outputs ...
    path = exe.asset_file_path("Execution_Asset", "results.csv")
    # ... write to path ...
    # On exit: sets status to Stopped (or Failed on exception).

# Commit AFTER the with block — required, not optional.
exe.commit_output_assets()
```

**Key points:**
- The `with` block transitions the execution to `Running` on entry and to `Stopped` (or `Failed` on exception) on exit.
- On exception, status is set to `Failed` automatically and the exception propagates (the context manager does not suppress).
- Call `commit_output_assets()` **after** exiting the `with` block, not inside it. The context manager's `__exit__` only sets status to `Stopped`/`Failed`; `commit_output_assets()` is what uploads staged bytes, writes asset rows, and transitions `Stopped → Pending_Upload → Uploaded`. The call is idempotent — re-run after partial failure to resume.
- When using `deriva-ml-run`, the commit is handled automatically by the runner.

## Execution Working Directory

Each execution gets a local working directory at `<ml_working_dir>/Execution/<execution_rid>/`:

```
Execution/<execution_rid>/
├── asset/                    # Output assets staged for upload
│   ├── <schema>/
│   │   └── <AssetTable>/     # Files organized by asset table
│   └── ml/
│       └── Execution_Asset/  # Default output table
├── asset-type/               # Asset type metadata (JSONL)
├── feature/                  # Feature values organized by table/feature
└── downloaded-assets/        # Downloaded input assets
```

Access via Python API `exe.working_dir` (MCP) or `execution.working_dir` (Python).

## Execution Metadata Auto-Generation

Every execution automatically captures four types of metadata, uploaded to the `Execution_Metadata` table. These provide a complete record of the environment and configuration used, enabling reproducibility without any manual effort.

| Metadata Type | What It Contains | When Created |
|---------------|-----------------|--------------|
| `Deriva_Config` | `configuration.json` — the fully resolved `ExecutionConfiguration` as JSON (workflow, datasets, assets, description, config choices) | On execution creation |
| `Hydra_Config` | Hydra YAML files from runtime — the `.hydra/` directory contents including `config.yaml`, `overrides.yaml`, and `hydra.yaml` | After Hydra config resolution (CLI and notebook runs) |
| `Execution_Config` | `uv.lock` — the environment lock file capturing exact dependency versions | On execution creation (when present in the project) |
| `Runtime_Env` | Python and system environment snapshot — Python version, platform, installed packages, environment variables | On execution creation |

These metadata files are uploaded automatically during `commit_output_assets()`. You do not need to register them manually — they are created and staged by the execution lifecycle.

**Why this matters:** If a model produces unexpected results, the metadata lets you reconstruct the exact software environment (`uv.lock`), configuration (`Deriva_Config`, `Hydra_Config`), and runtime context (`Runtime_Env`) that produced them.

**Querying metadata:**
- Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` and inspect its metadata field for the auto-created files.
- Use `get_entities(hostname, catalog_id, schema="deriva-ml", table="Execution_Metadata", filters={"Execution": execution_rid})` to query metadata records directly (whole-row read).

## Dry Run Mode

Dry run mode lets you test the full pipeline without writing to the catalog:

- No execution record is created (uses a placeholder RID of `"0"`)
- No catalog writes occur — no provenance, no status updates
- Datasets and assets **are** still downloaded — you can verify data loading works
- Configuration is still resolved — you can verify parameters are correct
- Output files can still be written locally — you can verify the model runs

Every bundled execution template accepts a `--dry-run` flag that threads through to `dry_run=True` on the context-manager call. For Hydra-driven runs, pass `dry_run=true` on the `deriva-ml-run` invocation.

Use dry runs to:
- Test data loading and model initialization before committing to a full run
- Debug configuration issues without cluttering the catalog with failed executions
- Verify the pipeline end-to-end on a new machine or environment
