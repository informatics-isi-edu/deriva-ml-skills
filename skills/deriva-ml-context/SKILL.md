---
name: deriva-ml-context
description: "Core concepts of DerivaML and a map to its other skills. DerivaML is a reproducible-ML layer on a Deriva catalog. This skill defines its basic abstractions — Dataset (a versioned collection of assets and their metadata), Workflow (a defined process, code or human-performed), Execution (one run of a workflow, recording its inputs, parameters, and outputs), Feature (a set of values, vocabulary terms, or assets attached to a record — a label, a measurement, a mask — linked to the execution that produced it), Asset (a file in the object store described in the catalog), and controlled vocabularies — and the project's domain schema beside them, then routes each kind of work to the skill that owns it. It also carries two plugin-wide rules: use a deriva-ml surface over the plain deriva one when both exist, and never guess a fact that can be looked up. Use whenever the deriva-ml plugin is active and the work touches the project's data, datasets, models, experiments, or catalog."
when_to_use: "Load first, before the first DerivaML action or answer, and keep it for the whole session; task skills load on top of it. In a DerivaML project, everyday words — data, data set, labels, images, model, training run, results — refer to these abstractions, so load it even when DerivaML is not named."
---

<!--
SYNC: this skill mirrors `_CONCEPTS_GUIDE` in
`deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/prompts.py`. When the conceptual
core changes (the catalog organization, the inheritance rule, the
vocabulary-extension pattern), update both. See CLAUDE.md ("Cross-plugin and cross-repo
rules") for the convention. Inheritance-rule rationale: docs/adr/0001.
-->

# DerivaML Plugin Context

DerivaML is a **reproducible-ML layer built on top of Deriva catalogs**. It records
the full provenance of every ML run — inputs, code versions, configurations,
outputs — as first-class catalog entities, so experiments can be reproduced,
audited, compared, and resumed. This skill defines the model and the work done with it;
each task skill owns the details of its part. **Starting from nothing, or adopting
an existing catalog?** Load `/deriva-ml:start-project` — it orders the cold start.

## The model: an ML schema and a domain schema

A DerivaML catalog holds **metadata about a collection of assets** — the files
(images, scans, model weights, CSVs) kept in Deriva's object store, which is
called *hatrac* in URLs and tool names. Three terms fit together:

- The **data model** is the design: the entities, attributes, relationships, and
  vocabularies that describe the project's data.
- A **schema** is the data model realized in the catalog as tables, columns, and
  foreign keys. A DerivaML catalog has two: the ML schema and the domain schema.
- **Metadata** is the records stored in those tables — everything the catalog
  knows about the assets and how they were organized, labeled, and produced.

**The ML schema (`deriva-ml`)** is fixed and library-managed. It defines the
machinery of reproducible ML:

- **Dataset** — a versioned collection of assets and their associated metadata
  (records from both schemas); the unit an experiment consumes or produces. A
  released version can be downloaded as a **bag** (a BDBag: a self-describing,
  checksummed package of that version's metadata plus its asset files), which is
  materialized into the local cache for training and analysis.
- **Workflow** — a defined process that creates or transforms data, typed by
  `Workflow_Type`: either code (identified by its script URL and checksum) or a
  human-performed process such as manual annotation, curation, or data
  collection.
- **Execution** — one performance of a Workflow (a code run or a human session)
  with specific inputs: datasets, assets, and configuration parameters. It
  results in an execution record that captures the workflow, every input and
  parameter, and every output (datasets, feature values, assets).
- **Feature** — a set of values attached to a row of some table, linked to the
  Execution that produced it. Each value is a vocabulary term (a diagnosis, a
  quality grade), a plain value (a score, a measurement), or an asset (a
  segmentation mask, an embedding file), and one feature can combine several.
  A record can carry many values of the same feature — one per annotator or
  model run — told apart by their executions.
- **Controlled vocabularies** — tables of named terms with a shared meaning:
  system terms (`Execution_Status`), terms that classify entities
  (`Dataset_Type`), and domain terms such as diagnoses, often used as feature
  values.

**The domain schema** (named after the project) holds the project's own
abstractions — `Subject`, `Patient`, `Observation`, `Image`, … — plus the asset
tables, feature tables, and domain vocabularies created for the project.

**Assets** span both: each is a file in the object store plus a row in an asset table,
either a domain one (`Image`) or an ML-schema one for run outputs
(`Execution_Asset`, `Execution_Metadata`). Every asset carries an `Asset_Type`
and links to the Executions that produced or consumed it.

Provenance lives in the **execution record**: it names the workflow, the exact
dataset versions and assets consumed, and the parameters used, and every output
links back to it — so any feature or asset traces back to (specific process) ×
(specific versioned inputs).

Treat these as **DerivaML domain objects, not raw tables**. Status values,
versioning rules, deduplication, and tool calls for each entity live in its
owning skill († = only the user can run it; suggest the command):

| Entity | Owning skill |
|---|---|
| Dataset | `/deriva-ml:dataset-lifecycle` |
| Workflow | `/deriva-ml:new-model` (authoring), `/deriva-ml:configure-experiment` (wiring) |
| Execution | `/deriva-ml:execution-lifecycle` |
| Feature | `/deriva-ml:create-feature` |
| Asset | `/deriva-ml:work-with-assets` |
| Vocabularies | `/deriva:manage-vocabulary` † (finding, adding, and matching terms) |
| Domain tables | `/deriva:create-table` †; meanwhile the `create_table` MCP tool |

Table-by-table reference for the ML schema: `references/ml-schema.md`.

**Vocabularies — two rules.** Never add terms to the system-managed
vocabularies `Execution_Status`, `Asset_Role`, and `Feature_Name`; the machinery
fills them. On a deriva-ml catalog, create a new vocabulary with
`deriva_ml_create_vocabulary`, not core's `create_vocabulary`. The built-in
vocabularies, how to extend them, and the calls are in
`references/built-in-vocabularies.md`.

## The work: three activities

Work lives in **two durable places**:

- **The catalog** — the *what*: the authoritative record of what exists and what
  produced it.
- **The experiment repository** (a git repo, started from
  [`deriva-ml-model-template`](https://github.com/informatics-isi-edu/deriva-ml-model-template))
  — the *how* and *why*: model code, hydra-zen configs in `src/configs/` (Python,
  not YAML), design docs under `docs/design/{experiment,dataset,feature,model}/`,
  `Experiments.md`, and `tacit-knowledge.md`. Every execution of a code workflow
  records the code it ran (a `Workflow` row plus the exact commit in its
  `configuration.json`), so any result traces back to this repo.

DerivaML work falls into three activities, and every dataset, feature, model,
or experiment within them follows the same arc: **Specify** — write the design
doc (goal, requirements, validation criteria); **Build** — create, configure, or
run it; **Validate** — check the result against the design and record why
decisions were made.

1. **Define and evolve the data model** — domain tables, controlled
   vocabularies, feature definitions, and asset tables, realized in the domain
   schema. Before changing or deleting a table, column, vocabulary, dataset, or
   asset, the user runs `/deriva-ml:schema-evolution-impact` † — until they do,
   list what references the target yourself before acting.
2. **Manage data and datasets** — load files and records, group them into
   datasets, split, subsample, version, and download them.
3. **Create workflows and executions** — define the process (code, or a human
   procedure such as an annotation pass), configure it, run it with provenance,
   and evaluate the results. **Executions are authored in Python**: creating and
   running them, staging feature values, and committing output assets happen in
   committed scripts on the user's machine — including the execution that
   records a human-performed process. The `deriva_ml_*` MCP tools observe the
   catalog and mutate its state but never author executions, and the MCP server
   cannot see the user's filesystem (`/deriva-ml:using-deriva-mcp`).

## Routing: which skill owns each step

Users rarely name DerivaML. Map what they ask for to the step below, then load
its skill (prefix `/deriva-ml:` unless shown; † = only the user can run it, so
suggest the command). When two rows seem to fit, the rules after the table
decide.

| Step | What the user asks | Concept | Skill |
|---|---|---|---|
| Start | new project, adopt an existing catalog, "where do I start", data in hand but no repo or catalog yet | repo + catalog | `start-project` |
| Specify | write down what an experiment, dataset, feature, or model must show and how success is judged, before building it | design doc | `design-experiment` |
| Model the data | where a kind of record goes; a new table or column | domain schema | `/deriva:semantic-awareness` first (is there already a table for it?), then `/deriva:create-table` † (meanwhile the `create_table` MCP tool); new catalog `setup-ml-catalog` †; diagram `browse-erd` † |
| | a new category or term | vocabulary | `/deriva:semantic-awareness` first (does the term exist under another name?), then `/deriva:manage-vocabulary` † (meanwhile `add_term`) |
| | rename or delete anything | — | `schema-evolution-impact` † |
| Record values on records | labels, grades, annotations, measurements, masks; a second annotator | Feature | `create-feature` (define the feature; values are written inside an execution) |
| Load files | files of a kind the catalog already has — one file or a folder of new scans into an existing asset table; an asset table | Asset | `work-with-assets` |
| | in a project whose repo and catalog exist, a new collection of raw data, often files plus a spreadsheet of labels or metadata | Asset, Feature, Dataset | `dataset-lifecycle` (routes to the `setup-ml-catalog` † loader) |
| Curate | train/test sets, split by subject, subsample, filter, freeze a version, download | Dataset | `dataset-lifecycle` |
| Prepare | bag → DataFrame, ImageFolder, framework loaders; pick among annotators | Dataset bag | `ml-data-engineering` |
| Build | model code; wrapping an existing training script | Workflow | `new-model` |
| | a notebook that records what it did | Workflow, Execution | `run-notebook` |
| | a script for bulk reads or writes past MCP's limits | Execution | `generate-scripts` |
| Configure | what the project can run: config groups, experiment presets (a quick-test variant), defining a sweep | config | `configure-experiment` |
| | writing or checking one config file: point an experiment at a dataset or asset version, add a parameter, bootstrap configs from a catalog, validate them against it | config | `write-hydra-config` |
| Run | train, dry run, launch a sweep, save weights and predictions, the dirty-tree gate, record a human annotation or review pass (the session is the execution; the labels it sets are feature values) | Execution | `execution-lifecycle` |
| Fix a run | crash, hang, stuck status, partial upload, surprising output; version checks | Execution | `troubleshoot-execution` |
| Look up a result | what a RID is; browse the labels or predictions on records; the misclassified images; what produced an artifact or which inputs a run used, to *see* it | Feature, Asset, execution record | `explore-results` |
| Evaluate | score a run: confusion matrix, per-class metrics, judge it against its design; rank runs, did the change help, regressions, aggregate a sweep; which runs used a dataset or label version | Execution | `compare-model-runs` |
| Iterate | a hypothesis to test ("does augmentation improve recall?"), what to try next, is the result conclusive | experiment cycle | `experiment-lifecycle` (a new, unproven pipeline: `model-development-workflow`) |
| Reproduce | the exact commit, config, and dataset versions behind a result, then re-run it | execution record | `compare-model-runs` (provenance walk), then `execution-lifecycle` |
| Rationale | why X was chosen, have we tried Y, a status write-up | tacit knowledge | `capture-tacit-knowledge` — it also fires alongside every other row, right after a decision is made |
| Local disk | cached bags, old downloads, execution directories | local cache | `manage-deriva-storage` |

Two rules settle the rows that touch the same words:

- **Predictions** are produced in a run (`execution-lifecycle`). Store each
  record's prediction as a **feature value** when it will be queried, filtered,
  or compared per record (define the feature first with `create-feature`); store
  a whole-run file — a prediction CSV with class probabilities, weights — as an
  **execution asset**. Many projects do both.
- **Provenance:** to *see* where something came from, `explore-results`; to
  *reproduce* it or to explain a metric, `compare-model-runs`.

> **"Experiment" has three meanings.** (1) an *experiment cycle* — one turn of the
> experiment lifecycle; (2) an *experiment config preset* — a named entry in
> `configs/experiments.py`; (3) the *experiment repository* itself. Keep them
> distinct.

## The rule: inheritance with override

The deriva-ml plugin **extends** the deriva plugin. Everything that applies in a
Deriva catalog applies in a deriva-ml catalog by default. **Override:** if a
deriva-ml surface exists for an operation, use it instead of the deriva one, on all
three planes:

- **Skills:** `/deriva-ml:<skill>` over `/deriva:<skill>`.
- **MCP:** `deriva_ml_*` tools, prompts, and resources over the equivalent
  `deriva-mcp-core` ones.
- **Python:** `deriva-ml` objects and methods (`DerivaML`, `Dataset`, `Execution`,
  `exe.asset_file_path()`, …) over `deriva-py` (`ErmrestCatalog`, `PathBuilder`,
  raw entity access).

The test is mechanical: "is there a deriva-ml `<thing>` for this?" If yes, use it;
if no, use the deriva default.

The override lands hardest on the ML-schema entities and assets. Writing Dataset,
Workflow, Execution, Feature, or Asset rows with generic `insert_entities` /
`update_entities` / `delete_entities` bypasses validation, cross-graph FK
invariants, provenance links, dataset version flips, RAG re-indexing, and audit
events — details in `references/inheritance-rationale.md`.

## Never guess — ground truth is observable

DerivaML is reproducible only because every fact is recorded somewhere
authoritative. So: **never guess, invent, or assume a fact you could observe.** If
you don't know a RID, version, vocabulary term, column name, file path, config
value, or whether something exists — **look it up** in one of four places:

- **The catalog** — RIDs, entity records, vocabulary terms, schema, lineage.
- **The project repo** — config values, model code, design docs,
  `tacit-knowledge.md`, `git`.
- **The working directory** — what the current execution staged.
- **The local cache** — bags and assets downloaded on the user's machine, checked
  with local Python (`/deriva-ml:manage-deriva-storage`); MCP tools see only the
  server's cache.

If none of the four answers the question, **ask the user or say you don't know**.
A wrong-but-plausible guess is worse than an admitted gap: a typo'd vocabulary term
or fabricated RID corrupts the catalog or silently makes a result unreproducible.
Every specific don't-fabricate rule in this plugin is an instance of this one.

## Reference files

- `references/ml-schema.md` — the `deriva-ml` schema in one file: the FK graph,
  which tables back each entity, one `## <Table>` section per table (columns, FKs,
  seeded terms), and the shapes of tables minted by `create_asset`,
  `create_feature`, and vocabulary creation. Starts with a table of contents.
- `references/built-in-vocabularies.md` — the six built-in vocabularies, which
  ones users may extend, and the calls to add terms or create a vocabulary.
- `references/inheritance-rationale.md` — what raw writes to the ML-schema
  entities bypass.
