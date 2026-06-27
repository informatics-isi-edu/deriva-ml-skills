---
type: Index
title: deriva-ml catalog schema
description: >
  The fixed deriva-ml catalog schema — every table, its foreign keys, and the
  FK graph — as an OKF bundle.
---

# deriva-ml catalog schema

These documents follow the
[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
— Markdown + YAML frontmatter. This bundle is the static reference for the
**fixed `deriva-ml` schema** as of **deriva-ml v1.53.0**; re-check it against the
library when the schema changes. For a live visual of a *specific* catalog, use
`/deriva-ml:browse-erd`.

> **`deriva-ml` schema vs domain schema.** These 26 tables are the fixed
> `deriva-ml` schema that backs the five abstractions — library-managed. Your
> project's own tables (`Subject`, `Image`, …) live in a separate **domain
> schema** named after the project; runtime-created asset and feature tables
> land there too (see the patterns below).

## Tables

**Core** — [Dataset](table/Dataset.md), [Dataset_Version](table/Dataset_Version.md), [Workflow](table/Workflow.md), [Execution](table/Execution.md)

**Vocabulary** — [Dataset_Type](table/Dataset_Type.md), [Workflow_Type](table/Workflow_Type.md), [Execution_Status](table/Execution_Status.md), [Asset_Type](table/Asset_Type.md), [Asset_Role](table/Asset_Role.md), [Feature_Name](table/Feature_Name.md)

**Association** — [Dataset_Dataset_Type](table/Dataset_Dataset_Type.md), [Dataset_Dataset](table/Dataset_Dataset.md), [Dataset_Execution](table/Dataset_Execution.md), [Dataset_File](table/Dataset_File.md), [Workflow_Workflow_Type](table/Workflow_Workflow_Type.md), [Execution_Execution](table/Execution_Execution.md), [Execution_Metadata_Asset_Type](table/Execution_Metadata_Asset_Type.md), [Execution_Metadata_Execution](table/Execution_Metadata_Execution.md), [Execution_Asset_Asset_Type](table/Execution_Asset_Asset_Type.md), [Execution_Asset_Execution](table/Execution_Asset_Execution.md), [File_Asset_Type](table/File_Asset_Type.md), [File_Execution](table/File_Execution.md)

**Asset** — [Execution_Metadata](table/Execution_Metadata.md), [Execution_Asset](table/Execution_Asset.md), [File](table/File.md)

**Satellite** — [Directory_Dataset](table/Directory_Dataset.md)

## Patterns

Cross-cutting concepts behind the fixed tables — the runtime-created table shapes and the vocabulary mechanism:

- [Asset table shape](pattern/asset-table.md) — `create_asset` mints domain asset tables.
- [Feature table shape](pattern/feature-table.md) — `create_feature` mints `Execution_{Target}_{Feature}` tables.
- [Controlled vocabulary](pattern/vocabulary.md) — how vocabularies type the abstractions; user-extensible vs system-managed; `add_term` vs `create_vocabulary`.

## Foreign-key graph (shape)

- `Execution` → `Workflow` (every execution runs a workflow); `Execution.Status` → `Execution_Status`.
- `Dataset.Version` → `Dataset_Version` (current version); `Dataset_Version.Dataset` → `Dataset` (each version belongs to one dataset).
- **Output-dataset provenance:** `Dataset_Version.Execution` → `Execution` (the run that produced the version).
- **Input-dataset edge:** `Dataset_Execution` links `Dataset` ↔ `Execution` (consumed), optionally pinning `Dataset_Version`.
- **Asset provenance:** each `{Asset}_Execution` association (`Execution_Metadata_Execution`, `Execution_Asset_Execution`, `File_Execution`) links the asset ↔ `Execution` with an `Asset_Role` (Input/Output).
- **Tagging:** `Dataset_Dataset_Type`, `Workflow_Workflow_Type`, and each `{Asset}_Asset_Type` link an entity to its vocabulary terms.
- **Self-nesting:** `Dataset_Dataset` (parent ↔ nested dataset), `Execution_Execution` (parent ↔ nested execution).

## Five abstractions → backing tables

| Abstraction | Backing tables |
|---|---|
| **Dataset** | `Dataset`, `Dataset_Version`, `Dataset_Type`/`Dataset_Dataset_Type`, `Dataset_Dataset`, `Dataset_Execution`, `Dataset_File`, `Directory_Dataset` |
| **Workflow** | `Workflow`, `Workflow_Type`/`Workflow_Workflow_Type` |
| **Execution** | `Execution`, `Execution_Status`, `Execution_Execution` |
| **Feature** | runtime `Execution_{Target}_{Feature}` tables + the `Feature_Name` registry (see the pattern) |
| **Asset** | built-in `Execution_Metadata`, `Execution_Asset`, `File` + their `*_Asset_Type`/`*_Execution` associations; domain asset tables via `create_asset` (see the pattern) |
