---
type: Concept
title: Feature design
description: Feature types, designing feature structure, naming conventions, metadata columns, column optionality and valid values, and multivalued features.
---

# Feature design

## Feature Types

| Type | `deriva_ml_create_feature` parameter | Use case |
|------|---------------------------|----------|
| Term-based | `terms=["Tumor_Grade"]` | Classification labels, categories |
| Asset-based | `assets=["Mask_Image"]` | Segmentation masks, annotation overlays |
| Mixed | `terms=[...], assets=[...]` | Labels with associated files |
| With metadata | `metadata=[...]` | Confidence scores, reviewer references, notes |

The `terms` and `assets` parameters take lists of vocabulary or asset table names. At least one of `terms` or `assets` is required.

### Term-based features

The most common type. Values come from controlled vocabulary tables, ensuring consistency.

```python
# Create vocabulary first
ml.create_vocabulary("Diagnosis_Type", "Clinical diagnosis categories")
ml.add_term("Diagnosis_Type", "Normal", "No abnormality detected")
ml.add_term("Diagnosis_Type", "Abnormal", "Abnormality present")

# Create the feature
ml.create_feature(
    target_table="Image",
    feature_name="Diagnosis",
    terms=["Diagnosis_Type"],
    comment="Clinical diagnosis for this image"
)
```

### Asset-based features

Link derived files (segmentation masks, embeddings, annotation overlays) to domain objects.

Asset tables are typically created via the generic `create_table` tool with the standard hatrac column shape (URL, Filename, Length, MD5, Description) plus an `Asset_Type` FK — see `/deriva:create-table` *(deriva-skills)* for the exact recipe.

```python
ml.create_asset("Segmentation_Mask", comment="Binary segmentation masks")

ml.create_feature(
    target_table="Image",
    feature_name="Segmentation",
    assets=["Segmentation_Mask"],
    comment="Segmentation mask for this image"
)
```

When creating asset-based feature values, you provide file paths. During execution upload, file paths are automatically replaced with the RIDs of the uploaded assets.

### Mixed features

Features can reference both terms and assets — for example, a classification label with an associated annotation overlay image.

## Designing a Feature

### Single-column vs multi-column features

A feature can have one or many term/asset/metadata columns. The choice affects how values are created and queried:

**Single term column** (most common):
```python
# One vocabulary, one label per annotation
create_feature("Image", "Diagnosis", terms=["Diagnosis_Type"])
# Values: {Image: "2-IMG1", Diagnosis_Type: "Normal"}
```

**Multiple term columns** (related dimensions in one annotation):
```python
# Two vocabularies, both set in one annotation record
create_feature("Image", "Clinical_Assessment",
               terms=["Diagnosis_Type", "Severity_Level"])
# Values: {Image: "2-IMG1", Diagnosis_Type: "Normal", Severity_Level: "Mild"}
```

**When to use multiple columns in one feature vs separate features:**

| Pattern | When to use |
|---------|-------------|
| **One feature, multiple columns** | The values are always assigned together in the same annotation act. A diagnosis and its severity are one clinical assessment. |
| **Separate features** | The values are assigned independently by different processes. Image quality is scored by QC; diagnosis is assigned by a pathologist. |

The test: if you always set them at the same time in the same execution, they belong together. If different workflows produce them, they're separate features.

### Feature with metadata

Add structured data beyond vocabulary terms — confidence scores, reviewer references, free-text notes:

```python
create_feature("Image", "Diagnosis_With_Confidence",
               terms=["Diagnosis_Type"],
               metadata=[
                   {"name": "confidence", "type": {"typename": "float4"}},
                   "Reviewer"  # FK to Reviewer table
               ])
# Values: {Image: "2-IMG1", Diagnosis_Type: "Normal", confidence: 0.95, Reviewer: "3-REV1"}
```

## Feature Naming

Feature names should be descriptive and follow these conventions:

- **Use PascalCase with underscores**: `Tumor_Classification`, `Image_Quality`, `Predicted_Class`
- **Name the annotation, not the vocabulary**: `Diagnosis` (the annotation act), not `Diagnosis_Type` (the vocabulary it draws from)
- **Be specific enough to avoid ambiguity**: `Cell_Classification` is better than just `Classification` (which classification?)
- **Feature names are vocabulary terms** — they're stored in the `Feature_Name` controlled vocabulary table. The same feature name can be used across different target tables.

**Good names:** `Diagnosis`, `Quality_Score`, `Tumor_Grade`, `Cell_Classification`, `Segmentation_Mask`

**Bad names:** `Labels`, `Feature1`, `My_Annotations`, `Data` (too vague)

## Metadata Columns

Features can include additional columns beyond the standard term/asset columns. The `metadata` parameter accepts a list where each item is either:

- **A string** — treated as a table name, adds a foreign key reference to that table (e.g., `"Reviewer"` adds an FK to the Reviewer table)
- **A dict** — column definition with `name` and `type` keys:
  - `type` must be `{"typename": "<type>"}` where type is one of: `text`, `int2`, `int4`, `int8`, `float4`, `float8`, `boolean`, `date`, `timestamp`, `timestamptz`, `json`, `jsonb`
  - Optional keys: `nullok` (bool), `default`, `comment`

Example: `metadata=[{"name": "confidence", "type": {"typename": "float4"}}, "Reviewer"]` adds both a float confidence column and an FK to the Reviewer table.

## Feature Column Optionality and Valid Values

Every feature has a set of columns — some required, some optional. Understanding this is critical when adding feature values.

### Required vs optional columns

- **Term columns** are required by default (NOT NULL). Each entry must provide a valid vocabulary term name
- **Asset columns** are required by default. Each entry must provide a valid asset RID
- **Metadata columns** follow the `nullok` setting from their definition:
  - `{"name": "confidence", "type": {"typename": "float4"}}` → optional (nullok=True by default)
  - `{"name": "confidence", "type": {"typename": "float4"}, "nullok": false}` → required

### How to check column requirements

The `deriva_ml_get_feature(hostname, catalog_id, target_table, feature_name)` tool returns the full column schema including:
- `required_fields` — list of all column names that must be provided
- Per-column `required` boolean for each term, asset, and value column
- The vocabulary table name for term columns (tells you what values are valid)
- The data type for value columns

### Valid values by column type

**Term columns** — values must exactly match a term name in the referenced vocabulary:
```
# See valid term names for a feature's term column
list_vocabulary_terms(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<vocabulary_table_name>")
```
Term names are case-sensitive. "Normal" ≠ "normal". Using an invalid term name will produce an error.

**Value columns** — values must match the column's data type:

| Column type | Valid values | Example |
|------------|-------------|---------|
| `text` | Any string | `"high quality"` |
| `float4` / `float8` | Decimal number | `0.95`, `3.14` |
| `int4` / `int8` | Integer | `42`, `-1` |
| `boolean` | `true` or `false` | `true` |
| `date` | ISO date string | `"2026-03-18"` |
| `timestamp` / `timestamptz` | ISO datetime | `"2026-03-18T14:30:00"` |
| `json` / `jsonb` | Valid JSON | `{"key": "value"}` |

**Asset columns** — values must be a valid RID of a record in the referenced asset table.

### Adding values with optional columns

When building `FeatureRecord` instances inside the bundled `populate_feature_values.py` template (see `workflow.md`), optional columns can be:
- **Included** in some records and **omitted** in others
- **Set to None** explicitly
- **Mixed** — some records with the column, some without

This is common for confidence scores: human annotations may not have confidence, while model predictions always include one.

```python
# Some records with confidence, some without — valid because confidence is optional
records = [
    RecordClass(Image="2-IMG1", Diagnosis_Type="Normal"),
    RecordClass(Image="2-IMG2", Diagnosis_Type="Abnormal", confidence=0.87),
]
exe.add_features(records)
```

Pydantic validation runs at `RecordClass(...)` construction, so a missing required column or a typo in a column name fails immediately.

## Multivalued Features

Because features track provenance through executions, a single record can accumulate multiple values for the same feature over time:

- **Multiple annotators** — different pathologists label the same image in separate executions
- **Multiple model runs** — different model versions produce different predictions
- **Corrections** — a later execution overrides an earlier label

This is by design — it enables inter-annotator agreement analysis, model comparison, and audit trails. But when you need a single value per record (e.g., for training), you need feature selection (see [selectors.md](selectors.md)).
