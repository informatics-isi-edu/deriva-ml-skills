---
name: model-development-workflow
description: "Use when STANDING UP a new ML pipeline or onboarding to one for the first time — the cycle-zero work that has to happen before any hypothesis-driven experiment can start. Covers the end-to-end bootstrap: schema design → create small representative dataset → validate features → dry run → small-data run → first full-scale production run. Teaches the three-tier pattern (dry_run → small dataset → full dataset) that catches config and pipeline bugs before they cost full-scale compute. The skill's job ends when the pipeline produces real results; from there, hypothesis-driven iteration belongs in `/deriva-ml:experiment-lifecycle`. Triggers on: 'new ML project', 'set up a new pipeline', 'first model', 'onboard to existing project', 'standing up training', 'how should I get started', 'start small', 'representative dataset', 'development subset', 'what order should I do things', 'best practices for training', 'debug my training' (when the pipeline itself is new/unproven)."
user-invocable: true
disable-model-invocation: true
---

# Model Development Workflow (cycle zero)

This skill teaches the **bootstrap** workflow for a new DerivaML pipeline. It's cycle-zero work: schema design through the first production-scale training run. The core principle: **start small, validate early, scale up only after everything works.**

Most wasted compute comes from running full-scale training on broken configurations. This workflow catches problems at each tier before they become expensive.

> **When this skill stops, `experiment-lifecycle` starts.** Once you have a working pipeline that's produced real (not validation) results, the hypothesis-driven iteration loop ("what's the next experiment that would teach us something we don't already know?") belongs in `/deriva-ml:experiment-lifecycle`. That skill assumes the pipeline exists and is sound; this skill exists to get you to that point.

> Every MCP tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## The Three-Tier Development Pattern

Every DerivaML workflow follows this progression:

| Tier | Data | Execution | Purpose | Cost |
|:---:|------|-----------|---------|:---:|
| **1** | None | `dry_run=True` | Validate config, test data loading paths | Free |
| **2** | Small subset (50–200 records) | Real execution | End-to-end pipeline validation | Minutes |
| **3** | Full dataset | Production execution | Real results | Hours/days |

**Never skip tiers.** Tier 1 catches config errors. Tier 2 catches data pipeline bugs. Tier 3 is only for generating real results.


## Phase 1: Schema Design

Before any data, design the catalog structure.

**Decision sequence:**
1. What domain tables do I need? (Subject, Image, Observation, etc.)
2. What vocabularies provide consistent categorical labels?
3. What features attach annotations to records?
4. What asset tables store files? (images, models, masks, etc.)

**Skills to use:**
- `/deriva:create-table` *(deriva-skills)* — domain tables with columns and foreign keys
- `/deriva:manage-vocabulary` *(deriva-skills)* — controlled vocabularies for categorical data
- `create-feature` *(this plugin)* — features linking annotations to domain objects
- `work-with-assets` *(this plugin)* — asset tables for file management

**Start simple.** You can always add columns, vocabularies, and features later. Don't over-design the schema before you have data.

**After creating the schema**, run `rag_index_schema()` so the RAG index includes your new tables.


## Phase 2: Create a Development Dataset

Create a small, representative dataset for development. This is the dataset you'll use for tiers 1 and 2.

### What "representative" means

A development dataset should:
- Have **50–200 records** (enough to test pipelines, small enough to iterate fast)
- Include **all classes** in your classification task (at least 5–10 per class)
- Cover **edge cases** you know about (missing values, unusual formats)
- Be **labeled** if your workflow needs labels

### How to create it

```
# 1. Register Image as a dataset element type
deriva_ml_add_dataset_element_type(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<dev_dataset>",
    element_table="Image",
)

# 2. Create the development dataset
deriva_ml_create_dataset(
    hostname="data.example.org",
    catalog_id="1",
    description="Development subset: 100 chest X-rays, ~20 per diagnosis class, for pipeline validation",
    dataset_types=["Development"],
)

# 3. Add a representative sample of members
# Query to find records spanning all classes:
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<source>",
    include_tables=["Image", "Image_Diagnosis"],
    limit=200,
)
# Pick records that cover all classes, then:
deriva_ml_add_dataset_members(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<dev_dataset>",
    members=[...selected RIDs...],
)
```

### Create a "Development" dataset type

If your catalog doesn't have a "Development" type yet, use the generic `add_term` tool against the `Dataset_Type` vocabulary:

```
add_term(
    hostname="data.example.org",
    catalog_id="1",
    schema="deriva-ml",
    table="Dataset_Type",
    name="Development",
    description="Small representative subset used for pipeline development, debugging, and rapid iteration. Not for production training.",
    synonyms=["Dev", "Debug"],
)
```

### Pin to a released version

After populating the development subset (which will have flipped `current_version` to a dev label per ADR-0003), call `deriva_ml_release` to mint a citable release that configs can pin to:

```
deriva_ml_release(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<dev_dataset>",
    bump="minor",
    description="Initial development subset with balanced class representation",
)
```

Use `deriva_ml_get_dataset_spec(hostname="data.example.org", catalog_id="1", dataset_rid="<dev_dataset>")` to get the `DatasetSpecConfig` for your config files. Always pin configs to a released label (no `.devN` suffix) — dev labels are mutable.


## Phase 3: Validate Features and Labels

Before training, confirm the feature schema works with your development data.

**Inspection sequence:**
1. `deriva_ml_get_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="<feature_name>")` — confirm column structure (required vs optional)
2. `list_vocabulary_terms(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<vocab_name>")` — confirm valid term values
3. `deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="<feature_name>", selector="newest")` — check that labels exist for your dev records

**If labels are missing**, add them to the development dataset before training. Feature-value writes go through a bundled script template — copy `skills/create-feature/scripts/populate_feature_values.py` to `src/scripts/populate_diagnosis.py`, edit the target table and feature name, commit, then run:

```bash
uv run python src/scripts/populate_diagnosis.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Annotation \
    --csv ./labels/dev_diagnosis.csv \
    --target-table Image --feature-name Diagnosis
```

The template opens `with ml.create_execution(config, workflow=workflow) as exe:`, stages `exe.add_features(records)`, and `exe.commit_output_assets()` post-`with` flushes them to the catalog. Pydantic validates each row against the feature's term vocabulary, so mismatched terms fail loudly.

**Verify the full pipeline** by denormalizing:
```
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<dev_dataset>",
    include_tables=["Image", "Image_Diagnosis"],
    limit=20,
)
```
This shows you exactly what the training pipeline will see.


## Phase 4: Tier 1 — Dry Run

A dry run validates configuration without creating execution records or writing to the catalog.

### With the CLI
```bash
# Resolve and print the config without running
uv run deriva-ml-run +experiment=my_experiment --cfg job

# Dry run — downloads data but doesn't create execution records
uv run deriva-ml-run +experiment=my_experiment dry_run=true
```

### With the bundled script template

`skills/execution-lifecycle/scripts/basic_execution.py` exposes `--dry-run` as a top-level argparse flag — it builds the `ExecutionConfiguration` and opens `with ml.create_execution(config, workflow=workflow, dry_run=True)` so the runner validates inputs without creating execution records or committing outputs:

```bash
uv run python src/scripts/train_resnet50.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Training \
    --dry-run
```

For ad-hoc validation without writing a script, use `deriva_ml_validate_execution_configuration` (see Phase 5 pre-flight) — it's the metadata-only equivalent that doesn't pay the bag-download cost.

### What dry_run validates
- ✅ Config resolves without errors
- ✅ Dataset RIDs and versions exist (the runner calls `get_entities(...)` per candidate table internally)
- ✅ Asset RIDs exist and are downloadable
- ✅ Data loading code runs without errors
- ✅ Model initialization works
- ❌ Does NOT write execution records to the catalog
- ❌ Does NOT upload outputs

### Fix problems at this tier
Common tier 1 failures:
- Missing or wrong dataset RID/version → fix config
- Missing vocabulary terms → add terms before proceeding
- Import errors → fix code
- Config schema mismatch → fix config structure


## Phase 5: Tier 2 — Small-Data Run

Run a real execution against your development dataset. This creates catalog records and tests the full pipeline end-to-end.

### Pre-flight checklist
1. Validate the full config with `deriva_ml_validate_execution_configuration(hostname=..., catalog_id=..., config={...})` — one call confirms every dataset RID, every dataset version, every asset RID, the workflow, and surfaces cross-spec issues (duplicate RIDs, version conflicts, role conflicts). Cheap metadata-only pre-flight; doesn't pay the bag-download cost that `dry_run=True` does.
2. `deriva_ml_bag_info(hostname=..., catalog_id=..., dataset_rid="...", version="...")` — check cache status
3. `uv run python src/scripts/warm_cache.py --hostname ... --catalog-id ... --dataset-rid ... --version ...` — pre-fetch via the bundled `manage-storage` template if anything reads `not_cached`
4. Code committed and version bumped (`bump_version(bump_type="patch")`)

### Run with small data
```bash
# Point at your development dataset
uv run deriva-ml-run +experiment=my_experiment \
    datasets.training.rid=<dev_rid> \
    datasets.training.version=<dev_version> \
    model_config.epochs=3
```

### Verify outputs
After the run completes:
1. Check execution status — `deriva_ml_get_execution(hostname=..., catalog_id=..., execution_rid="...")`
2. Verify outputs were uploaded — call `deriva_ml_lookup_asset(hostname=..., catalog_id=..., asset_rid="...")` for each output asset (or `deriva_ml_find_workflow_executions(hostname=..., catalog_id=..., workflow_rid="...")` for the broader query).
3. Inspect output files — download and examine predictions, metrics, model weights
4. Check provenance chain — `deriva_ml_list_execution_children(hostname=..., catalog_id=..., execution_rid="...")` for descendants and `deriva_ml_list_execution_parents(hostname=..., catalog_id=..., execution_rid="...")` for ancestors.
5. **Compare against prior runs** — fetch the same feature across this run and the last few runs in one call: `deriva_ml_list_feature_values(hostname=..., catalog_id=..., target_table=..., feature_name=..., execution_rids=["<this_rid>", "<prev_rid_1>", "<prev_rid_2>"])`. The `execution_rids=` filter runs server-side, so it's one round trip instead of N. Detects regressions early. See `/deriva-ml:compare-model-runs` for the full ranking pattern.

### Fix problems at this tier
Common tier 2 failures:
- Data shape mismatches → fix data loading or preprocessing
- NaN/Inf in training → fix normalization or learning rate
- Output upload failures → fix asset_file_path registration
- Wrong number of classes → check vocabulary and feature values


## Phase 6: Tier 3 — Production Run

Only after tiers 1 and 2 succeed, scale to the full dataset.

### Create the production dataset

If you don't already have one, see the `dataset-lifecycle` skill for:
- Creating and populating the full dataset
- Splitting into train/val/test via a script that calls the Python API `split_dataset(ml, source_rid, exe, ...)`
- Stratifying by label distribution

### Pre-production checklist

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `deriva_ml_validate_execution_configuration(hostname=..., catalog_id=..., config={...})` | Confirms all dataset RIDs + versions exist, all asset RIDs exist, workflow is valid, no cross-spec conflicts — single metadata-only call (cheaper than dry_run, which downloads bags) |
| 2 | `deriva_ml_bag_info(hostname=..., catalog_id=..., dataset_rid=...)` | Check dataset sizes and cache status |
| 3 | `uv run python src/scripts/warm_cache.py --hostname ... --catalog-id ... --dataset-rid ...` | Pre-fetch large datasets via the `manage-storage` template |
| 4 | `uv run bump-version <type>` (or `bump_version("<type>")` MCP) | Tag the code version — see decision matrix below for `<type>` |
| 5 | `git status` | Confirm clean working tree |
| 6 | Verify experiment description | Will be recorded in execution |

**Choosing the version bump type:**

| Component | When to use | Examples |
|-----------|------|----------|
| **patch** | Bug fixes, small parameter tweaks | Fixed mislabeled records, tightened a loss function, adjusted a hyperparameter default |
| **minor** | New experiment configurations, new model architectures | Added a new model variant, added a new dataset split, new hydra-zen experiment preset |
| **major** | Breaking changes to the training pipeline or data format | Restructured the catalog schema, broke backwards compatibility with prior bag exports |

Commit the version bump before running. The git tag created by `bump-version` becomes the version recorded in the execution metadata.

### Run production
```bash
uv run deriva-ml-run +experiment=my_experiment
```

Or for hyperparameter sweeps:
```bash
uv run deriva-ml-run +multirun=lr_sweep
```

### After production run
1. Verify all child executions completed (for multiruns)
2. Check output assets exist and have expected sizes
3. Record the **execution RID** and a one-line characterization of what the
   run was for in `tacit-knowledge.md` (via the `capture-tacit-knowledge`
   skill). The execution RID is the durable anchor — assets, features, status,
   inputs, and the workflow's git commit hash all hang off it. Do not
   enumerate asset RIDs in the notes; they go stale and the catalog already
   has them linked to the execution.
4. **If the execution attached features to the dataset's members** (e.g.,
   ground-truth labels, curated annotations, derived attributes that future
   consumers should see), record the drift and mint a release. Per
   ADR-0003, feature drift is not auto-detected by the dataset-mutation
   tools — call `dataset.mark_dev(description)` from the Python API to
   declare a dev period (which flips `current_version` to a `.devN`
   label), then `deriva_ml_release(...)` to mint a release that captures
   the new feature values. See the `dataset-lifecycle` skill, Phase 4.

   Do NOT bump for runs whose outputs are **assets only** (model weights,
   training logs, prediction CSVs, plots). Execution-output assets are
   linked to the execution, not to the dataset's members; future consumers
   reach them through the execution RID, so the dataset doesn't need a new
   version.


## Phase 7: Iterate

ML development is iterative. After each production run:

1. **Analyze results** — use `deriva_ml_denormalize_dataset(hostname=..., catalog_id=..., dataset_rid=...)` or download the bag to examine predictions
2. **Identify improvements** — more data? Better labels? Different architecture?
3. **Go back to the appropriate tier:**
   - Config change only → Tier 1 (dry run)
   - New feature or data pipeline change → Tier 2 (small-data run)
   - Ready for next experiment → Tier 3 (production run)

**Never skip back to Tier 3** after a significant change. Always validate with tiers 1–2 first.

## Git workflow

Cross-cutting across all phases — applies whenever you're committing code that an execution will eventually run.

- **Use feature branches for all work** — `git checkout -b feature/add-segmentation-model`. Keep `main` clean and passing.
- **Use pull requests, even solo** — PRs create a permanent record of what changed and why. The PR description becomes part of the project's institutional memory alongside `tacit-knowledge.md`. With the [GitHub CLI (`gh`)](https://cli.github.com/) installed, Claude can create PRs, review diffs, and merge directly from the terminal.
- **Commit before running** — DerivaML enforces git-clean for executions (`DerivaMLDirtyWorkflowError`). Use `--allow-dirty` only for debugging iterations; the resulting execution has degraded provenance. See `/deriva-ml:execution-lifecycle` for the canonical commit-before-running discipline.

## Extending DerivaML

If you need project-specific helpers that wrap DerivaML behavior, prefer inheritance over modifying the library:

```python
from deriva_ml import DerivaML

class MyProjectML(DerivaML):
    """Extended DerivaML with project-specific helpers."""

    def load_training_data(self, dataset_rid: str) -> pd.DataFrame:
        ...
```

This keeps the project-specific logic in your repository (versioned, reviewable) while inheriting all of DerivaML's behavior. Avoid monkey-patching DerivaML methods at runtime — those changes don't show up in `git diff` and break debuggability.

## Quick Reference: Which Skill for What

| Task | Skill | Plugin |
|------|-------|--------|
| Design tables, columns, FKs | `/deriva:create-table` | deriva-skills |
| Load row data into tables (CSV/JSON, asset uploads via deriva-upload-cli) | `/deriva:load-data` | deriva-skills |
| Create vocabularies and terms | `/deriva:manage-vocabulary` | deriva-skills |
| Create features for annotations | `create-feature` | this plugin |
| Create/split/version datasets | `dataset-lifecycle` | this plugin |
| Run experiments with provenance | `execution-lifecycle` | this plugin |
| Upload/download/track assets | `work-with-assets` | this plugin |
| Restructure data for PyTorch/TF | `ml-data-engineering` | this plugin |
| Write hydra-zen configs | `configure-experiment`; `write-hydra-config` for syntax | this plugin |
| Run notebooks with tracking | `run-notebook` | this plugin |
| Document decisions | `capture-tacit-knowledge` | this plugin |
| **Iterate on an existing pipeline** (cycle 2 onward — once cycle zero, this skill, is done) | **`experiment-lifecycle`** | this plugin |
