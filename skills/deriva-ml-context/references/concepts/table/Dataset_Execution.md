---
type: Table
title: Dataset_Execution
kind: association
description: Input edge recording that an execution consumed a dataset.
---

# Dataset_Execution

Association table recording that an [Execution](Execution.md) *consumed* a
[Dataset](Dataset.md) as input. One row per (dataset, execution) input pair.
An optional `Dataset_Version` FK pins the exact version that was consumed.

This is the **input** edge. The **output** edge — which execution *produced* a
dataset version — lives in [Dataset_Version](Dataset_Version.md) via the
`Execution` column on that table (not here).

## Foreign Keys

- `Dataset` → [Dataset](Dataset.md) — the dataset consumed as input.
- `Execution` → [Execution](Execution.md) — the execution that consumed it.
- `Dataset_Version` → [Dataset_Version](Dataset_Version.md) — the specific
  version consumed (nullable: `NULL` when the consumed version is unknown,
  e.g. on legacy rows).

## Notable columns

- `Dataset_Version` — nullable FK pinning the exact consumed version. When
  present, provides precise version-level provenance for inputs.
