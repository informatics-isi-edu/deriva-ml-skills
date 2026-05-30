# Execution Workflow Reference

Step-by-step recipes for authoring and running DerivaML executions. For background on the execution hierarchy, statuses, nested executions, and dry run mode, see `concepts.md`.

> The MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly.

## Table of Contents

1. [Tool + Template Quick Reference](#tool--template-quick-reference)
2. [Setting Up a Workflow](#setting-up-a-workflow)
3. [Bundled Script Templates: Full Execution Lifecycle](#bundled-script-templates-full-execution-lifecycle)
4. [Python API: Context Manager Pattern](#python-api-context-manager-pattern)
5. [CLI: deriva-ml-run](#cli-deriva-ml-run)
6. [Downloading Input Data](#downloading-input-data)
7. [Registering and Committing Outputs](#registering-and-committing-outputs)
8. [Notebook Results as Execution Assets](#notebook-results-as-execution-assets)
9. [Inspecting Executions](#inspecting-executions)
10. [Nested Executions](#nested-executions)
11. [Re-Running After an Aborted Execution](#re-running-after-an-aborted-execution)
12. [Creating an Output Dataset](#creating-an-output-dataset)
13. [Complete Example: Bundled Template](#complete-example-bundled-template)

---

## Tool + Template Quick Reference

**Read / observe (MCP)** — stateless, safe from any model turn:

| Tool / Resource | Purpose |
|---|---|
| `deriva_ml_get_dataset` / `get_entities` | Pre-flight: verify RIDs exist |
| `deriva_ml_bag_info` | Pre-flight: check dataset size and cache status; doubles as a version-existence check |
| `deriva_ml_get_execution` | Execution details by RID |
| `deriva_ml_list_executions` | Browse executions (filter by `workflow_rid`, `workflow_type`, `status`) |
| `deriva_ml_find_workflow_executions` | All executions for one workflow |
| `deriva_ml_get_lineage` | Walk provenance for a RID (asset / dataset / execution) |
| `deriva_ml_list_execution_children` | Parent → children navigation |
| `deriva_ml_list_execution_parents` | Child → parents navigation |

**Author / mutate (bundled script templates)** — copy from `skills/<name>/scripts/`, edit, commit, run via `deriva-ml-run`:

| Template | Replaces / Use case |
|---|---|
| `execution-lifecycle/scripts/basic_execution.py` | One-shot run producing output assets |
| `execution-lifecycle/scripts/nested_execution.py` | Parent run with N children (sweeps, pipelines, fan-out batches) |
| `execution-lifecycle/scripts/salvage_execution.py` | Drive `commit_output_assets()` on a `Stopped`/`Failed` execution with staged outputs |
| `execution-lifecycle/scripts/crash_recovery.py` | `Running → Pending_Upload` direct transition after a hard crash; `--abort` mode to discard |
| `create-feature/scripts/populate_feature_values.py` | Bulk-load feature values from a CSV |
| `manage-storage/scripts/warm_cache.py` | Pre-fetch a dataset bag into local cache |
| `work-with-assets/scripts/upload_asset.py` | Register local files as catalog assets |
| `work-with-assets/scripts/download_asset.py` | Pull catalog assets with execution-input provenance |

**Python API (used inside template work blocks)**:

| API | Purpose |
|---|---|
| `ml.create_workflow(name, workflow_type, description)` | Mint a workflow record |
| `ml.create_execution(config, workflow=workflow, dry_run=...) as exe:` | Open the execution context manager |
| `exe.download_dataset_bag(spec)` | Download dataset as BDBag (recorded as input) |
| `exe.download_asset(rid)` | Download an asset (recorded as input; auto-tagged `Input_File`) |
| `exe.asset_file_path(asset_table, file_name, ...)` | Register an output file for staging |
| `exe.add_features(records)` | Stage feature values for upload |
| `exe.create_dataset(dataset_types, description)` | Create an output dataset linked to this execution |
| `exe.add_nested_execution(child, sequence=...)` | Link a child execution to this parent |
| `exe.abort()` | Transition to `Aborted` (staged work preserved for inspection) |
| `exe.commit_output_assets()` | **After the `with` block** — upload staged bytes, write asset rows, transition `Stopped → Pending_Upload → Uploaded`. Idempotent. |

---

## Setting Up a Workflow

Every execution needs a workflow. The bundled templates call `ml.create_workflow(...)` automatically; this section covers ad-hoc workflow management.

### Check existing workflows

**Start with `rag_search`** to find workflows and types by concept:
```
rag_search("training workflows", doc_type="catalog-data")
rag_search("workflow types", doc_type="catalog-schema")
```

For the full structured list, call `deriva_ml_list_workflows(hostname, catalog_id)` or read `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/workflows`.

### Find a workflow by URL

Call `deriva_ml_find_workflow_by_url(hostname, catalog_id, url_or_checksum)` with the repository URL.

### Create a new workflow

Call `deriva_ml_create_workflow(hostname, catalog_id, ...)` with:
- `name` (required): human-readable name (e.g., `"CIFAR-10 CNN Training"`)
- `workflow_type` (required): a term from the `Workflow_Type` vocabulary
- `url` (required): URL of the workflow source code (typically a GitHub blob URL with commit hash)
- `checksum` (optional): SHA of the source
- `description` (optional): what this workflow does

### Add a new workflow type

If the term doesn't exist, call `add_term(hostname, catalog_id, schema="deriva-ml", table="Workflow_Type", name=..., description=...)`.

### Update a workflow

Call `deriva_ml_update_workflow(hostname, catalog_id, workflow_rid, description=..., workflow_type=...)`.

---

## Bundled Script Templates: Full Execution Lifecycle

For any catalog-mutating execution, **copy a bundled template** into the user's project (typically `src/scripts/<task>.py`), edit the parameters and the work block, commit the script, then run with `deriva-ml-run`. The committed script's git URL + commit hash become the workflow's reproducibility anchor.

The basic execution shape:

```python
ml = DerivaML(args.hostname, args.catalog_id)

workflow = ml.create_workflow(
    name="<task name>",
    workflow_type=args.workflow_type,
    description="<task description>",
)

config = ExecutionConfiguration(description="<execution description>")

with ml.create_execution(config, workflow=workflow,
                         dry_run=args.dry_run) as execution:
    # On enter: Running.
    # ... do work, stage outputs ...
    # On exit: Stopped (or Failed on exception).

# Required: commit AFTER the with block.
if not args.dry_run:
    execution.commit_output_assets()
```

Pick the template that matches the shape of your work:

- **`basic_execution.py`** — one-shot run that produces output assets (model weights, prediction CSVs, plots, derived datasets).
- **`nested_execution.py`** — parent run with multiple children (parameter sweeps, sequential pipeline stages, fan-out batch processing).
- **`salvage_execution.py`** — drive `commit_output_assets()` on an execution that exited the `with` block (status `Stopped`/`Failed`) but never committed (or partially failed). Idempotent: re-call to resume.
- **`crash_recovery.py`** — recover from a hard crash where the process died mid-execution and the catalog row is stuck `Running`. Direct `Running → Pending_Upload` transition; or `--abort` to discard.

---

## Python API: Context Manager Pattern

The canonical pattern, used inside every bundled template:

```python
from deriva_ml import DerivaML
from deriva_ml.execution import ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)

# 1. Find or create a workflow
workflow = ml.create_workflow(
    name="Image Classification Training",
    workflow_type="Training",
    description="Train CNN on labeled image dataset"
)

# 2. Configure the execution
config = ExecutionConfiguration(
    datasets=["2-ABC1"],
    assets=["2-DEF2"],
    description="Training run on labeled images"
)

# 3. Run within context manager (workflow is passed to create_execution, not to config)
with ml.create_execution(config, workflow=workflow) as exe:
    # Execution auto-starts (status → Running)
    # Datasets specified in config are auto-downloaded

    # Access downloaded datasets (DatasetBag objects)
    for dataset in exe.datasets:
        dataset.restructure_assets(...)

    # Do your work
    results = train_model(exe.working_dir)

    # Register output files
    output_path = exe.asset_file_path("Execution_Asset", "model_weights.pt")
    save_model(results, output_path)

    # On exit: status → Stopped (or Failed on exception)

# Commit AFTER the with block — required, not optional
exe.commit_output_assets()
```

**Key points:**

- The `with` block transitions the execution to `Running` on entry, and to `Stopped` (or `Failed` on exception) on exit.
- On exception, status is set to `Failed` automatically and the exception propagates (the context manager does not suppress).
- Call `commit_output_assets()` **after** exiting the `with` block, not inside it. The context manager's `__exit__` only sets status to `Stopped`/`Failed`; `commit_output_assets()` is what uploads staged bytes, writes asset rows, and transitions `Stopped → Pending_Upload → Uploaded`. The call is idempotent — re-run after partial failure to resume.
- When using `deriva-ml-run`, the commit is handled automatically by the runner.

---

## CLI: deriva-ml-run

The CLI runner handles the full lifecycle automatically — creates execution, downloads data, runs the model function, commits outputs, sets status.

```bash
# Inspect resolved config without running
uv run deriva-ml-run +experiment=baseline --info
uv run deriva-ml-run +experiment=baseline --cfg job

# Dry run (downloads data, runs model, does NOT commit to catalog)
uv run deriva-ml-run +experiment=baseline dry_run=True

# Production run
uv run deriva-ml-run +experiment=baseline

# Override parameters
uv run deriva-ml-run +experiment=baseline model_config.learning_rate=0.001

# Override host/catalog
uv run deriva-ml-run --host ml-dev.derivacloud.org --catalog 99 +experiment=baseline

# Named multirun (parameter sweep — creates nested executions automatically)
uv run deriva-ml-run +multirun=lr_sweep

# Ad-hoc multirun
uv run deriva-ml-run +experiment=baseline model_config.learning_rate=1e-2,1e-3,1e-4 --multirun
```

For the full CLI reference including pre-flight checks, Hydra override syntax, and troubleshooting, see `cli-reference.md`.

---

## Downloading Input Data

### Download a dataset within an execution

Call `exe.download_dataset_bag(spec)` with a `DatasetSpec(rid="...", version="...")`. Optional fields on `DatasetSpec`:
- `materialize` (default `True`): set to `False` for metadata only
- `exclude_tables`: set of table names to skip during FK path traversal
- `timeout`: `(connect_timeout, read_timeout)` tuple in seconds

The dataset is downloaded as a BDBag to the execution's working directory, and the dataset is recorded as an input for provenance.

### Download a single asset

Call `exe.download_asset(asset_rid)`. The asset is recorded as an input with the `Input_File` auto-tag. Optional `dest_dir` for a custom destination; the platform default is `working_dir/downloads/<asset_rid>/`.

### Find the working directory

`exe.working_dir` returns the local path where downloads are stored.

---

## Registering and Committing Outputs

### Register files for upload

**Note:** The target asset table must already exist in the catalog before you can register files for upload to it. The built-in `Execution_Asset` table is always available. If you need a new domain-specific asset table (e.g., `"Image"`, `"Model"`), use the `work-with-assets` skill to create it first with `create_table` plus the standard hatrac column shape.

Call `exe.asset_file_path()` with:
- `asset_name` (required): target asset table (e.g., `"Execution_Asset"`, `"Image"`, `"Model"`)
- `file_name` (required): path to an existing file to stage, or a filename for a new file to create
- `asset_types` (optional): list of `Asset_Type` vocabulary terms (defaults to `[asset_name]`)
- `description` (optional): human-readable description of the asset
- `copy_file` (optional, default `False`): `True` to copy, `False` to symlink
- `rename_file` (optional): rename the file during staging
- `metadata` (optional): dict of custom column values for tables with extra metadata columns

Returns an `AssetFilePath`. If `file_name` is an existing path, it's symlinked (or copied) to staging. If it's just a filename, write your output to the returned path.

**Always provide a description** for execution assets so they are identifiable in the catalog.

### Commit all registered files

Call `exe.commit_output_assets()` after the `with` block. Optional kwargs:
- `clean_folder` (default uses the DerivaML instance's setting): `True` to delete the working-folder copies after upload; `False` to keep them
- `progress_callback`: optional callback receiving `UploadProgress` events

The call uploads staged bytes to the object store, writes asset records (with descriptions + `Upload_Duration`), links each asset to the execution with role `Output` and the `Output_File` auto-tag, and transitions the execution `Stopped → Pending_Upload → Uploaded`. Returns an `UploadReport` (`total_uploaded`, `total_failed`, `per_table`, `errors`); per-asset paths on `exe.uploaded_assets`.

**Idempotent on re-call** — `BagCatalogLoader`'s `match_by_columns` dedup makes row inserts safe. Re-call after a partial failure resumes from the last known-good state.

**`Execution_Asset` vs domain asset tables:** Use `Execution_Asset` (the default) for general outputs like model weights, predictions, and plots. Use a domain asset table (e.g., `Image`, `Model`) when outputs should be queryable as first-class catalog entities with custom metadata.

For creating new asset tables and managing asset types, see the `work-with-assets` skill.

### Recording feature values

An execution can also record **feature values** (e.g., per-image predictions, classification labels). Like output files, feature values are **staged locally** and uploaded when `exe.commit_output_assets()` is called — they are not written to the catalog immediately.

Inside the execution context manager, call `execution.add_features(records)` where `records` is a list of typed `FeatureRecord` objects (one per row to add). Use the bundled `skills/create-feature/scripts/populate_feature_values.py` template for the canonical CSV-to-features bulk-load flow.

For creating features and querying values, see the `create-feature` skill.

---

## Notebook Results as Execution Assets

When a notebook is run via `deriva-ml-run-notebook` or `run_notebook()`, its outputs are automatically captured as execution assets. This happens without any extra registration steps beyond the normal notebook execution.

### What gets uploaded automatically

| Output | Asset Type | Description |
|--------|-----------|-------------|
| Executed `.ipynb` file | `Execution_Asset` | The fully executed notebook with all cell outputs (plots, tables, logs) preserved |
| Converted `.md` file | `Execution_Asset` | A Markdown rendering of the executed notebook, viewable directly in Chaise |

Both files are uploaded during `commit_output_assets()` after the notebook finishes.

### Registering additional output files from notebooks

During notebook execution, use `exe.asset_file_path()` to register output files (plots, CSVs, model artifacts) just like in script-based executions:

```python
# Inside a notebook running within an execution context
output_path = execution.asset_file_path("Execution_Asset", "roc_curves.png", ["Plot"])
plt.savefig(output_path)
```

All files registered via `asset_file_path()` are uploaded alongside the notebook `.ipynb` and `.md` files when the execution completes.

### Notebook execution flow

```
run_notebook() / deriva-ml-run-notebook
    → Create execution (with workflow from DERIVA_ML_WORKFLOW_URL or auto-detected)
    → Download input datasets and assets
    → Execute notebook cells (papermill)
    → Save executed .ipynb
    → Convert to .md
    → Register .ipynb and .md as execution assets
    → Commit all outputs (registered files + notebook artifacts)
```

For the full notebook development and running workflow, see the `run-notebook` skill.

---

## Inspecting Executions

### Get execution details

Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to get an execution's workflow, status, description, timing, linked datasets/assets, Hydra config, and input/output summaries.

The same content is also available via the resource `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/execution/{execution_rid}`.

### Browse executions

- `deriva_ml_list_executions(hostname, catalog_id, workflow_type=..., status=..., sort=True)` — browse all executions; filter by workflow type or status.
- `deriva_ml_find_workflow_executions(hostname, catalog_id, workflow_rid)` — all executions for a specific workflow.
- `deriva_ml_find_experiments(hostname, catalog_id, workflow_rid=..., status=...)` — Hydra-driven executions only.

### Find executions for a dataset or asset

Call `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)` and inspect its `executions` field to find all executions that used a dataset.

Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` to find the execution that produced an asset (returns producer info). For broader queries, `deriva_ml_find_workflow_executions(...)`.

### Walk lineage

Call `deriva_ml_get_lineage(hostname, catalog_id, rid, depth=...)` for any RID (asset, dataset, or execution) — returns the upstream provenance tree.

---

## Nested Executions

For parameter sweeps, pipeline stages, or fan-out batches, use the bundled `skills/execution-lifecycle/scripts/nested_execution.py` template — it encodes the parent + N-children pattern with the correct commit ordering.

Inside the template, link each child to the parent with `parent_exe.add_nested_execution(child_exe, sequence=i)` after the child's `with` block exits. Then commit each child individually so failed children don't block later ones. The parent's `commit_output_assets()` runs last so any parent-level summary outputs commit after the children.

### Navigate the hierarchy

Two MCP tools navigate parent-child relationships post-run:

- Parent → children: `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)`. Set `recurse=True` for the full tree.
- Child → parents: `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)`. Set `recurse=True` to walk up the full chain.

---

## Re-Running After an Aborted Execution

> **Known gap:** there is no dedicated tool to restore an aborted execution. To re-run after a failure or abort, inspect the prior execution and re-run the committed script that produced it.

Steps:

1. Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to retrieve the workflow, dataset RIDs, asset RIDs, and description from the original.
2. Decide whether to retry (transient failure) or fix something first (code/config bug).
3. Re-run the committed script (with the same parameters, or with fixes if needed). The new run creates a fresh execution record with a new RID; the prior one stays in its terminal state for provenance.

If the failure happened *after* the `with` block but before `commit_output_assets()` succeeded (status `Stopped`/`Failed` with staged work), use `skills/execution-lifecycle/scripts/salvage_execution.py` instead — same execution RID, resume the commit phase.

If the failure was a hard process crash that left the execution stuck `Running`, use `skills/execution-lifecycle/scripts/crash_recovery.py`.

Use cases:
- **Debugging** — inspect what data a failed execution was working with by reading its working directory at `<ml_working_dir>/Execution/<execution_rid>/`.
- **Continuing work** — start a new execution that consumes the same inputs.
- **Re-analysis** — run new analysis on the same inputs.

---

## Creating an Output Dataset

Inside an execution's `with` block, call `execution.create_dataset(dataset_types=[...], description="...")` to create a new dataset that's linked to the execution as an output:

```python
with ml.create_execution(config, workflow=workflow) as execution:
    # ... do work, identify the records to include ...
    new_dataset = execution.create_dataset(
        dataset_types=["Inference"],
        description="Predictions from <model> over <input dataset>",
    )
    new_dataset.add_dataset_members(members_dict)
```

This is useful when an execution's output is a curated set of records (not just files).

---

## Complete Example: Bundled Template

End-to-end walkthrough using the `basic_execution.py` template. All steps run inside the committed script; MCP tools only show up post-run for inspection.

**Step 1: Copy the template.**
```bash
cp skills/execution-lifecycle/scripts/basic_execution.py src/scripts/train_cifar.py
```

**Step 2: Edit `src/scripts/train_cifar.py`.** Replace the placeholders:
- Workflow `name="<task name>"` → `name="CIFAR-10 CNN Training"`
- Workflow `description="..."` → meaningful description
- Add task-specific argparse arguments (e.g., `--dataset-rid`, `--learning-rate`)
- Fill in the `with` block with `exe.download_dataset_bag(...)`, training code, `exe.asset_file_path(...)`

**Step 3: Commit the script.**
```bash
git add src/scripts/train_cifar.py
git commit -m "feat(scripts): CIFAR-10 training script"
```

**Step 4: Dry run.**
```bash
uv run python src/scripts/train_cifar.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Training \
    --dataset-rid 2-ABC1 \
    --dry-run
```

**Step 5: Production run.**
```bash
uv run python src/scripts/train_cifar.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Training \
    --dataset-rid 2-ABC1
```

Or via the CLI runner (preferred for Hydra-driven experiments):
```bash
uv run deriva-ml-run +experiment=cifar_baseline
```

**Step 6: Inspect post-run (MCP).**
```
deriva_ml_get_execution(hostname="data.example.org", catalog_id="1", execution_rid="<rid>")
```

Or read `deriva://catalog/data.example.org/1/deriva-ml/execution/<rid>`.

Verify the status is `Uploaded`, the inputs are linked, output assets are attached, and the git hash matches your commit.
