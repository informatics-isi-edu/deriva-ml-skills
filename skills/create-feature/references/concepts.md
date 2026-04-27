# Feature Concepts

Background on features in DerivaML. For the step-by-step guide, see `workflow.md`.

## Table of Contents

- [What is a Feature?](#what-is-a-feature)
- [When to Use a Feature vs a Column](#when-to-use-a-feature-vs-a-column)
- [Discovering Existing Features](#discovering-existing-features)
- [Feature Types](#feature-types)
- [Designing a Feature](#designing-a-feature)
- [Feature Naming](#feature-naming)
- [Metadata Columns](#metadata-columns)
- [Multivalued Features](#multivalued-features)
- [Feature Selection](#feature-selection)
- [Feature Value Table Naming](#feature-value-table-naming)
- [Feature Records (Python API)](#feature-records-python-api)
- [Features in Datasets](#features-in-datasets)
- [Exploring and Navigating Features](#exploring-and-navigating-features)
- [Operations Summary](#operations-summary)

---

## What is a Feature?

A feature links domain objects (e.g., Image, Subject) to a set of values — which could be controlled vocabulary terms, computed values, or assets. It is the primary way to attach structured meaning to records in DerivaML.

Common uses include:
- **Classification labels** — human-assigned or model-predicted categories (e.g., tumor grade, cell type, diagnosis)
- **Model predictions** — inference results from a classifier or detector
- **Quality scores** — numeric assessments (e.g., image quality, focus score, confidence)
- **Transformed data** — processed versions of source records (e.g., normalized images, cropped regions)
- **Statistical values** — computed aggregates (e.g., max intensity, mean pixel value, cell count)
- **Segmentation masks** — pixel-level or region annotations linked as assets
- **Review annotations** — status tracking with reviewer provenance

Each feature has:
- **A name** — identifies the annotation dimension (e.g., "Tumor_Classification", "Image_Quality")
- **A target table** — which domain table's records are being annotated (e.g., Image, Subject)
- **Value columns** — controlled vocabulary terms, asset references, or both
- **Optional metadata columns** — additional structured data like confidence scores or reviewer references
- **A description** — what the feature measures, what values it takes, its role in the workflow

Every feature value is associated with an **execution**, which provides full provenance. This means you can differentiate between multiple values for the same record by execution RID, workflow, execution description, timestamp, or any other execution attribute. For example, you can distinguish labels from "Pathologist A's review" vs "Model v2 predictions" vs "QC pipeline run #47".

Features are inherently **multivalued**: a single record can accumulate multiple values for the same feature over time (e.g., labels from different annotators or model runs), and the same term can be applied to many records. This is by design — it enables inter-annotator agreement analysis, model comparison, and audit trails. When you need a single value per record, use feature selection (see below).

## When to Use a Feature vs a Column

Not every piece of metadata belongs in a feature. Features have overhead (a separate table, execution requirement, provenance tracking) that's justified when you need their properties. Use this to decide:

**Use a feature when:**
- The value needs **provenance** — you need to know *who* assigned it (which execution, which annotator, which model run)
- The value is **multivalued** — the same record can have multiple values from different sources (multiple annotators, successive model runs)
- The value comes from a **controlled vocabulary** — ensuring consistency across annotators and experiments
- The value will be used for **ML training labels** — features integrate with dataset bags, denormalization, and Python API `bag.restructure_assets()`
- The value may **change over time** — features accumulate history, columns overwrite

**Use a column on the table when:**
- The value is **intrinsic to the record** — it's a property of the object itself, not an annotation about it (e.g., image dimensions, file format, collection date)
- There's **only ever one value** — no need for multi-annotator or multi-run support
- **No provenance needed** — you don't care who set it or when
- The value is **immutable** — it won't change after initial creation (e.g., patient age at enrollment)

**Examples:**

| Value | Feature or Column? | Why |
|-------|:---:|-----|
| Diagnosis label | Feature | Multiple annotators, controlled vocabulary, ML training label |
| Image quality score | Feature | Different reviewers may score differently, provenance matters |
| Model prediction probability | Feature | Different model runs produce different values |
| Image width in pixels | Column | Intrinsic property, single value, never changes |
| File format (PNG, DICOM) | Column | Intrinsic, immutable |
| Collection date | Column | Intrinsic to the record |
| Segmentation mask | Feature | Asset-based, tied to a specific model execution |

## Discovering Existing Features

Before creating a new feature, check what already exists. Duplicate features fragment annotations and confuse downstream consumers.

**MCP resources and tools:**
```
# Browse all features in the catalog — shows target tables, types, column schemas
Read resource: deriva://catalog/features

# Get details about a specific feature
Read resource: deriva://feature/{table_name}/{feature_name}

# See all feature values for a table (grouped by feature)
Read resource: deriva://table/{table_name}/feature-values

# See deduplicated values (newest per record per feature)
Read resource: deriva://table/{table_name}/feature-values/newest
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
- Does a feature with this purpose already exist on this table? Check `deriva://catalog/features`.
- Does a similar feature exist under a different name? (The `semantic-awareness` skill checks for this automatically, and `create_feature` warns about near-duplicates.)
- Can the existing feature be extended with new vocabulary terms instead of creating a new one?
- Is this really a feature, or should it be a column? (See [When to Use a Feature vs a Column](#when-to-use-a-feature-vs-a-column).)

## Feature Types

| Type | `create_feature` parameter | Use case |
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

The MCP resource `deriva://feature/{table}/{feature}` returns the full column schema including:
- `required_fields` — list of all column names that must be provided
- Per-column `required` boolean for each term, asset, and value column
- The vocabulary table name for term columns (tells you what values are valid)
- The data type for value columns

### Valid values by column type

**Term columns** — values must exactly match a term name in the referenced vocabulary:
```
# See valid term names for a feature's term column
Read resource: deriva://vocabulary/{vocabulary_table_name}
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

When using `add_feature_value_record`, optional columns can be:
- **Included** in some entries and **omitted** in others
- **Set to null** explicitly
- **Mixed** — some entries with the column, some without

This is common for confidence scores: human annotations may not have confidence, while model predictions always include one.

```
# Some entries with confidence, some without — valid because confidence is optional
add_feature_value_record("Image", "Diagnosis", [
    {"target_rid": "2-IMG1", "Diagnosis_Type": "Normal"},
    {"target_rid": "2-IMG2", "Diagnosis_Type": "Abnormal", "confidence": 0.87},
])
```

## Multivalued Features

Because features track provenance through executions, a single record can accumulate multiple values for the same feature over time:

- **Multiple annotators** — different pathologists label the same image in separate executions
- **Multiple model runs** — different model versions produce different predictions
- **Corrections** — a later execution overrides an earlier label

This is by design — it enables inter-annotator agreement analysis, model comparison, and audit trails. But when you need a single value per record (e.g., for training), you need feature selection.

## Feature Selection

When you need to *use* feature values — for training a model, computing metrics, or building a DataFrame — you typically need exactly one value per record. **Feature selection** is the process of choosing which value to keep when multiple exist for the same record and feature.

The choice depends on your use case:
- **Newest** — use the most recent value regardless of source (good for "latest state")
- **By workflow** — use values from a specific workflow type, e.g., only expert annotations or only model predictions
- **By execution** — use values from a specific execution run, e.g., comparing Run A vs Run B

### MCP resources (browsing and exploration)

Resources provide quick, no-parameter access for exploring what feature data exists.

| Resource | What it returns |
|----------|----------------|
| `deriva://table/{table}/feature-values` | All feature values for a table, grouped by feature name. Includes duplicates. |
| `deriva://table/{table}/feature-values/newest` | Deduplicated to one value per target record per feature — picks newest by RCT. |
| `deriva://feature/{table}/{feature}/values` | All values for a specific feature, with full provenance (Execution RID, RCT). |

### MCP tool: resource `deriva://table/{name}/features`

The tool provides filtering options that resources can't express. Returns a JSON dict mapping feature names to lists of feature value records.

Call resource `deriva://table/{name}/features` with:
- `table_name` (required): the target table (e.g., `"Image"`)
- `feature_name` (optional): fetch only a specific feature; if omitted, fetches all
- One of the following selection options (mutually exclusive):
  - `selector="newest"` — picks the most recent value (RCT) per record
  - `workflow` — a Workflow RID or Workflow_Type name. Filters to values from executions of that workflow, then picks newest
  - `execution` — an Execution RID. Filters to values from that specific execution

If none of `selector`, `workflow`, or `execution` is specified, all values are returned (including duplicates).

### Python API

```python
from deriva_ml.feature import FeatureRecord

# Newest by creation time
features = ml.resource deriva://table/{name}/features ("Image", selector=FeatureRecord.select_newest)

# Filter by execution RID, then pick newest
features = ml.resource deriva://table/{name}/features (
    "Image",
    selector=FeatureRecord.select_by_execution("3WY2"),
)

# Convenience wrapper for a single feature — returns flat list
values = list(ml.list_feature_values("Image", "Diagnosis"))
values = list(ml.list_feature_values(
    "Image", "Diagnosis",
    selector=FeatureRecord.select_newest,
))
```

**Workflow-based selection** uses `ml.select_by_workflow()`, which needs catalog access:

```python
from collections import defaultdict

features = ml.resource deriva://table/{name}/features ("Image", feature_name="Classification")
records = features.get("Classification", [])

grouped = defaultdict(list)
for r in records:
    grouped[r.Image].append(r)

selected = [ml.select_by_workflow(group, "Training") for group in grouped.values()]
```

The MCP tool's `workflow` parameter handles this grouping automatically.

**Custom selectors** can implement any logic:

```python
def select_best(records):
    return max(records, key=lambda r: getattr(r, "Confidence", 0))

features = ml.resource deriva://table/{name}/features ("Image", selector=select_best)
```

### Predefined selectors

All selectors live on `FeatureRecord` and work everywhere — catalog queries, bag queries, and Python API `bag.restructure_assets()`. The MCP tool maps string names to selectors automatically.

| Selector | Type | What it does |
|----------|------|-------------|
| `FeatureRecord.select_newest` | Static | Most recent by RCT (creation time) |
| `FeatureRecord.select_first` | Static | Earliest by RCT (original annotation) |
| `FeatureRecord.select_latest` | Static | Alias for `select_newest` (API symmetry) |
| `FeatureRecord.select_by_execution(rid)` | Factory | Filter by execution RID, then newest |
| `RecordClass.select_majority_vote(col)` | Factory | Most common value for column; ties by newest RCT. Auto-detects column for single-term features |
| `ml.select_by_workflow(records, wf)` | Instance | Filter by workflow type/RID, then newest. Not a `selector=` param — call directly on grouped records. Needs catalog access |

Import:
```python
from deriva_ml.feature import FeatureRecord
```

### Which selection method should I use?

| I want to... | MCP tool parameter | Python API |
|--------------|-------------------|-----------|
| Latest value per record | `selector="newest"` | `selector=FeatureRecord.select_newest` |
| Earliest value (original) | `selector="first"` | `selector=FeatureRecord.select_first` |
| Majority vote across annotators | `selector="majority_vote"` (requires `feature_name`) | `selector=RecordClass.select_majority_vote()` |
| Values from a workflow type | `workflow="Annotation"` | `ml.select_by_workflow(records, "Annotation")` |
| Values from a specific workflow RID | `workflow="2-ABC1"` | `ml.select_by_workflow(records, "2-ABC1")` |
| Values from one execution | `execution="3-XYZ"` | `selector=FeatureRecord.select_by_execution("3-XYZ")` |
| Single feature only | `feature_name="Diagnosis"` | `ml.list_feature_values("Image", "Diagnosis")` |
| Custom logic | Write a Python script | `selector=my_custom_function` |
| No deduplication | Omit selection params | Omit `selector` |

### MCP Resources for feature values

Feature values are also available as MCP resources, pre-deduplicated:

| Resource URI | What it returns |
|-------------|----------------|
| `deriva://table/{table}/feature-values` | All feature values (no deduplication) |
| `deriva://table/{table}/feature-values/newest` | One value per record (most recent) |
| `deriva://table/{table}/feature-values/first` | One value per record (earliest) |
| `deriva://table/{table}/feature-values/majority_vote` | One value per record (consensus) |

### Writing custom selectors

When the predefined selectors don't fit, write a Python callable with signature `(list[FeatureRecord]) -> FeatureRecord`. The same signature works for both catalog queries and bag Python API `bag.restructure_assets()`.

```python
from deriva_ml.feature import FeatureRecord

# Custom selector: highest confidence
def select_highest_confidence(records: list[FeatureRecord]) -> FeatureRecord:
    return max(records, key=lambda r: getattr(r, "Confidence", 0))

# Works with catalog queries
features = ml.resource deriva://table/{name}/features (
    "Image", feature_name="Diagnosis",
    selector=select_highest_confidence,
)

# Same selector works with bag restructuring
bag.restructure_assets(
    asset_table="Image", output_dir="./ml_data",
    group_by=["Diagnosis"], value_selector=select_highest_confidence,
)
```

When the MCP tool's built-in selectors are insufficient, write the script, test it, commit it for provenance, then run it. This follows the `catalog-operations-workflow` pattern.

### Common pitfalls

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Passing multiple selection options | Error — `selector`, `workflow`, `execution` are mutually exclusive | Pick one |
| Using `selector="newest"` in Python | Wrong — MCP uses strings, Python uses callables | Use `selector=FeatureRecord.select_newest` |
| Expecting `select_by_workflow` on a bag | Fails — needs live catalog access | Use `FeatureRecord.select_first` or filter by execution RID |
| `majority_vote` without `feature_name` | Error — needs to know which feature to look up column info | Always specify `feature_name` with `majority_vote` |
| No selector, surprised by duplicates | Returns ALL values including multiple per record | Add `selector="newest"` or another selection option |
| `workflow="Training"` vs `workflow="2-ABC1"` | Both work — auto-detected as type name vs RID | Just pass whichever you have |
| Using resource `deriva://table/{name}/features` for one feature | Works but returns a dict | Use `list_feature_values` for a flat list |

## Feature Value Table Naming

When you create a feature, DerivaML creates an association table to store feature values. The table name follows the pattern `{FeatureName}_Feature_Value` — for example, creating a feature named `"Tumor_Classification"` on the `Image` table creates a `Tumor_Classification_Feature_Value` table.

This table contains columns for:
- The target record (FK to the target table, e.g., `Image`)
- Each vocabulary term column (FK to the vocabulary table, e.g., `Tumor_Grade`)
- Each asset column (FK to the asset table)
- Each metadata column
- `Execution` (FK to the Execution table — provenance)
- `Feature_Name` (FK to the Feature_Name vocabulary)

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
features = bag.resource deriva://table/{name}/features ("Image")
values = list(bag.list_feature_values("Image", "Diagnosis",
                                       selector=FeatureRecord.select_newest))
features_on_table = bag.find_features("Image")
```

Note: `select_by_workflow` is not available on bags since it requires live catalog access.

### In preview_denormalized_dataset

Feature tables can be included in denormalization. Column names follow the pattern `{FeatureTableName}_{ColumnName}`:

```
# Schema exploration (no dataset needed)
preview_denormalized_dataset(include_tables=["Image", "Image_Classification"])
# Produces columns like: Image_RID, Image_Filename, Image_Classification_Image_Class
```

This is how the `stratify_by_column` parameter in `split_dataset` references feature columns.

### Dataset versioning impact

Adding feature values to records in a dataset does NOT automatically update existing dataset versions. Existing versions are frozen snapshots. After adding or modifying feature values, call `increment_dataset_version` to create a new version that includes the changes.

## Exploring and Navigating Features

### Understanding a feature's structure

```
# MCP — feature schema (columns, types, requirements)
Read resource: deriva://feature/{table_name}/{feature_name}
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
Read resource: deriva://feature/{table}/{feature}/values

# MCP — all features on a table, deduplicated to newest
Read resource: deriva://table/{table}/feature-values/newest

# MCP — fetch with selection/filtering
resource deriva://table/{name}/features (table_name="Image", feature_name="Diagnosis", selector="newest")
```

```python
# Python API — convenience wrapper for single feature
for v in ml.list_feature_values("Image", "Diagnosis"):
    print(f"Image {v.Image}: {v.Diagnosis_Type} (by Execution {v.Execution})")
```

### Checking what features exist on a table

```
# MCP
Read resource: deriva://catalog/features
```

```python
# Python API
features = ml.find_features("Image")
for f in features:
    print(f"  {f.feature_name}: target={f.target_table.name}, table={f.feature_table.name}")
```

## Operations Summary

### Creation and population

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Create feature | `create_feature` | `ml.create_feature()` | Vocabulary must exist first |
| Add values (simple) | `add_feature_value` | `exe.add_features()` | Single term/asset column |
| Add values (multi-column) | `add_feature_value_record` | `exe.add_features()` | Multiple columns per record |
| Delete feature | `delete_feature` | `ml.delete_feature()` | Removes feature table and all values |

### Discovery and navigation

| Operation | MCP Tool / Resource | Python API | Notes |
|-----------|---------------------|------------|-------|
| Browse all features | Resource: `deriva://catalog/features` | `ml.find_features()` | All features in catalog |
| Features on a table | Resource: `deriva://catalog/features` | `ml.find_features("Image")` | Filtered to one table |
| Feature details | Resource: `deriva://feature/{table}/{name}` | `ml.lookup_feature()` | Column types, requirements |
| Feature values (all) | Resource: `deriva://feature/{table}/{name}/values` | `ml.list_feature_values()` | With provenance |
| Table values (all) | Resource: `deriva://table/{table}/feature-values` | `ml.resource deriva://table/{name}/features ()` | Grouped by feature |
| Table values (newest) | Resource: `deriva://table/{table}/feature-values/newest` | `ml.resource deriva://table/{name}/features (..., selector=...)` | Deduplicated |
| Fetch with selection | resource `deriva://table/{name}/features` | `ml.resource deriva://table/{name}/features ()` | selector, workflow, execution |
| Values in a bag | — | `bag.resource deriva://table/{name}/features ()` | Same API on downloaded bags |
