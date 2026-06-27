---
type: Concept
title: Dataset lifecycle operations
description: Deleting datasets and the full operations summary tables (creation/modification, navigation/discovery, download/export).
---

# Dataset lifecycle operations

## Deleting Datasets

Datasets can be soft-deleted (marked as deleted but data preserved in the catalog):

```
# MCP — delete a single dataset
deriva_ml_delete_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")

# Delete dataset and all nested children
deriva_ml_delete_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", recurse=true)
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
| Create dataset | `deriva_ml_create_dataset` | `exe.create_dataset()` | Within an execution for provenance |
| Add types | `deriva_ml_update_dataset(dataset_rid, dataset_types=[...])` | `dataset.add_dataset_type()` | Additive labels |
| Remove types | `deriva_ml_update_dataset(dataset_rid, dataset_types=[...])` | `dataset.remove_dataset_type()` | Set-style: pass the reduced list |
| Create custom type | `add_term(schema="deriva-ml", table="Dataset_Type", ...)` | `ml.add_term(MLVocab.dataset_type, ...)` | Generic add_term |
| Register element type | `deriva_ml_add_dataset_element_type` | `ml.add_dataset_element_type()` | Catalog-level, idempotent |
| Add members | `deriva_ml_add_dataset_members` | `dataset.add_dataset_members()` | Auto-increments version |
| Remove members | `deriva_ml_delete_dataset_members` | `dataset.delete_dataset_members()` | |
| Split | *(script only)* | `split_dataset(ml, source_rid, exe, ...)` | Run from a script that opens an execution. Children auto-tagged with `Split_Partition` + role; source recorded as execution input, not Dataset_Dataset parent |
| Subsample | *(script only)* | `subsample(ml, source_rid, exe, size=, ...)` | Single output; stratified by `stratify_by_column`. Output auto-tagged `Subsample`; source recorded as execution input |
| Nest datasets | `deriva_ml_add_dataset_members(parent, members={"Dataset": [child_rid]})` | `parent.add_dataset_members()` | Children are members of element-type Dataset |
| Release a dev period | `deriva_ml_release_dataset` | `dataset.release(bump, description)` | Promotes dev → released; errors if no dev row |
| Update description | `deriva_ml_update_dataset(rid, description=...)` | — | Single setter for any updatable field |
| Delete | `deriva_ml_delete_dataset` | `ml.delete_dataset()` | Soft delete, optional recurse |

### Navigation and discovery

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Find datasets | `rag_search("...", doc_type="catalog-data")` or `deriva_ml_list_datasets` | `ml.find_datasets()` | RAG for discovery; typed list for full surface |
| Lookup by RID | `deriva_ml_get_dataset(rid)` | `ml.lookup_dataset(rid)` | Get specific dataset |
| List members | `deriva_ml_list_dataset_members` | `dataset.list_dataset_members()` | Grouped by table; supports `version`, `recurse`, `limit` |
| List relations (parents + children) | `deriva_ml_list_dataset_relations` | `dataset.list_dataset_children()` / `dataset.list_dataset_parents()` | MCP tool returns both directions in one call; the Python API has separate child/parent calls. Both support `recurse`, `version` |
| Check element types | `deriva_ml_list_dataset_element_types` | `ml.list_dataset_element_types()` | Per-dataset or catalog-wide |
| List executions | `deriva_ml_get_dataset` (includes provenance) | — | Provenance: which runs used this dataset |
| Validate RIDs | `get_entities(filters={"RID": "..."})` per candidate table; check for empty result | — | Use generic entity fetch |
| Bag info / size estimate | `deriva_ml_bag_info` | `dataset.estimate_bag_size()` | Preview before download |
| Get version spec | `deriva_ml_get_dataset_spec` | — | Generate `DatasetSpecConfig` string |
| Cite | `cite` | `ml.cite(rid)` | Permanent shareable URL |

### Download and export

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Download bag | Python API `dataset.download_dataset_bag(version)` | `dataset.download_dataset_bag()` | Standalone download |
| Download in execution | Python API `exe.download_dataset_bag()` | `exe.download_dataset_bag()` | Records provenance |
| Restructure assets | Python API `bag.restructure_assets()` | `bag.restructure_assets()` | ML-ready directory layout |
| Validate bag | Python API bag inspection | — | Cross-check bag vs catalog |
| Schema shape + size | `deriva_ml_denormalize_dataset(include_tables=[...])` | `dataset.describe_denormalized()` / `bag.describe_denormalized()` | Returns columns, join path, row/asset sizes |
| Denormalize with data | `deriva_ml_denormalize_dataset(..., dataset_rid=..., limit=N)` | `dataset.get_denormalized_as_dataframe()` | Flat DataFrame for analysis |
