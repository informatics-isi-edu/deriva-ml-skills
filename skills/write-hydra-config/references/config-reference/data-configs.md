---
type: ConfigReference
title: Datasets, Assets, and Workflow config groups
description: Annotated examples and starter templates for the datasets, assets, and workflow config groups — including the Architecture and Outputs subsections that appear in the workflow description template.
---

# Datasets, Assets, and Workflow config groups

## Datasets (`datasets.py`)

### Example

```python
from hydra_zen import store
from deriva_ml.dataset import DatasetSpecConfig
from deriva_ml.execution import with_description

datasets_store = store(group="datasets")

# With description (recommended for non-default configs)
datasets_store(
    with_description(
        [DatasetSpecConfig(rid="28DM", version="0.9.0")],
        "Complete CIFAR-10 dataset with all 10,000 images (5,000 training + 5,000 testing). "
        "Use for full-scale experiments.",
    ),
    name="cifar10_complete",
)

# Multiple datasets in one config
datasets_store(
    with_description(
        [
            DatasetSpecConfig(rid="28FC", version="0.4.0"),
            DatasetSpecConfig(rid="28FP", version="0.4.0"),
        ],
        "Small training (500) and testing (500) sets for rapid prototyping.",
    ),
    name="cifar10_small_both",
)

# Empty dataset list (for notebooks that don't need datasets)
datasets_store([], name="no_datasets")

# REQUIRED: default_dataset — plain list, no with_description()
# (with_description creates DictConfig which can't merge with BaseConfig's ListConfig)
datasets_store(
    [DatasetSpecConfig(rid="28DY", version="0.9.0")],
    name="default_dataset",
)
```

### Template

```python
"""Dataset Configuration.

REQUIRED: A configuration named "default_dataset" must be defined.

Usage:
    uv run deriva-ml-run datasets=my_dataset_name
"""
from hydra_zen import store
from deriva_ml.dataset import DatasetSpecConfig
from deriva_ml.execution import with_description

datasets_store = store(group="datasets")

# Empty dataset list (for notebooks that don't need datasets)
datasets_store([], name="no_datasets")

# Example: add your datasets here
# datasets_store(
#     with_description(
#         [DatasetSpecConfig(rid="XXXX", version="1.0.0")],
#         "Description of what this dataset contains and its purpose.",
#     ),
#     name="my_dataset",
# )

# REQUIRED: default_dataset — plain list, no with_description()
datasets_store(
    [DatasetSpecConfig(rid="XXXX", version="1.0.0")],
    name="default_dataset",
)
```

---

## Assets (`assets.py`)

### Example

```python
from hydra_zen import store
from deriva_ml.execution import with_description

asset_store = store(group="assets")

# Plain RID strings (most common)
asset_store(
    with_description(
        ["3WS6", "3X20"],
        "Prediction probabilities from quick (3 epochs) vs extended (50 epochs) training. "
        "Use with ROC analysis notebook.",
    ),
    name="roc_quick_vs_extended",
)

# AssetSpecConfig with caching (for large immutable files like model weights)
from deriva_ml import AssetSpecConfig

asset_store(
    with_description(
        [AssetSpecConfig(rid="3WS2", cache=True)],
        "Pre-trained weights from cifar10_quick (execution 3WR0, 3 epochs). "
        "Cached locally (~50MB) to avoid re-downloading.",
    ),
    name="quick_weights",
)

# REQUIRED: default_asset — empty list, plain (no with_description)
asset_store([], name="default_asset")

# Alias for clarity
asset_store([], name="no_assets")
```

### Template

```python
"""Asset Configuration.

REQUIRED: A configuration named "default_asset" must be defined.

Usage:
    uv run deriva-ml-run assets=my_assets
"""
from hydra_zen import store
from deriva_ml.execution import with_description

asset_store = store(group="assets")

# REQUIRED: default_asset — empty list
asset_store([], name="default_asset")

# Alias for clarity
asset_store([], name="no_assets")

# Example: add your assets here
# asset_store(
#     with_description(
#         ["RID1", "RID2"],
#         "Description of what these assets are and where they came from.",
#     ),
#     name="my_assets",
# )

# Example: cached asset (for large files like model weights)
# from deriva_ml import AssetSpecConfig
# asset_store(
#     with_description(
#         [AssetSpecConfig(rid="XXXX", cache=True)],
#         "Pre-trained weights (~500MB). Cached locally.",
#     ),
#     name="pretrained_weights",
# )
```

---

## Workflow (`workflow.py`)

### Example

```python
from hydra_zen import store, builds
from deriva_ml.execution import Workflow

# Build the workflow config class
Cifar10CNNWorkflow = builds(
    Workflow,
    name="CIFAR-10 2-Layer CNN",
    workflow_type=["Training", "Image Classification"],  # string or list of strings
    description="""
Train a 2-layer convolutional neural network on CIFAR-10 image data.

## Architecture
- **Conv Layer 1**: 3 -> 32 channels, 3x3 kernel, ReLU, MaxPool 2x2
- **Conv Layer 2**: 32 -> 64 channels, 3x3 kernel, ReLU, MaxPool 2x2
- **FC Layer**: 64x8x8 -> 128 hidden units -> 10 classes
""".strip(),
    populate_full_signature=True,
)

workflow_store = store(group="workflow")

# REQUIRED: default_workflow
workflow_store(Cifar10CNNWorkflow, name="default_workflow")

# Named variants
workflow_store(Cifar10CNNWorkflow, name="cifar10_cnn")
```

### Template

```python
"""Workflow Configuration.

REQUIRED: A configuration named "default_workflow" must be defined.

Usage:
    uv run deriva-ml-run workflow=my_workflow
"""
from hydra_zen import store, builds
from deriva_ml.execution import Workflow

MyWorkflow = builds(
    Workflow,
    name="My ML Workflow",
    workflow_type="Training",  # or ["Training", "Image Classification"]
    description="""
Describe what this workflow does.

## Architecture
- Describe the model or pipeline

## Outputs
- What files/artifacts are produced
""".strip(),
    populate_full_signature=True,
)

workflow_store = store(group="workflow")

# REQUIRED: default_workflow
workflow_store(MyWorkflow, name="default_workflow")
```
