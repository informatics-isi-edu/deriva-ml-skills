---
name: model-development-workflow
description: "ALWAYS use this skill when starting a new ML project, onboarding to an existing one, or asking about the recommended development workflow for DerivaML. Covers the end-to-end progression from schema design through production training: design schema → create small representative dataset → validate features → dry run → small-data run → full-scale production run. Teaches the three-tier development pattern (dry_run → small dataset → full dataset) that prevents wasting compute on broken configs. Triggers on: 'new ML project', 'getting started', 'development workflow', 'how should I develop', 'start small', 'representative dataset', 'development subset', 'dry run first', 'debug my training', 'iterate faster', 'what order should I do things', 'onboard to project', 'ML workflow', 'best practices for training'."
user-invocable: true
disable-model-invocation: true
---

# Model Development Workflow

This skill teaches the end-to-end development workflow for DerivaML projects. The core principle: **start small, validate early, scale up only after everything works.**

Most wasted compute comes from running full-scale training on broken configurations. This workflow catches problems at each tier before they become expensive.

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
- `/deriva:create-table` *(tier-1, deriva-skills)* — domain tables with columns and foreign keys
- `/deriva:manage-vocabulary` *(tier-1, deriva-skills)* — controlled vocabularies for categorical data
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

### Pin the version

```
deriva_ml_increment_dataset_version(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<dev_dataset>",
    description="Initial development subset with balanced class representation",
)
```

Use `deriva_ml_get_dataset_spec(hostname="data.example.org", catalog_id="1", dataset_rid="<dev_dataset>")` to get the `DatasetSpecConfig` for your config files.


## Phase 3: Validate Features and Labels

Before training, confirm the feature schema works with your development data.

**Inspection sequence:**
1. `deriva_ml_get_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="<feature_name>")` — confirm column structure (required vs optional)
2. `list_vocabulary_terms(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<vocab_name>")` — confirm valid term values
3. `deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="<feature_name>", selector="newest")` — check that labels exist for your dev records

**If labels are missing**, add them to the development dataset first. The legacy `start_execution` / `stop_execution` pair was split — create+start, then commit on success or abort on failure:

```
deriva_ml_create_execution(
    hostname="data.example.org",
    catalog_id="1",
    workflow_rid="<workflow_rid>",
    description="Dev labeling annotation run",
)
deriva_ml_start_execution(hostname="data.example.org", catalog_id="1", execution_rid="<exec_rid>")
deriva_ml_add_feature_values(
    hostname="data.example.org",
    catalog_id="1",
    target_table="Image",
    feature_name="Diagnosis",
    values=[{"target_rid": "...", "value": "Normal"}, ...],
)
deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="<exec_rid>")
```

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

### With MCP tools
```
deriva_ml_create_execution(
    hostname="data.example.org",
    catalog_id="1",
    workflow_rid="<workflow_rid>",
    dataset_rids=["<dev_dataset_rid>"],
    dry_run=True,
)
```

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
3. `deriva_ml_cache_dataset(hostname=..., catalog_id=..., dataset_rid="...", version="...")` — pre-fetch if needed
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
- Splitting into train/val/test with `deriva_ml_split_dataset(hostname=..., catalog_id=..., dataset_rid=..., ...)`
- Stratifying by label distribution

### Pre-production checklist

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `deriva_ml_validate_execution_configuration(hostname=..., catalog_id=..., config={...})` | Confirms all dataset RIDs + versions exist, all asset RIDs exist, workflow is valid, no cross-spec conflicts — single metadata-only call (cheaper than dry_run, which downloads bags) |
| 2 | `deriva_ml_bag_info(hostname=..., catalog_id=..., dataset_rid=...)` | Check dataset sizes and cache status |
| 3 | `deriva_ml_cache_dataset(hostname=..., catalog_id=..., dataset_rid=...)` | Pre-fetch large datasets |
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
3. Record results in experiment notes (`maintain-experiment-notes` skill)
4. Consider bumping the dataset version if you'll modify data next


## Phase 7: Iterate

ML development is iterative. After each production run:

1. **Analyze results** — use `deriva_ml_denormalize_dataset(hostname=..., catalog_id=..., dataset_rid=...)` (renamed from the legacy `preview_denormalized_dataset`) or download the bag to examine predictions
2. **Identify improvements** — more data? Better labels? Different architecture?
3. **Go back to the appropriate tier:**
   - Config change only → Tier 1 (dry run)
   - New feature or data pipeline change → Tier 2 (small-data run)
   - Ready for next experiment → Tier 3 (production run)

**Never skip back to Tier 3** after a significant change. Always validate with tiers 1–2 first.

## Git workflow

Cross-cutting across all phases — applies whenever you're committing code that an execution will eventually run.

- **Use feature branches for all work** — `git checkout -b feature/add-segmentation-model`. Keep `main` clean and passing.
- **Use pull requests, even solo** — PRs create a permanent record of what changed and why. The PR description becomes part of the project's institutional memory alongside `experiment-decisions.md`. With the [GitHub CLI (`gh`)](https://cli.github.com/) installed, Claude can create PRs, review diffs, and merge directly from the terminal.
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
| Design tables, columns, FKs | `/deriva:create-table` | tier-1 (deriva-skills) |
| Load row data into tables (CSV/JSON, asset uploads via deriva-upload-cli) | `/deriva:load-data` | tier-1 (deriva-skills) |
| Create vocabularies and terms | `/deriva:manage-vocabulary` | tier-1 (deriva-skills) |
| Create features for annotations | `create-feature` | this plugin |
| Create/split/version datasets | `dataset-lifecycle` | this plugin |
| Run experiments with provenance | `execution-lifecycle` | this plugin |
| Upload/download/track assets | `work-with-assets` | this plugin |
| Restructure data for PyTorch/TF | `ml-data-engineering` |
| Write hydra-zen configs | `configure-experiment`; `write-hydra-config` for syntax |
| Run notebooks with tracking | `run-notebook` |
| Document decisions | `maintain-experiment-notes` |
