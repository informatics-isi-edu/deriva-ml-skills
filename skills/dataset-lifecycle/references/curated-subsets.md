# Curated Subsets Workflow

When the user wants a dataset derived from an **existing dataset** — whether filtered by data values (e.g., "only labeled images", "just cats and dogs"), by numeric thresholds (e.g., "confidence > 0.8"), or by random sampling (e.g., "100 random images for dev") — follow this workflow. This requires a source dataset to download a bag from. If no dataset exists yet, use the bootstrap workflow in `workflow.md` instead.

Curated subsets run through `deriva-ml-run` using the `script_config` hydra group, giving them the same provenance tracking as model training.

## Two data paths

Filters declare `requires_data` to select the right path:

| `requires_data` | Path | When to use | Speed |
|-----------------|------|-------------|-------|
| `False` | Member-list path: `deriva_ml_list_dataset_members()` → filter RIDs | Random sample, all records, any RID-only filter | Fast (catalog query) |
| `True` | Bag-download path: `download_dataset_bag()` → denormalize → filter on values | Filter by column values (genotype, label, score) | Slower (bag export + FK traversal) |

**Always prefer `requires_data=False`** when the filter doesn't need data values. This avoids bag download, FK path timeouts, and server load.

## REQUIRED: Read templates first

**Before proposing any approach**, read the template files in this skill's `scripts/` directory:

- `scripts/generate_subset_template.py` — the template for generation functions
- `scripts/subset_filters.py` — the filter registry with built-in filters

Do NOT propose standalone scripts, custom solutions, or MCP-tool-only approaches without first understanding what the template provides. The template workflow is the prescribed approach.

## Scaffolding check

Before generating anything, verify the project has the required infrastructure. If any piece is missing, create it — this handles both first-time setup and subsequent subset scripts.

1. **Filter registry** — Check if `src/scripts/subset_filters.py` exists. If not, copy it from this skill's `scripts/subset_filters.py`. This provides built-in filters with `requires_data` metadata: `random_sample` (False), `all_records` (False), `has_feature` (True), `feature_equals` (True), `feature_in` (True), `numeric_range` (True).

2. **Config file** — Check if `src/configs/dataset_generation.py` exists. If not, create it with `script_store = store(group="script_config")` and a `script_store(None, name="none")` placeholder.

3. **Workflow config** — Check if `DatasetGenerationWorkflow` exists in `src/configs/workflow.py`. If not, add it with `workflow_type="Dataset_Generation"` and register as `name="dataset_generation"`.

4. **Base config** — Check if `script_config` appears in the hydra_defaults list in `src/configs/base.py` (or `model.py`). If not, add `{"optional script_config": "none"}` to the defaults.

5. **Workflow types** — Check if `Dataset_Generation` exists in the catalog's `Workflow_Type` vocabulary. If not, add it via `add_term(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Workflow_Type", name="Dataset_Generation", description="...")`.

## Subset workflow

### Step 1: Identify the filter type

Determine what the user wants. Random sample / all records → `requires_data=False` (no preview needed). Filter by data values → `requires_data=True` (preview data shape first).

For `requires_data=True` only, use `deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=[...])` to see the schema shape (columns, join path, row counts), then add `dataset_rid` and `limit=10` to preview actual data values and distributions.

### Step 2: Discuss criteria with the user

Based on the preview, confirm what filter they want. Common patterns:

- "100 random images for dev" → `random_sample` with n and seed params (`requires_data=False`)
- "All records in the dataset" → `all_records` (`requires_data=False`)
- "Give me all labeled images" → `has_feature` on the label column (`requires_data=True`)
- "Only cat images" → `feature_equals` with column + value (`requires_data=True`)
- "Cats and dogs" → `feature_in` with column + value list (`requires_data=True`)
- "High confidence predictions" → `numeric_range` on confidence column (`requires_data=True`)
- Something complex → generate a custom filter function and register it with the appropriate `requires_data` flag

### Step 3: Generate the script function

Read `scripts/generate_subset_template.py` and fill in the placeholders (`{{FUNCTION_NAME}}`, `{{EXPERIMENT_NAME}}`). Write to `src/scripts/generate_<name>.py`.

**IMPORTANT — Verify API calls.** Before writing the script, verify every DerivaML API call against the actual library. The template's docstring lists verified signatures. Common pitfalls:

- `list_dataset_members()` returns `dict[str, list[dict]]` keyed by table name — no positional table filter arg
- `pathBuilder()` is a method (needs `()`), not a property
- Dataset has no `add_child` method — use `pathBuilder().schemas["deriva-ml"].tables["Dataset_Dataset"].insert()`, or via MCP add the child as a member of element-type Dataset: `deriva_ml_add_dataset_members(parent_rid, members={"Dataset": [child_rid]})`
- `add_dataset_members(members=rids)` takes a list of RIDs or `{table: [rids]}` dict

If the user needs a custom filter not in the built-in registry, write the filter function in the same file and register it with `@register_filter("name", requires_data=True/False)`.

### Step 4: Generate config + experiment

Add a named config to `src/configs/dataset_generation.py` using `builds(generate_function, ...)` with the filter name, params, source dataset RIDs, and output metadata. For `requires_data=True` filters, include `include_tables` and `exclude_tables` (to avoid FK path timeouts on large catalogs). Also register a `script_store(None, name="none")` placeholder if one doesn't exist. Add an experiment entry to `src/configs/experiments.py` with `script_config=MISSING` (from `hydra_zen`) to force Hydra to fill it from the defaults list rather than inheriting `None` from the base config.

### Step 5: Dry run

Run `uv run deriva-ml-run +experiment=<name> dry_run=true`. Show the user the output (selected count, filter description) and wait for approval.

### Step 6: Commit

The script must be committed before running for real. DerivaML raises `DerivaMLDirtyWorkflowError` if uncommitted changes exist. Use `--allow-dirty` only for debugging iterations (degraded provenance).

### Step 7: Run for real

After approval: `uv run deriva-ml-run +experiment=<name>`

### Step 8: Log the decision

Use the `capture-tacit-knowledge` skill to record what was created, the filter criteria, why those criteria were chosen, and the resulting dataset RID.

## How this relates to `split_dataset` and `subsample`

Splitting, subsampling, and curated subsets are all "given a source dataset, produce one or more derived datasets" — but they differ in shape and intent:

| Operation | Output cardinality | Member selection | Use when |
|-----------|--------------------|------------------|----------|
| **`split_dataset(ml, source_rid, exe, ...)`** | Two or three children (train/test, optionally val) + a parent Split | ALL source members partitioned into non-overlapping subsets, by random / stratified / predicate (`selection_fn`) | You need train/test/val partitions of an existing dataset |
| **`subsample(ml, source_rid, exe, size=, ...)`** | One output dataset | Stratified random sample, no partitioning. Caller specifies size; output is a strict subset of the source's members | You need a smaller variant of a single dataset (rapid dev iteration, baseline runs, debugging) |
| **Curated subsets** *(this skill)* | One output dataset | SELECT by data values via a filter — some members excluded entirely based on predicates | You need a focused subset where the membership criterion is *what the data is*, not *how many* (e.g., "only labeled images of class X") |

Three quick disambiguations:

- **"Stratified subset"** could mean either `subsample` (single output, samples in proportion to a stratify column) or curated subsets with a stratified filter. Default to `subsample` when the goal is "smaller, in proportion"; default to curated subsets when the goal is "filter by attribute, then maybe partition further."
- **"Train/test split, but only labeled rows"** is a *filter then split* — see "Filter-then-split" in this file, or pass `stratify_missing="drop"` to `split_dataset` if the labeled-ness is encoded as null/non-null on the stratify column.
- **"Smaller mirror of an existing Split"** is `subsample` called once per child of the Split (Training and Testing each subsampled separately), not a single operation. There is intentionally no `subsample_split` primitive in deriva-ml.

All three produce datasets with full provenance tracking. Bags downloaded with `materialize=False` are cached by checksum, so multiple derived datasets from the same source don't re-download data.

## Reading feature values with `feature_values()`

When filtering by a single feature (e.g., "images with label X"), downloading a full bag just to read labels is overkill. The subset template supports a **catalog-query path** that uses `ml.feature_values()` to fetch feature values directly from the catalog:

```python
import pandas as pd
from deriva_ml.feature import FeatureRecord

records = ml.feature_values(
    "Image",                           # element table
    "Image_Classification",            # feature name
    selector=FeatureRecord.select_newest,
)
# Materialize as a DataFrame if your filter logic prefers tabular access:
feature_df = pd.DataFrame.from_records(r.model_dump() for r in records)
```

`feature_values()` returns an iterable of `FeatureRecord` objects. If your filter only needs a few columns, iterate directly; if you want pandas joins / boolean indexing, materialize into a DataFrame as shown above. For large feature sets, pass `materialize_limit=...` to cap how many records are pulled into memory before the call raises `DerivaMLMaterializeLimitExceeded`.

### When to use each path

| Situation | Path | Set `feature_name` in config? |
|-----------|------|:-----------------------------:|
| Filtering by a single feature column | Catalog-query (`feature_values()`) | Yes |
| Need columns from multiple joined tables | Bag | No |
| Iterating on filter criteria interactively | Catalog-query (`feature_values()`) | Yes |

### Re-running across iterations

Each `feature_values()` call hits the catalog. For interactive filter iteration, materialize the DataFrame once at the top of the script and reuse it across subsequent filter steps within the same session. To re-fetch after a feature value update, just call `feature_values()` again — there is no separate cache to invalidate.
