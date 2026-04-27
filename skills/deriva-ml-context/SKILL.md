---
name: deriva-ml-context
description: "ALWAYS load this context when the deriva-ml plugin is active. Establishes what DerivaML is (a reproducible-ML layer on top of Deriva catalogs), the five core abstractions (Dataset, Workflow, Execution, Feature, Asset), and the steering principle that DerivaML abstractions take precedence over raw Deriva catalog primitives whenever both are available. Triggers on: 'derivaml', 'deriva-ml', 'dataset', 'workflow', 'execution', 'feature', 'asset', 'experiment', 'training run', 'model', 'pipeline', 'reproducible', 'provenance', 'hydra-zen', 'configure-experiment'."
disable-model-invocation: false
---

# DerivaML Plugin Context

## What is DerivaML?

DerivaML is a **reproducible-ML layer built on top of Deriva catalogs**. It records the full provenance of every ML run — inputs, code versions, configurations, outputs, and intermediate artifacts — as first-class catalog entities so that experiments can be reproduced, audited, compared across users, and resumed across sessions.

The DerivaML stack:

- **`deriva-ml`** — the Python library; provides the `DerivaML` class, `Workflow`, `ExecutionConfiguration`, dataset / feature / asset APIs, and the `with ml.create_execution(config) as exe:` context manager pattern.
- **`deriva-ml-mcp`** — the MCP plugin loaded by `deriva-mcp-core`; exposes the `deriva_ml_*` MCP tools (e.g., `deriva_ml_create_dataset`, `deriva_ml_start_execution`, `deriva_ml_add_feature_value`) and the `deriva://catalog/{h}/{c}/ml/...` resource family.
- **`deriva-ml-skills`** — this Claude Code plugin; ~24 skills that drive the above two layers through Claude.

## The five core abstractions

These are the surface DerivaML adds on top of plain Deriva. Each is stored as one or more Deriva tables underneath, but **treat them as DerivaML domain objects, not as raw tables**.

| Abstraction | What it represents | Primary skill | Key MCP tools |
|---|---|---|---|
| **Dataset** | A versioned collection of catalog rows that an execution consumed or produced. Datasets have a type (`Dataset_Type` vocab), an element-type spec, a version history, and can be downloaded as bags. | `dataset-lifecycle` | `deriva_ml_create_dataset`, `deriva_ml_add_dataset_members`, `deriva_ml_increment_dataset_version`, `deriva_ml_cache_dataset` |
| **Workflow** | A versioned reference to the code (URL + git commit hash) that knows how to do a thing. A Workflow is content-addressed: same URL + same commit = same Workflow row. Workflows are typed (`Workflow_Type` vocab). | `route-run-workflows` → `new-model` / `configure-experiment` | `deriva_ml_create_workflow`, `deriva_ml_lookup_workflow_by_url` |
| **Execution** | One run of a Workflow against specific input Datasets, producing output Datasets / Features / Assets. Executions have a status (`Execution_Status_Type`), inputs / outputs links, and an active context manager that stages files in a working directory. | `execution-lifecycle` | `deriva_ml_create_execution`, `deriva_ml_start_execution`, `deriva_ml_stop_execution`, `deriva_ml_update_execution_status` |
| **Feature** | A typed value attached to a row of some target table (e.g., a per-image classification label produced by a run). Features link the value back to the producing Execution for provenance. | `create-feature` | `deriva_ml_create_feature`, `deriva_ml_add_feature_value` |
| **Asset** | A file uploaded to hatrac and recorded in the catalog with an Asset_Type and provenance link to its producing Execution. Assets are written to paths returned by `exe.asset_file_path()` and uploaded by `exe.upload_execution_outputs()`. | `work-with-assets` | `deriva_ml_create_asset_table`, `deriva_ml_add_asset_type`, `deriva_ml_add_asset_type_to_asset` |

## Steering principle: DerivaML abstractions take precedence

Datasets, Workflows, Executions, Features, and Asset_Type vocabularies are first-class DerivaML concepts. **In a deriva-ml-loaded catalog you must use the deriva-ml abstractions for them** — the dedicated MCP tools listed above and the deriva-ml Python API — NOT the raw `insert_records` / `update_record` / `get_record` core tools that plain Deriva exposes.

The raw tools bypass:

- **Business logic** — e.g., `add_dataset_members` validates RIDs against the dataset's element-type spec; raw inserts will let you add wrong-table rows that break the dataset on materialization.
- **FK validation across the Dataset / Workflow / Execution graph** — DerivaML enforces invariants (every Execution links to a Workflow, every output Dataset links to its producing Execution); raw inserts can create dangling references.
- **Provenance tracking** — each mutation links back to the active Execution; raw inserts have no Execution context.
- **Version management** — Datasets are versioned; `increment_dataset_version` creates a new snapshot. Raw inserts skip the version bump, leaving consumers pointed at stale data.
- **RAG re-indexing** — the `deriva_ml_*` tools fire surgical re-index hooks (v1.3) so freshly mutated rows are searchable on the next `rag_search`. Raw inserts do not.
- **Audit emission** — every `deriva_ml_*` mutation emits an audit event with the operation name, hostname, catalog, and result; raw inserts use the generic core audit which lacks DerivaML-specific context.

## Built-in DerivaML vocabularies — use the dedicated extender tools

DerivaML ships four built-in vocabularies. **In a deriva-ml-loaded catalog, extend them with the dedicated tools, not generic `add_term`:**

| Vocabulary | Use this tool | Not this |
|---|---|---|
| `Dataset_Type` | `deriva_ml_create_dataset_type_term` | `add_term` |
| `Workflow_Type` | `deriva_ml_add_workflow_type` | `add_term` |
| `Asset_Type` | `deriva_ml_add_asset_type` | `add_term` |
| `Execution_Status_Type` | (managed automatically by the execution-state machine) | `add_term` (don't extend manually) |

For all *other* vocabularies (your own domain vocabs like `Sample_Type`, `Tissue_Type`, `Image_Quality`), use the generic `add_term` documented in tier-1's `manage-vocabulary` skill.

## When to reach back to the raw catalog surface

The companion tier-1 `deriva` plugin remains active alongside this one. Use its skills for catalog objects that are **NOT** one of the five DerivaML domain concepts:

- **Custom domain tables** — `Subject`, `Sample`, `Image`, anything specific to your project's data model → `/deriva:create-table`, `/deriva:query-catalog-data`
- **Generic vocabularies** — anything that isn't `Dataset_Type` / `Workflow_Type` / `Asset_Type` / `Execution_Status_Type` → `/deriva:manage-vocabulary`
- **Schema introspection** — listing tables, browsing columns, reading the ERD → `/deriva:browse-erd`, `/deriva:query-catalog-data`
- **Display customization** — Chaise annotations on any table → `/deriva:customize-display`, `/deriva:use-annotation-builders`
- **Generic catalog errors** — auth, permissions, invalid RIDs, missing records, generic vocab term not found → `/deriva:troubleshoot-deriva-errors` (always check this first when an error doesn't smell execution-specific)
- **Version checks for the foundation** — `/deriva:check-deriva-versions` (tier-1) before `/deriva-ml:check-deriva-ml-versions` (tier-2)

## Pointers

DerivaML domain workflows (this plugin):

- `/deriva-ml:dataset-lifecycle` — Dataset creation, population, splitting, versioning, browsing, downloading
- `/deriva-ml:execution-lifecycle` — Pre-flight validation, running experiments, execution provenance
- `/deriva-ml:create-feature` — Features, labels, annotations, selectors
- `/deriva-ml:work-with-assets` — File assets — upload, download, provenance, types
- `/deriva-ml:configure-experiment` — DerivaML experiment project structure (Hydra-zen configs)
- `/deriva-ml:write-hydra-config` — Hydra-zen config files for experiments
- `/deriva-ml:new-model` — Scaffold a new model function
- `/deriva-ml:troubleshoot-execution` — Execution-lifecycle troubleshooting (asset paths, upload, stuck Running, version mismatch, missing feature)

Generic catalog operations (tier-1; install `deriva-skills`):

- `/deriva:troubleshoot-deriva-errors` — Generic catalog troubleshooting
- `/deriva:manage-vocabulary` — Generic vocabulary CRUD
- `/deriva:create-table` — Custom domain tables
- `/deriva:query-catalog-data` — Querying / browsing
