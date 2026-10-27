# deriva-ml ML schema reference

<!-- Maintainers: generated from the deriva-ml v1.53.0 schema; re-check against the
library when the schema changes. -->

Reference for the **fixed `deriva-ml` (ML) schema**: every table, its foreign keys,
and the runtime-created table patterns. Each table is a `## <Table>` section
named exactly after the table, so `grep -n '^## Dataset_Version'` jumps to it. For a
live diagram of a specific catalog, ask the user to run `/deriva-ml:browse-erd`.

> **`deriva-ml` schema vs domain schema.** These 26 tables are the fixed
> `deriva-ml` (ML) schema behind datasets, workflows, executions, features, and the built-in vocabularies — library-managed. Your
> project's own tables (`Subject`, `Image`, …) live in a separate **domain
> schema** named after the project; runtime-created asset and feature tables
> land there too (see the patterns below).

## Contents

- [Foreign-key graph](#foreign-key-graph-shape)
- [ML-schema entities → backing tables](#ml-schema-entities--backing-tables)
- Tables
  - **Core** — [Dataset](#dataset), [Dataset_Version](#dataset_version), [Workflow](#workflow), [Execution](#execution)
  - **Vocabulary** — [Dataset_Type](#dataset_type), [Workflow_Type](#workflow_type), [Execution_Status](#execution_status), [Asset_Type](#asset_type), [Asset_Role](#asset_role), [Feature_Name](#feature_name)
  - **Association** — [Dataset_Dataset_Type](#dataset_dataset_type), [Dataset_Dataset](#dataset_dataset), [Dataset_Execution](#dataset_execution), [Dataset_File](#dataset_file), [Workflow_Workflow_Type](#workflow_workflow_type), [Execution_Execution](#execution_execution), [Execution_Metadata_Asset_Type](#execution_metadata_asset_type), [Execution_Metadata_Execution](#execution_metadata_execution), [Execution_Asset_Asset_Type](#execution_asset_asset_type), [Execution_Asset_Execution](#execution_asset_execution), [File_Asset_Type](#file_asset_type), [File_Execution](#file_execution)
  - **Asset** — [Execution_Metadata](#execution_metadata), [Execution_Asset](#execution_asset), [File](#file)
  - **Satellite** — [Directory_Dataset](#directory_dataset)
- Patterns — [asset table shape](#pattern-asset-table-shape), [feature table shape](#pattern-feature-table-shape), [controlled vocabulary](#pattern-controlled-vocabulary)

## Foreign-key graph (shape)

- `Execution` → `Workflow` (every execution runs a workflow); `Execution.Status` → `Execution_Status`.
- `Dataset.Version` → `Dataset_Version` (current version); `Dataset_Version.Dataset` → `Dataset` (each version belongs to one dataset).
- **Output-dataset provenance:** `Dataset_Version.Execution` → `Execution` (the run that produced the version).
- **Input-dataset edge:** `Dataset_Execution` links `Dataset` ↔ `Execution` (consumed), optionally pinning `Dataset_Version`.
- **Asset provenance:** each `{Asset}_Execution` association (`Execution_Metadata_Execution`, `Execution_Asset_Execution`, `File_Execution`) links the asset ↔ `Execution` with an `Asset_Role` (Input/Output).
- **Tagging:** `Dataset_Dataset_Type`, `Workflow_Workflow_Type`, and each `{Asset}_Asset_Type` link an entity to its vocabulary terms.
- **Self-nesting:** `Dataset_Dataset` (parent ↔ nested dataset), `Execution_Execution` (parent ↔ nested execution).

## ML-schema entities → backing tables

| Abstraction | Backing tables |
|---|---|
| **Dataset** | `Dataset`, `Dataset_Version`, `Dataset_Type`/`Dataset_Dataset_Type`, `Dataset_Dataset`, `Dataset_Execution`, `Dataset_File`, `Directory_Dataset` |
| **Workflow** | `Workflow`, `Workflow_Type`/`Workflow_Workflow_Type` |
| **Execution** | `Execution`, `Execution_Status`, `Execution_Execution` |
| **Feature** | runtime `Execution_{Target}_{Feature}` tables + the `Feature_Name` registry (see the patterns below) |
| **Asset** | built-in `Execution_Metadata`, `Execution_Asset`, `File` + their `*_Asset_Type`/`*_Execution` associations; domain asset tables via `create_asset` (see the patterns below) |

## Dataset

*Core table.*

A **versioned collection** of catalog rows (assets, files, nested datasets) that
an execution consumed or produced. Soft-deletable. The backing table of the
DerivaML **Dataset** abstraction; its version history lives in
[Dataset_Version](#dataset_version).

Datasets are typed via [Dataset_Dataset_Type](#dataset_dataset_type), may
contain nested datasets via [Dataset_Dataset](#dataset_dataset), and link to
their input executions via [Dataset_Execution](#dataset_execution). Files in
a dataset are tracked through [Dataset_File](#dataset_file).

### Foreign Keys

- `Version` → [Dataset_Version](#dataset_version) — points at this dataset's
  **current** version row.

### Notable columns

- `Description` (markdown) — human-readable purpose.
- `Deleted` (boolean) — soft-delete flag. When `true`, the dataset is hidden
  from default listings but retained so existing execution provenance and
  citations remain resolvable.
- `Version` — FK to the current `Dataset_Version`.

## Dataset_Version

*Core table.*

Tracks the version history of a [Dataset](#dataset). Each row pins a
`(Dataset, Version)` pair, optionally with a catalog `Snapshot` for released
versions and a `Minid` URL for the materialized BDBag. The **current** version
of a dataset is selected by the outbound FK `Dataset.Version` pointing here.

Output-dataset provenance lives in this table: the `Execution` column records
which execution *produced* a given version. Contrast with
[Dataset_Execution](#dataset_execution), which records which executions
*consumed* a dataset.

### Foreign Keys

- `Dataset` → [Dataset](#dataset) — the dataset this version belongs to.
- `Execution` → [Execution](#execution) — the execution that produced this
  version (nullable: `NULL` for the initial release row created at dataset
  creation time, which has no producing execution).

### Notable columns

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

## Workflow

*Core table.*

A **versioned reference to the code** that knows how to run an ML step. Workflows
are deduplicated: `create_workflow` reuses an existing row whose `URL` *or*
`Checksum` (the git hash of the script file's contents) matches. Two executions
that share a Workflow row ran the same entry-script file — but not necessarily
the same commit of the rest of the repository, and the row's `URL` / `Version`
record its *first* registration. The commit a particular run used is in that
execution's `configuration.json` (`Execution_Metadata`).

Each [Execution](#execution) links back to exactly one Workflow row, making
the producing code recoverable for any result in the catalog. Workflows are
typed via the [Workflow_Workflow_Type](#workflow_workflow_type) association
(`Training`, `Prediction`, `Analysis`, ...).

Workflow rows are written by the DerivaML library during execution setup; they
are not intended for direct manual creation.

### Foreign Keys

This is a system-managed table. It has no outbound foreign keys to other
deriva-ml tables.

### Notable columns

- `Name` — short human-readable label used in execution listings and citations;
  not required to be unique.
- `Description` (markdown) — longer description of what the workflow does, what
  inputs it expects, and what outputs it produces.
- `URL` — location of the workflow code (typically a GitHub URL pinned to a
  specific commit hash, or a notebook URL). One half of the content address.
- `Checksum` — git commit hash (or other content hash) of the code at `URL`.
  Together with `URL` this uniquely identifies the executable code.
- `Version` — semantic version string of the workflow (e.g. `1.2.0`).
  Independent from `Checksum`; used for human-readable release tracking when
  the workflow code is itself published as a versioned package.

## Execution

*Core table.*

One **run of a [Workflow](#workflow)** against specific input Datasets,
producing output Datasets, Features, and Assets. Carries the execution state
machine (`Status`) and a timing breakdown across three lifecycle phases
(`Download_Duration`, `Execution_Duration`, `Upload_Duration`).

The backing table of the DerivaML **Execution** abstraction. Provenance edges
connect an Execution to its inputs (via `Dataset_Execution`) and outputs (via
`Dataset_Version.Execution`, `Execution_Asset_Execution`,
`Execution_Metadata_Execution`). Nested (child) executions are tracked in
[Execution_Execution](#execution_execution).

### Foreign Keys

- `Workflow` → [Workflow](#workflow) — the versioned code that ran this
  execution (deduplicated by URL or script checksum; the run's exact commit is in its `configuration.json`).
- `Status` → [Execution_Status](#execution_status) — current state in the
  execution state machine.

### Notable columns

- `Description` (markdown) — human-readable purpose, hyperparameters worth
  calling out, or anything a reader scanning an execution list should know.
- `Status_Detail` — free-form context for the current Status: typically the
  most recent stage message, error text on `Failed`, or a progress indicator
  on long-running phases.
- `Execution_Duration` — ISO 8601 duration string for the algorithm phase
  (inside the `with ml.create_execution()` block, excluding download and
  upload).
- `Download_Duration` — ISO 8601 duration string for the initialization phase
  (downloading input datasets and assets).
- `Upload_Duration` — ISO 8601 duration string for the commit phase (writing
  output bags, uploading assets to Hatrac, finalizing catalog rows).

## Dataset_Type

*Vocabulary table.*

Controlled vocabulary classifying datasets by their role in an ML pipeline.
Tags are assigned to datasets via the [Dataset_Dataset_Type](#dataset_dataset_type)
association table — a dataset can carry multiple types simultaneously (for
example `Training` + `Labeled`).

The three-axis framing (completeness, split role, label status) that gives
these terms their structure is documented in
`/deriva-ml:dataset-lifecycle`.

### Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

### Seeded terms

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

## Workflow_Type

*Vocabulary table.*

Controlled vocabulary classifying workflows by their **role in an ML pipeline**.
Tags are assigned to workflows via the
[Workflow_Workflow_Type](#workflow_workflow_type) association table — a
workflow can carry multiple types simultaneously (for example `Training` +
`Feature_Creation`).

### Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

### Seeded terms

Nine terms are seeded at schema initialization:

| Name | Description |
|------|-------------|
| `Training` | Model training and fine-tuning workflows. |
| `Testing` | Workflows that evaluate model performance on held-out data, computing metrics such as accuracy, AUC, confusion matrices, and per-class statistics. |
| `Prediction` | Workflows that apply a trained model to new data to generate predictions, probability scores, or classification labels. |
| `Feature_Creation` | Workflows that extract or engineer features from raw data, producing structured feature values linked to source records. |
| `Visualization` | Workflows that produce visual analyses of data or model results, including plots, charts, and summary dashboards. |
| `Analysis` | Computational analysis workflows that combine and analyze data from multiple sources without training a model. |
| `Ingest` | Workflows that load external data into the catalog, including file upload, record creation, and initial metadata population. |
| `Data_Cleaning` | Workflows that clean and preprocess raw data, including standardizing formats, handling missing values, and filtering invalid records. |
| `Dataset_Management` | Workflows that create, split, version, or manage datasets. |

Domain-specific workflow categories belong in user vocabularies, not here.

## Execution_Status

*Vocabulary table.*

Controlled vocabulary describing the **lifecycle state** of an
[Execution](#execution). Terms are managed by the execution state machine
and used as the FK target for `Execution.Status`.

For the full state-machine transitions and lifecycle semantics, see
`/deriva-ml:execution-lifecycle`.

### Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

### Seeded terms

Seven terms are seeded at schema initialization:

| Name | Description |
|------|-------------|
| `Created` | Execution row has been created; work has not started. |
| `Running` | Execution algorithm is actively running. |
| `Stopped` | Algorithm finished successfully; output assets not yet uploaded. |
| `Pending_Upload` | Algorithm succeeded; asset upload to the catalog is in progress. |
| `Uploaded` | Execution ran to success and all outputs are persisted to the catalog. |
| `Failed` | Execution encountered an unrecoverable error. |
| `Aborted` | Execution was canceled by the user before reaching a terminal state. |

Do not extend this vocabulary without coordinating with the deriva-ml execution
lifecycle — additional states require matching state-machine logic in the
library.

## Asset_Type

*Vocabulary table.*

Controlled vocabulary classifying **assets by purpose**. Terms are assigned to
assets via the `{Asset}_Asset_Type` association tables
([Execution_Asset_Asset_Type](#execution_asset_asset_type),
[Execution_Metadata_Asset_Type](#execution_metadata_asset_type),
[File_Asset_Type](#file_asset_type)) — an asset can carry multiple types
simultaneously (for example `Model_File` + `Output_File`).

Every domain-specific asset table created via `create_asset_table` also wires
its own `{Asset}_Asset_Type` association back to this vocabulary.

### Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

### Seeded terms

Twelve terms are seeded at schema initialization:

| Name | Description |
|------|-------------|
| `Execution_Config` | Configuration File for execution metadata |
| `Runtime_Env` | Information about the runtime environment |
| `Hydra_Config` | Hydra YAML configuration file (config.yaml, overrides.yaml, hydra.yaml) |
| `Deriva_Config` | DerivaML execution configuration (configuration.json with datasets, assets, workflow) |
| `Metrics_File` | Training-metric log file (typically JSONL, one record per evaluation point — epoch, step, or eval cycle). |
| `Execution_Metadata` | Information about the execution environment |
| `Execution_Asset` | A file generated by an execution |
| `File` | A file that is not managed by Hatrac |
| `Input_File` | A file input to an execution. |
| `Output_File` | A file output from an execution. |
| `Model_File` | The ML model. |
| `Notebook_Output` | A Jupyter notebook with output cells filled from an execution. |

Domain-specific asset categories belong in user vocabularies, not here.

## Asset_Role

*Vocabulary table.*

Controlled vocabulary distinguishing **input from output direction** on every
`{Asset}_Execution` association row. When an asset is linked to an execution,
the `Asset_Role` term records whether the asset flowed into the execution
(`Input`) or was produced by it (`Output`).

The role is carried on all three built-in asset-execution association tables
([Execution_Asset_Execution](#execution_asset_execution),
[Execution_Metadata_Execution](#execution_metadata_execution),
[File_Execution](#file_execution)) and on any domain-specific asset-execution
associations created via `create_asset_table`.

### Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

### Seeded terms

Two terms are seeded at schema initialization:

| Name | Description |
|------|-------------|
| `Input` | Asset used for input of an execution. |
| `Output` | Asset used for output of an execution. |

## Feature_Name

*Vocabulary table.*

Registry of **feature names** for the catalog. Every feature defined on a
target table — via `create_feature` — adds a term here. The vocabulary ensures
that the feature name space is audited and searchable rather than free-form
text scattered across individual feature tables.

Every feature table (`Execution_{Target}_{Feature}`) carries a FK to a
`Feature_Name` term. For the feature-table shape and the full
`create_feature` workflow, see `/deriva-ml:create-feature`.

### Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

### Seeded terms

No terms are seeded at schema initialization. Terms are added dynamically:
each call to `create_feature` registers a new name in this vocabulary as part
of creating the corresponding feature table. The term set therefore reflects the
feature definitions installed in a given catalog.

## Dataset_Dataset_Type

*Association table.*

Association table linking [Dataset](#dataset) ↔ [Dataset_Type](#dataset_type).
A dataset can carry multiple types simultaneously (for example `Training` +
`Labeled`); a type can apply to many datasets.

### Foreign Keys

- `Dataset` → [Dataset](#dataset) — the dataset being tagged.
- `Dataset_Type` → [Dataset_Type](#dataset_type) — the vocabulary term
  assigned to the dataset.

### Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns `RID`, `RCT`, `RMT`, `RCB`, `RMB`) it carries no additional
data columns.

## Dataset_Dataset

*Association table.*

Self-referential association on [Dataset](#dataset) expressing dataset
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

### Foreign Keys

Both columns reference the same table:

- `Dataset` → [Dataset](#dataset) — the parent (containing) dataset.
- `Nested_Dataset` → [Dataset](#dataset) — the member (contained) dataset.

### Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.

## Dataset_Execution

*Association table.*

Association table recording that an [Execution](#execution) *consumed* a
[Dataset](#dataset) as input. One row per (dataset, execution) input pair.
An optional `Dataset_Version` FK pins the exact version that was consumed.

This is the **input** edge. The **output** edge — which execution *produced* a
dataset version — lives in [Dataset_Version](#dataset_version) via the
`Execution` column on that table (not here).

### Foreign Keys

- `Dataset` → [Dataset](#dataset) — the dataset consumed as input.
- `Execution` → [Execution](#execution) — the execution that consumed it.
- `Dataset_Version` → [Dataset_Version](#dataset_version) — the specific
  version consumed (nullable: `NULL` when the consumed version was not
  recorded).

### Notable columns

- `Dataset_Version` — nullable FK pinning the exact consumed version. When
  present, provides precise version-level provenance for inputs.

## Dataset_File

*Association table.*

Association table linking [Dataset](#dataset) ↔ [File](#file). Records
that a file is a member of a dataset. A file can belong to multiple datasets;
a dataset can contain multiple files.

This table is populated by the `add_files` ingestion path when files are
registered into a dataset.

### Foreign Keys

- `Dataset` → [Dataset](#dataset) — the dataset the file belongs to.
- `File` → [File](#file) — the file that is a member of the dataset.

### Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.

## Workflow_Workflow_Type

*Association table.*

Many-to-many association between [Workflow](#workflow) and
[Workflow_Type](#workflow_type). A workflow can carry multiple types
simultaneously (for example `Training` + `Feature_Creation`).

### Foreign Keys

Both columns reference tables in this cluster:

- `Workflow` → [Workflow](#workflow) — the workflow being tagged.
- `Workflow_Type` → [Workflow_Type](#workflow_type) — the vocabulary term
  applied to that workflow.

### Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.

## Execution_Execution

*Association table.*

Self-referential association on [Execution](#execution) expressing execution
nesting. The `Execution` column is the **parent** (typically a sweep or
multirun controller); `Nested_Execution` is one of its **children**
(an individual run within that sweep).

`Sequence` optionally orders children within a parent for sequential runs; a
`NULL` value indicates parallel siblings with no defined order.

### Foreign Keys

Both columns reference the same table:

- `Execution` → [Execution](#execution) — the parent (containing) execution.
- `Nested_Execution` → [Execution](#execution) — the child (nested) execution.

### Notable columns

- `Sequence` (int, nullable) — ordinal position of this child within its
  parent. `NULL` means the child is one of a set of parallel siblings with
  no defined ordering.

## Execution_Metadata_Asset_Type

*Association table.*

Many-to-many association between [Execution_Metadata](#execution_metadata)
and [Asset_Type](#asset_type). Each row tags one metadata file with one
vocabulary term (e.g. `Hydra_Config`, `Deriva_Config`, `Runtime_Env`). A
single metadata file can carry multiple types.

Created automatically by `create_asset_table` alongside the
[Execution_Metadata](#execution_metadata) table.

### Foreign Keys

Both columns reference tables in this cluster:

- `Execution_Metadata` → [Execution_Metadata](#execution_metadata) — the
  metadata file being tagged.
- `Asset_Type` → [Asset_Type](#asset_type) — the vocabulary term applied to
  that file.

### Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.

## Execution_Metadata_Execution

*Association table.*

Many-to-many association between [Execution_Metadata](#execution_metadata)
and [Execution](#execution). Each row records that a metadata file was an
input to or output of a specific execution. The `Asset_Role` column carries the
direction (`Input` or `Output`) as a FK to [Asset_Role](#asset_role).

Created automatically by `create_asset_table` alongside the
[Execution_Metadata](#execution_metadata) table. The `Asset_Role` FK is
added via `create_reference` on the newly-created association table.

In practice, metadata files are almost always `Output` — the DerivaML runtime
uploads configs and runtime-env info at execution start, attributing them to
the running execution. The `Input` role is available for workflows that consume
a prior execution's metadata files.

### Foreign Keys

- `Execution_Metadata` → [Execution_Metadata](#execution_metadata) — the
  metadata file involved in this association.
- `Execution` → [Execution](#execution) — the execution it was input to or
  output from.
- `Asset_Role` → [Asset_Role](#asset_role) — direction of the association:
  `Input` or `Output`.

### Notable columns

Beyond the three FK columns (and ERMrest system columns) this table carries no
additional data columns.

## Execution_Asset_Asset_Type

*Association table.*

Many-to-many association between [Execution_Asset](#execution_asset) and
[Asset_Type](#asset_type). Each row tags one data asset file with one
vocabulary term (e.g. `Model_File`, `Output_File`, `Metrics_File`,
`Notebook_Output`). A single asset can carry multiple types.

Created automatically by `create_asset_table` alongside the
[Execution_Asset](#execution_asset) table.

### Foreign Keys

Both columns reference tables in this cluster:

- `Execution_Asset` → [Execution_Asset](#execution_asset) — the data asset
  file being tagged.
- `Asset_Type` → [Asset_Type](#asset_type) — the vocabulary term applied to
  that file.

### Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.

## Execution_Asset_Execution

*Association table.*

Many-to-many association between [Execution_Asset](#execution_asset) and
[Execution](#execution). Each row records that a data asset file was an
input to or output of a specific execution. The `Asset_Role` column carries
the direction (`Input` or `Output`) as a FK to [Asset_Role](#asset_role).

Created automatically by `create_asset_table` alongside the
[Execution_Asset](#execution_asset) table. The `Asset_Role` FK is added via
`create_reference` on the newly-created association table.

### Foreign Keys

- `Execution_Asset` → [Execution_Asset](#execution_asset) — the data asset
  file involved in this association.
- `Execution` → [Execution](#execution) — the execution it was input to or
  output from.
- `Asset_Role` → [Asset_Role](#asset_role) — direction of the association:
  `Input` or `Output`.

### Notable columns

Beyond the three FK columns (and ERMrest system columns) this table carries no
additional data columns.

## File_Asset_Type

*Association table.*

Many-to-many association between [File](#file) and [Asset_Type](#asset_type).
Each row tags one file with one vocabulary term (e.g. `File`, `Input_File`,
`Output_File`). A single file can carry multiple types.

Created automatically by `create_asset_table` alongside the [File](#file)
table.

### Foreign Keys

Both columns reference tables in this cluster:

- `File` → [File](#file) — the file being tagged.
- `Asset_Type` → [Asset_Type](#asset_type) — the vocabulary term applied to
  that file.

### Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.

## File_Execution

*Association table.*

Many-to-many association between [File](#file) and [Execution](#execution).
Each row records that a file (a by-reference external URL) was an input to or
output of a specific execution. The `Asset_Role` column carries the direction
(`Input` or `Output`) as a FK to [Asset_Role](#asset_role).

Created automatically by `create_asset_table` alongside the [File](#file)
table. The `Asset_Role` FK is added via `create_reference` on the
newly-created association table.

### Foreign Keys

- `File` → [File](#file) — the file involved in this association.
- `Execution` → [Execution](#execution) — the execution it was input to or
  output from.
- `Asset_Role` → [Asset_Role](#asset_role) — direction of the association:
  `Input` or `Output`.

### Notable columns

Beyond the three FK columns (and ERMrest system columns) this table carries no
additional data columns.

## Execution_Metadata

*Asset table.*

Asset table for files that describe an **execution's environment and
configuration** — Hydra YAML configs, runtime environment info, and the
DerivaML execution configuration JSON. Bytes are stored in Hatrac via the
upload template `/hatrac/metadata/{{MD5}}.{{Filename}}`.

Execution_Metadata is one of three built-in asset tables created by
`create_asset_table`. It is distinguished from
[Execution_Asset](#execution_asset) by *purpose* (environment / config vs.
data outputs), not by file shape — both tables have the same standard column
set.

The asset-table row shape and the bulk I/O operations (upload, download,
attach to execution) are documented in [Pattern: asset table shape](#pattern-asset-table-shape) and covered
by the `/deriva-ml:work-with-assets` skill.

### Foreign Keys

This table carries no outbound foreign keys itself. Associations to
[Asset_Type](#asset_type) and [Execution](#execution) are expressed
through the sibling tables [Execution_Metadata_Asset_Type](#execution_metadata_asset_type)
and [Execution_Metadata_Execution](#execution_metadata_execution).

### Notable columns

Standard asset shape (from `AssetTableDef`):

- `URL` (ermrest_uri, not null) — Hatrac object URL; populated by the Chaise
  upload UI using the template `/hatrac/metadata/{{MD5}}.{{Filename}}`.
- `Filename` (text) — original filename at upload time.
- `Length` (int8) — file size in bytes.
- `MD5` (text) — MD5 checksum of the file content.
- `Description` (markdown) — human-readable description of what this metadata
  file captures.

## Execution_Asset

*Asset table.*

Asset table for files that are **data outputs or inputs of an execution** —
trained model weights, prediction CSVs, evaluation plots, notebook outputs.
Bytes are stored in Hatrac via the upload template
`/hatrac/metadata/{{MD5}}.{{Filename}}`.

Execution_Asset is one of three built-in asset tables created by
`create_asset_table`. It is distinguished from
[Execution_Metadata](#execution_metadata) by *purpose* (data results vs.
environment/config), not by file shape — both tables have the same standard
column set.

The asset-table row shape and the bulk I/O operations (upload, download,
attach to execution) are documented in [Pattern: asset table shape](#pattern-asset-table-shape) and covered
by the `/deriva-ml:work-with-assets` skill.

### Foreign Keys

This table carries no outbound foreign keys itself. Associations to
[Asset_Type](#asset_type) and [Execution](#execution) are expressed
through the sibling tables [Execution_Asset_Asset_Type](#execution_asset_asset_type)
and [Execution_Asset_Execution](#execution_asset_execution).

### Notable columns

Standard asset shape (from `AssetTableDef`):

- `URL` (ermrest_uri, not null) — Hatrac object URL; populated by the Chaise
  upload UI using the template `/hatrac/metadata/{{MD5}}.{{Filename}}`.
- `Filename` (text) — original filename at upload time.
- `Length` (int8) — file size in bytes.
- `MD5` (text) — MD5 checksum of the file content.
- `Description` (markdown) — human-readable description of what this asset
  file represents.

## File

*Asset table.*

Asset table for files that **live outside Hatrac** — external or
locally-staged URLs the catalog references but does not host. Created by
`create_asset_table` with `use_hatrac=False`, which omits the Hatrac upload
template from the `URL` column: `URL` is a plain `ermrest_uri` string rather
than a wired upload target.

This is the table populated by `add_files` when ingesting a source directory.
Each row represents one file in the registered directory tree, with `URL`
carrying the path or external URL to the bytes and `MD5` / `Length` / `Filename`
carrying the standard provenance columns.

The row shape is identical to [Execution_Asset](#execution_asset) and
[Execution_Metadata](#execution_metadata) — the only difference is
the absence of the Hatrac upload template. File rows link into Datasets via
[Dataset_File](#dataset_file).

The asset-table row shape and the `add_files` ingest workflow are documented
in [Pattern: asset table shape](#pattern-asset-table-shape) and covered by the `/deriva-ml:work-with-assets`
skill.

### Foreign Keys

This table carries no outbound foreign keys itself. Associations to
[Asset_Type](#asset_type) and [Execution](#execution) are expressed
through the sibling tables [File_Asset_Type](#file_asset_type) and
[File_Execution](#file_execution). Membership in datasets is expressed
through [Dataset_File](#dataset_file).

### Notable columns

Standard asset shape (from `AssetTableDef`, `use_hatrac=False`):

- `URL` (ermrest_uri, not null) — plain URL to the file bytes (no Hatrac
  upload template). Points at bytes the catalog references but does not host.
- `Filename` (text) — original filename.
- `Length` (int8) — file size in bytes.
- `MD5` (text) — MD5 checksum of the file content.
- `Description` (markdown) — human-readable description of what this file
  represents.

## Directory_Dataset

*Satellite table.*

Satellite table recording the source folder that an `add_files`-created
directory dataset represents, as a path relative to the ingest root. One row
per directory dataset; absent for datasets not built from a directory tree.

Created automatically by `add_files` when ingesting a source directory: the
ingest root itself gets `Path = "."`, and each sub-folder gets a
`Path` relative to that root.

### Foreign Keys

- `Dataset` → [Dataset](#dataset) — the directory dataset this row describes.
  Also the **unique key** of this table — exactly one `Directory_Dataset` row
  may exist per dataset.

### Notable columns

- `Dataset` (text) — FK to the directory [Dataset](#dataset); also the unique
  key (one satellite row per dataset).
- `Path` (text) — source directory this dataset represents, relative to the
  ingest root. The ingest root stores `"."`.

## Pattern: asset table shape

Every DerivaML **asset table** has the same shape: the five standard columns
(`Filename`, `URL`, `Length`, `MD5`, `Description`) plus two auto-created
association tables — `{Name}_Asset_Type` (tags the asset with
[Asset_Type](#asset_type) terms) and `{Name}_Execution` (links it to
an [Execution](#execution) with an [Asset_Role](#asset_role)
of Input or Output).

The `deriva-ml` schema ships **three built-in** asset tables:
[Execution_Metadata](#execution_metadata),
[Execution_Asset](#execution_asset), and
[File](#file) (by-reference). **Domain asset tables** (`Image`,
`Model_Weights`, …) are created at runtime by `create_asset` and live in your
**project's domain schema**, not in `deriva-ml`.

For the full column reference, the `create_asset_table` mechanics, and how to
work with assets, see **`/deriva-ml:work-with-assets`** (it owns this surface).

## Pattern: feature table shape

A DerivaML **feature** is stored in a runtime-created association table named
`Execution_{TargetTable}_{FeatureName}` — for example, an `Image_Classification`
feature on the `Image` table is stored in `Execution_Image_Image_Classification`.
`create_feature` mints one such table per `(target_table, feature_name)` pair and
registers the name in the [Feature_Name](#feature_name) vocabulary.

Every feature table carries these FKs: `Execution` →
[Execution](#execution), `{TargetTable}` → the annotated domain table,
and `Feature_Name` → [Feature_Name](#feature_name) — plus one column
per vocabulary term, asset, and metadata field the feature defines. **Discovery:**
any association table with both `Feature_Name` and `Execution` columns is a
feature table.

Feature tables live in the **domain schema** (alongside the target table), not in
`deriva-ml`. For the full column reference and how to create/populate features,
see **`/deriva-ml:create-feature`** (it owns this surface).

## Pattern: controlled vocabulary

A **controlled vocabulary** is a table of standardized terms (each with a `Name`,
`Description`, optional `Synonyms`, and a stable `{project}:{RID}` CURIE) that
*types* a DerivaML entity. Typing entities this way is what makes them findable,
filterable, and stable: a consumer dispatches on `Dataset_Type == "Training"`,
not on a name string, and the CURIE survives catalog clones. Adding a term is the
sanctioned way to introduce a new *kind* of thing — distinct from going around
the abstractions with raw inserts.

### The six fixed `deriva-ml` vocabulary tables

Split by who writes them:

- **User-extensible** (add terms with `add_term`): [Dataset_Type](#dataset_type),
  [Workflow_Type](#workflow_type), [Asset_Type](#asset_type).
- **System-managed** (populated by the machinery — do not extend):
  [Execution_Status](#execution_status) (the execution-state machine),
  [Asset_Role](#asset_role) (the upload/download machinery, Input/Output),
  [Feature_Name](#feature_name) (`create_feature` registers one term per feature).

### Extending vs creating

- **Add a term to an existing vocabulary** — the common case. Use the generic
  `add_term(schema="deriva-ml", table="<Vocab>", name=..., description=...)`. No
  deriva-ml-specific variant exists for adding a term; the generic tool is correct.
- **Create a brand-new vocabulary table** on a deriva-ml catalog — prefer the
  ML-aware `deriva_ml_create_vocabulary` over the generic `create_vocabulary`: it
  scopes the CURIE prefix to the project, defaults to the domain schema, and
  refreshes the Chaise navbar. Then `add_term` for each term.

### Built-in vs domain vocabularies

The six above live in the `deriva-ml` schema. Your own domain vocabularies
(`Sample_Type`, `Tissue_Type`, `Image_Quality`, …) live in the **project's domain
schema** — same physical shape, created via `deriva_ml_create_vocabulary`,
extended with `add_term` using your domain schema name.

For the term-management surface (add/lookup/synonyms, the generic
`create_vocabulary` for non-deriva-ml catalogs), see
`/deriva:manage-vocabulary` *(deriva-skills)*. For DerivaML-specific vocabulary
guidance, see `/deriva-ml:deriva-ml-context` ("Built-in DerivaML vocabularies").
