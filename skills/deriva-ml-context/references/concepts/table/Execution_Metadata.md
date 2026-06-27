---
type: Table
title: Execution_Metadata
kind: asset
description: Asset table for files describing an execution's environment and configuration (Hydra configs, runtime info, DerivaML config JSON). Stored in Hatrac.
---

# Execution_Metadata

Asset table for files that describe an **execution's environment and
configuration** — Hydra YAML configs, runtime environment info, and the
DerivaML execution configuration JSON. Bytes are stored in Hatrac via the
upload template `/hatrac/metadata/{{MD5}}.{{Filename}}`.

Execution_Metadata is one of three built-in asset tables created by
`create_asset_table`. It is distinguished from
[Execution_Asset](Execution_Asset.md) by *purpose* (environment / config vs.
data outputs), not by file shape — both tables have the same standard column
set.

The asset-table row shape and the bulk I/O operations (upload, download,
attach to execution) are documented in `pattern/asset-table.md` and covered
by the `/deriva-ml:work-with-assets` skill.

## Foreign Keys

This table carries no outbound foreign keys itself. Associations to
[Asset_Type](Asset_Type.md) and [Execution](Execution.md) are expressed
through the sibling tables [Execution_Metadata_Asset_Type](Execution_Metadata_Asset_Type.md)
and [Execution_Metadata_Execution](Execution_Metadata_Execution.md).

## Notable columns

Standard asset shape (from `AssetTableDef`):

- `URL` (ermrest_uri, not null) — Hatrac object URL; populated by the Chaise
  upload UI using the template `/hatrac/metadata/{{MD5}}.{{Filename}}`.
- `Filename` (text) — original filename at upload time.
- `Length` (int8) — file size in bytes.
- `MD5` (text) — MD5 checksum of the file content.
- `Description` (markdown) — human-readable description of what this metadata
  file captures.
