---
type: ConfigReference
title: Config rules, parameter reference, bootstrap & validation
description: Per-group key rules, the description mechanisms, the full config-class parameter tables, MCP starter resources, and how to bootstrap/validate configs against a catalog.
---

# Config rules, parameter reference, bootstrap & validation

## Per-Group Key Rules

The detailed authoring rules for each config group. The SKILL.md body carries
the one-line summary and the compose/defaults-list mental model; this section is
the exhaustive per-group rule list.

### Datasets
- `version` is **required** — always a **released** PEP 440 string like `"0.9.0"`, not an integer, not a dev label (no `.devN` suffix). Dev labels are mutable; pinning a config to one defeats reproducibility.
- Use `with_description()` for non-default configs
- Default configs use plain lists (no `with_description`) for merge compatibility
- Find the current released version via `deriva_ml_get_dataset(hostname=..., catalog_id=..., dataset_rid="<rid>")` or read the `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/dataset/{rid}` MCP resource
- If `current_version` comes back as a dev label (`<release>.post1.devN`), the dataset is mid-mutation. Call `deriva_ml_release_dataset(hostname=..., catalog_id=..., dataset_rid=..., bump="minor", description="...")` to promote the dev period to a released version, then pin the config to the new release.

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

---

## Description Mechanisms and Good Descriptions

Two mechanisms exist — use the right one for the context:

| Config Type | Mechanism | Example |
|---|---|---|
| Lists (datasets, assets) | `with_description(items, "...")` | `with_description([DatasetSpecConfig(...)], "Training images v3")` |
| `builds()` configs (models, connections) | `zen_meta={"description": "..."}` | `store(Config, name="x", zen_meta={"description": "..."})` |
| Experiments | `description=` param on `make_config()` | `make_config(..., description="Quick training run")` |
| Multiruns | `description=` param on `multirun_config()` | `multirun_config("name", ..., description="...")` |
| Notebooks | `description=` param on `notebook_config()` | `notebook_config("name", ..., description="...")` |

Descriptions are recorded in execution metadata and make experiments self-documenting. Before writing descriptions, look up catalog details via `deriva_ml_get_dataset(hostname=..., catalog_id=..., dataset_rid=...)` (or the resource `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/dataset/{rid}`) and `deriva_ml_lookup_asset(hostname=..., catalog_id=..., asset_rid=...)`.

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

---

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
| `fetch_concurrency` | `int` | `8` | Parallelism for bag fetch. Lower if the catalog is rate-limiting; raise for fast networks |

### `AssetSpecConfig` (from `deriva_ml`)

Pins a **catalog-resident** asset (by RID) as an input the experiment consumes.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `rid` | `str` | *(required)* | Asset RID |
| `cache` | `bool` | `False` | Cache asset locally by MD5. Use for large immutable files (model weights) |

> **Role is by context, never a field.** There is no `asset_role` parameter. An
> asset declared in `assets=` is an **Input** because it is consumed; assets a run
> *produces* become **Outputs** when uploaded (via `asset_file_path` +
> `commit_output_assets`). The strict config model **rejects** a stray
> `asset_role=` — do not write one. (`asset_role` still exists as a read-side
> *filter* on query methods like `exe.list_assets(asset_role=...)`; that is
> unrelated to declaring a config entry.)

### `LocalFileConfig` (from `deriva_ml.execution`)

Declares an **external local file** (e.g. a CSV on disk) as an input — by
**path**, not RID. On input resolution the framework registers it as a referenced
`File` row (path/URL + MD5) and links it to the execution as an Input edge
(role from context). It is **not uploaded to Hatrac** — use this for files that
should stay local (e.g. a source CSV carrying sensitive data) while still giving
lineage from the run's outputs back to the source file.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | *(required)* | Local filesystem path (or URL) of the file to register and consume |
| `cache` | `bool` | `False` | Cache locally by MD5 (mirrors `AssetSpecConfig.cache`) |

---

## MCP Reference Resources

> Every MCP tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

- `deriva://docs/hydra-zen` — Full guide to hydra-zen configuration management in DerivaML
- `deriva://docs/execution-configuration` — Execution configuration reference
- `deriva://config/deriva-ml-template` — Starter template for DerivaML connection config
- `deriva://config/dataset-spec-template` — Starter template for dataset specs
- `deriva://config/model-template` — Starter template for model configs with `zen_partial`
- `deriva://config/experiment-template` — Starter template for experiment presets
- `deriva://config/multirun-template` — Starter template for multirun sweeps
- `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/dataset/{rid}` — Look up dataset details including current version (or call `deriva_ml_get_dataset(hostname=..., catalog_id=..., dataset_rid=...)`)
- Browse available `Workflow_Type` vocabulary terms with `list_vocabulary_terms(hostname=..., catalog_id=..., schema="deriva-ml", table="Workflow_Type")`

---

## Bootstrap Configs from a Catalog

Three situations bring you here:

- A new project — `src/configs/` exists as empty templates and needs to be populated from a catalog that already has datasets, workflows, and assets registered.
- A catalog clone — you've cloned a catalog and want to point fresh configs at the new catalog id.
- An incremental update — a single new entity (e.g., a freshly-released dataset) needs a config entry, but the rest of the configs are already correct.

The recipes below cover the per-config-group catalog queries; the worked example at the end ties them into a fresh-project bootstrap sequence.

> **Cardinal rule:** bootstrap reads the catalog and *proposes* entries. The agent writes the file; the user reviews. Don't write files from inferred state without confirmation — RIDs are forever, configs land in git, and mis-pointing a `deriva_ml` group at the wrong catalog produces silent cross-environment leaks.

> **Fast path:** `deriva_ml_bootstrap_config(hostname, catalog_id, kinds=[...])` returns ready-to-paste config bodies for every group in one round trip. Prefer it over the per-group recipes below for fresh-project or catalog-clone bootstraps; the recipes are for incremental / granular cases.

### Per-config-group recipes

#### `deriva_ml` (`src/configs/deriva.py`)

The connection group. You need a `hostname` + `catalog_id` and ideally a sanity-check that the catalog responds.

```
# Discovery — prefer the resource form (one round trip, no pagination)
# Read deriva://catalog/{hostname}/{catalog_id}/deriva-ml/datasets
# Look for non-zero datasets; any error here means the bootstrap can't proceed.

# Equivalent tool form if you need filters or paginated browsing:
deriva_ml_list_datasets(hostname="data.example.org", catalog_id="1")

# Or, for a multi-catalog server:
# Read deriva://registry/{hostname} to see available catalog aliases.
```

Entry shape (from "Deriva Connection" above):

```python
deriva_store(
    DerivaMLConfig,
    name="default_deriva",
    hostname="data.example.org",
    catalog_id="1",
    use_minid=False,
)
```

The `name=` is the Hydra config name (`deriva_ml=default_deriva`); pick names that distinguish environments (`default_deriva`, `prod_deriva`, `dev_deriva`).

#### `datasets` (`src/configs/datasets.py`)

The dataset group. One entry per dataset the project's experiments will consume.

```
# Browse all datasets in the catalog
deriva_ml_list_datasets(hostname="data.example.org", catalog_id="1")
# Returns RID, description, types, current_version, members per dataset.

# Or the resource form (one round trip):
# Read deriva://catalog/{hostname}/{catalog_id}/deriva-ml/datasets

# Per-dataset spec string (canonical, version-correct):
deriva_ml_get_dataset_spec(hostname=..., catalog_id=..., dataset_rid="2-B4C8")
# Returns a ready-to-paste `DatasetSpecConfig(...)` line.
```

Entry shape:

```python
datasets_store(
    name="cifar10_training",
    spec=DatasetSpecConfig(rid="2-B4C8", version="0.4.0"),
)
```

**Heuristics for picking which datasets to bootstrap:**

- Filter by dataset_type — `Training` / `Testing` / `Validation` / `Complete` / `Labeled` are the ones experiments consume. `Split` parents are usually navigated *to* children, not consumed directly.
- Prefer released versions (no `.devN` suffix). If a dataset only has a dev label, ask whether to skip it or call `deriva_ml_release_dataset(...)` first.
- Use `with_description(...)` if the file uses it; pull the description from the dataset record itself for consistency.

#### `assets` (`src/configs/assets.py`)

The asset group. One entry per asset (or asset group) experiments will pin as input.

```
# Browse assets in a schema
# Read deriva://catalog/{hostname}/{catalog_id}/deriva-ml/assets/{schema}
# Or paginated:
deriva_ml_list_assets(hostname="data.example.org", catalog_id="1")

# Per-asset metadata (RID + filename + MD5):
deriva_ml_lookup_asset(hostname=..., catalog_id=..., asset_rid="3-WTS1")
```

Entry shape:

```python
assets_store(
    name="cifar10_quick_weights",
    spec=AssetSpecConfig(rid="3-WTS1", cache=True),
)
```

**Heuristics:**

- Set `cache=True` for large, immutable files (model weights, large images) — caches by MD5 so re-downloads are skipped.
- Group related output assets (weights + predictions + plot from one training run) under a single config name if they'll always be consumed together.
- Skip auto-generated metadata (notebook `.ipynb`, hydra dumps); experiments don't pin those.

#### `workflow` (`src/configs/workflow.py`)

The workflow group. Typically one entry per script the project runs.

```
# Browse existing workflows — prefer the resource form (one round trip)
# Read deriva://catalog/{hostname}/{catalog_id}/deriva-ml/workflows

# Equivalent tool form if you need pagination or filters:
deriva_ml_list_workflows(hostname="data.example.org", catalog_id="1")

# Or find one by url:
deriva_ml_find_workflow_by_url(hostname=..., catalog_id=..., url="<git url>")
```

For bootstrap, the question is usually "does this script already have a Workflow row?" If yes, use its RID directly; if no, the workflow gets created at first-run time via `ml.create_workflow(...)` from the script and you don't need to pre-populate the config.

**Workflow configs are usually built, not bootstrapped** — they reference a script that's about to exist, and the Workflow row is minted on first execution. The interesting bootstrap case is when you're cloning configs from a sibling project and want to re-use existing workflow RIDs by name.

#### `model_config` (`src/configs/<model>.py`)

Project code, not catalog state. Bootstrap doesn't apply — this is where your model's hyperparameters live (epochs, lr, batch_size, architecture). Hand-author.

#### `experiments` (`src/configs/experiments.py`)

Composition group — picks one entry from each of the above. Bootstrap can stitch a default experiment together once the other groups are populated:

```python
experiment_store(
    name="cifar10_quick_train",
    deriva_ml="default_deriva",
    datasets={"training": "cifar10_training", "testing": "cifar10_testing"},
    workflow="train_cifar10_cnn",
    model_config="cifar10_quick",
)
```

Pull the choice-names from the entries you just registered. Don't invent new names — Hydra will silently use defaults if you point at a non-existent group entry.

#### `multiruns` (`src/configs/multiruns.py`)

Project code, not catalog state. Bootstrap doesn't apply.

### Worked end-to-end example: fresh-catalog bootstrap

Scenario: someone hands you a catalog id (`localhost`, catalog `19`) and asks you to populate the model template's `src/configs/` from scratch.

> Each tool call below has a resource-form equivalent (`deriva://catalog/{h}/{c}/deriva-ml/datasets`, `…/ml/assets/{schema}`, `…/ml/workflows`) — one round trip, no pagination cost. The tool form is shown here for readability; either works. See `deriva-ml-context` → "Read-side questions: fetch the resource first."

```python
# Step 1: confirm the catalog answers and capture inventory.
deriva_ml_list_datasets(hostname="localhost", catalog_id="19")
# -> list of datasets with RIDs, types, current_version
# Filter to Training / Testing / Validation / Complete / Labeled types.
# Note the released-version RIDs you want to consume.

deriva_ml_list_assets(hostname="localhost", catalog_id="19")
# -> asset tables and a snapshot of asset RIDs
# Note any that are pre-existing inputs (e.g., pretrained weights you'll
# pin as an asset). Skip outputs from prior runs (those land via
# execution-lifecycle's offer, not here).

deriva_ml_list_workflows(hostname="localhost", catalog_id="19")
# -> workflow RIDs and their urls. Usually empty on a fresh project,
# since workflows are minted on first run.

# Step 2: edit src/configs/deriva.py to point at the new catalog.
# Replace catalog_id=0 with 19. Commit immediately so subsequent
# bootstrap edits compose against the right connection.

# Step 3: for each dataset you'll consume, get the canonical spec string.
deriva_ml_get_dataset_spec(
    hostname="localhost", catalog_id="19", dataset_rid="2-B4C8",
)
# -> "DatasetSpecConfig(rid='2-B4C8', version='0.4.0')"
# Paste under a datasets_store(name=..., spec=...) registration.
# Repeat for each dataset.

# Step 4: for each asset you'll pin, get its metadata.
deriva_ml_lookup_asset(
    hostname="localhost", catalog_id="19", asset_rid="3-WTS1",
)
# -> filename, MD5, size — useful for description text. Paste under an
# assets_store(name=..., spec=AssetSpecConfig(rid=..., cache=...)) registration.

# Step 5: stitch an experiment that references all the above by name.
# experiments_store(name="default", deriva_ml="default_deriva",
#                   datasets={...}, workflow=None, model_config=...)

# Step 6: validate the whole tree against the catalog before committing.
# (see "Validating Configs Against the Catalog" below)
```

The agent that runs this drives one round-trip per `deriva_ml_get_dataset_spec` / `deriva_ml_lookup_asset`. That's tolerable for a one-time bootstrap (N usually < 20). For routine re-bootstrap against a heavily-populated catalog, use `deriva_ml_bootstrap_config(hostname, catalog_id, kinds=[...])` — one round trip that returns ready-to-write config bodies.

---

## Validating Configs Against the Catalog

Before running experiments, validate that all RIDs and versions in config files actually exist in the target catalog. The single-call tool covers the whole tree; the singular validators below are for granular per-group debugging.

| Tool | Scope | When to use |
|---|---|---|
| `deriva_ml_validate_config_file` | Whole `src/configs/` file — parses via AST, validates every dataset spec, asset spec, and workflow reference in one round trip | One-shot pre-flight gate; after a release lands |
| `deriva_ml_validate_dataset_specs` | List of dataset specs (RID + version pairs) you provide explicitly | Iterating on `datasets.py`; debugging a specific spec |
| `deriva_ml_lookup_asset` | One asset RID at a time | Iterating on `assets.py`; confirming an asset RID exists and is the expected type |
| `deriva_ml_validate_execution_configuration` | A complete `ExecutionConfiguration` (datasets + assets + workflow + cross-spec consistency) | Pre-flight check before `deriva-ml-run`; whole-experiment sanity |

### Single-call whole-file validation — `deriva_ml_validate_config_file`

The one-shot gate. Pass the file contents (the v0.5.0+ signature takes
`file_contents=`, not a path — the MCP server's filesystem view does not match
the caller's); the tool parses every `*Config(...)` constructor via AST (no
execution) and returns a structured per-entry report:

```
deriva_ml_validate_config_file(
    hostname="data.example.org",
    catalog_id="1",
    file_contents=<contents of src/configs/datasets.py>,
)
```

Returns a `ConfigValidationReport`: `{"file_count", "entry_count", "all_valid", "results": [...], "parse_errors": [...]}`. Each result carries the parsed entry (file, line, kind, rid, version), a `valid` flag, a `reasons` list, and helpful detail like `available_versions` for `version_not_found`.

### Iterating on `datasets.py` — `deriva_ml_validate_dataset_specs`

When you're editing `src/configs/datasets.py` and want to confirm the `(RID, version)` pairs you typed actually resolve, use the singular validator:

```
deriva_ml_validate_dataset_specs(
    hostname="data.example.org",
    catalog_id="1",
    specs=[
        {"rid": "2-B4C8", "version": "0.4.0"},
        {"rid": "2-XYZ9", "version": "1.0.0"},
    ],
)
```

Returns per-spec results with three failure modes (`rid_not_found`, `not_a_dataset`, `version_not_found`) and helpful detail (`available_versions` populated when the version is wrong — usually a typo). Fast: ~one round-trip per spec.

### Pre-flight before `deriva-ml-run` — `deriva_ml_validate_execution_configuration`

When you're about to run an experiment and want to confirm the whole `ExecutionConfiguration` resolves cleanly (datasets + assets + workflow + cross-spec consistency), use the composite validator:

```
deriva_ml_validate_execution_configuration(
    hostname="data.example.org",
    catalog_id="1",
    config={
        "workflow": {"name": "training_workflow", "url": "...", "checksum": "..."},
        "datasets": [{"rid": "2-B4C8", "version": "0.4.0"}],
        "assets": [{"rid": "3-WXYZ"}],
    },
)
```

Returns per-spec results (datasets, assets, workflow) plus cross-spec issues (`duplicate_rid`, `version_conflict`, `role_conflict`).

> **Why not `dry_run=True`?** Setting `dry_run=True` on an Execution does validate the config, but by actually downloading every dataset bag and materializing every asset — minutes-to-hours and several GB of bandwidth. `validate_execution_configuration` is the cheap metadata-only alternative for fast iteration. See deriva-ml ADR-0002 for the full rationale.

### Iterating on `assets.py` — `deriva_ml_lookup_asset` per-RID

For asset-by-asset validation, loop `deriva_ml_lookup_asset` over each RID in `assets.py`. For whole-file validation, use `deriva_ml_validate_config_file` (above):

```
for rid in [asset_rid for entry in src/configs/assets.py]:
    deriva_ml_lookup_asset(hostname="data.example.org", catalog_id="1", asset_rid=rid)
```

Three things to check on each response:

1. **The call succeeds** — `not_found` means the RID doesn't exist or you're pointing at the wrong catalog.
2. **The `asset_type` matches what your `assets.py` description claims** — a `prediction_probabilities.csv` filed under a "model_weights" config name is a copy-paste error worth catching.
3. **The MD5 / size hasn't drifted from when the config was last validated** — assets are usually immutable, but the `MD5` field will diverge if the file was re-uploaded.

### Whole-tree validation by composition

`deriva_ml_validate_config_file` is the single-call path for this. The composition recipe below is the granular fallback when you want per-group reports or are debugging one file at a time.

1. **Enumerate every `*Config(...)` constructor call** across `src/configs/*.py`. Sources to look for:
   - `DatasetSpecConfig(rid=..., version=...)` — datasets
   - `AssetSpecConfig(rid=..., ...)` — assets
   - `Workflow(rid=..., ...)` or workflow_rid string references in experiments
   - `DerivaMLConfig(hostname=..., catalog_id=...)` — connection groups (validate the catalog responds)

2. **Batch the dataset specs into one `validate_dataset_specs` call** — that one's already batched server-side:

   ```
   deriva_ml_validate_dataset_specs(
       hostname=..., catalog_id=...,
       specs=[<every DatasetSpecConfig you found>],
   )
   ```

3. **Loop `deriva_ml_lookup_asset` over each asset RID** — N round-trips, but assets are typically a handful per project.

4. **Loop `deriva_ml_get_workflow` over each workflow RID** if your `workflow.py` pins RIDs (most projects let workflows mint at first-run, in which case skip this).

5. **For each connection group**, run a heartbeat — read `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/datasets` (resource form, one round trip) or call `deriva_ml_list_datasets(...)` if you need filters. Either proves the catalog answers.

6. **Aggregate the per-tool reports** into one summary the user reviews. For each entry, surface:
   - File + line where the entry lives
   - RID + entity kind
   - Verdict: `valid` / `rid_not_found` / `not_an_X` / `version_not_found` / `version_stale` / `catalog_unreachable`
   - For `version_not_found`: the available versions (from `validate_dataset_specs`'s response)

**Common-fix patterns:**

| Symptom | Likely cause | Fix |
|---|---|---|
| `rid_not_found` for a single dataset | Catalog id mismatch — `deriva.py` points at a different catalog than the configs were authored against | Either repoint `deriva.py` or rebootstrap the dataset entries from the right catalog |
| `version_not_found` for many datasets, all at the same `.X.Y.Z` | A release cycle landed; configs lag by one minor version | Update each `DatasetSpecConfig.version` to the new release (`deriva_ml_get_dataset_spec` regenerates the canonical line) |
| `not_an_asset` | RID exists but it's a dataset or feature row, not an asset | Copy-paste error between configs; check the source dataset for an `Execution_Asset` link to the actual file |
| `catalog_unreachable` | Server or auth issue | Check `deriva_ml` group hostname and the MCP server's catalog reachability (`deriva_ml_list_datasets` should answer in <1s) |

### Workflow-type term existence

For workflow-type checks (separate from the workflow row itself), use:

```
lookup_term(hostname=..., catalog_id=..., schema="deriva-ml", table="Workflow_Type", name="Training")
```
