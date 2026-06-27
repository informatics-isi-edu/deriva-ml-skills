---
type: Table
title: File_Asset_Type
kind: association
description: Many-to-many tag assignments between File rows and Asset_Type vocabulary terms.
---

# File_Asset_Type

Many-to-many association between [File](File.md) and [Asset_Type](Asset_Type.md).
Each row tags one file with one vocabulary term (e.g. `File`, `Input_File`,
`Output_File`). A single file can carry multiple types.

Created automatically by `create_asset_table` alongside the [File](File.md)
table.

## Foreign Keys

Both columns reference tables in this cluster:

- `File` → [File](File.md) — the file being tagged.
- `Asset_Type` → [Asset_Type](Asset_Type.md) — the vocabulary term applied to
  that file.

## Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.
