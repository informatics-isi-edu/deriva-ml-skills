# Dataset Bags (BDBags) — DerivaML reference

> **Stateless model:** the new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

> **Generic BDBag mechanics live in `/deriva:download-bag`** *(deriva-skills)* — what a bag *is* (BagIt + fetch.txt + manifests), the two export paths (`DerivaExport`, `DerivaDownload` / `deriva-download-cli`), authoring an export spec by hand, the `bdbag` CLI (validate, resolve-fetch, materialize, archive), three-tier caching, the typed exception hierarchy, and the export-annotation route. **This reference covers only what's DerivaML-specific** — how `Dataset` entities wrap the generic mechanics with version pinning, member-driven spec generation, and the `DatasetBag` SQLite-backed API.

## Table of Contents

- [What a Dataset Bag Contains](#what-a-dataset-bag-contains)
- [How Bag Contents Are Determined](#how-bag-contents-are-determined)
- [Versioning and Reproducibility](#versioning-and-reproducibility)
- [Materialization](#materialization)
- [Caching](#caching)
- [Downloading a Bag](#downloading-a-bag)
- [Previewing Before Download](#previewing-before-download)
- [Validating Bag Contents](#validating-bag-contents)
- [When Downloads Are Slow or Timing Out](#when-downloads-are-slow-or-timing-out)
- [Working with Bag Contents](#working-with-bag-contents)
- [Restructuring Assets for ML](#restructuring-assets-for-ml)
- [Hydra-Zen Configuration](#hydra-zen-configuration)

---

## What a Dataset Bag Contains

A dataset bag is a BDBag (see `/deriva:download-bag` for the format) whose contents are driven by a DerivaML `Dataset` entity at a specific version. `dataset.download_dataset_bag(version)` generates the export spec automatically from the dataset's members + element types + element-type-reachable FK paths; you don't author the spec by hand.

The downloaded bag is backed by a **SQLite database** — all queries against a `DatasetBag` use SQL under the hood. The `DatasetBag` class mirrors the live `Dataset` API, so code can work uniformly with both live catalog data and downloaded snapshots.

### Dataset-specific contents

On top of the generic BDBag shape (`bag-info.txt`, `manifest-md5.txt`, `data/records/...`, `data/assets/...`, `schema.json` — see `/deriva:download-bag`), a dataset bag carries:

1. **Member records** — All records from registered element types that belong to the dataset (e.g., Image, Subject rows), stored as CSV files per table and loaded into the bag's SQLite database.
2. **Related records** — Data from tables reachable via foreign key paths from member records (see [How Bag Contents Are Determined](#how-bag-contents-are-determined)).
3. **Nested datasets** — Child datasets are included recursively with all their members. Navigate with `bag.list_dataset_children()`.
4. **Feature values** — All feature annotations for dataset members (e.g., Image_Classification labels). Access with `bag.fetch_table_features()`.
5. **Vocabulary terms** — Controlled vocabulary terms referenced by included records, exported separately.
6. **Asset files** — Binary files (images, model weights, etc.) referenced by member records, fetched when `materialize=True`.

## How Bag Contents Are Determined

A bag contains two categories of data: **directly included members** and **FK-reachable rows**. Understanding this distinction is essential for predicting what a bag will contain and diagnosing missing data.

### 1. Directly included members

These are the records you explicitly added to the dataset with `deriva_ml_add_dataset_members`. They come from tables registered as **dataset element types** (via `deriva_ml_add_dataset_element_type`). Only element-type tables that have members in this dataset serve as export starting points — unregistered tables or registered tables with no members are not starting points.

### 2. FK-reachable rows (related records)

From each directly included member, the export follows foreign key relationships to pull in related data. This is how a dataset with only Subject members can also include Images, feature values, and vocabulary terms — they are reachable via FK paths from the Subject records.

**Traversal rules:**

- **Both FK directions are followed.** Outgoing FKs (this table references another) and incoming FKs (another table references this one). For example, from a Subject record, the export follows both the Subject→Species FK (outgoing) and the Image→Subject FK (incoming).
- **Vocabulary tables are natural terminators.** Controlled vocabulary terms are collected and exported separately — they don't generate further FK traversal.
- **Feature tables are automatically included.** Feature annotation tables (e.g., `Image_Classification`) for reachable element types are added to the export.
- **Element type boundaries.** A registered element type that has *no members* in this dataset acts as a traversal boundary — the export won't follow FK paths through it. This prevents expensive joins that would return empty results.

### Multi-path inclusion (union semantics)

The same table can be reachable via multiple FK paths. For example, if your schema has both Subject→Image and Encounter→Image relationships, and the dataset contains both Subject and Encounter members, then Images are reachable through two different paths. The bag contains the **union** of all rows reached by any path — an Image included via either path will appear in the bag.

This means you may see more rows for a table than you'd expect from any single FK relationship. The `deriva_ml_bag_info` tool approximates this by taking the maximum count across paths — the true count may be larger when paths produce non-overlapping rows.

### Example

A dataset with `Subject` members where the schema has Subject → Image FK:
- **Directly included:** Subject records (these are the dataset members — the starting points)
- **FK-reachable:** Image records that reference those Subjects (inbound FK traversal from Image→Subject)
- **FK-reachable:** Image_Classification records for those Images (feature table, auto-included)
- **FK-reachable:** Vocabulary terms (e.g., Diagnosis, Species) referenced by any included record (collected separately)

If `Image` is also a registered element type but has no members in this dataset, it acts as a boundary and Image records would *not* be traversed through.

## Versioning and Reproducibility

Each bag is tied to a **catalog snapshot** — the exact catalog state at the time the dataset version was created. This means:

- The same dataset RID + **released** version always produces the same data
- Changes made to the catalog after the version was created (new features, updated records, new members) are **not** included in existing released versions
- To capture recent changes, mutate the dataset (which lands on a dev version per ADR-0003), then call `deriva_ml_release` to promote the dev period to a new release; download that new released version

> **Common mistake:** A bag does NOT contain everything in the catalog — it contains only what was reachable from the dataset's members at the time the released version was created. If you add new members, upload new feature values, or modify records *after* a release, those changes are invisible to that release. The dataset will flip to a dev version (`<last_release>.post1.devN`) on each mutation; call `deriva_ml_release` to mint a new released version that captures the current state, then download that. This is the most common source of "my data is missing from the bag" errors.

> **Dev versions and downloads:** `download_dataset_bag` does not yet accept a dev label (the dev row has no snapshot to pin to). If your code mutates a dataset and then tries to download `current_version` without releasing, you'll hit `ValidationError`. Tracked at [deriva-ml#89](https://github.com/informatics-isi-edu/deriva-ml/issues/89); workaround is to call `deriva_ml_release` between the mutation and the download.

## Materialization

The `materialize=True` default fetches all referenced asset files into the bag (self-contained); `materialize=False` keeps the bag manifest-only and defers asset fetching. See `/deriva:download-bag` "Materialization" for the full mechanics (including `bdbag --resolve-fetch` to materialize selectively after the fact). DerivaML-specific note: `bag.validate()` uses `materialize=False` under the hood, so validating a bag's contents against the live catalog is cheap even for large bags.

## Caching

The generic three-tier cache (local / MINID / generation) is described in `/deriva:download-bag` "Caching". DerivaML extends the cache key to **`{dataset_rid}_{checksum}`** so that two different datasets with coincidentally-identical spec hashes don't collide. The `{rid}@{version}` cache hit is what makes `dataset.download_dataset_bag(version="1.0.0")` deterministic — the same (rid, version) pair always lands in the same cache slot.

The cache location can be configured via the `cache_dir` argument when creating a DerivaML instance. Read the `deriva://storage/cache` resource to see cached bags, and use Python API `ml.clear_cache()` to remove all cached data.

## Downloading a Bag

### Python API

```python
bag = dataset.download_dataset_bag(version="1.0.0")

# Within an execution:
bag = exe.download_dataset_bag(DatasetSpec(rid="2-XXXX", version="1.0.0"))

# With options:
bag = dataset.download_dataset_bag(
    version="1.0.0",
    materialize=False,             # metadata only, no asset files
    exclude_tables={"Institution"},  # prune FK branches
    timeout=(10, 1800),            # 30 min read timeout
)
```

### MINID support

For sharing bags via persistent identifiers, pass `use_minid=True` to upload the bag to S3 and create a MINID. Requires `s3_bucket` configured on the catalog:

```python
bag = dataset.download_dataset_bag(version="1.0.0", use_minid=True)
```

## Previewing Before Download

Two ways to preview bag contents without downloading:

### deriva_ml_bag_info (tool)

Call `deriva_ml_bag_info` with `hostname`, `catalog_id`, `dataset_rid`, and `version`. Returns row counts, asset file sizes per table, and a manifest preview. Covers both size estimation and manifest inspection. Use this to:
- Verify the bag includes the expected tables
- Decide whether to increase the timeout or use `exclude_tables`
- Estimate disk space needed

Supports the same `exclude_tables` parameter as Python API `dataset.download_dataset_bag(version)`, so you can preview the effect of pruning FK branches before committing to a download:

```
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="2-XXXX", version="1.0.0", exclude_tables=["Institution"])
```

### bag-preview resource

Read `deriva://catalog/{h}/{c}/ml/dataset/{rid}/bag-preview` to see projected FK paths and tables without running any size queries.

## Validating Bag Contents

Call Python API bag inspection with `dataset_rid` (and optionally `version`) to cross-validate a downloaded bag against the live catalog. Returns a per-table comparison:

- **Expected RIDs** — records the catalog says should be in the bag (based on members + FK traversal)
- **Bag RIDs** — records actually present in the downloaded bag
- **Missing RIDs** — in catalog but not in bag (indicates traversal or export issue)
- **Extra RIDs** — in bag but not expected (usually harmless — e.g., from broader FK paths)
- **PASS/FAIL status** per table

Use this to verify bag integrity before using it for ML workflows, or to diagnose missing data. See the `debug-bag-contents` skill for a complete diagnostic workflow.

## When Downloads Are Slow or Timing Out

Deep FK chains (e.g., Image → Sample → Subject → Study → Institution) can produce expensive server-side joins. Three solutions, in order of preference:

### 1. Increase the download timeout

The default read timeout is 610 seconds (~10 min). For large datasets, call Python API `dataset.download_dataset_bag(version)` with `timeout`: `[10, 1800]`. The first value is the connect timeout (rarely needs changing), the second is the read timeout (30 min in this example).

### 2. Exclude tables from the FK graph

Prune tables whose data you don't need by calling Python API `dataset.download_dataset_bag(version)` with `exclude_tables` (e.g., `["Study", "Institution"]`). This prevents traversal into those tables entirely.

### 3. Add intermediate records as direct members

Register intermediate tables as element types and add their records as dataset members. This replaces deep FK joins with simpler association lookups.

## Working with Bag Contents

Once downloaded, the bag is a `DatasetBag` object with a rich API that mirrors the live `Dataset` class.

### Browsing data

```python
# List all tables in the bag
bag.list_tables()  # ["Image", "Subject", "Species", ...]

# Access tables as DataFrames or dicts
images_df = bag.get_table_as_dataframe("Image")
subjects = list(bag.get_table_as_dict("Subject"))

# List members grouped by table
members = bag.list_dataset_members()  # {"Image": [...], "Subject": [...]}
members = bag.list_dataset_members(recurse=True)  # includes nested datasets

# Check version
bag.current_version  # DatasetVersion("1.0.0")
bag.dataset_types    # ["Training"]
bag.description      # "500 CIFAR-10 images..."
bag.execution_rid    # "3-XYZ" or None
```

### Features and annotations

```python
# Discover features on a table
features = bag.find_features("Image")  # [Feature(name="Diagnosis", ...)]

# Fetch feature values (same selector API as live Dataset)
feature_df = bag.fetch_table_features(
    table="Image",
    feature_name="Diagnosis",
    selector="newest",           # or: workflow="classify", execution="3-XYZ"
)

# List all feature values for a specific record
values = bag.list_feature_values(target="2-ABCD", feature="Diagnosis")
```

### Denormalization

```python
# Flatten to a wide table (DataFrame) — joins across FK paths
df = bag.denormalize_as_dataframe(include_tables=["Image", "Subject"])

# Same as dict (memory-efficient streaming)
rows = bag.denormalize_as_dict(include_tables=["Image", "Subject"])

# Multi-hop FK chain — tables don't need to be dataset members
df = bag.denormalize_as_dataframe(include_tables=["Image", "Observation", "Subject"])
```

Denormalize follows FK chains automatically, including through intermediate tables. Tables in `include_tables` don't need to be dataset members — they just need to be FK-reachable from a member table. If multiple FK paths exist between two tables (ambiguous), you'll get a `DerivaMLException` asking you to include intermediate tables to disambiguate. See the `ml-data-engineering` skill's `references/denormalize-guide.md` for details.

### Navigating dataset hierarchy

```python
# Both directions of nested relationships in a single call
relations = bag.list_dataset_children()              # direct parents AND children
relations = bag.list_dataset_children(recurse=True)  # full ancestor + descendant tree

# Element types registered for this dataset
element_types = bag.list_dataset_element_types()

# Executions associated with this dataset
execution_rids = bag.list_executions()

# Version history
history = bag.dataset_history()
```

## Restructuring Assets for ML

The Python API `bag.restructure_assets()` method organizes downloaded asset files into directory hierarchies for ML frameworks (e.g., PyTorch ImageFolder).

### Basic usage

```python
bag.restructure_assets(
    output_dir="./ml_data",
    asset_table="Image",        # auto-detected if only one asset table
    targets=["Diagnosis"],      # create subdirs by label
)
# Result: ./ml_data/training/normal/img001.png
#         ./ml_data/training/pneumonia/img002.png
```

### `targets` options

The `targets` parameter takes either a list (default selector per feature) or a dict mapping each feature name to its own selector. Items can be:
- **Column names** — direct columns on the asset table (e.g., `"Species"`)
- **Feature names** — features defined on the asset table or FK-reachable tables (e.g., `"Diagnosis"`)

For multi-column features where you want the directory name to come from one specific column, use `target_transform`:

```python
bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Classification"],
    target_transform=lambda rec: rec.Label,
)
```

### Handling multi-valued features

When an asset has multiple feature values (annotations from different executions), use the dict form of `targets` to attach a per-feature selector:

```python
from deriva_ml.feature import FeatureRecord

# Built-in selectors:
bag.restructure_assets(
    output_dir="./ml_data",
    targets={"Diagnosis": FeatureRecord.select_majority_vote("Diagnosis_Type")},
)

# Other built-ins: FeatureRecord.select_newest, .select_first, .select_latest

# Custom selector:
def select_highest_confidence(records):
    return max(records, key=lambda r: getattr(r, "Confidence", 0))

bag.restructure_assets(
    output_dir="./ml_data",
    targets={"Diagnosis": select_highest_confidence},
)
```

### File transformation on placement

Use `file_transformer` to convert file formats during restructuring:

```python
def oct_to_png(src, dest):
    img = load_oct_dcm(str(src))
    out = dest.with_suffix(".png")
    PILImage.fromarray((img * 255).astype(np.uint8)).save(out)
    return out

bag.restructure_assets(
    output_dir="./ml_data",
    targets=["Diagnosis"],
    file_transformer=oct_to_png,
)
```

### Additional options

- **`use_symlinks=True`** (default) — symlink to original files to save disk space. Set `False` to copy.
- **`type_to_dir_map`** — customize directory names: `{"Training": "train", "Testing": "test"}`
- **`enforce_vocabulary=True`** (default) — require features used in `targets` to have vocabulary terms. Set `False` to allow any feature type.
- **`missing`** — behavior when an asset has no feature value for one of its targets: `"unknown"` (default; place in an `Unknown` subdirectory), `"skip"` (omit from output), `"error"` (raise on first miss).
- **Datasets without types** are treated as Testing (common for prediction/inference).

## Hydra-Zen Configuration

Both `timeout` and `exclude_tables` are available on `DatasetSpecConfig`:

```python
from deriva_ml.dataset.aux_classes import DatasetSpecConfig

DatasetSpecConfig(rid="28EA", version="0.4.0", timeout=[10, 1800])
DatasetSpecConfig(rid="28EA", version="0.4.0", exclude_tables=["Study", "Institution"])
```

## Reference Resources

| Resource / Tool | Purpose |
|-----------------|---------|
| Python API `dataset.download_dataset_bag(version)` | Download bag (supports `exclude_tables`, `timeout`, `materialize`) |
| `deriva_ml_bag_info` | Preview row counts, asset sizes per table, and manifest |
| Python API bag inspection | Cross-validate bag contents against live catalog |
| `deriva_ml_denormalize_dataset` | Schema shape + size estimates (no dataset needed), or flatten dataset tables with `dataset_rid` + `limit` |
| `deriva://catalog/{h}/{c}/ml/dataset/{rid}/bag-preview` | Preview FK paths and tables before downloading |
| `deriva_ml_list_dataset_element_types` | Tables registered as element types (catalog-wide or per-dataset) |
| `deriva://catalog/{h}/{c}/ml/vocabularies/deriva-ml` | Browse the deriva-ml vocabularies (Dataset_Type, Workflow_Type, Asset_Type, Execution_Status) |
| `deriva://storage/cache` | View cached bags |
