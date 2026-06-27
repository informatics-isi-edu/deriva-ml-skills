---
type: Table
title: Dataset_Dataset_Type
kind: association
description: Many-to-many tag assignments between datasets and dataset types.
---

# Dataset_Dataset_Type

Association table linking [Dataset](Dataset.md) ↔ [Dataset_Type](Dataset_Type.md).
A dataset can carry multiple types simultaneously (for example `Training` +
`Labeled`); a type can apply to many datasets.

## Foreign Keys

- `Dataset` → [Dataset](Dataset.md) — the dataset being tagged.
- `Dataset_Type` → [Dataset_Type](Dataset_Type.md) — the vocabulary term
  assigned to the dataset.

## Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns `RID`, `RCT`, `RMT`, `RCB`, `RMB`) it carries no additional
data columns.
