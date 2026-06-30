---
name: configure-experiment
description: "Use when setting up a DerivaML experiment project, adding config groups, or understanding how experiments compose. Triggers on: 'set up experiment', 'config groups', 'project structure', 'hydra defaults', 'DerivaModelConfig', 'experiment preset', 'new project from template'. Auto-fires in the experiment-lifecycle Phase 2 (configuration) moment, the seam where the lifecycle hands off here. Do NOT use for per-config-file Python syntax (use write-hydra-config) or for the up-front design doc (use design-experiment)."
---

# Configure ML Experiments with hydra-zen and DerivaML

This covers the structure of a DerivaML experiment project: config groups, how they compose, and project setup. The table below is the orientation map — which groups exist and which file each lives in. For the exhaustive per-group **key rules** (required keys, PITFALLs, the Python API patterns for each config type), see `/deriva-ml:write-hydra-config` → `references/config-reference/rules-and-validation.md`.

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
4. **Inspect before running** — three distinct commands (don't confuse them):
   - `uv run deriva-ml-run --list-configs` — the *menu* of registered `group=value` options (ignores overrides; deriva-ml-specific)
   - `uv run deriva-ml-run +experiment=X --cfg job` — the fully *resolved* config that experiment composes to, without executing (Hydra's native `--cfg`)
   - `uv run deriva-ml-run +experiment=X dry_run=true` — resolve *and* validate every referenced RID/term against the live catalog, then stop before training
   Every Hydra command-line flag is forwarded to Hydra; see <https://hydra.cc/docs/advanced/hydra-command-line-flags/> and the override grammar at <https://hydra.cc/docs/advanced/override_grammar/basic/>.
5. **Write goal-oriented experiment descriptions** — The `description` field on experiments and multiruns should state what question the experiment answers or what hypothesis it tests, not just list technical parameters. Technical details belong in the config; the description explains *why* the experiment exists. **If the experiment has a design doc (`docs/design/experiment/<slug>.md` — it should, from `/deriva-ml:design-experiment`), append its committed URL to the description** so the Execution record links back to the design it implements (`"… See design: https://github.com/<org>/<repo>/blob/main/docs/design/experiment/<slug>.md"`). See `/deriva-ml:write-hydra-config` → `rules-and-validation.md` ("Experiments") for the exact rule.

**Good experiment descriptions:**
- "Test whether dropout 0.25 reduces overfitting on the small labeled split compared to the unregularized baseline"
- "Sweep learning rates to find the optimal convergence/stability tradeoff for the 2-layer CNN"
- "Evaluate whether the extended architecture (64→128 channels) improves accuracy enough to justify 10x training time"

**Bad experiment descriptions (just restating parameters):**
- "50 epochs, 64->128 channels, dropout 0.25, weight decay 1e-4"
- "Quick CIFAR-10 training with batch size 128"

## Setup Steps

> **The config implements an approved experiment-design doc.** Before writing config groups, you should have a `docs/design/experiment/<slug>.md` at **Approved** (see `/deriva-ml:design-experiment`). As you fill the groups below, cross-check that every **Requirement** in that design — the datasets/versions, assets, vocabularies — is satisfied by a config entry. A requirement with no config home is a gap to close before running.
>
> If you don't know whether a design doc exists for this work, look in `docs/design/experiment/` for one matching the experiment (by slug) and read it before configuring — its Requirements are the contract this config implements.

1. Clone the model template or create `configs/` directory
2. Configure each group in order: `deriva.py` → `datasets.py` → `assets.py` → `workflow.py` → `<model>.py` → `base.py` → `experiments.py`
3. Verify the config tree composes: `uv run deriva-ml-run --list-configs` (the menu of registered options), then `uv run deriva-ml-run +experiment=<name> --cfg job` to confirm a specific experiment resolves

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

`Experiments.md` is an **OKF document** (Markdown + YAML frontmatter) — it opens
with a frontmatter block, then the `# Experiments` H1 and the registry tables. It
is the config-derived counterpart to the design bundle's `docs/design/index.md`
(also `type: Index`); both list "all experiments," one from configs and one from
design docs (see `/deriva-ml:deriva-ml-context` → "The repo's planning artifacts").

```markdown
---
type: Index
title: Experiments — <project name>
description: >
  Config-derived registry of every defined experiment and multirun in this
  project — config-group overrides, key parameters, and a link to each
  experiment's design doc. Generated from src/configs/experiments.py and
  multiruns.py.
tags: [experiments, configs, deriva-ml]
---

# Experiments

Human-readable registry of all defined experiments and multiruns.
Generated from `src/configs/experiments.py` and `src/configs/multiruns.py`.

## Experiments

| Experiment | Model Config | Dataset | Design | Description |
|------------|-------------|---------|--------|-------------|
| `name` | `model_config_name` | `dataset_name` | [design](docs/design/experiment/name.md) | Brief purpose |

## Multiruns

| Multirun | Overrides | Description |
|----------|----------|-------------|
| `name` | override summary | Brief purpose |

## Experiment Details

### `experiment_name`

- **Config group overrides**: `model_config=X`, `datasets=Y`
- **Parameters**: epochs, channels, batch size, learning rate, etc.
- **Purpose**: Why this experiment exists
- **Design doc**: link to `docs/design/experiment/<slug>.md` (the plan + Validation criteria + Outcome) when one exists — omit if not yet designed
```

`Experiments.md` is the **runnable/config view** of experiments; `docs/design/experiment/<slug>.md` is the **plan view** (Goal, Validation, Outcome). They share the experiment `<slug>` — link each Experiments.md entry to its design doc (and the design doc's "Status & links" points back at the config). The two registries — `Experiments.md` (config) and `docs/design/index.md` (design corpus) — are connected by these links, not merged; see `/deriva-ml:deriva-ml-context` → "The repo's planning artifacts — and how they connect".

## Configuring storage locations in `configs/deriva.py`

DerivaML uses two distinct storage locations — a **working directory** (per-execution inputs/outputs/logs, ephemeral) and a **cache directory** (downloaded dataset bags and assets that persist across executions). The defaults work for most users, but you can override both in your hydra-zen config when needed.

For the conceptual difference, the on-disk layout, and the management commands (cleanup, garbage-collection, incomplete-execution recovery), see **`/deriva-ml:manage-deriva-storage`** — that skill owns the storage surface.

This skill owns only the **config-authorship** side: how to set `working_dir` and `cache_dir` in `configs/deriva.py`.

### Setting custom locations

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
- Default `~/.deriva-ml/<hostname>/<catalog_id>/` is on a small disk — redirect to a larger volume.
- Running on a compute cluster — use a local scratch disk for speed.
- Shared environment — use a per-user directory on shared storage.

**When to set a custom `cache_dir`:**
- **Team sharing** — point to a shared NFS or network mount so downloaded bags and large assets are reused across team members. When one person downloads a 15 GB dataset, everyone else gets a cache hit instead of re-downloading. This is the most common reason to customize the cache directory.
- **Disk management** — keep the cache on a large, cheap volume separate from fast compute storage.
- **Cluster environments** — use a shared filesystem visible to all compute nodes.
- If not set, defaults to `<working_dir>/cache/`.

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

## Reference Resources

> Every MCP tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

- `deriva://config/experiment-template` — Experiment config template
- `deriva://config/multirun-template` — Multirun config template
- `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/workflows` — Available workflows and types (or call `deriva_ml_list_workflows(hostname=..., catalog_id=...)`)

## Related Skills

- **`design-experiment`** — Authors the `docs/design/experiment/<slug>.md` this config implements. Write the design first; the config satisfies its Requirements.
- **`write-hydra-config`** — Exact Python API patterns for each config type
- **`execution-lifecycle`** — Pre-flight checklist and CLI commands for running
