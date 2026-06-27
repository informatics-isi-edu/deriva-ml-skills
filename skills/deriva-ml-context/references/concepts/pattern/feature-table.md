---
type: Pattern
title: Feature table shape
description: The runtime-created shape of a DerivaML feature-value table.
---

# Feature table shape

A DerivaML **feature** is stored in a runtime-created association table named
`Execution_{TargetTable}_{FeatureName}` — for example, an `Image_Classification`
feature on the `Image` table is stored in `Execution_Image_Image_Classification`.
`create_feature` mints one such table per `(target_table, feature_name)` pair and
registers the name in the [Feature_Name](../table/Feature_Name.md) vocabulary.

Every feature table carries these FKs: `Execution` →
[Execution](../table/Execution.md), `{TargetTable}` → the annotated domain table,
and `Feature_Name` → [Feature_Name](../table/Feature_Name.md) — plus one column
per vocabulary term, asset, and metadata field the feature defines. **Discovery:**
any association table with both `Feature_Name` and `Execution` columns is a
feature table.

Feature tables live in the **domain schema** (alongside the target table), not in
`deriva-ml`. For the full column reference and how to create/populate features,
see **`/deriva-ml:create-feature`** (it owns this surface).
