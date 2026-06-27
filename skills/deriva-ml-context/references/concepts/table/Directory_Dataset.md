---
type: Table
title: Directory_Dataset
kind: satellite
description: Records the source directory path for a dataset auto-created by add_files.
---

# Directory_Dataset

Satellite table recording the source folder that an `add_files`-created
directory dataset represents, as a path relative to the ingest root. One row
per directory dataset; absent for datasets not built from a directory tree.

Created automatically by `add_files` when ingesting a source directory: the
ingest root itself gets `Path = "."`, and each sub-folder gets a
`Path` relative to that root.

## Foreign Keys

- `Dataset` → [Dataset](Dataset.md) — the directory dataset this row describes.
  Also the **unique key** of this table — exactly one `Directory_Dataset` row
  may exist per dataset.

## Notable columns

- `Dataset` (text) — FK to the directory [Dataset](Dataset.md); also the unique
  key (one satellite row per dataset).
- `Path` (text) — source directory this dataset represents, relative to the
  ingest root. The ingest root stores `"."`.
