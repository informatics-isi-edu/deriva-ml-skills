---
type: Concept
title: Discovering, navigating, and using datasets
description: Pre-creation discovery, read-side exploration (members, hierarchies, element types, provenance), and consumption patterns. Bag downloads are in bags.md.
---

# Discovering, navigating, and using datasets

**Contents**

- [Discovering Existing Datasets](#discovering-existing-datasets)
- [Exploring and Navigating Datasets](#exploring-and-navigating-datasets)
  - [Understanding a dataset's structure](#understanding-a-datasets-structure)
  - [Listing members](#listing-members)
  - [Navigating hierarchies](#navigating-hierarchies)
  - [Checking element types](#checking-element-types)
  - [Provenance](#provenance)
- [Using Datasets](#using-datasets)
  - [Browse in Chaise (web UI)](#browse-in-chaise-web-ui)
  - [Reference in experiment configurations](#reference-in-experiment-configurations)
  - [Query via MCP tools](#query-via-mcp-tools)
  - [Download as a BDBag](#download-as-a-bdbag)
  - [Use in Python with the Dataset object](#use-in-python-with-the-dataset-object)

## Discovering Existing Datasets

Before creating a new dataset, check whether an existing one already serves your purpose. Duplicate datasets fragment data and confuse downstream consumers.

**MCP tools and resources:**
```
# Search for datasets by description, type, or purpose (preferred for discovery)
rag_search("your purpose here", doc_type="ml-dataset")

# Full structured list of all datasets — preferred typed form
deriva_ml_list_datasets(hostname="data.example.org", catalog_id="1")

# Equivalent resource URI
Read resource: deriva://catalog/{h}/{c}/deriva-ml/datasets

# Get details about a specific dataset
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")

# Query datasets with filters — for whole-row fetches use get_entities;
# use query_attribute when you need column projection or path syntax (comparison ops, joins).
get_entities(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Dataset", filters={"Description": "..."})
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
- Can an existing dataset be extended with `deriva_ml_add_dataset_members`?
- Can an existing dataset be split differently via a script that calls `split_dataset(ml, source_rid, exe, ...)`?
- Is the needed data a subset of an existing "Complete" dataset?

## Exploring and Navigating Datasets

Once a dataset exists, you need to understand what's in it — its structure, contents, hierarchy, and provenance. This section covers the read-side operations.

### Understanding a dataset's structure

Start by checking its metadata — types, element types, version, and description:

```
# MCP — typed call (preferred)
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")
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

This is the starting point for browsing — the table names tell you which element types to explore with `deriva_ml_denormalize_dataset`.

**MCP tools:**
```
# All members of the current version
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")

# Members at a specific version
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", version="1.0.0")

# Members including all nested child datasets
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", recurse=true)

# Limit results (useful for large datasets)
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", limit=100)
```

**Python API:**
```python
# Current version — returns dict[str, list[dict]]
members = dataset.list_dataset_members()
for table_name, rids in members.items():
    print(f"{table_name}: {len(rids)} members")

# Specific version
members_v1 = dataset.list_dataset_members(version="1.0.0")
```

`deriva_ml_list_dataset_members` returns only RIDs, not actual record data. To see the data values (demographics, labels, metadata), use `deriva_ml_denormalize_dataset` with the table names discovered here (no dataset RID needed for schema exploration; add `dataset_rid` and `limit` for actual data) — see [Using Datasets](#using-datasets).

### Navigating hierarchies

Datasets form parent-child hierarchies. The most common is the split hierarchy created by `split_dataset`, but you can nest manually too.

**Listing children and parents in one call:**
```
# Both directions in a single call
deriva_ml_list_dataset_relations(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")

# Recurse for the full tree
deriva_ml_list_dataset_relations(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", recurse=true)

# At a specific version
deriva_ml_list_dataset_relations(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", version="1.0.0")
```

`deriva_ml_list_dataset_relations` returns both parents and children together; there is no separate parents-only call.

**When to use recursion:**
- Use `recurse=false` (default) when you only need the immediate level — e.g., listing the Training/Testing/Validation children of a Split dataset
- Use `recurse=true` when you need the full tree — e.g., listing all members across a Split → Training/Testing hierarchy (start from the Split; the source dataset it came from is not its parent)
- Recursive member listing (`deriva_ml_list_dataset_members(..., recurse=true)`) aggregates members from the dataset and all its descendants

### Checking element types

Element types determine which tables can contribute members. Check what's available before planning a dataset, or verify what an existing dataset can contain:

```
# MCP — catalog-wide registered element types
deriva_ml_list_dataset_element_types(hostname="data.example.org", catalog_id="1")

# Or per-dataset element types (scoped to one dataset)
deriva_ml_list_dataset_element_types(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")
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
# MCP — `deriva_ml_get_dataset` includes execution provenance
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")
```

This returns all executions that used this dataset as an input — useful for understanding a dataset's lineage and which experiments depend on it.

## Using Datasets

Once a dataset is created and versioned, there are several ways to consume it.

### Browse in Chaise (web UI)

Every dataset has a page in the Chaise web interface where you can browse its metadata, types, members, children, and version history. Use `cite()` to generate a shareable URL:

```
# MCP — permanent URL with snapshot timestamp
cite(hostname="data.example.org", catalog_id="1", rid="1-ABC4")

# URL to current state (no snapshot)
cite(hostname="data.example.org", catalog_id="1", rid="1-ABC4", current=true)
```

```python
# Python API
url = ml.cite("1-ABC4")          # permanent snapshot URL
url = ml.cite("1-ABC4", current=True)  # live URL
```

### Reference in experiment configurations

The standard way to use a dataset in an ML experiment is through a Hydra-zen configuration file. The `DatasetSpecConfig` captures the RID and pinned version:

```python
from deriva_ml.dataset import DatasetSpecConfig

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

Use the `deriva_ml_get_dataset_spec` MCP tool to generate the config string with the dataset's current version. If that is a dev label, release the dataset first and generate it again; configs pin released versions only. See the `write-hydra-config` and `configure-experiment` skills for how dataset configs integrate into experiment configurations.

### Query via MCP tools

For interactive exploration without downloading:

```
# Explore schema shape (no dataset needed)
deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=["Image", "Subject"])

# Denormalize with dataset-scoped info + row data
deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=["Image", "Subject"], dataset_rid="1-ABC4", limit=50)

# Query individual tables (whole rows from one table by FK -> use get_entities)
get_entities(hostname="data.example.org", catalog_id="1", schema="<schema>", table="Image", filters={"Subject": "2-SUB1"})
```

### Download as a BDBag

For training and reproducible experiments, download a released version as a bag. The recipe (preview, pin, download, validate) and every download option are in `bags.md` → "Download recipe".

### Use in Python with the Dataset object

The `Dataset` class provides direct access to dataset operations:

```python
dataset = ml.lookup_dataset("1-ABC4")

# Access metadata
print(dataset.description)
print(dataset.current_version)
print(dataset.dataset_types)

# Work with a specific version (pass the keyword-only version=)
members = dataset.list_dataset_members(version="1.0.0")

# Download and work with the bag
bag = dataset.download_dataset_bag(version="1.0.0")
images_df = bag.get_table_as_dataframe("Image")
subjects_df = bag.get_table_as_dataframe("Subject")
```

What a bag contains, how its contents are chosen, caching, and slow-download fixes: `bags.md`. Turning a bag into training data (DataFrames, `restructure_assets` for ImageFolder): `/deriva-ml:ml-data-engineering`. Missing data in a bag: `/deriva-ml:debug-bag-contents` †.
