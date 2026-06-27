---
type: Table
title: Dataset_Type
kind: vocabulary
description: Controlled vocabulary classifying datasets by role in an ML pipeline.
---

# Dataset_Type

Controlled vocabulary classifying datasets by their role in an ML pipeline.
Tags are assigned to datasets via the [Dataset_Dataset_Type](Dataset_Dataset_Type.md)
association table — a dataset can carry multiple types simultaneously (for
example `Training` + `Labeled`).

The three-axis framing (completeness, split role, label status) that gives
these terms their structure is documented in
[/deriva-ml:dataset-lifecycle](/deriva-ml:dataset-lifecycle).

## Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

## Seeded terms

Nine terms are seeded at schema initialization:

| Name | Description |
|------|-------------|
| `Complete` | A dataset containing all available records of a given type. |
| `File` | A dataset that contains file assets. |
| `Directory` | A dataset auto-created by `add_files` to mirror an ingested source directory structure; nested Directory datasets reflect the source folder hierarchy. |
| `Training` | A dataset subset used for model training. |
| `Testing` | A dataset subset used for model testing/evaluation. |
| `Validation` | A dataset subset used for model validation during training. |
| `Split` | A dataset that contains nested dataset splits. |
| `Labeled` | A dataset containing records with ground truth labels. |
| `Unlabeled` | A dataset containing records without ground truth labels. |

Domain-specific dataset categories belong in user vocabularies, not here.
