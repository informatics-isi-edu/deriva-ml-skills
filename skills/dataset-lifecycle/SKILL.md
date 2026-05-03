---
name: dataset-lifecycle
description: "Use this skill for ALL DerivaML dataset operations — creating, populating, splitting, versioning, browsing, and downloading datasets. Covers: creating datasets and adding members, train/test/validation splits (stratified, labeled, dry run), dataset version management after catalog changes, choosing and designing dataset types (orthogonal tagging), exploring and browsing dataset contents by element type using deriva_ml_denormalize_dataset, navigating parent/child hierarchies, downloading BDBags (timeouts, exclude_tables, deriva_ml_bag_info), restructuring assets for ML frameworks, and referencing datasets in experiment configs via DatasetSpecConfig. Also covers preparing datasets specifically for model training — stratified splits by label distribution, setting up training/validation/testing partitions, and creating explicit split datasets in the catalog rather than computing on the fly. Triggers on: 'create a dataset', 'split dataset', 'stratify', 'train test split', 'prepare data for model', 'dataset version', 'what is in this dataset', 'browse dataset', 'wide table', 'flat table', 'denormalize', 'dataset types', 'element types', 'BDBag download', 'DatasetSpecConfig', 'add members', 'list members', 'dataset children', 'training data setup', 'curated subset', 'filter dataset', 'subset by class', 'select by value', 'create labeled dataset', 'filter by feature', 'subset with labels', 'has feature', 'images with labels', 'records that have', 'build dataset from'. Do NOT use for: creating features/labels (use create-feature), creating tables (use create-table), running experiments (use execution-lifecycle), uploading assets (use work-with-assets), or managing vocabularies (use manage-vocabulary)."
---

# Dataset Lifecycle

This skill covers the full lifecycle of a DerivaML dataset: assessing whether one is needed, planning its structure and types, creating and populating it, versioning for reproducibility, and consuming it in experiments.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

**Check project context first.** Before running any commands, look for catalog references in the project:
- `experiment-decisions.md` — records which catalog/hostname previous operations used
- `src/configs/deriva.py` — hydra-zen connection configs with hostname and catalog_id
- `CLAUDE.md` — may specify the working catalog

Use the catalog the project is actively working with, NOT the original source catalog (e.g., use the clone on dev.facebase.org, not the source on www.facebase.org).

If you don't know the catalog ID, read `deriva://registry/{hostname}` to see available catalogs and aliases.

## Phase 1: Assess

Before creating a dataset, determine whether an existing one can be reused, extended, or split. The find-before-you-create discipline is carried by `/deriva:semantic-awareness` *(tier-1, deriva-skills, auto-fires)* — its synonym/abbreviation/spelling-variant search expansion applies to ML entities (Datasets) as well as generic catalog entities. The same skill covers the EAV-vs-wide-table dual extreme, which is worth knowing when designing the *element-type* tables a dataset will draw members from.

1. **Search existing datasets.** Use `rag_search("your purpose", doc_type="catalog-data")` to find datasets by description, type, or purpose. Fall back to `deriva_ml_list_datasets(hostname="data.example.org", catalog_id="1")` for the full structured list. Use `get_table_sample_data(hostname="data.example.org", catalog_id="1", schema="<schema>", table="Image")` to understand how much data is available.
2. **Check available element types.** Read `deriva://catalog/{h}/{c}/ml/registries` to see which tables can contribute members. If the table you need isn't registered, call `deriva_ml_add_dataset_element_type(hostname="data.example.org", catalog_id="1", element_table="Image")`.
3. **Decide: reuse, extend, or create.**

| Situation | Action |
|-----------|--------|
| Existing dataset covers your need | Reuse it — reference its RID + version in config |
| Existing dataset needs more members | `deriva_ml_add_dataset_members` to extend it |
| Need a different split of existing data | `deriva_ml_split_dataset` from the existing dataset |
| Need a focused subset for an experiment | Create a new dataset with selected member RIDs |
| Building from scratch | Create a new dataset |

## Phase 2: Plan

### Choose the dataset structure

| Pattern | When to use | How |
|---------|-------------|-----|
| Standalone | Building a new collection from scratch | `deriva_ml_create_dataset` |
| Split children | Need train/test/val partitions | `deriva_ml_split_dataset` from a parent |
| Curated subset | Focused set filtered by data values | Preview shape → generate script from template → run |
| Manual nesting | Grouping related datasets together | `deriva_ml_create_dataset` + `deriva_ml_add_dataset_members(parent_rid, [child_rid])` (children are members of element-type Dataset) |

### Choose dataset types

Types describe independent dimensions of a dataset — they are orthogonal tags, not a hierarchy. A dataset gets one or more tags from each relevant dimension.

**Built-in dimensions:**

| Dimension | Types | Mutually exclusive? |
|-----------|-------|:-------------------:|
| Partition role | `Training`, `Testing`, `Validation`, `Complete`, `Split` | Mostly yes |
| Annotation status | `Labeled`, `Unlabeled` | Yes |

**Guidelines:**
- Apply at least one type — untyped datasets are hard to discover
- Apply types from each relevant dimension — if the data has ground truth labels, add `Labeled`
- Types compose freely across dimensions — `Training` + `Labeled` + `Fundus` is three independent tags
- Don't compound dimensions — use `Training` + `Labeled`, never `TrainingLabeled`
- Check existing types first — use `rag_search("dataset types", doc_type="catalog-schema")` or `list_vocabulary_terms(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Dataset_Type")` for the full list

For DerivaML-specific guidance — what the built-in `Dataset_Type` terms mean, how multiple types compose on a single Dataset row, and worked examples for an imaging-domain catalog — see `references/type-naming-strategy.md`.

The **generic naming and design principles** that apply to all four DerivaML vocabularies (`Dataset_Type`, `Workflow_Type`, `Asset_Type`, `Execution_Status_Type`) and to any custom domain vocabulary live in two tier-1 skills in `deriva-skills`: `entity-naming` covers naming (PascalCase, singular form, descriptive, short, specific, FK column conventions); `manage-vocabulary/references/term-naming-strategy.md` covers vocabulary-term-specific design concerns (orthogonal tagging, dimension identification, term descriptions, synonyms, anti-patterns, the substitution test, semantic checking). Read both before adding terms to any DerivaML vocabulary.

For creating custom types, see `references/workflow.md` under "Managing Types."

## Phase 3: Create

**Default: use the script-based workflow** for any dataset creation that adds more than a handful of members. This ensures code provenance — every execution record links to a committed git hash. The MCP tool path is only for trivial cases (creating an empty dataset, adding 2-3 members manually).

### Choosing the right script path

There are two script-based approaches. Choose based on whether a source dataset already exists:

| Situation | Path | Template |
|-----------|------|----------|
| **No source dataset** — creating the first dataset from raw table data (bootstrap) | **Phase 3a: Bootstrap** | `catalog-operations-workflow` script patterns |
| **Source dataset exists** — filtering, subsetting, or selecting from an existing dataset | **Phase 3b: Curated Subsets** | `generate_subset_template.py` with filter registry |

The subset template (Phase 3b) requires downloading a bag from a source dataset. If no dataset exists yet (bootstrap case), use the standalone script pattern from Phase 3a instead.

### Phase 3a: Bootstrap dataset (no source dataset)

Use this when creating the **first dataset** from records already in the catalog — e.g., "create a dataset with all file records" or "create a dataset from all Image records." There is no existing dataset to filter from.

**Use the script patterns from the `catalog-operations-workflow` skill** (`references/script-patterns.md`), specifically the **Base Script Template** + **Dataset Creation** pattern.

1. **Register element types** (via MCP — idempotent, one-time setup):
   ```
   deriva_ml_add_dataset_element_type(hostname="data.example.org", catalog_id="1", element_table="Image")
   ```

2. **Generate a standalone script** in `src/scripts/` following the Base Script Template:
   - Accept `--hostname`, `--catalog-id`, `--schema`, `--workflow-type`, and `--dry-run` as CLI arguments
   - Connect via `DerivaML(hostname=..., catalog_id=...)`
   - **Ensure all vocabulary terms exist** before use — call `ml.add_term(vocab_table, term_name, description)` (Python API) or `add_term(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table=vocab_table, name=term_name, description=...)` (MCP tool) for `Workflow_Type`, `Dataset_Type`, and any other vocabularies the script references. Catalog clones often have empty vocabulary tables.
   - Query all RIDs using `list(ml.pathBuilder().schemas[schema].tables[table].entities())` — note `pathBuilder()` is a **method call**, and `entities()` returns a lazy iterator needing `list()`
   - Create a workflow and execution for provenance — create a workflow with `ml.create_workflow(name, workflow_type)`, then pass it via `ExecutionConfiguration(workflow=workflow)`, then call `ml.create_execution(config)` (or use the context manager `with ml.create_execution(config) as exe:`)
   - Create the dataset with `exe.create_dataset()`
   - Add members with `dataset.add_dataset_members({table: rids}, validate=False)` — use **dict form** with `validate=False` for large datasets to avoid expensive per-RID table resolution
   - **Do NOT add a CLI entry point** in `pyproject.toml`. These are one-time catalog operations, not reusable tools. Run with `uv run python src/scripts/<script>.py`.

3. **Test with `--dry-run`**, commit, then run for real.

4. **Split** (optional — use `dry_run=true` to preview first):
   ```
   deriva_ml_split_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="...", test_size=0.2, seed=42, dry_run=true)
   ```

### MCP tool path (trivial cases only)

For creating an empty dataset or adding a small number of known RIDs:

1. **Create a workflow and execution** for provenance tracking:
   ```
   deriva_ml_create_workflow(hostname="data.example.org", catalog_id="1", name="Dataset Curation", workflow_type="Dataset_Management", description="...")
   deriva_ml_create_execution(hostname="data.example.org", catalog_id="1", workflow_rid="<workflow_rid>", description="...")
   deriva_ml_start_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")
   ```

2. **Create the dataset** with types and a good description:
   ```
   deriva_ml_create_dataset(hostname="data.example.org", catalog_id="1", description="...", dataset_types=["Complete", "Labeled"])
   ```

3. **Add members and finalize:**
   ```
   deriva_ml_add_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="...", members={"Image": ["2-IMG1", "2-IMG2"]})
   deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")
   ```

Note: For large member lists, always pass members as a `{table: [rids]}` dict (the typed form) instead of a flat list to avoid expensive per-RID table resolution.

For complete MCP tool parameters and Python API examples, see `references/workflow.md`.

### Description guidance

Every dataset needs a description that explains its composition, purpose, and key characteristics.

**Good:** "500 CIFAR-10 images (50 per class), balanced across all 10 categories, for rapid iteration during development"

**Bad:** "Training data" or "My dataset" or empty

For split datasets, note the split strategy and rationale.

For description templates and quality guidelines, see the `/deriva-ml:generate-descriptions` skill (always-on; auto-loaded). It carries the Dataset, Workflow, Execution, Feature, Asset, Experiment, and multirun templates.

### Why render splits explicitly in the catalog

**Always create explicit split datasets** (Training, Validation, Testing) and store them as children of the source dataset in the catalog. Don't compute splits on the fly each time you run an experiment.

| Approach | Problem |
|----------|---------|
| Split on the fly each run | Different random seeds → different splits → non-reproducible results. No record of which images were in which split |
| Explicit split datasets in catalog | Fixed, versioned, shareable. Every experiment references the same split by RID + version. Results are reproducible across team members |

The recommended pattern:
1. Create the source dataset with all data
2. `deriva_ml_split_dataset` to create explicit Training/Validation/Testing children
3. Reference the split datasets by RID + version in experiment configs (`DatasetSpecConfig`)
4. All team members use the same splits — results are comparable

This is especially important for stratified splits — recomputing a stratified split each time may produce different partitions if the underlying data changes.

## Phase 3b: Curated Subsets (source dataset exists)

When the user wants a dataset derived from an **existing dataset** — whether filtered by data values (e.g., "only labeled images", "just cats and dogs"), by numeric thresholds (e.g., "confidence > 0.8"), or by random sampling (e.g., "100 random images for dev") — follow this workflow. This requires a source dataset to download a bag from — if no dataset exists yet, use **Phase 3a: Bootstrap** instead.

Curated subsets run through `deriva-ml-run` using the `script_config` hydra group, giving them the same provenance tracking as model training.

### Two data paths

Filters declare `requires_data` to select the right path:

| `requires_data` | Path | When to use | Speed |
|-----------------|------|-------------|-------|
| `False` | Member-list path: `deriva_ml_list_dataset_members()` → filter RIDs | Random sample, all records, any RID-only filter | Fast (catalog query) |
| `True` | Bag-download path: `download_dataset_bag()` → denormalize → filter on values | Filter by column values (genotype, label, score) | Slower (bag export + FK traversal) |

**Always prefer `requires_data=False`** when the filter doesn't need data values. This avoids bag download, FK path timeouts, and server load.

### REQUIRED: Read templates first

**Before proposing any approach**, read the template files in this skill's `scripts/` directory:
- `scripts/generate_subset_template.py` — the template for generation functions
- `scripts/subset_filters.py` — the filter registry with built-in filters

Do NOT propose standalone scripts, custom solutions, or MCP-tool-only approaches without first understanding what the template provides. The template workflow is the prescribed approach.

### Scaffolding check

Before generating anything, verify the project has the required infrastructure. If any piece is missing, create it — this handles both first-time setup and subsequent subset scripts.

1. **Filter registry** — Check if `src/scripts/subset_filters.py` exists. If not, copy it from this skill's `scripts/subset_filters.py`. This provides built-in filters with `requires_data` metadata: `random_sample` (False), `all_records` (False), `has_feature` (True), `feature_equals` (True), `feature_in` (True), `numeric_range` (True).

2. **Config file** — Check if `src/configs/dataset_generation.py` exists. If not, create it with `script_store = store(group="script_config")` and a `script_store(None, name="none")` placeholder.

3. **Workflow config** — Check if `DatasetGenerationWorkflow` exists in `src/configs/workflow.py`. If not, add it with `workflow_type="Dataset_Generation"` and register as `name="dataset_generation"`.

4. **Base config** — Check if `script_config` appears in the hydra_defaults list in `src/configs/base.py` (or `model.py`). If not, add `{"optional script_config": "none"}` to the defaults.

5. **Workflow types** — Check if `Dataset_Generation` exists in the catalog's `Workflow_Type` vocabulary. If not, add it via `add_term(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Workflow_Type", name="Dataset_Generation", description="...")`.

### Subset workflow

**Step 1: Identify the filter type.** Determine what the user wants: Random sample/all records → `requires_data=False` (no preview needed). Filter by data values → `requires_data=True` (preview data shape first). For `requires_data=True` only, use `deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=[...])` to see the schema shape (columns, join path, row counts), then add `dataset_rid` and `limit=10` to preview actual data values and distributions.

**Step 2: Discuss criteria with the user.** Based on the preview, confirm what filter they want. Common patterns:
- "100 random images for dev" → `random_sample` with n and seed params (`requires_data=False`)
- "All records in the dataset" → `all_records` (`requires_data=False`)
- "Give me all labeled images" → `has_feature` on the label column (`requires_data=True`)
- "Only cat images" → `feature_equals` with column + value (`requires_data=True`)
- "Cats and dogs" → `feature_in` with column + value list (`requires_data=True`)
- "High confidence predictions" → `numeric_range` on confidence column (`requires_data=True`)
- Something complex → generate a custom filter function and register it with the appropriate `requires_data` flag

**Step 3: Generate the script function.** Read `scripts/generate_subset_template.py` and fill in the placeholders (`{{FUNCTION_NAME}}`, `{{EXPERIMENT_NAME}}`). Write to `src/scripts/generate_<name>.py`.

**IMPORTANT — Verify API calls.** Before writing the script, verify every DerivaML API call against the actual library. The template's docstring lists verified signatures. Common pitfalls:
- `list_dataset_members()` returns `dict[str, list[dict]]` keyed by table name — no positional table filter arg
- `pathBuilder()` is a method (needs `()`), not a property
- Dataset has no `add_child` method — use `pathBuilder().schemas["deriva-ml"].tables["Dataset_Dataset"].insert()`, or via MCP add the child as a member of element-type Dataset: `deriva_ml_add_dataset_members(parent_rid, members={"Dataset": [child_rid]})`
- `add_dataset_members(members=rids)` takes a list of RIDs or `{table: [rids]}` dict

If the user needs a custom filter not in the built-in registry, write the filter function in the same file and register it with `@register_filter("name", requires_data=True/False)`.

**Step 4: Generate config + experiment.** Add a named config to `src/configs/dataset_generation.py` using `builds(generate_function, ...)` with the filter name, params, source dataset RIDs, and output metadata. For `requires_data=True` filters, include `include_tables` and `exclude_tables` (to avoid FK path timeouts on large catalogs). Also register a `script_store(None, name="none")` placeholder if one doesn't exist. Add an experiment entry to `src/configs/experiments.py` with `script_config=MISSING` (from `hydra_zen`) to force Hydra to fill it from the defaults list rather than inheriting `None` from the base config.

**Step 5: Dry run.** Run `uv run deriva-ml-run +experiment=<name> dry_run=true`. Show the user the output (selected count, filter description) and wait for approval.

**Step 6: Commit.** The script must be committed before running for real. DerivaML raises `DerivaMLDirtyWorkflowError` if uncommitted changes exist. Use `--allow-dirty` only for debugging iterations (degraded provenance).

**Step 7: Run for real.** After approval: `uv run deriva-ml-run +experiment=<name>`

**Step 8: Log the decision.** Use the `maintain-experiment-notes` skill to record what was created, the filter criteria, why those criteria were chosen, and the resulting dataset RID.

### How this relates to deriva_ml_split_dataset

Splitting and curated subsets are both "given a source dataset, produce child datasets" — but they differ:
- **deriva_ml_split_dataset** partitions ALL members into non-overlapping train/test/val sets
- **Curated subsets** SELECT members by data values — some members may be excluded entirely

Both produce datasets with full provenance tracking. Bags downloaded with `materialize=False` are cached by checksum, so multiple subset scripts from the same source don't re-download data.

### Caching feature values with `cache_features()`

When filtering by a single feature (e.g., "images with label X"), downloading a full bag just to read labels is overkill. The subset template supports a **catalog-query path** that uses `cache_features()` to fetch feature values directly from the catalog into SQLite-backed working data:

```python
from deriva_ml.feature import FeatureRecord

feature_df = ml.cache_features(
    "Image",                           # element table
    "Image_Classification",            # feature name
    selector=FeatureRecord.select_newest,
)
```

**When to use each path:**

| Situation | Path | Set `feature_name` in config? |
|-----------|------|:-----------------------------:|
| Filtering by a single feature column | Catalog-query | Yes |
| Need columns from multiple joined tables | Bag | No |
| Iterating on filter criteria interactively | Catalog-query | Yes |

**Caching behavior:**
- The first call to `cache_features()` fetches from the catalog and stores locally. Subsequent calls within the same script return the cached data instantly.
- The cache persists across multiple filter iterations, making it efficient to experiment with different filter thresholds or value lists without re-querying.
- Use `force=True` if feature values may have changed since the last cache (e.g., new labels were added between runs).
- **Cache key limitation:** The cache key is `features_{table}_{feature}` and does NOT include the selector. Always use the same selector for a given table/feature pair within a session. Use `force=True` if you need to switch selectors.

## Phase 4: Version

Versioning is essential for reproducible experiments. Every version is a frozen snapshot of the catalog state at the time it was created.

### Rules

1. **Always use explicit versions for real experiments.** `DatasetSpecConfig(rid="28EA", version="0.4.0")` — never omit the version or use "current" except for debugging.
2. **Increment after catalog changes.** Adding features, fixing labels, adding assets — none of these are visible in existing versions until you call `deriva_ml_increment_dataset_version`.
3. **Always provide a version description.** Explain what changed, why, and the impact.
4. **Update configs immediately, commit before running.** The git hash in the execution record must match the config state.

### Semantic versioning

| Component | When | Examples |
|-----------|------|----------|
| **Major** | Breaking/schema changes | Columns added/removed, restructured tables |
| **Minor** | New data or features | Members added, new annotations, split created |
| **Patch** | Bug fixes, corrections | Fixed mislabeled records, metadata typos |

### Pre-experiment checklist

- [ ] Version explicitly specified (not "current")
- [ ] Config updated with correct version
- [ ] Config committed to git

For the full versioning rules, common mistakes, and version history API, see `references/concepts.md` under "Dataset Versioning."

## Phase 5: Use

Once a dataset is created and versioned, there are several ways to consume it.

### Browse in Chaise

Every dataset has a page in the Chaise web UI. Generate a shareable URL:
```
cite(hostname="data.example.org", catalog_id="1", rid="1-ABC4")              # permanent snapshot URL
cite(hostname="data.example.org", catalog_id="1", rid="1-ABC4", current=true) # live URL
```

### Reference in experiment configs

The standard way to use a dataset in an ML experiment is through `DatasetSpecConfig` in a Hydra-zen config:

```python
DatasetSpecConfig(rid="28EA", version="0.4.0")
```

Use the `deriva_ml_get_dataset_spec` MCP tool to generate the correct string. See the `configure-experiment` and `write-hydra-config` skills for how dataset configs integrate into experiment configurations.

### Explore and browse contents

Understand what's in a dataset using MCP tools (no browser needed):

**Step 1: Get the overview** — types, version, description, member counts:
```
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")
```

**Step 2: See what's inside** — members are returned grouped by element type (table). This tells you which tables have data in this dataset:
```
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")
```
Pass `version` and/or `recurse` as parameters when needed (e.g., `version="1.0.0"`, `recurse=true`).

**Step 3: Explore schema shape** — see what columns a denormalized join would produce, plus row counts and asset sizes:
```
deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=["Image", "Subject"])
```
Returns columns, join path, and per-table row counts/asset sizes. Use this to debug FK path errors or find the right column name for stratification.

**Step 4: Browse actual data** — add `dataset_rid` and `limit` to see real values. Include related tables to see joined data (e.g., an Image's Subject metadata, or feature annotations):
```
# See Image data joined with Subject metadata
deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=["Image", "Subject"], dataset_rid="...", limit=10)

# See Images with their classification labels
deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=["Image", "Image_Classification"], dataset_rid="...", limit=10)
```

**Important:** `deriva_ml_denormalize_dataset` is a preview only — results are not cached or stored. It returns a small sample (max 100 rows) to help you understand the data shape, column names, and relationships.

Once you understand the shape and decide on your filter criteria, use the DerivaML Python API to access the full dataset for building subsets or ML pipelines.

**Step 5: Check features and labels** — see what annotations exist on member records:
```
deriva_ml_list_features(hostname="data.example.org", catalog_id="1", target_table="Image")
```

**Step 6: Navigate the hierarchy** — check both parent and child datasets:
```
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")              # includes children list
deriva_ml_list_dataset_relations(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")  # both parents AND children in one call
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", recurse=true)   # full tree
```

> Note: the legacy `list_dataset_parents` tool was renamed/generalized to `deriva_ml_list_dataset_relations`, which returns both directions in a single response.

**Step 7: Check provenance and validate:**
```
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")              # includes execution provenance
# Python API: bag inspection for integrity checks
```

For individual records, use `get_entities(hostname="data.example.org", catalog_id="1", schema="<schema>", table="Image", filter={"RID": "2-IMG1"})`.

Alternatively, browse in the Chaise web UI — use `cite(hostname=..., catalog_id=..., rid="...")` to generate a URL.

### Download as BDBag

For production pipelines and reproducible experiments:

```
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="...", version="1.0.0")  # preview first (size + manifest)
# Python API: dataset.download_dataset_bag(dataset_rid="...", version="1.0.0")
```

For slow downloads, increase the timeout or exclude tables:
```
# Python API: dataset.download_dataset_bag(dataset_rid="...", version="1.0.0", timeout=[10, 1800])
# Python API: dataset.download_dataset_bag(dataset_rid="...", version="1.0.0", exclude_tables=["Study"])
```

### Restructure for ML frameworks

After downloading, organize files for PyTorch ImageFolder or similar (Python API on the downloaded bag):
```python
bag.restructure_assets(
    output_dir="./ml_data",
    asset_table="Image",
    group_by=["Diagnosis"],
)
```

## Reference Resources

- `scripts/subset_filters.py` — Filter registry with built-in filters (has_feature, feature_equals, feature_in, numeric_range). Copy to user's `src/scripts/` on first use.
- `scripts/generate_subset_template.py` — Template for generated dataset scripts. Fill in placeholders per use case.
- `references/concepts.md` — Full background: what datasets are, types, element types, versioning, navigation, consumption, bag downloads
- `references/workflow.md` — Step-by-step MCP and Python API examples for every operation
- `references/bags.md` — BDBag contents, FK traversal, materialization, caching, timeouts
- `references/type-naming-strategy.md` — DerivaML-specific: built-in `Dataset_Type` dimensions, composing multiple types on a Dataset, worked imaging-domain examples. (Generic vocabulary design principles live in tier-1 `deriva-skills` at `skills/manage-vocabulary/references/term-naming-strategy.md`.)
- `rag_search("...", doc_type="catalog-data")` — Discover datasets by description, type, or purpose
- `deriva_ml_list_datasets(hostname, catalog_id)` — Full structured list of all datasets (preferred over the URI form)
- `deriva://catalog/{h}/{c}/ml/datasets` — Same content via resource URI
- `rag_search("...", doc_type="catalog-schema")` — Find dataset types by meaning
- `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)` — Dataset details including current version
- `deriva://catalog/{h}/{c}/ml/registries` — Element types, dataset types, and other ML registries
- `deriva://docs/datasets` — Full user guide to datasets in DerivaML

## Related Skills

- **`ml-data-engineering`** — Restructuring assets for PyTorch/TensorFlow, building training DataFrames, DatasetBag API, value selectors
- **`debug-bag-contents`** — Diagnosing missing data, FK traversal issues, and export problems in dataset bags
- **`create-feature`** — Creating features and adding labels/annotations to records in datasets
- **`configure-experiment`** — Setting up Hydra-zen configs that reference datasets
- **`execution-lifecycle`** — Running experiments that consume datasets with provenance tracking
- **`catalog-operations-workflow`** — Writing Python scripts for batch dataset operations with code provenance
