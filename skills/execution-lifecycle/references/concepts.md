# Execution Concepts

Background on executions, workflows, and provenance in DerivaML. For the step-by-step guide, see `workflow.md`.

> The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Table of Contents

- [Executions in the Catalog](#executions-in-the-catalog)
- [Execution RIDs](#execution-rids)
- [Execution Structure](#execution-structure)
- [Execution Statuses](#execution-statuses)
- [Workflows and Workflow Types](#workflows-and-workflow-types)
- [Automatic Source Code Detection](#automatic-source-code-detection)
- [Nested Executions](#nested-executions)
- [Execution Data Flow](#execution-data-flow)
- [Creating and Managing Executions](#creating-and-managing-executions)
- [ExecutionConfiguration](#executionconfiguration)
- [The Execution Context Manager](#the-execution-context-manager)
- [Execution Working Directory](#execution-working-directory)
- [Execution Metadata Auto-Generation](#execution-metadata-auto-generation)
- [Dry Run Mode](#dry-run-mode)
- [Re-Running an Aborted Execution](#re-running-an-aborted-execution)
- [Schema Pinning for Long Runs](#schema-pinning-for-long-runs)
- [Offline Mode](#offline-mode)

---

## Executions in the Catalog

An execution is a catalog record that captures a unit of work — a model training run, a data analysis, a notebook evaluation, a feature annotation pass. Executions are the fundamental unit of provenance in DerivaML. They are persistent, queryable entities stored in the catalog alongside your data.

Every execution record answers: "What work was done? With what inputs? What was produced? What code and configuration were used?"

Executions are represented in the `Execution` table in the `deriva-ml` schema. Like all catalog records, each execution has a unique **RID** that permanently identifies it.

## Execution RIDs

Every execution has a unique RID (Resource IDentifier) — a short, immutable string like `2-YYYY` or `3-AB4C`. This RID is the primary way to reference an execution:

- **In MCP tools**: Pass `execution_rid` to `deriva_ml_get_execution`, `deriva_ml_list_execution_children`, `deriva_ml_list_execution_parents`, `deriva_ml_get_lineage`, etc.
- **In provenance queries**: Asset and dataset provenance records reference execution RIDs
- **In the web UI**: Each execution has a Chaise page at its RID-based URL
- **In citation**: `cite(hostname, catalog_id, rid)` generates a permanent URL for an execution
- **In nested relationships**: Parent-child links between executions use RIDs

RIDs are assigned by the catalog when the execution record is created and never change.

## Execution Structure

An execution record in the catalog has these relationships:

```
Execution
├── Workflow (FK)           — what kind of work was performed
├── Status (FK)             — current state (Running, Completed, Failed, ...)
├── Description             — human-readable purpose (supports Markdown)
├── Start/Stop timestamps   — when the work ran
├── Input Datasets          — which datasets were consumed (association table)
├── Input Assets            — which assets were consumed (association table)
├── Output Assets           — which files were produced (association table)
├── Code provenance         — git commit hash and repository URL
├── Configuration           — Hydra config choices and parameters
└── Nested Executions       — parent-child relationships (association table)
```

The input and output links are tracked through association tables with role information ("Input" or "Output"), so you can trace provenance in both directions — from an execution to its artifacts, or from an artifact back to the execution that created it.

**Querying executions:**
- Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` for full details (workflow, status, datasets, assets, timestamps).
- Read `deriva://catalog/{hostname}/{catalog_id}/ml/execution/{execution_rid}` for the same content as a resource.
- Call `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)` then inspect its `executions` field to find all executions that used a dataset.
- Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` to find the producer execution; use `deriva_ml_find_workflow_executions(...)` for the broader query.

**The ExecutionRecord class** in the Python API is the lightweight read-only representation of an execution record. It's returned by lookup and query methods:

```python
record = ml.lookup_execution("2-YYYY")
print(record.execution_rid)   # "2-YYYY"
print(record.status)          # "Completed"
print(record.description)     # "Train CNN on batch 1"
print(record.workflow_rid)    # "1-WXYZ"
```

`ExecutionRecord` is also what you get back from provenance queries like `asset.list_executions()` and `ml.find_workflow_executions()`.

## Execution Statuses

| Status | Meaning |
|--------|---------|
| `Created` | Record created in catalog, no work started |
| `Running` | Work in progress inside the context manager |
| `Stopped` | Algorithm finished successfully; outputs staged but not yet committed |
| `Failed` | Encountered an error (set by `__exit__` on exception, or by `update_status`) |
| `Pending_Upload` | `commit_output_assets()` has started uploading staged outputs |
| `Uploaded` | All staged outputs successfully committed to the catalog |
| `Aborted` | Manually stopped; staged work preserved for inspection/recovery |

Values are defined as the `ExecutionStatus` `StrEnum` in `deriva_ml.execution.state_store`.

### Status State Machine

```
Created → Running → Stopped → Pending_Upload → Uploaded
              ↓        ↓                       ↗ ↓
              ↓     Failed → Pending_Upload    ↑ Failed
              ↓                                ↑
              └──→ Pending_Upload (crash recovery)
Created → Aborted
Running → Aborted
```

| Transition | When It Occurs |
|-----------|----------------|
| `Created` → `Running` | Context manager `__enter__`; records `start_time` |
| `Running` → `Stopped` | Context manager `__exit__` on clean exit; records `stop_time` |
| `Running` → `Failed` | Context manager `__exit__` on exception; records the error message and propagates the exception |
| `Stopped` → `Pending_Upload` → `Uploaded` | `exe.commit_output_assets()` succeeds — uploads staged bytes, writes asset rows |
| `Stopped` → `Pending_Upload` → `Failed` | `commit_output_assets()` fails mid-upload; idempotent, re-call to resume |
| `Running` → `Pending_Upload` | **Crash recovery** path: a process died mid-execution without `__exit__` running. Re-hydrate via `ml.resume_execution(rid)` then call `exe.update_status(ExecutionStatus.Pending_Upload)` followed by `commit_output_assets()`. See `crash_recovery.py` bundled template. |
| `Created` → `Aborted` or `Running` → `Aborted` | `exe.abort()`. Staged rows are preserved (not discarded), so the user can inspect them and decide whether to salvage via `resume_execution` or clean up via `gc_executions`. |

`commit_output_assets()` is the single per-execution commit primitive (ADR-0009). It must be called **after** the `with` block exits — the context manager only sets status to `Stopped`/`Failed`, never commits. The call is idempotent: re-running after a partial failure picks up the failed rows and leaves already-uploaded ones alone.

For mid-run progress reporting (e.g. "epoch 12 of 20"), write JSON-lines to a metrics file via `exe.metrics_file().open("a")`. The catalog does not store free-form progress messages on the Execution row.

**The lifecycle in code:** Executions are authored in user-local Python via the `with ml.create_execution(config, workflow=workflow, dry_run=...) as exe:` context manager. The skills in this plugin ship runnable templates under `skills/<name>/scripts/` — copy the template, edit parameters, commit, then run with `deriva-ml-run`. The committed script's git URL + checksum become the workflow's reproducibility anchor. MCP tools (`deriva_ml_get_execution`, `deriva_ml_list_executions`, `deriva_ml_get_lineage`, etc.) are the read-side observation surface.

## Workflows and Workflow Types

Every execution references a **workflow** — a reusable definition of a kind of work.

A workflow can represent many things:
- **A program** — a Python script, a trained model pipeline, a CLI tool
- **A person performing a process** — a pathologist annotating slides, a curator reviewing data quality
- **A workflow manager** — an Airflow DAG, a Nextflow pipeline, a Snakemake workflow
- **A notebook** — a Jupyter notebook performing analysis or visualization

What matters is that it identifies *what kind of work* was done, so that executions are traceable and reproducible.

**Workflow_Type** is a controlled vocabulary term that categorizes workflows broadly — for example, "Training", "Inference", "Analysis", "ETL", "Annotation". These are terms in the `Workflow_Type` vocabulary.

**Workflow** is the specific workflow definition. It has:
- A **name** (e.g., "CIFAR-10 CNN Training")
- A **URL** (typically a GitHub repository, but could be a documentation page or any identifier)
- One or more **workflow types**
- A **description** of what it does

Workflows are created once and reused across many executions. For example, the same "CIFAR-10 CNN Training" workflow might be used for hundreds of training runs with different hyperparameters — each run is a separate execution.

### Finding and creating workflows

Before creating an execution, you need a workflow. Check for existing workflows first:
- Call `deriva_ml_list_workflows(hostname, catalog_id)` to list all workflows.
- Call `deriva_ml_find_workflow_by_url(hostname, catalog_id, url)` with the repository URL to find a workflow by its source.

If no suitable workflow exists, create one:
- Call `deriva_ml_create_workflow(hostname, catalog_id, name=..., workflow_type=..., description=...)`.
- If the workflow type doesn't exist yet, add it with `add_term(hostname, catalog_id, schema="deriva-ml", table="Workflow_Type", name=..., description=...)` first.

The bundled script templates do the lookup-or-create automatically: `ml.create_workflow(name, workflow_type, description)` mints a fresh row when no matching one exists.

## Automatic Source Code Detection

DerivaML automatically records the source code that produced each execution by detecting the workflow's origin and creating or reusing a workflow record with a source URL.

### How source detection works

| Workflow Source | How DerivaML Finds the URL | Example URL |
|----------------|---------------------------|-------------|
| **Python scripts** (`deriva-ml-run`) | Inspects the git repository — constructs a GitHub blob URL using the remote origin, current commit hash, and script file path | `https://github.com/org/repo/blob/abc1234/src/models/train.py` |
| **Notebooks** (`deriva-ml-run-notebook`) | Reads the `DERIVA_ML_WORKFLOW_URL` environment variable, which must be set before running the notebook | Value of `$DERIVA_ML_WORKFLOW_URL` |
| **Pure-Python (no `deriva-ml-run`)** | You pass a Workflow object built explicitly with `ml.create_workflow(name, workflow_type, url=..., checksum=...)` | Caller must supply the URL + commit hash; auto-detection only applies through `deriva-ml-run` |

For Python scripts, the URL includes the **exact commit hash** (not a branch name), ensuring the source reference is permanent and immutable. This means the URL always points to the specific code version that ran.

### Git commit enforcement

DerivaML enforces clean working trees by default. Both `deriva-ml-run` and `deriva-ml-run-notebook` check for uncommitted changes before creating an execution. If any are found, `DerivaMLDirtyWorkflowError` is raised and the run is aborted.

- **`--allow-dirty` flag** overrides the check for debugging iterations. The execution still records a git hash, but it may not match the code that actually ran — this is **degraded provenance**.
- Executions created with `--allow-dirty` should not be cited or used as production baselines.

### Workflow deduplication

DerivaML avoids creating duplicate workflow records. When a new execution is created:

1. The system computes the workflow's **source URL** (as described above)
2. It calls `deriva_ml_find_workflow_by_url` to check if a workflow with that URL already exists
3. If a match is found **and** the checksum matches, the existing workflow is reused
4. If no match is found, a new workflow record is created

This means that running the same script from the same commit reuses the same workflow record, while a new commit creates a new workflow (since the URL contains the commit hash).

### Setting notebook workflow URLs

For notebooks, set the environment variable before running:

```bash
export DERIVA_ML_WORKFLOW_URL="https://github.com/org/repo/blob/main/notebooks/analysis.ipynb"
uv run deriva-ml-run-notebook notebooks/analysis.ipynb
```

If `DERIVA_ML_WORKFLOW_URL` is not set, the notebook execution will still work but the workflow record will not have a source URL for provenance.

## Nested Executions

Executions can be organized into parent-child relationships for multi-step work:

```
Parent execution (e.g., "Hyperparameter Sweep")
├── Child 1 (e.g., "lr=0.001")
├── Child 2 (e.g., "lr=0.01")
└── Child 3 (e.g., "lr=0.1")
```

Common use cases:
- **Parameter sweeps** — parent represents the sweep, children are individual runs
- **Pipelines** — parent represents the pipeline, children are stages (preprocessing, training, evaluation)
- **Cross-validation** — parent represents the CV experiment, children are individual folds
- **Multi-experiment comparisons** — parent groups related experiments (e.g., "compare architectures")

Each child is a full execution with its own RID, inputs, outputs, and provenance. The parent-child link is tracked via an association table with an optional `sequence` number for ordering.

Use `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)` to walk down the tree and `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)` to walk up.

### How multiruns create nested executions

The `deriva-ml-run` CLI automatically creates nested executions when using `multirun_config` or `--multirun`:

```bash
uv run deriva-ml-run +multirun=lr_sweep
```

This creates:
1. A **parent execution** for the sweep — its description comes from `multirun_config`'s `description` field
2. One **child execution** per parameter combination — each with its own config, inputs, outputs, and status

The parent's RID is the single reference point for the entire sweep. All children are accessible via `deriva_ml_list_execution_children`.

### Manual nesting with the bundled template

For custom multi-step workflows, copy `skills/execution-lifecycle/scripts/nested_execution.py` and edit. The template encodes the canonical pattern:

```python
with ml.create_execution(parent_config, workflow=parent_workflow,
                         dry_run=args.dry_run) as parent_exe:
    for i, unit in enumerate(work_units):
        child_config = ExecutionConfiguration(description=f"Child {i}: {unit}")
        with ml.create_execution(child_config, workflow=child_workflow,
                                 dry_run=args.dry_run) as child_exe:
            # ... child work ...
            ...

        parent_exe.add_nested_execution(child_exe, sequence=i)
        if not args.dry_run:
            child_exe.commit_output_assets()

if not args.dry_run:
    parent_exe.commit_output_assets()
```

Each child is its own execution with its own inputs and outputs; the parent's `add_nested_execution(child)` writes the parent → child link. Each child's `commit_output_assets()` runs after its own `with` block exits; the parent's runs last so the parent's summary outputs (if any) commit after the children.

### Navigating nested execution hierarchies

**MCP tools:**

| Tool | Direction | Parameters |
|------|-----------|-----------|
| `deriva_ml_list_execution_children` | Parent → Children | `hostname`, `catalog_id`, `execution_rid`, `recurse=True` for all descendants |
| `deriva_ml_list_execution_parents` | Child → Parent | `hostname`, `catalog_id`, `execution_rid`, `recurse=True` for all ancestors |

**MCP resources:**

| Resource | What it returns |
|----------|----------------|
| `deriva://catalog/{h}/{c}/ml/execution/{rid}` | Execution details including status, workflow, timing, inputs, outputs |

**Python API:**

```python
# From parent to children
children = parent_execution.list_execution_children(recurse=False)
all_descendants = parent_execution.list_execution_children(recurse=True)

# From child to parent
parents = child_execution.list_execution_parents(recurse=False)

# Each child is an ExecutionRecord with .execution_rid, .status, .description
for child in children:
    print(f"{child.execution_rid}: {child.status} — {child.description}")
```

### Analyzing sweep results

After a multirun completes, the typical analysis flow is:

1. `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid="PARENT_RID")` — get all children
2. For each child, call `deriva_ml_get_execution(hostname, catalog_id, execution_rid=child_rid)` — get config parameters and results
3. Compare results across children (metrics, output assets)
4. Optionally, create a summary notebook that reads all children's outputs

The `run-notebook` skill covers how to build analysis notebooks that consume execution results.

## Execution Data Flow

An execution consumes inputs, does work in a local working directory, and produces outputs that get uploaded back to the catalog. Understanding this flow is key to working with executions.

### Consuming inputs

An execution's inputs are **datasets** and **assets** specified when the execution is created. During execution, you download these to a local working directory:

- **Datasets** are downloaded as BDBags — self-contained, versioned archives that include all member records, asset files, feature values, and vocabulary terms at the exact catalog state when the version was created. Call Python API `exe.download_dataset_bag()` with a dataset RID and version. See the `dataset-lifecycle` skill for how datasets and versions work, and its `references/bags.md` for details on the BDBag format.
- **Individual assets** (e.g., pretrained model weights) are downloaded directly. Call Python API `ml.download_asset(rid)` with an asset RID. See the `work-with-assets` skill for asset concepts including caching.

Both operations automatically record provenance — the downloaded dataset or asset is linked to the execution with role "Input".

### The working directory

Each execution gets a local working directory where all downloaded inputs and staged outputs live. This directory is created automatically and persists until cleaned up. Access it via Python API `exe.working_dir` (MCP) or `execution.working_dir` (Python). See [Execution Working Directory](#execution-working-directory) for the layout.

### Producing outputs

Output files (model weights, predictions, plots, etc.) must be **registered** before they can be uploaded to the catalog. Registration is done via Python API `exe.asset_file_path()`, which:

1. Takes an asset table name (e.g., `"Execution_Asset"`) and filename
2. Stages the file in the execution's working directory
3. Returns a file path — write your output to this path, or pass an existing file to be staged
4. Records the file's metadata (asset types, table) for upload

Registered files are **not yet in the catalog** — they exist only in the local staging area.

### Uploading outputs

After the execution's work is complete, call Python API `exe.commit_output_assets()` to commit all registered files to the catalog in one batch. This:

1. Uploads each staged file to the object store
2. Creates asset records in the appropriate asset tables (writing the descriptions you supplied at `asset_file_path()` time and the `Upload_Duration` on every row)
3. Links each asset to the execution with role "Output"
4. Transitions the execution `Stopped → Pending_Upload → Uploaded` (or `→ Failed` on error)
5. Optionally cleans up the local staging directory (`clean_folder=True` by default)
6. Returns an `UploadReport` (`total_uploaded`, `total_failed`, `per_table`, `errors`) — for per-asset path data, read `exe.uploaded_assets` after the call

If the caller bypasses the `with` block and calls `commit_output_assets()` on a still-`Running` execution, the method auto-stops the execution first; the end state is the same `Uploaded`. The call is idempotent — re-running after a partial failure picks up the failed rows and leaves the already-uploaded ones alone.

Until Python API `exe.commit_output_assets()` is called, output files exist only locally. This is a deliberate design — it allows the execution to complete (or fail) without partial uploads.

### Recording feature values

An execution can also produce **feature values** — structured annotations on catalog records (e.g., per-image classification labels, confidence scores). Like output files, feature values are **staged locally** and uploaded when Python API `exe.commit_output_assets()` is called:

- Inside the `with` block of an execution template, call `execution.add_features(records)`. This writes JSONL files to disk in the execution's `feature/` directory — the catalog is not updated until `commit_output_assets()` runs after the `with` block.
- For a one-shot CSV bulk-load, use the bundled `skills/create-feature/scripts/populate_feature_values.py` template.

Both output files and feature values are linked to the execution for provenance. For creating features and populating values, see the `create-feature` skill.

### The complete flow

```
Create execution → Start → Download inputs → Do work → Register outputs → Stop → Upload
                            ↓                               ↓                       ↓
                     Working directory              Staging area             Catalog updated
                     (downloaded data)        (files + feature JSONL)    (assets + features)
```

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

## Re-Running an Aborted Execution

> **Known gap:** there is no dedicated tool to restore an aborted execution. The pattern is to inspect the prior execution and create a fresh one with the same configuration.

When you need to re-run work after a failure or abort:

1. **Inspect the prior execution.** Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to retrieve the workflow RID, dataset RIDs, asset RIDs, and description from the original.
2. **Decide whether to retry.** If the failure was transient (network, timeout) re-running with the same config is the right move. If the failure was a code or config bug, fix it first.
3. **Re-run the committed script.** Use the same template (and the same dataset / asset / workflow parameters) that produced the original execution. The new run creates a fresh execution record with a new RID; the prior execution remains in its terminal state for provenance. If the failure happened *after* the work block but before commit (status `Stopped`/`Failed` with staged work), use `skills/execution-lifecycle/scripts/salvage_execution.py` instead — same execution RID, resume the commit phase.

### Finding execution RIDs to inspect

- **From the catalog**: Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` if you know the RID, or `get_entities(hostname, catalog_id, schema="deriva-ml", table="Execution", filters=...)` to search by workflow, status, or description (or `query_attribute` with a `path` expression for column projection / FK joins).
- **From local storage**: Read `deriva://storage/execution-dirs` to see execution working directories that still exist locally. Each entry includes the execution RID, a label, size, and modification time.
- **From provenance**: Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` to find which execution produced an asset, or `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)` and inspect its `executions` field to find executions that used it.
- **From the web UI**: Browse executions in Chaise and copy the RID from the record page.

## Pre-Flight Validation

Before running an experiment, several checks prevent runtime failures and data issues.

### Why pre-flight matters

Experiments fail at runtime when:
- Dataset RIDs in the config don't exist or point to wrong versions
- Asset RIDs (model weights, etc.) are invalid
- Bags are too large to download during execution
- Network issues during materialization

All of these can be caught before the execution context manager opens.

### The pre-flight checklist

| Step | Tool / Template | What it checks |
|------|------|---------------|
| Validate RIDs | `deriva_ml_get_dataset` / `get_entities` | All dataset and asset RIDs exist (check by typed lookup) |
| Check cache | `deriva_ml_bag_info` | Dataset sizes, cache status (`not_cached`, `cached_metadata_only`, `cached_materialized`, `cached_incomplete`); also doubles as a version-existence check |
| Warm cache | `skills/manage-storage/scripts/warm_cache.py` | Pre-fetches bags into local cache (no execution row) |
| Git clean | `git status` | No uncommitted changes (for CLI runs) |
| Config check | `--info` | Resolved Hydra config is correct (for CLI runs) |

### Cache status values

The `deriva_ml_bag_info` tool returns a `cache_status` field:

| Status | Meaning | Action |
|--------|---------|--------|
| `not_cached` | No local copy | Run `warm_cache.py` if large |
| `cached_metadata_only` | Table data present, assets not fetched | Run `warm_cache.py` (default materialize=True) |
| `cached_materialized` | Fully downloaded and validated | Ready to use — no action needed |
| `cached_incomplete` | Was cached but assets are missing | Run `warm_cache.py` to re-materialize |

### Prefetching strategy

For large datasets (>1 GB), warm the cache ahead of time rather than downloading during the execution. The bundled `skills/manage-storage/scripts/warm_cache.py` template handles this:

```bash
uv run python src/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0
```

Equivalent Python-API call (what the template runs under the hood):

```python
info = ml.bag_info(DatasetSpec(rid="28CT", version="0.9.0"))
print(f"Size: {info['total_asset_size']}, Cache: {info['cache_status']}")
if info["cache_status"] == "not_cached":
    ml.cache_dataset(DatasetSpec(rid="28CT", version="0.9.0"))
```

## Schema Pinning for Long Runs

DerivaML caches the catalog schema locally so reads don't pay a `/schema` round-trip on every call. By default, `refresh_schema()` re-fetches the cache when needed (e.g., after a known out-of-band mutation). **Pinning** the schema freezes that cache at its current snapshot so nothing — not even `refresh_schema(force=True)` — can replace it while the pin is held. This is the right discipline when a long-running experiment must see a stable schema view even if the catalog is migrating underneath.

### When to pin

- **Long training run on a shared catalog.** A schema migration landing mid-training (column rename, table split, FK retarget) can break the model's view of the data between epoch 12 and epoch 13. Pinning at the start of the run guarantees every read in the run sees the same shape.
- **Multi-step pipeline that must agree on schema.** When a sweep parent and its children all read the same target tables, pinning the parent's schema ensures children inherit a consistent view (the workspace's SQLite cache is shared across executions in the same `working_dir`).
- **Offline reproduction of a historical run.** If you cloned the catalog at a specific snaptime and want to run analysis against it, pin to freeze the analysis's view of that snapshot.

### How to pin

```python
from deriva_ml import DerivaML
ml = DerivaML(hostname=..., catalog_id=...)

# Freeze the local cache. Returns a SchemaDiff if the live catalog
# has already drifted from the cache (online mode only); None if
# the cache and live are in sync, or always None in offline mode.
drift = ml.pin_schema(reason="ResNet50 training v0.4.2 — Aug 2026 run")
if drift is not None:
    print("Live schema has moved on; pin was applied to cached snapshot.")
    print(drift)  # structural diff (added / removed tables / columns / FKs)
```

`pin_schema(reason=...)` stores the reason alongside the pin; you can read it later with `ml.pin_status()`. The reason field is the operational log entry — it's what answers "why is this pinned?" three months later.

### Working with a pin

| Method | Effect |
|---|---|
| `ml.pin_status()` | Returns `PinStatus(pinned, pinned_at, pin_reason, pinned_snapshot_id)` — current pin state |
| `ml.diff_schema()` | Returns the structural diff between cached and live schemas (online mode only) — use to see what the migration changed without breaking the pin |
| `ml.unpin_schema()` | Clears the pin. After unpinning, `refresh_schema()` is allowed again |
| `ml.refresh_schema(force=True)` while pinned | **Raises `DerivaMLSchemaPinned`** — `force=True` does NOT bypass a pin. Call `unpin_schema()` first |

### Composition with the dirty-tree rule

Pinning the schema is the **environment-side** discipline; the git-clean-tree rule (`DerivaMLDirtyWorkflowError`) is the **code-side** discipline. Both should be in place for any production run — together they guarantee the run is reproducible as (committed code) × (frozen catalog shape). Either alone leaves a reproducibility gap.

### Common errors

- `DerivaMLSchemaPinned` — `refresh_schema()` or `refresh_schema(force=True)` was called while a pin is held. Resolution: `ml.unpin_schema()` first, or skip the refresh if the pinned snapshot is still the right view.
- `DerivaMLSchemaRefreshBlocked` — `refresh_schema()` (without `force=True`) was called while the workspace has pending rows. Resolution: commit the pending work first (`ml.commit_pending_executions()`), or `force=True` if you accept the risk that staged rows may reference columns that disappeared.

## Offline Mode

`ConnectionMode.offline` lets a DerivaML instance operate against a previously-cached schema with **no network calls** except RID leases and the final upload. Every write — execution creation, status transitions, feature values, asset registrations — stages into the workspace's local SQLite and stays there until you drain it with `ml.commit_pending_executions()`.

### When to use offline mode

- **Laptop / disconnected work.** Author and run an execution on a plane; upload when you land. The execution's full state (status, staged outputs, feature values) survives in the workspace SQLite until you reconnect.
- **Throttled / unreliable network.** Batch jobs on a cluster where the per-call network hop to the catalog dominates wall time. Offline mode amortizes the cost into one bulk upload.
- **Replay against a frozen catalog snapshot.** Combined with a pinned schema, offline mode gives you a fully reproducible run with no network dependency on the live catalog.

### How to enter offline mode

```python
from deriva_ml import ConnectionMode, DerivaML

ml = DerivaML(
    hostname="data.example.org", catalog_id="1",
    mode=ConnectionMode.offline,
    # working_dir must contain a schema cache from a prior online run
    working_dir="/path/to/workspace",
)
assert ml.mode is ConnectionMode.offline
```

**Prerequisite:** the workspace's schema cache must already exist (populated by a prior online `DerivaML.__init__` or `refresh_schema()` against the same `(hostname, catalog_id)`). Offline mode refuses to bootstrap from scratch — there's no live catalog to fetch a schema from. Trying to start offline against an unpopulated workspace raises `DerivaMLConfigurationError`.

`DerivaML.from_context()` does **not** take a `mode` argument — to start offline, construct `DerivaML(...)` explicitly.

### What works offline

| Operation | Offline behavior |
|---|---|
| `ml.create_execution(config) as exe:` | Works. Execution row stages to SQLite; status transitions stage too. |
| `exe.add_features(records)` | Works. Feature values stage to SQLite. |
| `exe.asset_file_path(...)` | Works. Files stage in the local working directory as usual. |
| `exe.create_dataset(...)` | Works. Dataset row stages to SQLite. |
| Read-side calls (`ml.find_datasets()`, `ml.lookup_feature(...)`, etc.) | Work — served from the cached schema and any locally-staged rows. |
| `ml.refresh_schema()` | **Raises `DerivaMLOfflineError`** — refresh requires online mode. |
| `ml.diff_schema()` | **Raises `DerivaMLOfflineError`** — diff needs live catalog. |
| `exe.commit_output_assets()` | Drains this one execution's staged rows + asset files. Requires network at call time. |
| `ml.commit_pending_executions()` | Drains every staged execution in one pass. The canonical "back online — flush everything" call. |

### Composing offline mode with the upload drain

The full pattern for offline-then-online:

```python
# 1. Initial online cache population (one-time, with network).
ml = DerivaML(hostname=..., catalog_id=...,
              working_dir="/workspace/project-x")
# Schema cache now populated under /workspace/project-x.

# 2. Switch to offline. Run N executions over time without network.
ml_offline = DerivaML(hostname=..., catalog_id=...,
                       mode=ConnectionMode.offline,
                       working_dir="/workspace/project-x")
for config in configs_to_run:
    with ml_offline.create_execution(config) as exe:
        do_work(exe)
    # No commit_output_assets() yet — let everything stage.

# 3. Reconnect. Drain everything in one pass.
ml_online = DerivaML(hostname=..., catalog_id=...,
                      working_dir="/workspace/project-x")
report = ml_online.commit_pending_executions(
    execution_rids=None,        # None = drain every staged execution
    clean_folder=False,         # True to also wipe working dirs after success
)
print(report)  # UploadReport: total_uploaded, total_failed, per_table, errors
```

### Common errors

- `DerivaMLOfflineError` — A read that requires the live catalog was called in offline mode (`refresh_schema`, `diff_schema`, or any direct `ml.catalog.get(...)` call). Resolution: drop back to online mode for that call, or skip it.
- `DerivaMLConfigurationError: offline mode requires a cached schema...` — The workspace has no schema cache. Resolution: run online once with the same `working_dir` to populate it.
- `DerivaMLConfigurationError: cached schema is for X/Y, but __init__ was called with A/B` — The workspace cache is for a different `(hostname, catalog_id)`. Resolution: use a different `working_dir` per catalog, or refresh online against the new catalog.
