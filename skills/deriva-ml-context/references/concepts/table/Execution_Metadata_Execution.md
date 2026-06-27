---
type: Table
title: Execution_Metadata_Execution
kind: association
description: Association between Execution_Metadata rows and Executions, with an Asset_Role column recording input vs. output direction.
---

# Execution_Metadata_Execution

Many-to-many association between [Execution_Metadata](Execution_Metadata.md)
and [Execution](Execution.md). Each row records that a metadata file was an
input to or output of a specific execution. The `Asset_Role` column carries the
direction (`Input` or `Output`) as a FK to [Asset_Role](Asset_Role.md).

Created automatically by `create_asset_table` alongside the
[Execution_Metadata](Execution_Metadata.md) table. The `Asset_Role` FK is
added via `create_reference` on the newly-created association table.

In practice, metadata files are almost always `Output` — the DerivaML runtime
uploads configs and runtime-env info at execution start, attributing them to
the running execution. The `Input` role is available for workflows that consume
a prior execution's metadata files.

## Foreign Keys

- `Execution_Metadata` → [Execution_Metadata](Execution_Metadata.md) — the
  metadata file involved in this association.
- `Execution` → [Execution](Execution.md) — the execution it was input to or
  output from.
- `Asset_Role` → [Asset_Role](Asset_Role.md) — direction of the association:
  `Input` or `Output`.

## Notable columns

Beyond the three FK columns (and ERMrest system columns) this table carries no
additional data columns.
