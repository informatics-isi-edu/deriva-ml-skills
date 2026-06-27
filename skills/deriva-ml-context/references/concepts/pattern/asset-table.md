---
type: Pattern
title: Asset table shape
description: The invariant shape every DerivaML asset table has, fixed and runtime-created.
---

# Asset table shape

Every DerivaML **asset table** has the same shape: the five standard columns
(`Filename`, `URL`, `Length`, `MD5`, `Description`) plus two auto-created
association tables — `{Name}_Asset_Type` (tags the asset with
[Asset_Type](../table/Asset_Type.md) terms) and `{Name}_Execution` (links it to
an [Execution](../table/Execution.md) with an [Asset_Role](../table/Asset_Role.md)
of Input or Output).

The `deriva-ml` schema ships **three built-in** asset tables:
[Execution_Metadata](../table/Execution_Metadata.md),
[Execution_Asset](../table/Execution_Asset.md), and
[File](../table/File.md) (by-reference). **Domain asset tables** (`Image`,
`Model_Weights`, …) are created at runtime by `create_asset` and live in your
**project's domain schema**, not in `deriva-ml`.

For the full column reference, the `create_asset_table` mechanics, and how to
work with assets, see **`/deriva-ml:work-with-assets`** (it owns this surface).
