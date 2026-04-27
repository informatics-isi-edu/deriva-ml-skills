---
name: ml-data-engineering
description: "ALWAYS use this skill when getting data OUT of a DerivaML dataset and INTO an ML pipeline — restructuring assets for PyTorch/TensorFlow/ImageFolder, building training DataFrames via denormalize, working with the DatasetBag API, handling multi-annotator labels with value selectors, converting file formats during restructuring, and previewing bag contents before downloading. Covers training, inference, and evaluation data preparation. Triggers on: 'restructure assets', 'prepare training data', 'build dataframe', 'denormalize', 'wide table', 'flat table', 'join tables', 'columns only', 'preview columns', 'ImageFolder', 'PyTorch data', 'value selector for training', 'convert DICOM', 'bag contents', 'get data for model'. Do NOT use for creating, splitting, or versioning datasets — use dataset-lifecycle for those."
disable-model-invocation: true
---

# Preparing Training Data from a DerivaML Dataset

You have a dataset — now get it into your ML pipeline. This skill covers extracting, restructuring, and transforming dataset contents for training, evaluation, or analysis.

For creating, populating, splitting, versioning, or browsing datasets, see the `dataset-lifecycle` skill.


## Prerequisite: Connect to a Catalog

All operations in this skill require an active catalog connection. Before anything else:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.


## Step 1: Download the Dataset

### Preview before downloading

```
estimate_bag_size(dataset_rid="2-XXXX", version="1.0.0")
```

Returns row counts and asset sizes per table so you know what to expect.

### Download as BDBag

```python
# Python API -- standalone download (no execution required)
bag = dataset.download_dataset_bag(version="1.0.0")

# Python API -- within an execution context (records provenance)
bag = exe.download_dataset_bag(DatasetSpec(rid="2-XXXX", version="1.0.0"))
```

For slow downloads, increase the timeout or exclude tables:
```python
bag = dataset.download_dataset_bag(version="1.0.0", timeout=[10, 1800])
bag = dataset.download_dataset_bag(version="1.0.0", exclude_tables=["Study"])
```

Use `materialize=False` to skip downloading actual asset files (only metadata).

For details on bag contents, FK traversal, and caching, see the `dataset-lifecycle` skill's `bags.md` reference.

## Step 2: Choose Your Extraction Approach

### Option A: Restructure assets for ML frameworks

Best when you need files organized into directories (image classification, object detection).

```python
# Python API — after downloading
bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"]
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

For the full restructuring guide — `group_by` options, value selectors, file transformers, directory layout control, and ML framework integration — see `references/restructure-guide.md`.

### Option B: Build a flat DataFrame

Best for tabular ML, feature engineering, or interactive exploration.

**Step 1 — Explore the schema shape (no dataset needed):**
```
preview_denormalized_dataset(
    include_tables=["Image", "Subject", "Diagnosis"]
)
```
Returns column names/types, join path, and per-table row counts and asset sizes. No dataset RID required — use this to explore what a denormalized join would look like before you have a dataset, or to verify FK paths and discover column names for `stratify_by_column`.

**Step 2 — Fetch actual rows from a dataset:**
```
preview_denormalized_dataset(
    include_tables=["Image", "Subject", "Diagnosis"],
    dataset_rid="2-XXXX",
    version="1.0.0",
    limit=50
)
```

**From a downloaded bag (Python API):**
```python
# Preview columns without data
columns = bag.denormalize_columns(include_tables=["Image", "Subject"])

# Fetch the data
df = bag.denormalize_as_dataframe(include_tables=["Image", "Subject"])
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

# From the catalog directly
preview_table(table_name="Image", columns=["RID", "Filename", "Subject"],
            filters={"Subject": "2-SUB1"})
```

## Step 3: Work with Features and Labels

### Discover features on a table

```python
# From a bag
features = bag.find_features("Image")

# From the catalog
resource deriva://table/{name}/features (table_name="Image")
```

### Fetch feature values

```python
# From a bag — with deduplication
feature_df = bag.resource deriva://table/{name}/features (
    table="Image",
    feature_name="Diagnosis",
    selector="newest",           # most recent annotation per record
)

# From the catalog
resource deriva://table/{name}/features (table_name="Image", feature_name="Diagnosis", selector="newest")
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
    group_by=["Diagnosis"],
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
df = bag.denormalize_as_dataframe(include_tables=["Subject", "Measurement"])

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
    group_by=["Diagnosis"],
)

train_ds = tf.keras.utils.image_dataset_from_directory(
    "./ml_data/training",
    image_size=(224, 224),
    batch_size=32,
)
```

### Multi-label with file conversion

```python
bag.restructure_assets(
    output_dir="./data",
    group_by=["Primary_Diagnosis", "Severity"],  # nested dirs
    value_selector=FeatureRecord.select_latest,
    file_transformer=dicom_to_png,
    use_symlinks=False,
)
```

## DatasetBag API Reference

Once downloaded, a `DatasetBag` provides:

```python
# Tables
bag.list_tables()                            # ["Image", "Subject", ...]
bag.get_table_as_dataframe("Image")          # pandas DataFrame
bag.get_table_as_dict("Subject")             # generator of dicts

# Members
bag.resource deriva://dataset/{rid}/members ()                   # {"Image": [...], "Subject": [...]}
bag.resource deriva://dataset/{rid}/members (recurse=True)       # includes nested datasets

# Hierarchy
bag.list_dataset_children()
bag.list_dataset_children(recurse=True)
bag.list_dataset_element_types()

# Features
bag.find_features("Image")                   # [Feature(name="Diagnosis", ...)]
bag.resource deriva://table/{name}/features (table="Image", feature_name="Diagnosis", selector="newest")

# Denormalization
bag.denormalize_as_dataframe(include_tables=["Image", "Subject"])
bag.denormalize_as_dict(include_tables=["Image", "Subject"])

# Restructuring
bag.restructure_assets(output_dir="./data", group_by=["Diagnosis"])
```

## Reference Resources

- `references/restructure-guide.md` — Full guide: group_by options, value selectors, file transformers, ML framework integration, directory layout control
- `deriva://docs/datasets` — Full user guide to datasets and BDBags
- `deriva://catalog/features` — Available features for building training labels

## Related Skills

- **`dataset-lifecycle`** — Creating, populating, splitting, versioning, and browsing datasets. Start there if you don't have a dataset yet.
- **`debug-bag-contents`** — Diagnosing missing data in bag exports.
- **`create-feature`** — Creating the features and labels that this skill consumes.
- **`execution-lifecycle`** — Running the experiment that uses the prepared data.
