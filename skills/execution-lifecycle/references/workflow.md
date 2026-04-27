# Execution Workflow Reference

Step-by-step MCP tool and Python API examples for running executions. For background on the execution hierarchy, statuses, nested executions, and dry run mode, see `concepts.md`.

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
12. [Restoring a Previous Execution](#restoring-a-previous-execution)
13. [Creating an Output Dataset](#creating-an-output-dataset)
14. [Complete Example: MCP Workflow](#complete-example-mcp-workflow)
15. [Complete Example: Python API](#complete-example-python-api)

---

## Tool Quick Reference

| Tool / API | Purpose |
|------|---------|
| `validate_rids` | Pre-flight: verify RIDs and versions exist |
| `bag_info` | Pre-flight: check dataset size and cache status |
| `cache_dataset` | Pre-flight: download data into cache without execution |
| `create_execution` | Create execution (finds/creates workflow automatically) |
| `start_execution` / `stop_execution` | Manage lifecycle timing |
| Python API `exe.download_dataset_bag()` | Download dataset as BDBag within execution |
| Python API `ml.download_asset(rid)` | Download individual asset within execution |
| Python API `exe.asset_file_path()` | Register output file for upload |
| Python API `exe.upload_execution_outputs()` | Upload all registered files to catalog |
| resource `deriva://execution/{rid}` | Active execution details |
| `update_execution_status` | Progress tracking |
| `restore_execution` | Re-download previous execution's inputs |
| `add_nested_execution` | Link parent-child executions |
| `list_nested_executions` | Navigate parent → children (supports `recurse`) |
| resource `deriva://execution/{rid}` | Navigate child → parent (supports `recurse`) |

---

## Setting Up a Workflow

Every execution needs a workflow. Before creating an execution, check if a suitable workflow already exists.

### Check existing workflows

**Start with `rag_search`** to find workflows and types by concept:
```
rag_search("training workflows", doc_type="catalog-data")
rag_search("workflow types", doc_type="catalog-schema")
```

For the full structured list, read `deriva://catalog/workflows` or `deriva://catalog/workflow-types`.

### Find a workflow by URL

Call `lookup_workflow_by_url` with `url` set to the repository URL (e.g., `"https://github.com/org/repo"`).

### Create a new workflow

Call `create_workflow` with:
- `name` (required): human-readable name (e.g., `"CIFAR-10 CNN Training"`)
- `workflow_type` (required): a term from the `Workflow_Type` vocabulary (e.g., `"Training"`)
- `description` (optional): what this workflow does

### Add a new workflow type

If the workflow type you need doesn't exist, call `add_workflow_type` with `type_name` and `description`.

### Set or update a workflow description

Call `set_workflow_description` with `workflow_rid` and `description`.

## MCP Tools: Full Execution Lifecycle

The MCP workflow mirrors the Python context manager but uses explicit tool calls for each step.

**Step 1: Create the execution.**

Call `create_execution` with:
- `workflow_name` (required): workflow name — creates the workflow if it doesn't exist
- `workflow_type` (required): workflow type vocabulary term
- `description` (optional): what this specific execution does
- `dataset_rids` (optional): list of input dataset RIDs
- `asset_rids` (optional): list of input asset RIDs
- `dry_run` (optional, default `false`): skip catalog writes for testing

Returns the execution RID. This execution becomes the **active execution** — subsequent lifecycle tools operate on it automatically.

**Step 2: Start the execution.**

Call `start_execution`. No parameters — operates on the active execution. Sets status to "Running" and records the start time.

**Step 3: Download input data.**

Call Python API `exe.download_dataset_bag()` with `dataset_rid` and `version` to download a dataset as a BDBag. See [Downloading Input Data](#downloading-input-data) for full parameter details.

Call Python API `ml.download_asset(rid)` with `asset_rid` to download individual input assets.

**Step 4: Do your work.**

Run notebooks, scripts, or interactive analysis. Use Python API `exe.working_dir` to find the local working directory.

**Step 5: Register output files.**

Call Python API `exe.asset_file_path()` to register each output file for upload. See [Registering and Uploading Outputs](#registering-and-uploading-outputs) for full parameter details.

**Step 6: Stop the execution.**

Call `stop_execution`. Sets status to "Completed" and records the stop time.

**Step 7: Upload outputs.**

Call Python API `exe.upload_execution_outputs()` to upload all registered files to the catalog. Optionally set `clean_folder` to `false` to keep local staging files.

**Important:** Steps 2-7 operate on the **active execution** — they take no `execution_rid` parameter. Only one execution can be active at a time.

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
- The `with` block automatically calls `start_execution()` on entry and `stop_execution()` on exit.
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

**Note:** The target asset table must already exist in the catalog before you can register files for upload to it. The built-in `Execution_Asset` table is always available. If you need a new domain-specific asset table (e.g., `"Image"`, `"Model"`), use the `work-with-assets` skill to create it first with `create_asset_table`.

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

In MCP tools, call `add_feature_value` or `add_feature_value_record` during the execution. In Python, call `execution.add_features(records)`. Both write JSONL files to the execution's `feature/` directory on disk. The catalog is updated when `upload_execution_outputs()` processes these files.

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

Read `deriva://execution/{execution_rid}` to get an execution's workflow, status, description, timing, and linked datasets/assets.

Read `deriva://experiment/{execution_rid}` for a richer view that includes Hydra configuration choices, model parameters, and input/output summaries.

Read `deriva://execution/{execution_rid}/inputs` to see just the input datasets and assets.

### Get active execution info

Call resource `deriva://execution/{rid}` — operates on the active execution (no parameters). Returns workflow, status, datasets, assets, nested executions, and timestamps.

### Find executions for a dataset or asset

Call resource `deriva://dataset/{rid}` with `dataset_rid` to find all executions that used a dataset.

Call `list_asset_executions` with `asset_rid` to find executions that created or used an asset. Optionally filter with `asset_role`: `"Output"` or `"Input"`.

## Updating Execution State

### Update status with a message

Call `update_execution_status` with `status` and `message`. Valid statuses: `"Pending"`, `"Running"`, `"Completed"`, `"Failed"`. Useful for tracking progress during long-running work (e.g., `"Running"`, `"Processing batch 3 of 10"`).

### Set or update the description

Call `set_execution_description` with `execution_rid` and `description`. The description supports Markdown.

## Nested Executions

### Link a child to a parent

Call `add_nested_execution` with:
- `parent_execution_rid` (required): RID of the parent execution
- `child_execution_rid` (required): RID of the child execution
- `sequence` (optional): integer for ordering children

### Navigate the hierarchy

Call `list_nested_executions` with `execution_rid` to get children. Set `recurse` to `true` for the full tree.

Call resource `deriva://execution/{rid}` with `execution_rid` to get parents. Set `recurse` to `true` to walk up the full chain.

## Restoring a Previous Execution

Call `restore_execution` with `execution_rid` to re-download a previous execution's datasets and assets. The restored execution becomes the active execution.

Use this for:
- **Debugging** — inspect the data a failed execution was working with
- **Continuing work** — resume from where a previous execution left off
- **Re-analysis** — run new analysis on the same inputs

## Creating an Output Dataset

Call `create_execution_dataset` to create a new dataset linked to the active execution as an output:
- `description` (optional): dataset description
- `dataset_types` (optional): list of dataset type terms

This is useful when an execution's output is a curated set of records (not just files).

## Complete Example: MCP + Python API Workflow

End-to-end workflow combining MCP tools (for lifecycle management) with Python API (for I/O operations).

**Step 1:** Read `deriva://catalog/workflows` to check for existing workflows.

**Step 2:** Call `create_execution` with `workflow_name`: `"Image Classification"`, `workflow_type`: `"Training"`, `description`: `"Train CNN on labeled CIFAR-10 subset"`, `dataset_rids`: `["2-ABC1"]`.

**Step 3:** Call `start_execution`.

**Step 4:** Call Python API `exe.download_dataset_bag()` with `dataset_rid`: `"2-ABC1"`, `version`: `"1.0.0"`.

**Step 5:** Call Python API `exe.working_dir` to find the local data path. Run your training script.

**Step 6:** Call Python API `exe.asset_file_path()` with `asset_name`: `"Execution_Asset"`, `file_name`: `"model_weights.pt"`, `asset_types`: `["Model_Weights"]`. Write the weights to the returned path.

**Step 7:** Call Python API `exe.asset_file_path()` with `asset_name`: `"Execution_Asset"`, `file_name`: `"predictions.csv"`, `asset_types`: `["Predictions"]`. Write the predictions to the returned path.

**Step 8:** Call `stop_execution`.

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
