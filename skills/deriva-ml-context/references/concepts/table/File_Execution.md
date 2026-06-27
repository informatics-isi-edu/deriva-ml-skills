---
type: Table
title: File_Execution
kind: association
description: Association between File rows and Executions, with an Asset_Role column recording input vs. output direction.
---

# File_Execution

Many-to-many association between [File](File.md) and [Execution](Execution.md).
Each row records that a file (a by-reference external URL) was an input to or
output of a specific execution. The `Asset_Role` column carries the direction
(`Input` or `Output`) as a FK to [Asset_Role](Asset_Role.md).

Created automatically by `create_asset_table` alongside the [File](File.md)
table. The `Asset_Role` FK is added via `create_reference` on the
newly-created association table.

## Foreign Keys

- `File` → [File](File.md) — the file involved in this association.
- `Execution` → [Execution](Execution.md) — the execution it was input to or
  output from.
- `Asset_Role` → [Asset_Role](Asset_Role.md) — direction of the association:
  `Input` or `Output`.

## Notable columns

Beyond the three FK columns (and ERMrest system columns) this table carries no
additional data columns.
