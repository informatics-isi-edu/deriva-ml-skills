# Execution Lifecycle Reference

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
- [Restoring Executions](#restoring-executions)
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

Add custom types:
```python
ml.add_term(table="Workflow_Type", term_name="Data_Augmentation",
            description="Workflows that augment training data")
```

### MCP tool

```
create_workflow(
    workflow_name="ResNet50 Training",
    workflow_type="Training",
    description="Fine-tune ResNet50 on medical images"
)
```

### Workflow deduplication

If a workflow with the same source URL or Git checksum already exists in the catalog, the existing record is reused. Running the same committed script multiple times reuses the same workflow.

### Looking up workflows

```
lookup_workflow_by_url(url="https://github.com/org/repo/blob/abc123/train.py")
```

```python
workflow = ml.lookup_workflow("2-ABC1")
workflow = ml.lookup_workflow_by_url("https://github.com/...")
all_workflows = ml.find_workflows()
```

## Execution Configuration

### MCP tools

```
create_execution(
    workflow_name="ResNet50 Training",
    workflow_type="Training",
    description="Training run with augmented data"
)
start_execution()
```

### Python API

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

# Upload AFTER context exits
exe.upload_execution_outputs()
```

What the context manager does:
- **On entry**: Records start time, sets status to "Running"
- **On exit (success)**: Records stop time, calculates duration
- **On exit (exception)**: Sets status to "Failed", records error

### Why upload is separate

`upload_execution_outputs()` is called **outside** the context manager because:
1. Upload can be done asynchronously for large files
2. You can inspect outputs before uploading
3. Partial uploads can be retried if they fail
4. Even failed executions should upload partial results

## Registering Output Files

Use `asset_file_path()` to register files for upload:

### MCP tool

```
asset_file_path(
    asset_name="Execution_Asset",
    file_name="model_weights.pt",
    asset_types=["Model_Weights"]
)
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

### MCP tool

```
upload_execution_outputs()
```

### Python API

```python
# Default: 50 MB chunks, 10 min timeout, 3 retries
exe.upload_execution_outputs()
```

### What upload does

1. Finds all files registered via `asset_file_path()`
2. Uploads each file to the object store
3. Creates catalog records in the target asset tables
4. Assigns asset types
5. Links each asset to the execution with role "Output"
6. Cleans up the local staging directory (by default)

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
exe.upload_execution_outputs(timeout=(1800, 1800))

# Smaller chunks if timeouts persist (25 MB)
exe.upload_execution_outputs(chunk_size=25 * 1024 * 1024)

# More retries with longer delay
exe.upload_execution_outputs(max_retries=5, retry_delay=10.0)

# Combined: large files on slow connection
exe.upload_execution_outputs(
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
5. Check resource `deriva://execution/{rid}` to see if partial uploads succeeded

## Status Updates

Report progress during long-running workflows:

### MCP tool

```
update_execution_status(status="Running", description="Epoch 15/100 complete")
```

### Python API

```python
from deriva_ml.core.definitions import Status

with ml.create_execution(config) as exe:
    exe.update_status(Status.running, "Loading data...")
    data = load_data()

    for epoch in range(100):
        train_epoch(model, data)
        exe.update_status(Status.running, f"Epoch {epoch+1}/100 complete")
```

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

## Restoring Executions

Resume working with a previous execution:

### MCP tool

```
restore_execution(execution_rid="1-XYZ")
```

### Python API

```python
exe = ml.restore_execution("1-XYZ")
# Continue working — register more files, upload, etc.
exe.asset_file_path("Model", "continued_model.pt")
exe.upload_execution_outputs()
```

## Nested Executions

Executions can be nested for complex workflows:

### MCP tool

```
add_nested_execution(parent_rid="1-AAA", child_rid="1-BBB")
list_nested_executions(execution_rid="1-AAA")
list_parent_executions(execution_rid="1-BBB")
```

### Inspecting execution trees

Read `deriva://execution/{rid}` to see full execution details including nested children and parent relationships.

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

exe.upload_execution_outputs()
```

### MCP tool equivalent

```
create_execution_dataset(
    description="Augmented training images",
    dataset_types=["Training", "Augmented"]
)
add_dataset_members(dataset_rid="<new_rid>", members=["2-A1", "2-A2", ...])
```

## Dry Run Debugging

To debug execution configuration without modifying the catalog:

### Preview bag contents

```
estimate_bag_size(dataset_rid="2-XXXX", version="1.0.0")
```

Shows row counts and asset sizes per table. Use to verify the execution would download the expected data.

### Preview split

```
split_dataset(dataset_rid="2-XXXX", test_size=0.2, dry_run=true)
```

Shows partition sizes without creating datasets.

### Inspect working directory

```
get_execution_working_dir()
```

Returns the local filesystem path for the active execution. Inspect to verify input files were downloaded and output files are staged correctly.

## Reference Resources

| Resource / Tool | Purpose |
|-----------------|---------|
| `deriva://execution/{rid}` | Execution details, status, inputs, outputs |
| `deriva://storage/execution-dirs` | Local execution working directories |
| resource `deriva://execution/{rid}` | Full execution metadata and state |
| Python API `exe.working_dir` | Local filesystem path for active execution |
| `update_execution_status` | Report progress during long runs |
| `list_nested_executions` | View execution tree for complex workflows |
| resource `deriva://execution/{rid}` | Find parent of a nested execution |
| `restore_execution` | Resume a previous execution |
| Python API `exe.upload_execution_outputs()` | Upload registered files to catalog |
