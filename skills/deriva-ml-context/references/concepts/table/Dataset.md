---
type: Table
title: Dataset
kind: core
description: A versioned collection of catalog rows an execution consumed or produced.
---

# Dataset

A **versioned collection** of catalog rows (assets, files, nested datasets) that
an execution consumed or produced. Soft-deletable. The backing table of the
DerivaML **Dataset** abstraction; its version history lives in
[Dataset_Version](Dataset_Version.md).

Datasets are typed via [Dataset_Dataset_Type](Dataset_Dataset_Type.md), may
contain nested datasets via [Dataset_Dataset](Dataset_Dataset.md), and link to
their input executions via [Dataset_Execution](Dataset_Execution.md). Files in
a dataset are tracked through [Dataset_File](Dataset_File.md).

## Foreign Keys

- `Version` → [Dataset_Version](Dataset_Version.md) — points at this dataset's
  **current** version row.

## Notable columns

- `Description` (markdown) — human-readable purpose.
- `Deleted` (boolean) — soft-delete flag. When `true`, the dataset is hidden
  from default listings but retained so existing execution provenance and
  citations remain resolvable.
- `Version` — FK to the current `Dataset_Version`.
