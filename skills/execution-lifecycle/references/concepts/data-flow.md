---
type: Concept
title: Execution data flow
description: How executions consume inputs and produce outputs — dataset/asset download, working directory, output registration, commit, feature values, and the end-to-end flow.
---

# Execution data flow

## Execution Data Flow

An execution consumes inputs, does work in a local working directory, and produces outputs that get uploaded back to the catalog. Understanding this flow is key to working with executions.

### Consuming inputs

An execution's inputs are **datasets** and **assets** specified when the execution is created. During execution, you download these to a local working directory:

- **Datasets** are downloaded as BDBags — self-contained, versioned archives that include all member records, asset files, feature values, and vocabulary terms at the exact catalog state when the version was created. Call Python API `exe.download_dataset_bag()` with a dataset RID and version. See the `dataset-lifecycle` skill for how datasets and versions work, and its `references/bags.md` for details on the BDBag format.
- **Individual assets** (e.g., pretrained model weights) are downloaded directly. Call Python API `exe.download_asset(rid)` with an asset RID. See the `work-with-assets` skill for asset concepts including caching.

Both operations automatically record provenance — the downloaded dataset or asset is linked to the execution with role "Input".

### The working directory

Each execution gets a local working directory where all downloaded inputs and staged outputs live. This directory is created automatically and persists until cleaned up. Access it via Python API `exe.working_dir` (MCP) or `execution.working_dir` (Python). See [Execution Working Directory](authoring.md) for the layout.

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
