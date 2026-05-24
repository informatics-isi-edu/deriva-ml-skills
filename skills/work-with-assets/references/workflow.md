# Asset Workflow Reference

Step-by-step MCP tool and Python API examples for working with assets. For background on asset tables, types, caching, and provenance, see `concepts.md`.

> The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Table of Contents

1. [Discovering Assets](#discovering-assets)
2. [Finding Assets by Type and Execution](#finding-assets-by-type-and-execution)
3. [Inspecting an Asset](#inspecting-an-asset)
4. [Downloading Assets](#downloading-assets)
5. [Creating Asset Tables](#creating-asset-tables)
6. [Registering and Uploading Assets](#registering-and-uploading-assets)
7. [Asset Types](#asset-types)
8. [Asset Provenance](#asset-provenance)
9. [Complete Example: Asset Discovery](#complete-example-asset-discovery)
10. [Complete Example: Python API Output](#complete-example-python-api-output)

---

## Discovering Assets

### Finding asset tables

**Start with `rag_search`** to discover asset tables by concept:
```
rag_search("image assets files", doc_type="catalog-schema")
rag_search("model weights checkpoints", doc_type="catalog-schema")
```

For a schema-scoped list, read the resource `deriva://catalog/{h}/{c}/ml/assets/{schema}` (e.g., `ml/assets/deriva-ml` for the built-ins, `ml/assets/myproject` for your domain schema). Same-named asset tables in different schemas are disambiguated by the schema segment. To survey across schemas, enumerate the schemas with `list_schemas` (deriva-mcp-core) and read this resource per schema — there is no single all-schemas asset-table tool or resource.

### Browsing assets in a table

For a bounded snapshot of one asset table, read `deriva://catalog/{h}/{c}/ml/assets/{schema}/{asset_table}` — returns up to the resource limit of assets in that table with `truncated` and `next_after_rid` set when the table exceeds the cap.

For a paginated, filterable browse, call `deriva_ml_list_assets(hostname="data.example.org", catalog_id="1", asset_table="Image")` to see all assets in a specific table with their RIDs, filenames, sizes, types, and descriptions.

To query with filters, call `get_entities(hostname="data.example.org", catalog_id="1", schema=<schema>, table="Image", filters={"Subject": "2-A1B2"})` for whole rows, or `query_attribute(hostname="data.example.org", catalog_id="1", path="<schema>:Image/Subject=2-A1B2", attributes=["RID", "Filename"])` if you only need specific columns. (Both replace the legacy `preview_table`.)

For an unfiltered sample, call `get_table_sample_data(hostname="data.example.org", catalog_id="1", schema=<schema>, table="Image")`.

### Finding a specific asset by RID

Call `deriva_ml_lookup_asset(hostname="data.example.org", catalog_id="1", asset_rid="2-IMG1")` to get full details including filename, size, MD5, types, description, and provenance (which execution created it).

For the raw catalog row with all custom metadata columns, call `get_entities(hostname="data.example.org", catalog_id="1", schema=<schema>, table=<asset_table>, filters={"RID": "2-IMG1"})`. (Replaces the legacy `get_record`.)

## Finding Assets by Type and Execution

### Discovering asset types

Use `rag_search` to find asset type vocabulary terms by concept:
```
rag_search("model weights asset type", doc_type="catalog-schema")
rag_search("prediction output types", doc_type="catalog-schema")
```

Call `list_vocabulary_terms(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Asset_Type")` to see all available type terms.

### Finding execution metadata

Every execution automatically generates metadata files in the `Execution_Metadata` table (see `concepts.md` for the four metadata types). To find metadata for a specific execution:

- Call `deriva_ml_get_execution(hostname="data.example.org", catalog_id="1", execution_rid="<rid>")` — returns the execution including its metadata files (Deriva_Config, Hydra_Config, Execution_Config, Runtime_Env)
- Call `get_entities(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Execution_Metadata", filters={"Execution": "<execution_rid>"})` — query the metadata table directly with filters (whole-row read; use `query_attribute` with a `path` expression if you only want specific columns)

### Finding execution output assets

To find the user-produced output assets for a specific execution:

- Call `deriva_ml_get_execution(hostname="data.example.org", catalog_id="1", execution_rid="<rid>")` — returns the output assets (Execution_Asset entries) for an execution alongside its inputs and metadata
- Call `deriva_ml_lookup_asset(hostname="data.example.org", catalog_id="1", asset_rid=...)` — given an asset RID, find which execution created it (reverse lookup; returns producer info). For the broader workflow-scoped query, use `deriva_ml_find_workflow_executions(...)`.

### Tracing asset provenance

To answer "where did this asset come from?":
1. Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` — returns producer execution info.
2. Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` — get full execution details including inputs, configuration, and other outputs.

To answer "what used this asset?":
- The legacy `list_asset_executions(asset_rid, asset_role="Input")` was removed. Use `deriva_ml_find_workflow_executions(hostname, catalog_id, workflow_rid=...)` and filter the results, or query the asset's Execution association table directly via `query_attribute` on `<AssetTable>_Execution` with `filters={"<AssetTable>": asset_rid, "Asset_Role": "Input"}`.

## Inspecting an Asset

To inspect an asset's properties:

1. Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` — returns filename, size, MD5, types, description, and producer execution info.
2. To see the raw catalog record with all columns (including custom metadata), call `get_entities(hostname, catalog_id, schema, table, filters={"RID": asset_rid})`.
3. To see which executions used the asset, query the asset's `<AssetTable>_Execution` association table via `get_entities(hostname, catalog_id, schema=<asset_schema>, table="<AssetTable>_Execution", filters={"<AssetTable>": asset_rid, "Asset_Role": "Input"})` (or `"Output"`).

## Downloading Assets

### Download a single asset

Call Python API `ml.download_asset(rid)` with `asset_rid` set to the asset's RID. Optionally set `dest_dir` to specify where to save the file (defaults to the active execution's working directory).

Returns the local file path, filename, asset table name, and asset types.

### Download assets as part of a dataset

Within an active execution, call Python API `exe.download_dataset_bag()` with `dataset_rid` and `version`. This downloads the full dataset as a BDBag, including all asset files for dataset members.

Parameters:
- `dataset_rid` (required): RID of the dataset
- `version` (required): semantic version string (e.g., `"1.0.0"`)
- `materialize` (optional, default `true`): set to `false` to download only metadata without fetching asset files
- `exclude_tables` (optional): list of table names to exclude from FK path traversal
- `timeout` (optional): `[connect_timeout, read_timeout]` in seconds

### Restructure downloaded assets for ML

After downloading a dataset, call Python API `bag.restructure_assets()` to organize asset files into a directory hierarchy suitable for ML frameworks like PyTorch ImageFolder. See the `ml-data-engineering` skill for details.

### Get the execution working directory

Call Python API `exe.working_dir` to find the local path where downloaded assets and staged outputs are located.

## Creating Asset Tables

> **Known gap:** the legacy `create_asset_table` shortcut is gone. Build the table by hand using the deriva-skills `create_table` tool plus the standard hatrac column shape, plus an Asset_Type FK, plus the necessary association tables.

See `concepts.md` → "Creating an Asset Table (Manual Recipe)" for the full step-by-step recipe. Summary:

1. Call `create_table(hostname, catalog_id, schema=..., table_name=..., columns=[...])` with the standard hatrac columns (`URL`, `Filename`, `Length`, `MD5`, `Description`) plus any custom metadata columns. *(`create_table` is a `deriva-mcp-core` tool — see `/deriva:create-table`.)*
2. Add the new table name as a term in the `Asset_Type` vocabulary: `add_term(hostname, catalog_id, schema="deriva-ml", table="Asset_Type", name="<TableName>", description=...)`.
3. Declare an `Asset_Type` foreign-key column on the new table — there is no standalone `create_foreign_key` MCP tool, so include the FK in `create_table`'s `foreign_keys=[...]` list at step 1, OR (if the table already exists) use `add_column` and then declare the FK via the schema-management surface. See `/deriva:create-table` for the FK definition shape.
4. Optionally add domain FK columns (e.g., `Image` → `Subject`).
5. Apply visible-columns / table-display annotations as needed (immediate-apply — there is no `apply_annotations()` staging step in the new MCP server).

Once those steps are done you can register files for upload via Python API `exe.asset_file_path(asset_name="<TableName>", ...)`.

## Registering and Uploading Assets

Asset upload happens within an execution context. The workflow is: register files for upload, then upload them all at once.

### Step 1: Create and start an execution

Call `deriva_ml_create_execution(hostname="data.example.org", catalog_id="1", workflow_rid="<workflow_rid>", description=...)` and capture the returned `execution_rid`. Then call `deriva_ml_start_execution(hostname="data.example.org", catalog_id="1", execution_rid=...)`. The `workflow_rid` is the RID of an already-registered Workflow record — look it up with `deriva_ml_find_workflow_by_url` or create it with `deriva_ml_create_workflow`.

### Step 2: Register output files

Call Python API `exe.asset_file_path()` to register each file for upload:
- `asset_name` (required): target asset table (e.g., `"Execution_Asset"`, `"Image"`, `"Model"`)
- `file_name` (required): path to an existing file to stage, or a filename for a new file to create
- `asset_types` (optional): list of Asset_Type vocabulary terms (defaults to `[asset_name]`)
- `description` (optional): human-readable description of the asset — what it contains and how it was produced
- `copy_file` (optional, default `false`): `true` to copy the file, `false` to symlink (saves disk space)
- `rename_file` (optional): rename the file during staging
- `metadata` (optional): dict of custom column values for asset tables with extra metadata columns

Returns a `file_path` — if creating a new file, write your output to this path. If staging an existing file, the file is symlinked or copied to the staging area.

**Always provide a description** for execution assets. Descriptions are applied to the catalog record after upload and are visible in the Chaise UI. Built-in execution metadata files (Hydra configs, `configuration.json`, `uv.lock`, environment snapshots) receive automatic descriptions.

**Example:** To register model weights for upload, call Python API `exe.asset_file_path()` with `asset_name`: `"Execution_Asset"`, `file_name`: `"model_weights.pt"`, `asset_types`: `["Model_Weights"]`, `description`: `"Trained CNN weights, optimizer state, and training log"`. Then write or copy the weights file to the returned `file_path`.

**Example:** To stage an existing CSV, call Python API `exe.asset_file_path()` with `asset_name`: `"Execution_Asset"`, `file_name`: `"/path/to/predictions.csv"`, `asset_types`: `["Predictions"]`, `description`: `"Per-image class predictions and probability distributions"`.

### Step 3: Commit all staged files

Call Python API `exe.commit_output_assets()` with `clean_folder` (optional, default `true`) to remove the local staging directory after upload.

This uploads all files registered via Python API `exe.asset_file_path()` to the object store, creates catalog records, assigns asset types, writes the descriptions you supplied plus `Upload_Duration`, links each asset to the execution with role "Output", and transitions the execution from `Stopped` → `Pending_Upload` → `Uploaded`. Returns an `UploadReport` (`total_uploaded`, `total_failed`, `per_table`, `errors`); per-asset path data is on `exe.uploaded_assets`. The call is idempotent — re-running after a partial failure resumes the failed rows and leaves the already-uploaded ones alone.

### Step 4: Commit (or abort) the execution

On success: call `deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid=...)` to finalize.

On failure: call `deriva_ml_abort_execution(hostname="data.example.org", catalog_id="1", execution_rid=...)` instead. (The legacy `stop_execution` tool was split into these two: pick the right one for the path you're on.)

### Python API pattern

```python
from deriva_ml import DerivaML, ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)

config = ExecutionConfiguration(
    workflow=workflow,
    description="Train CNN on CIFAR-10"
)

with ml.create_execution(config) as exe:
    # Register and write an output file
    model_path = exe.asset_file_path(
        "Execution_Asset",    # Asset table
        "model.pt",           # Filename
        ["Model_Weights"]     # Asset types
    )
    torch.save(model.state_dict(), model_path)

    # Stage an existing file
    csv_path = exe.asset_file_path(
        "Execution_Asset",
        "predictions.csv",     # Existing file path
        ["Predictions"]
    )

    # Upload happens automatically when context manager exits
    # Or call: exe.commit_output_assets()
```

## Asset Types

### Create a new asset type

Call `add_term(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Asset_Type", name=..., description=...)`. The legacy `add_asset_type` shortcut was removed; generic `add_term` works.

### Add a type to an asset

> **Known gap:** there is no dedicated tool. Use `update_entities` on the asset row's `Asset_Type` column. (The legacy `add_asset_type_to_asset` was removed.)

```
update_entities(hostname="data.example.org", catalog_id="1",
    schema="<asset_schema>", table="<asset_table>",
    entities=[{"RID": "2-IMG1", "Asset_Type": "Segmentation_Mask"}])
```

For tables that allow multiple types via an association table, insert into the `<AssetTable>_Asset_Type` association table directly with `insert_entities(...)`.

### Remove a type from an asset

> **Known gap:** there is no dedicated tool. Use `update_entities` to clear the `Asset_Type` column (or delete the association row). (The legacy `remove_asset_type_from_asset` was removed.)

```
update_entities(hostname="data.example.org", catalog_id="1",
    schema="<asset_schema>", table="<asset_table>",
    entities=[{"RID": "2-IMG1", "Asset_Type": null}])
```

### View asset types

Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` to see an asset's current types, or `list_vocabulary_terms(hostname, catalog_id, schema="deriva-ml", table="Asset_Type")` to see all available type terms.

## Asset Provenance

### Find what created an asset

Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` — returns the producer execution (RID, workflow, status, description). The legacy `list_asset_executions(..., asset_role="Output")` was removed; the typed lookup returns the same info.

### Find what used an asset

There is no single dedicated tool. Two options:
1. `deriva_ml_find_workflow_executions(hostname, catalog_id, workflow_rid=...)` — broad query by workflow.
2. `get_entities(hostname, catalog_id, schema=<asset_schema>, table="<AssetTable>_Execution", filters={"<AssetTable>": asset_rid, "Asset_Role": "Input"})` — direct whole-row query on the association table. Use `query_attribute` with a `path` expression if you only want projected columns or want to traverse FKs in one call.

### Trace from execution to assets

Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to see an execution's full details including input and output assets.

## Complete Example: Asset Discovery

End-to-end MCP workflow: find assets, inspect one, check its provenance. Substitute your hostname (e.g. `"data.example.org"`) and catalog ID (e.g. `"1"`).

**Step 1:** Read `deriva://catalog/data.example.org/1/ml/assets/{schema}` (your domain schema, or `deriva-ml` for the built-ins) to find what asset tables exist in that schema.

**Step 2:** Call `deriva_ml_list_assets(hostname="data.example.org", catalog_id="1", asset_table="Image")` to browse images.

**Step 3:** Call `deriva_ml_lookup_asset(hostname="data.example.org", catalog_id="1", asset_rid="2-IMG1")` to inspect a specific image — filename, size, MD5, types, and producer execution.

**Step 4:** The producer execution RID comes from step 3; call `deriva_ml_get_execution(hostname="data.example.org", catalog_id="1", execution_rid=<from-step-3>)` to see the full execution context — workflow, configuration, other inputs and outputs.

## Complete Example: Python API Output

```python
from deriva_ml import DerivaML, ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)

# Look up an existing asset
asset = ml.lookup_asset("3-JSE4")
print(f"File: {asset.filename}, Size: {asset.length} bytes")
print(f"MD5: {asset.md5}")
print(f"Types: {asset.asset_types}")
print(f"Table: {asset.asset_table}")

# Find what created it
creators = asset.list_executions(asset_role="Output")
for exe in creators:
    print(f"Created by execution {exe.execution_rid}: {exe.description}")

# Find what used it
consumers = asset.list_executions(asset_role="Input")
for exe in consumers:
    print(f"Used by execution {exe.execution_rid}: {exe.description}")

# Download it
local_path = asset.download(Path("/tmp/assets"))
print(f"Downloaded to: {local_path}")
```
