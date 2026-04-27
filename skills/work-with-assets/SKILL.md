---
name: work-with-assets
description: "ALWAYS use this skill when working with file assets in DerivaML — discovering, downloading, uploading, inspecting, or managing images, model weights, CSVs, or any file-based catalog records. Triggers on: 'download asset', 'upload files', 'asset table', 'find images', 'model weights', 'what created this file', 'asset provenance', 'asset types', 'create asset table'."
disable-model-invocation: true
---

# Working with Assets in DerivaML

An asset is a file-based record in a Deriva catalog — it combines a file (stored in Deriva's object store) with catalog metadata like filename, size, MD5 checksum, and description. Assets live in asset tables, which have standard file-tracking columns plus optional custom metadata. Every asset has a unique RID for stable referencing across the system.

For background on asset tables, types, RIDs, object storage, caching, and provenance, see `references/concepts.md`.


## Prerequisite: Connect to a Catalog

All operations in this skill require an active catalog connection. Before anything else:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.


## Critical Rules

1. **Use RIDs to reference assets** — not filenames or URLs. RIDs are immutable and unique.
2. **Upload within an execution** — assets must be registered with Python API `exe.asset_file_path()` and uploaded with Python API `exe.upload_execution_outputs()` inside an active execution for provenance tracking.
3. **Download records provenance automatically** — calling Python API `ml.download_asset(rid)` within an execution links the asset as an "Input" to that execution.
4. **Create the asset table before uploading** — the table must exist before you can register files for upload to it.

## Workflow Summary

### Discovering and inspecting assets

1. **Start with `rag_search`** to discover asset tables and types by concept:
   ```
   rag_search("image assets", doc_type="catalog-schema")
   rag_search("model weights files", doc_type="catalog-schema")
   ```
2. Read `deriva://catalog/asset-tables` or `deriva://catalog/assets` — full structured list of asset tables and counts
3. Read `deriva://table/{table_name}/assets` — browse assets in a table
4. Read `deriva://asset/{asset_rid}` — inspect a specific asset (metadata, types, provenance, Chaise URL)
5. `list_asset_executions` — find which execution created or used an asset
6. Read `deriva://execution/{rid}/metadata` — find auto-generated metadata files for an execution
7. Read `deriva://execution/{rid}/outputs` — find output assets for an execution

### Downloading assets

1. Python API `ml.download_asset(rid)` — download a single asset by RID
2. Python API `dataset.download_dataset_bag(version)` — download a dataset as a BDBag with all asset files (no execution required)
3. Python API `exe.download_dataset_bag()` — same as above but within an active execution (records the dataset as an input for provenance)
4. Python API `bag.restructure_assets()` — organize downloaded assets into ML-ready directory layouts

### Creating asset tables

1. `create_asset_table` — define a new asset table with optional custom columns and FK references

### Uploading assets (within an execution)

1. `create_execution` + `start_execution` — start provenance tracking
2. Python API `exe.asset_file_path()` — register each output file for upload (returns a path to write to)
3. Python API `exe.upload_execution_outputs()` — upload all registered files to the object store and catalog
4. `stop_execution` — finalize

### Managing asset types

1. `add_asset_type` — create a new term in the Asset_Type vocabulary
2. `add_asset_type_to_asset` / `remove_asset_type_from_asset` — tag or untag assets

For the full step-by-step guide with MCP tool parameters and Python API examples, see `references/workflow.md`.

## Reference Resources

- `references/concepts.md` — What assets are, asset tables, RIDs, types, object storage, caching, provenance, execution metadata vs execution assets, notebook output assets
- `references/workflow.md` — Step-by-step MCP and Python API workflows, finding assets by type and execution
- `references/restructure-guide.md` — Restructuring assets for ML: group_by options, value selectors, file transformers, ML framework patterns, upload tuning
- `rag_search("file assets in DerivaML", doc_type="user-guide")` — Search the user guide for file asset documentation
- `deriva://catalog/asset-tables` — List all asset tables
- `deriva://catalog/assets` — Asset tables with record counts
- `deriva://table/{table_name}/assets` — Browse assets in a table
- `deriva://asset/{asset_rid}` — Asset details and provenance
- `deriva://execution/{rid}/metadata` — Auto-generated metadata files for an execution
- `deriva://execution/{rid}/outputs` — Output assets for an execution

## Related Skills

- **`execution-lifecycle`** — Full execution lifecycle including asset upload patterns
- **`ml-data-engineering`** — Downloading and restructuring assets for ML training
- **`dataset-lifecycle`** — Datasets organize assets into versioned collections for reproducibility
