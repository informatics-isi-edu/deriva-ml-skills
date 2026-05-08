---
name: deriva-ml-context
description: "ALWAYS load this context when the deriva-ml plugin is active. Establishes what DerivaML is (a reproducible-ML layer on top of Deriva catalogs), the five core abstractions (Dataset, Workflow, Execution, Feature, Asset), and the inheritance-with-override rule that governs when to use a deriva-ml surface versus the underlying deriva surface. Triggers on: 'derivaml', 'deriva-ml', 'dataset', 'workflow', 'execution', 'feature', 'asset', 'experiment', 'training run', 'model', 'pipeline', 'reproducible', 'provenance', 'hydra-zen', 'configure-experiment'."
disable-model-invocation: false
---

<!--
SYNC: this skill mirrors `_CONCEPTS_GUIDE` in
`deriva-ml-mcp/src/deriva_ml_mcp/prompts.py`. When the conceptual
core changes (the five abstractions, the inheritance rule, the
vocabulary-extension pattern), update both. See CLAUDE.md ("Cross-Repo
Sync") for the full convention. Inheritance-rule rationale: ADR-0001.
-->

# DerivaML Plugin Context

## What is DerivaML?

DerivaML is a **reproducible-ML layer built on top of Deriva catalogs**. It records the full provenance of every ML run — inputs, code versions, configurations, outputs, and intermediate artifacts — as first-class catalog entities so that experiments can be reproduced, audited, compared across users, and resumed across sessions.

The DerivaML stack:

- **`deriva-ml`** — the Python library; provides the `DerivaML` class, `Workflow`, `ExecutionConfiguration`, dataset / feature / asset APIs, and the `with ml.create_execution(config) as exe:` context manager pattern.
- **`deriva_ml_*` MCP tools** — e.g., `deriva_ml_create_dataset`, `deriva_ml_start_execution`, `deriva_ml_add_feature_values`, plus the `deriva://catalog/{h}/{c}/ml/...` resource family.
- **`deriva-ml-skills`** — this Claude Code plugin; ~28 skills that drive the above two layers through Claude.

All `deriva_ml_*` tools take `hostname=` and `catalog_id=` arguments explicitly — see `/deriva:deriva-context` for the stateless-model framing that applies to the whole stack.

## The five core abstractions

These are the surface DerivaML adds on top of plain Deriva. Each is stored as one or more Deriva tables underneath, but **treat them as DerivaML domain objects, not as raw tables**.

| Abstraction | What it represents | Primary skill | Key MCP tools |
|---|---|---|---|
| **Dataset** | A versioned collection of catalog rows that an execution consumed or produced. Datasets have a type (`Dataset_Type` vocab), an element-type spec, a version history, and can be downloaded as bags. | `dataset-lifecycle` | `deriva_ml_create_dataset`, `deriva_ml_add_dataset_members`, `deriva_ml_increment_dataset_version`, `deriva_ml_cache_dataset`, `deriva_ml_validate_dataset_specs` (pre-flight), `deriva_ml_validate_execution_configuration` (full pre-flight) |
| **Workflow** | A versioned reference to the code (URL + git commit hash) that knows how to do a thing. A Workflow is content-addressed: same URL + same commit = same Workflow row. Workflows are typed (`Workflow_Type` vocab). | `new-model` (authoring) / `configure-experiment` (wiring) | `deriva_ml_create_workflow`, `deriva_ml_find_workflow_by_url` |
| **Execution** | One run of a Workflow against specific input Datasets, producing output Datasets / Features / Assets. Executions have a status (`Execution_Status_Type`), inputs / outputs links, and an active context manager that stages files in a working directory. | `execution-lifecycle` | `deriva_ml_create_execution`, `deriva_ml_start_execution`, `deriva_ml_commit_execution`, `deriva_ml_abort_execution`, `deriva_ml_update_execution`, `deriva_ml_get_lineage` (provenance traversal — "how did this come to exist?") |
| **Feature** | A typed value attached to a row of some target table (e.g., a per-image classification label produced by a run). Features link the value back to the producing Execution for provenance. | `create-feature` | `deriva_ml_create_feature`, `deriva_ml_add_feature_values` |
| **Asset** | A file uploaded to hatrac and recorded in the catalog with an Asset_Type and provenance link to its producing Execution. Assets are written to paths returned by `exe.asset_file_path()` and uploaded by `exe.upload_execution_outputs()`. | `work-with-assets` | `deriva_ml_list_asset_tables`, `deriva_ml_lookup_asset`, `deriva_ml_update_asset` |

### Core ML resources

The plugin exposes a `deriva://catalog/{hostname}/{catalog_id}/ml/...` resource family for read-only browsing of the abstractions above. Singular vs plural is semantic: singular = one-by-RID, plural = a collection.

| URI | Returns |
|---|---|
| `ml/datasets`, `ml/dataset/{rid}` | Datasets list / one dataset |
| `ml/workflows`, `ml/workflow/{rid}` | Workflows list / one workflow |
| `ml/executions`, `ml/execution/{rid}` | Executions list / one execution |
| `ml/features/{table}` | Features defined on a target table |
| `ml/vocabularies/{schema}` | Vocabulary tables in one schema (`{schema}` = `deriva-ml` for the four built-ins, or your domain schema) |
| `ml/vocabularies/{schema}/{vocab_name}` | Full term list for one vocabulary (name, rid, description, synonyms, CURIE, URI) |
| `ml/assets/{schema}` | Asset tables in one schema |
| `ml/assets/{schema}/{asset_table}` | Snapshot of assets in one asset table |
| `ml/asset/{rid}` | One asset by RID |

For paginated access to assets, prefer the `deriva_ml_list_assets` tool. For element-type discovery (which tables can contribute dataset members), use the purpose-built `deriva_ml_list_dataset_element_types` tool.

## The rule: inheritance with override

The deriva-ml plugin **extends** the deriva plugin. Everything that applies in a Deriva catalog applies in a deriva-ml catalog by default. **Override:** if a deriva-ml surface exists for an operation, prefer it over the equivalent deriva surface. This applies symmetrically on all three planes:

- **Skills:** prefer `/deriva-ml:<skill>` over `/deriva:<skill>` when both exist.
- **MCP:** prefer `deriva_ml_*` MCP tools, prompts, and resources over the equivalent `deriva-mcp-core` tool / prompt / resource.
- **Python API:** prefer `deriva-ml` objects and methods (`DerivaML`, `Dataset`, `Workflow`, `Execution`, `Feature`, the `with ml.create_execution(config) as exe:` context manager, `exe.asset_file_path()`, etc.) over the equivalent `deriva-py` calls (`ErmrestCatalog`, `PathBuilder`, raw entity resource access).

The override boundary is mechanical: "is there a deriva-ml `<thing>` for this?" If yes, use it. If no, the deriva default applies and the LLM should reach for the corresponding `/deriva:<skill>`, `deriva-mcp-core` tool, or `deriva-py` call.

The five abstractions above are where the override mostly lands. Going around them — using `insert_entities` / `update_entities` / `delete_entities` to mutate Datasets, Workflows, Executions, Features, or Asset rows — bypasses real machinery:

- **Business logic** — e.g., `deriva_ml_add_dataset_members` validates RIDs against the dataset's element-type spec; raw inserts will let you add wrong-table rows that break the dataset on materialization.
- **FK validation across the Dataset / Workflow / Execution graph** — DerivaML enforces invariants (every Execution links to a Workflow, every output Dataset links to its producing Execution); raw inserts can create dangling references.
- **Provenance tracking** — each mutation links back to the active Execution; raw inserts have no Execution context.
- **Version management** — Datasets are versioned; `deriva_ml_increment_dataset_version` creates a new snapshot. Raw inserts skip the version bump, leaving consumers pointed at stale data.
- **RAG re-indexing** — the `deriva_ml_*` tools fire surgical re-index hooks so freshly mutated rows are searchable on the next `rag_search`. Raw inserts do not.
- **Audit emission** — every `deriva_ml_*` mutation emits an audit event with the operation name, hostname, catalog, and result; raw inserts use the generic core audit which lacks DerivaML-specific context.

## What DerivaML adds on top

Deriva's seven design pillars (see `/deriva:deriva-context`) are about **data design** — how to model your data so it's findable, accessible, interoperable, and reusable. DerivaML adds **process design** — how to run an ML pipeline against that data so the run itself is reproducible. The two are orthogonal: a Deriva catalog with no DerivaML use can be FAIR-by-construction; a DerivaML catalog adds reproducibility-by-construction on top. The mechanism is three abstractions doing complementary jobs: **Datasets pin** which rows the run consumed; **Workflows pin** which code (URL + git commit) ran them; **Executions link** the two so any output Feature or Asset traces back to (specific code) × (specific inputs).

The provenance graph is **walkable in one tool call**: `deriva_ml_get_lineage(rid=...)` traces any artifact (Dataset, Asset, Feature value, Execution) back through its producing-execution chain to the root. That's how you answer "how did this come to exist?" without manually walking 5-15 typed-read calls. Conversely, when you're about to run an experiment and want to confirm the config is valid before paying the bag-download cost of `dry_run=True`, use `deriva_ml_validate_execution_configuration(config=...)` — the cheap metadata-only pre-flight gate.

## Built-in DerivaML vocabularies

DerivaML ships four built-in vocabularies. Extend them via the generic `add_term` tool, passing `schema="deriva-ml"` and the appropriate `table=`:

| Vocabulary | How to add a term | Notes |
|---|---|---|
| `Dataset_Type` | `add_term(hostname=..., catalog_id=..., schema="deriva-ml", table="Dataset_Type", name=..., description=...)` | Tag your dataset with this term via `deriva_ml_create_dataset(dataset_types=[...])` |
| `Workflow_Type` | `add_term(hostname=..., catalog_id=..., schema="deriva-ml", table="Workflow_Type", name=..., description=...)` | Pass to `deriva_ml_create_workflow(workflow_type=...)` |
| `Asset_Type` | `add_term(hostname=..., catalog_id=..., schema="deriva-ml", table="Asset_Type", name=..., description=...)` | Tag specific assets via `deriva_ml_update_asset(...)` |
| `Execution_Status_Type` | (managed automatically by the execution-state machine — do not extend) | Status transitions happen via `deriva_ml_start_execution` / `deriva_ml_commit_execution` / `deriva_ml_abort_execution` |

The inheritance rule still applies: even though you are using the generic `add_term` for the term itself (no deriva-ml override exists for it), the **lifecycle of Datasets / Workflows / Executions / Features / Assets** must go through the `deriva_ml_*` tools.

For all *other* vocabularies (your own domain vocabs like `Sample_Type`, `Tissue_Type`, `Image_Quality`), use the same generic `add_term` documented in `/deriva:manage-vocabulary` — pass your domain schema name instead of `"deriva-ml"`.

## The entity resolution workflow

This applies to **any catalog entity** referenced by name — tables, columns, schemas, vocabulary terms, datasets, workflows, executions, features, assets, or anything else the catalog tracks. ML-domain or generic, the workflow is the same.

When the user mentions an entity by name, OR when the user asks to create a new one, follow these steps:

1. **Exact match first.** If the user-supplied string matches a known canonical name exactly (case-sensitive), use it. Don't search, don't ask. Catalog names are case-sensitive: `"Training"` is the `Dataset_Type` term; `"training"` is not.

2. **Semantic search if ambiguous, fuzzy, or descriptive.** If the user's phrasing doesn't match a canonical name exactly — it's descriptive (`"the training data type"`), abbreviated (`"DR"`), misspelled (`"Diagnossis"`), or just unfamiliar — call `rag_search` with their phrase. Use the appropriate `doc_type`:

   - `catalog-schema` for tables, columns, features, vocabulary terms
   - `catalog-data` for datasets, workflows, executions
   - `ml-docs` / `user-guide` for documentation references

3. **Present a picker when multiple options appear.** If RAG returns more than one plausible candidate, list 3-5 of them with their canonical name + one-line description + RID (or `table.column` for column hits) and ask the user to pick. Don't choose blindly when reasonable people might disagree. If RAG returns ONE clear top hit (significantly above runners-up), use it but tell the user what you resolved it to in one sentence (`"I'm using the Training Dataset_Type."`). If RAG returns NO useful hits, ask a clarifying question. **Do NOT fabricate a name; do NOT call `create_*` with a guessed identifier.**

4. **Lookup path ends here.** With the canonical entity in hand, call the relevant `lookup_*` / `get_*` / `find_*` tool, or pass the canonical name / RID to whatever operation the user requested.

5. **Create path has one more step.** If you arrived here because the user asked to CREATE a new entity, before actually calling `create_*`, surface the candidates from step 3 to the user explicitly:

   > "I found these similar existing entities: `<list>`. Would modifying or reusing one of these work, or do you want to create a new one?"

   If the user picks an existing one, switch to the lookup path. If the user confirms a new one is needed, proceed to step 6.

6. **Description handling on create.** Every `create_*` / `add_*` tool that accepts a `description` (or `comment`) argument SHOULD receive a non-empty, user-confirmed one — never empty, never placeholder text like `"TODO"`, never a fabricated description without showing the user. The full discipline (gather context → draft → confirm → create) and the autonomous-agent fallback live in the always-on `/deriva:generate-descriptions` (generic entities) and `/deriva-ml:generate-descriptions` (ML entities) skills.

### Why this workflow matters

The cost of getting it wrong:
- **Fabricating a name** leads to FK-violation errors at best, or silent data corruption at worst (e.g. a typo'd `"Trianing"` Dataset_Type that creates a duplicate vocab term).
- **Skipping the picker** when there are multiple matches lets the LLM commit the user to an entity they didn't intend.
- **Empty descriptions** destroy catalog discoverability — a catalog with 500 datasets all described as `""` is indistinguishable from a catalog with 500 datasets nobody can find.

The cost of doing it right is one or two extra round-trips per operation. **Always prefer the round-trips.**

### Related always-on skills

Several always-on skills reinforce this workflow:

- **`/deriva:semantic-awareness`** *(deriva-skills)* — find-before-you-create discipline; teaches the synonym/abbreviation/spelling-variant search expansion that step 2 relies on. The discipline applies to ML entities (Datasets, Workflows, Features) as well as generic catalog entities.
- **`/deriva:generate-descriptions`** *(deriva-skills)* — description-generation guidance for generic catalog entities (tables, columns, vocabularies, vocabulary terms).
- **`/deriva-ml:generate-descriptions`** *(this plugin)* — description-generation guidance for DerivaML entities (Datasets, Workflows, Executions, Features, Assets, Experiments). The deriva-skills and this plugin's description skills cover non-overlapping entity sets and share the same generic workflow and quality bar.

This skill links them together into one workflow; the always-on skills cover each half in more depth.

## Routing notes where both plugins have a surface

For most operations the inheritance rule resolves the routing on its own — if a deriva-ml `<thing>` exists, use it; otherwise the deriva default applies. One genuine ambiguity remains where both plugins legitimately have a surface and the rule alone doesn't pick:

- **Version checks** — `/deriva:troubleshoot-deriva-errors` ("Versioning and updates" section) for the foundation (deriva-py, deriva-mcp-core, deriva plugin); `/deriva-ml:troubleshoot-execution` ("Versioning and updates" section) for the DerivaML layer. Check the foundation first — the DerivaML stack depends on it.

The `deriva-skills` plugin has two paths for Chaise display annotations — `/deriva:customize-display` (interactive MCP-tool path) and `/deriva:use-annotation-builders` (type-safe Python builder classes for production scripts). The choice between them is interactive-vs-script-based, not domain-based.

## Pointers

DerivaML domain workflows (this plugin):

- `/deriva-ml:dataset-lifecycle` — Dataset creation, population, splitting, versioning, browsing, downloading
- `/deriva-ml:execution-lifecycle` — Pre-flight validation, running experiments, execution provenance
- `/deriva-ml:create-feature` — Features, labels, annotations, selectors
- `/deriva-ml:work-with-assets` — File assets — upload, download, provenance, types
- `/deriva-ml:configure-experiment` — DerivaML experiment project structure (Hydra-zen configs)
- `/deriva-ml:write-hydra-config` — Hydra-zen config files for experiments
- `/deriva-ml:new-model` — Scaffold a new model function
- `/deriva-ml:browse-erd` — Interactive entity-relationship diagram for the catalog
- `/deriva-ml:troubleshoot-execution` — Execution-lifecycle troubleshooting (asset paths, upload, stuck Running, version mismatch, missing feature)

Generic catalog operations (provided by the `deriva-skills` plugin, assumed loaded):

- `/deriva:deriva-context` — Plugin-wide context for the deriva plugin (the seven design pillars, stateless-model framing, plugin scope)
- `/deriva:troubleshoot-deriva-errors` — Generic catalog troubleshooting
- `/deriva:manage-vocabulary` — Generic vocabulary CRUD
- `/deriva:create-table` — Custom domain tables
- `/deriva:query-catalog-data` — Querying / browsing
