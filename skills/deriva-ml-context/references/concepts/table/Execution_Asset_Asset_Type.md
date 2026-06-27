---
type: Table
title: Execution_Asset_Asset_Type
kind: association
description: Many-to-many tag assignments between Execution_Asset rows and Asset_Type vocabulary terms.
---

# Execution_Asset_Asset_Type

Many-to-many association between [Execution_Asset](Execution_Asset.md) and
[Asset_Type](Asset_Type.md). Each row tags one data asset file with one
vocabulary term (e.g. `Model_File`, `Output_File`, `Metrics_File`,
`Notebook_Output`). A single asset can carry multiple types.

Created automatically by `create_asset_table` alongside the
[Execution_Asset](Execution_Asset.md) table.

## Foreign Keys

Both columns reference tables in this cluster:

- `Execution_Asset` → [Execution_Asset](Execution_Asset.md) — the data asset
  file being tagged.
- `Asset_Type` → [Asset_Type](Asset_Type.md) — the vocabulary term applied to
  that file.

## Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.
