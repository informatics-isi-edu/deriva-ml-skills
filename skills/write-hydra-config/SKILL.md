---
name: write-hydra-config
description: "Write, bootstrap, and validate hydra-zen config files for DerivaML — DatasetSpecConfig, asset_store, builds(), experiment_config, multirun_config, with_description. Use when adding/editing/updating any config in configs/, when bootstrapping a fresh project's configs from an existing catalog (per-config-group recipes + a worked end-to-end example), or when validating that config RIDs and versions match the catalog (singular validators per group, whole-tree composition, or the single-call deriva_ml_validate_config_file tool). Triggers on: 'write hydra config', 'edit datasets.py', 'edit assets.py', 'bootstrap configs', 'populate configs from catalog', 'validate config', 'validate datasets.py', 'check config matches catalog'. Auto-fires when editing a config file or wiring a RID into configs/, the mechanics behind the dataset-lifecycle/execution-lifecycle 'add the RID to configs' offers. Do NOT use for config-group composition/project structure (use configure-experiment)."
user-invocable: true
---

# Writing Hydra-Zen Config Files for DerivaML

This skill is the authoritative reference for the Python API used in DerivaML hydra-zen configuration files. Every config group has a specific pattern — follow the examples exactly.

## When to Use This Skill

- Writing a new config file (`datasets.py`, `assets.py`, `model.py`, etc.)
- Adding a new entry to an existing config file
- After creating a catalog entity (dataset, asset, workflow) that should be added to configs
- Fixing or updating existing config entries
- **Bootstrapping a fresh project's configs from an existing catalog** — per-config-group recipes and a worked end-to-end example
- **Validating that config RIDs and versions exist in the catalog** — the single-call `deriva_ml_validate_config_file` tool, or singular per-group validators + whole-tree composition for granular debugging

After any catalog-modifying action (`deriva_ml_create_dataset`, `deriva_ml_create_workflow`, or running a splitting script that calls `split_dataset(ml, source_rid, exe, ...)` from the Python API, etc.), proactively offer to update the relevant config file using these patterns.

## Reference File

- `references/config-reference/` — Annotated examples and starter templates for every config group. Each section shows a populated example from a real project, followed by a minimal template. Read the relevant section when writing or modifying a specific config file.

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

The high-leverage rules that change what you write. The exhaustive per-group rule
list is in `references/config-reference/rules-and-validation.md` → "Per-Group Key Rules"; read it when
authoring a specific group.

- **Datasets** — `version` is **required** and must be a **released** PEP 440 string (`"0.9.0"`); never an integer, never a `.devN` dev label (dev labels are mutable, pinning to one defeats reproducibility). Default config uses a plain list; non-default configs use `with_description()`. Find the released version via `deriva_ml_get_dataset(...)`; if `current_version` is a dev label, `deriva_ml_release_dataset(...)` first.
- **Assets** — plain RID strings (`["3WS6", "3X20"]`) or `AssetSpecConfig(rid=..., cache=True)` for large immutable files. Default/empty configs use plain lists.
- **Workflow** — `builds(Workflow, ...)` with `populate_full_signature=True`; git URL + commit hash captured automatically at runtime.
- **Model Config** — `zen_partial=True` is **required** (execution context injected later) + `populate_full_signature=True`. Override params when registering variants.
- **Experiments** — `package="_global_"` on the `store()` call; group is `"experiment"` (singular). **PITFALL**: base-config optional fields defaulting to `None` (e.g. `script_config`) shadow Hydra's resolved override — use `MISSING` from `hydra_zen` for any optional field you override via the defaults list.
- **Multiruns** — first arg is the name (string, not keyword); `overrides` is a list of Hydra override strings; no `--multirun` flag needed.

> Plain-list-vs-`with_description` matters for merge: `with_description` builds a DictConfig that can't merge with BaseConfig's ListConfig, so the **default** config of a group must stay a plain list.

## Description Mechanisms

Pick the mechanism by config type: **lists** (datasets, assets) → `with_description(items, "...")`; **`builds()` configs** (models, connections) → `zen_meta={"description": "..."}`; **experiments** → `description=` on `make_config()`; **multiruns / notebooks** → `description=` on `multirun_config()` / `notebook_config()`. Descriptions land in execution metadata, so make them specific, quantified, purposeful, and version-aware — state the *goal/hypothesis*, not the parameters (those are already in the config). Before writing, look up catalog details via `deriva_ml_get_dataset(...)` / `deriva_ml_lookup_asset(...)`.

Full mechanism table + per-config-type good/bad description examples: `references/config-reference/rules-and-validation.md` → "Description Mechanisms and Good Descriptions".

## Config Class Parameter Reference

Exhaustive parameter tables for `DerivaMLConfig`, `DatasetSpecConfig`, `AssetSpecConfig`, and `LocalFileConfig` (every field, type, default, description) are in `references/config-reference/rules-and-validation.md` → "Config Class Parameter Reference". The load-bearing distinctions:

- **`AssetSpecConfig`** pins a catalog-resident asset by RID. **Role is by context, never a field** — there is no `asset_role` parameter; an asset in `assets=` is an Input because it's consumed. The strict model **rejects** a stray `asset_role=`.
- **`LocalFileConfig`** declares an external local file by **path** (not RID) — registered as a referenced `File` row + Input edge, **not uploaded to Hatrac**. Use for files that must stay local (e.g. sensitive source CSVs) while keeping lineage.
- **`DerivaMLConfig`** — never set `hydra_runtime_output_dir` (Hydra sets it). `catalog_id` defaults to `1`; `use_minid` auto-enables when `s3_bucket` is set.

## Wiring fresh RIDs into config files

Three skills produce new RIDs the user may want to consume downstream:

| Source skill | What it produces | When to offer |
|---|---|---|
| [`dataset-lifecycle`](../dataset-lifecycle/SKILL.md) | New dataset RIDs + released versions (create, split, release, curated subset) | The skill prompts the offer; this skill owns the *shape* |
| [`work-with-assets`](../work-with-assets/SKILL.md) | Single asset RID (asset-table creation, ad-hoc upload, role-tagged registration — one at a time) | Same |
| [`execution-lifecycle`](../execution-lifecycle/SKILL.md) | Bulk output assets from a completed run (N at once, all linked to one execution) | Same |

When any of those skills surfaces a new RID, the user-facing offer comes from there. The **format of the resulting config entry** lives here — read this section for the field reference, the canonical line generator, the file structure, and the commit conventions.

### Generating the canonical entry line

The Python-API generators below produce the exact string to paste into the config file. They handle PEP-440-correct version formatting (released, no dev labels) and ensure every required field is set.

| Entry kind | Generator | Why prefer it over hand-typing |
|---|---|---|
| `DatasetSpecConfig` | `deriva_ml_get_dataset_spec(hostname=..., catalog_id=..., dataset_rid=..., version=...)` | Only call that guarantees the version segment is PEP-440 released-only (no `.devN` suffix would silently slip past pin-the-version reproducibility) |
| `AssetSpecConfig` | Read the asset details first via `deriva://catalog/{h}/{c}/deriva-ml/asset/{rid}` or `deriva_ml_lookup_asset(...)`, then write `AssetSpecConfig(rid="<rid>", cache=<True\|False>)`. Choose `cache=True` for large immutable files (model weights, reference images); leave default for small files that may evolve. **No `asset_role`** — role is by context (a declared asset is an Input) |
| `LocalFileConfig` | For an **external local file** input (a CSV/file on disk, not a catalog asset), write `LocalFileConfig(path="<local/path>")`. Registers a referenced `File` row + Input edge, no Hatrac upload. Use a path the run will find at execution time; the same constant can feed both this entry and the script's read path |

### File structure conventions

- Wrap the new entry under the existing `datasets_store(...)` or `assets_store(...)` registration in the matching file (`src/configs/datasets.py` or `src/configs/assets.py`). Mirror the surrounding entries' shape.
- Use `with_description(items, "...")` to attach a human-readable description if the file's other entries do.
- Default configs (the one Hydra picks when no override is given) should use plain lists — `with_description` interferes with merge composition.

### Commit conventions

The git hash in execution records must match the config state at run time, so config edits commit on their own — never bundled with unrelated changes:

| Source skill | Suggested commit message |
|---|---|
| `dataset-lifecycle` (single new dataset / split children) | `chore(configs): add <name> dataset RIDs from <date> run` |
| `dataset-lifecycle` (version bump after release) | `chore(configs): bump <name> to <new_version>` |
| `work-with-assets` (single new asset RID) | `chore(configs): add <name> asset (RID <rid>)` |
| `execution-lifecycle` (bulk outputs from a completed run) | `chore(configs): add outputs from execution <rid>` |

The execution or release RID in the message is the cross-reference back to provenance — a reader scanning `git log src/configs/` can trace each entry back to the action that produced it.

### Decision hand-back

The offer is *one prompt*. If the user declines, **acknowledge plainly** so future invocations in the same session don't re-offer the same RIDs. The config file isn't a side effect — the user has owned the decision. If they later change their mind, they'll ask again.

### After the entry is committed

- For *wiring* the new dataset / asset into a downstream experiment config (`input_assets=[...]`, `datasets=[...]`), see [`configure-experiment`](../configure-experiment/SKILL.md).
- For *validating* the new entry against the catalog before running, use `deriva_ml_validate_config_file(hostname=..., catalog_id=..., file_contents=<file>)` — see "Validating Configs Against the Catalog" below.

## MCP Reference Resources

Substitute your catalog's hostname and ID wherever examples show them. The most-reached-for: `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/dataset/{rid}` (dataset details incl. current version, or call `deriva_ml_get_dataset(...)`). Full list of `deriva://docs/*` and `deriva://config/*` starter-template resources: `references/config-reference/rules-and-validation.md` → "MCP Reference Resources".

## Bootstrap Configs from a Catalog

Three situations bring you here: a **new project** (empty `src/configs/` to populate from a catalog), a **catalog clone** (repoint fresh configs at a new catalog id), or an **incremental update** (one new entity needs an entry, rest is correct).

> **Cardinal rule:** bootstrap reads the catalog and *proposes* entries. The agent writes the file; the user reviews. Don't write files from inferred state without confirmation — RIDs are forever, configs land in git, and mis-pointing a `deriva_ml` group at the wrong catalog produces silent cross-environment leaks.

**Fast path — one call:** `deriva_ml_bootstrap_config(hostname, catalog_id, kinds=[...])` walks the catalog and returns ready-to-paste config bodies (each with a `spec_string` + `rationale`) for every group in one round trip. Prefer it for fresh-project and catalog-clone bootstraps. It's a pure read — it does NOT write files.

**Granular path — per-group recipes + worked fresh-catalog example:** the per-config-group catalog queries (which tool/resource discovers each group's entries, the entry shape, the heuristics for picking which datasets/assets to bootstrap) and a full Step 1–6 worked example (`localhost` catalog `19` → populated `src/configs/`) are in `references/config-reference/rules-and-validation.md` → "Bootstrap Configs from a Catalog". Use these for incremental updates or when you want to drive the discovery one group at a time.

Quick orientation on which groups bootstrap from the catalog vs. are hand-authored project code:

| Group | Bootstraps from catalog? | Discovery |
|---|---|---|
| `deriva_ml` | Yes (hostname + catalog_id + heartbeat) | `deriva_ml_list_datasets` proves the catalog answers |
| `datasets` | Yes — one entry per consumed dataset | `deriva_ml_get_dataset_spec(...)` → canonical version-correct line |
| `assets` | Yes — pinned inputs (skip prior-run outputs) | `deriva_ml_lookup_asset(...)` → RID + filename + MD5 |
| `workflow` | Rarely — minted on first run; bootstrap only when cloning a sibling project's RIDs | `deriva_ml_list_workflows` / `find_workflow_by_url` |
| `model_config`, `multiruns` | No — project code (hyperparameters, sweeps) | Hand-author |
| `experiments` | Stitched last, by name, from the groups above | — |

## Validating Configs Against the Catalog

Before running experiments, validate that all RIDs and versions in config files actually exist in the target catalog.

**Whole-file gate (preferred):** `deriva_ml_validate_config_file(hostname, catalog_id, file_contents)` parses the file via AST (no execution) and validates every `DatasetSpecConfig` / `AssetSpecConfig` / `Workflow` / `DerivaMLConfig` call in one round trip. Pass the file **contents** as a string (the v0.5.0+ signature dropped `file_path=` — the server's filesystem view doesn't match the caller's). Returns a `ConfigValidationReport` with a per-entry `valid` flag, `reasons`, and `available_versions` for `version_not_found`. This is the one-shot pre-flight gate and the after-a-release re-check.

**Singular validators (granular debugging):**

| Tool | Scope | When to use |
|---|---|---|
| `deriva_ml_validate_dataset_specs` | List of (RID + version) pairs you provide | Iterating on `datasets.py`; debugging one spec |
| `deriva_ml_lookup_asset` | One asset RID at a time | Iterating on `assets.py`; confirming a RID exists and is the expected type |
| `deriva_ml_validate_execution_configuration` | A complete `ExecutionConfiguration` (datasets + assets + workflow + cross-spec consistency) | Pre-flight before `deriva-ml-run`; whole-experiment sanity |

> **Why not `dry_run=True`?** `dry_run=True` validates the config but by actually downloading every bag and materializing every asset — minutes-to-hours and GBs. The validators above are the cheap metadata-only alternative. See deriva-ml ADR-0002.

The exhaustive validator recipes — per-tool call examples, the by-composition whole-tree walk (for when you want per-group reports), the common-fix patterns table, the `deriva_ml_validate_config_file` report shape, and the `lookup_term` workflow-type-existence check — are in `references/config-reference/rules-and-validation.md` → "Validating Configs Against the Catalog". That section also carries the full "Common Issues" symptom/cause/fix table (RID not found, stale version, dev-label-in-`current_version`, wrong catalog).

### Proactive Validation

After any catalog-modifying action (`deriva_ml_create_dataset`, `deriva_ml_release_dataset`, running a splitting script that calls `split_dataset(ml, source_rid, exe, ...)` from the Python API, etc.), proactively:

1. Note the new RID, version, and description
2. Check if existing config files reference the affected entity
3. Offer to update configs if versions are stale or new entities should be added
4. Present changes for approval before modifying files
5. Remind the user to commit config changes before running experiments

## Related Skills

- **`dataset-lifecycle`** — Dataset versioning rules, version pinning, increment conventions, and the full dataset lifecycle.
- **`configure-experiment`** — Project structure, config group composition, and experiment setup.
