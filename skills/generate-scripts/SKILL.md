---
name: generate-scripts
description: "Use whenever Claude needs to generate a Python script that interacts with a Deriva catalog — data exploration, bulk reads beyond MCP's 100-row cap, loading data, creating features, uploading assets, or any catalog mutation that needs reproducibility. Two script categories: EXPLORATION scripts (ephemeral, throwaway analysis) and CATALOG-MODIFYING scripts (committed, with execution provenance via the `with ml.create_execution(...) as exe:` context manager). Triggers on: 'write a script', 'generate a script', 'fetch all records', 'get all features', 'load data into catalog', 'bulk insert', 'upload results', 'I need more than 100 rows', 'cache the data', 'compute metrics across all images', and implicitly whenever query_attribute, get_table_sample_data, or deriva_ml_denormalize_dataset returns truncated results. Also use when about to perform raw catalog mutations (insert_entities / update_entities / delete_entities, ETL, bulk loads) — those belong in a committed script, not an interactive MCP call, so the git hash records what ran."
disable-model-invocation: true
---

# Script Generation for DerivaML

When MCP tools return truncated results (`query_attribute`, `get_table_sample_data`, and `deriva_ml_denormalize_dataset` cap at 100 rows), or when operations need to mutate the catalog (load data, create features, upload assets, register output datasets), generate a Python script that uses the DerivaML Python API directly.

> **RAG-first.** Before generating, use `rag_search()` to discover relevant catalog entities (tables, features, datasets, vocabulary terms) so the script references the correct names, RIDs, and column types.

> **Python API ≠ MCP tools.** Methods like `ml.cache_table()`, `dataset.cache_denormalized()`, `ml.feature_values()`, `ml.create_workflow()`, `ml.create_execution()`, and `execution.asset_file_path()` are all Python API methods available only in scripts and notebooks. They are **not** MCP tools.

## When to use scripts vs interactive MCP

| Situation | Approach |
|---|---|
| One-off exploration, quick queries, checking state | Interactive MCP tools |
| Setting descriptions, display names, annotations | Interactive MCP tools |
| Operations you'll need to reproduce or share | **Committed script** |
| Dataset creation, splitting, ETL, data loading | **Committed script** |
| Feature creation and bulk population | **Committed script** |
| Output asset upload | **Committed script** |
| Operations others need to audit or re-run | **Committed script** |

The reason: DerivaML records the git commit hash with every execution. A committed script gives the execution record a code reference that anyone can trace back. Interactive MCP operations have no such reference.

## Two categories of scripts

### Category 1: Exploration scripts (ephemeral)

**Purpose.** Fetch bulk data, compute statistics, produce plots, analyze distributions. Read-only against the catalog.

**Rules:**

- Do NOT commit to repo — these are throwaway.
- Do NOT create executions — no provenance needed.
- DO use the table cache (`ml.cache_table()`) and feature reads (`ml.feature_values()`).
- DO print summary output so Claude can read the results.
- Save to a temp file or run inline.

**Template:**

```python
from deriva_ml import DerivaML
import pandas as pd

ml = DerivaML.from_context()

# cache_table is idempotent — fetch once, cache in SQLite, reuse on subsequent calls
df = ml.cache_table("Image")
print(f"Total images: {len(df)}")
print(df.describe())

# Or denormalize a dataset
dataset = ml.lookup_dataset("28CT")
wide = dataset.cache_denormalized(["Image", "Image_Diagnosis"], version="1.0.0")
print(wide["Image_Diagnosis.Diagnosis_Image"].value_counts())

# Or fetch features (returns an Iterable[FeatureRecord])
records = list(ml.feature_values("Image", "Classification"))
labels = pd.DataFrame.from_records(r.model_dump() for r in records)
print(f"Labeled images: {len(labels)}")
print(labels["Diagnosis_Type"].value_counts())
```

**When to use exploration scripts:**

- User asks "how many images have each diagnosis?"
- User asks "show me the distribution of ages"
- User asks "what does the denormalized data look like?"
- `query_attribute` or `get_table_sample_data` returned 100 rows but the user needs counts/stats on the full table.
- Any read-only analysis that doesn't change the catalog.

### Category 2: Catalog-modifying scripts (committed)

**Purpose.** Load data, create features, upload assets, produce outputs that go into the catalog.

**Rules:**

- **MUST be committed to the repo** before running (code provenance).
- **MUST open an execution** via the `with ml.create_execution(...) as exe:` context manager (provenance tracking).
- **MUST be documented** in `experiment-decisions.md` (via `maintain-experiment-notes`).
- Save to `src/scripts/` in the project.

**Don't reinvent the lifecycle pattern.** This plugin ships ready-to-edit templates that already implement the canonical context manager, argparse, dry-run, and commit shape. Copy the one matching your task, customize the work block, commit, and run:

| Template | When to use |
|---|---|
| [`skills/execution-lifecycle/scripts/basic_execution.py`](../execution-lifecycle/scripts/basic_execution.py) | One-shot run producing output assets |
| [`skills/execution-lifecycle/scripts/nested_execution.py`](../execution-lifecycle/scripts/nested_execution.py) | Parent + N children (sweeps, fan-out batches) |
| [`skills/execution-lifecycle/scripts/salvage_execution.py`](../execution-lifecycle/scripts/salvage_execution.py) | Commit staged outputs from a `Stopped` / `Pending_Upload` execution |
| [`skills/execution-lifecycle/scripts/crash_recovery.py`](../execution-lifecycle/scripts/crash_recovery.py) | `Running → Pending_Upload` direct transition after a hard crash; `--abort` to discard |
| [`skills/create-feature/scripts/populate_feature_values.py`](../create-feature/scripts/populate_feature_values.py) | Bulk-load feature values from a CSV |
| [`skills/manage-storage/scripts/warm_cache.py`](../manage-storage/scripts/warm_cache.py) | Pre-fetch a dataset bag into local cache (no execution needed) |
| [`skills/work-with-assets/scripts/upload_asset.py`](../work-with-assets/scripts/upload_asset.py), [`download_asset.py`](../work-with-assets/scripts/download_asset.py) | Per-asset file I/O with execution provenance |

For dataset-shaped operations (bootstrap a dataset, split, ETL, generic feature population without a CSV), see `references/script-patterns.md` — Base Template plus four patterns (Dataset Creation, Dataset Splitting, Feature Creation and Population, ETL / Data Loading).

The lifecycle inside every template is the same:

```python
from deriva_ml import DerivaML
from deriva_ml.execution import ExecutionConfiguration

ml = DerivaML(hostname=args.hostname, catalog_id=args.catalog_id)

workflow = ml.create_workflow(
    name="<one-line description>",
    workflow_type=args.workflow_type,
    description="<longer description>",
)
config = ExecutionConfiguration(description="<what this run does>")

with ml.create_execution(config, workflow=workflow,
                         dry_run=args.dry_run) as execution:
    # ... do the work ...
    # execution.add_features(records)
    # execution.asset_file_path(...)
    # execution.create_dataset(...)
    pass

# AFTER the with block — flushes staged bytes + writes asset rows,
# transitions Stopped → Pending_Upload → Uploaded. Idempotent on re-call.
execution.commit_output_assets()
```

Two things that frequently bite first-time authors:

- `commit_output_assets()` is called **after** the `with` block exits. The `execution` object remains valid for upload after the context closes. Calling it *inside* the `with` block is a common bug.
- The `workflow=` argument goes to `ml.create_execution(...)`, **not** to `ExecutionConfiguration(...)`. (ExecutionConfiguration accepts `datasets=`, `assets=`, `description=`, and `argv=`; workflow goes to the execution itself.)

## Develop, Test, Commit, Run

The standard cycle for any catalog-modifying script:

1. **Generate** the script in `src/scripts/`, starting from the template that matches your task.
2. **Test** with `--dry-run` to verify correctness without creating catalog records. The bundled templates support `--dry-run` out of the box; the `create_execution(..., dry_run=True)` flag opens the execution in a mode that validates inputs but does not write.
3. **Commit** the script. DerivaML enforces this: running an uncommitted script raises `DerivaMLDirtyWorkflowError`. Use `--allow-dirty` only for tight debugging iterations (degraded provenance — the recorded git hash won't match the running code).
4. **Run** for real. The execution record captures the git commit hash, repository URL, input datasets and versions, output assets and datasets, and execution parameters.

## Branch workflow and code provenance

DerivaML captures the git commit hash and repository URL at run time, so the branch you run from matters:

- **Worktrees and feature branches are temporary.** If a branch is deleted before merging, the commit hash in the execution record becomes unreachable, breaking the provenance link.
- **Main-branch commits are permanent.** Anyone can trace the execution back to the exact code that ran.

**Recommended workflow:**

1. **Develop** scripts in a feature branch or worktree. Iterate freely with `--dry-run`.
2. **Merge to main** once the script is working.
3. **Run for real from main** so execution records reference permanent, reachable commits.
4. **Bump version** *after* merging, not before — the tag should include all changes.

Especially important for:

- Dataset creation scripts that establish the foundation for downstream experiments.
- ETL / data loading scripts that others will need to audit.
- Any script whose execution record will be cited or shared.

**What to avoid:**

- Running catalog-modifying scripts from unmerged branches — the provenance link may break.
- Bumping versions before merging feature work — the tag won't include the new code.
- Deleting branches that have execution records pointing to them.

## Connection context

All scripts use `DerivaML(hostname=..., catalog_id=...)` (or `DerivaML.from_context()` if a `.deriva-context.json` is set up in the project working directory — that file holds hostname, catalog_id, default_schema, working_dir).

**Never hardcode connection details** in committed scripts. Either accept them as CLI args (preferred for explicit, reproducible runs — what the bundled templates do) or read them from context.

## Script naming conventions

| Category | Location | Naming |
|---|---|---|
| Exploration | Inline or `/tmp/` | `explore_*.py` |
| Data loading | `src/scripts/` | `load_*.py` |
| Feature computation | `src/scripts/` | `compute_*.py` |
| Asset generation | `src/scripts/` | `generate_*.py` |
| Data migration | `src/scripts/` | `migrate_*.py` |

## Decision matrix: exploration vs catalog-modifying

Ask yourself: **does this script change the catalog?**

| Action | Category | Commit? | Execution? |
|---|---|:--:|:--:|
| Count records, compute statistics, plot distributions | Exploration | No | No |
| Fetch and analyze features (read-only) | Exploration | No | No |
| Insert records, add feature values, upload assets, create datasets | Catalog-modifying | **Yes** | **Yes** |
| Modify vocabulary terms | Catalog-modifying | **Yes** | **Yes** |

## When to suggest writing a script

When a user asks to perform a catalog-modifying operation interactively, suggest:

> *"For full provenance tracking, I recommend creating a script we can commit before running. The execution record will reference the exact code, so anyone can reproduce or audit this operation. Want me to generate it from the matching template?"*

Then follow Develop, Test, Commit, Run.

## Related skills

- [`maintain-experiment-notes`](../maintain-experiment-notes/SKILL.md) — Document catalog-modifying scripts in `experiment-decisions.md`.
- [`execution-lifecycle`](../execution-lifecycle/SKILL.md) — The full context-manager lifecycle, salvage flows, status state machine, and the bundled templates linked above.
- [`setup-derivaml-project`](../setup-derivaml-project/SKILL.md) — Project bootstrap and coding conventions (Google docstrings, type hints, ruff).
- [`work-with-assets`](../work-with-assets/SKILL.md) — Asset upload patterns (Python API).
- [`dataset-lifecycle`](../dataset-lifecycle/SKILL.md) — Dataset operations that scripts may perform.
- [`create-feature`](../create-feature/SKILL.md) — Feature definition + the bulk-load template.
