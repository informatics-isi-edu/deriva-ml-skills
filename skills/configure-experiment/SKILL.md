---
name: configure-experiment
description: "ALWAYS use this skill when setting up a DerivaML experiment project, adding config groups, or understanding how experiments compose. Triggers on: 'set up experiment', 'config groups', 'project structure', 'hydra defaults', 'DerivaModelConfig', 'experiment preset', 'new project from template'."
disable-model-invocation: true
---

# Configure ML Experiments with hydra-zen and DerivaML

This covers the structure of a DerivaML experiment project: config groups, how they compose, and project setup. For exact Python API patterns for each config type, see the `write-hydra-config` skill.

## Config Groups

| Group | Purpose | File |
|---|---|---|
| `deriva_ml` | Catalog connection (host, catalog ID) | `configs/deriva.py` |
| `datasets` | Dataset RIDs and versions | `configs/datasets.py` |
| `assets` | Pre-trained weights, reference files | `configs/assets.py` |
| `workflow` | What the code does | `configs/workflow.py` |
| `model_config` | Hyperparameters and architecture | `configs/<model>.py` |
| `notebook` | Notebook-specific configs | `configs/<notebook>.py` |
| `experiment` | Named combinations of the above | `configs/experiments.py` |
| `multiruns` | Sweeps over experiments/parameters | `configs/multiruns.py` |

## How Experiments Compose

```
Base config (defaults for every group)
  + Experiment overrides (swap specific groups)
    + CLI overrides (fine-tune individual parameters)
```

Example: `uv run deriva-ml-run +experiment=cifar10_quick` loads base defaults, then overrides `model_config` and `datasets` from the experiment preset.

## Critical Rules

1. **Every group needs a default** — `default_deriva`, `default_dataset`, `default_asset`, `default_workflow`, `default_model`
2. **Pin dataset versions** — Use `DatasetSpecConfig(rid="...", version="...")` for reproducibility
3. **Use meaningful names** — `resnet50_extended` not `config2`
4. **Test with `--info`** — `uv run deriva-ml-run +experiment=X --info` to inspect resolved config
5. **Write goal-oriented experiment descriptions** — The `description` field on experiments and multiruns should state what question the experiment answers or what hypothesis it tests, not just list technical parameters. Technical details belong in the config; the description explains *why* the experiment exists.

**Good experiment descriptions:**
- "Test whether dropout 0.25 reduces overfitting on the small labeled split compared to the unregularized baseline"
- "Sweep learning rates to find the optimal convergence/stability tradeoff for the 2-layer CNN"
- "Evaluate whether the extended architecture (64→128 channels) improves accuracy enough to justify 10x training time"

**Bad experiment descriptions (just restating parameters):**
- "50 epochs, 64->128 channels, dropout 0.25, weight decay 1e-4"
- "Quick CIFAR-10 training with batch size 128"

## Setup Steps

1. Clone the model template or create `configs/` directory
2. Configure each group in order: `deriva.py` → `datasets.py` → `assets.py` → `workflow.py` → `<model>.py` → `base.py` → `experiments.py`
3. Verify: `uv run deriva-ml-run --info`

For the full project structure, `base.py` template, and setup walkthrough, read `references/workflow.md`.

## Multiruns

A multirun runs multiple experiment configurations in a single command — parameter sweeps, model comparisons, or any combination. DerivaML creates a **parent execution** that links to one **child execution** per parameter combination, so results are grouped and traceable.

Two ways to define multiruns:

**Named multiruns** (`multirun_config` in `configs/multiruns.py`) — reproducible, documented sweeps:

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
```

```bash
uv run deriva-ml-run +multirun=lr_sweep
```

**Ad-hoc multiruns** — comma-separated values on the CLI with `--multirun`:

```bash
uv run deriva-ml-run +experiment=quick,extended --multirun
```

Named multiruns are preferred because they're committed to the repo, self-documenting (the `description` appears on the parent execution), and don't require remembering the `--multirun` flag.

For the full `multirun_config` API, see the `write-hydra-config` skill.

## Optional: Generate Experiments.md

For projects with many experiments, consider maintaining an `Experiments.md` file in the project root as a human-readable summary of all defined experiments. This is optional but helpful for discoverability.

1. **Read the config source** — `experiments.py`, `multiruns.py`, and any model config files they reference
2. **Extract each experiment's** name, config group overrides, key parameters (epochs, lr, batch size, architecture), and purpose
3. **Extract each multirun's** name, overrides, sweep ranges, and description
4. **Write `Experiments.md`** with a quick-reference table, a multiruns table, and a detail section per experiment

If maintained, include `Experiments.md` in the same commit as the config changes — it should travel with the code it describes.

### Format

```markdown
# Experiments

Human-readable registry of all defined experiments and multiruns.
Generated from `src/configs/experiments.py` and `src/configs/multiruns.py`.

## Experiments

| Experiment | Model Config | Dataset | Description |
|------------|-------------|---------|-------------|
| `name` | `model_config_name` | `dataset_name` | Brief purpose |

## Multiruns

| Multirun | Overrides | Description |
|----------|----------|-------------|
| `name` | override summary | Brief purpose |

## Experiment Details

### `experiment_name`

- **Config group overrides**: `model_config=X`, `datasets=Y`
- **Parameters**: epochs, channels, batch size, learning rate, etc.
- **Purpose**: Why this experiment exists
```

## Storage: Cache vs Working Directory

DerivaML uses two distinct storage locations. Understanding the difference prevents data loss and disk bloat.

### Working Directory

The **working directory** is where execution-specific data lives — each execution gets its own subdirectory with downloaded inputs, generated outputs, and logs. After upload, execution directories are cleaned up (controlled by `clean_execution_dir`).

**Default:** `~/.deriva-ml/<hostname>/<catalog_id>/`

**Contains:** `executions/<execution_rid>/` subdirectories — one per run.

### Cache Directory

The **cache directory** stores downloaded dataset bags and cached assets that persist across executions. When you download the same dataset version twice, the second download hits the cache instantly. Cache entries are keyed by checksum, so they're only invalidated when data actually changes.

**Default:** `<working_dir>/cache/`

**Contains:** Dataset bags (keyed by `{rid}_{checksum}`) and cached assets (keyed by `{rid}_{md5}`).

### Why separate them?

| | Working Dir | Cache Dir |
|---|---|---|
| **Lifecycle** | Ephemeral — cleaned after upload | Persistent — survives across runs |
| **Content** | Execution inputs/outputs | Downloaded dataset bags, cached assets |
| **Growth** | Bounded (auto-cleanup) | Unbounded (manual cleanup) |
| **Sharing** | Not shared between executions | Shared across all executions |

### Configuring custom locations

Set these in your `configs/deriva.py`:

```python
from hydra_zen import store
from deriva_ml import DerivaMLConfig

deriva_store = store(group="deriva_ml")

deriva_store(
    DerivaMLConfig,
    name="production",
    hostname="ml.example.org",
    catalog_id="52",
    working_dir="/scratch/ml-work",     # Fast local SSD for computation
    cache_dir="/shared/ml-cache",       # Large shared NFS for cached data
)
```

**When to set a custom `working_dir`:**
- Default `~/.deriva-ml` is on a small disk — redirect to a larger volume
- Running on a compute cluster — use a local scratch disk for speed
- Shared environment — use a per-user directory on shared storage

**When to set a custom `cache_dir`:**
- **Team sharing** — point to a shared NFS or network mount so downloaded bags and large assets are reused across team members. When one person downloads a 15 GB dataset, everyone else gets a cache hit instead of re-downloading. This is the most common reason to customize the cache directory.
- **Disk management** — keep the cache on a large, cheap volume separate from fast compute storage
- **Cluster environments** — use a shared filesystem visible to all compute nodes
- If not set, defaults to `<working_dir>/cache/`

**Shared cache example:**
```python
# All team members point to the same shared cache
deriva_store(
    DerivaMLConfig,
    name="production",
    hostname="ml.example.org",
    catalog_id="52",
    working_dir="/scratch/$USER/ml-work",    # Per-user fast local disk
    cache_dir="/shared/team-ml-cache",       # Shared across team
)
```
When user A downloads dataset `28CT v0.9.0`, the bag lands in `/shared/team-ml-cache/`. When user B runs an experiment referencing the same dataset and version, it's already there — no download needed.

### ⚠️ The working directory must NOT be inside the cache directory

If the working directory is a subdirectory of the cache directory (or vice versa), execution cleanup can delete cached data, or cache cleanup can delete active execution files. Always keep them as independent directory trees.

**Good:**
```python
working_dir="/scratch/ml-work"    # Fast local disk
cache_dir="/data/ml-cache"        # Large shared disk
```

**Bad:**
```python
working_dir="/data/ml-cache/work"   # ❌ Working dir INSIDE cache dir
cache_dir="/scratch/ml-work/cache"  # ❌ Cache dir INSIDE working dir
```

### Managing storage

Use the Bash `ls -la ~/.deriva-ml/` MCP tool to see what's consuming disk space:

```
# Python API or Bash: inspect ~/.deriva-ml/ ()                    # Everything
# Python API or Bash: inspect ~/.deriva-ml/ (filter="cache")      # Just cached bags
# Python API or Bash: inspect ~/.deriva-ml/ (filter="executions") # Just execution dirs
```

To free disk space, use Bash `rm -rf ~/.deriva-ml/...` with specific RIDs:

```
# Python API: ml.clean_storage(rids=["28CT"], confirm=False)  # Preview what would be deleted
# Python API: ml.clean_storage(rids=["28CT"], confirm=True)   # Actually delete
```

**Caution:** Cached bags can be re-downloaded, but execution outputs that haven't been uploaded to the catalog will be permanently lost.

## Reference Resources

- `deriva://config/experiment-template` — Experiment config template
- `deriva://config/multirun-template` — Multirun config template
- `deriva://catalog/workflows` — Available workflows and types

## Related Skills

- **`write-hydra-config`** — Exact Python API patterns for each config type
- **`run-experiment`** — Pre-flight checklist and CLI commands for running
