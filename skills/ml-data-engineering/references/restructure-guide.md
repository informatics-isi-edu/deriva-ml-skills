# Restructuring Assets for ML Training

> **Stateless model:** the new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [`targets` Options](#targets-options)
- [Per-Feature Selectors](#per-feature-selectors)
- [Extracting a Column with `target_transform`](#extracting-a-column-with-target_transform)
- [Handling Missing Labels](#handling-missing-labels)
- [File Transformation](#file-transformation)
- [Directory Layout Control](#directory-layout-control)
- [ML Framework Integration](#ml-framework-integration)
- [DatasetBag API for Training Data](#datasetbag-api-for-training-data)
- [Denormalization for Flat DataFrames](#denormalization-for-flat-dataframes)
- [Common Patterns](#common-patterns)

---

## Overview

After downloading a dataset bag, Python API `bag.restructure_assets()` organizes asset files into directory hierarchies expected by ML frameworks like PyTorch ImageFolder or TensorFlow image_dataset_from_directory.

The tool reads the bag's metadata (dataset types, feature values, vocabulary terms) to determine how to place each file. It works with any asset type — images, model weights, CSVs — not just images.

## Basic Usage

`restructure_assets` is a Python API on the downloaded bag — there is no MCP tool equivalent. Download the bag first, then call the method.

### Python API

```python
bag = dataset.download_dataset_bag(version="1.0.0")

bag.restructure_assets(
    output_dir="./ml_data",
    asset_table="Image",        # auto-detected if only one asset table
    targets=["Diagnosis"],      # create subdirs by label
)
```

### Result

```
./ml_data/
  training/
    normal/
      img001.png
      img002.png
    pneumonia/
      img003.png
  testing/
    normal/
      img004.png
    pneumonia/
      img005.png
```

## `targets` Options

The `targets` parameter controls subdirectory creation. Two shapes:

### List form (default selector per feature)
```python
targets=["Diagnosis"]
# Looks up feature values for each asset, creates subdirs by value.
# Multi-valued features fall back to the most-recent annotation.
```

### Dict form (per-feature selector)
```python
from deriva_ml.feature import FeatureRecord

targets={"Diagnosis": FeatureRecord.select_newest}
# Each feature gets its own selector — see "Per-Feature Selectors" below.
```

Targets can be:

### Column names
Direct columns on the asset table:
```python
targets=["Species"]
# Result: training/mouse/..., training/human/...
```

### Feature names
Features defined on the asset table or FK-reachable tables:
```python
targets=["Diagnosis"]
# Looks up feature values for each asset, creates subdirs by value
```

### Multiple `targets` levels
Create nested hierarchies:
```python
targets=["Species", "Diagnosis"]
# Result: training/human/normal/..., training/mouse/tumor/...
```

## Per-Feature Selectors

When an asset has multiple feature values (annotations from different executions or annotators), use the dict form of `targets` to attach a selector per feature.

All selectors use `FeatureRecord` — the same type used everywhere in the API.

```python
from deriva_ml.feature import FeatureRecord

# Most recent annotation (by RCT timestamp)
bag.restructure_assets(
    output_dir="./ml_data",
    targets={"Diagnosis": FeatureRecord.select_newest},
)

# Earliest annotation (by RCT timestamp)
bag.restructure_assets(
    output_dir="./ml_data",
    targets={"Diagnosis": FeatureRecord.select_first},
)

# Most common label; ties broken by newest annotation
bag.restructure_assets(
    output_dir="./ml_data",
    targets={"Diagnosis": FeatureRecord.select_majority_vote("Diagnosis_Type")},
)

# Different selector per feature (the whole point of the dict form):
bag.restructure_assets(
    output_dir="./ml_data",
    targets={
        "Diagnosis": FeatureRecord.select_newest,
        "Severity":  FeatureRecord.select_majority_vote("Grade"),
    },
)
```

### Custom selector

A selector receives a list of `FeatureRecord` objects and returns one. `FeatureRecord` is a Pydantic model with named attributes for each column:

The selector below is specific to features that have a `Confidence` column. Direct attribute access on the Pydantic record fails loud (`AttributeError`) if applied to a feature without one — that's the contract being made explicit:

```python
from deriva_ml.feature import FeatureRecord

def select_highest_confidence(records: list[FeatureRecord]) -> FeatureRecord:
    """Pick the annotation with the highest confidence score.

    Requires the feature to have a Confidence column.
    """
    return max(records, key=lambda r: r.Confidence or 0)

bag.restructure_assets(
    output_dir="./ml_data",
    targets={"Diagnosis": select_highest_confidence},
)
```

Key `FeatureRecord` attributes:
- Named attributes for each feature column (e.g., `.Diagnosis_Type`, `.Confidence`)
- `.Execution` — RID of the execution that produced this value
- `.RCT` — ISO 8601 creation timestamp
- `.Feature_Name` — name of the feature

## Extracting a Column with `target_transform`

When a target feature has multiple columns and you want the directory name to come from one specific column (or some computation across columns), use `target_transform`:

```python
# Feature "Classification" has columns Label, Confidence, Reviewer.
# Use the Label column as the directory name:
bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Classification"],
    target_transform=lambda rec: rec.Label,
)

# Or combine columns:
bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Classification"],
    target_transform=lambda rec: f"{rec.Label}_{rec.Confidence_Bucket}",
)
```

`target_transform` is a callable `(FeatureRecord) -> str`. The returned string is used as the directory segment. Non-string returns raise `DerivaMLValidationError`.

## Handling Missing Labels

The `missing` parameter controls behavior when an asset has no matching feature value for one of its targets:

| Value | Behavior |
|---|---|
| `"unknown"` *(default)* | Place the asset in an `Unknown` subdirectory |
| `"skip"` | Omit the asset from the output tree entirely |
| `"error"` | Raise `DerivaMLValidationError` on the first missing label |

```python
# Strict mode for production training: fail loudly if any asset is unlabeled
bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Diagnosis"],
    missing="error",
)

# Drop unlabeled assets from the output (useful for exploratory work)
bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Diagnosis"],
    missing="skip",
)
```

## File Transformation

Use `file_transformer` to convert file formats during restructuring:

```python
from PIL import Image as PILImage
import numpy as np

def oct_to_png(src, dest):
    """Convert OCT DICOM to PNG during restructuring."""
    img = load_oct_dcm(str(src))
    out = dest.with_suffix(".png")
    PILImage.fromarray((img * 255).astype(np.uint8)).save(out)
    return out

bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Diagnosis"],
    file_transformer=oct_to_png,
)
```

A transformer receives `(src_path, dest_path)` and returns the actual output path (which may differ from `dest_path` if the extension changes).

## Directory Layout Control

### Dataset type mapping

By default, dataset types map to directory names (Training → "training", Testing → "testing"). Customize with `type_to_dir_map`:

```python
bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Diagnosis"],
    type_to_dir_map={"Training": "train", "Testing": "test", "Validation": "val"},
)
# Result: train/normal/..., test/normal/..., val/normal/...
```

### Symlinks vs copies

```python
# Default: symlinks (saves disk space)
bag.restructure_assets(output_dir="./ml_data", use_symlinks=True)

# Copy files instead (portable, safe to delete the bag)
bag.restructure_assets(output_dir="./ml_data", use_symlinks=False)
```

### Datasets without types

Datasets that have no dataset type are treated as Testing. This is common for prediction/inference datasets.

### Assets without labels

The `missing` parameter controls behavior — see [Handling Missing Labels](#handling-missing-labels) above.

### Vocabulary enforcement

By default, features used in `targets` must have vocabulary terms:
```python
# Allow non-vocabulary features (e.g., numeric or free-text columns)
bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Score"],
    enforce_vocabulary=False,
)
```

## Upload Tuning

When uploading large assets, the default timeouts may not suffice. Pass these to `exe.commit_output_assets()`:

```python
# Large files on a slow connection
exe.commit_output_assets(
    timeout=(1800, 1800),         # 30 min per chunk
    chunk_size=25 * 1024 * 1024,  # 25 MB chunks
    max_retries=5,
    retry_delay=10.0,
)
```

See the `troubleshoot-execution` skill's execution lifecycle reference for the full `commit_output_assets()` parameter documentation.

## ML Framework Integration

### PyTorch ImageFolder

```python
from torchvision.datasets import ImageFolder
from torchvision import transforms

bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Diagnosis"],
    type_to_dir_map={"Training": "train", "Testing": "test"},
)

train_dataset = ImageFolder(
    root="./ml_data/train",
    transform=transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
)
```

### TensorFlow image_dataset_from_directory

```python
import tensorflow as tf

bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Diagnosis"],
)

train_ds = tf.keras.utils.image_dataset_from_directory(
    "./ml_data/training",
    image_size=(224, 224),
    batch_size=32,
)
```

### Tabular ML with denormalization

For non-image tasks, use `get_denormalized_as_dataframe` instead:

```python
df = bag.get_denormalized_as_dataframe(include_tables=["Subject", "Measurement"])
# Returns a flat DataFrame with joined columns
```

## DatasetBag API for Training Data

Once downloaded, a `DatasetBag` provides a rich API for accessing training data:

### Browsing data

```python
# List all tables
bag.list_tables()  # ["Image", "Subject", "Species", ...]

# Get table as DataFrame
images_df = bag.get_table_as_dataframe("Image")

# Get table as list of dicts
subjects = list(bag.get_table_as_dict("Subject"))

# List members grouped by table
members = bag.list_dataset_members()  # {"Image": [...], "Subject": [...]}
members = bag.list_dataset_members(recurse=True)  # includes nested datasets
```

### Feature values

```python
from deriva_ml.feature import FeatureRecord

# Discover features on a table
features = bag.find_features("Image")  # [Feature(name="Diagnosis", ...)]

# Fetch feature values (one feature per call). Returns an iterator of FeatureRecord.
records = bag.feature_values(
    "Image",
    "Diagnosis",
    selector=FeatureRecord.select_newest,   # collapse multi-value groups
)

# Feature values for a specific record — read all, then filter by target RID
record = next(
    (r for r in bag.feature_values("Image", "Diagnosis")
     if r.Image == "2-ABCD"),
    None,
)
```

### Denormalization

```python
# Flatten to wide table — joins across FK paths
df = bag.get_denormalized_as_dataframe(include_tables=["Image", "Subject"])

# Same as dict
rows = bag.get_denormalized_as_dict(include_tables=["Image", "Subject"])
```

### Dataset hierarchy

```python
# Both directions of nested relationships in one call
relations = bag.list_dataset_children()
relations = bag.list_dataset_children(recurse=True)

# Element types registered for this dataset
element_types = bag.list_dataset_element_types()
```

## Denormalization for Flat DataFrames

The `deriva_ml_denormalize_dataset` MCP tool and `bag.get_denormalized_as_dataframe()` method join dataset tables into a single flat DataFrame, following FK relationships. This is the fastest path from catalog data to ML-ready tabular features.

### MCP tool

```
# Explore schema shape (no dataset needed)
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    include_tables=["Image", "Subject", "Diagnosis"]
)

# With dataset-scoped data
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    include_tables=["Image", "Subject", "Diagnosis"],
    dataset_rid="2-XXXX",
    version="1.0.0",
    limit=50
)
```

### Column naming

Denormalized columns follow the pattern `TableName_ColumnName`:
- `Image_Filename`, `Image_URL`
- `Subject_Age`, `Subject_Sex`
- `Diagnosis_Name` (vocabulary term name)

### Include tables

Only include tables you actually need — this keeps the join efficient and avoids pulling in unrelated data through FK chains.

Tables don't need to be explicit dataset members — denormalize follows FK chains to fetch related records automatically. If the schema has multiple FK paths between two tables, you'll get a `DerivaMLException` asking you to include intermediate tables to disambiguate. For multi-hop FK traversal details, ambiguous path resolution, and troubleshooting, see `denormalize-guide.md`.

## Common Patterns

### Image classification pipeline

```python
# 1. Download dataset
bag = dataset.download_dataset_bag(version="1.0.0")

# 2. Restructure for PyTorch
bag.restructure_assets(
    output_dir="./data",
    targets={"Diagnosis": FeatureRecord.select_newest},
    type_to_dir_map={"Training": "train", "Testing": "test"},
)

# 3. Create dataloaders
train_ds = ImageFolder("./data/train", transform=train_transform)
test_ds = ImageFolder("./data/test", transform=test_transform)
```

### Tabular classification

```python
# 1. Download dataset (metadata only — no asset files needed)
bag = dataset.download_dataset_bag(version="1.0.0", materialize=False)

# 2. Build flat DataFrame
df = bag.get_denormalized_as_dataframe(include_tables=["Subject", "Measurement"])

# 3. Split features and labels
X = df[["Subject_Age", "Subject_Weight", "Measurement_Value"]]
y = df["Subject_Diagnosis"]
```

### Multi-label with custom file conversion

```python
bag.restructure_assets(
    output_dir="./data",
    # Per-feature selector picks the most-recent annotation for each:
    targets={
        "Primary_Diagnosis": FeatureRecord.select_latest,
        "Severity":          FeatureRecord.select_latest,
    },
    file_transformer=dicom_to_png,
    use_symlinks=False,  # copy for portability
)
```

## Reference Resources

| Resource / Tool | Purpose |
|-----------------|---------|
| Python API `dataset.download_dataset_bag(version)` | Download bag (supports `exclude_tables`, `timeout`, `materialize`) |
| Python API `bag.restructure_assets()` | Organize assets into ML-ready directory layouts |
| Python API `exe.download_asset(rid)` | Download a single asset by RID (Execution method) |
| Python API `exe.asset_file_path()` | Register a file for upload |
| Python API `exe.commit_output_assets()` | Commit staged files to catalog (uploads + writes rows + transitions execution to `Uploaded`) |
| `deriva_ml_denormalize_dataset` | Schema shape + size estimates (no dataset needed), or flatten dataset tables with `dataset_rid` + `limit` |
| `deriva_ml_bag_info` | Preview row counts, asset sizes, and manifest per table |
| `deriva_ml_list_feature_values` | Access feature values from the catalog (or `bag.feature_values()` from a downloaded bag) |
| `deriva_ml_get_dataset` | Dataset details including version and element types |
| `deriva_ml_list_features` | Available features for building training labels |
| Creating an asset table | No dedicated tool; use the manual `create_table` recipe — see `work-with-assets/references/concepts.md` |
