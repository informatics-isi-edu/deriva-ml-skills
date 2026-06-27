---
type: ConfigReference
title: Multiruns and Notebook Configs
description: Annotated examples and starter templates for multirun sweep configs and notebook configs.
---

# Multiruns and Notebook Configs

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
