---
name: execution-lifecycle
description: "ALWAYS use this skill when running ML experiments, creating executions, managing workflow provenance, pre-flight validation, or configuring experiment runs in DerivaML. Covers the full execution lifecycle: pre-flight checks (validate RIDs, check cache, cache data), creating and running executions via MCP tools or Python API, managing inputs/outputs with provenance, uploading results, nested executions, dry runs, and the deriva-ml-run CLI. Triggers on: 'run experiment', 'create execution', 'execution lifecycle', 'upload outputs', 'pre-flight', 'dry run', 'validate before running', 'cache dataset', 'workflow provenance', 'deriva-ml-run', 'multirun', 'sweep', 'check git before running', 'nested execution', 'track my work'."
---

# Execution Lifecycle in DerivaML

An execution is the fundamental unit of provenance in DerivaML. It records what work was done, with what inputs (datasets, assets), what outputs were produced, and what code and configuration were used.

For background on the execution hierarchy, statuses, workflows, nested executions, dry run mode, and the working directory layout, see `references/concepts.md`.

## Stateless model

> The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

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

**For MCP tool runs** — the user provides the RIDs directly in the `deriva_ml_create_execution` call. Collect them before proceeding.

**For Python API runs** — read the `ExecutionConfiguration` or the hydra-zen config module to extract dataset and asset references.

### Step 2: Validate all RIDs and versions

The legacy `validate_rids` tool is gone. Use `get_entities` (tier-1 deriva-mcp-core) per candidate table and check for empty results, or use the typed lookups for each domain object:

```
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="28CT")
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="28D0")
get_entities(hostname="data.example.org", catalog_id="1", schema="<asset_schema>", table="<asset_table>", filter={"RID": "3WSE"})
```

For dataset-version validity, `deriva_ml_bag_info(...)` (next step) doubles as a version check — if the version doesn't exist, it errors immediately.

**Stop if any RID returns empty / errors.** Fix the configuration before proceeding.

### Step 3: Check data readiness and decide whether to stage

For each dataset in the config, check cache status and size:

```
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="28CT", version="0.9.0")
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
| Large dataset (>1 GB), not cached | **Stage first** with `deriva_ml_cache_dataset` |
| Any dataset, `cached_materialized` | No action needed — will use cache |
| Asset (model weights), not cached | **Stage first** by downloading via the Python API (`ml.download_asset`) before the run |

### Step 4: Stage data if needed

For datasets:
```
deriva_ml_cache_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="28CT", version="0.9.0")
```

For individual assets (model weights, etc.), use the Python API in a short staging script:
```python
ml.download_asset("3WSE")
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
| **MCP Tools** | Claude-driven interactive work | Explicit tool calls (`deriva_ml_create_execution` → `deriva_ml_start_execution` → work → `deriva_ml_commit_execution` / `deriva_ml_abort_execution`) + Python API for I/O |
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
deriva_ml_get_execution(hostname="data.example.org", catalog_id="1", execution_rid="{execution_rid}")
Read resource: deriva://catalog/data.example.org/1/ml/execution/{execution_rid}
cite(hostname="data.example.org", catalog_id="1", rid="{execution_rid}", current=True)
```

Verify: status is "Completed", correct inputs linked, output assets attached, git hash matches.

## Critical Rules

1. **Validate before running** — typed reads (`deriva_ml_get_dataset`, `get_entities`) plus `deriva_ml_bag_info` catch config errors early
2. **Dry run first** — test with `dry_run=True` before production runs
3. **Every execution needs a workflow** — find with `deriva_ml_find_workflow_by_url` or let `deriva_ml_create_execution` create one
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
- `deriva://catalog/{hostname}/{catalog_id}/ml/execution/{execution_rid}` — Execution details and status
- `deriva://catalog/{hostname}/{catalog_id}/ml/executions` — Browse recent executions
- `deriva://catalog/{hostname}/{catalog_id}/ml/workflows` — Available workflows
- `deriva://catalog/{hostname}/{catalog_id}/ml/registries` — Workflow type and dataset type vocabulary terms

When in doubt, prefer the typed tool calls: `deriva_ml_get_execution`, `deriva_ml_list_executions`, `deriva_ml_list_workflows`.

## Related Skills

- **`configure-experiment`** — Setting up Hydra-zen config groups and experiment presets
- **`write-hydra-config`** — Python API patterns for each config type
- **`run-notebook`** — Notebook-specific creation and development cycle
- **`dataset-lifecycle`** — Creating and versioning the datasets that executions consume
- **`create-feature`** — Creating features whose values are produced by executions
- **`ml-data-engineering`** — Restructuring downloaded data for ML frameworks
