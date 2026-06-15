# Restructuring Assets for ML

> The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them. (Most of this skill is Python-API-driven; only the few MCP tool examples need the parameters.)

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [`targets` Options](#targets-options)
- [Per-Feature Selectors](#per-feature-selectors)
- [Extracting a Column with `target_transform`](#extracting-a-column-with-target_transform)
- [Handling Missing Labels](#handling-missing-labels)
- [File Transformers](#file-transformers)
- [Directory Layout Options](#directory-layout-options)
- [ML Framework Patterns](#ml-framework-patterns)
- [Upload Tuning](#upload-tuning)

---

## Overview

After downloading a dataset bag, Python API `bag.restructure_assets()` organizes asset files into directory hierarchies expected by ML frameworks. It reads the bag's metadata (dataset types, feature values, vocabulary terms) to determine placement. This reference covers the full parameter set and integration patterns.

For the complete asset upload and download workflow, see `workflow.md`. For background on asset tables and provenance, see `concepts.md`.

## Basic Usage

`restructure_assets` is a Python-only operation on a downloaded `DatasetBag` — there is no MCP tool equivalent. Download the bag (via MCP or Python) first, then call `restructure_assets()` on the resulting bag object:

### Python API

```python
bag = dataset.download_dataset_bag(version="1.0.0")
bag.restructure_assets(
    output_dir="./ml_data",
    asset_table="Image",        # auto-detected if only one asset table
    targets=["Diagnosis"],
)
```

## `targets` Options

`targets` takes either a list (default selector per feature) or a dict mapping each feature name to a selector. Items can be:

| Type | Example | How it works |
|------|---------|--------------|
| Column name | `"Species"` | Direct column on the asset table |
| Feature name | `"Diagnosis"` | Feature values for each asset (via feature table) |

Multiple `targets` levels create nested directories:
```python
targets=["Species", "Diagnosis"]
# → training/human/normal/..., training/mouse/tumor/...
```

## Per-Feature Selectors

When an asset has multiple feature values (from different annotators or executions), use the dict form of `targets` to attach a selector per feature.

### Built-in selectors

```python
from deriva_ml.feature import FeatureRecord

# Most common label; ties broken by newest
targets={"Diagnosis": FeatureRecord.select_majority_vote("Diagnosis_Type")}

# Most recent annotation (by RCT timestamp)
targets={"Diagnosis": FeatureRecord.select_latest}

# Earliest annotation
targets={"Diagnosis": FeatureRecord.select_first}

# Different selector per feature:
targets={
    "Diagnosis": FeatureRecord.select_newest,
    "Severity":  FeatureRecord.select_majority_vote("Grade"),
}
```

### Custom selector

Receives a list of `FeatureRecord` objects, returns one:

Specific to features with a `Confidence` column — direct attribute access raises `AttributeError` on features without one (the right failure mode):

```python
from deriva_ml.feature import FeatureRecord

def select_highest_confidence(records: list[FeatureRecord]) -> FeatureRecord:
    return max(records, key=lambda r: r.Confidence or 0)

bag.restructure_assets(
    output_dir="./ml_data",
    targets={"Diagnosis": select_highest_confidence},
)
```

`FeatureRecord` attributes:
- Named attributes for each feature column (e.g., `.Diagnosis_Type`, `.Confidence`)
- `.Execution` — RID of the execution that produced this value
- `.RCT` — record creation timestamp
- `.Feature_Name` — name of the feature

## Extracting a Column with `target_transform`

When a feature has multiple columns and you want the directory name to come from one specific column, use `target_transform`:

```python
# Feature "Classification" has columns Label, Confidence, Reviewer.
# Use the Label column as the directory name:
bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Classification"],
    target_transform=lambda rec: rec.Label,
)
```

`target_transform` is `(FeatureRecord) -> str`. The returned string is the directory segment; non-string returns raise `DerivaMLValidationError`.

## Handling Missing Labels

The `missing` parameter controls behavior when an asset has no matching feature value for one of its targets:

| Value | Behavior |
|---|---|
| `"unknown"` *(default)* | Place the asset in an `Unknown` subdirectory |
| `"skip"` | Omit the asset from the output tree entirely |
| `"error"` | Raise `DerivaMLValidationError` on the first missing label |

## File Transformers

Convert file formats during restructuring:

```python
def dicom_to_png(src, dest):
    img = load_dicom(str(src))
    out = dest.with_suffix(".png")
    PILImage.fromarray(img).save(out)
    return out

bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Diagnosis"],
    file_transformer=dicom_to_png,
)
```

A transformer receives `(src_path, dest_path)` and returns the actual output path.

## Directory Layout Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_symlinks` | `True` | Symlink to original files (saves disk). Set `False` to copy. |
| `type_to_dir_map` | Auto | Map dataset types to directory names: `{"Training": "train", "Testing": "test"}` |
| `enforce_vocabulary` | `True` | Require features in `targets` to have vocabulary terms. Set `False` for any feature type. |
| `missing` | `"unknown"` | Behavior on missing labels — see [Handling Missing Labels](#handling-missing-labels) above. |

**Datasets without types** → treated as Testing (common for prediction/inference).

## ML Framework Patterns

### PyTorch ImageFolder

```python
from torchvision.datasets import ImageFolder

bag.restructure_assets(
    output_dir="./data",
    targets=["Diagnosis"],
    type_to_dir_map={"Training": "train", "Testing": "test"},
)
train_ds = ImageFolder("./data/train", transform=train_transform)
```

### TensorFlow image_dataset_from_directory

```python
import tensorflow as tf

bag.restructure_assets(
    output_dir="./data",
    targets=["Diagnosis"],
)
train_ds = tf.keras.utils.image_dataset_from_directory(
    "./data/training", image_size=(224, 224), batch_size=32
)
```

## Upload Tuning

When uploading large assets, the default timeouts may not suffice. See the `troubleshoot-execution` skill's execution lifecycle reference for full `commit_output_assets()` parameter documentation.

Quick reference:

```python
# Large files on slow connection
exe.commit_output_assets(
    timeout=(1800, 1800),        # 30 min per chunk
    chunk_size=25 * 1024 * 1024, # 25 MB chunks
    max_retries=5,
    retry_delay=10.0,
)
```

## Reference Resources

| Resource / Tool | Purpose |
|-----------------|---------|
| Python API `bag.restructure_assets()` | Organize assets into ML-ready layouts |
| Python API `dataset.download_dataset_bag(version)` | Download bag with assets |
| Python API `exe.download_asset(rid)` | Download single asset by RID (Execution method) |
| Python API `exe.asset_file_path()` | Register file for upload |
| Python API `exe.commit_output_assets()` | Commit staged files to catalog (uploads + writes rows + transitions execution to `Uploaded`) |
| (gap) Creating an asset table | No dedicated tool; use the manual `create_table` recipe — see `concepts.md` |
| `deriva_ml_bag_info(hostname, catalog_id, dataset_rid, version)` | Preview what a download will contain |
