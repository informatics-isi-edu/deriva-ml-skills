---
type: Table
title: Asset_Role
kind: vocabulary
description: Controlled vocabulary distinguishing input from output direction on asset-execution associations.
---

# Asset_Role

Controlled vocabulary distinguishing **input from output direction** on every
`{Asset}_Execution` association row. When an asset is linked to an execution,
the `Asset_Role` term records whether the asset flowed into the execution
(`Input`) or was produced by it (`Output`).

The role is carried on all three built-in asset-execution association tables
([Execution_Asset_Execution](Execution_Asset_Execution.md),
[Execution_Metadata_Execution](Execution_Metadata_Execution.md),
[File_Execution](File_Execution.md)) and on any domain-specific asset-execution
associations created via `create_asset_table`.

## Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

## Seeded terms

Two terms are seeded at schema initialization:

| Name | Description |
|------|-------------|
| `Input` | Asset used for input of an execution. |
| `Output` | Asset used for output of an execution. |
