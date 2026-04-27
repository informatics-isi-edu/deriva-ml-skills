# Feature Workflow Reference

Step-by-step MCP tool and Python API examples for creating and populating features. For background concepts (feature types, multivalued features, selection), see `concepts.md`.

> **Stateless model:** the new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

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

If your feature needs a new set of terms, create the vocabulary first. See `/deriva:manage-vocabulary` *(tier-1, deriva-skills)* for full details.

In brief:
1. Call `create_vocabulary(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<vocab_name>", comment=...)`.
2. Call `add_term(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<vocab_name>", name=..., description=..., synonyms=[...])` for each term.

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

**Asset-based feature** (segmentation masks): call with `target_table`: `"Image"`, `feature_name`: `"Segmentation_Mask"`, `assets`: `["Mask_Image"]`. (Asset tables are created via the generic `create_table` tool with the standard hatrac column shape — see `/deriva:create-table` *(tier-1, deriva-skills)*. The legacy `create_asset_table` shortcut was not ported.)

**Mixed feature** (labels with overlays): include both `terms` and `assets`.

**Feature with metadata** (confidence scores): add `metadata`: `[{"name": "confidence", "type": {"typename": "float4"}}]`.

## Add Feature Values

Feature values require an active execution for provenance tracking. Every label assignment is tied to the execution that created it.

### MCP workflow

**Step 1:** Create a workflow and execution.

Call `deriva_ml_create_workflow(hostname=..., catalog_id=..., name=..., workflow_type=..., description=...)`.

Then call `deriva_ml_create_execution(hostname=..., catalog_id=..., workflow_rid=<workflow_rid>, description=...)`.

Then call `deriva_ml_start_execution(hostname=..., catalog_id=..., execution_rid=<execution_rid>)`.

**Step 2:** Add values using `deriva_ml_add_feature_values` (one tool — singular vs multi-column shape was unified):

- `hostname`, `catalog_id`
- `target_table`: the target table (e.g., `"Image"`)
- `feature_name`: the feature name (e.g., `"Tumor_Classification"`)
- `values`: list of dicts, each with `target_rid` plus column values matching the feature's schema. For a single-column feature, supply `target_rid` plus the one term column (e.g., `Tumor_Grade`). For a multi-column feature, include all required columns and any optional ones you have values for.
- `execution_rid` (optional): defaults to the active execution

**Step 3:** Call `deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid=<execution_rid>)` to finalize. (Use `deriva_ml_abort_execution` instead if something went wrong.) Feature values are written directly to the catalog by `deriva_ml_add_feature_values` — no Python API `exe.upload_execution_outputs()` call is needed unless you also registered file assets with Python API `exe.asset_file_path()`.

> Note: the legacy `add_feature_value` (singular) and `add_feature_value_record` (multi-column) tools were both subsumed by `deriva_ml_add_feature_values` (plural). Pass a single-element list when you only have one value.

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

When you need to filter by specific column values (e.g., "all images with Grade III"), use `query_attribute` on the feature value table directly:

Call `query_attribute(hostname="data.example.org", catalog_id="1", schema="<schema>", table="Tumor_Classification_Feature_Value", filter={"Tumor_Grade": "Grade III"})`. Use `filter` to narrow results (e.g., `{"Image": "2-IMG1"}` for a specific image).

This is the only case where `query_attribute` is appropriate for feature values — the dedicated tool above doesn't support arbitrary column filters.

## Managing Features

To **delete a feature**, call `deriva_ml_delete_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis")`. This removes the feature and its value table — existing data will be lost.

To **list all features**, call `deriva_ml_list_features(hostname="data.example.org", catalog_id="1")`.

## Complete Example

End-to-end MCP workflow: create a vocabulary, create a feature, and add values.

**Step 1:** Create the vocabulary.

Call `create_vocabulary(hostname="data.example.org", catalog_id="1", schema="<schema>", table="Cell_Type", comment="Cell type classifications for microscopy images")`.

Then call `add_term` for each term:
- `add_term(hostname="data.example.org", catalog_id="1", schema="<schema>", table="Cell_Type", name="Epithelial", description="Epithelial cells lining surfaces and cavities")`
- `add_term(...table="Cell_Type", name="Stromal", description="Connective tissue support cells")`
- `add_term(...table="Cell_Type", name="Immune", description="Immune system cells including lymphocytes and macrophages")`
- `add_term(...table="Cell_Type", name="Necrotic", description="Dead or dying cells")`

**Step 2:** Create the feature.

Call `deriva_ml_create_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Cell_Classification", terms=["Cell_Type"], comment="Primary cell type visible in microscopy image")`.

**Step 3:** Add values within an execution.

Call `deriva_ml_create_workflow(hostname="data.example.org", catalog_id="1", name="Expert Cell Annotation", workflow_type="Annotation", description="Expert cell type annotation workflow")`.

Call `deriva_ml_create_execution(hostname="data.example.org", catalog_id="1", workflow_rid="<workflow_rid>", description="Expert cell type annotation - batch 1")`.

Call `deriva_ml_start_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")`.

Call `deriva_ml_add_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Cell_Classification", values=[{"target_rid": "2-IMG1", "Cell_Type": "Epithelial"}, {"target_rid": "2-IMG2", "Cell_Type": "Immune"}])`.

Call `deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")` to finalize. Feature values were already written to the catalog by `deriva_ml_add_feature_values`.

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
