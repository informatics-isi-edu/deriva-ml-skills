# Config Group Reference

Annotated examples and starter templates for each hydra-zen config group. Each section shows a populated example from a real project, followed by a minimal template for starting from scratch.

## Table of Contents

1. [Config `__init__.py`](#config-initpy)
2. [Base Config (`base.py`)](#base-config-basepy)
3. [Deriva Connection (`deriva.py`)](#deriva-connection-derivapy)
4. [Datasets (`datasets.py`)](#datasets-datasetspy)
5. [Assets (`assets.py`)](#assets-assetspy)
6. [Workflow (`workflow.py`)](#workflow-workflowpy)
7. [Model Config (`model.py`)](#model-config-modelpy)
8. [Experiments (`experiments.py`)](#experiments-experimentspy)
9. [Multiruns (`multiruns.py`)](#multiruns-multirunspy)
10. [Notebook Configs](#notebook-configs)

---

## Config `__init__.py`

All config modules in the package are imported automatically by `load_configs()`.

```python
"""Configuration Package."""
from deriva_ml.execution import load_configs

load_all_configs = lambda: load_configs("configs")
```

---

## Base Config (`base.py`)

The base config defines the top-level structure that experiments inherit from. Each default name must match a `name=` in the corresponding config group's store.

### Example

```python
from hydra_zen import store
from deriva_ml import DerivaML
from deriva_ml.execution import BaseConfig, DerivaBaseConfig, base_defaults, create_model_config

DerivaModelConfig = create_model_config(
    DerivaML,
    description="Simple model run",
    hydra_defaults=[
        "_self_",
        {"deriva_ml": "default_deriva"},
        {"datasets": "default_dataset"},
        {"assets": "default_asset"},
        {"workflow": "default_workflow"},
        {"model_config": "default_model"},
        {"optional script_config": "none"},
    ],
)

store(DerivaModelConfig, name="deriva_model")
```

### Template

```python
"""Base configuration for the model runner.

Experiments inherit from DerivaModelConfig.
"""
from hydra_zen import store
from deriva_ml import DerivaML
from deriva_ml.execution import BaseConfig, DerivaBaseConfig, base_defaults, create_model_config

DerivaModelConfig = create_model_config(
    DerivaML,
    description="Model training run",
    hydra_defaults=[
        "_self_",
        {"deriva_ml": "default_deriva"},
        {"datasets": "default_dataset"},
        {"assets": "default_asset"},
        {"workflow": "default_workflow"},
        {"model_config": "default_model"},
        {"optional script_config": "none"},
    ],
)

store(DerivaModelConfig, name="deriva_model")

__all__ = ["BaseConfig", "DerivaBaseConfig", "DerivaModelConfig", "base_defaults"]
```

---

## Deriva Connection (`deriva.py`)

### Example

```python
from hydra_zen import store
from deriva_ml import DerivaMLConfig

deriva_store = store(group="deriva_ml")

# REQUIRED: default_deriva
deriva_store(
    DerivaMLConfig,
    name="default_deriva",
    hostname="localhost",
    catalog_id=6,
    use_minid=False,
    zen_meta={
        "description": (
            "Local development catalog (localhost:6) with CIFAR-10 data. "
            "Schema: cifar10_10k."
        )
    },
)
```

### Template

```python
"""DerivaML Connection Configuration.

REQUIRED: A configuration named "default_deriva" must be defined.
"""
from hydra_zen import store
from deriva_ml import DerivaMLConfig

deriva_store = store(group="deriva_ml")

# REQUIRED: default_deriva
deriva_store(
    DerivaMLConfig,
    name="default_deriva",
    hostname="YOUR_HOST_HERE",      # e.g., "ml.derivacloud.org" or "localhost"
    catalog_id=YOUR_CATALOG_ID,     # e.g., 6
    use_minid=False,
    zen_meta={
        "description": "Development catalog. Replace with your catalog details."
    },
)
```

---

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
from deriva_ml.asset.aux_classes import AssetSpecConfig

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
# from deriva_ml.asset.aux_classes import AssetSpecConfig
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

---

## Model Config (`model.py`)

### Example

```python
from hydra_zen import builds, store
from models.cifar10_cnn import cifar10_cnn

# Build the base config — zen_partial=True is critical
# (execution context is injected at runtime)
Cifar10CNNConfig = builds(
    cifar10_cnn,
    conv1_channels=32,
    conv2_channels=64,
    hidden_size=128,
    dropout_rate=0.0,
    learning_rate=1e-3,
    epochs=10,
    batch_size=64,
    weight_decay=0.0,
    populate_full_signature=True,
    zen_partial=True,
)

model_store = store(group="model_config")

# REQUIRED: default_model
model_store(
    Cifar10CNNConfig,
    name="default_model",
    zen_meta={
        "description": (
            "Default CIFAR-10 CNN: 32->64 channels, 128 hidden units, 10 epochs, "
            "batch size 64, lr=1e-3. Balanced config for standard training runs."
        )
    },
)

# Variants override specific parameters
model_store(
    Cifar10CNNConfig,
    name="cifar10_quick",
    epochs=3,
    batch_size=128,
    zen_meta={
        "description": (
            "Quick training: 3 epochs, batch 128. Use for rapid iteration, "
            "debugging, and verifying the training pipeline works correctly."
        )
    },
)

model_store(
    Cifar10CNNConfig,
    name="cifar10_extended",
    conv1_channels=64,
    conv2_channels=128,
    hidden_size=256,
    dropout_rate=0.25,
    weight_decay=1e-4,
    learning_rate=1e-3,
    epochs=50,
    zen_meta={
        "description": (
            "Extended training for best accuracy: Large model (64->128 ch, 256 hidden), "
            "regularization (dropout 0.25, weight decay 1e-4), 50 epochs."
        )
    },
)
```

### Template

```python
"""Model Configuration.

REQUIRED: A configuration named "default_model" must be defined.

Usage:
    uv run deriva-ml-run model_config=my_variant
    uv run deriva-ml-run model_config.learning_rate=0.01
"""
from hydra_zen import builds, store
from my_project.models import my_model_function  # Your model's entry point

# Build the base config
# zen_partial=True is critical — execution context is injected at runtime
MyModelConfig = builds(
    my_model_function,
    # Add your model's parameters here:
    learning_rate=1e-3,
    epochs=10,
    batch_size=64,
    populate_full_signature=True,
    zen_partial=True,
)

model_store = store(group="model_config")

# REQUIRED: default_model
model_store(
    MyModelConfig,
    name="default_model",
    zen_meta={
        "description": "Default configuration. Describe hyperparameters and intended use."
    },
)

# Add variants by overriding specific parameters
# model_store(
#     MyModelConfig,
#     name="quick",
#     epochs=3,
#     zen_meta={"description": "Quick test: 3 epochs for pipeline validation."},
# )
```

---

## Experiments (`experiments.py`)

**IMPORTANT pitfall**: When `bases=(DerivaModelConfig,)` is used and the base has its own `hydra_defaults`, optional fields that default to `None` in the base will shadow Hydra's resolved value. Use `MISSING` for any optional field you override in the experiment's defaults list (e.g., `script_config=MISSING`).

### Example

```python
from hydra_zen import make_config, store, MISSING
from configs.base import DerivaModelConfig

# package="_global_" is set on the store, not on make_config
experiment_store = store(group="experiment", package="_global_")

experiment_store(
    make_config(
        hydra_defaults=[
            "_self_",
            {"override /model_config": "cifar10_quick"},
            {"override /datasets": "cifar10_small_labeled_split"},
        ],
        description="Quick CIFAR-10 training: 3 epochs, 32->64 channels, batch size 128",
        bases=(DerivaModelConfig,),
    ),
    name="cifar10_quick",
)

experiment_store(
    make_config(
        hydra_defaults=[
            "_self_",
            {"override /model_config": "cifar10_extended"},
            {"override /datasets": "cifar10_small_labeled_split"},
        ],
        description="Extended CIFAR-10 training: 50 epochs, 64->128 channels, full regularization",
        bases=(DerivaModelConfig,),
    ),
    name="cifar10_extended",
)

# Script-only experiment (e.g., dataset generation via script_config)
experiment_store(
    make_config(
        hydra_defaults=[
            "_self_",
            {"override /deriva_ml": "dev_facebase"},
            {"override /datasets": "none"},
            {"override /script_config": "my_generation_script"},
            {"override /workflow": "dataset_generation"},
        ],
        description="Generate a curated subset from the source dataset",
        script_config=MISSING,  # IMPORTANT: use MISSING, not None, so Hydra resolves the override
        bases=(DerivaModelConfig,),
    ),
    name="generate_my_subset",
)
```

### Template

```python
"""Experiment definitions.

Usage:
    uv run deriva-ml-run +experiment=my_experiment
"""
from hydra_zen import make_config, store, MISSING
from configs.base import DerivaModelConfig

experiment_store = store(group="experiment", package="_global_")

# Example experiment
# experiment_store(
#     make_config(
#         hydra_defaults=[
#             "_self_",
#             {"override /model_config": "quick"},
#             {"override /datasets": "my_dataset"},
#         ],
#         description="Quick test run with small dataset",
#         bases=(DerivaModelConfig,),
#     ),
#     name="quick_test",
# )
```

---

## Multiruns (`multiruns.py`)

### Example

```python
from deriva_ml.execution import multirun_config

multirun_config(
    "quick_vs_extended",
    overrides=[
        "+experiment=cifar10_quick,cifar10_extended",
    ],
    description="""## Quick vs Extended Training Comparison

| Config | Epochs | Architecture | Regularization |
|--------|--------|--------------|----------------|
| quick | 3 | 32->64 channels | None |
| extended | 50 | 64->128 channels | Dropout 0.25, WD 1e-4 |

**Objective:** Compare training duration vs accuracy tradeoff.
""",
)

# Hyperparameter sweep
multirun_config(
    "lr_sweep",
    overrides=[
        "+experiment=cifar10_quick",
        "model_config.epochs=10",
        "model_config.learning_rate=0.0001,0.001,0.01,0.1",
    ],
    description="Learning rate sweep: 4 values from 1e-4 to 1e-1 on quick config.",
)

# Grid search (N x M runs)
multirun_config(
    "lr_batch_grid",
    overrides=[
        "+experiment=cifar10_quick",
        "model_config.epochs=10",
        "model_config.learning_rate=0.001,0.01",
        "model_config.batch_size=64,128",
    ],
    description="LR x batch size grid: 2x2 = 4 total runs.",
)
```

### Template

```python
"""Multirun configurations for experiment sweeps.

Usage:
    uv run deriva-ml-run +multirun=my_sweep
"""
from deriva_ml.execution import multirun_config

# Example: compare two experiments
# multirun_config(
#     "compare_models",
#     overrides=[
#         "+experiment=quick_test,extended_test",
#     ],
#     description="Compare quick vs extended training configurations.",
# )

# Example: hyperparameter sweep
# multirun_config(
#     "lr_sweep",
#     overrides=[
#         "+experiment=quick_test",
#         "model_config.learning_rate=0.0001,0.001,0.01,0.1",
#     ],
#     description="Learning rate sweep: 4 values from 1e-4 to 1e-1.",
# )
```

---

## Notebook Configs

### Example

```python
from dataclasses import dataclass
from deriva_ml.execution import BaseConfig, notebook_config

@dataclass
class ROCAnalysisConfig(BaseConfig):
    """Custom parameters for this notebook."""
    show_per_class: bool = True
    confidence_threshold: float = 0.0

notebook_config(
    "roc_analysis",
    config_class=ROCAnalysisConfig,
    defaults={"assets": "roc_quick_vs_extended", "datasets": "no_datasets"},
    description="ROC curve analysis (default: quick vs extended training)",
)

# Simple notebook with no custom parameters
notebook_config(
    "my_analysis",
    defaults={"assets": "my_assets"},
)
```

In the notebook:
```python
from deriva_ml.execution import run_notebook

ml, execution, config = run_notebook("roc_analysis")
# config.assets, config.show_per_class, config.confidence_threshold are available
```

### Template

```python
"""Configuration for a Jupyter notebook.

Usage in notebook:
    from deriva_ml.execution import run_notebook
    ml, execution, config = run_notebook("my_analysis")

From CLI:
    uv run deriva-ml-run-notebook notebooks/my_analysis.ipynb --config my_analysis
"""
from dataclasses import dataclass
from deriva_ml.execution import BaseConfig, notebook_config


@dataclass
class MyAnalysisConfig(BaseConfig):
    """Custom parameters for this notebook."""
    threshold: float = 0.5
    show_plots: bool = True


# Simple notebook (no custom params)
# notebook_config(
#     "simple_analysis",
#     defaults={"assets": "my_assets"},
# )

# Notebook with custom parameters
# notebook_config(
#     "my_analysis",
#     config_class=MyAnalysisConfig,
#     defaults={"assets": "my_assets", "datasets": "no_datasets"},
#     description="Analysis notebook with configurable threshold",
# )
```
