# Configure ML Experiments with hydra-zen and DerivaML

This skill covers the high-level structure of a DerivaML experiment project: what config groups exist, how they compose into experiments, and how to set up a new project. For the exact Python API and code patterns for each config type, see the `write-hydra-config` skill.

## Config Groups

DerivaML experiments are organized into config groups, each controlling a different aspect of the run:

| Config Group | Purpose | File |
|---|---|---|
| `deriva_ml` | Catalog connection (host, catalog ID) | `configs/deriva.py` |
| `datasets` | Which datasets and versions to use | `configs/datasets.py` |
| `assets` | Additional files (weights, predictions) | `configs/assets.py` |
| `workflow` | What the code does (name, type, description) | `configs/workflow.py` |
| `model_config` | Hyperparameters and architecture | `configs/<model>.py` |
| `experiment` | Named combinations of the above | `configs/experiments.py` |
| multiruns | Sweeps over experiments/parameters | `configs/multiruns.py` |
| notebooks | Notebook-specific configs | `configs/<notebook>.py` |

## How Experiments Compose

An experiment is a named combination of config group choices. The composition hierarchy:

```
DerivaModelConfig (base.py)
  ├── default_deriva    (deriva.py)
  ├── default_dataset   (datasets.py)
  ├── default_asset     (assets.py)
  ├── default_workflow   (workflow.py)
  └── default_model     (cifar10_cnn.py)

+experiment=cifar10_quick (experiments.py)
  overrides:
    /model_config → cifar10_quick
    /datasets → cifar10_small_labeled_split
```

The base config defines defaults for every group. Experiments override specific groups. Multiruns sweep over experiments or parameters.

### Execution Flow

```
uv run deriva-ml-run +experiment=cifar10_quick
```

1. Load base config (`DerivaModelConfig`) with its defaults
2. Apply experiment overrides (model_config, datasets, etc.)
3. Apply any CLI overrides (`model_config.epochs=5`)
4. Resolve the final config and execute

### Required Defaults

Every config group needs a `default_*` entry. These are the fallback when no override is specified:

- `default_deriva` — catalog connection
- `default_dataset` — dataset list
- `default_asset` — asset list (typically empty `[]`)
- `default_workflow` — workflow definition
- `default_model` — model hyperparameters

## Project Structure

```
my-project/
  src/
    configs/
      __init__.py           # Re-exports load_configs
      base.py               # create_model_config() — the root config
      deriva.py             # DerivaMLConfig — catalog connections
      datasets.py           # DatasetSpecConfig lists
      assets.py             # Asset RID lists / AssetSpecConfig
      workflow.py            # Workflow definitions
      cifar10_cnn.py        # Model hyperparameters (one file per model type)
      experiments.py        # Named experiment presets
      multiruns.py          # Named multirun sweeps
      multirun_descriptions.py  # Long markdown descriptions for multiruns
      roc_analysis.py       # Notebook config example
    models/
      cifar10_cnn.py        # Model code (the task_function)
  notebooks/
    roc_analysis.ipynb      # Notebook using notebook_config
  pyproject.toml
  uv.lock
```

### `__init__.py`

```python
from deriva_ml.execution import load_configs

load_all_configs = lambda: load_configs("configs")
```

`load_configs()` discovers and imports all config modules in the package automatically.

### `base.py` — The Root Config

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

Each default name must match a `name=` in its config group's store.

**Optional groups and MISSING**: The `{"optional script_config": "none"}` entry makes `script_config` available but not required. When an experiment overrides `script_config` via its `hydra_defaults`, the base config's `None` default for that field can shadow Hydra's resolved value. Use `MISSING` from `hydra_zen` for any such optional field in the experiment's `make_config()` call (e.g., `script_config=MISSING`) so Hydra resolves the override correctly.

## Setting Up a New Project

### Step 1: Scaffold the Project

If starting from the model template:
```bash
# Clone the template
git clone https://github.com/informatics-isi-edu/deriva-ml-model-template my-project
cd my-project
uv sync
```

If adding configs to an existing project, create the `configs/` directory structure above.

### Step 2: Configure Each Group

Work through the config groups in order. For each one, see the `write-hydra-config` skill for the exact Python API:

1. **`deriva.py`** — Set your catalog hostname and ID
2. **`datasets.py`** — Add your datasets with RIDs and versions
3. **`assets.py`** — Add any pre-trained weights or reference files
4. **`workflow.py`** — Describe what your code does
5. **`<model>.py`** — Define your model's hyperparameters with `builds()`
6. **`base.py`** — Wire up the defaults
7. **`experiments.py`** — Create named presets
8. **`multiruns.py`** — Define any sweeps

### Step 3: Verify

```bash
# Check config resolves correctly
uv run deriva-ml-run --info

# Check a specific experiment
uv run deriva-ml-run +experiment=my_experiment --info

# Dry run (downloads data, runs model, doesn't persist)
uv run deriva-ml-run +experiment=my_experiment dry_run=True
```

## Running Experiments

See the `run-experiment` skill for the full pre-flight checklist, CLI commands, and troubleshooting. Quick reference:

```bash
uv run deriva-ml-run +experiment=baseline              # Single experiment
uv run deriva-ml-run +multirun=lr_sweep                # Named multirun
uv run deriva-ml-run +experiment=quick,extended --multirun  # Ad-hoc multirun
uv run deriva-ml-run --info                            # Inspect resolved config
```

## Multiruns

A multirun runs multiple experiment configurations in a single invocation. DerivaML creates a parent-child execution hierarchy:

```
Parent execution ("lr_sweep")
├── Child 1 (lr=0.0001)
├── Child 2 (lr=0.001)
├── Child 3 (lr=0.01)
└── Child 4 (lr=0.1)
```

The parent execution stores the multirun description and links to all children. Each child is a full execution with its own inputs, outputs, and provenance.

### Named multiruns

Define reusable sweeps in `configs/multiruns.py` using `multirun_config`:

```python
from deriva_ml.execution import multirun_config

multirun_config(
    "lr_sweep",
    overrides=[
        "+experiment=cifar10_quick",
        "model_config.learning_rate=0.0001,0.001,0.01,0.1",
    ],
    description="Learning rate sweep on small labeled split",
)

multirun_config(
    "quick_vs_extended",
    overrides=[
        "+experiment=cifar10_quick,cifar10_extended",
    ],
    description="Compare quick and extended training configs",
)
```

Run with:
```bash
uv run deriva-ml-run +multirun=lr_sweep
```

The `--multirun` flag is not needed — `multirun_config` enables it automatically.

### Ad-hoc multiruns

For one-off sweeps, use comma-separated values with `--multirun`:

```bash
uv run deriva-ml-run +experiment=quick,extended --multirun
uv run deriva-ml-run +experiment=cifar10_quick model_config.epochs=3,10,50 --multirun
```

### Override syntax

Overrides use Hydra's syntax. Comma-separated values create the sweep:

- `+experiment=a,b,c` — sweep over three experiments
- `model_config.learning_rate=0.001,0.01` — sweep a single parameter
- Combine both for a grid: each experiment runs with each parameter value

### When to use multiruns

- **Parameter sweeps** — learning rate, batch size, architecture variants
- **Model comparisons** — same data, different model configs
- **Ablation studies** — systematically vary one factor while holding others constant
- **Cross-validation** — one child per fold (use `sequence` to order)

### Navigating multirun results

- `list_nested_executions` with the parent execution RID — see all children
- resource `deriva://execution/{rid}` with a child RID — find the parent
- Read `deriva://experiment/{parent_rid}` — see the full multirun with description and children

## Best Practices

- **Pin dataset versions** so runs are reproducible
- **Use meaningful names** — `resnet50_extended` not `config2`
- **Add descriptions everywhere** — they're recorded in execution metadata
- **Test with `dry_run=True`** before production runs
- **Commit before running** — git state is recorded in the execution
- **Use `--info`** to inspect resolved config without running
