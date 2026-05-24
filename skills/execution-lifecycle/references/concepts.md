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

---

## Executions in the Catalog

An execution is a catalog record that captures a unit of work — a model training run, a data analysis, a notebook evaluation, a feature annotation pass. Executions are the fundamental unit of provenance in DerivaML. They are persistent, queryable entities stored in the catalog alongside your data.

Every execution record answers: "What work was done? With what inputs? What was produced? What code and configuration were used?"

Executions are represented in the `Execution` table in the `deriva-ml` schema. Like all catalog records, each execution has a unique **RID** that permanently identifies it.

## Execution RIDs

Every execution has a unique RID (Resource IDentifier) — a short, immutable string like `2-YYYY` or `3-AB4C`. This RID is the primary way to reference an execution:

- **In MCP tools**: Pass `execution_rid` to `deriva_ml_get_execution`, `deriva_ml_list_execution_children`, `deriva_ml_list_execution_parents`, `deriva_ml_update_execution`, etc.
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
| `Pending` → `Running` | `deriva_ml_start_execution(...)` is called (automatic in the context manager); records the start timestamp |
| `Running` → `Completed` | `deriva_ml_commit_execution(...)` is called (automatic on context manager exit); records the stop timestamp |
| `Running` → `Failed` | An unhandled exception occurs inside the context manager; the error is recorded |
| Any → `Aborted` | `deriva_ml_abort_execution(hostname, catalog_id, execution_rid, reason="...")`. The state machine forbids manual `Status` edits via `update_execution`; abort is the only entry to the Aborted state. |

The execution context manager automatically transitions through `Created` → `Initializing` → `Pending` → `Running` → `Completed` (or `Failed` on exception). You have three patterns for status changes from MCP tools:

- `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)` — normal success completion
- `deriva_ml_abort_execution(hostname, catalog_id, execution_rid)` — failure marking
- `deriva_ml_update_execution(hostname, catalog_id, execution_rid, description="<text>")` — update the execution's description after the fact (description-only; status edits are not allowed)
- For mid-run progress (e.g. "epoch 12 of 20"), write JSON-lines to a metrics file via the Python API's `exe.metrics_file().open("a")`. The catalog does not store free-form progress messages on the Execution row.

**MCP tools vs Python API:** Both MCP tools and the Python API use the same underlying `Execution` class, so the status transitions work identically. The difference is only in how the lifecycle is driven:

- **Python API (context manager):** The `with ml.create_execution(config) as exe:` block automatically transitions through all states — `Created` → `Initializing` → `Pending` → `Running` → `Completed` (or `Failed` on exception).
- **MCP tools (explicit calls):** You call `deriva_ml_create_execution` (sets `Created`), `deriva_ml_start_execution` (sets `Running`), and `deriva_ml_commit_execution` / `deriva_ml_abort_execution` (sets `Completed` / `Failed`) individually. The `Initializing` and `Pending` transitions still occur — they happen internally when input datasets and assets are downloaded via the Python API (e.g., `exe.download_dataset_bag()`).

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
- Call `deriva_ml_list_workflows(hostname, catalog_id)` to list all workflows.
- Call `deriva_ml_find_workflow_by_url(hostname, catalog_id, url)` with the repository URL to find a workflow by its source.

If no suitable workflow exists, create one:
- Call `deriva_ml_create_workflow(hostname, catalog_id, name=..., workflow_type=..., description=...)`.
- If the workflow type doesn't exist yet, add it with `add_term(hostname, catalog_id, schema="deriva-ml", table="Workflow_Type", name=..., description=...)` first.

When using MCP tools, `deriva_ml_create_execution` can find or create the workflow for you — pass `workflow_name` and `workflow_type` and it handles the lookup/creation automatically.

## Automatic Source Code Detection

DerivaML automatically records the source code that produced each execution by detecting the workflow's origin and creating or reusing a workflow record with a source URL.

### How source detection works

| Workflow Source | How DerivaML Finds the URL | Example URL |
|----------------|---------------------------|-------------|
| **Python scripts** (`deriva-ml-run`) | Inspects the git repository — constructs a GitHub blob URL using the remote origin, current commit hash, and script file path | `https://github.com/org/repo/blob/abc1234/src/models/train.py` |
| **Notebooks** (`deriva-ml-run-notebook`) | Reads the `DERIVA_ML_WORKFLOW_URL` environment variable, which must be set before running the notebook | Value of `$DERIVA_ML_WORKFLOW_URL` |
| **MCP tools** (`deriva_ml_create_execution`) | You provide `workflow_name` and `workflow_type`; the URL is not auto-detected | Set manually via `deriva_ml_update_workflow(...)` or `deriva_ml_create_workflow(...)` |

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

Use `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)` to walk down the tree and `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)` to walk up. The legacy `list_nested_executions` tool was split into these two directional tools.

### How multiruns create nested executions

The `deriva-ml-run` CLI automatically creates nested executions when using `multirun_config` or `--multirun`:

```bash
uv run deriva-ml-run +multirun=lr_sweep
```

This creates:
1. A **parent execution** for the sweep — its description comes from `multirun_config`'s `description` field
2. One **child execution** per parameter combination — each with its own config, inputs, outputs, and status

The parent's RID is the single reference point for the entire sweep. All children are accessible via `deriva_ml_list_execution_children`.

### Manual nesting with MCP tools

For custom multi-step workflows, create nested executions manually:

```
# Create the parent
# workflow_rid is the RID of a pre-registered Workflow record
deriva_ml_create_execution(hostname="data.example.org", catalog_id="1",
    workflow_rid="<workflow_rid>")
deriva_ml_start_execution(hostname="data.example.org", catalog_id="1",
    execution_rid="1-PARENT")
# ... parent-level work (e.g., shared preprocessing) ...
deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1",
    execution_rid="1-PARENT")

# Record the parent RID, then create children
# Each child is its own execution with its own inputs/outputs
deriva_ml_create_execution(hostname="data.example.org", catalog_id="1",
    workflow_rid="<workflow_rid>", ...)
deriva_ml_start_execution(hostname="data.example.org", catalog_id="1",
    execution_rid="1-CHILD1")
# ... child work ...
deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1",
    execution_rid="1-CHILD1")
# Then commit outputs via the Python API: exe.commit_output_assets()

# Link child to parent
deriva_ml_add_nested_execution(hostname="data.example.org", catalog_id="1",
    parent_rid="1-PARENT", child_rid="1-CHILD1", sequence=0)
```

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

If the caller bypasses the `with` block and calls `commit_output_assets()` on a still-`Running` execution, the method auto-stops the execution first; the end state is the same `Uploaded`. The call is idempotent — re-running after a partial failure picks up the failed rows and leaves the already-uploaded ones alone (no separate `retry_failed=` flag needed — that was the v1.38 surface, see [ADR-0009](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0009-unified-commit-output-assets.md)).

Until Python API `exe.commit_output_assets()` is called, output files exist only locally. This is a deliberate design — it allows the execution to complete (or fail) without partial uploads.

### Recording feature values

An execution can also produce **feature values** — structured annotations on catalog records (e.g., per-image classification labels, confidence scores). Like output files, feature values are **staged locally** and uploaded when Python API `exe.commit_output_assets()` is called:

- In MCP tools, call `deriva_ml_add_feature_values(hostname, catalog_id, table, feature_name, execution_rid="<execution_rid>", entries=[...])` during the execution.
- In Python, call `execution.add_features(records)`. This writes JSONL files to disk in the execution's `feature/` directory — the catalog is not updated until `commit_output_assets()` runs.

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

In MCP tools, the lifecycle is managed through explicit tool calls (`deriva_ml_create_execution`, `deriva_ml_start_execution`, `deriva_ml_commit_execution` for success, `deriva_ml_abort_execution` for failure, `deriva_ml_update_execution` for arbitrary status changes) that take an explicit `execution_rid` parameter (the new server is stateless — there is no implicit "active execution").

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

When using MCP tools, `deriva_ml_create_execution(hostname, catalog_id, ...)` accepts `workflow_name`, `workflow_type`, and `description` directly — it finds or creates the workflow automatically.

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
- The `with` block automatically transitions the execution to `Running` on entry (equivalent to the MCP `deriva_ml_start_execution` tool) and to `Completed` (or `Failed`/`Aborted` on exception) on exit (equivalent to MCP `deriva_ml_commit_execution` / `deriva_ml_abort_execution`).
- If an exception occurs, status is set to "Failed" automatically
- Call `commit_output_assets()` **after** exiting the `with` block, not inside it (or omit it entirely and let the context manager's auto-stop drive the commit on exit; if you bypass `with`, the method auto-stops a still-`Running` execution before draining)
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

In MCP tools, pass `dry_run`: `true` to `deriva_ml_create_execution`. In Python, pass `dry_run=True` to the runner or set it in the Hydra config.

Use dry runs to:
- Test data loading and model initialization before committing to a full run
- Debug configuration issues without cluttering the catalog with failed executions
- Verify the pipeline end-to-end on a new machine or environment

## Re-Running an Aborted Execution

> **Known gap:** the legacy `restore_execution` tool has **no equivalent** in the new MCP surface. The replacement pattern is to inspect the prior execution and create a fresh one with the same configuration.

When you need to re-run work after a failure or abort:

1. **Inspect the prior execution.** Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to retrieve the workflow RID, dataset RIDs, asset RIDs, and description from the original.
2. **Decide whether to retry.** If the failure was transient (network, timeout) re-running with the same config is the right move. If the failure was a code or config bug, fix it first.
3. **Create a fresh execution.** Call `deriva_ml_create_execution(hostname, catalog_id, ...)` with the same workflow, dataset_rids, and asset_rids you collected in step 1. This creates a new execution record (new RID) — the prior execution remains in its terminal state for provenance.
4. **Continue the lifecycle as normal.** Start it (`deriva_ml_start_execution`), do the work, and commit (`deriva_ml_commit_execution`).

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

All of these can be caught before `deriva_ml_start_execution(...)`.

### The pre-flight checklist

| Step | Tool | What it checks |
|------|------|---------------|
| Validate RIDs | `deriva_ml_get_dataset` / `get_entities` | All dataset and asset RIDs exist (legacy `validate_rids` was removed; check by typed lookup) |
| Check cache | `deriva_ml_bag_info` | Dataset sizes, cache status (`not_cached`, `cached_metadata_only`, `cached_materialized`, `cached_incomplete`); also doubles as a version-existence check |
| Cache data | `deriva_ml_cache_dataset` | Downloads bags/assets into cache without execution provenance |
| Git clean | `git status` | No uncommitted changes (for CLI runs) |
| Config check | `--info` | Resolved Hydra config is correct (for CLI runs) |

### Cache status values

The `deriva_ml_bag_info` tool returns a `cache_status` field:

| Status | Meaning | Action |
|--------|---------|--------|
| `not_cached` | No local copy | Call `deriva_ml_cache_dataset` if large |
| `cached_metadata_only` | Table data present, assets not fetched | Call `deriva_ml_cache_dataset(..., materialize=True)` |
| `cached_materialized` | Fully downloaded and validated | Ready to use — no action needed |
| `cached_incomplete` | Was cached but assets are missing | Call `deriva_ml_cache_dataset` to re-materialize |

### Prefetching strategy

For large datasets (>1 GB), cache ahead of time rather than downloading during the execution:

```python
# Check what we're dealing with (Python API)
info = ml.bag_info(DatasetSpec(rid="28CT", version="0.9.0"))
print(f"Size: {info['total_asset_size']}, Cache: {info['cache_status']}")

# Cache if not already cached
if info["cache_status"] == "not_cached":
    ml.cache_dataset(DatasetSpec(rid="28CT", version="0.9.0"))
```

The MCP tool `deriva_ml_cache_dataset(hostname, catalog_id, dataset_rid, version)` does the same thing without requiring Python.
