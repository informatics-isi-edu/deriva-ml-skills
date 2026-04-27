# Dataset Concepts

Background on datasets in DerivaML. For the step-by-step guide to creating and managing datasets, see `workflow.md`.

## Table of Contents

- [What is a Dataset?](#what-is-a-dataset)
- [Discovering Existing Datasets](#discovering-existing-datasets)
- [Dataset Types](#dataset-types)
- [Dataset Element Types](#dataset-element-types)
- [Dataset Structure: Standalone, Nested, and Splits](#dataset-structure-standalone-nested-and-splits)
- [Splitting Datasets](#splitting-datasets)
- [Dataset Versioning](#dataset-versioning)
- [Identifying a Dataset: RID + Version](#identifying-a-dataset-rid--version)
- [Exploring and Navigating Datasets](#exploring-and-navigating-datasets)
- [Using Datasets](#using-datasets)
- [Downloading Datasets as Bags](#downloading-datasets-as-bags)
- [Deleting Datasets](#deleting-datasets)
- [Operations Summary](#operations-summary)

---

## What is a Dataset?

A dataset is a versioned collection of records (members) from one or more catalog tables. Datasets organize data for ML workflows — training sets, evaluation sets, curated subsets — with full provenance tracking.

Each dataset has:
- **An RID** — unique identifier, like any other catalog record
- **Members** — specific records included in the dataset, referenced by RID
- **Element types** — which tables can contribute members
- **Types** — labels describing the dataset's purpose (Training, Testing, etc.)
- **A version** — monotonically increasing, tied to a catalog snapshot for reproducibility
- **A description** — what the dataset contains and why it exists
- **Provenance** — which execution created it, which executions have used it

Datasets can be heterogeneous: a single dataset can contain records from multiple tables (e.g., both Image and Subject records). DerivaML manages the relationships between these records and makes them accessible from all FK paths.

## Discovering Existing Datasets

Before creating a new dataset, check whether an existing one already serves your purpose. Duplicate datasets fragment data and confuse downstream consumers.

**MCP resources and tools:**
```
# Search for datasets by description, type, or purpose (preferred for discovery)
rag_search("your purpose here", doc_type="catalog-data")

# Full structured list of all datasets (when you need complete output)
Read resource: deriva://catalog/datasets

# Get details about a specific dataset
Read resource: deriva://dataset/{rid}

# Query datasets with filters (when you need specific column filters)
preview_table(table_name="Dataset", filters={"Description": "..."})
```

**Python API:**
```python
# Search datasets
all_datasets = ml.find_datasets()
for ds in all_datasets:
    print(f"{ds.dataset_rid}: {ds.description} (v{ds.current_version})")

# Look up a specific dataset by RID
dataset = ml.lookup_dataset("1-ABC4")
```

**Before creating, ask:**
- Does a dataset with this data already exist? Check descriptions and member counts.
- Can an existing dataset be extended with `add_dataset_members`?
- Can an existing dataset be split differently with `split_dataset`?
- Is the needed data a subset of an existing "Complete" dataset?

## Dataset Types

Dataset types are labels from the `Dataset_Type` controlled vocabulary. They describe the dataset along independent dimensions and are used for organizing, filtering, and discovery. A dataset can have multiple types simultaneously.

### Standard types

These types are available by default in every DerivaML catalog:

| Type | Purpose |
|------|---------|
| Training | Data for model training |
| Testing | Data for model evaluation |
| Validation | Data for hyperparameter tuning |
| Complete | Full dataset before splitting |
| Split | Parent container created by `split_dataset` |
| Labeled | Data with ground truth feature annotations |
| Unlabeled | Data without feature annotations |

### Types are orthogonal tags

Types describe independent dimensions. A dataset gets one or more tags from each relevant dimension. The key principle is that types from different dimensions compose freely — they are not alternatives to each other but describe different aspects of the dataset.

**Example compositions:**

| Dataset | Types | Meaning |
|---------|-------|---------|
| Master collection | `Complete`, `Labeled` | All records, all annotated |
| Training partition | `Training`, `Labeled` | Training split with ground truth |
| Unlabeled prediction set | `Testing` | Inference data, no labels |
| Quick dev subset | `Training`, `Labeled` | Small curated subset for iteration |

The substitution test helps identify whether two types belong on the same dimension: can you swap one for the other? `Training` swaps for `Testing` (same dimension: split role). `Training` does *not* swap for `Labeled` (different dimensions: role vs annotation status). If two types can both apply to the same dataset and aren't alternatives, they describe different dimensions.

### Creating custom types

Custom types can be created with `create_dataset_type_term` (MCP) or `ml.add_term(MLVocab.dataset_type, ...)` (Python). Before creating, check existing types — the term you need may already exist under a different name. Use `rag_search("dataset types", doc_type="catalog-schema")` to find types by meaning, or read `deriva://catalog/dataset-types` for the full list.

For detailed guidance on naming conventions, facet design, and anti-patterns, see `type-naming-strategy.md`.

### How `split_dataset` assigns types

`split_dataset` automatically assigns types to the datasets it creates:

- **Parent dataset** gets type `Split`
- **Training partition** gets `Training` + any additional `training_types`
- **Testing partition** gets `Testing` + any additional `testing_types`
- **Validation partition** gets `Validation` + any additional `validation_types` (if three-way split)

To mark partitions as having ground truth labels, pass `training_types=["Labeled"]`, etc. This makes splits easy to discover and distinguish from unlabeled ones.

## Dataset Element Types

Before adding records from a table to any dataset, that table must be registered as a **dataset element type**. This is a catalog-level operation — once registered, records from that table can be added to any dataset in the catalog.

Registration creates the association table (`Dataset_{TableName}`) that links datasets to records in that table. Without this association table, the catalog has no way to track which records belong to which datasets.

### Why element types matter for planning

Understanding which element types are available is an early planning step — it determines what kind of data can go into your dataset. Check what's registered before deciding what to include:

```
# MCP
Read resource: deriva://catalog/dataset-element-types
```

```python
# Python API
element_types = ml.list_dataset_element_types()
for table in element_types:
    print(table.name)
```

### Registering element types

```
# MCP
add_dataset_element_type(table_name="Image")
```

```python
# Python API
ml.add_dataset_element_type("Image")
```

**Key points:**
- Registration is idempotent — calling it again for an already-registered table is harmless
- Common tables to register: `Subject`, `Image` (or other asset tables), `Observation`, and any custom domain tables whose records should be dataset members
- Element types also determine the starting points for FK traversal during bag export (see [Downloading Datasets as Bags](#downloading-datasets-as-bags))

### Element types and bag exports

During bag export, only tables registered as element types that have members in the dataset serve as starting points for FK traversal. Unregistered tables are traversed normally if reached via FK paths, but cannot contribute starting points. This means:

- A table must be an element type *and* have members for its records to be traversal roots
- A registered element type with *no members* in a dataset acts as a traversal boundary — the export won't follow FK paths through it
- This prevents expensive joins that would return empty results

See `bags.md` for the full FK traversal algorithm.

## Dataset Structure: Standalone, Nested, and Splits

Before creating a dataset, decide its structure. The right choice depends on how the dataset relates to other data in the catalog.

### Decision guide

| Situation | Structure | How |
|-----------|-----------|-----|
| Building a new collection from scratch | Standalone dataset | `create_dataset` |
| Need train/test/val partitions from existing data | Split children | `split_dataset` from a parent |
| Curating a focused subset for a specific experiment | New standalone dataset | `create_dataset` + `add_dataset_members` with selected RIDs |
| Grouping related datasets together | Manual nesting | `create_dataset` + `add_dataset_child` |
| Creating a versioned snapshot for reproducibility | Any structure | Create, populate, then pin version in config |

### Nested datasets

Datasets can contain other datasets as children, forming hierarchies. The most common use is train/test/validation splits:

```
Complete Dataset (type: Complete, Labeled)
└── Split (type: Split — created by split_dataset)
    ├── Training (type: Training, Labeled — 70%)
    ├── Validation (type: Validation, Labeled — 10%)
    └── Testing (type: Testing, Labeled — 20%)
```

Child datasets are independent — they have their own RIDs, versions, and types. The parent-child relationship is purely organizational. Child datasets automatically inherit their parent's element types.

`split_dataset` creates nested datasets automatically. You can also nest manually:

```
# MCP
add_dataset_child(parent_rid="1-PAR", child_rid="1-CHD")
```

```python
# Python API
parent_dataset.add_dataset_members(
    members=[child1.dataset_rid, child2.dataset_rid]
)
```

## Splitting Datasets

`split_dataset` partitions a dataset into training, testing, and optionally validation subsets. It follows scikit-learn conventions (`test_size`, `train_size`, `val_size`, `shuffle`, `seed`) and creates a proper dataset hierarchy with full provenance tracking.

### Two-way split (default)

```
Split (parent, type: "Split")
├── Training (type: "Training")
└── Testing (type: "Testing")
```

### Three-way split (when `val_size` is provided)

```
Split (parent, type: "Split")
├── Training (type: "Training")
├── Validation (type: "Validation")
└── Testing (type: "Testing")
```

### Splitting strategies

- **Random** (default): Shuffles members and splits at the boundary. Fast for any size.
- **Stratified**: Maintains class distribution across partitions. Requires `stratify_by_column` and `include_tables`.
- **Custom**: Provide a `selection_fn` for advanced logic (balanced sampling, filtered subsets).

### Key parameters

- `dry_run=true` — preview the split plan without modifying the catalog
- `seed` — random seed for reproducibility (default: 42)
- `*_types=["Labeled"]` — mark partitions as having ground truth labels
- `stratify_by_column` — denormalized column name format: `{TableName}_{ColumnName}`
- `stratify_missing` — how to handle nulls in the stratify column: `"error"` (default), `"drop"`, or `"include"`

For the full parameter reference, MCP tool examples, and Python API, see `workflow.md`.

## Dataset Versioning

Every dataset has a version number using semantic versioning (`major.minor.patch`):

| Component | When to increment | Examples |
|-----------|-------------------|----------|
| **Major** (X.0.0) | Breaking changes, schema modifications | Table columns added/removed, restructured tables |
| **Minor** (0.X.0) | New data, new features, non-breaking additions | Members added, new feature annotations, split created |
| **Patch** (0.0.X) | Bug fixes, metadata corrections | Fixed mislabeled records, corrected metadata, typo fixes |

DerivaML assigns version `0.1.0` when a dataset is created. The tools `add_dataset_members` and `split_dataset` auto-increment the minor version. For other changes, call `increment_dataset_version` manually.

### Versions are snapshots

Each version is tied to a catalog snapshot timestamp. When you download a specific version, you get the exact data that existed when that version was created — not the current state. This is the foundation of reproducibility: the same dataset RID + version always produces the same data.

**If you've modified data since the last version** (added features, updated records, corrected labels), those changes are NOT included in existing versions. Call `increment_dataset_version` to create a new version that captures the current state.

### When to increment

Any change that affects a dataset's contents requires a version increment before the changes become visible in downloads:

- Adding new features or feature values to records in the dataset
- Fixing or correcting labels
- Adding new images, assets, or records to the catalog
- Modifying asset metadata
- Adding or removing dataset members (auto-incremented by the tools)
- Changing vocabulary terms used by features

### Version descriptions

Always provide a description when incrementing. Good descriptions explain what changed, why, and the impact:

- "Added severity grading feature (mild/moderate/severe) to all 12,450 images. Required for new stratified training pipeline"
- "Fixed 47 mislabeled pneumonia images identified in audit review. Retraining recommended for any model trained on v1.1.0"
- "Added 2,000 new COVID-19 images from March 2026 collection. Increases COVID class from 3,200 to 5,200 images"

Bad descriptions: "Updated", "New version", "Changes", or empty.

### Dataset history

Every version increment is recorded in the dataset's history — a chronological log of all versions with their snapshot timestamps, descriptions, and the execution that created them.

```python
# Python API
history = dataset.dataset_history()
for entry in history:
    print(f"Version {entry.dataset_version}: {entry.description} (snapshot: {entry.snapshot})")
```

Each `DatasetHistory` entry contains:
- `dataset_version` — the version number (e.g., `0.3.0`)
- `snapshot` — catalog snapshot timestamp (ties this version to an exact catalog state)
- `description` — why this version was created
- `execution_rid` — which execution created it (provenance)
- `minid` — permanent identifier URL, if registered

### Versioning rules for experiments

1. **Always use explicit versions for real experiments.** Never use "current" or omit the version in production configs. The only acceptable use of "current" is for debugging and dry runs.
2. **Increment after catalog changes.** If you modify anything that affects dataset contents, increment before running experiments.
3. **Update configs immediately after incrementing.** The config file should always reference the version you intend to use.
4. **Commit configs before running.** The git commit hash in the execution record should match the config state.

### Pre-experiment checklist

Before running any experiment:
- [ ] Dataset version is explicitly specified (not "current")
- [ ] Config file is updated with the correct version
- [ ] Config changes are committed to git

After any catalog modification:
- [ ] Version has been incremented with a descriptive message
- [ ] All affected config files are updated to the new version
- [ ] Config changes are committed to git

### Common versioning mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Running without explicit version | Results not reproducible | Always specify version in config |
| Expecting catalog changes in old versions | Old versions are frozen snapshots | Increment version to capture changes |
| Empty or vague version descriptions | Cannot understand version history | Write specific, informative descriptions |
| Not updating config after increment | Experiments still use old version | Update config immediately after incrementing |
| Not committing config before running | Git hash doesn't match config state | Always commit, then run |

## Identifying a Dataset: RID + Version

A dataset is uniquely identified by its **RID** (Resource Identifier), like any catalog record. But because datasets evolve over time, the combination of **RID + version** is what identifies a specific, reproducible snapshot of the data.

This pair is captured in a **DatasetSpec** — the standard way to reference a dataset in code:

```python
from deriva_ml.dataset.aux_classes import DatasetSpec, DatasetSpecConfig

# Python API
DatasetSpec(rid="28EA", version="0.4.0")

# Hydra-zen configuration (version is required)
DatasetSpecConfig(rid="28EA", version="0.4.0")
```

Use the `get_dataset_spec` MCP tool to generate the correct `DatasetSpecConfig` string for a dataset, including its current version. The `deriva://dataset/{rid}` resource also shows the current version.

### Binding to a specific version

```python
# Get current version
current = dataset.current_version  # e.g., "1.2.0"

# Bind a dataset object to a specific version for version-aware operations
versioned_dataset = dataset.set_version("1.0.0")
members = versioned_dataset.resource deriva://dataset/{rid}/members ()  # members at v1.0.0
```

## Exploring and Navigating Datasets

Once a dataset exists, you need to understand what's in it — its structure, contents, hierarchy, and provenance. This section covers the read-side operations.

### Understanding a dataset's structure

Start by checking its metadata — types, element types, version, and description:

```
# MCP
Read resource: deriva://dataset/{rid}
```

```python
# Python API
dataset = ml.lookup_dataset("1-ABC4")
print(f"Description: {dataset.description}")
print(f"Version: {dataset.current_version}")
print(f"Types: {dataset.dataset_types}")
```

### Listing members

Members are the records that belong to a dataset. Results are returned as a JSON object mapping table names to arrays of `{RID}` objects — this grouping by table tells you which element types have data and how many records of each type:

```json
{
  "Image": [{"RID": "2-IMG1"}, {"RID": "2-IMG2"}, ...],
  "Subject": [{"RID": "2-SUB1"}, {"RID": "2-SUB2"}, ...]
}
```

This is the starting point for browsing — the table names tell you which element types to explore with `preview_denormalized_dataset`.

**MCP tools:**
```
# All members of the current version
resource deriva://dataset/{rid}/members (dataset_rid="1-ABC4")

# Members at a specific version
resource deriva://dataset/{rid}/members (dataset_rid="1-ABC4", version="1.0.0")

# Members including all nested child datasets
resource deriva://dataset/{rid}/members (dataset_rid="1-ABC4", recurse=true)

# Limit results (useful for large datasets)
resource deriva://dataset/{rid}/members (dataset_rid="1-ABC4", limit=100)
```

**Python API:**
```python
# Current version — returns dict[str, list[dict]]
members = dataset.resource deriva://dataset/{rid}/members ()
for table_name, rids in members.items():
    print(f"{table_name}: {len(rids)} members")

# Specific version
members_v1 = dataset.resource deriva://dataset/{rid}/members (version="1.0.0")
```

Note that resource `deriva://dataset/{rid}/members` returns only RIDs, not actual record data. To see the data values (demographics, labels, metadata), use `preview_denormalized_dataset` with the table names discovered here (no dataset RID needed for schema exploration; add `dataset_rid` and `limit` for actual data) — see [Using Datasets](#using-datasets).

### Navigating hierarchies

Datasets form parent-child hierarchies. The most common is the split hierarchy created by `split_dataset`, but you can nest manually too.

**Listing children:**
```
# Direct children only
# Resource: deriva://dataset/{rid} (dataset_rid="1-ABC4")

# All descendants (children, grandchildren, etc.)
# Resource: deriva://dataset/{rid} (dataset_rid="1-ABC4", recurse=true)

# Children at a specific version
# Resource: deriva://dataset/{rid} (dataset_rid="1-ABC4", version="1.0.0")
```

**Listing parents:**
```
# Direct parents
list_dataset_parents(dataset_rid="1-CHD")

# All ancestors
list_dataset_parents(dataset_rid="1-CHD", recurse=true)
```

**When to use recursion:**
- Use `recurse=false` (default) when you only need the immediate level — e.g., listing the Training/Testing/Validation children of a Split dataset
- Use `recurse=true` when you need the full tree — e.g., listing all members across a Complete → Split → Training/Testing hierarchy
- Recursive member listing (resource `deriva://dataset/{rid}/members` with `recurse=true`) aggregates members from the dataset and all its descendants

### Checking element types

Element types determine which tables can contribute members. Check what's available before planning a dataset, or verify what an existing dataset can contain:

```
# MCP — catalog-wide registered element types
Read resource: deriva://catalog/dataset-element-types
```

```python
# Python API — element types for a specific dataset
element_types = dataset.list_dataset_element_types()
for table in element_types:
    print(table.name)
```

### Provenance

Track which executions created or used a dataset:

```
# MCP
# Resource: deriva://dataset/{rid} (dataset_rid="1-ABC4")
```

This returns all executions that used this dataset as an input — useful for understanding a dataset's lineage and which experiments depend on it.

## Using Datasets

Once a dataset is created and versioned, there are several ways to consume it.

### Browse in Chaise (web UI)

Every dataset has a page in the Chaise web interface where you can browse its metadata, types, members, children, and version history. Use `cite()` to generate a shareable URL:

```
# MCP — permanent URL with snapshot timestamp
cite(rid="1-ABC4")

# URL to current state (no snapshot)
cite(rid="1-ABC4", current=true)
```

```python
# Python API
url = ml.cite("1-ABC4")          # permanent snapshot URL
url = ml.cite("1-ABC4", current=True)  # live URL
```

### Reference in experiment configurations

The standard way to use a dataset in an ML experiment is through a Hydra-zen configuration file. The `DatasetSpecConfig` captures the RID and pinned version:

```python
from deriva_ml.dataset.aux_classes import DatasetSpecConfig

# In a config module (e.g., src/configs/datasets.py)
training_data = DatasetSpecConfig(rid="28EA", version="0.4.0")

# With download options
training_data = DatasetSpecConfig(
    rid="28EA",
    version="0.4.0",
    timeout=[10, 1800],          # increase read timeout for large datasets
    exclude_tables=["Study"],     # prune FK graph if needed
)
```

Use the `get_dataset_spec` MCP tool to generate the correct config string including the current version. See the `write-hydra-config` and `configure-experiment` skills for how dataset configs integrate into experiment configurations.

### Query via MCP tools

For interactive exploration without downloading:

```
# Explore schema shape (no dataset needed)
preview_denormalized_dataset(include_tables=["Image", "Subject"])

# Denormalize with dataset-scoped info + row data
preview_denormalized_dataset(include_tables=["Image", "Subject"], dataset_rid="1-ABC4", limit=50)

# Query individual tables
preview_table(table_name="Image", filters={"Subject": "2-SUB1"})
```

### Download as a BDBag

For production training pipelines and reproducible experiments, download the dataset as a self-contained archive:

```
# MCP
# Python API: dataset.download_dataset_bag(dataset_rid="1-ABC4", version="1.0.0")

# Within an execution (records provenance)
download_execution_dataset(dataset_rid="1-ABC4", version="1.0.0")
```

```python
# Python API
bag = dataset.download_dataset_bag(version="1.0.0")

# Within an execution
bag = exe.download_dataset_bag(DatasetSpec(rid="1-ABC4", version="1.0.0"))
```

See [Downloading Datasets as Bags](#downloading-datasets-as-bags) for details.

### Use in Python with the Dataset object

The `Dataset` class provides direct access to dataset operations:

```python
dataset = ml.lookup_dataset("1-ABC4")

# Access metadata
print(dataset.description)
print(dataset.current_version)
print(dataset.dataset_types)

# Work with a specific version
v1 = dataset.set_version("1.0.0")
members = v1.resource deriva://dataset/{rid}/members ()

# Download and work with the bag
bag = dataset.download_dataset_bag(version="1.0.0")
images_df = bag.get_table_as_dataframe("Image")
subjects_df = bag.get_table_as_dataframe("Subject")
```

## Downloading Datasets as Bags

Datasets can be downloaded as **BDBag** archives — self-describing, checksummed packages containing all member records, related data, asset files, feature values, and vocabulary terms. The same dataset RID + version always produces the same bag.

### What a bag contains

1. **Member records** — CSV files per table for all records that belong to the dataset
2. **Related records** — data from tables reachable via FK paths from member records
3. **Nested datasets** — child datasets included recursively with all their members
4. **Feature values** — all feature annotations for dataset members
5. **Vocabulary terms** — controlled vocabulary terms referenced by included records
6. **Asset files** — binary files (images, model weights) when `materialize=True`
7. **Checksums** — cryptographic checksums for integrity verification

### Working with downloaded bags

```python
bag = dataset.download_dataset_bag(version="1.0.0", materialize=True)

# Access tables as DataFrames
images_df = bag.get_table_as_dataframe("Image")
subjects_df = bag.get_table_as_dataframe("Subject")

# Access the local filesystem path
print(f"Bag path: {bag.path}")
```

### Restructuring assets for ML frameworks

After downloading, organize files into the directory structure expected by ML frameworks (e.g., PyTorch ImageFolder):

```python
bag.restructure_assets(
    asset_table="Image",
    output_dir=Path("./ml_data"),
    group_by=["Diagnosis"],
)
```

Creates:
```
ml_data/
  Training/
    Normal/image1.jpg
    Abnormal/image2.jpg
  Testing/
    Normal/image3.jpg
```

By default, symlinks are used to save disk space. Set `use_symlinks=False` to copy files.

### Previewing before download

```
# MCP
estimate_bag_size(dataset_rid="1-ABC4", version="1.0.0")
```

Returns row counts and asset sizes per table. Use this to verify expected tables, estimate disk space, and decide whether to adjust timeout or use `exclude_tables`.

For full details on FK traversal, materialization, caching, timeout handling, and Hydra-zen configuration options, see `bags.md`.

For diagnosing missing data in bag exports, see the `debug-bag-contents` skill.

## Deleting Datasets

Datasets can be soft-deleted (marked as deleted but data preserved in the catalog):

```
# MCP — delete a single dataset
delete_dataset(dataset_rid="1-ABC4")

# Delete dataset and all nested children
delete_dataset(dataset_rid="1-ABC4", recurse=true)
```

```python
# Python API
ml.delete_dataset(dataset)
ml.delete_dataset(dataset, recurse=True)
```

Deletion removes the dataset container and member associations, not the member records themselves. The underlying Image, Subject, etc. records remain in the catalog.

## Operations Summary

### Creation and modification

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Create dataset | `create_dataset` | `exe.create_dataset()` | Within an execution for provenance |
| Add types | `add_dataset_type` | `dataset.add_dataset_type()` | Additive labels |
| Remove types | `remove_dataset_type` | `dataset.remove_dataset_type()` | |
| Create custom type | `create_dataset_type_term` | `ml.add_term(MLVocab.dataset_type, ...)` | Check existing types first |
| Register element type | `add_dataset_element_type` | `ml.add_dataset_element_type()` | Catalog-level, idempotent |
| Add members | `add_dataset_members` | `dataset.add_dataset_members()` | Auto-increments version |
| Remove members | `delete_dataset_members` | `dataset.delete_dataset_members()` | |
| Split | `split_dataset` | `split_dataset(ml, rid, ...)` | Auto-increments version |
| Nest datasets | `add_dataset_child` | `parent.add_dataset_members()` | Manual hierarchy |
| Increment version | `increment_dataset_version` | `dataset.increment_dataset_version()` | Always provide description |
| Set description | `set_dataset_description` | — | |
| Delete | `delete_dataset` | `ml.delete_dataset()` | Soft delete, optional recurse |

### Navigation and discovery

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Find datasets | `rag_search("...", doc_type="catalog-data")` or Resource: `deriva://catalog/datasets` | `ml.find_datasets()` | RAG for discovery; resource for full list |
| Lookup by RID | `get_record("Dataset", rid)` | `ml.lookup_dataset(rid)` | Get specific dataset |
| List members | resource `deriva://dataset/{rid}/members` | `dataset.resource deriva://dataset/{rid}/members ()` | Grouped by table; supports `version`, `recurse`, `limit` |
| List children | resource `deriva://dataset/{rid}` | `dataset.list_dataset_children()` | Supports `recurse`, `version` |
| List parents | `list_dataset_parents` | `dataset.list_dataset_parents()` | Supports `recurse`, `version` |
| Check element types | Resource: `dataset-element-types` | `ml.list_dataset_element_types()` | Catalog-wide |
| List executions | resource `deriva://dataset/{rid}` | — | Provenance: which runs used this dataset |
| Validate RIDs | `validate_rids` | — | Check RIDs exist before adding |
| Estimate bag size | `estimate_bag_size` | `dataset.estimate_bag_size()` | Preview before download |
| Get version spec | `get_dataset_spec` | — | Generate `DatasetSpecConfig` string |
| Cite | `cite` | `ml.cite(rid)` | Permanent shareable URL |

### Download and export

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Download bag | Python API `dataset.download_dataset_bag(version)` | `dataset.download_dataset_bag()` | Standalone download |
| Download in execution | Python API `exe.download_dataset_bag()` | `exe.download_dataset_bag()` | Records provenance |
| Restructure assets | Python API `bag.restructure_assets()` | `bag.restructure_assets()` | ML-ready directory layout |
| Validate bag | Python API bag inspection | — | Cross-check bag vs catalog |
| Schema shape + size | `preview_denormalized_dataset(include_tables=[...])` | `ml.denormalize_info()` / `dataset.denormalize_info()` | No dataset needed for schema-only |
| Denormalize with data | `preview_denormalized_dataset(..., dataset_rid=..., limit=N)` | `dataset.denormalize_as_dataframe()` | Flat DataFrame for analysis |
