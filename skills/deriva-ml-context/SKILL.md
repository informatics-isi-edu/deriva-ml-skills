---
name: deriva-ml-context
description: "Always-on plugin context — load whenever the deriva-ml plugin is active and any DerivaML work is in view (datasets, workflows, executions, features, assets, experiments, training runs, pipelines, provenance, hydra-zen configs). This is background framing the model should carry the whole session, not a selective per-task trigger. Establishes what DerivaML is (a reproducible-ML layer on top of Deriva catalogs), the five core abstractions (Dataset, Workflow, Execution, Feature, Asset), and the inheritance-with-override rule that governs when to use a deriva-ml surface versus the underlying deriva surface."
disable-model-invocation: false
---

<!--
SYNC: this skill mirrors `_CONCEPTS_GUIDE` in
`deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/prompts.py`. When the conceptual
core changes (the five abstractions, the inheritance rule, the
vocabulary-extension pattern), update both. See CLAUDE.md ("Cross-plugin and cross-repo
rules") for the convention. Inheritance-rule rationale: ADR-0001.
-->

# DerivaML Plugin Context

## What is DerivaML?

DerivaML is a **reproducible-ML layer built on top of Deriva catalogs**. It records the full provenance of every ML run — inputs, code versions, configurations, outputs, and intermediate artifacts — as first-class catalog entities so that experiments can be reproduced, audited, compared across users, and resumed across sessions.

### Experiments live in GitHub repositories

DerivaML organizes ML activities into **experiments**. An experiment is a **GitHub repository** that holds the *executable* and *human-readable* sides of a research project; the catalog stores the *what* (data, RIDs, lineage), the experiment repository stores the *how* and the *why*:

- **Code** — model implementations, data-loading scripts, notebooks.
- **Configuration** — hydra-zen configs (Python, not YAML) declaring which catalog, which datasets, which workflow, which hyperparameters.
- **Tacit knowledge** — `tacit-knowledge.md` (project root) capturing the *why* behind decisions, dead ends explored, and the project's conventions. See `/deriva-ml:capture-tacit-knowledge` for the discipline.
- **Provenance link** — every execution records the code it ran: a `Workflow` row for the script, plus the exact URL and commit in the execution's own `configuration.json` (`Execution_Metadata`), so a result can be traced to the code that produced it.

Bootstrap a new experiment from [`deriva-ml-model-template`](https://github.com/informatics-isi-edu/deriva-ml-model-template) — it provides hydra-zen scaffolding, CLI entry points (`deriva-ml-run`, `deriva-ml-run-notebook`), GitHub Actions for versioning and docs, and an example model (CIFAR-10) you can replace with your own.

> **Capture the *why* as you go.** After any decision-bearing action, append a short dated entry to `tacit-knowledge.md`; consult it before recommending an action and before answering "why was X chosen". The full WRITE / GUIDANCE / FORENSIC discipline is in `/deriva-ml:capture-tacit-knowledge`, and the plugin's session-start hook loads it every session.

The DerivaML stack:

- **`deriva-ml`** — the Python library; provides the `DerivaML` class, `Workflow`, `ExecutionConfiguration`, dataset / feature / asset APIs, and the `with ml.create_execution(config) as exe:` context manager pattern.
- **`deriva_ml_*` MCP tools** — e.g., `deriva_ml_create_dataset`, `deriva_ml_create_feature`, `deriva_ml_release_dataset`, plus the `deriva://catalog/{h}/{c}/deriva-ml/...` resource family. MCP is the **observation + catalog-state-mutation** surface; execution authorship (creating + running executions, staging feature values, committing output assets) lives in user-local Python via bundled script templates — see the `execution-lifecycle` skill.
- **`deriva-ml-skills`** — this Claude Code plugin; the skills that drive the above two layers through Claude.

All `deriva_ml_*` tools take `hostname=` and `catalog_id=` arguments explicitly — see `/deriva:deriva-context` for the stateless-model framing that applies to the whole stack.

## The object model in one screen (start here if you're new)

DerivaML keeps your work in **two durable places**, and knowing which is which prevents most early confusion:

- **The catalog** (a Deriva server) — the *data and its provenance*: datasets, features, assets, workflows, executions, RIDs, and the lineage graph connecting them. This is the authoritative record of *what exists and what produced it*.
- **The project repository** (a git repo on your machine) — the *code and intent*: model code, Hydra-zen configs (`src/configs/`), the design docs (`docs/design/experiment/`, `docs/design/dataset/`, `docs/design/feature/`, `docs/design/model/`), and `tacit-knowledge.md`. This is where you *plan and build*; the catalog is where results *land*.

Everything you do follows one arc — **Specify → Build → Validate**: write a design doc (Specify), implement/configure/run it (Build), check the result against the design (Validate). The four entities all share this arc.

### The repo's planning artifacts — and how they connect

A project describes each experiment in several Markdown files that are **distinct views joined by a shared `<slug>`, not duplicates**: the design doc `docs/design/<entity>/<slug>.md` (the plan and verdict), the design index `docs/design/index.md`, the generated `Experiments.md` (the runnable view, built from `src/configs/experiments.py` and `multiruns.py`), the config itself, and `tacit-knowledge.md` (the journal of why). Don't treat one as a substitute for another. When you add or change an experiment config, update `Experiments.md`, link the design doc both ways, and add the design-index line **in the same commit**.

The full map of the files, how they link, and the multi-model case: `references/planning-artifacts.md`. Owned by `/deriva-ml:configure-experiment` (`Experiments.md`) and `/deriva-ml:design-experiment` (the design bundle).

### Which skill do I start with?

| Your situation | Start with |
|---|---|
| No project repo yet | `/deriva-ml:setup-derivaml-project` |
| No ML catalog yet | `/deriva-ml:setup-ml-catalog` |
| New / unproven pipeline (no real results yet) | `/deriva-ml:model-development-workflow` (cycle zero) |
| Working pipeline, want to test a hypothesis | `/deriva-ml:experiment-lifecycle` |
| Need one specific entity | `/deriva-ml:dataset-lifecycle`, `/deriva-ml:create-feature`, `/deriva-ml:new-model`, or `/deriva-ml:work-with-assets` |
| About to plan any of the above | `/deriva-ml:design-experiment` (the Specify phase for all four) |
| Want to read / inspect existing results without writing code | `/deriva-ml:explore-results` |
| Running or pre-flighting an execution | `/deriva-ml:execution-lifecycle` |
| Wiring configs (project structure, config files, RIDs) | `/deriva-ml:configure-experiment`, `/deriva-ml:write-hydra-config` |
| About to change or delete a table, column, vocabulary, dataset or asset | `/deriva-ml:schema-evolution-impact` |
| Want a diagram of the catalog | `/deriva-ml:browse-erd` |
| Something broke / am I up to date | `/deriva-ml:troubleshoot-execution` |

> **One term, three meanings — "experiment".** (1) the *experiment cycle* (one turn of the experiment lifecycle); (2) an *experiment config preset* (a named entry in `configs/experiments.py` composing model + dataset + params); (3) the *experiment repository* (the project repo itself). Keep them distinct.

## Never guess — ground truth is observable

DerivaML work is reproducible only because every fact is recorded somewhere
authoritative. So the governing rule for this whole domain: **never guess, invent,
or assume a fact you could observe.** If you don't know a value — a RID, a version,
a vocabulary term, a column name, a file path, a config value, whether a dataset
exists — **look it up; do not make it up.** Ground truth lives in exactly four
places, and one of them has the answer:

- **The catalog** — RIDs, dataset/feature/workflow/execution records, vocabulary
  terms, schema, lineage. Read it via the `deriva://…` resources / `deriva_ml_*`
  tools / `rag_search` (see the resolution workflow below). For **raw table shape**
  — the exact columns, keys, or foreign keys of a *named* table (e.g. "columns on
  `Subject`", "does `Image` have a `Diagnosis` FK") — there is no `deriva_ml_*`
  surface; that is a generic-catalog fact, so fall through to `/deriva`'s
  `deriva://catalog/{hostname}/{catalog_id}/table/{schema}/{table}` resource (or
  `get_table` / `get_schema`). Read the exact resource, not `rag_search` — semantic
  search finds *which* table by concept, but can return a partial column list.
- **The project repo** — config values, model code, design docs
  (`docs/design/`), and the rationale journal (`tacit-knowledge.md`). Read the
  files; check `git`.
- **The working directory** — what the current execution staged: files written to
  `exe.asset_file_path(...)` paths, the working-dir layout. Inspect it.
- **The cache** — downloaded dataset bags and assets (`deriva_ml_bag_info`,
  the cache dir). Check what's materialized before assuming it is or isn't.

If none of the four answers the question, **ask the user or say you don't know** —
never fabricate a plausible-looking RID, term, version, or path. A wrong-but-
plausible guess is worse than an admitted gap: it corrupts the catalog (a typo'd
vocab term, a fabricated RID that FK-violates) or silently produces an
unreproducible result. The specific don't-fabricate rules elsewhere in this skill
(don't invent a name in entity resolution, don't fabricate a `cite_url`, don't
write a placeholder description) are all instances of this one principle.

## Confirm authentication before the first catalog operation

Before the **first catalog operation** against a catalog in a session — read or write — confirm you're authenticated to *that* catalog, so a missing login shows up front instead of as a 401 deep in a run. Check the credential of whatever will do the work:

- **Python** (scripts, loaders, executions): `ml.is_authenticated()` after constructing `DerivaML(...)`; if false, stop and tell the user to run `deriva-globus-auth-utils login --host <host>`. There is no `check_auth=` constructor argument.
- **MCP**: call `deriva_ml_check_authentication(hostname, catalog_id)`. `authenticated: false` means no valid session; `{"error": ...}` means the server wasn't reachable.

Either check confirms *authentication*, not *authorization* — ACLs can still refuse a write. This section is the canonical rule other skills point to; code, return shapes and caveats are in `references/authentication.md`.

## Read-side questions: fetch the resource first

For **read-side questions about an existing entity** — "show me X by RID," "what's in Y," "what did Z produce / consume," "what's the current version of W" — fetch the matching `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/...` resource *before* reaching for `deriva_ml_*` tools or generic catalog CRUD (`get_entities`, `query_attribute`, `list_foreign_keys`). The resource family is purpose-built for these lookups: a single fetch returns the entity's summary plus its associated children (a dataset's members and version, an execution's inputs/outputs/metadata, a workflow's executions, etc.) in a stable bundled shape, while the equivalent tool path typically takes 2–7 round trips of fetch + filter + join.

| URI | Returns |
|---|---|
| `deriva-ml/datasets`, `deriva-ml/dataset/{rid}` | Datasets list / one dataset (summary, type, current version, `cite_url`, members) |
| `deriva-ml/workflows`, `deriva-ml/workflow/{rid}` | Workflows list / one workflow |
| `deriva-ml/executions`, `deriva-ml/execution/{rid}` | Executions list / one execution (summary + inputs + outputs split into `assets` and `metadata` + experiment; per-row `cite_url`) |
| `deriva-ml/lineage/{rid}` | Provenance chain for any artifact (Dataset, Asset, Feature value, Execution) |
| `deriva-ml/features/{table}` | Features defined on a target table |
| `deriva-ml/vocabularies/{schema}` | Vocabulary tables in one schema (`{schema}` = `deriva-ml` for the six built-in vocabulary tables, or your domain schema) |
| `deriva-ml/vocabularies/{schema}/{vocab_name}` | Full term list for one vocabulary (name, rid, description, synonyms, CURIE, URI) |
| `deriva-ml/assets/{schema}` | Asset tables in one schema |
| `deriva-ml/assets/{schema}/{asset_table}` | Snapshot of assets in one asset table |
| `deriva-ml/asset/{rid}` | One asset by RID |

Each row is the tail of `deriva://catalog/{hostname}/{catalog_id}/…`. The URI is constructable from the catalog hostname + ID + entity RID — no tool search needed. Reach for tools when the resource doesn't cover the question (paginated browsing of large asset tables → `deriva_ml_list_assets`; element-type discovery → `deriva_ml_list_dataset_element_types`; mutations and complex queries → the appropriate `deriva_ml_*` tool).

### Always render a RID as a click-through link — never bare text

**Global rule for the whole plugin: anywhere a RID appears in Markdown — your chat
output AND any document you write (design docs under `docs/design/`,
`tacit-knowledge.md`, READMEs, `Experiments.md`, PR descriptions) — render it as a
click-through Markdown link, never as a bare string.** A bare RID is a dead end: a
reader cannot follow it back to the catalog without hand-reconstructing a URL. The
link form is the `/id/`-resolver (`https://{host}/id/{cat}/{rid}[@snaptime]`):

- For **datasets** at a released version it is snapshot-pinned (`...@{snaptime}`) — clicking lands on the dataset state at that release.
- For **datasets** at a dev version (PEP 440 `is_devrelease`, e.g. `0.4.0.post1.dev3` per ADR-0003) it has no snaptime — clicking lands on the live catalog state.
- For **assets / executions / workflows / features** it is always the live form (no snaptime) — those entities aren't versioned the way datasets are.

**Where the URL comes from, by context:**
- **Presenting RIDs from a bundle resource** (chat output): use the row's `cite_url` field — the bundle resources (`DatasetDetail`, `ExecutionInputDatasetRef`, `ExecutionAssetRef`, …) carry per-row `cite_url`.
- **Writing a RID into a document** (you have a `ml = DerivaML(...)` in scope — the author of a design doc or journal entry does): call `ml.cite(rid)`, which returns the same permanent `/id/` URL (snapshot-pinned by default; `ml.cite(rid, current=True)` for the live form). Paste the returned URL into the Markdown link.

Example: `[8N4](https://localhost/id/1407/8N4) cifar10_cnn_weights.pt`, not `8N4 cifar10_cnn_weights.pt`. The same applies to a design doc's "Outcome" execution RID, a `tacit-knowledge.md` entry's catalog handle, an `Experiments.md` row — every one is `[label](cite-url)`.

This is the **citation URL** (for a human to click through), distinct from the `deriva://catalog/…` **resource URI** (for programmatic/MCP fetches against the live catalog). Use the citation URL whenever the audience is a reader.

When no `cite_url` is available (a best-effort failure, a thinly-built ref, or `ml.cite()` can't resolve the RID), fall back to the bare RID — but **flag the gap rather than fabricating a URL** (the never-guess rule).

### Cold-start orientation: call the primer before the first MCP call

This skill (`deriva-ml-context`) teaches the resource-vs-tool *rule* above; the
cold-start *procedure* it's grounded in — calling `deriva_ml_primer` before the
first MCP call, then fetching on-demand guides — is owned by
`/deriva-ml:using-deriva-mcp` *(auto-loaded before the first MCP call)*. Both
should be active before the first MCP call. Skip `using-deriva-mcp` only when the
entire interaction stays on the shell/Python side (`load-cifar10`,
`deriva-ml-run`, direct `deriva-ml` library calls) and never crosses the MCP
boundary.

## The five core abstractions

These are the surface DerivaML adds on top of plain Deriva. Each is stored as one or more Deriva tables underneath, but **treat them as DerivaML domain objects, not as raw tables**. The "Key MCP tools" column lists the tools used for *write-side* and complex operations; for read-side lookup-by-RID, see the resource table above.

| Abstraction | What it represents | Primary skill | Key MCP tools |
|---|---|---|---|
| **Dataset** | A versioned collection of catalog rows that an execution consumed or produced. Datasets carry a type (`Dataset_Type` vocab), an element-type spec, a two-state PEP 440 version (released or dev, per ADR-0003), and can be downloaded as bags. | `dataset-lifecycle` | `deriva_ml_create_dataset`, `deriva_ml_add_dataset_members`, `deriva_ml_release_dataset` (dev → released), `deriva_ml_validate_dataset_specs` (pre-flight), `deriva_ml_validate_execution_configuration` (full pre-flight). Bag-cache warming via `manage-deriva-storage/scripts/warm_cache.py`. |
| **Workflow** | A reference to the script that does a thing: its URL and the git hash of the file's contents (`Checksum`), typed by the `Workflow_Type` vocab. Rows are deduplicated — `create_workflow` reuses a row whose URL *or* checksum matches — so a row's URL and version are from its first registration. The commit a particular run used is in that execution's `configuration.json`. | `new-model` (authoring) / `configure-experiment` (wiring) | `deriva_ml_create_workflow`, `deriva_ml_find_workflow_by_url` |
| **Execution** | One run of a Workflow against specific input Datasets, producing output Datasets / Features / Assets. Executions have a status (Created → Running → Stopped → Pending_Upload → Uploaded; plus terminal `Failed` / `Aborted`), inputs / outputs links, and an active context manager that stages files in a working directory. Runs are governed by a **provenance contract** (terminal-state requirement, unknown-provenance sentinels, `ml.audit_provenance()`) — owned by `/deriva-ml:execution-lifecycle` (steps 7–8) and `/deriva-ml:troubleshoot-execution` for the catalog-wide audit. | `execution-lifecycle` | **Authoring**: `execution-lifecycle/scripts/basic_execution.py` (and the other bundled templates) — these are runnable Python that you copy, edit, commit, and run. **Observation** (MCP): `deriva_ml_get_execution`, `deriva_ml_list_executions`, `deriva_ml_find_workflow_executions`, `deriva_ml_list_execution_children`, `deriva_ml_list_execution_parents`, `deriva_ml_get_lineage` (provenance traversal — "how did this come to exist?"). |
| **Feature** | A typed value attached to a row of some target table (e.g., a per-image classification label produced by a run). Features link the value back to the producing Execution for provenance. | `create-feature` | **Define the feature** (MCP): `deriva_ml_create_feature`. **Add feature values** (bundled template): `create-feature/scripts/populate_feature_values.py` (or `exe.add_features(records)` inside another execution template). |
| **Asset** | A file uploaded to hatrac and recorded in the catalog with an Asset_Type and provenance link to its producing Execution. Assets are written to paths returned by `exe.asset_file_path()` and committed by `exe.commit_output_assets()`. | `work-with-assets` | `deriva_ml_list_assets`, `deriva_ml_lookup_asset`, `deriva_ml_update_asset` |

This table is the *tools & skills* cut. For the complementary *catalog tables* cut — which `deriva-ml` schema tables back each abstraction, with their foreign keys — see `references/concepts/index.md` ("Five abstractions → backing tables").

### Use direct attribute access on these domain objects

The five abstractions above are returned as **typed records** (Pydantic models / DerivaML domain objects), not as raw dicts or row-tuples. Read their fields with the dot operator:

- A `Dataset` exposes `.dataset_rid`, `.current_version`, `.dataset_types`, `.description`.
- An `Execution` exposes `.execution_rid`, `.status`, `.workflow`, `.description`.
- A `Workflow` exposes `.workflow_rid`, `.workflow_type`, `.url`, `.checksum`.
- A `FeatureRecord` exposes one named attribute per feature column (`.Diagnosis_Type`, `.Confidence`, etc.) plus `.Execution`, `.Feature_Name`, `.RCT`.
- An `Asset` exposes `.asset_rid`, `.filename`, `.length`, `.md5`, `.asset_types`.

The `repr()` of any domain object spells out its field names — `print(obj)` is faster than guessing.

**Do not use `getattr(obj, "name", default)` on these objects.** The attributes either exist by contract or they don't; a wrong name is an `AttributeError` you *want* to see. `getattr`-with-default converts API ignorance into a silent fallback — `getattr(d, "version", "?")` quietly returns `"?"` when the real field is `current_version`, and the bug ships. Dot directly into the object, let `AttributeError` tell you what's wrong, and fix the call. Reach for `getattr` only when reflecting over genuinely unknown attribute names (e.g. iterating a list of column names a user supplied at runtime, debug-printing arbitrary records). That is rare; the normal case is `obj.field_name`.

This is the mechanical follow-through on "treat them as DerivaML domain objects, not as raw tables" — the override rule says *use the domain object*, this paragraph says *and once you have it, use its named attributes*.

### Carry structure, don't decay it

The dot-access rule above is the local case. The broader principle is: **when data has a known shape, carry it in a container that knows the shape**, end-to-end through the analysis. The shape doesn't have to be one row — it can be a table, a table of tables, or a free-form mapping. Pick the container that matches the shape you've actually got:

| Shape | Right container | Why |
|---|---|---|
| **One record** (a row, a config, a ranking entry you're building up) | `@dataclass` or Pydantic `BaseModel` | Named fields, typo-checked at definition, `repr()` is readable. |
| **Many records of the same shape** (a query result, a denormalized dataset, a per-image prediction table) | `pandas.DataFrame` (or `polars.DataFrame`) | Columns are named, dtypes are tracked, indexing/joining/aggregation are first-class. **A DataFrame returned by `get_denormalized_as_dataframe()` (on a `Dataset` or `DatasetBag`) is exactly this — keep it as a DataFrame.** |
| **A few labeled tables that belong together** (e.g., one DataFrame per model run, joined on image RID) | `@dataclass` whose fields are DataFrames, or `dict[str, DataFrame]` if names are dynamic | The outer container makes the relationships obvious; the inner DataFrames keep their column schemas. |
| **Genuinely schemaless** (config blobs from arbitrary YAML, MCP responses you're inspecting interactively) | `dict` — and reach for `.get(key, default)` here, *only* here | When there's no contract, defensive lookup is correct. Outside this row, it's an anti-pattern. |

The reason this matters: when structure decays — when a typed `Execution` becomes a `dict`, a DataFrame becomes a `list[dict]`, a `@dataclass` becomes a tuple — you lose the named-field check at every downstream call site. `getattr(d, "version", "?")` returning `"?"` instead of erroring is the symptom; the disease is that `d` should never have been treated as if its fields were optional in the first place. Same disease shows up as `row["confidence"]` silently returning `None` because the real column is `Confidence`, or `result.get("status")` masking a renamed field.

The rule is not "avoid DataFrames" — DataFrames *are* the typed container for table-of-records. The rule is **don't downgrade**: don't turn a DataFrame into a list-of-dicts, don't turn a Pydantic record into a dict, don't turn a `@dataclass` into a tuple. Each downgrade trades a real schema for stringly-typed lookups, and every downstream call site pays the cost. Two worked examples of the downgrade failure mode (the execution-ranking `list[dict]` and the `get_denormalized_as_dataframe()` DataFrame) are in [`references/python-idioms.md`](references/python-idioms.md) → "Carry structure — worked examples".

## Two schemas: `deriva-ml` vs your domain schema

A deriva-ml catalog has two kinds of schema, and knowing which is which prevents
most confusion about where a table lives:

- **The `deriva-ml` schema** — 26 fixed tables that back the five abstractions
  (Dataset/Workflow/Execution + the asset and vocabulary machinery).
  Library-managed: you extend it only through the `deriva_ml_*` surface and
  through `add_term` on its built-in vocabularies — never by hand-editing these
  tables.
- **Your domain schema** — your project's own tables (`Subject`, `Image`,
  `Specimen`, …), named after the project, created per-project. The asset tables
  and feature tables you create at runtime (`create_asset`, `create_feature`)
  land in the domain schema, not in `deriva-ml`.

For the concrete table-by-table reference — every `deriva-ml` table, its foreign
keys, the FK graph, and the five-abstractions → backing-tables mapping — see the
OKF schema bundle at `references/concepts/index.md`. (For a live visual of a
specific catalog, use `/deriva-ml:browse-erd`.)

## The rule: inheritance with override

The deriva-ml plugin **extends** the deriva plugin. Everything that applies in a Deriva catalog applies in a deriva-ml catalog by default. **Override:** if a deriva-ml surface exists for an operation, prefer it over the equivalent deriva surface. This applies symmetrically on all three planes:

- **Skills:** prefer `/deriva-ml:<skill>` over `/deriva:<skill>` when both exist.
- **MCP:** prefer `deriva_ml_*` MCP tools, prompts, and resources over the equivalent `deriva-mcp-core` tool / prompt / resource.
- **Python API:** prefer `deriva-ml` objects and methods (`DerivaML`, `Dataset`, `Workflow`, `Execution`, `Feature`, the `with ml.create_execution(config) as exe:` context manager, `exe.asset_file_path()`, etc.) over the equivalent `deriva-py` calls (`ErmrestCatalog`, `PathBuilder`, raw entity resource access).

The override boundary is mechanical: "is there a deriva-ml `<thing>` for this?" If yes, use it. If no, the deriva default applies and the LLM should reach for the corresponding `/deriva:<skill>`, `deriva-mcp-core` tool, or `deriva-py` call.

The five abstractions are where the override mostly lands. Mutating Dataset, Workflow, Execution, Feature or Asset rows with the generic `insert_entities` / `update_entities` / `delete_entities` bypasses business-logic validation, FK invariants across the graph, provenance links, dataset version flips, RAG re-indexing and DerivaML audit events. What each of those does, with examples: `references/inheritance-rationale.md`.

## What DerivaML adds on top

Deriva's seven design pillars (see `/deriva:deriva-context`) are about **data design** — how to model your data so it's findable, accessible, interoperable, and reusable. DerivaML adds **process design** — how to run an ML pipeline against that data so the run itself is reproducible. The two are orthogonal: a Deriva catalog with no DerivaML use can be FAIR-by-construction; a DerivaML catalog adds reproducibility-by-construction on top. The mechanism is three abstractions doing complementary jobs: **Datasets pin** which rows the run consumed; **Workflows identify** which script ran them (each execution's `configuration.json` pins the exact commit); **Executions link** the two so any output Feature or Asset traces back to (specific code) × (specific inputs).

The provenance graph is **walkable in one tool call**: `deriva_ml_get_lineage(rid=...)` traces any artifact (Dataset, Asset, Feature value, Execution) back through its producing-execution chain to the root. That's how you answer "how did this come to exist?" without manually walking 5-15 typed-read calls. For audits — every execution that could have contributed, with gaps reported — use the Python `ml.lookup_provenance(rid)`; for which runs labeled a dataset's members, `ml.find_feature_producers(dataset_rid)`; for a shareable one-page report, `deriva-ml-lineage --rid …`. All three are covered in `/deriva-ml:compare-model-runs` → "Trace an artifact's provenance". Conversely, when you're about to run an experiment and want to confirm the config is valid before paying the bag-download cost of `dry_run=True`, use `deriva_ml_validate_execution_configuration(config=...)` — the cheap metadata-only pre-flight gate.

## Python API method naming: `find_*` vs `list_*`

`find_*` searches the catalog for entities of a kind (its argument is a *filter*); `list_*` enumerates entities scoped to a specific parent (its first argument *is* the scope). The full taxonomy with examples lives in `/deriva-ml:api-naming-conventions` *(auto-loaded)* — consult it when choosing a method.

## Built-in DerivaML vocabularies

Controlled vocabularies are how DerivaML types its abstractions — consumers dispatch on `Dataset_Type == "Training"`, not on a name string, and a term's `{project}:{RID}` CURIE survives catalog clones. Adding a term is the sanctioned way to add a new *kind* of thing.

- **User-extensible:** `Dataset_Type`, `Workflow_Type`, `Asset_Type`. Add terms with the generic `add_term(..., schema="deriva-ml", table=...)`. Then run `deriva_ml_reindex_vocabularies` so the term shows up in `rag_search` (a discoverability refresh — the term is usable immediately).
- **System-managed — do NOT extend:** `Execution_Status`, `Asset_Role`, `Feature_Name`. The execution, upload and feature machinery writes these.
- **Domain vocabularies** (`Sample_Type`, `Image_Quality`, …): the same `add_term`, with your domain schema name (`/deriva:manage-vocabulary`).

The inheritance rule still applies: `add_term` is generic, but the lifecycle of Datasets, Workflows, Executions, Features and Assets goes through the `deriva_ml_*` tools. Per-vocabulary call examples, the reindex detail and the system-managed values: `references/built-in-vocabularies.md`.

### Creating a new vocabulary: prefer `deriva_ml_create_vocabulary`

On a deriva-ml catalog, create a new vocabulary table with `deriva_ml_create_vocabulary`, not core's generic `create_vocabulary`. The ML version scopes the CURIE prefix to the project (stable `{project}:{RID}` identifiers across clones), defaults to the domain schema, and refreshes the Chaise navbar. Then add terms with `add_term`. The generic tool stays right for non-deriva-ml catalogs (`/deriva:manage-vocabulary` *(deriva-skills)*). Example call: `references/built-in-vocabularies.md`.

## The entity resolution workflow

This applies to **any catalog entity** referenced by name — tables, columns, vocabulary terms, datasets, workflows, executions, features, assets. When the user names one, or asks to create one:

1. **Exact match first.** A case-sensitive exact match on a canonical name: use it, no search. (`"Training"` is the `Dataset_Type` term; `"training"` is not.)
2. **Search when it's fuzzy.** Descriptive, abbreviated, misspelled or unfamiliar phrasing → `rag_search` (`catalog-schema` for tables, columns, features, terms; `catalog-data` for datasets, workflows, executions). Dataset, Workflow and Execution rows are indexed only once read, so prefer the structured tool first — `deriva_ml_list_datasets(dataset_type=...)`, `deriva_ml_list_executions(status=...)`, `deriva_ml_find_workflow_by_url`.
3. **Several candidates → a picker** of 3–5 (name, one-line description, RID). One clear hit → use it and say what you resolved it to. None → ask. **Never fabricate a name or call `create_*` with a guessed identifier.**
4. **Lookup path ends here** — pass the canonical name or RID on.
5. **Create path:** first show the similar existing entities and ask whether one would do.
6. **Descriptions on create** are non-empty and user-confirmed — never placeholders (`/deriva:generate-descriptions`, `/deriva-ml:generate-descriptions`).

Wrong resolution corrupts data; right resolution costs a round-trip or two — always pay it. The full steps, the read-through-index caveat, and the structured-vs-fuzzy table are in `references/entity-resolution.md`. The find-before-create discipline itself is owned by `/deriva:semantic-awareness` *(deriva-skills, auto-loaded)*.

## Routing notes where both plugins have a surface

For most operations the inheritance rule resolves the routing on its own — if a deriva-ml `<thing>` exists, use it; otherwise the deriva default applies. One genuine ambiguity remains where both plugins legitimately have a surface and the rule alone doesn't pick:

- **Version checks** — `/deriva:troubleshoot-deriva-errors` ("Versioning and updates" section) for the foundation (deriva-py, deriva-mcp-core, deriva plugin); `/deriva-ml:troubleshoot-execution` ("Versioning and updates" section) for the DerivaML layer. Check the foundation first — the DerivaML stack depends on it.

There are two paths for Chaise display annotations: `/deriva:customize-display` *(deriva-skills, interactive MCP-tool path — works on any Deriva catalog)* and `/deriva-ml:use-annotation-builders` *(this plugin, type-safe Python builder classes for production scripts — requires the deriva-ml Python package)*. The choice between them is interactive-vs-script-based, not domain-based.

## Reference files

Read these directly — no need to go through the index first:

- `references/concepts/index.md` — the fixed `deriva-ml` schema at a glance: tables by group, the FK graph, and which tables back each abstraction.
- `references/concepts/table/<Table>.md` — one file per `deriva-ml` table (columns, FKs, seeded terms), named exactly after the table: `Asset_Role.md`, `Asset_Type.md`, `Dataset.md`, `Dataset_Dataset.md`, `Dataset_Dataset_Type.md`, `Dataset_Execution.md`, `Dataset_File.md`, `Dataset_Type.md`, `Dataset_Version.md`, `Directory_Dataset.md`, `Execution.md`, `Execution_Asset.md`, `Execution_Asset_Asset_Type.md`, `Execution_Asset_Execution.md`, `Execution_Execution.md`, `Execution_Metadata.md`, `Execution_Metadata_Asset_Type.md`, `Execution_Metadata_Execution.md`, `Execution_Status.md`, `Feature_Name.md`, `File.md`, `File_Asset_Type.md`, `File_Execution.md`, `Workflow.md`, `Workflow_Type.md`, `Workflow_Workflow_Type.md`.
- `references/concepts/pattern/asset-table.md` — the shape of domain asset tables minted by `create_asset`.
- `references/concepts/pattern/feature-table.md` — the shape of `Execution_{Target}_{Feature}` tables minted by `create_feature`.
- `references/concepts/pattern/vocabulary.md` — controlled vocabularies: user-extensible vs system-managed, `add_term` vs `create_vocabulary`.
- `references/planning-artifacts.md` — the full map of the repo's planning files (design docs, `Experiments.md`, configs, journal), how they link, and keeping them in sync.
- `references/authentication.md` — the Python and MCP authentication checks: code, return shapes, caveats.
- `references/built-in-vocabularies.md` — the six `deriva-ml` vocabularies with per-table `add_term` calls, the reindex detail, system-managed values, and a `deriva_ml_create_vocabulary` example.
- `references/entity-resolution.md` — find-before-create: the six steps in full, the read-through-index caveat, structured vs fuzzy lookup, related skills.
- `references/inheritance-rationale.md` — what raw catalog writes to the five abstractions bypass (validation, FK invariants, provenance, versioning, re-indexing, audit).
- `references/python-idioms.md` — DerivaML Python idioms (typed containers; don't downgrade records to dicts).

## Generic catalog operations (deriva-skills)

DerivaML skills are routed from "Which skill do I start with?" above; `/deriva-ml:using-deriva-mcp` loads itself before the first MCP call. For operations with no DerivaML surface, the `deriva-skills` plugin (assumed loaded):

- `/deriva:deriva-context` — plugin-wide context (the seven design pillars, the stateless model)
- `/deriva:troubleshoot-deriva-errors` — generic catalog troubleshooting
- `/deriva:manage-vocabulary` — generic vocabulary CRUD
- `/deriva:create-table` — custom domain tables
- `/deriva:query-catalog-data` — querying and browsing
