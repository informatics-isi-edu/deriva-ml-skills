---
name: write-hydra-config
description: "Write and validate hydra-zen config files for DerivaML — DatasetSpecConfig, asset_store, builds(), experiment_config, multirun_config, with_description. Use when adding, editing, or updating any config in configs/, or when validating that config RIDs and versions match the catalog."
user-invocable: true
disable-model-invocation: true
---

# Writing Hydra-Zen Config Files for DerivaML

This skill is the authoritative reference for the Python API used in DerivaML hydra-zen configuration files. Every config group has a specific pattern — follow the examples exactly.

## When to Use This Skill

- Writing a new config file (datasets.py, assets.py, model.py, etc.)
- Adding a new entry to an existing config file
- After creating a catalog entity (dataset, asset, workflow) that should be added to configs
- Fixing or updating existing config entries
- Validating that config RIDs and versions exist in the catalog

After any catalog-modifying action (create_dataset, split_dataset, create_workflow, etc.), proactively offer to update the relevant config file using these patterns.

## Reference File

- `references/config-reference.md` — Annotated examples and starter templates for every config group. Each section shows a populated example from a real project, followed by a minimal template. Read the relevant section when writing or modifying a specific config file.

## Config Groups Overview

| Group | File | Key Import | Registration |
|---|---|---|---|
| `deriva_ml` | `configs/deriva.py` | `from deriva_ml import DerivaMLConfig` | `store(group="deriva_ml")` |
| `datasets` | `configs/datasets.py` | `from deriva_ml.dataset import DatasetSpecConfig` | `store(group="datasets")` |
| `assets` | `configs/assets.py` | `from deriva_ml.execution import with_description` | `store(group="assets")` |
| `workflow` | `configs/workflow.py` | `from deriva_ml.execution import Workflow` | `store(group="workflow")` |
| `model_config` | `configs/<model>.py` | `from hydra_zen import builds` | `store(group="model_config")` |
| `experiment` | `configs/experiments.py` | `from hydra_zen import make_config` | `store(group="experiment", package="_global_")` |
| multiruns | `configs/multiruns.py` | `from deriva_ml.execution import multirun_config` | `multirun_config("name", ...)` |
| notebooks | `configs/<notebook>.py` | `from deriva_ml.execution import notebook_config` | `notebook_config("name", ...)` |

## Key Rules by Config Group

### Datasets
- `version` is **required** — always a semver string like `"0.9.0"`, not an integer
- Use `with_description()` for non-default configs
- Default configs use plain lists (no `with_description`) for merge compatibility
- Find the current version via the `deriva://dataset/{rid}` MCP resource
- If data has changed since the version was created, call `increment_dataset_version` first

### Assets
- Plain RID strings for simple references: `["3WS6", "3X20"]`
- `AssetSpecConfig(rid=..., cache=True)` for large files that shouldn't re-download
- Default/empty configs use plain lists for merge compatibility
- Assets are typically execution outputs — note the source execution RID in the description

### Workflow
- Use `builds(Workflow, ...)` with `populate_full_signature=True`
- `workflow_type` can be a single string or a list of strings
- `description` supports markdown — use it for architecture details
- Git URL and commit hash are captured automatically at runtime

### Model Config
- `zen_partial=True` is required — the execution context is injected later
- `populate_full_signature=True` exposes all constructor params to Hydra
- `zen_meta={"description": "..."}` documents the config variant
- Override individual params when registering variants (no need to rebuild)

### Experiments
- `package="_global_"` goes on the `store()` call
- `bases=(DerivaModelConfig,)` inherits from the base config
- `hydra_defaults` uses `{"override /group": "name"}` syntax
- `"_self_"` must be first in the defaults list
- `description` is a plain string on `make_config()` (not zen_meta)
- Group must be `"experiment"` (singular), matching `+experiment=` CLI syntax
- **PITFALL**: When the base config has optional fields that default to `None` (e.g., `script_config`), those `None` values shadow Hydra's resolved override. Use `MISSING` from `hydra_zen` for any optional field you override via the experiment's defaults list (e.g., `script_config=MISSING`)

### Multiruns
- First arg is the multirun name (string), not a keyword
- `overrides` is a list of Hydra override strings (comma-separated values for sweeps)
- `description` supports rich markdown (tables, headers) — shown on the parent execution
- No `--multirun` flag needed when using `multirun_config` — it's automatic
- CLI usage: `uv run deriva-ml-run +multirun=lr_sweep`

### Base Config
- Each default name must match a `name=` in the corresponding config group's store

### Config `__init__.py`
- Must re-export `load_configs` so all config modules are discovered

## Description Mechanisms

Two mechanisms exist — use the right one for the context:

| Config Type | Mechanism | Example |
|---|---|---|
| Lists (datasets, assets) | `with_description(items, "...")` | `with_description([DatasetSpecConfig(...)], "Training images v3")` |
| `builds()` configs (models, connections) | `zen_meta={"description": "..."}` | `store(Config, name="x", zen_meta={"description": "..."})` |
| Experiments | `description=` param on `make_config()` | `make_config(..., description="Quick training run")` |
| Multiruns | `description=` param on `multirun_config()` | `multirun_config("name", ..., description="...")` |
| Notebooks | `description=` param on `notebook_config()` | `notebook_config("name", ..., description="...")` |

Descriptions are recorded in execution metadata and make experiments self-documenting. Before writing descriptions, look up catalog details via `deriva://dataset/{rid}` or `deriva://asset/{rid}`.

### Good Descriptions

General principles — descriptions should be specific, quantified, purposeful, and version-aware:

- **Specific**: "ResNet-50 with 3-class output head, trained with cosine annealing LR schedule"
- **Quantified**: "4,500 histopathology tiles at 224x224, balanced across 3 subtypes"
- **Purposeful**: "Validation set held out by patient ID to prevent data leakage"
- **Version-aware**: "Frozen at version 3, which excludes 12 QC-failed slides"

#### By Config Type

**Experiments** — State the goal or hypothesis, not just parameters. Parameters are already in the config; the description explains *why* the experiment exists:
- Good: "Test whether dropout 0.25 reduces overfitting compared to the unregularized baseline"
- Bad: "50 epochs, 64->128 channels, dropout 0.25"

**Multiruns** — State what question the sweep answers and what the parameter range covers:
- Good: "Sweep learning rates [1e-4, 1e-3, 1e-2, 1e-1] to find the optimal convergence/stability tradeoff for the 2-layer CNN on the small labeled split"

**Datasets** — Describe composition, source, and intended use:
- Good: "500 CIFAR-10 images (50 per class), balanced, for rapid iteration during development"

**Assets** — Describe what the assets are, which experiments produced them, and how to use them:
- Good: "Prediction probability CSVs from the learning rate sweep. Compare AUC scores in roc_analysis notebook"

**Model configs** — Describe the architectural or training variant and when to choose it:
- Good: "Extended training with full regularization — use when accuracy matters more than training time"

## Config Class Parameter Reference

### `DerivaMLConfig` (from `deriva_ml`)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `hostname` | `str` | *(required)* | Hostname of the Deriva server (e.g., `'localhost'`, `'www.facebase.org'`) |
| `catalog_id` | `str \| int` | `1` | Catalog identifier — numeric ID or catalog alias name |
| `domain_schemas` | `str \| set[str] \| None` | `None` | Domain schema name(s). `None` = auto-detect all non-system schemas |
| `default_schema` | `str \| None` | `None` | Default schema for table creation. Required if multiple domain schemas exist |
| `project_name` | `str \| None` | `None` | Project name for organizing outputs. Defaults to `default_schema` |
| `cache_dir` | `str \| Path \| None` | `None` | Dataset/bag cache directory. Defaults to `working_dir/cache` |
| `working_dir` | `str \| Path \| None` | `None` | Base computation directory. Defaults to `~/.deriva-ml` |
| `ml_schema` | `str` | `'deriva-ml'` | Schema name for ML tables |
| `logging_level` | `int` | `WARNING` | Logging level for DerivaML |
| `deriva_logging_level` | `int` | `WARNING` | Logging level for underlying Deriva libraries |
| `credential` | `dict \| None` | `None` | Auth credentials. `None` = retrieved automatically |
| `s3_bucket` | `str \| None` | `None` | S3 bucket URL for bag storage (e.g., `'s3://my-bucket'`). Enables MINID |
| `use_minid` | `bool \| None` | `None` | Use MINID for bags. `None` = auto (True if `s3_bucket` set) |
| `check_auth` | `bool` | `True` | Verify authentication on connection |
| `clean_execution_dir` | `bool` | `True` | Clean execution dirs after successful upload |

**Note:** `hydra_runtime_output_dir` is set automatically by Hydra — never set it manually.

### `DatasetSpecConfig` (from `deriva_ml.dataset`)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `rid` | `str` | *(required)* | Dataset RID |
| `version` | `str` | *(required)* | Semantic version string (e.g., `"0.9.0"`) |
| `materialize` | `bool` | `True` | Download asset files. `False` = metadata only |
| `description` | `str` | `""` | Human-readable description of this dataset spec |
| `exclude_tables` | `list[str] \| None` | `None` | Table names to exclude from FK path traversal during bag export |
| `timeout` | `list[int] \| None` | `None` | `[connect_timeout, read_timeout]` in seconds. Default `[10, 610]` |

### `AssetSpecConfig` (from `deriva_ml.asset.aux_classes`)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `rid` | `str` | *(required)* | Asset RID |
| `cache` | `bool` | `False` | Cache asset locally by MD5. Use for large immutable files (model weights) |

## MCP Reference Resources

- `deriva://docs/hydra-zen` — Full guide to hydra-zen configuration management in DerivaML
- `deriva://docs/execution-configuration` — Execution configuration reference
- `deriva://config/deriva-ml-template` — Starter template for DerivaML connection config
- `deriva://config/dataset-spec-template` — Starter template for dataset specs
- `deriva://config/model-template` — Starter template for model configs with `zen_partial`
- `deriva://config/experiment-template` — Starter template for experiment presets
- `deriva://config/multirun-template` — Starter template for multirun sweeps
- `deriva://dataset/{rid}` — Look up dataset details including current version
- `deriva://catalog/workflow-types` — Browse available workflow types

## Validating Configs Against the Catalog

Before running experiments, validate that all RIDs and versions in config files actually exist in the connected catalog.

### Validation Checklist

| Config Type | What to Validate | MCP Tool / Resource |
|---|---|---|
| `DatasetSpecConfig(rid=..., version=...)` | RID exists, version exists | `deriva://dataset/{rid}` |
| Asset RID strings `["3WS6"]` | RID exists in an asset table | `validate_rids(rids=[...])` |
| `AssetSpecConfig(rid=...)` | RID exists | `validate_rids(rids=[...])` |
| `workflow_type="Training"` | Workflow type term exists | `deriva://catalog/workflow-types` |

### Validation Workflow

1. **Connect to the catalog** using the same `deriva_ml` config the experiment will use
2. **Read the config files** and extract all RIDs and versions
3. **Validate RIDs** — use `validate_rids` to batch-check that all RIDs exist
4. **Check dataset versions** — for each `DatasetSpecConfig`, read `deriva://dataset/{rid}` and verify the version exists
5. **Report mismatches** — list any RIDs that don't exist, versions that are missing, or versions that are behind current

### Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `Dataset not found: RID=...` | RID doesn't exist in target catalog | Verify RID against correct catalog (dev vs prod) |
| `Version X not found` | Version never created | Use CLI `git describe --tags` to find latest, or `increment_dataset_version` |
| Stale version | Data changed since version was created | Call `increment_dataset_version`, then update config |
| Wrong catalog | Config RIDs are from a different catalog | Check `deriva_ml` config group — are you pointing at the right host/catalog? |

### Proactive Validation

After any catalog-modifying action (create_dataset, split_dataset, increment_dataset_version, etc.), proactively:

1. Note the new RID, version, and description
2. Check if existing config files reference the affected entity
3. Offer to update configs if versions are stale or new entities should be added
4. Present changes for approval before modifying files
5. Remind the user to commit config changes before running experiments

## Related Skills

- **`dataset-lifecycle`** — Dataset versioning rules, version pinning, increment conventions, and the full dataset lifecycle.
- **`configure-experiment`** — Project structure, config group composition, and experiment setup.
