---
type: Table
title: Dataset_Dataset
kind: association
description: Self-association expressing dataset nesting — parent collection and member sub-dataset.
---

# Dataset_Dataset

Self-referential association on [Dataset](Dataset.md) expressing dataset
nesting. The `Dataset` column is the **parent** (the containing collection);
`Nested_Dataset` is a **member** (a sub-dataset inside that collection).

Typical use: a `Complete` parent dataset contains `Training`, `Testing`, and
`Validation` children as a three-way split. Note that `split_dataset` is the
**exception**: it does **not** create a `Dataset_Dataset` row. Instead it
records the source dataset as an execution input (via `Dataset_Execution`) and
produces the split children as outputs whose producing execution is recorded in
`Dataset_Version.Execution`. To trace the origin of a split child, follow its
producing execution's input datasets — not a `Dataset_Dataset` row. Manual
grouping and structured collections that should model explicit parent-child
nesting are the primary use case for this table.

## Foreign Keys

Both columns reference the same table:

- `Dataset` → [Dataset](Dataset.md) — the parent (containing) dataset.
- `Nested_Dataset` → [Dataset](Dataset.md) — the member (contained) dataset.

## Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.
