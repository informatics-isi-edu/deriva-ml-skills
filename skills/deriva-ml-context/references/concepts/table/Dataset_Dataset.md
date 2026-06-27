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
`Validation` children as a three-way split. Note that `split_dataset` does
**not** create these edges — the split is an execution input and the nested
datasets are outputs; the edge between input and output lives in
[Dataset_Version](Dataset_Version.md) via the `Execution` FK, not here.

## Foreign Keys

Both columns reference the same table:

- `Dataset` → [Dataset](Dataset.md) — the parent (containing) dataset.
- `Nested_Dataset` → [Dataset](Dataset.md) — the member (contained) dataset.

## Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.
