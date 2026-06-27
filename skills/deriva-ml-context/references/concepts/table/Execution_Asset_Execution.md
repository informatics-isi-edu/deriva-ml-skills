---
type: Table
title: Execution_Asset_Execution
kind: association
description: Association between Execution_Asset rows and Executions, with an Asset_Role column recording input vs. output direction.
---

# Execution_Asset_Execution

Many-to-many association between [Execution_Asset](Execution_Asset.md) and
[Execution](Execution.md). Each row records that a data asset file was an
input to or output of a specific execution. The `Asset_Role` column carries
the direction (`Input` or `Output`) as a FK to [Asset_Role](Asset_Role.md).

Created automatically by `create_asset_table` alongside the
[Execution_Asset](Execution_Asset.md) table. The `Asset_Role` FK is added via
`create_reference` on the newly-created association table.

## Foreign Keys

- `Execution_Asset` → [Execution_Asset](Execution_Asset.md) — the data asset
  file involved in this association.
- `Execution` → [Execution](Execution.md) — the execution it was input to or
  output from.
- `Asset_Role` → [Asset_Role](Asset_Role.md) — direction of the association:
  `Input` or `Output`.

## Notable columns

Beyond the three FK columns (and ERMrest system columns) this table carries no
additional data columns.
