# Execution Concepts

Background on executions, workflows, and provenance in DerivaML. For the step-by-step guide, see `workflow.md`.

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
- [Restoring Executions](#restoring-executions)

---

## Executions in the Catalog

An execution is a catalog record that captures a unit of work — a model training run, a data analysis, a notebook evaluation, a feature annotation pass. Executions are the fundamental unit of provenance in DerivaML. They are persistent, queryable entities stored in the catalog alongside your data.

Every execution record answers: "What work was done? With what inputs? What was produced? What code and configuration were used?"

Executions are represented in the `Execution` table in the `deriva-ml` schema. Like all catalog records, each execution has a unique **RID** that permanently identifies it.

## Execution RIDs

Every execution has a unique RID (Resource IDentifier) — a short, immutable string like `2-YYYY` or `3-AB4C`. This RID is the primary way to reference an execution:

- **In MCP tools**: Pass `execution_rid` to `restore_execution`, `list_nested_executions`, `set_execution_description`, etc.
- **In provenance queries**: Asset and dataset provenance records reference execution RIDs
- **In the web UI**: Each execution has a Chaise page at its RID-based URL
- **In citation**: `ml.cite(rid)` generates a permanent URL for an execution
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
- Read `deriva://execution/{execution_rid}` for full details
- Read `deriva://experiment/{execution_rid}` for a richer view with Hydra config and model parameters
- Read `deriva://execution/{execution_rid}/inputs` for just the input datasets and assets
- Call resource `deriva://dataset/{rid}` to find all executions that used a dataset
- Call `list_asset_executions` to find executions that created or used an asset

**The ExecutionRecord class** in the Python API is the lightweight read-only representation of an execution record. It's returned by lookup and query methods:

```python
record = ml.lookup_execution("2-YYYY")
print(record.execution_rid)   # "2-YYYY"
print(record.status)          # "Completed"
print(record.description)     # "Train CNN on batch 1"
print(record.workflow_rid)    # "1-WXYZ"
```

`ExecutionRecord` is also what you get back from provenance queries like `asset.list_executions()` and `ml.list_asset_executions()`.

## Execution Statuses

| Status | Meaning |
|--------|---------|
| `Created` | Record created in catalog, no work started |
| `Initializing` | Downloading input datasets and assets |
| `Pending` | Initialization complete, ready to run |
| `Running` | Model/workflow work in progress |
| `Completed` | Finished successfully |
| `Failed` | Encountered an error |
| `Aborted` | Manually stopped |

### Status State Machine

The execution lifecycle follows a defined state machine. Each transition occurs at a specific point:

```
Created → Initializing → Pending → Running → Completed
                                      ↓
                                    Failed
```

| Transition | When It Occurs |
|-----------|----------------|
| `Created` → `Initializing` | Context manager entered; begins downloading input datasets and assets specified in the configuration |
| `Initializing` → `Pending` | All input downloads complete; execution is ready to begin work |
| `Pending` → `Running` | `start_execution()` is called (automatic in the context manager); records the start timestamp |
| `Running` → `Completed` | `stop_execution()` is called (automatic on context manager exit); records the stop timestamp |
| `Running` → `Failed` | An unhandled exception occurs inside the context manager; the error is recorded |
| Any → `Aborted` | Manual intervention via `update_execution_status(status="Aborted", message="...")` |

The execution context manager automatically transitions through `Created` → `Initializing` → `Pending` → `Running` → `Completed` (or `Failed` on exception). You can also update status manually with `update_execution_status` for finer-grained progress tracking during long-running work.

**MCP tools vs Python API:** Both MCP tools and the Python API use the same underlying `Execution` class, so the status transitions work identically. The difference is only in how the lifecycle is driven:

- **Python API (context manager):** The `with ml.create_execution(config) as exe:` block automatically transitions through all states — `Created` → `Initializing` → `Pending` → `Running` → `Completed` (or `Failed` on exception).
- **MCP tools (explicit calls):** You call `create_execution` (sets `Created`), `start_execution` (sets `Running`), and `stop_execution` (sets `Completed`) individually. The `Initializing` and `Pending` transitions still occur — they happen internally when input datasets and assets are downloaded via the Python API (e.g., `exe.download_dataset_bag()`).

In both cases, the same `Execution` object manages the state machine. The context manager simply automates the start/stop calls and error handling that you would otherwise do manually with MCP tools.

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
- Read `deriva://catalog/workflows` to list all workflows
- Call `lookup_workflow_by_url` with the repository URL to find a workflow by its source

If no suitable workflow exists, create one:
- Call `create_workflow` with `name`, `workflow_type`, and optionally `description`
- If the workflow type doesn't exist yet, call `add_workflow_type` with `type_name` and `description` first

When using MCP tools, `create_execution` can find or create the workflow for you — pass `workflow_name` and `workflow_type` and it handles the lookup/creation automatically.

## Automatic Source Code Detection

DerivaML automatically records the source code that produced each execution by detecting the workflow's origin and creating or reusing a workflow record with a source URL.

### How source detection works

| Workflow Source | How DerivaML Finds the URL | Example URL |
|----------------|---------------------------|-------------|
| **Python scripts** (`deriva-ml-run`) | Inspects the git repository — constructs a GitHub blob URL using the remote origin, current commit hash, and script file path | `https://github.com/org/repo/blob/abc1234/src/models/train.py` |
| **Notebooks** (`deriva-ml-run-notebook`) | Reads the `DERIVA_ML_WORKFLOW_URL` environment variable, which must be set before running the notebook | Value of `$DERIVA_ML_WORKFLOW_URL` |
| **MCP tools** (`create_execution`) | You provide `workflow_name` and `workflow_type`; the URL is not auto-detected | Set manually via `set_workflow_description` or `create_workflow` |

For Python scripts, the URL includes the **exact commit hash** (not a branch name), ensuring the source reference is permanent and immutable. This means the URL always points to the specific code version that ran.

### Git commit enforcement

DerivaML enforces clean working trees by default. Both `deriva-ml-run` and `deriva-ml-run-notebook` check for uncommitted changes before creating an execution. If any are found, `DerivaMLDirtyWorkflowError` is raised and the run is aborted.

- **`--allow-dirty` flag** overrides the check for debugging iterations. The execution still records a git hash, but it may not match the code that actually ran — this is **degraded provenance**.
- Executions created with `--allow-dirty` should not be cited or used as production baselines.

### Workflow deduplication

DerivaML avoids creating duplicate workflow records. When a new execution is created:

1. The system computes the workflow's **source URL** (as described above)
2. It calls `lookup_workflow_by_url` to check if a workflow with that URL already exists
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

### How multiruns create nested executions

The `deriva-ml-run` CLI automatically creates nested executions when using `multirun_config` or `--multirun`:

```bash
uv run deriva-ml-run +multirun=lr_sweep
```

This creates:
1. A **parent execution** for the sweep — its description comes from `multirun_config`'s `description` field
2. One **child execution** per parameter combination — each with its own config, inputs, outputs, and status

The parent's RID is the single reference point for the entire sweep. All children are accessible via `list_nested_executions`.

### Manual nesting with MCP tools

For custom multi-step workflows, create nested executions manually:

```
# Create the parent
create_execution(workflow_name="Architecture Comparison", workflow_type="Analysis")
start_execution()
# ... parent-level work (e.g., shared preprocessing) ...
stop_execution()

# Record the parent RID, then create children
# Each child is its own execution with its own inputs/outputs
create_execution(workflow_name="ResNet Training", workflow_type="Training", ...)
start_execution()
# ... child work ...
stop_execution()
upload_execution_outputs()

# Link child to parent
add_nested_execution(parent_execution_rid="1-PARENT", child_execution_rid="1-CHILD1", sequence=0)
```

### Navigating nested execution hierarchies

**MCP tools:**

| Tool | Direction | Parameters |
|------|-----------|-----------|
| `list_nested_executions` | Parent → Children | `execution_rid`, `recurse=True` for all descendants |
| resource `deriva://execution/{rid}` | Child → Parent | `execution_rid`, `recurse=True` for all ancestors |

**MCP resources:**

| Resource | What it returns |
|----------|----------------|
| `deriva://execution/{rid}` | Execution details including status, workflow, timing |
| `deriva://experiment/{rid}` | Rich view with Hydra config, model params, inputs/outputs |
| `deriva://execution/{rid}/inputs` | Input datasets and assets |

**Python API:**

```python
# From parent to children
children = parent_execution.list_nested_executions(recurse=False)
all_descendants = parent_execution.list_nested_executions(recurse=True)

# From child to parent
parents = child_execution.list_parent_executions(recurse=False)

# Each child is an ExecutionRecord with .execution_rid, .status, .description
for child in children:
    print(f"{child.execution_rid}: {child.status} — {child.description}")
```

### Analyzing sweep results

After a multirun completes, the typical analysis flow is:

1. `list_nested_executions(execution_rid="PARENT_RID")` — get all children
2. For each child, read `deriva://experiment/{child_rid}` — get config parameters and results
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

After the execution's work is complete, call Python API `exe.upload_execution_outputs()` to upload all registered files to the catalog in one batch. This:

1. Uploads each staged file to the object store
2. Creates asset records in the appropriate asset tables
3. Links each asset to the execution with role "Output"
4. Optionally cleans up the local staging directory

Until Python API `exe.upload_execution_outputs()` is called, output files exist only locally. This is a deliberate design — it allows the execution to complete (or fail) without partial uploads.

### Recording feature values

An execution can also produce **feature values** — structured annotations on catalog records (e.g., per-image classification labels, confidence scores). Like output files, feature values are **staged locally** and uploaded when Python API `exe.upload_execution_outputs()` is called:

- In MCP tools, call `add_feature_value` or `add_feature_value_record` during the execution.
- In Python, call `execution.add_features(records)`. This writes JSONL files to disk in the execution's `feature/` directory — the catalog is not updated until `upload_execution_outputs()` runs.

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

In MCP tools, the lifecycle is managed through explicit tool calls (`create_execution`, `start_execution`, `stop_execution`, etc.) that operate on the active execution.

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

When using MCP tools, `create_execution` accepts `workflow_name`, `workflow_type`, and `description` directly — it finds or creates the workflow automatically.

## The Execution Context Manager

The recommended Python pattern uses a `with` block:

```python
with ml.create_execution(config) as exe:
    # On enter: creates execution record, sets status to Initializing → Running
    # Datasets specified in config are auto-downloaded
    for dataset in exe.datasets:
        dataset.restructure_assets(...)  # DatasetBag objects
    # ... do work ...
    path = exe.asset_file_path("Execution_Asset", "results.csv")
    # ... write to path ...
    # On exit: sets status to Completed (or Failed), outputs auto-uploaded
```

**Key points:**
- The `with` block automatically calls `start_execution()` on entry and `stop_execution()` on exit
- If an exception occurs, status is set to "Failed" automatically
- Call `upload_execution_outputs()` **after** exiting the `with` block, not inside it
- When using `deriva-ml-run`, upload is handled automatically by the runner

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

These metadata files are uploaded automatically during `upload_execution_outputs()`. You do not need to register them manually — they are created and staged by the execution lifecycle.

**Why this matters:** If a model produces unexpected results, the metadata lets you reconstruct the exact software environment (`uv.lock`), configuration (`Deriva_Config`, `Hydra_Config`), and runtime context (`Runtime_Env`) that produced them.

**Querying metadata:**
- Read `deriva://execution/{rid}/metadata` to see the auto-created metadata files for an execution
- Use `preview_table("Execution_Metadata", filters={"Execution": execution_rid})` to query metadata records directly

## Dry Run Mode

Dry run mode lets you test the full pipeline without writing to the catalog:

- No execution record is created (uses a placeholder RID of `"0"`)
- No catalog writes occur — no provenance, no status updates
- Datasets and assets **are** still downloaded — you can verify data loading works
- Configuration is still resolved — you can verify parameters are correct
- Output files can still be written locally — you can verify the model runs

In MCP tools, pass `dry_run`: `true` to `create_execution`. In Python, pass `dry_run=True` to the runner or set it in the Hydra config.

Use dry runs to:
- Test data loading and model initialization before committing to a full run
- Debug configuration issues without cluttering the catalog with failed executions
- Verify the pipeline end-to-end on a new machine or environment

## Restoring Executions

`restore_execution` re-downloads a previous execution's datasets and assets to a local working directory. This is useful for:

- **Debugging** — inspect what data a failed execution was working with
- **Continuing work** — resume from where a previous execution left off
- **Analysis** — run new analysis on the same inputs without re-configuring

The restored execution becomes the active execution, so subsequent MCP tool calls (Python API `exe.working_dir`, Python API `exe.asset_file_path()`, etc.) operate on it.

### Finding execution RIDs to restore

You need the execution's RID to restore it. Several ways to find it:

- **From the catalog**: Read `deriva://execution/{execution_rid}` if you know the RID, or query the `Execution` table via `preview_table` to search by workflow, status, or description.
- **From local storage**: Read the `deriva://storage/execution-dirs` resource to see execution working directories that still exist locally. Each entry includes the execution RID, a label, size, and modification time.
- **From provenance**: Call `list_asset_executions` with an asset RID to find which execution produced it, or resource `deriva://dataset/{rid}` with a dataset RID to find executions that used it.
- **From the web UI**: Browse executions in Chaise and copy the RID from the record page.

## Pre-Flight Validation

Before running an experiment, several checks prevent runtime failures and data issues.

### Why pre-flight matters

Experiments fail at runtime when:
- Dataset RIDs in the config don't exist or point to wrong versions
- Asset RIDs (model weights, etc.) are invalid
- Bags are too large to download during execution
- Network issues during materialization

All of these can be caught before `start_execution()`.

### The pre-flight checklist

| Step | Tool | What it checks |
|------|------|---------------|
| Validate RIDs | `validate_rids` | All dataset and asset RIDs exist, versions are valid, descriptions present |
| Check cache | `bag_info` | Dataset sizes, cache status (`not_cached`, `cached_metadata_only`, `cached_materialized`, `cached_incomplete`) |
| Cache data | `cache_dataset` | Downloads bags/assets into cache without execution provenance |
| Git clean | `git status` | No uncommitted changes (for CLI runs) |
| Config check | `--info` | Resolved Hydra config is correct (for CLI runs) |

### Cache status values

The `bag_info` tool returns a `cache_status` field:

| Status | Meaning | Action |
|--------|---------|--------|
| `not_cached` | No local copy | Call `cache_dataset` if large |
| `cached_metadata_only` | Table data present, assets not fetched | Call `cache_dataset(materialize=True)` |
| `cached_materialized` | Fully downloaded and validated | Ready to use — no action needed |
| `cached_incomplete` | Was cached but assets are missing | Call `cache_dataset` to re-materialize |

### Prefetching strategy

For large datasets (>1 GB), cache ahead of time rather than downloading during the execution:

```python
# Check what we're dealing with
info = ml.bag_info(DatasetSpec(rid="28CT", version="0.9.0"))
print(f"Size: {info['total_asset_size']}, Cache: {info['cache_status']}")

# Cache if not already cached
if info["cache_status"] == "not_cached":
    ml.cache_dataset(DatasetSpec(rid="28CT", version="0.9.0"))
```

The MCP tool `cache_dataset` does the same thing without requiring Python.
