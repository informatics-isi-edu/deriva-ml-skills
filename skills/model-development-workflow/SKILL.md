---
name: model-development-workflow
description: "ALWAYS use this skill when starting a new ML project, onboarding to an existing one, or asking about the recommended development workflow for DerivaML. Covers the end-to-end progression from schema design through production training: design schema → create small representative dataset → validate features → dry run → small-data run → full-scale production run. Teaches the three-tier development pattern (dry_run → small dataset → full dataset) that prevents wasting compute on broken configs. Triggers on: 'new ML project', 'getting started', 'development workflow', 'how should I develop', 'start small', 'representative dataset', 'development subset', 'dry run first', 'debug my training', 'iterate faster', 'what order should I do things', 'onboard to project', 'ML workflow', 'best practices for training'."
user-invocable: true
disable-model-invocation: true
---

# Model Development Workflow

This skill teaches the end-to-end development workflow for DerivaML projects. The core principle: **start small, validate early, scale up only after everything works.**

Most wasted compute comes from running full-scale training on broken configurations. This workflow catches problems at each tier before they become expensive.

## Prerequisite: Connect to a Catalog

All operations require an active catalog connection:
```
connect_catalog(hostname="...", catalog_id="...")
```

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
# 1. Register the element type
add_dataset_element_type(table_name="Image")

# 2. Create the development dataset
create_dataset(
    description="Development subset: 100 chest X-rays, ~20 per diagnosis class, for pipeline validation",
    dataset_types=["Development"]
)

# 3. Add a representative sample of members
# Query to find records spanning all classes:
preview_denormalized_dataset(include_tables=["Image", "Image_Diagnosis"],
                    dataset_rid="<source>",
                    limit=200)
# Pick records that cover all classes, then:
add_dataset_members(dataset_rid="<dev_dataset>",
                    member_rids=[...selected RIDs...])
```

### Create a "Development" dataset type

If your catalog doesn't have a "Development" type yet:
```
create_dataset_type_term(
    type_name="Development",
    description="Small representative subset used for pipeline development, debugging, and rapid iteration. Not for production training.",
    synonyms=["Dev", "Debug"]
)
```

### Pin the version

```
increment_dataset_version(
    dataset_rid="<dev_dataset>",
    description="Initial development subset with balanced class representation"
)
```

Use `get_dataset_spec("<dev_dataset>")` to get the `DatasetSpecConfig` for your config files.


## Phase 3: Validate Features and Labels

Before training, confirm the feature schema works with your development data.

**Inspection sequence:**
1. Read `deriva://feature/Image/<feature_name>` — confirm column structure (required vs optional)
2. Read `deriva://vocabulary/<vocab_name>` — confirm valid term values
3. `resource deriva://table/{name}/features (table_name="Image", selector="newest")` — check that labels exist for your dev records

**If labels are missing**, add them to the development dataset first:
```
create_execution(workflow_name="Dev Labeling", workflow_type="Annotation")
start_execution()
add_feature_value(table_name="Image", feature_name="Diagnosis",
                  entries=[{"target_rid": "...", "value": "Normal"}, ...])
stop_execution()
```

**Verify the full pipeline** by denormalizing:
```
preview_denormalized_dataset(include_tables=["Image", "Image_Diagnosis"],
                    dataset_rid="<dev_dataset>",
                    limit=20)
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
create_execution(
    workflow_name="My Training",
    workflow_type="Training",
    dataset_rids=["<dev_dataset_rid>"],
    dry_run=True
)
```

### What dry_run validates
- ✅ Config resolves without errors
- ✅ Dataset RIDs and versions exist (`validate_rids` runs internally)
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
1. `validate_rids(dataset_rids=[...], asset_rids=[...])` — confirm all RIDs
2. `bag_info(dataset_rid="...", version="...")` — check cache status
3. `cache_dataset(dataset_rid="...", version="...")` — pre-fetch if needed
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
1. Check execution status — `get_execution_info()`
2. Verify outputs were uploaded — `list_asset_executions(asset_rid="...", asset_role="Output")`
3. Inspect output files — download and examine predictions, metrics, model weights
4. Check provenance chain — `list_nested_executions(execution_rid="...")`

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
- Splitting into train/val/test with `split_dataset`
- Stratifying by label distribution

### Pre-production checklist

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `validate_rids(...)` | All RIDs and versions exist |
| 2 | `bag_info(...)` | Check dataset sizes and cache status |
| 3 | `cache_dataset(...)` | Pre-fetch large datasets |
| 4 | `bump_version("minor")` | Tag the code version |
| 5 | `git status` | Confirm clean working tree |
| 6 | Verify experiment description | Will be recorded in execution |

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

1. **Analyze results** — use `preview_denormalized_dataset` or download the bag to examine predictions
2. **Identify improvements** — more data? Better labels? Different architecture?
3. **Go back to the appropriate tier:**
   - Config change only → Tier 1 (dry run)
   - New feature or data pipeline change → Tier 2 (small-data run)
   - Ready for next experiment → Tier 3 (production run)

**Never skip back to Tier 3** after a significant change. Always validate with tiers 1–2 first.


## Quick Reference: Which Skill for What

| Task | Skill | Plugin |
|------|-------|--------|
| Design tables, columns, FKs | `/deriva:create-table` via `/deriva:route-catalog-schema` | tier-1 (deriva-skills) |
| Create vocabularies and terms | `/deriva:manage-vocabulary` | tier-1 (deriva-skills) |
| Create features for annotations | `create-feature` | this plugin |
| Create/split/version datasets | `dataset-lifecycle` | this plugin |
| Run experiments with provenance | `execution-lifecycle` | this plugin |
| Upload/download/track assets | `work-with-assets` | this plugin |
| Restructure data for PyTorch/TF | `ml-data-engineering` via `route-run-workflows` |
| Write hydra-zen configs | `configure-experiment` via `route-run-workflows` |
| Run notebooks with tracking | `run-notebook` via `route-run-workflows` |
| Document decisions | `maintain-experiment-notes` |
