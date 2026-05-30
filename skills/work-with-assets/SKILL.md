---
name: work-with-assets
description: "ALWAYS use this skill when working with file assets in DerivaML — discovering, downloading, uploading, inspecting, or managing images, model weights, CSVs, or any file-based catalog records, AND wiring resulting asset RIDs into src/configs/assets.py. After any operation that produces a new asset RID an experiment may consume downstream (creating an asset table, uploading a file inside an execution, registering an asset type that gates a future config), proactively offer to add an AssetSpecConfig entry — this skill owns the offer because this skill produced the RID. Triggers on: 'download asset', 'upload files', 'asset table', 'find images', 'model weights', 'what created this file', 'asset provenance', 'asset types', 'create asset table', 'update assets config', 'update assets.py', 'add asset RID to config', 'wire asset into config'."
disable-model-invocation: true
---

# Working with Assets in DerivaML

An asset is a file-based record in a Deriva catalog — it combines a file (stored in Deriva's object store) with catalog metadata like filename, size, MD5 checksum, and description. Assets live in asset tables, which have standard file-tracking columns plus optional custom metadata. Every asset has a unique RID for stable referencing across the system.

For background on asset tables, types, RIDs, object storage, caching, and provenance, see `references/concepts.md`.


> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.


## Critical Rules

1. **Use RIDs to reference assets** — not filenames or URLs. RIDs are immutable and unique.
2. **Upload within an execution** — assets must be registered with Python API `exe.asset_file_path()` and committed with Python API `exe.commit_output_assets()` inside an active execution for provenance tracking.
3. **Download records provenance automatically** — calling Python API `ml.download_asset(rid)` within an execution links the asset as an "Input" to that execution.
4. **Create the asset table before uploading** — the table must exist before you can register files for upload to it.

## Workflow Summary

### Discovering and inspecting assets

1. **Start with `rag_search`** to discover asset tables and types by concept:
   ```
   rag_search("image assets", doc_type="catalog-schema")
   rag_search("model weights files", doc_type="catalog-schema")
   ```
2. **Browse asset tables in one schema** — read `deriva://catalog/{h}/{c}/deriva-ml/assets/{schema}` for a schema-scoped list of asset tables (e.g., `ml/assets/deriva-ml`, `ml/assets/myproject`). To survey across schemas, list the schemas with `list_schemas` (deriva-mcp-core) and read this resource per schema; there is no single all-schemas asset-table tool.
3. **Snapshot the contents of one asset table** — read `deriva://catalog/{h}/{c}/deriva-ml/assets/{schema}/{asset_table}` for a bounded snapshot of assets in one table (capped at the resource limit; for paginated/filtered access, use the tool below).
4. `deriva_ml_list_assets(hostname, catalog_id, ...)` — paginated, filterable browse across asset tables (use this when the snapshot resource hits its cap or when you need filters).
5. `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` — inspect a specific asset (metadata, types, producer execution).
6. `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` — find auto-generated metadata files and output assets for an execution.

### Downloading assets

1. Python API `ml.download_asset(rid)` — download a single asset by RID
2. Python API `dataset.download_dataset_bag(version)` — download a dataset as a BDBag with all asset files (no execution required)
3. Python API `exe.download_dataset_bag()` — same as above but within an active execution (records the dataset as an input for provenance)
4. Python API `bag.restructure_assets()` — organize downloaded assets into ML-ready directory layouts

### Creating asset tables

1. Use `create_table` (from the deriva plugin) with the standard hatrac column shape and an Asset_Type FK. See `references/concepts.md` for the recipe.

### Uploading assets (within an execution)

Asset upload always goes through a bundled script template — the execution context manager (`with ml.create_execution(config, workflow=workflow) as exe:`) is what binds the upload to a workflow + git commit for provenance. Copy `skills/work-with-assets/scripts/upload_asset.py` to `src/scripts/upload_<thing>.py`, customize the work block, commit, and run via `deriva-ml-run`.

Inside the template, the pattern is:

1. Python API `exe.asset_file_path(asset_name, file_name, asset_types=[...])` — register each output file for upload (returns a path to write to).
2. Write the bytes to that path.
3. Post-`with` block: `exe.commit_output_assets()` — uploads bytes, writes catalog rows, sets descriptions and `Upload_Duration`, transitions the execution `Stopped → Pending_Upload → Uploaded`. Returns an `UploadReport`; for per-asset paths, read `exe.uploaded_assets` after the call.

The context manager handles status transitions on success or exception — there is no separate "commit execution" call.

### Managing asset types

1. **Create a new term in the Asset_Type vocabulary:** `add_term(hostname, catalog_id, schema="deriva-ml", table="Asset_Type", name=..., description=...)`.
2. **Tag / untag an asset with a type:** `update_entities(hostname, catalog_id, schema, table, entities=[{"RID": asset_rid, "Asset_Type": <term>}])` to set the value, or pass `null` to clear it. See `references/workflow.md` for the full recipe.

> **DerivaML auto-tags every execution-crossing asset.** When an asset is uploaded via `exe.commit_output_assets()` it gets the `Output_File` tag added to its `asset_types` list; when consumed via `exe.download_asset()` it gets `Input_File`. **Do not pass these tags yourself** to `exe.asset_file_path(asset_types=[...])` — DerivaML adds them. **Filters that use equality on `asset_types` will silently miss matches** because the directional tag is always present. Use `in` membership: `"Model_Weights" in asset.asset_types`, not `asset.asset_types == ["Model_Weights"]`. Full contract in `references/concepts.md` → "Asset_Type auto-tags (directional)".

For the full step-by-step guide with MCP tool parameters and Python API examples, see `references/workflow.md`.

### Proactively offer to update `src/configs/assets.py`

Whenever this skill produces an asset RID a downstream experiment may consume — after creating a new asset table the agent expects to point an experiment at, after uploading an asset inside an execution, after registering a new role-tagged asset — **offer to write the result into `src/configs/assets.py`** as an `AssetSpecConfig` entry. Don't wait for the user to ask.

This skill's scope is asset *creation* / *registration* — **one RID at a time, intentional.** The parallel offer for bulk output assets (N at once at the end of a run) belongs in `/deriva-ml:execution-lifecycle`; the two are disjoint.

Sample wording:

> *"The new model-weights asset is at RID `3-WTS1`. Want me to add it to `src/configs/assets.py` so the inference experiment can pin it?"*

If they say yes, follow `/deriva-ml:write-hydra-config` → **"Wiring fresh RIDs into config files"** — that section carries the canonical entry-line shape (`AssetSpecConfig`'s field reference, including the `cache=True` rule for large immutable files and `asset_role='Input'|'Output'`), the file-structure conventions, and the commit-message template (`chore(configs): add <name> asset (RID <rid>)`).

**This skill owns the offer** (because this skill produced the RID); `write-hydra-config` owns the shape.

## Reference Resources

- `references/concepts.md` — What assets are, asset tables, RIDs, types, object storage, caching, provenance, execution metadata vs execution assets, notebook output assets, and the manual recipe for creating an asset table.
- `references/workflow.md` — Step-by-step MCP and Python API workflows, finding assets by type and execution.
- `references/restructure-guide.md` — Restructuring assets for ML: `targets` and `target_transform` shapes, per-feature selectors, file transformers, ML framework patterns, upload tuning.
- `rag_search("file assets in DerivaML", doc_type="user-guide")` — Search the user guide for file asset documentation.
- Use `deriva_ml_list_assets(hostname, catalog_id, ...)` and `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` for the typed asset reads.
- `deriva://catalog/{h}/{c}/deriva-ml/assets/{schema}` — schema-scoped list of asset tables.
- `deriva://catalog/{h}/{c}/deriva-ml/assets/{schema}/{asset_table}` — snapshot of assets in one asset table (bounded; complements the paginated `deriva_ml_list_assets` tool).
- `deriva://catalog/{h}/{c}/deriva-ml/asset/{rid}` — one asset by RID.
- `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` returns metadata files and output assets for an execution.

## Related Skills

- **`execution-lifecycle`** — Full execution lifecycle including asset upload patterns
- **`ml-data-engineering`** — Downloading and restructuring assets for ML training
- **`dataset-lifecycle`** — Datasets organize assets into versioned collections for reproducibility
- **`/deriva:create-table`** *(deriva-skills)* — Generic table creation via `create_table`, used to build new asset tables
- **`/deriva:load-data`** *(deriva-skills)* — Row-side loading once the asset table exists; covers both ad-hoc inserts and the production `deriva-upload-cli` path with upload specs (`asset_mappings`)
- **`/deriva:manage-vocabulary`** *(deriva-skills)* — Generic vocabulary CRUD via `add_term`/`delete_term`, used to manage Asset_Type terms
