# Restructuring Assets for ML

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [group_by Options](#group_by-options)
- [Value Selectors](#value-selectors)
- [File Transformers](#file-transformers)
- [Directory Layout Options](#directory-layout-options)
- [ML Framework Patterns](#ml-framework-patterns)
- [Upload Tuning](#upload-tuning)

---

## Overview

After downloading a dataset bag, Python API `bag.restructure_assets()` organizes asset files into directory hierarchies expected by ML frameworks. It reads the bag's metadata (dataset types, feature values, vocabulary terms) to determine placement. This reference covers the full parameter set and integration patterns.

For the complete asset upload and download workflow, see `workflow.md`. For background on asset tables and provenance, see `concepts.md`.

## Basic Usage

### MCP tool

```
restructure_assets(
    dataset_rid="2-XXXX",
    asset_table="Image",
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    version="1.0.0"
)
```

### Python API

```python
bag = dataset.download_dataset_bag(version="1.0.0")
bag.restructure_assets(
    output_dir="./ml_data",
    asset_table="Image",        # auto-detected if only one asset table
    group_by=["Diagnosis"],
)
```

## group_by Options

The `group_by` list determines the subdirectory hierarchy. Each item can be:

| Type | Example | How it works |
|------|---------|--------------|
| Column name | `"Species"` | Direct column on the asset table |
| Feature name | `"Diagnosis"` | Feature values for each asset (via feature table) |
| Feature.column | `"Classification.Label"` | Specific column from a multi-column feature |

Multiple `group_by` levels create nested directories:
```python
group_by=["Species", "Diagnosis"]
# → training/human/normal/..., training/mouse/tumor/...
```

## Value Selectors

When an asset has multiple feature values (from different annotators or executions), a `value_selector` picks one.

### Built-in selectors

```python
from deriva_ml.dataset.dataset_bag import select_majority_vote, select_latest, select_first

# Most common label; ties broken by newest
value_selector=select_majority_vote

# Most recent annotation (by RCT timestamp)
value_selector=select_latest

# Earliest annotation
value_selector=select_first
```

### Custom selector

Receives a list of `FeatureValueRecord` objects, returns one:

```python
def select_highest_confidence(records):
    return max(records, key=lambda r: r.raw_record.get("Confidence", 0))
```

`FeatureValueRecord` attributes:
- `.value` — the feature value (e.g., vocabulary term name)
- `.raw_record` — full row dict from the feature table
- `.execution_rid` — which execution produced this annotation
- `.rct` — record creation timestamp

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
    group_by=["Diagnosis"],
    file_transformer=dicom_to_png,
)
```

A transformer receives `(src_path, dest_path)` and returns the actual output path.

## Directory Layout Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_symlinks` | `True` | Symlink to original files (saves disk). Set `False` to copy. |
| `type_to_dir_map` | Auto | Map dataset types to directory names: `{"Training": "train", "Testing": "test"}` |
| `enforce_vocabulary` | `True` | Require features in `group_by` to have vocabulary terms. Set `False` for any feature type. |

**Datasets without types** → treated as Testing (common for prediction/inference).

**Assets without labels** → placed in `"Unknown"` subdirectory.

## ML Framework Patterns

### PyTorch ImageFolder

```python
from torchvision.datasets import ImageFolder

bag.restructure_assets(
    output_dir="./data",
    group_by=["Diagnosis"],
    type_to_dir_map={"Training": "train", "Testing": "test"},
)
train_ds = ImageFolder("./data/train", transform=train_transform)
```

### TensorFlow image_dataset_from_directory

```python
import tensorflow as tf

bag.restructure_assets(
    output_dir="./data",
    group_by=["Diagnosis"],
)
train_ds = tf.keras.utils.image_dataset_from_directory(
    "./data/training", image_size=(224, 224), batch_size=32
)
```

## Upload Tuning

When uploading large assets, the default timeouts may not suffice. See the `troubleshoot-execution` skill's execution lifecycle reference for full `upload_execution_outputs()` parameter documentation.

Quick reference:

```python
# Large files on slow connection
exe.upload_execution_outputs(
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
| Python API `ml.download_asset(rid)` | Download single asset by RID |
| Python API `exe.asset_file_path()` | Register file for upload |
| Python API `exe.upload_execution_outputs()` | Upload staged files to catalog |
| `create_asset_table` | Create new asset table with custom columns |
| `estimate_bag_size` | Preview what a download will contain |
