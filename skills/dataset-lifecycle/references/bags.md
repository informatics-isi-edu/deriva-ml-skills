# Dataset Bags (BDBags)

## Table of Contents

- [What is a Bag?](#what-is-a-bag)
- [What a Bag Contains](#what-a-bag-contains)
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

## What is a Bag?

A **BDBag** (Big Data Bag) is a self-describing, portable archive of a specific dataset version. It packages everything needed to reproduce a dataset offline: member records, related data, asset files, feature values, and vocabulary terms — all checksummed for integrity.

Bags are the standard way to get data out of a DerivaML catalog for ML training, analysis, or sharing. When you call Python API `dataset.download_dataset_bag(version)`, the result is a bag.

The downloaded bag is backed by a **SQLite database** — all queries against a `DatasetBag` use SQL under the hood. The `DatasetBag` class mirrors the live `Dataset` API, so code can work uniformly with both live catalog data and downloaded snapshots.

## What a Bag Contains

A bag for a specific dataset version includes:

1. **Member records** — All records from registered element types that belong to the dataset (e.g., Image, Subject rows), stored as CSV files per table and loaded into SQLite.
2. **Related records** — Data from tables reachable via foreign key paths from member records (see [How Bag Contents Are Determined](#how-bag-contents-are-determined)).
3. **Nested datasets** — Child datasets are included recursively with all their members. Navigate with `bag.list_dataset_children()`.
4. **Feature values** — All feature annotations for dataset members (e.g., Image_Classification labels). Access with `bag.resource deriva://table/{name}/features ()`.
5. **Vocabulary terms** — Controlled vocabulary terms referenced by included records, exported separately.
6. **Asset files** — Binary files (images, model weights, etc.) referenced by member records, fetched when `materialize=True`.
7. **Checksums** — Every file has a cryptographic checksum for integrity verification.
8. **Schema snapshot** — `schema.json` describing the catalog structure at export time.

## How Bag Contents Are Determined

A bag contains two categories of data: **directly included members** and **FK-reachable rows**. Understanding this distinction is essential for predicting what a bag will contain and diagnosing missing data.

### 1. Directly included members

These are the records you explicitly added to the dataset with `add_dataset_members`. They come from tables registered as **dataset element types** (via `add_dataset_element_type`). Only element-type tables that have members in this dataset serve as export starting points — unregistered tables or registered tables with no members are not starting points.

### 2. FK-reachable rows (related records)

From each directly included member, the export follows foreign key relationships to pull in related data. This is how a dataset with only Subject members can also include Images, feature values, and vocabulary terms — they are reachable via FK paths from the Subject records.

**Traversal rules:**

- **Both FK directions are followed.** Outgoing FKs (this table references another) and incoming FKs (another table references this one). For example, from a Subject record, the export follows both the Subject→Species FK (outgoing) and the Image→Subject FK (incoming).
- **Vocabulary tables are natural terminators.** Controlled vocabulary terms are collected and exported separately — they don't generate further FK traversal.
- **Feature tables are automatically included.** Feature annotation tables (e.g., `Image_Classification`) for reachable element types are added to the export.
- **Element type boundaries.** A registered element type that has *no members* in this dataset acts as a traversal boundary — the export won't follow FK paths through it. This prevents expensive joins that would return empty results.

### Multi-path inclusion (union semantics)

The same table can be reachable via multiple FK paths. For example, if your schema has both Subject→Image and Encounter→Image relationships, and the dataset contains both Subject and Encounter members, then Images are reachable through two different paths. The bag contains the **union** of all rows reached by any path — an Image included via either path will appear in the bag.

This means you may see more rows for a table than you'd expect from any single FK relationship. The `estimate_bag_size` tool approximates this by taking the maximum count across paths — the true count may be larger when paths produce non-overlapping rows.

### Example

A dataset with `Subject` members where the schema has Subject → Image FK:
- **Directly included:** Subject records (these are the dataset members — the starting points)
- **FK-reachable:** Image records that reference those Subjects (inbound FK traversal from Image→Subject)
- **FK-reachable:** Image_Classification records for those Images (feature table, auto-included)
- **FK-reachable:** Vocabulary terms (e.g., Diagnosis, Species) referenced by any included record (collected separately)

If `Image` is also a registered element type but has no members in this dataset, it acts as a boundary and Image records would *not* be traversed through.

## Versioning and Reproducibility

Each bag is tied to a **catalog snapshot** — the exact catalog state at the time the dataset version was created. This means:

- The same dataset RID + version always produces the same data
- Changes made to the catalog after the version was created (new features, updated records, new members) are **not** included in existing versions
- To capture recent changes, call `increment_dataset_version` first, then download the new version

> **Common mistake:** A bag does NOT contain everything in the catalog — it contains only what was reachable from the dataset's members at the time the version was created. If you add new members, upload new feature values, or modify records *after* the version was created, those changes are invisible to that version. You must call `increment_dataset_version` to create a new snapshot that captures the current state, then download that new version. This is the most common source of "my data is missing from the bag" errors.

## Materialization

- **`materialize=True`** (default): The bag fetches all referenced asset files from the object store. Creates a fully self-contained archive.
- **`materialize=False`**: The bag contains only metadata and remote file references. Smaller download, but requires network access to use the assets later.

Use `materialize=False` when you only need the tabular data (record metadata, feature values) and not the actual files. Also useful for validation (Python API bag inspection uses `materialize=False` to check contents quickly).

## Caching

Bags are cached locally by checksum. When you download the same dataset version again, the cached bag is reused without re-downloading. The cache key is `{dataset_rid}_{checksum}`.

The cache location can be configured via the `cache_dir` argument when creating a DerivaML instance. Read the `deriva://storage/cache` resource to see cached bags, and use Python API `ml.clear_cache()` to remove all cached data.

## Downloading a Bag

### MCP tool

Call Python API `dataset.download_dataset_bag(version)` with `dataset_rid` and `version`. Returns JSON with `bag_path`, `bag_tables` inventory, `dataset_types`, and `execution_rid`.

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

### estimate_bag_size (tool)

Call `estimate_bag_size` with `dataset_rid` and `version`. Returns row counts and asset file sizes per table. Use this to:
- Verify the bag includes the expected tables
- Decide whether to increase the timeout or use `exclude_tables`
- Estimate disk space needed

Supports the same `exclude_tables` parameter as Python API `dataset.download_dataset_bag(version)`, so you can preview the effect of pruning FK branches before committing to a download:

```
estimate_bag_size(dataset_rid="2-XXXX", version="1.0.0", exclude_tables=["Institution"])
```

### bag-preview resource

Read `deriva://dataset/{rid}/bag-preview` to see projected FK paths and tables without running any size queries.

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
members = bag.resource deriva://dataset/{rid}/members ()  # {"Image": [...], "Subject": [...]}
members = bag.resource deriva://dataset/{rid}/members (recurse=True)  # includes nested datasets

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
feature_df = bag.resource deriva://table/{name}/features (
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
# Nested child datasets (e.g., Training/Testing splits)
children = bag.list_dataset_children()        # direct children
children = bag.list_dataset_children(recurse=True)  # all descendants

# Parent datasets
parents = bag.list_dataset_parents()

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
    group_by=["Diagnosis"],     # create subdirs by label
)
# Result: ./ml_data/training/normal/img001.png
#         ./ml_data/training/pneumonia/img002.png
```

### group_by options

The `group_by` list can contain:
- **Column names** — direct columns on the asset table (e.g., `"Species"`)
- **Feature names** — features defined on the asset table or FK-reachable tables (e.g., `"Diagnosis"`)
- **Feature.column** — specific column from a multi-column feature (e.g., `"Classification.Label"`)

### Handling multi-valued features

When an asset has multiple feature values (e.g., annotations from different executions), use `value_selector` to choose one:

```python
from deriva_ml.dataset.dataset_bag import select_majority_vote, select_latest, select_first

# Built-in selectors:
bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    value_selector=select_majority_vote,  # most common label, ties broken by newest
)

# Or: select_latest (most recent RCT), select_first (earliest RCT)

# Custom selector:
def select_highest_confidence(records):
    return max(records, key=lambda r: r.raw_record.get("Confidence", 0))

bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    value_selector=select_highest_confidence,
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
    group_by=["Diagnosis"],
    file_transformer=oct_to_png,
)
```

### Additional options

- **`use_symlinks=True`** (default) — symlink to original files to save disk space. Set `False` to copy.
- **`type_to_dir_map`** — customize directory names: `{"Training": "train", "Testing": "test"}`
- **`enforce_vocabulary=True`** (default) — require features used in `group_by` to have vocabulary terms. Set `False` to allow any feature type.
- **Datasets without types** are treated as Testing (common for prediction/inference).
- **Assets without labels** are placed in an `"Unknown"` subdirectory.

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
| `estimate_bag_size` | Preview row counts and asset sizes per table |
| Python API bag inspection | Cross-validate bag contents against live catalog |
| `preview_denormalized_dataset` | Schema shape + size estimates (no dataset needed), or flatten dataset tables with `dataset_rid` + `limit` |
| `deriva://dataset/{rid}/bag-preview` | Preview FK paths and tables before downloading |
| `deriva://catalog/dataset-element-types` | Check registered element types |
| `deriva://storage/cache` | View cached bags |
