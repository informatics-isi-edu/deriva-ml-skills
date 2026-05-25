---
name: execution-lifecycle
description: "ALWAYS use this skill when running ML experiments, creating executions, managing workflow provenance, pre-flight validation, or configuring experiment runs in DerivaML. Covers the full execution lifecycle: pre-flight checks (validate RIDs, check cache, cache data), creating and running executions via MCP tools or Python API, managing inputs/outputs with provenance, committing results via the unified commit_output_assets API, nested executions, dry runs, and the deriva-ml-run CLI. After an execution completes and commits its output assets (model weights, prediction CSVs, plots, etc.), proactively offer to wire the resulting asset RIDs into src/configs/assets.py so downstream experiments can pin them — this skill owns the bulk-output offer (the per-asset scope lives in work-with-assets). Triggers on: 'run experiment', 'create execution', 'execution lifecycle', 'commit outputs', 'upload outputs', 'commit_output_assets', 'pre-flight', 'dry run', 'validate before running', 'cache dataset', 'workflow provenance', 'deriva-ml-run', 'multirun', 'sweep', 'check git before running', 'nested execution', 'track my work', 'wire outputs into config', 'add output assets to assets.py'."
---

# Execution Lifecycle in DerivaML

An execution is the fundamental unit of provenance in DerivaML. It records what work was done, with what inputs (datasets, assets), what outputs were produced, and what code and configuration were used.

For background on the execution hierarchy, statuses, workflows, nested executions, dry run mode, and the working directory layout, see `references/concepts.md`.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly.

## Git Commit Enforcement

DerivaML enforces that all code is committed before running catalog-mutating operations. If uncommitted changes are detected, `deriva-ml-run` and `deriva-ml-run-notebook` raise `DerivaMLDirtyWorkflowError` and refuse to proceed.

- **`--allow-dirty`** overrides the check, but the resulting execution has **degraded provenance** — the git hash in the execution record may not match the code that actually ran. Acceptable scope: **rapid local iteration during development** (you're tweaking a script and want a few smoke runs before committing). Never acceptable for: any execution whose RID will be cited downstream, any execution that produces dataset versions or feature values that anyone else will consume, any production training run. The rule of thumb: if anyone else will ever ask "what code produced this?", commit first; if you'd throw the execution away in an hour, `--allow-dirty` is fine.
- This applies to all `deriva-ml-run` and `deriva-ml-run-notebook` invocations.
- Simple one-off MCP tool operations (adding a vocabulary term, updating a description) are not affected.

> **Schema pinning (the catalog-side counterpart).** Git-clean-tree freezes the *code* the run will see; `ml.pin_schema(reason=...)` freezes the *catalog shape* the run will see. Both should be in place for any production run on a shared catalog where a concurrent migration could change column names or table structure mid-run. See `references/concepts.md` → "Schema Pinning for Long Runs" for when and how.

> **Offline mode (laptop / batch / disconnected work).** `DerivaML(mode=ConnectionMode.offline)` stages every write to local SQLite and drains via `ml.commit_pending_executions()` when you reconnect. Requires a previously-populated schema cache in the same `working_dir`. See `references/concepts.md` → "Offline Mode" for the full pattern.

## Phase 1: Pre-Flight Validation

Before running an experiment, validate that everything is in place. **Stop and fix any issues.** The full pre-flight walkthrough (Hydra `--info` / `--cfg job` invocations, per-RID validation calls, staging script patterns) lives in `references/workflow.md`; this section names what to validate.

1. **Resolve the configuration.** For CLI runs, dump the resolved config with `uv run deriva-ml-run +experiment=<name> --info` (or `--cfg job` for the full YAML). Extract dataset RIDs, asset RIDs, and versions from the resolved `datasets` and `assets` groups. For MCP-tool / Python-API runs, collect the RIDs from the call site.
2. **Validate all RIDs and versions.** Use `deriva_ml_get_dataset` for datasets, `get_entities` for assets, `deriva_ml_bag_info` for pinned dataset-version validity (it errors immediately if the version doesn't exist). Stop if any RID returns empty / errors.
3. **Check data readiness.** For the dataset's **current** version, the lead path is the bag-preview resource `deriva://catalog/{h}/{c}/ml/dataset/{rid}/bag-preview` (one round trip, no parameters). For a **pinned version** or to **exclude tables**, use the tool: `deriva_ml_bag_info(hostname, catalog_id, dataset_rid, version)`. Both return size info AND cache status:

   | Status | Meaning |
   |---|---|
   | `not_cached` | Will need to download (check `total_asset_size`) |
   | `cached_metadata_only` | Table data present; assets need materialization |
   | `cached_materialized` | Ready to go |
   | `cached_incomplete` | Needs re-materialization |

4. **Stage if needed.** Small datasets (< 100 MB) — let the execution download. Large datasets (> 1 GB) — use the bundled `skills/manage-storage/scripts/warm_cache.py` template to pre-fetch into the local cache before the execution starts. Individual assets (model weights) — `skills/work-with-assets/scripts/download_asset.py`. Staging populates the local cache without creating execution records.
5. **Code and environment checks (CLI runs).** `git status` clean (`DerivaMLDirtyWorkflowError` if not — use `--allow-dirty` only for debugging). Version current (`bump_version("patch")` or `uv run bump-version patch|minor`). Lock file valid (`uv lock --check`).
6. **User confirmation.** Present commit hash + version + branch + experiment name + key parameters + dataset versions and cache status. Get explicit approval before production runs.

## Phase 2: Create and Run

Two paths; choose based on context:

| Path | When to use | What runs |
|------|-------------|-----------|
| **Bundled script template** | Author any catalog-mutating execution | Copy a template from `scripts/`, edit parameters, commit, run with `deriva-ml-run` |
| **CLI (`deriva-ml-run`)** | Reproducible Hydra-driven experiment runs | Wraps the same context-manager pattern + drives `commit_output_assets()` automatically |

**MCP tools are for observation only**, not for authoring or mutating executions. Use them to inspect: `deriva_ml_get_execution`, `deriva_ml_list_executions`, `deriva_ml_find_workflow_executions`, `deriva_ml_get_lineage`, `deriva_ml_list_execution_children`, `deriva_ml_list_execution_parents`. Lifecycle transitions and output uploads happen inside the script you committed — the workflow's URL + checksum then resolve to real code, which is the reproducibility contract.

### Bundled script templates

This skill ships ready-to-edit templates under `skills/execution-lifecycle/scripts/`. Copy the one that matches your task into the user's project (typically `src/scripts/<task>.py`), edit the parameters and the work block, commit the script, then run with `deriva-ml-run`.

| Template | When to use |
|---|---|
| `basic_execution.py` | One-shot run producing output assets |
| `nested_execution.py` | Parent run with N children (sweeps, pipelines, fan-out batches) |
| `salvage_execution.py` | Drive `commit_output_assets()` on a `Stopped`/`Failed` execution with staged outputs |
| `crash_recovery.py` | `Running → Pending_Upload` direct transition after a hard crash; `--abort` mode to discard |

Companion task templates live under other skills' `scripts/` directories:

- `skills/create-feature/scripts/populate_feature_values.py` — bulk-load feature values from a CSV
- `skills/manage-storage/scripts/warm_cache.py` — pre-fetch a dataset bag into local cache
- `skills/work-with-assets/scripts/upload_asset.py` / `download_asset.py` — per-asset file I/O with execution provenance

**Key rule:** Always dry run first — `--dry-run` on the script (or `dry_run=true` Hydra override on `deriva-ml-run`).

The lifecycle inside every template is the same:

1. Create the workflow (content-addressed by URL + commit hash).
2. Open `with ml.create_execution(config, workflow=workflow, dry_run=...) as exe:`.
3. Inside the `with` block: download inputs (`exe.download_dataset_bag()`, `exe.download_asset()`), do the work, stage outputs (`exe.asset_file_path()`, `exe.add_features()`, `exe.create_dataset()`).
4. After the `with` block: `exe.commit_output_assets()` — uploads staged bytes, writes asset rows, transitions `Stopped → Pending_Upload → Uploaded`. Idempotent on re-call.

**Automatic metadata:** Every execution captures configuration (`Deriva_Config`, `Hydra_Config`), environment lock file (`Execution_Config`), and runtime environment (`Runtime_Env`) as `Execution_Metadata` records — see `references/concepts.md`.

**Notebook outputs:** When running notebooks via `deriva-ml-run-notebook`, the executed `.ipynb` and converted `.md` are automatically uploaded as execution assets alongside any files registered via `asset_file_path()` — see `references/workflow.md`.

For complete tool-call sequences, code examples, and CLI commands for each path, see `references/workflow.md`. For the `deriva-ml-run` CLI surface (Hydra overrides, multirun syntax), see `references/cli-reference.md`.

## Phase 3: Verify Results

After a run, check the execution:

```
deriva_ml_get_execution(hostname, catalog_id, execution_rid="<rid>")
```

Or read the resource `deriva://catalog/{hostname}/{catalog_id}/ml/execution/{rid}`, or `cite(hostname, catalog_id, rid="<rid>", current=true)` for a Chaise URL. Verify: status is `Uploaded`, correct inputs linked, output assets attached, git hash matches.

### Proactively offer to wire output assets into `src/configs/assets.py`

A completed execution typically produces one or more **output assets** (model weights, prediction CSVs, ROC plots, etc.) that downstream experiments will consume. The execution's `deriva_ml_get_execution` response lists them with their fresh RIDs. **Offer to wire those RIDs into `src/configs/assets.py`** so the next experiment in the pipeline can pin them. Don't wait for the user to ask.

The scope is distinct from `work-with-assets`'s offer:

| Scope | When the offer fires | Who owns |
|---|---|---|
| Bulk output of a completed run (N assets at once) | `exe.commit_output_assets()` returns an `UploadReport`; `deriva_ml_get_execution` lists the new asset RIDs | `execution-lifecycle` (this skill) |
| Single-asset creation / registration / upload (one at a time, intentional) | a single new asset RID becomes visible | `work-with-assets` |

Sample wording (multi-asset case is the common one for executions):

> *"The run produced 3 output assets:*
> *- `3-WTS1` — model_weights.pt*
> *- `3-CSV1` — prediction_probabilities.csv*
> *- `3-PNG1` — confusion_matrix.png*
> *Want me to add them to `src/configs/assets.py`? I can group them as a single config entry (e.g., `cifar10_quick_outputs`) or as separate entries — your call."*

If they say yes:

- Use `deriva_ml_get_execution(...)` (or its resource form) to confirm the assets are committed and to read each asset's metadata (file name, MD5, size) before writing the config entry.
- Group decision is the user's call — for a single training run that produces weights + predictions + a plot, a single config entry referencing all three is idiomatic. For an unrelated set of uploads, separate entries make more sense.
- The `AssetSpecConfig` shape lives in `deriva_ml.asset.aux_classes`; see `/deriva-ml:write-hydra-config` for the field reference.
- Commit as `chore(configs): add outputs from execution <rid>` — the execution RID in the commit message is the cross-reference back to provenance.

If they say no, **say so plainly** so future invocations in the same session don't re-offer the same RIDs. The config file isn't a side effect — the user has owned the decision.

Hand-offs: `/deriva-ml:write-hydra-config` for `assets.py` format mechanics; `/deriva-ml:configure-experiment` for wiring the assets into a downstream experiment config.

## Critical Rules

1. **Validate before running** — typed reads (`deriva_ml_get_dataset`, `get_entities`) plus `deriva_ml_bag_info` catch config errors early
2. **Dry run first** — test with `dry_run=True` before production runs
3. **Every execution needs a workflow** — find with `deriva_ml_find_workflow_by_url`, or let `ml.create_workflow(name, workflow_type, description)` mint a new one (the bundled templates do this for you)
4. **Commit AFTER the with block** — `exe.commit_output_assets()` goes after `with`, not inside (or omit it entirely and let the context manager's auto-stop drive the commit on exit). Re-call if the first attempt partially failed — the bag-commit pipeline is idempotent.
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
