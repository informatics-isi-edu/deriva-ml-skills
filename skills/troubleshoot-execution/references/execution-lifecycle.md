# Execution Lifecycle Reference

> The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them. Lifecycle tools also take an explicit `execution_rid` — there is no implicit "active execution".

## Table of Contents

- [Execution Architecture](#execution-architecture)
- [Workflows and Workflow Types](#workflows-and-workflow-types)
- [Execution Configuration](#execution-configuration)
- [The Execution Context Manager](#the-execution-context-manager)
- [Registering Output Files](#registering-output-files)
- [Uploading Outputs](#uploading-outputs)
- [Tuning Uploads for Large Files](#tuning-uploads-for-large-files)
- [Status Updates](#status-updates)
- [Automatic Source Code Detection](#automatic-source-code-detection)
- [Recovering from a Failed Execution](#recovering-from-a-failed-execution)
- [Nested Executions](#nested-executions)
- [Creating Output Datasets](#creating-output-datasets)
- [Dry Run Debugging](#dry-run-debugging)

---

## Execution Architecture

An execution represents a single run of a computational workflow with full provenance tracking. The hierarchy is:

```
Workflow_Type (vocabulary term — e.g., "Training", "Inference")
  └── Workflow (reusable definition — source code URL, checksum, version)
        └── Execution (one specific run — inputs, outputs, timing, status)
        └── Execution (another run, same code)
        └── ...
```

Every execution records:
- **Inputs**: Which datasets and assets were used
- **Outputs**: Which files and datasets were produced
- **Timing**: When the workflow started and stopped
- **Status**: Progress updates and completion state
- **Provenance**: Source code URL and Git checksum of the workflow

## Workflows and Workflow Types

### Creating a workflow

```python
workflow = ml.create_workflow(
    name="ResNet50 Training",
    workflow_type="Training",
    description="Fine-tune ResNet50 on medical images"
)
```

The `workflow_type` must exist in the `Workflow_Type` vocabulary before creating a workflow. Common types:

| Type | Description |
|------|-------------|
| Training | Model training workflows |
| Inference | Running predictions on new data |
| Preprocessing | Data cleaning and transformation |
| Evaluation | Model evaluation and metrics |
| Annotation | Adding labels or features |

Add custom types via the generic `add_term` tool:
```python
ml.add_term(table="Workflow_Type", term_name="Data_Augmentation",
            description="Workflows that augment training data")
```

```
add_term(hostname="data.example.org", catalog_id="1",
    schema="deriva-ml", table="Workflow_Type",
    name="Data_Augmentation",
    description="Workflows that augment training data")
```

### MCP tool

```
deriva_ml_create_workflow(hostname="data.example.org", catalog_id="1",
    name="ResNet50 Training",
    workflow_type="Training",
    description="Fine-tune ResNet50 on medical images")
```

### Workflow deduplication

If a workflow with the same source URL or Git checksum already exists in the catalog, the existing record is reused. Running the same committed script multiple times reuses the same workflow.

### Looking up workflows

```
deriva_ml_find_workflow_by_url(hostname="data.example.org", catalog_id="1",
    url="https://github.com/org/repo/blob/abc123/train.py")
```

```python
workflow = ml.lookup_workflow("2-ABC1")
workflow = ml.lookup_workflow_by_url("https://github.com/...")
all_workflows = ml.find_workflows()
```

## Execution Configuration

### Bundled script template

Copy `skills/execution-lifecycle/scripts/basic_execution.py` into your project, then customize the workflow + work block. The template handles workflow lookup-or-create and opens the execution context manager:

```python
workflow = ml.create_workflow(
    name="ResNet50 Training",
    workflow_type=args.workflow_type,
    description="Train ResNet50 with augmented data",
)
config = ExecutionConfiguration(description="ResNet50 training run")
with ml.create_execution(config, workflow=workflow,
                         dry_run=args.dry_run) as execution:
    # ... training code ...
```

### Python API (under the hood)

```python
from deriva_ml.execution import ExecutionConfiguration
from deriva_ml.dataset.aux_classes import DatasetSpec

config = ExecutionConfiguration(
    workflow=workflow,
    description="Training run with augmented data",
    datasets=[
        DatasetSpec(rid="1-ABC", version="1.2.0"),
        DatasetSpec(rid="1-DEF", materialize=False),
    ],
    assets=["2-GHI", "2-JKL"],  # Additional input asset RIDs
)
```

### DatasetSpec options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rid` | str | required | Dataset RID |
| `version` | str | None | Specific version (None = current) |
| `materialize` | bool | True | Download asset files (False = metadata only) |
| `timeout` | tuple | (10, 610) | (connect_timeout, read_timeout) in seconds |
| `exclude_tables` | list | None | Tables to prune from FK traversal |

## The Execution Context Manager

```python
with ml.create_execution(config) as exe:
    print(f"Execution RID: {exe.execution_rid}")
    print(f"Working directory: {exe.working_dir}")

    # Your ML workflow here...

# Commit AFTER context exits
exe.commit_output_assets()
```

What the context manager does:
- **On entry**: Records start time, sets status to "Running"
- **On exit (success)**: Records stop time, calculates duration
- **On exit (exception)**: Sets status to "Failed", records error

### Why commit is separate

`commit_output_assets()` is called **outside** the context manager because:
1. Upload can be done asynchronously for large files
2. You can inspect outputs before committing
3. Partial uploads can be re-driven by simply re-calling — the bag-commit pipeline is idempotent under `match_by_columns` dedup, so already-uploaded rows are a no-op and failed entries get re-attempted
4. Even failed executions should upload partial results

If the caller bypasses the `with` block and calls `commit_output_assets()` on a still-`Running` execution, the method auto-stops the execution first. The end state is the same: `Uploaded` (or `Failed` on error).

## Registering Output Files

Use `asset_file_path()` to register files for upload:

### Python API (the primary surface for this operation)

This is a Python-API-only operation; it has no direct MCP tool equivalent. Use it inside the execution context manager:

```python
with ml.create_execution(config) as exe:
    output_path = exe.asset_file_path(
        asset_name="Execution_Asset",
        file_name="model_weights.pt",
        asset_types=["Model_Weights"],
    )
    # write your file to output_path
```

Returns a `file_path` — write your output file to this path.

### Python API methods

```python
with ml.create_execution(config) as exe:
    # Method 1: Get a path for a new file
    output_path = exe.asset_file_path("Model", "model.pt")
    torch.save(model, output_path)

    # Method 2: Stage an existing file (symlink by default)
    exe.asset_file_path("Image", "/path/to/existing.png")

    # Method 3: Stage with copy (not symlink)
    exe.asset_file_path("Image", "/path/to/file.png", copy_file=True)

    # Method 4: Rename during staging
    exe.asset_file_path("Image", "/path/to/temp.png", rename_file="final.png")

    # Method 5: Apply asset types
    exe.asset_file_path("Image", "mask.png", asset_types=["Segmentation_Mask", "Derived"])
```

### Common mistake: wrong file path

Files **must** be written to the exact path returned by `asset_file_path()`. Writing to any other directory causes uploads to miss those files.

## Uploading Outputs

### Python API (the only surface for this operation)

This is a Python-API-only operation. Call it after the `with` block exits:

```python
# Default: 50 MB chunks, 10 min timeout, 3 retries
exe.commit_output_assets()
```

### What commit does

1. Finds all files registered via `asset_file_path()`
2. Uploads each file to the object store
3. Creates catalog records in the target asset tables (writing the descriptions you supplied at `asset_file_path()` time and `Upload_Duration` on every row — earlier versions silently skipped these on the post-CLI path)
4. Assigns asset types
5. Links each asset to the execution with role "Output"
6. Transitions the execution `Stopped → Pending_Upload → Uploaded` (or `→ Failed` on error)
7. Cleans up the local staging directory (`clean_folder=True` by default)
8. Returns an `UploadReport` (`total_uploaded`, `total_failed`, `per_table`, `errors`) — for per-asset paths, read `exe.uploaded_assets` after the call

The call is idempotent — re-running after a partial failure picks up the failed rows and leaves the already-uploaded ones alone.

## Tuning Uploads for Large Files

When uploading large files (> 1 GB), default timeouts may be insufficient.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `timeout` | `(600, 600)` | `(connect_timeout, read_timeout)` in seconds per chunk |
| `chunk_size` | 50 MB | Chunk size in bytes for object store uploads |
| `max_retries` | 3 | Maximum retry attempts for failed uploads |
| `retry_delay` | 5.0 | Initial delay between retries (doubles each attempt) |

### Examples

```python
# Large files on slow connection (30 min per chunk)
exe.commit_output_assets(timeout=(1800, 1800))

# Smaller chunks if timeouts persist (25 MB)
exe.commit_output_assets(chunk_size=25 * 1024 * 1024)

# More retries with longer delay
exe.commit_output_assets(max_retries=5, retry_delay=10.0)

# Combined: large files on slow connection
exe.commit_output_assets(
    timeout=(1800, 1800),
    chunk_size=25 * 1024 * 1024,
    max_retries=5,
    retry_delay=10.0,
)
```

### Timeout note

The `timeout` tuple is `(connect_timeout, read_timeout)`. urllib3 uses `connect_timeout` when **writing** the request body (uploading chunk data). Both values should be large enough for a full chunk to transfer over your network.

### When uploads fail

1. Check network connectivity
2. Increase timeout — transient network issues are the most common cause
3. Reduce chunk size — smaller chunks are more resilient to interruptions
4. Increase retries — retries use exponential backoff
5. Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to see if partial uploads succeeded

## Status Updates and Progress Reporting

Execution status transitions are driven by the context manager (`Running` on entry, `Stopped`/`Failed` on exit) and by `exe.commit_output_assets()` (the `Stopped → Pending_Upload → Uploaded` phase). Free-form progress messages do not live on the Execution row.

For mid-run progress reporting (e.g., "epoch 15 of 100"), write JSON-lines to a metrics file via the dedicated `exe.metrics_file()` API:

```python
import json
from deriva_ml.execution.state_store import ExecutionStatus

with ml.create_execution(config, workflow=workflow) as exe:
    data = load_data()

    with exe.metrics_file().open("a") as f:
        for epoch in range(100):
            train_epoch(model, data)
            # Append one JSON record per evaluation point
            f.write(json.dumps({"epoch": epoch, "val_loss": 0.42}) + "\n")

    # Failure marking from inside the with block (only when you need to override
    # the auto-Stopped transition — usually you let the context manager handle it):
    # exe.update_status(ExecutionStatus.Failed, error="Out of memory mid-epoch")

# After the with block:
exe.commit_output_assets()
```

The metrics file is uploaded as an `Execution_Metadata` asset (type `Metrics_File`) when `commit_output_assets()` runs. Readback from the downloaded bag is a simple JSONL parse.

## Automatic Source Code Detection

When a `Workflow` is created, DerivaML automatically detects the source code for provenance:

### Python scripts

Records the script's GitHub blob URL (including commit hash) and Git object hash:
```
URL:      https://github.com/org/repo/blob/a1b2c3d/src/models/train.py
Checksum: e5f6a7b8c9d0...
Version:  0.3.1
```

**Warning:** If the script has uncommitted changes, the URL points to the last committed version. The checksum may not match the code that actually ran. Always commit before running.

### Jupyter notebooks

Identifies the notebook via the Jupyter server, computes checksum after stripping cell outputs with `nbstripout`. Re-running without code changes produces the same checksum regardless of output differences.

### Docker containers

When `DERIVA_MCP_IN_DOCKER=true`, reads provenance from environment variables:
- `DERIVA_MCP_IMAGE_NAME` — Docker image name
- `DERIVA_MCP_IMAGE_DIGEST` — Image digest (used as checksum)
- `DERIVA_MCP_GIT_COMMIT` — Git commit hash at build time
- `DERIVA_MCP_VERSION` — Semantic version

### Manual override

```python
workflow = Workflow(
    name="Custom Pipeline",
    workflow_type="Training",
    url="https://github.com/org/repo/blob/main/pipeline.py",
    checksum="abc123def456",
)
```

Or via environment variables:
```bash
export DERIVA_ML_WORKFLOW_URL="https://github.com/org/repo/blob/main/pipeline.py"
export DERIVA_ML_WORKFLOW_CHECKSUM="abc123def456"
```

## Recovering from a Failed Execution

For the full recovery decision tree (salvage vs recovery-from-inputs vs claim-survivors-as-inputs), see the **"Salvage a Failed Execution"** section in this skill's `SKILL.md`. Quick orientation:

- An execution in `Stopped` or `Pending_Upload` is salvageable — run `skills/execution-lifecycle/scripts/salvage_execution.py` to drain the staged work. Idempotent under `match_by_columns` dedup, so re-call to resume on partial failure.
- An execution in `Failed` (terminal) cannot be salvaged from the same RID — the rows that already uploaded are preserved in the catalog, but anything still staged at the moment of failure is lost. Start a new execution by re-running the committed script (Branch B in SKILL.md).
- An execution in `Aborted` keeps its staged work for inspection — `ml.resume_execution(rid)` followed by `commit_output_assets()` will commit it, or you can leave it as a permanent provenance row.
- A "recovery execution" is a new execution that consumes the failed run's inputs (Branch B) or its surviving outputs (Branch C); set `ExecutionConfiguration(assets=[...])` in the recovery script to claim existing asset RIDs as inputs.

The one piece that does NOT live in this guide: the failed execution's row stays in the catalog as a permanent provenance record, but the catalog does not auto-link it to its recovery successor. That linkage is your responsibility — capture both RIDs in `experiment-decisions.md` (the `capture-tacit-knowledge` skill auto-fires when you do this).

## Nested Executions

Executions can be nested for complex workflows. Author parent-child runs via the bundled `skills/execution-lifecycle/scripts/nested_execution.py` template; the template calls `parent_exe.add_nested_execution(child_exe, sequence=i)` after each child's `with` block exits.

Two directional MCP tools navigate the hierarchy post-run:

```
# Walk down (descendants)
deriva_ml_list_execution_children(hostname="data.example.org", catalog_id="1",
    execution_rid="1-AAA")

# Walk up (ancestors)
deriva_ml_list_execution_parents(hostname="data.example.org", catalog_id="1",
    execution_rid="1-BBB")
```

### Inspecting execution trees

Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to see full execution details, then use the directional list tools above to walk the tree.

## Creating Output Datasets

If your workflow produces a curated dataset:

```python
with ml.create_execution(config) as exe:
    processed_rids = process_data(input_data)

    output_dataset = exe.create_dataset(
        description="Augmented training images",
        dataset_types=["Training", "Augmented"]
    )
    output_dataset.add_dataset_members(processed_rids)

exe.commit_output_assets()
```

The dataset row is created with the execution as its producer for provenance; `exe.commit_output_assets()` afterward writes the new dataset's bag and any staged feature values.

## Dry Run Debugging

To debug execution configuration without modifying the catalog:

### Preview bag contents

```
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1",
    dataset_rid="2-XXXX", version="1.0.0")
```

Shows row counts and asset sizes per table. Use to verify the execution would download the expected data.

### Preview split

Splits run from a script using the Python API. Pass `dry_run=True` to preview partition sizes without creating datasets:

```python
from deriva_ml.dataset.split import split_dataset

# Inside a script that has already opened ``exe``:
result = split_dataset(
    ml, "2-XXXX", exe,
    test_size=0.2, dry_run=True,
)
print(result.training.count, result.testing.count)
```

The `dataset-lifecycle` skill carries the full splitting recipe.

### Inspect working directory

Use the Python API: `exe.working_dir` returns the local filesystem path for the execution. Inspect to verify input files were downloaded and output files are staged correctly. (This is a Python-only operation; there's no MCP tool for it because the new server is stateless.)

## Reference Resources

| Resource / Tool | Purpose |
|-----------------|---------|
| `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` | Execution details, status, inputs, outputs, metadata |
| `deriva://catalog/{h}/{c}/ml/execution/{rid}` | Resource form of the same content |
| `deriva://storage/execution-dirs` | Local execution working directories |
| Python API `exe.working_dir` | Local filesystem path for the execution |
| `skills/execution-lifecycle/scripts/salvage_execution.py` | Drive `commit_output_assets()` on a `Stopped`/`Failed` execution. Idempotent under `match_by_columns` dedup. The canonical salvage entry point. |
| `skills/execution-lifecycle/scripts/crash_recovery.py` | `Running → Pending_Upload` direct transition after a hard crash; `--abort` mode to discard. |
| Python API `exe.abort()` | Transition to `Aborted`. Staged rows are preserved for inspection; the execution row stays in the catalog as a permanent provenance record. |
| `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)` | Walk down a nested-execution tree |
| `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)` | Walk up a nested-execution tree |
| Python API `exe.pending_summary()` | Per-table breakdown of staged / failed / uploaded counts for a resumed execution. The authoritative diagnostic for "what survived the crash". No MCP wrapper yet — Python-only |
| Python API `exe.commit_output_assets()` | Commit registered files to catalog — uploads bytes, writes asset rows (descriptions + `Upload_Duration`), transitions `Stopped → Pending_Upload → Uploaded`. Returns `UploadReport`; per-asset paths on `exe.uploaded_assets`. Idempotent on re-call |
