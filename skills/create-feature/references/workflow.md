# Feature Workflow Reference

Step-by-step MCP tool and Python API examples for creating and populating features. For background concepts (feature types, multivalued features, selection), see `concepts.md`.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Table of Contents

1. [Check Existing Features](#check-existing-features)
2. [Create a Vocabulary](#create-a-vocabulary-if-needed)
3. [Create the Feature](#create-the-feature)
4. [Add Feature Values](#add-feature-values) — MCP tools and Python API
5. [Query Feature Values](#query-feature-values) — Fetching and selecting
6. [Managing Features](#managing-features) — Delete, list
7. [Complete Example](#complete-example) — End-to-end MCP workflow
8. [Complete Example: Python API](#complete-example-python-api)

---

## Check Existing Features

Before creating a new feature, review what already exists.

- Call `deriva_ml_list_features(hostname="data.example.org", catalog_id="1")` to list all features with their target tables and column schemas.
- Call `deriva_ml_get_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis")` for details on a specific feature.
- Check existing feature values with `deriva_ml_list_feature_values(hostname=..., catalog_id=..., target_table="Image", selector="newest")` to see what annotations already exist.

## Create a Vocabulary (if needed)

If your feature needs a new set of terms, create the vocabulary first.

**Prefer `deriva_ml_create_vocabulary` over the generic `create_vocabulary`** on any catalog with the deriva-ml schema installed (the typical case for this skill). The ML-aware tool delegates to `DerivaML.create_vocabulary`, which scopes the curie prefix to the deriva-ml project name (so terms get stable `{project}:{RID}` identifiers), defaults to the domain schema, and refreshes the catalog navbar so the new vocab is visible in Chaise immediately. Both tools produce physically-identical tables, so the existing `add_term` (from deriva-mcp-core) works against either.

In brief:
1. Call `deriva_ml_create_vocabulary(hostname="data.example.org", catalog_id="1", vocab_name="<vocab_name>", comment=...)`.
   - Optional: `schema=...` (defaults to the deriva-ml domain schema), `update_navbar=False` to skip the navbar refresh during batch creation.
   - On non-deriva-ml catalogs, fall back to the generic `create_vocabulary(hostname, catalog_id, schema, vocabulary_name, comment)` from deriva-mcp-core. See `/deriva:manage-vocabulary` *(deriva-skills)* for that surface.
2. Call `add_term(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<vocab_name>", name=..., description=..., synonyms=[...])` for each term. `add_term` lives in deriva-mcp-core; there is no ML-specific variant.

**Always provide meaningful descriptions for terms.** They appear in the UI and help annotators understand what each label means.

## Create the Feature

Call `deriva_ml_create_feature` with:
- `hostname`, `catalog_id`
- `target_table`: the target table whose records will be labeled (e.g., `"Image"`)
- `feature_name`: unique name for the feature (e.g., `"Tumor_Classification"`)
- `comment`: description of what this feature represents
- `terms` (optional): list of vocabulary table names whose terms can be values (e.g., `["Tumor_Grade"]`)
- `assets` (optional): list of asset table names that can be referenced (e.g., `["Mask_Image"]`)
- `metadata` (optional): list of additional columns — see `concepts.md` for format details

At least one of `terms` or `assets` is required.

This creates the feature record and a `{FeatureName}_Feature_Value` association table.

### Examples

**Term-based feature** (classification labels): call with `target_table`: `"Image"`, `feature_name`: `"Tumor_Classification"`, `terms`: `["Tumor_Grade"]`.

**Asset-based feature** (segmentation masks): call with `target_table`: `"Image"`, `feature_name`: `"Segmentation_Mask"`, `assets`: `["Mask_Image"]`. (Asset tables are created via the generic `create_table` tool with the standard hatrac column shape — see `/deriva:create-table` *(deriva-skills)*.)

**Mixed feature** (labels with overlays): include both `terms` and `assets`.

**Feature with metadata** (confidence scores): add `metadata`: `[{"name": "confidence", "type": {"typename": "float4"}}]`.

## Add Feature Values

Feature values require an active execution for provenance tracking. Every label assignment is tied to the execution that created it.

### Bundled script template

The canonical entry point is `skills/create-feature/scripts/populate_feature_values.py`. Copy it into the user's project (typically `src/scripts/populate_<feature>.py`), edit the CSV path / feature name, commit, then run via `deriva-ml-run`. The template handles workflow creation, execution context, validation, `add_features()` staging, and commit — all with the typed argparse skeleton and `--dry-run` flag.

```bash
# 1. Copy + customize
cp skills/create-feature/scripts/populate_feature_values.py \
   src/scripts/populate_tumor_classification.py
# Edit the script: set target_table, feature_name, CSV column mapping.

# 2. Commit so the workflow URL + commit hash resolve to real code
git add src/scripts/populate_tumor_classification.py
git commit -m "feat(scripts): populate Tumor_Classification feature values"

# 3. Run dry-first
uv run python src/scripts/populate_tumor_classification.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Annotation \
    --csv ./labels/tumor_grades.csv \
    --target-table Image --feature-name Tumor_Classification \
    --dry-run

# 4. Production run (drop --dry-run)
uv run python src/scripts/populate_tumor_classification.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Annotation \
    --csv ./labels/tumor_grades.csv \
    --target-table Image --feature-name Tumor_Classification
```

Inside the template, the work block builds typed `FeatureRecord` objects, calls `execution.add_features(records)` to stage them, and the post-`with`-block `execution.commit_output_assets()` flushes them to the catalog. Pydantic validates each row against the feature's term vocabulary; mismatched terms raise `DerivaMLInvalidTerm` immediately.

For multi-column features, edit the `RecordClass(**row)` instantiation in the loop to map CSV columns to the feature's columns. For asset-based features, set the asset reference column to the asset RID.

### Python API with context manager

```python
from deriva_ml import DerivaML, ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)
workflow = ml.find_workflow_by_url("https://github.com/my-org/my-repo")

config = ExecutionConfiguration(
    workflow=workflow,
    description="Expert pathologist tumor grading"
)

with ml.create_execution(config) as exe:
    # Look up the feature and get its record class
    feature = exe.catalog.lookup_feature("Image", "Tumor_Classification")
    RecordClass = feature.feature_record_class()

    # Create feature records
    records = [
        RecordClass(Image="2-IMG1", Tumor_Grade="Grade II"),
        RecordClass(Image="2-IMG2", Tumor_Grade="Grade III"),
    ]

    # Bulk add from a results dict
    for image_rid, grade in labeling_results.items():
        records.append(RecordClass(Image=image_rid, Tumor_Grade=grade))

    # Add all records in batch (execution RID set automatically)
    exe.add_features(records)
    # Feature values are uploaded automatically on context exit
```

## Query Feature Values

### Preferred: Use the typed feature tool

Always prefer the dedicated `deriva_ml_list_feature_values` tool over generic table queries:

Call `deriva_ml_list_feature_values` with:
- `hostname`, `catalog_id`
- `target_table`: the target table (e.g., `"Image"`)
- `feature_name` (optional): fetch only a specific feature
- `selector`: `"newest"` / `"first"` / `"latest"` / `"majority_vote"` to pick one value per record
- `workflow`: a Workflow RID or Workflow_Type name to filter by source workflow
- `execution`: an Execution RID to filter by a specific execution run

Only one of `selector`, `workflow`, or `execution` may be specified. See `concepts.md` for the full Python API including custom selectors.

### Fallback: Filtered queries on the feature value table

When you need to filter feature values by specific column values (e.g., "all images with Grade III"), query the feature value table directly with `get_entities` for whole-row reads, or `query_attribute` for column projection / FK joins:

```python
# Whole-row read filtered by feature column
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="<schema>", table="Tumor_Classification_Feature_Value",
    filters={"Tumor_Grade": "Grade III"},
)

# Or scope to a specific image
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="<schema>", table="Tumor_Classification_Feature_Value",
    filters={"Image": "2-IMG1"},
)

# Project specific columns or join — use query_attribute with path syntax
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="<schema>:Tumor_Classification_Feature_Value/Tumor_Grade=Grade%20III",
    attributes=["RID", "Image", "Tumor_Grade", "Confidence"],
)
```

This is the case where reaching past the dedicated feature-value tool is appropriate — that tool doesn't support arbitrary column filters.

## Managing Features

To **delete a feature**, call `deriva_ml_delete_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis")`. This removes the feature and its value table — existing data will be lost.

To **list all features**, call `deriva_ml_list_features(hostname="data.example.org", catalog_id="1")`.

## Complete Example

End-to-end MCP workflow: create a vocabulary, create a feature, and add values.

**Step 1:** Create the vocabulary.

Call `deriva_ml_create_vocabulary(hostname="data.example.org", catalog_id="1", vocab_name="Cell_Type", comment="Cell type classifications for microscopy images")`. The vocab lands in the deriva-ml domain schema, terms carry `{project}:{RID}` curie identifiers, and the navbar refreshes automatically.

Then call `add_term` for each term (from deriva-mcp-core — no ML-specific variant):
- `add_term(hostname="data.example.org", catalog_id="1", schema="<schema>", table="Cell_Type", name="Epithelial", description="Epithelial cells lining surfaces and cavities")`
- `add_term(...table="Cell_Type", name="Stromal", description="Connective tissue support cells")`
- `add_term(...table="Cell_Type", name="Immune", description="Immune system cells including lymphocytes and macrophages")`
- `add_term(...table="Cell_Type", name="Necrotic", description="Dead or dying cells")`

**Step 2:** Create the feature.

Call `deriva_ml_create_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Cell_Classification", terms=["Cell_Type"], comment="Primary cell type visible in microscopy image")`.

**Step 3:** Add values within an execution.

Copy `skills/create-feature/scripts/populate_feature_values.py` to `src/scripts/populate_cell_classification.py`. Edit the `target_table` and `feature_name` arguments (already CLI-driven), or hardcode for this specific use case. Stage a CSV with columns `Image` (the target table's RID column) and `Cell_Type` (the feature's term column), commit the script, then run:

```bash
uv run python src/scripts/populate_cell_classification.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Annotation \
    --csv ./annotations/cell_types_batch1.csv \
    --target-table Image --feature-name Cell_Classification
```

The script's `with ml.create_execution(...) as exe:` block stages the values via `exe.add_features(records)`; `exe.commit_output_assets()` post-context flushes them to the catalog. Each value carries provenance back to the committed script (workflow URL + git commit) and the execution.

## Complete Example: Python API

```python
from deriva_ml import DerivaML, ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)

# 1. Create vocabulary and terms
ml.create_vocabulary("Cell_Type", comment="Cell type classifications")
ml.add_term("Cell_Type", "Epithelial", description="Epithelial cells lining surfaces")
ml.add_term("Cell_Type", "Stromal", description="Connective tissue support cells")
ml.add_term("Cell_Type", "Immune", description="Immune system cells")

# 2. Create the feature
ml.create_feature("Image", "Cell_Classification",
                   terms=["Cell_Type"],
                   comment="Primary cell type visible in microscopy image")

# 3. Add values within an execution
workflow = ml.create_workflow(
    name="Expert Cell Annotation",
    workflow_type="Annotation",
    description="Expert cell type annotation"
)

with ml.create_execution(ExecutionConfiguration(workflow=workflow)) as exe:
    feature = exe.catalog.lookup_feature("Image", "Cell_Classification")
    RecordClass = feature.feature_record_class()

    records = [
        RecordClass(Image="2-IMG1", Cell_Type="Epithelial"),
        RecordClass(Image="2-IMG2", Cell_Type="Immune"),
    ]
    exe.add_features(records)
    # Feature values are uploaded automatically on context exit
```
