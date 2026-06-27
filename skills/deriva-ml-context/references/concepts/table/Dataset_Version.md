---
type: Table
title: Dataset_Version
kind: core
description: Version history for a dataset, one row per (Dataset, Version) pair.
---

# Dataset_Version

Tracks the version history of a [Dataset](Dataset.md). Each row pins a
`(Dataset, Version)` pair, optionally with a catalog `Snapshot` for released
versions and a `Minid` URL for the materialized BDBag. The **current** version
of a dataset is selected by the outbound FK `Dataset.Version` pointing here.

Output-dataset provenance lives in this table: the `Execution` column records
which execution *produced* a given version. Contrast with
[Dataset_Execution](Dataset_Execution.md), which records which executions
*consumed* a dataset.

## Foreign Keys

- `Dataset` → [Dataset](Dataset.md) — the dataset this version belongs to.
- `Execution` → [Execution](Execution.md) — the execution that produced this
  version (nullable: `NULL` for the initial release row created at dataset
  creation time, which has no producing execution).

## Notable columns

- `Version` (text, default `0.1.0`) — PEP 440 version label. Released rows
  carry `MAJOR.MINOR.PATCH`; dev rows carry `<last_release>.post1.devN` to
  denote drift since the last release.
- `Description` (markdown) — release notes for this version.
- `Snapshot` (text, nullable) — catalog snapshot ID pinned at release time.
  `NULL` on dev rows (tracks live catalog state with no pinned snapshot).
- `Minid` (text) — URL to the MINID for the materialized BDBag.
- `Minid_Spec_Hash` (text) — SHA-256 hash of the download spec used to generate
  the MINID bag; used to detect stale MINIDs when the schema or traversal paths
  change.
- **Unique key**: `(Dataset, Version)` — no two version rows for the same
  dataset may share the same version label.
