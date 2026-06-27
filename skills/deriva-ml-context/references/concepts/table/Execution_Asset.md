---
type: Table
title: Execution_Asset
kind: asset
description: Asset table for data files produced or consumed by an execution (model weights, prediction CSVs, plots, notebook outputs). Stored in Hatrac.
---

# Execution_Asset

Asset table for files that are **data outputs or inputs of an execution** —
trained model weights, prediction CSVs, evaluation plots, notebook outputs.
Bytes are stored in Hatrac via the upload template
`/hatrac/metadata/{{MD5}}.{{Filename}}`.

Execution_Asset is one of three built-in asset tables created by
`create_asset_table`. It is distinguished from
[Execution_Metadata](Execution_Metadata.md) by *purpose* (data results vs.
environment/config), not by file shape — both tables have the same standard
column set.

The asset-table row shape and the bulk I/O operations (upload, download,
attach to execution) are documented in `pattern/asset-table.md` and covered
by the `/deriva-ml:work-with-assets` skill.

## Foreign Keys

This table carries no outbound foreign keys itself. Associations to
[Asset_Type](Asset_Type.md) and [Execution](Execution.md) are expressed
through the sibling tables [Execution_Asset_Asset_Type](Execution_Asset_Asset_Type.md)
and [Execution_Asset_Execution](Execution_Asset_Execution.md).

## Notable columns

Standard asset shape (from `AssetTableDef`):

- `URL` (ermrest_uri, not null) — Hatrac object URL; populated by the Chaise
  upload UI using the template `/hatrac/metadata/{{MD5}}.{{Filename}}`.
- `Filename` (text) — original filename at upload time.
- `Length` (int8) — file size in bytes.
- `MD5` (text) — MD5 checksum of the file content.
- `Description` (markdown) — human-readable description of what this asset
  file represents.
