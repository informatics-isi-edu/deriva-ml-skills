---
type: Table
title: Dataset_File
kind: association
description: Many-to-many membership of File rows in Datasets.
---

# Dataset_File

Association table linking [Dataset](Dataset.md) ↔ [File](File.md). Records
that a file is a member of a dataset. A file can belong to multiple datasets;
a dataset can contain multiple files.

This table is populated by the `add_files` ingestion path when files are
registered into a dataset.

## Foreign Keys

- `Dataset` → [Dataset](Dataset.md) — the dataset the file belongs to.
- `File` → [File](File.md) — the file that is a member of the dataset.

## Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.
