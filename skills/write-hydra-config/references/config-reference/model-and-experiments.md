---
type: ConfigReference
title: Model Config and Experiments config groups
description: Annotated examples and starter templates for the model_config and experiments config groups.
---

# Model Config and Experiments config groups

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
        # Goal-oriented, not parameter-restating; design URL appended so the
        # Execution row links back to the hypothesis it implements.
        description=(
            "Smoke-test the pipeline on a small split before a full run — "
            "is the plumbing correct end to end? "
            "See design: https://github.com/<org>/<repo>/blob/main/docs/design/experiment/cifar10-quick.md"
        ),
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
        description=(
            "Does the extended architecture (64->128 channels) + full regularization "
            "beat the quick baseline by enough to justify ~10x training time? "
            "See design: https://github.com/<org>/<repo>/blob/main/docs/design/experiment/cifar10-extended.md"
        ),
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
