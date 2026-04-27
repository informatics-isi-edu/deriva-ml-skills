# Asset Workflow Reference

Step-by-step MCP tool and Python API examples for working with assets. For background on asset tables, types, caching, and provenance, see `concepts.md`.

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

For the full structured list, read `deriva://catalog/asset-tables` or `deriva://catalog/assets` (includes record counts).

### Browsing assets in a table

Read the `deriva://table/{table_name}/assets` resource to see all assets in a specific table with their RIDs, filenames, sizes, types, and descriptions.

To query with filters, call `preview_table` with `table_name` set to the asset table and `filters` for your criteria. For example, to find images linked to a specific subject, call `preview_table` with `table_name`: `"Image"`, `filters`: `{"Subject": "2-A1B2"}`.

To get a count, call `preview_table` (with limit=1) with `table_name` set to the asset table.

### Finding a specific asset by RID

Read the `deriva://asset/{asset_rid}` resource to get full details including filename, size, MD5, types, description, provenance (which executions created or used it), and a link to the Chaise web UI.

Alternatively, call `get_record` with `table_name` set to the asset table and `rid` set to the asset's RID.

## Finding Assets by Type and Execution

### Discovering asset types

Use `rag_search` to find asset type vocabulary terms by concept:
```
rag_search("model weights asset type", doc_type="catalog-schema")
rag_search("prediction output types", doc_type="catalog-schema")
```

Read `deriva://catalog/vocabularies` and look for the `Asset_Type` vocabulary to see all available type terms.

### Finding execution metadata

Every execution automatically generates metadata files in the `Execution_Metadata` table (see `concepts.md` for the four metadata types). To find metadata for a specific execution:

- Read `deriva://execution/{rid}/metadata` — returns the auto-generated metadata files for an execution (Deriva_Config, Hydra_Config, Execution_Config, Runtime_Env)
- Call `preview_table("Execution_Metadata", filters={"Execution": "<execution_rid>"})` — query the metadata table directly with filters

### Finding execution output assets

To find the user-produced output assets for a specific execution:

- Read `deriva://execution/{rid}/outputs` — returns the output assets (Execution_Asset entries) for an execution
- Call `list_asset_executions(asset_rid, asset_role="Output")` — given an asset RID, find which execution created it (reverse lookup)

### Tracing asset provenance

To answer "where did this asset come from?":
1. Call `list_asset_executions` with `asset_rid` and `asset_role`: `"Output"` — returns the execution that created the asset
2. Read `deriva://experiment/{execution_rid}` — get full execution details including inputs, configuration, and other outputs

To answer "what used this asset?":
1. Call `list_asset_executions` with `asset_rid` and `asset_role`: `"Input"` — returns all executions that consumed the asset

## Inspecting an Asset

To inspect an asset's properties:

1. Read `deriva://asset/{asset_rid}` — returns filename, size, MD5, types, description, provenance, and Chaise URL.
2. To see the raw catalog record with all columns (including custom metadata), call `get_record` with `table_name` and `rid`.
3. To see which executions created or used the asset, call `list_asset_executions` with `asset_rid`. Optionally filter with `asset_role`: `"Output"` (created it) or `"Input"` (used it).

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

Call `create_asset_table` with:
- `asset_name` (required): name for the table (e.g., `"Image"`, `"Model"`, `"Prediction"`)
- `comment` (optional): description of what the table stores
- `columns` (optional): list of additional metadata column definitions beyond the standard asset columns
- `referenced_tables` (optional): list of table names to create foreign keys to (e.g., `["Subject"]`)
- `schema` (optional): schema to create in (defaults to the domain schema)

Each column definition is a dict with `name`, `type` (a dict with `typename` key), and optional `nullok`, `default`, `comment`.

**Example:** To create an Image asset table with custom metadata and a link to Subject, call `create_asset_table` with `asset_name`: `"Image"`, `comment`: `"Microscopy images with metadata"`, `columns`: `[{"name": "Width", "type": {"typename": "int4"}}, {"name": "Height", "type": {"typename": "int4"}}]`, `referenced_tables`: `["Subject"]`.

This creates:
- The `Image` table with standard asset columns plus `Width`, `Height`, and an FK to `Subject`
- An `Image_Asset_Type` association table for type vocabulary links
- An `Image_Execution` association table for provenance tracking
- An `"Image"` term in the `Asset_Type` vocabulary

## Registering and Uploading Assets

Asset upload happens within an execution context. The workflow is: register files for upload, then upload them all at once.

### Step 1: Create and start an execution

Call `create_execution` with `workflow_name`, `workflow_type`, and `description`. Then call `start_execution`.

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

### Step 3: Upload all staged files

Call Python API `exe.upload_execution_outputs()` with `clean_folder` (optional, default `true`) to remove the local staging directory after upload.

This uploads all files registered via Python API `exe.asset_file_path()` to the object store, creates catalog records, assigns asset types, and links each asset to the execution with role "Output".

### Step 4: Stop the execution

Call `stop_execution` to finalize the execution.

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
    # Or call: exe.upload_execution_outputs()
```

## Asset Types

### Create a new asset type

Call `add_asset_type` with `type_name` and `description`.

### Add a type to an asset

Call `add_asset_type_to_asset` with `asset_rid` and `type_name`. Assets can have multiple types.

### Remove a type from an asset

Call `remove_asset_type_from_asset` with `asset_rid` and `type_name`.

### View asset types

Read `deriva://asset/{asset_rid}` to see an asset's current types. Read `deriva://catalog/vocabularies` and look for `Asset_Type` to see all available type terms.

## Asset Provenance

### Find what created an asset

Call `list_asset_executions` with `asset_rid` and `asset_role`: `"Output"`. Returns the execution(s) that produced this asset, including execution RID, workflow, status, and description.

### Find what used an asset

Call `list_asset_executions` with `asset_rid` and `asset_role`: `"Input"`. Returns all executions that consumed this asset.

### Find all executions for an asset

Call `list_asset_executions` with just `asset_rid` (no role filter) to get both creators and consumers.

### Trace from execution to assets

Read `deriva://experiment/{execution_rid}` to see an execution's full details including input and output assets.

## Complete Example: Asset Discovery

End-to-end MCP workflow: find assets, inspect one, check its provenance.

**Step 1:** Read `deriva://catalog/asset-tables` to find what asset tables exist.

**Step 2:** Read `deriva://table/Image/assets` to browse images.

**Step 3:** Read `deriva://asset/2-IMG1` to inspect a specific image — filename, size, MD5, types, and provenance.

**Step 4:** Call `list_asset_executions` with `asset_rid`: `"2-IMG1"`, `asset_role`: `"Output"` to find which execution created this image.

**Step 5:** Read `deriva://experiment/{execution_rid}` (using the execution RID from step 4) to see the full execution context — workflow, configuration, other inputs and outputs.

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
