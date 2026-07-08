---
name: ml-data-engineering
description: "Use when getting data OUT of a DerivaML dataset and INTO an ML pipeline — restructuring assets for PyTorch/TensorFlow/ImageFolder, building training DataFrames via denormalize, working with the DatasetBag API, handling multi-annotator labels with value selectors, converting file formats during restructuring, and previewing bag contents before downloading. Covers training, inference, and evaluation data preparation. Triggers on: 'restructure assets', 'prepare training data', 'build dataframe', 'denormalize', 'wide table', 'flat table', 'join tables', 'columns only', 'preview columns', 'ImageFolder', 'PyTorch data', 'value selector for training', 'convert DICOM', 'bag contents', 'get data for model'. Do NOT use for creating, splitting, or versioning datasets — use dataset-lifecycle for those."
---

# Preparing Training Data from a DerivaML Dataset

You have a dataset — now get it into your ML pipeline. This skill covers extracting, restructuring, and transforming dataset contents for training, evaluation, or analysis.

For creating, populating, splitting, versioning, or browsing datasets, see the `dataset-lifecycle` skill.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Step 1: Download the Dataset

> **Where the four-step recipe lives.** The full download recipe (preview → validate version → download → validate bag), the dev-version pitfall, and the option matrix (`materialize`, `timeout`, `exclude_tables`, `use_minid`, `DatasetSpecConfig`) belong with the dataset abstraction itself — see `/deriva-ml:dataset-lifecycle` Phase 7 → "Download workflow". For the BDBag format mechanics underneath (manifest, checksums, materialization, the `bdbag` CLI, `DerivaDownload` / `DerivaExport` Python classes), see `/deriva:download-bag` *(deriva-skills)*. This skill picks up from "you have a downloaded bag" — Step 2 onward.

The condensed version, for in-context reference:

```python
# Preview row counts and asset sizes before committing to a download
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1",
                   dataset_rid="2-XXXX", version="1.0.0")

# Then download — standalone, or inside an execution for provenance
bag = dataset.download_dataset_bag(version="1.0.0")
bag = exe.download_dataset_bag(DatasetSpec(rid="2-XXXX", version="1.0.0"))
```

## Step 2: Choose Your Extraction Approach

### Option A: Restructure assets for ML frameworks

Best when you need files organized into directories (image classification, object detection).

```python
# Python API — after downloading
bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Diagnosis"],
)
```

Creates:
```
./ml_data/
  training/
    normal/
      img001.png
    pneumonia/
      img003.png
  testing/
    normal/
      img004.png
```

For the full restructuring guide — `targets` and `target_transform` shapes, per-feature selectors, file transformers, directory layout control, and ML framework integration — see `references/restructure-guide.md`.

### Option B: Build a flat DataFrame

Best for tabular ML, feature engineering, or interactive exploration.

**Step 1 — Explore the schema shape (no dataset needed):**

Don't guess the table names. If you don't already know them, list the catalog's tables live first — read `ReadMcpResourceTool(uri="deriva://catalog/{hostname}/{catalog_id}/tables")` (or `rag_search` for concept-based discovery, e.g. "imaging tables") — then pass the real names into `include_tables`.

```
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    include_tables=["Image", "Subject", "Diagnosis"]
)
```
Returns column names/types, join path, and per-table row counts and asset sizes. No dataset RID required — use this to explore what a denormalized join would look like before you have a dataset, or to verify FK paths and discover column names for `stratify_by_column`.

**Step 2 — Fetch actual rows from a dataset:**
```
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    include_tables=["Image", "Subject", "Diagnosis"],
    dataset_rid="2-XXXX",
    version="1.0.0",
    limit=50
)
```

**From a downloaded bag (Python API):**
```python
# Preview columns without data
columns = bag.list_denormalized_columns(include_tables=["Image", "Subject"])

# Fetch the data
df = bag.get_denormalized_as_dataframe(include_tables=["Image", "Subject"])
```

Denormalized columns follow the pattern `TableName_ColumnName`:

| Pattern | Example | Description |
|---------|---------|-------------|
| `Image_URL` | `https://...` | Asset download URL |
| `Image_Filename` | `img_001.png` | Original filename |
| `Subject_Age` | `42` | Numeric feature |
| `Subject_Sex` | `Male` | Categorical feature from vocabulary |
| `Diagnosis_Label` | `Malignant` | Classification label from vocabulary |
| `Measurement_Value` | `3.14` | Numeric measurement |

Only include tables you actually need — this keeps the join efficient. If the schema has multiple FK paths between two tables (e.g., `Image → Subject` direct and `Image → Observation → Subject`), you'll get an error asking you to include intermediate tables to disambiguate. See `references/denormalize-guide.md` for multi-hop FK traversal, ambiguous path resolution, and troubleshooting.

### Option C: Access individual tables

When you need fine-grained control or just one table:

```python
# From a downloaded bag
images_df = bag.get_table_as_dataframe("Image")
subjects = list(bag.get_table_as_dict("Subject"))

# From the catalog directly — column-projected, filtered query.
# query_attribute uses ERMrest path-expression syntax: filter is part of the path.
query_attribute(hostname="data.example.org", catalog_id="1",
                path="<schema>:Image/Subject=2-SUB1",
                attributes=["RID", "Filename", "Subject"])
```

## Step 3: Work with Features and Labels

### Discover features on a table

```python
# From a bag
features = bag.find_features("Image")

# From the catalog
deriva_ml_list_features(hostname="data.example.org", catalog_id="1", target_table="Image")
```

### Fetch feature values

```python
from deriva_ml.feature import FeatureRecord

# From a bag — with deduplication. Returns an iterator of FeatureRecord.
records = bag.feature_values(
    "Image",
    "Diagnosis",
    selector=FeatureRecord.select_newest,   # most recent annotation per record
)

# From the catalog
deriva_ml_list_feature_values(
    hostname="data.example.org",
    catalog_id="1",
    target_table="Image",
    feature_name="Diagnosis",
    selector="newest"
)
```

### Handling multiple annotators / model runs

When the same record has values from different executions, use selection options:
- `selector="newest"` — picks the most recent by creation time
- `workflow="Training"` — filters by workflow type, then newest
- `execution="3-XYZ"` — filters by specific execution

## Step 4: Build Your Training Pipeline

### Image classification

```python
from torchvision.datasets import ImageFolder
from torchvision import transforms

# 1. Download and restructure
bag = dataset.download_dataset_bag(version="1.0.0")
bag.restructure_assets(
    output_dir="./data",
    targets=["Diagnosis"],
    type_to_dir_map={"Training": "train", "Testing": "test"},
)

# 2. Create dataloaders
train_ds = ImageFolder("./data/train", transform=transforms.Compose([
    transforms.Resize(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
]))
```

### Tabular classification

```python
# 1. Download metadata only (no asset files needed)
bag = dataset.download_dataset_bag(version="1.0.0", materialize=False)

# 2. Build flat DataFrame
df = bag.get_denormalized_as_dataframe(include_tables=["Subject", "Measurement"])

# 3. Split features and labels
X = df[["Subject_Age", "Subject_Weight", "Measurement_Value"]]
y = df["Subject_Diagnosis"]

# 4. Encode categoricals
import pandas as pd
X_encoded = pd.get_dummies(X, columns=["Subject_Sex"])
```

### TensorFlow

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

### Multi-label with file conversion

```python
from deriva_ml.feature import FeatureRecord

bag.restructure_assets(
    output_dir="./data",
    # Per-feature selector dict — picks the latest annotation for each feature.
    targets={
        "Primary_Diagnosis": FeatureRecord.select_newest,
        "Severity": FeatureRecord.select_newest,
    },
    file_transformer=dicom_to_png,
    use_symlinks=False,
)
```

The `targets=` dict form lets you attach a different selector per feature; the list form (`targets=["Primary_Diagnosis", "Severity"]`) takes the most-recent annotation for each feature.

## DatasetBag API Reference

Once downloaded, a `DatasetBag` provides:

```python
# Tables
bag.list_tables()                            # ["Image", "Subject", ...]
bag.get_table_as_dataframe("Image")          # pandas DataFrame
bag.get_table_as_dict("Subject")             # generator of dicts

# Members
bag.list_dataset_members()                   # {"Image": [...], "Subject": [...]}
bag.list_dataset_members(recurse=True)       # includes nested datasets

# Hierarchy (both directions in one call)
bag.list_dataset_children()
bag.list_dataset_children(recurse=True)
bag.list_dataset_element_types()

# Features
bag.find_features("Image")                   # [Feature(name="Diagnosis", ...)]
bag.feature_values("Image", "Diagnosis", selector=FeatureRecord.select_newest)

# Denormalization
bag.get_denormalized_as_dataframe(include_tables=["Image", "Subject"])
bag.get_denormalized_as_dict(include_tables=["Image", "Subject"])

# Restructuring
bag.restructure_assets(output_dir="./data", targets=["Diagnosis"])
```

## Reference Resources

- `references/restructure-guide.md` — Full guide: `targets` and `target_transform` shapes, per-feature selectors, file transformers, ML framework integration, directory layout control
- `deriva://docs/datasets` — Full user guide to datasets and BDBags
- `deriva_ml_list_features(hostname, catalog_id)` — Available features for building training labels

## Related Skills

- **`dataset-lifecycle`** — Creating, populating, splitting, versioning, and browsing datasets. Start there if you don't have a dataset yet.
- **`debug-bag-contents`** — Diagnosing missing data in bag exports.
- **`create-feature`** — Creating the features and labels that this skill consumes.
- **`execution-lifecycle`** — Running the experiment that uses the prepared data.
