---
name: dataset-lifecycle
description: "Use this skill for ALL DerivaML dataset operations — creating, populating, splitting, versioning, browsing, and downloading datasets. Covers: creating datasets and adding members, train/test/validation splits (stratified, labeled, dry run), dataset version management after catalog changes, choosing and designing dataset types (orthogonal tagging), exploring and browsing dataset contents by element type using deriva_ml_denormalize_dataset, navigating parent/child hierarchies, downloading BDBags (timeouts, exclude_tables, deriva_ml_bag_info), restructuring assets for ML frameworks, and referencing datasets in experiment configs via DatasetSpecConfig. Also covers preparing datasets specifically for model training — stratified splits by label distribution, setting up training/validation/testing partitions, and creating explicit split datasets in the catalog rather than computing on the fly. Triggers on: 'create a dataset', 'split dataset', 'stratify', 'train test split', 'prepare data for model', 'dataset version', 'what is in this dataset', 'browse dataset', 'wide table', 'flat table', 'denormalize', 'dataset types', 'element types', 'BDBag download', 'DatasetSpecConfig', 'add members', 'list members', 'dataset children', 'training data setup', 'curated subset', 'filter dataset', 'subset by class', 'select by value', 'create labeled dataset', 'filter by feature', 'subset with labels', 'has feature', 'images with labels', 'records that have', 'build dataset from'. Do NOT use for: creating features/labels (use create-feature), creating tables (use create-table), running experiments (use execution-lifecycle), uploading assets (use work-with-assets), or managing vocabularies (use manage-vocabulary)."
---

# Dataset Lifecycle

This skill covers the full lifecycle of a DerivaML dataset: assessing whether one is needed, planning its structure and types, creating and populating it, versioning for reproducibility, and consuming it in experiments.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly.

**Check project context first.** Before running any commands, look for catalog references in the project: `experiment-decisions.md` records which catalog/hostname previous operations used; `src/configs/deriva.py` carries hydra-zen connection configs; `CLAUDE.md` may specify the working catalog. Use the catalog the project is actively working with, NOT the original source catalog (e.g., the clone on dev.facebase.org, not the source on www.facebase.org). If you don't know the catalog ID, read `deriva://registry/{hostname}` to see available catalogs and aliases.

## Phase 1: Assess

Before creating a dataset, determine whether an existing one can be reused, extended, or split. The find-before-you-create discipline is carried by `/deriva:semantic-awareness` *(deriva-skills, auto-fires)* — its synonym/abbreviation/spelling-variant search expansion applies to ML entities (Datasets) as well as generic catalog entities. The same skill covers the EAV-vs-wide-table dual extreme, which is worth knowing when designing the *element-type* tables a dataset will draw members from.

1. **Search existing datasets.** `rag_search("your purpose", doc_type="catalog-data")` finds datasets by description, type, or purpose. Fall back to `deriva_ml_list_datasets(hostname, catalog_id)` for the full structured list. Use `get_table_sample_data(...)` to understand how much data is available.
2. **Check available element types.** Call `deriva_ml_list_dataset_element_types(hostname, catalog_id)` to see which tables can contribute members. If the table you need isn't registered, call `deriva_ml_add_dataset_element_type(hostname, catalog_id, element_table=...)`.
3. **Decide: reuse, extend, or create.**

| Situation | Action |
|-----------|--------|
| Existing dataset covers your need | Reuse it — reference its RID + version in config |
| Existing dataset needs more members | `deriva_ml_add_dataset_members` to extend it |
| Need a different split of existing data | `deriva_ml_split_dataset` from the existing dataset |
| Need a focused subset for an experiment | Create a new dataset (curated subset — see below) |
| Building from scratch | Bootstrap a new dataset from raw table data |

## Phase 2: Plan

### Choose the dataset structure

| Pattern | When to use | How |
|---------|-------------|-----|
| Standalone | Building a new collection from scratch | `deriva_ml_create_dataset` |
| Split children | Need train/test/val partitions | `deriva_ml_split_dataset` from a parent |
| Curated subset | Focused set filtered by data values | Generate from template — see `references/curated-subsets.md` |
| Manual nesting | Grouping related datasets together | `deriva_ml_create_dataset` + `deriva_ml_add_dataset_members(parent_rid, members={"Dataset": [child_rid]})` |

### Choose dataset types

Types describe **independent dimensions** of a dataset — orthogonal tags, not a hierarchy. A dataset gets one or more tags from each relevant dimension.

Built-in dimensions: partition role (`Training`, `Testing`, `Validation`, `Complete`, `Split`) and annotation status (`Labeled`, `Unlabeled`). Apply at least one type — untyped datasets are hard to discover. Compose types freely across dimensions (`Training` + `Labeled` + `Fundus`); never compound them (`TrainingLabeled` is wrong).

For DerivaML-specific guidance on what the built-in `Dataset_Type` terms mean, how multiple types compose, and worked imaging-domain examples, see `references/type-naming-strategy.md`. For the generic naming and design principles that apply to all four DerivaML vocabularies, see `/deriva:entity-naming` and `/deriva:manage-vocabulary` *(deriva-skills)*.

## Phase 3: Create

**Default: use the script-based workflow** for any dataset creation that adds more than a handful of members. This ensures code provenance — every execution record links to a committed git hash. The MCP-tool path is only for trivial cases (creating an empty dataset, adding 2-3 members manually).

Choose the script path based on whether a source dataset already exists:

| Situation | Path | Where to read |
|-----------|------|---------------|
| **No source dataset** — first dataset from raw table data (bootstrap) | Standalone script via `catalog-operations-workflow` patterns | `references/workflow.md` → "Bootstrap dataset (no source dataset)" |
| **Source dataset exists** — filtering, subsetting, or selecting from existing | Subset template via `scripts/generate_subset_template.py` | `references/curated-subsets.md` |
| **Trivial case** — empty dataset or 2-3 known RIDs | MCP-tool path | `references/workflow.md` → "MCP-tool-only path (trivial cases)" |

### Description guidance

Every dataset needs a description that explains its composition, purpose, and key characteristics. **Good:** "500 CIFAR-10 images (50 per class), balanced across all 10 categories, for rapid iteration during development". **Bad:** "Training data" or "My dataset" or empty. For split datasets, note the split strategy and rationale.

For description templates and quality guidelines, see `/deriva-ml:generate-descriptions` *(auto-loaded)*. It carries the Dataset, Workflow, Execution, Feature, Asset, Experiment, and multirun templates.

### Always render splits explicitly in the catalog

Create explicit split datasets (Training, Validation, Testing) and store them as children of the source dataset in the catalog. Don't compute splits on the fly each time you run an experiment — different random seeds produce different splits, breaking reproducibility, and there's no record of which records went into which split. The `references/workflow.md` "Why render splits explicitly" section walks through the pattern and the failure modes.

## Phase 4: Version

Datasets carry a **two-state PEP 440 version** per [ADR-0003](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0003-dataset-dev-versioning-model.md) (deriva-ml 1.34+):

- **Released** versions like `0.4.0` — frozen snapshots, citable, reproducible. Snapshot-pinned in cite URLs.
- **Dev** versions like `0.4.0.post1.dev3` — mutable working state between releases. The PEP 440 dev-release suffix marks "drift after the last release"; dev rows have no snapshot, so cite URLs resolve to the live catalog state.

### Rules

1. **Always use explicit released versions in experiment configs.** `DatasetSpecConfig(rid="28EA", version="0.4.0")` — never a dev label, never "current". Dev labels are mutable; consuming a dev label as if it were a snapshot would silently break reproducibility.
2. **Mutations land on dev, not release.** `deriva_ml_add_dataset_members`, `deriva_ml_delete_dataset_members`, and the dataset-type mutation tools flip the dataset to a dev version (creating `.dev1` if none exists, advancing `.devN` if a dev row is already present). The returned `new_version` is a dev label.
3. **Release is the only operation that produces a released version.** Call `deriva_ml_release(hostname, catalog_id, dataset_rid, bump=...)` to promote a dev period to a release. The `bump` argument selects which release segment to advance (`major` / `minor` / `patch`). Errors if the dataset has no dev row to promote.
4. **Execution-output assets do NOT flip the dataset.** Model weights, prediction CSVs, training logs, plots — these are linked to the producing execution, not to the dataset's members. Future consumers reach them through the execution RID, not through a new dataset version. The dev-flip rule applies only to mutations of dataset *contents* (members + features attached to members).
5. **Always provide a description.** For mutation tools, the `description` is recorded on the dev row and **replaced** on each subsequent mutation (not appended). For `deriva_ml_release`, the `description` becomes the release notes — replaces the dev row's accumulated description, not appended.
6. **Update configs immediately after a release, commit before running.** The git hash in the execution record must match the config state.

### PEP 440 version segments

| Component | When | Examples |
|-----------|------|----------|
| **Major** | Breaking/schema changes | Columns added/removed, restructured tables |
| **Minor** | New data or features | Members added, new annotations, split created |
| **Patch** | Bug fixes, corrections | Fixed mislabeled records, metadata typos |

### Typical lifecycle

```
0.1.0 (release)               <- create_dataset
  ↓ add_dataset_members
0.1.0.post1.dev1 (dev)
  ↓ add_dataset_members
0.1.0.post1.dev2 (dev)
  ↓ release(bump="minor", description="...")
0.2.0 (release)               <- citable, reproducible
```

### Drift detection (deriva-ml Python API)

The Python API exposes three methods for inspecting catalog drift since the last release:

- `dataset.is_dirty()` — fast bool predicate.
- `dataset.release_diff()` — per-table change counts.
- `dataset.compare_versions(v_a, v_b)` — per-table change counts between two versions.

These don't appear on the MCP tool surface; reach for them from notebook code or scripts.

### Pre-experiment checklist

- [ ] Version is a released label (no `.devN` suffix)
- [ ] Version explicitly specified in config (not omitted, not "current")
- [ ] Config updated with correct version
- [ ] Config committed to git

For the full versioning rules, common mistakes, and version history API, see `references/concepts.md` under "Dataset Versioning."

## Phase 5: Use

Once a dataset is created and versioned, there are several ways to consume it.

- **Browse in Chaise** — `cite(hostname, catalog_id, rid="1-ABC4")` for a permanent snapshot URL; add `current=true` for the live URL.
- **Reference in experiment configs** — `DatasetSpecConfig(rid="28EA", version="0.4.0")` in a Hydra-zen config. Use `deriva_ml_get_dataset_spec` to generate the correct string. See `/deriva-ml:configure-experiment` and `/deriva-ml:write-hydra-config` for how dataset configs integrate.
- **Explore and browse contents (no browser)** — 7-step MCP workflow from overview → members → schema shape → actual data → features → hierarchy → provenance. See `references/workflow.md` → "Explore and browse dataset contents".
- **Download as BDBag** — `deriva_ml_bag_info(...)` for size/manifest preview; Python API `dataset.download_dataset_bag(rid, version)` to actually download. For slow downloads, increase timeout or `exclude_tables=[...]`. See `references/bags.md` for FK-traversal mechanics, materialization, caching.
- **Restructure for ML frameworks** — after downloading, `bag.restructure_assets(output_dir, asset_table, group_by=[...])` organizes files for PyTorch ImageFolder or similar. See `/deriva-ml:ml-data-engineering` for the full restructuring patterns.

## Reference Resources

- `scripts/subset_filters.py` — Filter registry with built-in filters. Copy to user's `src/scripts/` on first use.
- `scripts/generate_subset_template.py` — Template for generated dataset scripts. Fill in placeholders per use case.
- `references/concepts.md` — Full background: what datasets are, types, element types, versioning, navigation, consumption, bag downloads
- `references/workflow.md` — Bootstrap procedure, MCP-tool-only path, explicit-splits pattern, 7-step explore/browse depth, every step-by-step example
- `references/curated-subsets.md` — Phase 3b workflow: filter types, scaffolding, the 8-step subset workflow, `cache_features()` pattern
- `references/bags.md` — BDBag contents, FK traversal, materialization, caching, timeouts
- `references/type-naming-strategy.md` — DerivaML-specific built-in `Dataset_Type` dimensions, composing multiple types, imaging-domain examples
- `rag_search("...", doc_type="catalog-data")` — Discover datasets by description, type, or purpose
- `deriva_ml_list_datasets(hostname, catalog_id)` — Full structured list of all datasets
- `deriva_ml_list_dataset_element_types(hostname, catalog_id)` — Tables registered as element types (can contribute dataset members)
- `deriva://catalog/{h}/{c}/ml/vocabularies/deriva-ml` — All deriva-ml vocabularies (Dataset_Type, Workflow_Type, Asset_Type, Execution_Status, plus any user-added ones)
- `deriva://catalog/{h}/{c}/ml/vocabularies/deriva-ml/Dataset_Type` — Drill into Dataset_Type terms (use other vocab names similarly)
- `deriva://docs/datasets` — Full user guide to datasets in DerivaML

## Related Skills

- **`/deriva-ml:ml-data-engineering`** — Restructuring assets for PyTorch/TensorFlow, building training DataFrames, DatasetBag API, value selectors
- **`/deriva-ml:debug-bag-contents`** — Diagnosing missing data, FK traversal issues, and export problems in dataset bags
- **`/deriva-ml:create-feature`** — Creating features and adding labels/annotations to records in datasets
- **`/deriva-ml:configure-experiment`** — Setting up Hydra-zen configs that reference datasets
- **`/deriva-ml:execution-lifecycle`** — Running experiments that consume datasets with provenance tracking
- **`/deriva-ml:catalog-operations-workflow`** — Writing Python scripts for batch dataset operations with code provenance
- **`/deriva-ml:setup-ml-catalog`** — If you don't have a populated catalog yet: creating one from scratch (with a phased loader) or by cloning a slice from a source catalog. The handoff into this skill
