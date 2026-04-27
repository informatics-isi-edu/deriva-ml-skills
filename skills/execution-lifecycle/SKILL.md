---
name: execution-lifecycle
description: "ALWAYS use this skill when running ML experiments, creating executions, managing workflow provenance, pre-flight validation, or configuring experiment runs in DerivaML. Covers the full execution lifecycle: pre-flight checks (validate RIDs, check cache, cache data), creating and running executions via MCP tools or Python API, managing inputs/outputs with provenance, uploading results, nested executions, dry runs, and the deriva-ml-run CLI. Triggers on: 'run experiment', 'create execution', 'execution lifecycle', 'upload outputs', 'pre-flight', 'dry run', 'validate before running', 'cache dataset', 'workflow provenance', 'deriva-ml-run', 'multirun', 'sweep', 'check git before running', 'nested execution', 'restore execution', 'track my work'."
disable-model-invocation: true
---

# Execution Lifecycle in DerivaML

An execution is the fundamental unit of provenance in DerivaML. It records what work was done, with what inputs (datasets, assets), what outputs were produced, and what code and configuration were used.

For background on the execution hierarchy, statuses, workflows, nested executions, dry run mode, and the working directory layout, see `references/concepts.md`.

## Prerequisite: Connect to a Catalog

All execution operations require an active catalog connection:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.

## Git Commit Enforcement

DerivaML enforces that all code is committed before running catalog-mutating operations. If uncommitted changes are detected, `deriva-ml-run` and `deriva-ml-run-notebook` raise `DerivaMLDirtyWorkflowError` and refuse to proceed.

- **`--allow-dirty`** overrides the check for debugging iterations, but the resulting execution has **degraded provenance** — the git hash in the execution record may not match the code that actually ran.
- This applies to all `deriva-ml-run` and `deriva-ml-run-notebook` invocations.
- Simple one-off MCP tool operations (adding a vocabulary term, updating a description) are not affected.

## Phase 1: Pre-Flight Validation

Before running an experiment, validate that everything is in place. **Stop and fix any issues.**

### Step 1: Resolve the configuration

Before validating anything, you need to know what the configuration specifies. Identify all dataset RIDs, asset RIDs, and versions that will be used:

**For CLI runs** — use standard Hydra arguments to dump the resolved config:
```bash
# deriva-ml-run's built-in config inspector
uv run deriva-ml-run +experiment=baseline --info

# Standard Hydra config dump (shows the full resolved YAML)
uv run deriva-ml-run +experiment=baseline --cfg job

# Show just a specific config group
uv run deriva-ml-run +experiment=baseline --cfg job --package datasets
uv run deriva-ml-run +experiment=baseline --cfg job --package assets
```
Extract the dataset RIDs and versions from the resolved `datasets` group, and asset RIDs from the `assets` group. The `--cfg job` output shows exactly what the execution will receive — including all defaults, overrides, and interpolations resolved.

**For MCP tool runs** — the user provides the RIDs directly in the `create_execution` call. Collect them before proceeding.

**For Python API runs** — read the `ExecutionConfiguration` or the hydra-zen config module to extract dataset and asset references.

### Step 2: Validate all RIDs and versions

```
validate_rids(
    dataset_rids=["28CT", "28D0"],
    asset_rids=["3WSE"],
    dataset_versions={"28CT": "0.9.0"}
)
```

This checks that all RIDs exist in the catalog, versions are valid, and warns about missing descriptions. Catches typos, deleted datasets, and wrong version numbers before runtime.

**Stop if any errors.** Fix the configuration before proceeding.

### Step 3: Check data readiness and decide whether to stage

For each dataset in the config, check cache status and size:

```
bag_info(dataset_rid="28CT", version="0.9.0")
```

Returns size info AND cache status:
- `not_cached` → will need to download (check `total_asset_size` to estimate time)
- `cached_metadata_only` → table data present, assets need materialization
- `cached_materialized` → ready to go, no download needed
- `cached_incomplete` → needs re-materialization

**Decision: should you stage data before running?**

| Situation | Action |
|-----------|--------|
| Small dataset (<100 MB), not cached | Let execution download it — fast enough |
| Large dataset (>1 GB), not cached | **Stage first** with `cache_dataset` |
| Any dataset, `cached_materialized` | No action needed — will use cache |
| Asset (model weights), not cached | **Stage first** with `cache_dataset(asset_rid=...)` |

### Step 4: Stage data if needed

For datasets:
```
cache_dataset(dataset_rid="28CT", version="0.9.0")
```

For individual assets (model weights, etc.):
```
cache_dataset(asset_rid="3WSE")
```

These download into the local cache without creating execution records. Subsequent dataset/asset downloads (via `exe.download_dataset_bag()` / `ml.download_asset()` in Python, or the CLI runner) will use the cached copy.

### Step 5: Code and environment checks (CLI runs)

For `deriva-ml-run` CLI experiments:

1. **Git clean** — `git status` must show no uncommitted changes. DerivaML enforces this: `DerivaMLDirtyWorkflowError` is raised if uncommitted changes exist. Use `--allow-dirty` only for debugging (degraded provenance).
2. **Version current** — bump with `bump_version("patch")` MCP tool or `uv run bump-version patch|minor` CLI if needed
3. **Lock file valid** — `uv lock --check` must pass

### Step 6: User confirmation

Present a summary before production runs:
- Commit hash, version, branch
- Experiment name and key parameters
- Dataset versions and cache status (all should be `cached_materialized` after staging)
- Get explicit approval

## Phase 2: Create and Run

There are three ways to run an execution. Choose based on context:

| Path | When to use | Lifecycle managed by |
|------|-------------|---------------------|
| **MCP Tools** | Claude-driven interactive work | Explicit tool calls (create → start → work → stop) + Python API for I/O |
| **Python API** | Scripts and custom workflows | Context manager (`with ml.create_execution(config) as exe:`) |
| **CLI** | Reproducible experiment runs | `deriva-ml-run` handles everything automatically |

**Key rule:** Always dry run first — `dry_run=True` (MCP/Python) or `dry_run=True` (CLI override).

The execution lifecycle is always the same regardless of path:
1. Create execution (with workflow, inputs, description)
2. Start → download inputs → do work → register outputs → stop
3. Upload outputs to catalog

**Important:** Downloading inputs, registering output files, and uploading outputs are done via the **Python API** (not MCP tools). Use `exe.download_dataset_bag()`, `exe.asset_file_path()`, and `exe.upload_execution_outputs()`.

**Automatic metadata:** Every execution automatically captures configuration (`Deriva_Config`, `Hydra_Config`), environment lock file (`Execution_Config`), and runtime environment (`Runtime_Env`) as `Execution_Metadata` records. See `references/concepts.md` for details.

**Notebook outputs:** When running notebooks via `deriva-ml-run-notebook`, the executed `.ipynb` and converted `.md` are automatically uploaded as execution assets alongside any files registered via `asset_file_path()`. See `references/workflow.md` for the notebook output flow.

For the complete tool call sequences, code examples, and CLI commands for each path, see `references/workflow.md`.

## Phase 3: Verify Results

After a run, check the execution:

```
Read resource: deriva://execution/{execution_rid}
Read resource: deriva://experiment/{execution_rid}
cite(rid="{execution_rid}", current=True)
```

Verify: status is "Completed", correct inputs linked, output assets attached, git hash matches.

## Critical Rules

1. **Validate before running** — `validate_rids` + `bag_info` catches config errors early
2. **Dry run first** — test with `dry_run=True` before production runs
3. **Every execution needs a workflow** — find with `lookup_workflow_by_url` or let `create_execution` create one
4. **Upload AFTER the with block** — `exe.upload_execution_outputs()` goes after `with`, not inside
5. **Use Python API `exe.asset_file_path()` for all outputs** — never manually place files in the working directory
6. **Commit code before running** — DerivaML raises `DerivaMLDirtyWorkflowError` if uncommitted changes exist. Use `--allow-dirty` only for debugging.

## Reference Resources

**Discovery (use RAG first):**
- `rag_search("training experiments", doc_type="catalog-data")` — find executions by workflow or status
- `rag_search("workflow types", doc_type="catalog-schema")` — discover available workflow types

**Structured resources (for complete output):**
- `references/concepts.md` — Execution hierarchy, statuses (state machine), workflows, source code detection, nested executions, metadata auto-generation, dry run, working directory, data flow
- `references/workflow.md` — Step-by-step MCP and Python API workflows, notebook output handling, complete examples
- `references/cli-reference.md` — deriva-ml-run CLI commands, Hydra overrides, multirun syntax
- `deriva://execution/{execution_rid}` — Execution details and status
- `deriva://catalog/executions` — Browse recent executions
- `deriva://catalog/experiments` — Browse experiments (executions with Hydra config)
- `deriva://experiment/{execution_rid}` — Rich view with Hydra config and parameters
- `deriva://execution/{execution_rid}/inputs` — Input datasets and assets
- `deriva://execution/{execution_rid}/outputs` — Output assets produced by the execution
- `deriva://execution/{execution_rid}/metadata` — Auto-created metadata files (config, environment, lock file)
- `deriva://catalog/workflows` — Available workflows
- `deriva://catalog/workflow-types` — Workflow type vocabulary terms

## Related Skills

- **`configure-experiment`** — Setting up Hydra-zen config groups and experiment presets
- **`write-hydra-config`** — Python API patterns for each config type
- **`run-notebook`** — Notebook-specific creation and development cycle
- **`dataset-lifecycle`** — Creating and versioning the datasets that executions consume
- **`create-feature`** — Creating features whose values are produced by executions
- **`ml-data-engineering`** — Restructuring downloaded data for ML frameworks
