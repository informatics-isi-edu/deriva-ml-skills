---
type: Concept
title: Feature usage and API
description: Discovering existing features, FeatureRecord Python API, features in datasets, exploring and navigating features, feature value table naming, and the operations summary.
---

# Feature usage and API

## Discovering Existing Features

Before creating a new feature, check what already exists. Duplicate features fragment annotations and confuse downstream consumers.

**MCP tools:**
```
# Browse all features in the catalog — shows target tables, types, column schemas
deriva_ml_list_features(hostname="data.example.org", catalog_id="1")

# Get details about a specific feature
deriva_ml_get_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis")

# See feature values for a table — pass `feature_name` to scope to one feature
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image")

# See deduplicated values (newest per record per feature)
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", selector="newest")
```

**Python API:**
```python
# Discover features on a specific table
features = ml.find_features("Image")
for f in features:
    print(f"{f.feature_name}: {f.feature_table.name}")

# Discover all features in the catalog
all_features = ml.find_features()

# Inspect a specific feature's structure (columns, types)
feature = ml.lookup_feature("Image", "Diagnosis")
print(f"Term columns: {[c.name for c in feature.term_columns]}")
print(f"Asset columns: {[c.name for c in feature.asset_columns]}")
print(f"Value columns: {[c.name for c in feature.value_columns]}")
```

**Before creating, ask:**
- Does a feature with this purpose already exist on this table? Check `deriva_ml_list_features(hostname=..., catalog_id=...)`.
- Does a similar feature exist under a different name? (The `semantic-awareness` skill checks for this automatically, and `deriva_ml_create_feature` warns about near-duplicates.)
- Can the existing feature be extended with new vocabulary terms instead of creating a new one?
- Is this really a feature, or should it be a column? (See [feature-vs-column.md](feature-vs-column.md).)

## Feature Records (Python API)

Feature values are represented as **FeatureRecord** objects — dynamically generated Pydantic models whose fields match the feature's columns.

```python
# Get the record class (two equivalent ways)
RecordClass = ml.feature_record_class("Image", "Tumor_Classification")
# or
feature = ml.lookup_feature("Image", "Tumor_Classification")
RecordClass = feature.feature_record_class()

# Construct a record
record = RecordClass(Image="2-IMG1", Tumor_Grade="Grade II")
```

- Target table column (e.g., `Image`) takes the record's RID
- Vocabulary term columns take the term name (not the RID)
- Asset columns take the asset RID or a file path (replaced with RID during upload)
- Metadata columns take the appropriate typed value
- The `Execution` column is set automatically by `exe.add_features()`

## Features in Datasets

Features are tightly integrated with the dataset lifecycle:

### In dataset bags

Feature values for dataset members are automatically included in BDBag exports. When you download a dataset, the bag contains all feature annotations for the included records.

```python
# Query features in a downloaded bag (same API as live catalog)
bag = dataset.download_dataset_bag(version="1.0.0")
values = list(bag.feature_values("Image", "Diagnosis",
                                  selector=FeatureRecord.select_newest))
features_on_table = bag.find_features("Image")
```

Note: `select_by_workflow` is not available on bags since it requires live catalog access.

### In deriva_ml_denormalize_dataset

Feature tables can be included in denormalization. Column names follow the pattern `{FeatureTableName}_{ColumnName}`:

```
# Schema exploration (no dataset needed)
deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=["Image", "Image_Classification"])
# Produces columns like: Image_RID, Image_Filename, Image_Classification_Image_Class
```

This is how the `stratify_by_column` parameter in the Python `split_dataset(ml, source_rid, exe, ...)` API references feature columns.

### Dataset versioning impact

Adding feature values to records in a dataset does NOT automatically update existing released versions. Released versions are frozen snapshots. Per ADR-0003, feature drift is also not auto-detected by the dataset-mutation tools (which would flip the dataset to dev) — feature mutations leave `current_version` unchanged. To record feature drift, use the Python API: call `dataset.mark_dev(description)` to declare a dev period (which flips `current_version` to a `<release>.post1.devN` label), then `deriva_ml_release_dataset(bump, description)` to promote the dev period to a new released version that captures the new feature values.

## Exploring and Navigating Features

### Understanding a feature's structure

```
# MCP — feature schema (columns, types, requirements)
deriva_ml_get_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis")
```

```python
# Python API — inspect feature structure
feature = ml.lookup_feature("Image", "Diagnosis")
print(f"Target: {feature.target_table.name}")
print(f"Feature table: {feature.feature_table.name}")
print(f"Term columns: {[c.name for c in feature.term_columns]}")
print(f"Asset columns: {[c.name for c in feature.asset_columns]}")
print(f"Value columns: {[c.name for c in feature.value_columns]}")
```

### Browsing feature values

```
# MCP — all values for a feature with provenance
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis")

# MCP — all features on a table, deduplicated to newest
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", selector="newest")

# MCP — fetch with selection/filtering
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis", selector="newest")
```

```python
# Python API — iterator of FeatureRecord for a single feature
for v in ml.feature_values("Image", "Diagnosis"):
    print(f"Image {v.Image}: {v.Diagnosis_Type} (by Execution {v.Execution})")
```

### Checking what features exist on a table

```
# MCP
deriva_ml_list_features(hostname="data.example.org", catalog_id="1", target_table="Image")
```

```python
# Python API
features = ml.find_features("Image")
for f in features:
    print(f"  {f.feature_name}: target={f.target_table.name}, table={f.feature_table.name}")
```

## Feature Value Table Naming

When you create a feature, DerivaML creates an association table to store feature values. The table name follows the pattern `Execution_{TargetTable}_{FeatureName}` — for example, creating a feature named `"Tumor_Classification"` on the `Image` table creates an `Execution_Image_Tumor_Classification` table.

This table contains columns for:
- The target record (FK to the target table, e.g., `Image`)
- Each vocabulary term column (FK to the vocabulary table, e.g., `Tumor_Grade`)
- Each asset column (FK to the asset table)
- Each metadata column
- `Execution` (FK to the Execution table — provenance)
- `Feature_Name` (FK to the Feature_Name vocabulary)

## Operations Summary

### Creation and population

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Create feature | `deriva_ml_create_feature` | `ml.create_feature()` | Vocabulary must exist first |
| Add values | `skills/create-feature/scripts/populate_feature_values.py` | `exe.add_features()` | Bundled template — no MCP equivalent; authorship belongs in committed scripts |
| Delete feature | `deriva_ml_delete_feature` | `ml.delete_feature()` | Removes feature table and all values |

### Discovery and navigation

| Operation | MCP Tool | Python API | Notes |
|-----------|---------------------|------------|-------|
| Browse all features | `deriva_ml_list_features` | `ml.find_features()` | All features in catalog |
| Features on a table | `deriva_ml_list_features(target_table=...)` | `ml.find_features("Image")` | Filtered to one table |
| Feature details | `deriva_ml_get_feature` | `ml.lookup_feature()` | Column types, requirements |
| Feature values | `deriva_ml_list_feature_values` | `ml.feature_values()` | With provenance, supports selectors |
| Values in a bag | — | `bag.feature_values()` | Same API on downloaded bags |
