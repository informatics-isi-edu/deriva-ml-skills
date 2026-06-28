---
type: ConfigReference
title: Config __init__.py, Base Config, and Deriva Connection
description: Annotated examples and starter templates for the config package init, the base config that experiments inherit from, and the Deriva connection config group.
---

# Config `__init__.py`, Base Config, and Deriva Connection

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
