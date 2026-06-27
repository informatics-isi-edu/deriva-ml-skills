---
type: Table
title: Execution_Metadata_Asset_Type
kind: association
description: Many-to-many tag assignments between Execution_Metadata rows and Asset_Type vocabulary terms.
---

# Execution_Metadata_Asset_Type

Many-to-many association between [Execution_Metadata](Execution_Metadata.md)
and [Asset_Type](Asset_Type.md). Each row tags one metadata file with one
vocabulary term (e.g. `Hydra_Config`, `Deriva_Config`, `Runtime_Env`). A
single metadata file can carry multiple types.

Created automatically by `create_asset_table` alongside the
[Execution_Metadata](Execution_Metadata.md) table.

## Foreign Keys

Both columns reference tables in this cluster:

- `Execution_Metadata` → [Execution_Metadata](Execution_Metadata.md) — the
  metadata file being tagged.
- `Asset_Type` → [Asset_Type](Asset_Type.md) — the vocabulary term applied to
  that file.

## Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.
