# Runner Interface and Data Access

How the DerivaML runner invokes model functions, how models access input data, and how models produce output files. This is the reference for understanding the runtime environment your model function executes in.

## Table of Contents

1. [The Model Function Protocol](#the-model-function-protocol)
2. [How the Runner Invokes Models](#how-the-runner-invokes-models)
3. [Accessing Input Datasets](#accessing-input-datasets)
4. [Restructuring Bags for ML Frameworks](#restructuring-bags-for-ml-frameworks)
5. [Accessing Input Assets](#accessing-input-assets)
6. [Registering Output Files](#registering-output-files)
7. [Recording Feature Values](#recording-feature-values)
8. [Complete Data Flow](#complete-data-flow)
9. [Complete Example](#complete-example)

---

## The Model Function Protocol

DerivaML models are plain Python functions with a specific parameter convention:

```python
def my_model(
    # Model-specific parameters (become configurable hyperparameters)
    learning_rate: float = 1e-3,
    epochs: int = 10,
    batch_size: int = 64,
    # Framework-injected parameters (always last, always default None)
    ml_instance: DerivaML = None,
    execution: Execution | None = None,
) -> None:
    ...
```

**Rules:**

- `ml_instance` and `execution` must be the last two parameters with default `None`.
- All other parameters become configurable via hydra-zen. Every parameter with a default value is exposed in the Hydra config and can be overridden from the CLI or experiment configs.
- The function returns `None` — results are captured through output files registered with `execution.asset_file_path()`, not return values.
- Avoid side effects outside the execution context (no writing to arbitrary paths, no direct catalog mutations). All outputs go through the execution's staging mechanism.

## How the Runner Invokes Models

The `deriva-ml-run` CLI calls `run_model()` in the runner, which:

1. Resolves the Hydra config and creates a `functools.partial` from your model function (this is what `zen_partial=True` does — it pre-binds all hyperparameters but leaves `ml_instance` and `execution` unbound).
2. Creates an `Execution` record in the catalog with the configured workflow, datasets, and assets.
3. Enters the execution context manager, which:
   - Sets the execution status to Running
   - Downloads all configured input datasets as BDBags
   - Downloads all configured input assets
   - Populates `execution.datasets` and `execution.asset_paths`
4. Calls your model function: `model_config(ml_instance=ml_instance, execution=exec_context)`
5. On exit, sets status to Completed (or Failed on exception).
6. Uploads all files registered via `asset_file_path()` to the catalog.

Your model function runs inside step 4. By the time it's called, all input data is already downloaded and available through the execution object.

## Accessing Input Datasets

Datasets configured in the experiment are downloaded as BDBags before your model runs. Access them via `execution.datasets`:

```python
# execution.datasets is a list[DatasetBag]
for dataset in execution.datasets:
    print(dataset.name)        # Dataset name from catalog
    print(dataset.dataset_rid) # Dataset RID
    print(dataset.path)        # Local path to the downloaded bag
```

A `DatasetBag` is a self-contained archive containing all dataset members, their asset files, feature values, and vocabulary terms at the exact catalog state when the version was created. The bag is already downloaded and materialized — asset files are available on disk.

**For most ML tasks, you don't work with the bag directly.** Instead, use `restructure_assets()` to organize the bag's files into a directory layout your ML framework expects.

## Restructuring Bags for ML Frameworks

`restructure_assets()` is a method on `DatasetBag` that reorganizes downloaded asset files into ML-ready directory structures. This is the bridge between DerivaML's catalog-based data organization and framework conventions like PyTorch's `ImageFolder`.

### Basic usage

```python
for dataset in execution.datasets:
    dataset.restructure_assets(
        asset_table="Image",
        output_dir=execution.working_dir / "data",
        group_by=["Image_Classification"],
    )
```

This creates:

```
data/
    training/          # From child dataset with type "Training"
        airplane/      # From Image_Classification feature value
        automobile/
        ...
    testing/           # From child dataset with type "Testing"
        airplane/
        ...
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_dir` | `Path \| str` | *(required)* | Base directory for restructured files |
| `asset_table` | `str \| None` | `None` | Which asset table to restructure. Auto-detected if the dataset has only one asset table type |
| `group_by` | `list[str] \| None` | `None` | Create nested subdirectories by column or feature name. Each entry adds a nesting level |
| `use_symlinks` | `bool` | `True` | Symlink files instead of copying (saves disk space) |
| `type_selector` | `Callable` | `None` | Custom function to choose the top-level directory name from a list of dataset types |
| `type_to_dir_map` | `dict[str, str]` | `None` | Map dataset types to directory names. Default: `Training→"training"`, `Testing→"testing"` |
| `enforce_vocabulary` | `bool` | `True` | Raise error if an asset has multiple different feature values for the same feature |
| `value_selector` | `Callable` | `None` | Resolve conflicts when an asset has multiple feature values |
| `file_transformer` | `Callable` | `None` | Transform files during restructuring (e.g., DICOM to PNG conversion) |

Returns a `dict[Path, Path]` manifest mapping source paths to output paths.

### How `group_by` works

Each string in the `group_by` list creates a directory nesting level. Values are resolved in order:

1. **Column name** — a direct column on the asset table (e.g., `"Diagnosis"`)
2. **Feature name** — a feature defined on the asset table (e.g., `"Image_Classification"` uses the first term column of that feature)
3. **Feature.column** — a specific column from a multi-term feature (e.g., `"Classification.Label"`)

If a value is missing or `None`, the directory name defaults to `"Unknown"`.

### Custom type selection

By default, restructure_assets maps dataset types to directory names using a built-in mapping. For custom behavior, pass a `type_selector`:

```python
def type_selector(types: list[str]) -> str:
    """Choose directory name from dataset types."""
    type_lower = [t.lower() for t in types]
    if "training" in type_lower:
        return "training"
    elif "testing" in type_lower:
        return "testing"
    return "unknown"

dataset.restructure_assets(
    asset_table="Image",
    output_dir=data_dir,
    group_by=["Image_Classification"],
    type_selector=type_selector,
)
```

## Accessing Input Assets

Individual assets (e.g., pretrained model weights) configured in the experiment are downloaded before your model runs. Access them via `execution.asset_paths`:

```python
# execution.asset_paths is a dict[str, list[AssetFilePath]]
# Keys are asset table names, values are lists of file paths
for table_name, paths in execution.asset_paths.items():
    for asset_path in paths:
        print(asset_path)             # Path to the downloaded file
        print(asset_path.name)        # Filename
        print(asset_path.asset_rid)   # RID of the asset in the catalog
```

`AssetFilePath` is a `Path` subclass with an extra `.asset_rid` attribute for provenance tracking.

### Finding a specific asset by filename

```python
def find_asset(execution, filename):
    """Find a downloaded asset by filename."""
    for table_name, paths in execution.asset_paths.items():
        for path in paths:
            if path.name == filename:
                return path
    return None

weights_path = find_asset(execution, "model_weights.pt")
```

## Registering Output Files

All output files must be registered with `execution.asset_file_path()`. This both creates the file path and stages the file for upload after the model completes.

```python
# For new files: get a path, then write to it
output_path = execution.asset_file_path("Execution_Asset", "predictions.csv")
predictions_df.to_csv(output_path, index=False)

# For existing files: pass the path and it gets staged
execution.asset_file_path("Execution_Asset", existing_file_path)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `asset_name` | `str` | *(required)* | Target asset table (e.g., `"Execution_Asset"`) |
| `file_name` | `str \| Path` | *(required)* | Filename for a new file, or path to an existing file |
| `asset_types` | `list[str]` | `[asset_name]` | Asset type vocabulary terms (e.g., `["Model_Weights"]`, `["Predictions"]`) |
| `copy_file` | `bool` | `False` | Copy instead of symlink when staging an existing file |
| `rename_file` | `str` | `None` | Rename the file during staging |

Use `"Execution_Asset"` for all model-produced files. Use a domain asset table (e.g., `"Image"`, `"Model"`) only when outputs should be queryable as first-class catalog entities with custom metadata.

**Upload happens automatically** after the model function returns and the execution context manager exits. You never call `upload_execution_outputs()` from inside the model function.

## Recording Feature Values

Models can record feature values (e.g., per-image predictions) that get uploaded with other outputs:

```python
# Look up the feature definition
feature = ml_instance.lookup_feature("Image", "Predicted_Class")
RecordClass = feature.feature_record_class()

# Create records
records = [
    RecordClass(Image=image_rid, Predicted_Class="airplane"),
    RecordClass(Image=image_rid, Predicted_Class="ship"),
]

# Add to execution (uploaded with other outputs)
execution.add_features(records)
```

`add_features()` automatically sets the Execution field on each record. Like output files, feature values are staged locally as JSONL files in the execution's `feature/` directory and uploaded to the catalog when `upload_execution_outputs()` runs after the model completes.

## Complete Data Flow

```
Experiment config
    ↓
Runner creates Execution, downloads inputs
    ↓
execution.datasets ← BDBags (versioned data snapshots)
execution.asset_paths ← Individual files (weights, etc.)
    ↓
Model function called with (ml_instance, execution)
    ↓
restructure_assets() → ML-ready directory layout
    ↓
Training / Evaluation
    ↓
asset_file_path() → Staged output files
add_features() → Staged feature records
    ↓
Runner uploads all staged outputs to catalog
```

## Complete Example

A model that loads image data, trains a classifier, and saves weights and predictions:

```python
from pathlib import Path
import torch
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader

from deriva_ml import DerivaML
from deriva_ml.execution import Execution


def image_classifier(
    conv_channels: int = 32,
    hidden_size: int = 128,
    learning_rate: float = 1e-3,
    epochs: int = 10,
    batch_size: int = 64,
    ml_instance: DerivaML = None,
    execution: Execution | None = None,
) -> None:
    """Train an image classifier on execution datasets."""

    # 1. Restructure bag data into ImageFolder layout
    data_dir = execution.working_dir / "data"
    for dataset in execution.datasets:
        dataset.restructure_assets(
            asset_table="Image",
            output_dir=data_dir,
            group_by=["Image_Classification"],
        )

    # 2. Load with PyTorch
    train_dataset = ImageFolder(data_dir / "training", transform=my_transform)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    test_dataset = ImageFolder(data_dir / "testing", transform=my_transform)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)

    # 3. Train
    model = MyNetwork(conv_channels, hidden_size, num_classes=len(train_dataset.classes))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    for epoch in range(epochs):
        train_one_epoch(model, train_loader, optimizer)

    # 4. Save weights
    weights_path = execution.asset_file_path(
        "Execution_Asset", "model_weights.pt", ["Model_Weights"]
    )
    torch.save(model.state_dict(), weights_path)

    # 5. Save predictions
    predictions_path = execution.asset_file_path(
        "Execution_Asset", "predictions.csv", ["Predictions"]
    )
    save_predictions(model, test_loader, predictions_path)
```
