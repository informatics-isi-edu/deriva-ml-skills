# Dataset Workflow Reference

Step-by-step MCP tool examples for creating and managing datasets. For background concepts, see `concepts.md`. For bag downloads, see `bags.md`.

> **Stateless model:** the new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Table of Contents

1. [Creating a Dataset](#creating-a-dataset) — Check resources, create execution, add members
2. [Managing Types](#managing-types) — Add, remove, create custom types
3. [Managing Members](#managing-members) — Add, remove, validate, list
4. [Splitting Datasets](#splitting-datasets) — Random, stratified, labeled, dry run, navigation
5. [Versioning](#versioning) — When and how to increment
6. [Downloading](#downloading) — Preview and download
7. [Provenance](#provenance) — Track dataset lineage
8. [Deleting](#deleting) — Remove datasets
9. [Complete Example](#complete-example) — End-to-end workflow

---

## Creating a Dataset

### Check existing resources first

Before creating a dataset, review what already exists:

- Use `rag_search("your purpose", doc_type="catalog-data")` to find existing datasets by description, type, or purpose. Fall back to `deriva_ml_list_datasets(hostname="data.example.org", catalog_id="1")` for the full structured list.
- Use `rag_search("dataset types", doc_type="catalog-schema")` to find dataset type terms. Fall back to `list_vocabulary_terms(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Dataset_Type")` for the full list.
- Read `deriva://catalog/{h}/{c}/ml/registries` to see which tables are registered as element types.

### MCP Tools

Each step below is a separate MCP tool call. Use the RID returned by each tool in subsequent calls.

**Step 1: Create a workflow and execution for provenance**

Call `deriva_ml_create_workflow` with:
- `hostname`: `"data.example.org"`, `catalog_id`: `"1"`
- `name`: `"Dataset Curation"`
- `workflow_type`: `"Data Management"`
- `description`: `"Curate and organize training datasets"`

Then call `deriva_ml_create_execution` with the returned `workflow_rid` and `description="Create training dataset"`.

Then call `deriva_ml_start_execution` with the returned `execution_rid`.

**Step 2: Create the dataset**

Call `deriva_ml_create_dataset` with:
- `hostname`: `"data.example.org"`, `catalog_id`: `"1"`
- `description`: `"Curated set of labeled tumor histology images"`
- `dataset_types`: `["Training", "Labeled"]`

Note the returned dataset RID (e.g., `"2-DS01"`) — you'll need it for subsequent steps.

**Step 3: Register element types** (catalog-level, idempotent)

Call `deriva_ml_add_dataset_element_type` with `dataset_rid="2-DS01"`, `element_table="Image"`.
Call `deriva_ml_add_dataset_element_type` with `dataset_rid="2-DS01"`, `element_table="Subject"`.

**Step 4: Add members**

Call `deriva_ml_add_dataset_members` with:
- `hostname`: `"data.example.org"`, `catalog_id`: `"1"`
- `dataset_rid`: the RID from step 2
- `members`: `{"Image": ["2-IMG1", "2-IMG2", "2-IMG3", "2-IMG4", "2-IMG5"]}`
- `description`: `"Initial population of labeled tumor images"`

This auto-increments the dataset version; the description is recorded in version history.

For multi-table additions, pass multiple keys:
- `members`: `{"Image": ["2-IMG1", "2-IMG2"], "Subject": ["2-SUB1"]}`
- `description`: `"Added remaining images and subjects"`

**Step 5: Finalize**

Call `deriva_ml_commit_execution` with the execution RID. (No need to call Python API `exe.upload_execution_outputs()` — dataset operations don't produce output files. If something went wrong, call `deriva_ml_abort_execution` instead.)

### Python API

For creating datasets in Python scripts with full provenance, see the `execution-lifecycle` skill which covers `ExecutionConfiguration` and context manager patterns. A brief example:

```python
from deriva_ml import DerivaML, ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)
workflow = ml.create_workflow(
    name="Dataset Curation",
    workflow_type="Data Management",
    description="Curate and organize training datasets"
)

with ml.create_execution(ExecutionConfiguration(workflow=workflow)) as exe:
    dataset = exe.create_dataset(
        description="Labeled tumor images",
        dataset_types=["Training", "Labeled"]
    )
    ml.add_dataset_element_type("Image")
    dataset.add_dataset_members(
        members=["2-IMG1", "2-IMG2", "2-IMG3"],
        description="Initial labeled images"
    )
```

## Managing Types

To **add a type** to a dataset, call `deriva_ml_update_dataset` with `dataset_rid` and `dataset_types=["Training", ...]` (the existing types plus your additions).

To **remove a type**, call `update_entities` on the dataset's type-association table and remove the row that links the dataset to the type. (The legacy `remove_dataset_type` shortcut was removed; only generic `update_entities` remains.)

To **create a new custom type**, call `add_term(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Dataset_Type", name="Preprocessed", description="...")`. The legacy `create_dataset_type_term` shortcut was subsumed by the generic `add_term` tool.

To **delete a custom type**, call `delete_term(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Dataset_Type", name="Preprocessed")`.

For more on vocabulary CRUD see `/deriva:manage-vocabulary` *(tier-1, deriva-skills)*.

## Managing Members

To **list current members**, call `deriva_ml_list_dataset_members` with `hostname`, `catalog_id`, and `dataset_rid`.

To **validate RIDs** before adding (catches invalid RIDs early), call `get_entities(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<table>", filter={"RID": "<rid>"})` per candidate RID and check whether the result is non-empty. The legacy single-shot `validate_rids` tool was removed.

To **add more members**, call `deriva_ml_add_dataset_members` with:
- `hostname`, `catalog_id`
- `dataset_rid`: the dataset's RID
- `members`: list of RIDs (or a `{table: [rids]}` dict for the typed form)
- `description`: why these members are being added (recorded in version history)

This auto-increments the dataset version.

To **remove members**, call `deriva_ml_delete_dataset_members` with `hostname`, `catalog_id`, `dataset_rid`, and `members`.

## Splitting Datasets

`deriva_ml_split_dataset` creates nested child datasets from a parent. It follows the same conventions as scikit-learn's [`train_test_split`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html) — parameters like `test_size`, `train_size`, `shuffle`, `seed`, and stratification work the same way. It auto-increments the dataset version. Always use `dry_run=true` first to preview the split plan.

### Basic usage

To **preview a split** without modifying the catalog, call `deriva_ml_split_dataset` with `hostname`, `catalog_id`, `dataset_rid`, `test_size`, `seed`, and `dry_run`: `true`.

To **create a two-way split** (e.g., 80% Training / 20% Testing), call `deriva_ml_split_dataset` with:
- `hostname`: `"data.example.org"`, `catalog_id`: `"1"`
- `dataset_rid`: the dataset's RID
- `test_size`: `0.2`
- `seed`: `42`

To **create a three-way split**, also include `val_size` (e.g., `0.1` for 10% Validation).

### Stratified and labeled splits

To maintain class distribution, add `stratify_by_column` with the denormalized column name. Use `deriva_ml_denormalize_dataset(hostname=..., catalog_id=..., include_tables=[...])` (no dataset RID needed) to discover the exact column names, or derive them from the table schema.

**Finding the stratify column name:**

1. Use `rag_search("feature table columns", doc_type="catalog-schema")` to find the feature table name and its columns, or call `deriva_ml_list_features(hostname="data.example.org", catalog_id="1")` for the full structured output
2. Construct the denormalized column name as `{FeatureTableName}_{ColumnName}`

For example, if the feature table is `Execution_Image_Image_Classification` and the column is `Image_Class`, the stratify column is `Execution_Image_Image_Classification_Image_Class`.

### Denormalized column naming convention

When `deriva_ml_denormalize_dataset` or `deriva_ml_split_dataset` flattens tables into a wide DataFrame, columns are prefixed with their source table name using underscores: `{TableName}_{ColumnName}`.

**Simple columns** (from domain tables):
- `Image` table, `Filename` column becomes `Image_Filename`
- `Subject` table, `Age` column becomes `Subject_Age`
- `Subject` table, `RID` column becomes `Subject_RID`

**Feature columns** (from feature/annotation tables):
- `Image_Classification` table, `Image_Class` column becomes `Image_Classification_Image_Class`
- `Image_Classification` table, `Confidence` column becomes `Image_Classification_Confidence`
- `Diagnosis_Feature` table, `Diagnosis_Type` column becomes `Diagnosis_Feature_Diagnosis_Type`

**Key rules:**
- The prefix is always the **table name** as it appears in the schema, not a shortened alias
- Feature tables often have long names (e.g., `Execution_Image_Image_Classification`) — the full name is used as the prefix
- Use `deriva_ml_denormalize_dataset(include_tables=[...])` to see the actual column names if unsure — no dataset RID needed, returns column headers and size estimates without fetching data

`include_tables` is required when using stratification — use the feature table name from the schema.

**Handling missing values in the stratify column:** Not all members may have a value for the stratify column (e.g., unlabeled images in a labeled feature table). Use `stratify_missing` to control this:

| Policy | Behavior |
|--------|----------|
| `"error"` (default) | Raise an error reporting the count and percentage of nulls |
| `"drop"` | Exclude rows with missing values — only labeled rows are split |
| `"include"` | Treat nulls as a distinct class — missing-value rows are distributed proportionally |

To label partitions with ground truth metadata (needed for evaluation, ROC curves, etc.), add `training_types`, `testing_types`, and/or `validation_types` (e.g., `["Labeled"]`).

**Example:** A stratified, labeled three-way split would use:
- `hostname`: `"data.example.org"`, `catalog_id`: `"1"`
- `dataset_rid`: the dataset's RID
- `test_size`: `0.2`, `val_size`: `0.1`, `seed`: `42`
- `stratify_by_column`: `"Image_Classification_Image_Class"`
- `include_tables`: `["Image", "Image_Classification"]`
- `stratify_missing`: `"drop"` (if some images lack labels)
- `training_types`: `["Labeled"]`, `testing_types`: `["Labeled"]`, `validation_types`: `["Labeled"]`

### Parameter reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hostname` | `str` | *(required)* | Catalog hostname |
| `catalog_id` | `str` | *(required)* | Catalog ID |
| `dataset_rid` | `str` | *(required)* | RID of the dataset to split |
| `test_size` | `float` | `0.2` | Fraction for testing (0-1) |
| `train_size` | `float \| None` | `None` | Fraction for training. Default: complement of test + val |
| `val_size` | `float \| None` | `None` | Fraction for validation. When set, creates 3-way split |
| `seed` | `int` | `42` | Random seed for reproducibility |
| `shuffle` | `bool` | `True` | Shuffle before splitting |
| `stratify_by_column` | `str \| None` | `None` | Denormalized column name for stratified split |
| `stratify_missing` | `str` | `"error"` | Policy for nulls in stratify column: `"error"`, `"drop"`, `"include"` |
| `element_table` | `str \| None` | `None` | Table to split. Auto-detected if dataset has one element type |
| `include_tables` | `list[str] \| None` | `None` | Tables for denormalization. Required with `stratify_by_column` |
| `training_types` | `list[str] \| None` | `None` | Additional types for training set (e.g., `["Labeled"]`) |
| `testing_types` | `list[str] \| None` | `None` | Additional types for testing set |
| `validation_types` | `list[str] \| None` | `None` | Additional types for validation set |
| `split_description` | `str` | `""` | Description for the parent Split dataset |
| `dry_run` | `bool` | `False` | Preview without modifying catalog |

### Navigating split results

`deriva_ml_split_dataset` creates a parent "Split" dataset with child datasets for each partition.

To **list relations** of a dataset (both children and parents in one call), call `deriva_ml_list_dataset_relations(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")`. Add `recurse=true` to include all descendants/ancestors, or `version` to list relations at a specific version.

> Note: the legacy split between `list_dataset_children` and `list_dataset_parents` is gone — `deriva_ml_list_dataset_relations` returns both directions.

To **list members across nested datasets**, call `deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", recurse=true)` (optionally with `limit`).

To create parent-child relationships manually (without `deriva_ml_split_dataset`), use `deriva_ml_add_dataset_members(parent_rid, members={"Dataset": [child_rid]})` — children are members of the parent's `Dataset` element type. See `concepts.md` for background on nested dataset hierarchies.

## Versioning

`deriva_ml_add_dataset_members` and `deriva_ml_split_dataset` auto-increment the minor version. Manual incrementation is only needed for other changes (removing members, changing element types, data cleanup).

To **manually increment**, call `deriva_ml_increment_dataset_version` with `hostname`, `catalog_id`, `dataset_rid`. Optionally specify `component` (`"major"`, `"minor"`, or `"patch"`) and `description` (e.g., `"Corrected mislabeled records"`).

See the versioning section of `references/concepts.md` for full rules and the pre-experiment checklist.

## Downloading

To **preview** what a bag will contain (size + manifest), call `deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", version="1.0.0")`. The legacy `estimate_bag_size` tool was subsumed by `deriva_ml_bag_info`.

For downloading, preparing, and restructuring dataset data for ML training, see the `ml-data-engineering` skill. For details on bag contents, FK traversal, and timeout handling, see `bags.md`. For diagnosing missing data, see the `debug-bag-contents` skill.

## Provenance

To find **which executions used a dataset**, call `deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")` — the returned record includes execution provenance.

To find **which executions produced or used an asset**, call `deriva_ml_lookup_asset(hostname="data.example.org", catalog_id="1", asset_rid="<rid>")` for the producing execution, or `deriva_ml_find_workflow_executions(hostname="data.example.org", catalog_id="1", workflow_rid="<rid>")` for broader workflow queries. (The legacy single-shot `list_asset_executions` tool was removed in favor of these targeted calls.)

## Deleting

To **delete a dataset** (removes the container and member associations, not the member records themselves), call `deriva_ml_delete_dataset` with `hostname`, `catalog_id`, `dataset_rid`.

To **delete a dataset and all its children**, add `recurse`: `true`.

## Complete Example

End-to-end workflow: create a dataset, add members, and execute a stratified labeled split.

```python
from deriva_ml import DerivaML, ExecutionConfiguration
from deriva_ml.dataset.split import split_dataset

ml = DerivaML(hostname, catalog_id)

workflow = ml.create_workflow(
    name="Image Dataset Curation",
    workflow_type="Data Management",
    description="Curate and split image datasets for training"
)

config = ExecutionConfiguration(
    workflow=workflow,
    description="Create and split tumor image dataset"
)

with ml.create_execution(config) as exe:
    # 1. Register element types (catalog-level, idempotent)
    ml.add_dataset_element_type("Image")

    # 2. Create the master dataset
    dataset = exe.create_dataset(
        description="All labeled tumor histology images as of 2025-06",
        dataset_types=["Complete", "Labeled"]
    )

    # 3. Add all labeled images (description records why this version was created)
    dataset.add_dataset_members(
        members=["2-IMG1", "2-IMG2", "2-IMG3", "2-IMG4", "2-IMG5",
                 "2-IMG6", "2-IMG7", "2-IMG8", "2-IMG9", "2-IMG10"],
        description="Initial population of labeled tumor images"
    )

    # 4. Preview the split
    result = split_dataset(
        ml, dataset.dataset_rid,
        test_size=0.15, val_size=0.15,
        stratify_by_column="Image_Classification_Image_Class",
        stratify_missing="drop",  # exclude unlabeled images
        include_tables=["Image", "Image_Classification"],
        seed=42, dry_run=True
    )
    print(f"Plan: {result.training.count} train, "
          f"{result.validation.count} val, {result.testing.count} test")

    # 5. Execute the split
    result = split_dataset(
        ml, dataset.dataset_rid,
        test_size=0.15, val_size=0.15,
        stratify_by_column="Image_Classification_Image_Class",
        stratify_missing="drop",
        include_tables=["Image", "Image_Classification"],
        training_types=["Labeled"],
        testing_types=["Labeled"],
        validation_types=["Labeled"],
        seed=42
    )
    print(f"Training: {result.training.rid}, Testing: {result.testing.rid}")

# Execution is automatically committed and outputs uploaded on context exit
```
