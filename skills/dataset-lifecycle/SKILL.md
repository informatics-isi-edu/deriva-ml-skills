---
name: dataset-lifecycle
description: "Use for ALL DerivaML dataset operations — creating, populating, splitting (train/test/validation, stratified), versioning, browsing (deriva_ml_denormalize_dataset), navigating parent/child hierarchies, downloading BDBags (timeouts, exclude_tables, bag_info), restructuring assets for ML frameworks, and wiring resulting RIDs into src/configs/datasets.py. After any operation that produces a RID + version downstream code may consume, proactively offer to add it to src/configs/datasets.py — this skill owns that offer. Triggers include 'create / split / stratify / browse / download / denormalize a dataset', 'dataset version', 'training data setup', 'curated subset', 'filter by class / by feature', 'BDBag', 'DatasetSpecConfig', 'wire dataset into config'. Do NOT use for: creating features/labels (use create-feature), creating tables (use create-table), running experiments (use execution-lifecycle), uploading assets (use work-with-assets), or managing vocabularies (use manage-vocabulary)."
---

# Dataset Lifecycle

This skill covers the full lifecycle of a DerivaML dataset: assessing whether one is needed, planning its structure and types, creating and populating it, versioning for reproducibility, and consuming it in experiments.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly.

**Check project context first.** Before running any commands, look for catalog references in the project: `tacit-knowledge.md` records which catalog/hostname previous operations used; `src/configs/deriva.py` carries hydra-zen connection configs; `CLAUDE.md` may specify the working catalog. Use the catalog the project is actively working with, NOT the original source catalog (e.g., the clone on dev.facebase.org, not the source on www.facebase.org). If you don't know the catalog ID, read `deriva://registry/{hostname}` to see available catalogs and aliases.

## Phase 1: Assess

Before creating a dataset, determine whether an existing one can be reused, extended, or split. The find-before-you-create discipline is carried by `/deriva:semantic-awareness` *(deriva-skills, auto-fires)* — its synonym/abbreviation/spelling-variant search expansion applies to ML entities (Datasets) as well as generic catalog entities. The same skill covers the EAV-vs-wide-table dual extreme, which is worth knowing when designing the *element-type* tables a dataset will draw members from.

1. **Search existing datasets.** `rag_search("your purpose", doc_type="catalog-data")` finds datasets by description, type, or purpose. For a bounded snapshot of all datasets, read `deriva://catalog/{h}/{c}/ml/datasets` (one round trip, includes summary + type + current version + `cite_url` + members per dataset); for paginated browsing or filtered queries beyond the snapshot cap, use `deriva_ml_list_datasets(hostname, catalog_id)` instead. Use `get_table_sample_data(...)` to understand how much data is available.
2. **Check available element types.** Call `deriva_ml_list_dataset_element_types(hostname, catalog_id)` to see which tables can contribute members. If the table you need isn't registered, call `deriva_ml_add_dataset_element_type(hostname, catalog_id, element_table=...)`.
3. **Decide: reuse, extend, or create.**

| Situation | Action |
|-----------|--------|
| Existing dataset covers your need | Reuse it — reference its RID + version in config |
| Existing dataset needs more members | `deriva_ml_add_dataset_members` to extend it |
| Need a different split of existing data | Write a script that calls the Python API `split_dataset(ml, source_rid, exe, ...)` — see `references/workflow.md` § "Splitting Datasets" |
| Need a focused subset for an experiment | Create a new dataset (curated subset — see below) |
| Building from scratch | Bootstrap a new dataset from raw table data |

## Phase 2: Plan

### Choose the dataset structure

| Pattern | When to use | How |
|---------|-------------|-----|
| Standalone | Building a new collection from scratch | `deriva_ml_create_dataset` |
| Split children | Need train/test/val partitions | Script that opens an execution and calls `split_dataset(ml, source_rid, exe, ...)`. See `references/workflow.md` § "Splitting Datasets" |
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
| **No source dataset** — first dataset from raw table data (bootstrap) | Standalone script via `generate-scripts` patterns | `references/workflow.md` → "Bootstrap dataset (no source dataset)" |
| **Source dataset exists** — filtering, subsetting, or selecting from existing | Subset template via `scripts/generate_subset_template.py` | `references/curated-subsets.md` |
| **Source dataset exists** — partition into train/val/test | Script (Base Template from `generate-scripts` + `split_dataset` Python API) | `references/workflow.md` → "Splitting Datasets" |
| **Trivial case** — empty dataset or 2-3 known RIDs | MCP-tool path | `references/workflow.md` → "MCP-tool-only path (trivial cases)" |

### Description guidance

Every dataset needs a description that explains its composition, purpose, and key characteristics. **Good:** "500 CIFAR-10 images (50 per class), balanced across all 10 categories, for rapid iteration during development". **Bad:** "Training data" or "My dataset" or empty. For split datasets, note the split strategy and rationale.

For description templates and quality guidelines, see `/deriva-ml:generate-descriptions` *(auto-loaded)*. It carries the Dataset, Workflow, Execution, Feature, Asset, Experiment, and multirun templates.

### Always render splits explicitly in the catalog

Create explicit split datasets (Training, Validation, Testing) and store them as children of the source dataset in the catalog. Don't compute splits on the fly each time you run an experiment — different random seeds produce different splits, breaking reproducibility, and there's no record of which records went into which split. The `references/workflow.md` "Why render splits explicitly" section walks through the pattern and the failure modes.

### Proactively offer to update `src/configs/datasets.py`

Whenever this skill produces a RID + version the user may want to consume downstream — after creating a dataset, after running a split (one or more children), after promoting a dev row to a release, after a curated-subset generation — **offer to write the result into `src/configs/datasets.py`** as a `DatasetSpecConfig` entry. Don't wait for the user to ask.

Sample wording:

> *"The new split produced Training RID `2-TRN1` @ `0.1.0`, Testing RID `2-TST1` @ `0.1.0`. Want me to add them to `src/configs/datasets.py`?"*

If they say yes, follow `/deriva-ml:write-hydra-config` → **"Wiring fresh RIDs into config files"** — that section carries the canonical entry-line generator (`deriva_ml_get_dataset_spec(...)`), the file-structure conventions, and the commit message template (`chore(configs): add <name> dataset RIDs from <date> run`).

**This skill owns the offer** (because this skill produced the RID); `write-hydra-config` owns the shape.

## Phase 4: Version

Datasets carry a **two-state PEP 440 version** per [ADR-0003](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0003-dataset-dev-versioning-model.md):

- **Released** versions like `0.4.0` — frozen snapshots, citable, reproducible. Snapshot-pinned in cite URLs.
- **Dev** versions like `0.4.0.post1.dev3` — mutable working state between releases. The PEP 440 dev-release suffix marks "drift after the last release"; dev rows have no snapshot, so cite URLs resolve to the live catalog state.

### Rules

1. **Always use explicit released versions in experiment configs.** `DatasetSpecConfig(rid="28EA", version="0.4.0")` — never a dev label, never "current". Dev labels are mutable; consuming a dev label as if it were a snapshot would silently break reproducibility.
2. **Mutations land on dev, not release.** `deriva_ml_add_dataset_members`, `deriva_ml_delete_dataset_members`, and the dataset-type mutation tools flip the dataset to a dev version (creating `.dev1` if none exists, advancing `.devN` if a dev row is already present). The returned `new_version` is a dev label.
3. **Release is the only operation that produces a released version.** Call `deriva_ml_release(hostname, catalog_id, dataset_rid, bump=...)` to promote a dev period to a release. The `bump` argument selects which release segment to advance (`major` / `minor` / `patch`). Errors if the dataset has no dev row to promote.
4. **Execution-output assets do NOT flip the dataset.** Model weights, prediction CSVs, training logs, plots — these are linked to the producing execution, not to the dataset's members. Future consumers reach them through the execution RID, not through a new dataset version. The dev-flip rule applies only to mutations of dataset *contents* (members + features attached to members).
5. **Always provide a description.** For mutation tools, the `description` is recorded on the dev row and **replaced** on each subsequent mutation (not appended). For `deriva_ml_release`, the `description` becomes the release notes — replaces the dev row's accumulated description, not appended.
6. **Adding *feature values* to existing dataset members does NOT auto-flip the dataset, but probably should.** The auto-flip detection in rule 2 fires on member-set changes (add/remove members) and dataset-type changes. It does NOT fire when a feature value gets written for an existing member RID — feature drift is invisible to that detection. But a dataset whose members gained new feature values is materially different from before: a consumer who downloads its bag tomorrow gets different data than they got yesterday, even though the member RIDs are the same. Reproducibility breaks silently. **If your work added feature values to members of a Dataset that has a released version, call `dataset.mark_dev(description)` from the Python API to flip the dataset to a dev label, then `deriva_ml_release(...)` when the drift period is done.** See `/deriva-ml:create-feature` "Integration with Datasets" for the symmetric statement from the feature-author side.
7. **Update configs immediately after a release, commit before running.** Specifically `src/configs/datasets.py` — find the `DatasetSpecConfig` entry whose `rid` matches the dataset you just released and bump its `version` to the new release label, then `git commit src/configs/datasets.py -m "chore(configs): bump <name> to <new_version>"`. Proactively offer to do this for the user as soon as `deriva_ml_release` returns the new version (see "Proactively offer to update `src/configs/datasets.py`" in Phase 3). The git hash in the execution record must match the config state — running an experiment whose config still pins the prior release means the execution row says "run X" but the dataset bytes loaded are version X+1's.

### PEP 440 version segments

| Component | When | Examples |
|-----------|------|----------|
| **Major** | Breaking/schema changes | Columns added/removed, restructured tables |
| **Minor** | New data or features | Members added, new annotations, split created |
| **Patch** | Bug fixes, corrections | Fixed mislabeled records, metadata typos |

> **Schema change underneath an existing dataset?** A major bump signals that consumer code must change too — column renamed, table split, FK retargeted. The migration itself (snapshot, backfill, drop the old shape) belongs in `/deriva:evolve-schema` *(deriva-skills)*; this skill governs what to do *to the dataset* afterward (cut a major release that pins the post-migration schema so downstream experiments don't silently break across the boundary).

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
- [ ] `src/configs/datasets.py` `DatasetSpecConfig(...)` entries reflect the new RID + released version (use `deriva_ml_get_dataset_spec` to generate the line)
- [ ] `src/configs/datasets.py` committed to git on the branch the run will use

For the full versioning rules, common mistakes, and version history API, see `references/concepts.md` under "Dataset Versioning."

## Phase 5: Use

Once a dataset is created and versioned, there are several ways to consume it.

- **Browse in Chaise** — `cite(hostname, catalog_id, rid="1-ABC4")` for a permanent snapshot URL; add `current=true` for the live URL.
- **Reference in experiment configs** — `DatasetSpecConfig(rid="28EA", version="0.4.0")` in a Hydra-zen config. Use `deriva_ml_get_dataset_spec` to generate the correct string. If the user has just created, split, or released a dataset in this session, proactively offer to add the new RID + version to `src/configs/datasets.py` (see Phase 3 → "Proactively offer to update `src/configs/datasets.py`"). For how dataset configs integrate into the broader experiment configuration surface, see `/deriva-ml:configure-experiment` and `/deriva-ml:write-hydra-config`.
- **Explore and browse contents (no browser)** — 7-step MCP workflow from overview → members → schema shape → actual data → features → hierarchy → provenance. See `references/workflow.md` → "Explore and browse dataset contents".
- **Download as BDBag** — see "Download workflow" below for the worked recipe; `references/bags.md` for DerivaML-specific behavior (version pinning, cache key, `DatasetBag` API). For the generic BDBag format and the underlying export mechanics (what a bag *is*, the `bdbag` CLI, materialization, `DerivaDownload` / `DerivaExport` Python classes), `/deriva:download-bag` *(deriva-skills)*.
- **Restructure for ML frameworks** — after downloading, `bag.restructure_assets(output_dir, asset_table, targets=[...])` organizes files for PyTorch ImageFolder or similar. See `/deriva-ml:ml-data-engineering` for the full restructuring patterns.

### Download workflow

The dataset-aware download path wraps the generic BDBag export (see `/deriva:download-bag` *(deriva-skills)* for the underlying mechanics) with three things that matter to ML reproducibility: **version pinning, member-driven spec generation, and a `{rid}@{version}` cache key**. The result is that the same `(rid, version)` pair always produces the same bytes, indefinitely.

The full recipe — preview, validate version, download, handle errors — in four steps:

```python
# Step 1: Preview before downloading. Cheap; no bytes transferred.
#
# For the dataset's CURRENT version (released or dev), the lead path is the
# bag-preview resource — one round trip, no parameters:
#     deriva://catalog/data.example.org/1/ml/dataset/2-XXXX/bag-preview
#
# For a PINNED version or to EXCLUDE specific tables from the preview,
# use the deriva_ml_bag_info tool:
deriva_ml_bag_info(
    hostname="data.example.org", catalog_id="1",
    dataset_rid="2-XXXX", version="1.0.0",
)
# Both return per-table row counts + per-table asset sizes + manifest preview.
# Use these to: confirm the right tables are included, estimate disk and time,
# decide whether to use exclude_tables or increase timeout.

# Step 2: Validate version. Reject dev versions up front.
ds = ml.find_dataset("2-XXXX")          # or ds = dataset for an in-scope object
v = ds.find_version("1.0.0")             # raises if version doesn't exist
assert not v.is_dev, (
    f"Version {v} is a dev label — bags cannot pin to a dev label "
    f"(no snapshot to pin). Release first with deriva_ml_release()."
)

# Step 3: Download. Cached the first time; cache hits after.
bag = ds.download_dataset_bag(version="1.0.0")
# In an execution: exe.download_dataset_bag(DatasetSpec(rid="2-XXXX", version="1.0.0"))

# Step 4: Validate (optional, manual; cheap insurance for important runs).
# Diff what the catalog says is in this dataset+version against what
# actually made it into the bag. See /deriva-ml:debug-bag-contents Step 6
# for the recipe; the gist is:
#
# expected = ds.list_dataset_members(version="1.0.0")
# for table_name in bag.list_tables():
#     actual_rids = {r["RID"] for r in bag.get_table_as_dict(table_name)}
#     missing = {m["RID"] for m in expected[table_name]} - actual_rids
#     assert not missing, f"{table_name}: {len(missing)} missing RIDs"
```

**Common patterns:**

| Goal | Override |
|---|---|
| Metadata only — skip asset bytes | `materialize=False` |
| Slow download / deep FK chain | `timeout=[10, 1800]` (30 min read timeout) |
| Prune an expensive FK branch | `exclude_tables=["Institution", "Study"]` |
| Share via persistent identifier | `use_minid=True` (requires `s3_bucket` configured on the catalog) |
| Embed in Hydra-zen experiment config | `DatasetSpecConfig(rid="28EA", version="0.4.0", timeout=[10, 1800], exclude_tables=["Study"])` |

**The dev-version pitfall.** If your code mutates a dataset (added members, new feature values) and then immediately tries `download_dataset_bag(current_version)`, you'll hit `ValidationError` — the dataset will have flipped to a dev label (`x.y.z.post1.devN`) on the mutation, and dev labels have no snapshot to pin to. The fix is to call `deriva_ml_release(...)` between the mutation and the download to mint a new release that captures the post-mutation state, then download that. See "Versioning and Reproducibility" in `references/bags.md` for the full version-state diagram. Tracked at [deriva-ml#89](https://github.com/informatics-isi-edu/deriva-ml/issues/89).

For what to do with the bag after it lands — restructure for PyTorch, build training DataFrames, denormalize across FK paths, handle multi-annotator features — see `/deriva-ml:ml-data-engineering`. For BDBag-format mechanics (manifest, checksums, fetch.txt materialization, `bdbag` CLI), see `/deriva:download-bag` *(deriva-skills)*.

## Reference Resources

- `scripts/subset_filters.py` — Filter registry with built-in filters. Copy to user's `src/scripts/` on first use.
- `scripts/generate_subset_template.py` — Template for generated dataset scripts. Fill in placeholders per use case.
- `references/concepts.md` — Full background: what datasets are, types, element types, versioning, navigation, consumption, bag downloads
- `references/workflow.md` — Bootstrap procedure, MCP-tool-only path, explicit-splits pattern, 7-step explore/browse depth, every step-by-step example
- `references/curated-subsets.md` — Phase 3b workflow: filter types, scaffolding, the 8-step subset workflow, catalog-query path using `feature_values()` for label-based filters
- `references/bags.md` — BDBag contents, FK traversal, materialization, caching, timeouts
- `references/type-naming-strategy.md` — DerivaML-specific built-in `Dataset_Type` dimensions, composing multiple types, imaging-domain examples
- `rag_search("...", doc_type="catalog-data")` — Discover datasets by description, type, or purpose
- `deriva://catalog/{h}/{c}/ml/datasets` — Bounded snapshot of all datasets (one round trip; includes summary, type, current version, `cite_url`, members per dataset). Preferred for "show me what datasets exist."
- `deriva_ml_list_datasets(hostname, catalog_id)` — Paginated list for filtered queries or when the snapshot cap is exceeded.
- `deriva://catalog/{h}/{c}/ml/dataset/{rid}` — One dataset by RID with members and version in a single read (preferred over `deriva_ml_get_dataset` for inspection).
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
- **`/deriva-ml:generate-scripts`** — Writing Python scripts for batch dataset operations with code provenance
- **`/deriva-ml:setup-ml-catalog`** — If you don't have a populated catalog yet: creating one from scratch (with a phased loader) or by cloning a slice from a source catalog. The handoff into this skill.
- **`/deriva:evolve-schema`** *(deriva-skills)* — When a catalog schema change (split / merge / FK move / retype) lands beneath an existing dataset. The schema migration runs there; cutting the dataset's major release to pin the post-migration shape happens here.
