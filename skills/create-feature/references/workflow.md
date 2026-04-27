# Feature Workflow Reference

Step-by-step MCP tool and Python API examples for creating and populating features. For background concepts (feature types, multivalued features, selection), see `concepts.md`.

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

- Read `deriva://catalog/features` to list all features with their target tables and column schemas.
- Read `deriva://feature/{table_name}/{feature_name}` for details on a specific feature.
- Check existing feature values with `deriva://table/{table_name}/feature-values/newest` to see what annotations already exist.

## Create a Vocabulary (if needed)

If your feature needs a new set of terms, create the vocabulary first. See the `manage-vocabulary` skill for full details.

In brief:
1. Call `create_vocabulary` with `vocabulary_name` and `comment`.
2. Call `add_term` for each term with `vocabulary_name`, `term_name`, `description`, and optional `synonyms`.

**Always provide meaningful descriptions for terms.** They appear in the UI and help annotators understand what each label means.

## Create the Feature

Call `create_feature` with:
- `table_name`: the target table whose records will be labeled (e.g., `"Image"`)
- `feature_name`: unique name for the feature (e.g., `"Tumor_Classification"`)
- `comment`: description of what this feature represents
- `terms` (optional): list of vocabulary table names whose terms can be values (e.g., `["Tumor_Grade"]`)
- `assets` (optional): list of asset table names that can be referenced (e.g., `["Mask_Image"]`)
- `metadata` (optional): list of additional columns — see `concepts.md` for format details

At least one of `terms` or `assets` is required.

This creates the feature record and a `{FeatureName}_Feature_Value` association table.

### Examples

**Term-based feature** (classification labels): call with `table_name`: `"Image"`, `feature_name`: `"Tumor_Classification"`, `terms`: `["Tumor_Grade"]`.

**Asset-based feature** (segmentation masks): call with `table_name`: `"Image"`, `feature_name`: `"Segmentation_Mask"`, `assets`: `["Mask_Image"]`.

**Mixed feature** (labels with overlays): include both `terms` and `assets`.

**Feature with metadata** (confidence scores): add `metadata`: `[{"name": "confidence", "type": {"typename": "float4"}}]`.

## Add Feature Values

Feature values require an active execution for provenance tracking. Every label assignment is tied to the execution that created it.

### MCP workflow

**Step 1:** Call `create_execution` with `workflow_name`, `workflow_type`, and `description`. Then call `start_execution`.

**Step 2:** Add values using one of two tools:

**For simple features** (single term or asset column), call `add_feature_value` with:
- `table_name`: the target table (e.g., `"Image"`)
- `feature_name`: the feature name (e.g., `"Tumor_Classification"`)
- `entries`: list of dicts, each with `target_rid` and `value` (a term name or asset RID)
- `execution_rid` (optional): defaults to the active execution

**For features with multiple columns** (e.g., term + confidence), call `add_feature_value_record` with:
- `table_name`: the target table
- `feature_name`: the feature name
- `entries`: list of dicts, each with `target_rid` plus column values matching the feature's schema
- `execution_rid` (optional): defaults to the active execution

**Step 3:** Call `stop_execution` to finalize. Feature values are written directly to the catalog by `add_feature_value` — no Python API `exe.upload_execution_outputs()` call is needed unless you also registered file assets with Python API `exe.asset_file_path()`.

### Python API with context manager

```python
from deriva_ml import DerivaML, ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)
workflow = ml.lookup_workflow_by_url("https://github.com/my-org/my-repo")

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

### Preferred: Use dedicated feature tools and resources

Always prefer the feature-specific tools and resources over generic `preview_table`:

**Browse values via resources:**
- Read `deriva://feature/{table}/{name}/values` — all values for a specific feature, with full provenance
- Read `deriva://table/{table}/feature-values` — all feature values for a table, grouped by feature name
- Read `deriva://table/{table}/feature-values/newest` — deduplicated to one value per record per feature

**Fetch with selection via tool:**

Call resource `deriva://table/{name}/features` with:
- `table_name`: the target table (e.g., `"Image"`)
- `feature_name` (optional): fetch only a specific feature
- `selector`: `"newest"` to pick the most recent value per record
- `workflow`: a Workflow RID or Workflow_Type name to filter by source workflow
- `execution`: an Execution RID to filter by a specific execution run

Only one of `selector`, `workflow`, or `execution` may be specified. See `concepts.md` for the full Python API including custom selectors.

### Fallback: Filtered queries on the feature value table

When you need to filter by specific column values (e.g., "all images with Grade III"), use `preview_table` on the feature value table directly:

Call `preview_table` with `table_name` set to the feature value table (e.g., `"Tumor_Classification_Feature_Value"`). Use `filters` to narrow results (e.g., `{"Image": "2-IMG1"}` for a specific image, or `{"Tumor_Grade": "Grade III"}` for all images with a specific grade).

This is the only case where `preview_table` is appropriate for feature values — the dedicated tools above don't support arbitrary column filters.

## Managing Features

To **delete a feature**, call `delete_feature` with `table_name` and `feature_name`. This removes the feature and its value table — existing data will be lost.

To **list all features**, read the `deriva://catalog/features` resource.

## Complete Example

End-to-end MCP workflow: create a vocabulary, create a feature, and add values.

**Step 1:** Create the vocabulary.

Call `create_vocabulary` with `vocabulary_name`: `"Cell_Type"`, `comment`: `"Cell type classifications for microscopy images"`.

Then call `add_term` for each term:
- `term_name`: `"Epithelial"`, `description`: `"Epithelial cells lining surfaces and cavities"`
- `term_name`: `"Stromal"`, `description`: `"Connective tissue support cells"`
- `term_name`: `"Immune"`, `description`: `"Immune system cells including lymphocytes and macrophages"`
- `term_name`: `"Necrotic"`, `description`: `"Dead or dying cells"`

**Step 2:** Create the feature.

Call `create_feature` with `table_name`: `"Image"`, `feature_name`: `"Cell_Classification"`, `terms`: `["Cell_Type"]`, `comment`: `"Primary cell type visible in microscopy image"`.

**Step 3:** Add values within an execution.

Call `create_execution` with `workflow_name`: `"Expert Cell Annotation"`, `workflow_type`: `"Annotation"`, `description`: `"Expert cell type annotation - batch 1"`. Then call `start_execution`.

Call `add_feature_value` with `table_name`: `"Image"`, `feature_name`: `"Cell_Classification"`, `entries`:
- `{"target_rid": "2-IMG1", "value": "Epithelial"}`
- `{"target_rid": "2-IMG2", "value": "Immune"}`

Call `stop_execution` to finalize. Feature values were already written to the catalog by `add_feature_value`.

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
