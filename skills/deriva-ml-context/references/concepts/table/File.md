---
type: Table
title: File
kind: asset
description: Asset table for files that live outside Hatrac — external URLs the catalog references but does not host. Used by add_files.
---

# File

Asset table for files that **live outside Hatrac** — external or
locally-staged URLs the catalog references but does not host. Created by
`create_asset_table` with `use_hatrac=False`, which omits the Hatrac upload
template from the `URL` column: `URL` is a plain `ermrest_uri` string rather
than a wired upload target.

This is the table populated by `add_files` when ingesting a source directory.
Each row represents one file in the registered directory tree, with `URL`
carrying the path or external URL to the bytes and `MD5` / `Length` / `Filename`
carrying the standard provenance columns.

The row shape is identical to [Execution_Asset](Execution_Asset.md) and
[Execution_Metadata](Execution_Metadata.md) — the only difference is
the absence of the Hatrac upload template. File rows link into Datasets via
[Dataset_File](Dataset_File.md).

The asset-table row shape and the `add_files` ingest workflow are documented
in `pattern/asset-table.md` and covered by the `/deriva-ml:work-with-assets`
skill.

## Foreign Keys

This table carries no outbound foreign keys itself. Associations to
[Asset_Type](Asset_Type.md) and [Execution](Execution.md) are expressed
through the sibling tables [File_Asset_Type](File_Asset_Type.md) and
[File_Execution](File_Execution.md). Membership in datasets is expressed
through [Dataset_File](Dataset_File.md).

## Notable columns

Standard asset shape (from `AssetTableDef`, `use_hatrac=False`):

- `URL` (ermrest_uri, not null) — plain URL to the file bytes (no Hatrac
  upload template). Points at bytes the catalog references but does not host.
- `Filename` (text) — original filename.
- `Length` (int8) — file size in bytes.
- `MD5` (text) — MD5 checksum of the file content.
- `Description` (markdown) — human-readable description of what this file
  represents.
