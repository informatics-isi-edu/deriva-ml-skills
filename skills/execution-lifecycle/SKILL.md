---
name: execution-lifecycle
description: "ALWAYS use this skill when running ML experiments, creating executions, managing workflow provenance, pre-flight validation, or configuring experiment runs in DerivaML. Covers the full execution lifecycle: pre-flight checks (validate RIDs, check cache, cache data), creating and running executions via MCP tools or Python API, managing inputs/outputs with provenance, uploading results, nested executions, dry runs, and the deriva-ml-run CLI. Triggers on: 'run experiment', 'create execution', 'execution lifecycle', 'upload outputs', 'pre-flight', 'dry run', 'validate before running', 'cache dataset', 'workflow provenance', 'deriva-ml-run', 'multirun', 'sweep', 'check git before running', 'nested execution', 'track my work'."
---

# Execution Lifecycle in DerivaML

An execution is the fundamental unit of provenance in DerivaML. It records what work was done, with what inputs (datasets, assets), what outputs were produced, and what code and configuration were used.

For background on the execution hierarchy, statuses, workflows, nested executions, dry run mode, and the working directory layout, see `references/concepts.md`.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly.

## Git Commit Enforcement

DerivaML enforces that all code is committed before running catalog-mutating operations. If uncommitted changes are detected, `deriva-ml-run` and `deriva-ml-run-notebook` raise `DerivaMLDirtyWorkflowError` and refuse to proceed.

- **`--allow-dirty`** overrides the check for debugging iterations, but the resulting execution has **degraded provenance** — the git hash in the execution record may not match the code that actually ran.
- This applies to all `deriva-ml-run` and `deriva-ml-run-notebook` invocations.
- Simple one-off MCP tool operations (adding a vocabulary term, updating a description) are not affected.

## Phase 1: Pre-Flight Validation

Before running an experiment, validate that everything is in place. **Stop and fix any issues.** The full pre-flight walkthrough (Hydra `--info` / `--cfg job` invocations, per-RID validation calls, staging script patterns) lives in `references/workflow.md`; this section names what to validate.

1. **Resolve the configuration.** For CLI runs, dump the resolved config with `uv run deriva-ml-run +experiment=<name> --info` (or `--cfg job` for the full YAML). Extract dataset RIDs, asset RIDs, and versions from the resolved `datasets` and `assets` groups. For MCP-tool / Python-API runs, collect the RIDs from the call site.
2. **Validate all RIDs and versions.** Use `deriva_ml_get_dataset` for datasets, `get_entities` for assets, `deriva_ml_bag_info` for dataset-version validity (it errors immediately if the version doesn't exist). Stop if any RID returns empty / errors.
3. **Check data readiness with `deriva_ml_bag_info(hostname, catalog_id, dataset_rid, version)`.** Returns size info AND cache status:

   | Status | Meaning |
   |---|---|
   | `not_cached` | Will need to download (check `total_asset_size`) |
   | `cached_metadata_only` | Table data present; assets need materialization |
   | `cached_materialized` | Ready to go |
   | `cached_incomplete` | Needs re-materialization |

4. **Stage if needed.** Small datasets (< 100 MB) — let the execution download. Large datasets (> 1 GB) — `deriva_ml_cache_dataset(...)` first. Individual assets (model weights) — `ml.download_asset("3WSE")` in a short Python staging script. Staging populates the local cache without creating execution records.
5. **Code and environment checks (CLI runs).** `git status` clean (`DerivaMLDirtyWorkflowError` if not — use `--allow-dirty` only for debugging). Version current (`bump_version("patch")` or `uv run bump-version patch|minor`). Lock file valid (`uv lock --check`).
6. **User confirmation.** Present commit hash + version + branch + experiment name + key parameters + dataset versions and cache status. Get explicit approval before production runs.

## Phase 2: Create and Run

Three paths; choose based on context:

| Path | When to use | Lifecycle managed by |
|------|-------------|---------------------|
| **MCP Tools** | Claude-driven interactive work | Explicit tool calls (`deriva_ml_create_execution` → `deriva_ml_start_execution` → work → `deriva_ml_commit_execution` / `deriva_ml_abort_execution`) + Python API for I/O |
| **Python API** | Scripts and custom workflows | Context manager (`with ml.create_execution(config) as exe:`) |
| **CLI** | Reproducible experiment runs | `deriva-ml-run` handles everything automatically |

**Key rule:** Always dry run first — `dry_run=True` (MCP/Python) or `dry_run=True` (CLI override).

The lifecycle is the same regardless of path:

1. Create execution (with workflow, inputs, description)
2. Start → download inputs → do work → register outputs → stop
3. Upload outputs to catalog

**I/O goes through the Python API**, not MCP tools: `exe.download_dataset_bag()`, `exe.asset_file_path()`, `exe.upload_execution_outputs()`. MCP tools handle lifecycle state transitions; Python handles file I/O.

**Automatic metadata:** Every execution captures configuration (`Deriva_Config`, `Hydra_Config`), environment lock file (`Execution_Config`), and runtime environment (`Runtime_Env`) as `Execution_Metadata` records — see `references/concepts.md`.

**Notebook outputs:** When running notebooks via `deriva-ml-run-notebook`, the executed `.ipynb` and converted `.md` are automatically uploaded as execution assets alongside any files registered via `asset_file_path()` — see `references/workflow.md`.

For complete tool-call sequences, code examples, and CLI commands for each path, see `references/workflow.md`. For the `deriva-ml-run` CLI surface (Hydra overrides, multirun syntax), see `references/cli-reference.md`.

## Phase 3: Verify Results

After a run, check the execution:

```
deriva_ml_get_execution(hostname, catalog_id, execution_rid="<rid>")
```

Or read the resource `deriva://catalog/{hostname}/{catalog_id}/ml/execution/{rid}`, or `cite(hostname, catalog_id, rid="<rid>", current=true)` for a Chaise URL. Verify: status is `Completed`, correct inputs linked, output assets attached, git hash matches.

## Critical Rules

1. **Validate before running** — typed reads (`deriva_ml_get_dataset`, `get_entities`) plus `deriva_ml_bag_info` catch config errors early
2. **Dry run first** — test with `dry_run=True` before production runs
3. **Every execution needs a workflow** — find with `deriva_ml_find_workflow_by_url` or let `deriva_ml_create_execution` create one
4. **Upload AFTER the with block** — `exe.upload_execution_outputs()` goes after `with`, not inside
5. **Use Python API `exe.asset_file_path()` for all outputs** — never manually place files in the working directory
6. **Commit code before running** — DerivaML raises `DerivaMLDirtyWorkflowError` if uncommitted changes exist. Use `--allow-dirty` only for debugging.

## Reference Resources

- `references/concepts.md` — Execution hierarchy, status state machine, workflows, source code detection, nested executions, metadata auto-generation, dry run, working directory, data flow
- `references/workflow.md` — Step-by-step MCP and Python API workflows, notebook output handling, complete examples, full pre-flight walkthrough
- `references/cli-reference.md` — `deriva-ml-run` CLI commands, Hydra overrides, multirun syntax
- `rag_search("training experiments", doc_type="catalog-data")` — find executions by workflow or status
- `rag_search("workflow types", doc_type="catalog-schema")` — discover available workflow types
- `deriva://catalog/{hostname}/{catalog_id}/ml/execution/{rid}` — Execution details and status
- `deriva://catalog/{hostname}/{catalog_id}/ml/executions` — Browse recent executions
- `deriva://catalog/{hostname}/{catalog_id}/ml/workflows` — Available workflows
- `deriva://catalog/{hostname}/{catalog_id}/ml/vocabularies/deriva-ml/Workflow_Type` — Workflow type vocabulary terms
- `deriva://catalog/{hostname}/{catalog_id}/ml/vocabularies/deriva-ml/Dataset_Type` — Dataset type vocabulary terms

Prefer typed tool calls: `deriva_ml_get_execution`, `deriva_ml_list_executions`, `deriva_ml_list_workflows`.

## Related Skills

- **`/deriva-ml:configure-experiment`** — Setting up Hydra-zen config groups and experiment presets
- **`/deriva-ml:write-hydra-config`** — Python API patterns for each config type
- **`/deriva-ml:run-notebook`** — Notebook-specific creation and development cycle
- **`/deriva-ml:dataset-lifecycle`** — Creating and versioning the datasets that executions consume
- **`/deriva-ml:create-feature`** — Creating features whose values are produced by executions
- **`/deriva-ml:ml-data-engineering`** — Restructuring downloaded data for ML frameworks
