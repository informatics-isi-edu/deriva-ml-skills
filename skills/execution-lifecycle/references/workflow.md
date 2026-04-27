# Execution Workflow Reference

Step-by-step MCP tool and Python API examples for running executions. For background on the execution hierarchy, statuses, nested executions, and dry run mode, see `concepts.md`.

> The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them. Lifecycle tools also take an explicit `execution_rid` — there is no implicit "active execution".

## Table of Contents

1. [Tool Quick Reference](#tool-quick-reference)
2. [Setting Up a Workflow](#setting-up-a-workflow)
3. [MCP Tools: Full Execution Lifecycle](#mcp-tools-full-execution-lifecycle)
4. [Python API: Context Manager Pattern](#python-api-context-manager-pattern)
5. [CLI: deriva-ml-run](#cli-deriva-ml-run)
6. [Downloading Input Data](#downloading-input-data)
7. [Registering and Uploading Outputs](#registering-and-uploading-outputs)
8. [Notebook Results as Execution Assets](#notebook-results-as-execution-assets)
9. [Inspecting Executions](#inspecting-executions)
10. [Updating Execution State](#updating-execution-state)
11. [Nested Executions](#nested-executions)
12. [Re-Running After an Aborted Execution](#re-running-after-an-aborted-execution)
13. [Creating an Output Dataset](#creating-an-output-dataset)
14. [Complete Example: MCP Workflow](#complete-example-mcp-workflow)
15. [Complete Example: Python API](#complete-example-python-api)

---

## Tool Quick Reference

| Tool / API | Purpose |
|------|---------|
| `deriva_ml_get_dataset` / `get_entities` | Pre-flight: verify RIDs exist (legacy `validate_rids` was removed) |
| `deriva_ml_bag_info` | Pre-flight: check dataset size and cache status; also serves as a version-existence check |
| `deriva_ml_cache_dataset` | Pre-flight: download data into cache without execution |
| `deriva_ml_create_execution` | Create execution (finds/creates workflow automatically) |
| `deriva_ml_start_execution` | Sets status to `Running`, records start timestamp |
| `deriva_ml_commit_execution` | Sets status to `Completed` (success path) |
| `deriva_ml_abort_execution` | Sets status to `Failed`/`Aborted` (failure path) |
| `deriva_ml_update_execution` | Arbitrary status / message updates (replaces legacy `update_execution_status`) |
| Python API `exe.download_dataset_bag()` | Download dataset as BDBag within execution |
| Python API `ml.download_asset(rid)` | Download individual asset within execution |
| Python API `exe.asset_file_path()` | Register output file for upload |
| Python API `exe.upload_execution_outputs()` | Upload all registered files to catalog |
| `deriva_ml_get_execution` | Execution details by RID |
| `deriva_ml_add_nested_execution` | Link parent-child executions |
| `deriva_ml_list_execution_children` | Navigate parent → children (supports `recurse`) |
| `deriva_ml_list_execution_parents` | Navigate child → parent (supports `recurse`) |
| (gap) | Re-running an aborted execution: legacy `restore_execution` was removed; create a fresh execution from the prior config — see [Re-Running After an Aborted Execution](#re-running-after-an-aborted-execution) |

---

## Setting Up a Workflow

Every execution needs a workflow. Before creating an execution, check if a suitable workflow already exists.

### Check existing workflows

**Start with `rag_search`** to find workflows and types by concept:
```
rag_search("training workflows", doc_type="catalog-data")
rag_search("workflow types", doc_type="catalog-schema")
```

For the full structured list, call `deriva_ml_list_workflows(hostname, catalog_id)` or read `deriva://catalog/{hostname}/{catalog_id}/ml/workflows`.

### Find a workflow by URL

Call `deriva_ml_find_workflow_by_url(hostname, catalog_id, url)` with `url` set to the repository URL (e.g., `"https://github.com/org/repo"`).

### Create a new workflow

Call `deriva_ml_create_workflow(hostname, catalog_id, ...)` with:
- `name` (required): human-readable name (e.g., `"CIFAR-10 CNN Training"`)
- `workflow_type` (required): a term from the `Workflow_Type` vocabulary (e.g., `"Training"`)
- `description` (optional): what this workflow does

### Add a new workflow type

If the workflow type you need doesn't exist, call `add_term(hostname, catalog_id, schema="deriva-ml", table="Workflow_Type", name=..., description=...)`. The legacy `add_workflow_type` shortcut is gone — generic `add_term` handles all DerivaML built-in vocabularies.

### Set or update a workflow description

Call `deriva_ml_update_workflow(hostname, catalog_id, workflow_rid, description=...)`.

## MCP Tools: Full Execution Lifecycle

The MCP workflow mirrors the Python context manager but uses explicit tool calls for each step.

**Step 1: Create the execution.**

Call `deriva_ml_create_execution(hostname, catalog_id, ...)` with:
- `hostname`, `catalog_id` (required): catalog identification
- `workflow_name` (required): workflow name — creates the workflow if it doesn't exist
- `workflow_type` (required): workflow type vocabulary term
- `description` (optional): what this specific execution does
- `dataset_rids` (optional): list of input dataset RIDs
- `asset_rids` (optional): list of input asset RIDs
- `dry_run` (optional, default `false`): skip catalog writes for testing

Returns the execution RID. **Capture this RID** — you must pass it to every subsequent lifecycle call (the new server is stateless; there is no implicit "active execution").

**Step 2: Start the execution.**

Call `deriva_ml_start_execution(hostname, catalog_id, execution_rid)`. Sets status to "Running" and records the start time.

**Step 3: Download input data.**

Call Python API `exe.download_dataset_bag()` with `dataset_rid` and `version` to download a dataset as a BDBag. See [Downloading Input Data](#downloading-input-data) for full parameter details.

Call Python API `ml.download_asset(rid)` with `asset_rid` to download individual input assets.

**Step 4: Do your work.**

Run notebooks, scripts, or interactive analysis. Use Python API `exe.working_dir` to find the local working directory.

**Step 5: Register output files.**

Call Python API `exe.asset_file_path()` to register each output file for upload. See [Registering and Uploading Outputs](#registering-and-uploading-outputs) for full parameter details.

**Step 6: Commit (or abort) the execution.**

On success: call `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)`. Sets status to "Completed" and records the stop time.

On failure: call `deriva_ml_abort_execution(hostname, catalog_id, execution_rid)`. For arbitrary status transitions or progress messages mid-run, call `deriva_ml_update_execution(hostname, catalog_id, execution_rid, status=..., message=...)`.

**Step 7: Upload outputs.**

Call Python API `exe.upload_execution_outputs()` to upload all registered files to the catalog. Optionally set `clean_folder` to `false` to keep local staging files.

**Important:** Every lifecycle call takes the explicit `execution_rid` you captured in Step 1. There is no implicit active execution.

## Python API: Context Manager Pattern

The recommended Python approach uses a `with` block that auto-starts and auto-stops:

```python
from deriva_ml import DerivaML, ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)

# 1. Find or create a workflow
workflow = ml.create_workflow(
    name="Image Classification Training",
    workflow_type="Training",
    description="Train CNN on labeled image dataset"
)

# 2. Configure the execution
config = ExecutionConfiguration(
    workflow=workflow,
    datasets=["2-ABC1"],
    assets=["2-DEF2"],
    description="Training run on labeled images"
)

# 3. Run within context manager
with ml.create_execution(config) as exe:
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

    # Execution auto-stops on exit (status → Completed, or Failed on exception)
    # Outputs auto-uploaded on context exit
```

**Key points:**
- The `with` block automatically transitions the execution to `Running` on entry (equivalent to the MCP `deriva_ml_start_execution` tool) and to `Completed` (or `Failed`/`Aborted` on exception) on exit (equivalent to MCP `deriva_ml_commit_execution` / `deriva_ml_abort_execution`).
- If an exception occurs inside the block, status is set to "Failed" automatically.
- Call `upload_execution_outputs()` **after** exiting the `with` block, not inside it.
- When using `deriva-ml-run`, upload is handled automatically by the runner.

## CLI: deriva-ml-run

The CLI runner handles the full lifecycle automatically — creates execution, downloads data, runs the model function, uploads outputs, sets status.

```bash
# Inspect resolved config without running
uv run deriva-ml-run +experiment=baseline --info
uv run deriva-ml-run +experiment=baseline --cfg job

# Dry run (downloads data, runs model, does NOT upload to catalog)
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

## Downloading Input Data

### Download a dataset within an execution

Call Python API `exe.download_dataset_bag()` with:
- `dataset_rid` (required): RID of the dataset
- `version` (required): semantic version string (e.g., `"1.0.0"`)
- `materialize` (optional, default `true`): set to `false` for metadata only
- `exclude_tables` (optional): list of table names to skip during FK path traversal
- `timeout` (optional): `[connect_timeout, read_timeout]` in seconds

The dataset is downloaded as a BDBag to the execution's working directory, and the dataset is recorded as an input for provenance.

### Download a single asset

Call Python API `ml.download_asset(rid)` with `asset_rid`. Optionally set `dest_dir` to specify the destination (defaults to the execution's working directory). The asset is recorded as an input.

### Find the working directory

Call Python API `exe.working_dir` to get the local path where downloads are stored.

## Registering and Uploading Outputs

### Register files for upload

**Note:** The target asset table must already exist in the catalog before you can register files for upload to it. The built-in `Execution_Asset` table is always available. If you need a new domain-specific asset table (e.g., `"Image"`, `"Model"`), use the `work-with-assets` skill to create it first with `create_table` plus the standard hatrac column shape (the legacy `create_asset_table` shortcut was removed).

Call Python API `exe.asset_file_path()` with:
- `asset_name` (required): target asset table (e.g., `"Execution_Asset"`, `"Image"`, `"Model"`)
- `file_name` (required): path to an existing file to stage, or a filename for a new file to create
- `asset_types` (optional): list of `Asset_Type` vocabulary terms (defaults to `[asset_name]`)
- `description` (optional): human-readable description of the asset (applied to catalog record after upload)
- `copy_file` (optional, default `false`): `true` to copy, `false` to symlink
- `rename_file` (optional): rename the file during staging
- `metadata` (optional): dict of custom column values for tables with extra metadata columns

Returns a `file_path`. If `file_name` is a path to an existing file, it's symlinked (or copied) to the staging area. If it's just a filename, write your output to the returned path.

**Always provide a description** for execution assets so they are identifiable in the catalog.

### Upload all registered files

Call Python API `exe.upload_execution_outputs()` with `clean_folder` (optional, default `true`) to upload all staged files to the catalog, create asset records, and link them to the execution with role "Output".

**`Execution_Asset` vs domain asset tables:** Use `Execution_Asset` (the default) for general outputs like model weights, predictions, and plots. Use a domain asset table (e.g., `Image`, `Model`) when outputs should be queryable as first-class catalog entities with custom metadata.

For creating new asset tables and managing asset types, see the `work-with-assets` skill.

### Recording feature values

An execution can also record **feature values** (e.g., per-image predictions, classification labels). Like output files, feature values are **staged locally** and uploaded when Python API `exe.upload_execution_outputs()` is called — they are not written to the catalog immediately.

In MCP tools, call `deriva_ml_add_feature_values(hostname, catalog_id, target_table, feature_name, values=[...])` during the execution (the legacy single-value `add_feature_value` and `add_feature_value_record` are subsumed — pass a single-element list). In Python, call `execution.add_features(records)`. Both write JSONL files to the execution's `feature/` directory on disk. The catalog is updated when `upload_execution_outputs()` processes these files.

For creating features and populating values, see the `create-feature` skill.

## Notebook Results as Execution Assets

When a notebook is run via `deriva-ml-run-notebook` or `run_notebook()`, its outputs are automatically captured as execution assets. This happens without any extra registration steps beyond the normal notebook execution.

### What gets uploaded automatically

| Output | Asset Type | Description |
|--------|-----------|-------------|
| Executed `.ipynb` file | `Execution_Asset` | The fully executed notebook with all cell outputs (plots, tables, logs) preserved |
| Converted `.md` file | `Execution_Asset` | A Markdown rendering of the executed notebook, viewable directly in Chaise |

Both files are uploaded during `upload_execution_outputs()` after the notebook finishes.

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
    → Upload all outputs (registered files + notebook artifacts)
```

For the full notebook development and running workflow, see the `run-notebook` skill.

## Inspecting Executions

### Get execution details

Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to get an execution's workflow, status, description, timing, linked datasets/assets, Hydra config, and input/output summaries.

The same content is also available via the resource `deriva://catalog/{hostname}/{catalog_id}/ml/execution/{execution_rid}`.

### Find executions for a dataset or asset

Call `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)` and inspect its `executions` field to find all executions that used a dataset.

Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` to find the execution that produced an asset (returns producer info). For broader queries by workflow, use `deriva_ml_find_workflow_executions(hostname, catalog_id, workflow_rid)`.

## Updating Execution State

The legacy `update_execution_status` and `set_execution_description` tools were folded into `deriva_ml_update_execution`. Three patterns:

1. **Normal completion (success):**
   ```
   deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-YYYY")
   ```
2. **Failure marking:**
   ```
   deriva_ml_abort_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-YYYY")
   ```
3. **Arbitrary status / progress messages / description updates:**
   ```
   deriva_ml_update_execution(hostname="data.example.org", catalog_id="1",
       execution_rid="2-YYYY", status="Running", message="Processing batch 3 of 10")
   deriva_ml_update_execution(hostname="data.example.org", catalog_id="1",
       execution_rid="2-YYYY", description="Train CNN with augmented inputs (Markdown supported)")
   ```

Valid statuses: `"Pending"`, `"Running"`, `"Completed"`, `"Failed"`, `"Aborted"`.

## Nested Executions

### Link a child to a parent

Call `deriva_ml_add_nested_execution(hostname, catalog_id, ...)` with:
- `parent_rid` (required): RID of the parent execution
- `child_rid` (required): RID of the child execution
- `sequence` (optional): integer for ordering children

### Navigate the hierarchy

The legacy `list_nested_executions` was split into two directional tools:

- Parent → children: `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)`. Set `recurse=True` for the full tree.
- Child → parents: `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)`. Set `recurse=True` to walk up the full chain.

## Re-Running After an Aborted Execution

> **Known gap:** the legacy `restore_execution` tool has **no equivalent**. To re-run after a failure or abort, manually inspect the prior execution and create a fresh one.

Steps:

1. Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to retrieve the workflow, dataset RIDs, asset RIDs, and description from the original.
2. Decide whether to retry (transient failure) or fix something first (code/config bug).
3. Call `deriva_ml_create_execution(hostname, catalog_id, ...)` with the same workflow/dataset/asset config — this creates a **new** execution (new RID); the prior one stays in its terminal state for provenance.
4. Continue the lifecycle as normal.

Use cases:
- **Debugging** — inspect what data a failed execution was working with by reading its working directory at `<ml_working_dir>/Execution/<execution_rid>/`.
- **Continuing work** — start a new execution that consumes the same inputs.
- **Re-analysis** — run new analysis on the same inputs.

## Creating an Output Dataset

Call `deriva_ml_create_execution_dataset(hostname, catalog_id, execution_rid, ...)` to create a new dataset linked to the execution as an output:
- `execution_rid` (required): RID of the execution producing this dataset
- `description` (optional): dataset description
- `dataset_types` (optional): list of dataset type terms

This is useful when an execution's output is a curated set of records (not just files).

## Complete Example: MCP + Python API Workflow

End-to-end workflow combining MCP tools (for lifecycle management) with Python API (for I/O operations). All MCP tools take `hostname` and `catalog_id`; substitute `"data.example.org"` and `"1"` for your catalog.

**Step 1:** Call `deriva_ml_list_workflows(hostname="data.example.org", catalog_id="1")` (or read `deriva://catalog/data.example.org/1/ml/workflows`) to check for existing workflows.

**Step 2:** Call `deriva_ml_create_execution(hostname="data.example.org", catalog_id="1", workflow_name="Image Classification", workflow_type="Training", description="Train CNN on labeled CIFAR-10 subset", dataset_rids=["2-ABC1"])`. Capture the returned execution RID, e.g. `"2-YYYY"`.

**Step 3:** Call `deriva_ml_start_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-YYYY")`.

**Step 4:** Call Python API `exe.download_dataset_bag()` with `dataset_rid`: `"2-ABC1"`, `version`: `"1.0.0"`.

**Step 5:** Call Python API `exe.working_dir` to find the local data path. Run your training script.

**Step 6:** Call Python API `exe.asset_file_path()` with `asset_name`: `"Execution_Asset"`, `file_name`: `"model_weights.pt"`, `asset_types`: `["Model_Weights"]`. Write the weights to the returned path.

**Step 7:** Call Python API `exe.asset_file_path()` with `asset_name`: `"Execution_Asset"`, `file_name`: `"predictions.csv"`, `asset_types`: `["Predictions"]`. Write the predictions to the returned path.

**Step 8:** Call `deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-YYYY")`. (On failure, call `deriva_ml_abort_execution` instead.)

**Step 9:** Call Python API `exe.upload_execution_outputs()`.

## Complete Example: Python API

```python
from deriva_ml import DerivaML, ExecutionConfiguration
from deriva_ml.asset.aux_classes import AssetSpec

ml = DerivaML(hostname, catalog_id)

# Find or create workflow
workflow = ml.create_workflow(
    name="CIFAR-10 CNN Training",
    workflow_type="Training",
    description="Train 2-layer CNN on CIFAR-10 images"
)

# Configure with cached pretrained weights
config = ExecutionConfiguration(
    workflow=workflow,
    datasets=["2-ABC1"],
    assets=[AssetSpec(rid="3-JSE4", cache=True)],
    description="Training run with pretrained initialization"
)

with ml.create_execution(config) as exe:
    # Datasets auto-downloaded; access as DatasetBag objects
    for dataset in exe.datasets:
        dataset.restructure_assets(...)

    # Access working directory
    data_dir = exe.working_dir

    # ... training code ...

    # Register outputs
    weights_path = exe.asset_file_path(
        "Execution_Asset", "model_weights.pt", ["Model_Weights"]
    )
    torch.save(model.state_dict(), weights_path)

    preds_path = exe.asset_file_path(
        "Execution_Asset", "predictions.csv", ["Predictions"]
    )
    predictions_df.to_csv(preds_path, index=False)

# Upload after context manager exits
exe.upload_execution_outputs()
```
