# Entity Resolution: Expanded Rationale and Examples

**Contents**

- [Why this workflow matters](#why-this-workflow-matters)
- [Read-through-index caveat for Dataset / Workflow / Execution rows](#read-through-index-caveat-for-dataset--workflow--execution-rows)
- [Structured-vs-fuzzy path selection](#structured-vs-fuzzy-path-selection)
- [The six steps in full](#the-six-steps-in-full)
- [Related always-on skills](#related-always-on-skills)

This reference carries the depth behind the six-step entity-resolution workflow
in `SKILL.md` ("The entity resolution workflow"). The steps themselves stay
inline in the skill — read those first. This document explains *why* the
workflow is shaped the way it is and supplies the detailed caveat and examples
that would bloat the always-on context.

## Why this workflow matters

The cost of getting it wrong:
- **Fabricating a name** leads to FK-violation errors at best, or silent data corruption at worst (e.g. a typo'd `"Trianing"` Dataset_Type that creates a duplicate vocab term).
- **Skipping the picker** when there are multiple matches lets the LLM commit the user to an entity they didn't intend.
- **Empty descriptions** destroy catalog discoverability — a catalog with 500 datasets all described as `""` is indistinguishable from a catalog with 500 datasets nobody can find.

The cost of doing it right is one or two extra round-trips per operation. **Always prefer the round-trips.**

## Read-through-index caveat for Dataset / Workflow / Execution rows

These three entity types are indexed **read-through** — a row enters the
`catalog-data` index only once it has been listed or fetched (the
`deriva_ml_list_*` / `deriva_ml_get_*` tools warm each row they return), or
after a mutation (surgical reindex), or via
`deriva_ml_reindex_rows(hostname, catalog_id)` to warm a whole catalog's rows
on demand. So a bare `rag_search(doc_type="catalog-data")` can miss rows nobody
has touched since the server started.

Prefer the **structured path first** — it's deterministic *and* warms the
index:

- **"find Training datasets"** → `deriva_ml_list_datasets(dataset_type="Training")` (exact type filter; no fuzzy needed).
- **executions by status / workflow type** → `deriva_ml_list_executions(status=..., workflow_type=...)`.
- **workflow dedup / "is this workflow already here?"** → `deriva_ml_find_workflow_by_url` — it matches an existing row by URL or by the script file's checksum, so it's the exact, deterministic dedup check — strictly better than fuzzy `rag_search`.
- **hybrid** ("Training datasets matching `<description text>`") → structured `deriva_ml_list_datasets(dataset_type=...)` to narrow, then `rag_search` to rank within the warmed result.

Vocabulary terms and schema are indexed catalog-wide and searchable immediately
— the read-through caveat applies only to the Dataset/Workflow/Execution data
rows.

## Structured-vs-fuzzy path selection

| Situation | Preferred path |
|-----------|---------------|
| Exact canonical name known (case-sensitive match) | Use it directly — no search needed |
| Descriptive phrase / abbreviation / fuzzy | `rag_search` with `doc_type="catalog-schema"` (schema/vocab) or structured list tool first (data rows) |
| Dataset by type | `deriva_ml_list_datasets(dataset_type=...)` — deterministic, warms index |
| Workflow dedup | `deriva_ml_find_workflow_by_url` — exact match on URL or script checksum, strictly better than fuzzy |
| Execution by status/type | `deriva_ml_list_executions(status=..., workflow_type=...)` |
| Multiple RAG candidates | Show a 3–5 item picker with canonical name + description + RID; let the user pick |
| No RAG hits | Ask a clarifying question — do NOT fabricate |

The "do NOT fabricate" row is the entity-resolution instance of the SKILL's
canonical rule (deriva-ml-context → "Never guess — ground truth is observable"):
a name you can't resolve is a name to look up or ask about, never to invent.

The find-before-create discipline that governs all of these choices is owned by
`/deriva:semantic-awareness` *(deriva-skills, auto-loaded)*.

## The six steps in full

Moved from `SKILL.md` → "The entity resolution workflow", which keeps a one-line version of each step.

When the user mentions an entity by name, OR when the user asks to create a new one, follow these steps:

1. **Exact match first.** If the user-supplied string matches a known canonical name exactly (case-sensitive), use it. Don't search, don't ask. Catalog names are case-sensitive: `"Training"` is the `Dataset_Type` term; `"training"` is not.

2. **Semantic search if ambiguous, fuzzy, or descriptive.** If the user's phrasing doesn't match a canonical name exactly — it's descriptive (`"the training data type"`), abbreviated (`"DR"`), misspelled (`"Diagnossis"`), or just unfamiliar — call `rag_search` with their phrase. Use the appropriate `doc_type`:

   - `catalog-schema` for tables, columns, features, vocabulary terms
   - `catalog-data` for datasets, workflows, executions
   - `ml-docs` / `user-guide` for documentation references

   **Read-through caveat for Dataset / Workflow / Execution rows.** These three are indexed **read-through** — a row enters the `catalog-data` index only once it has been listed or fetched (the `deriva_ml_list_*` / `deriva_ml_get_*` tools warm each row they return), or after a mutation (surgical reindex), or via `deriva_ml_reindex_rows(hostname, catalog_id)` to warm a whole catalog's rows on demand. So a bare `rag_search(doc_type="catalog-data")` can miss rows nobody has touched since the server started. Prefer the **structured path first** — it's deterministic *and* warms the index:

   - **"find Training datasets"** → `deriva_ml_list_datasets(dataset_type="Training")` (exact type filter; no fuzzy needed).
   - **executions by status / workflow type** → `deriva_ml_list_executions(status=..., workflow_type=...)`.
   - **workflow dedup / "is this workflow already here?"** → `deriva_ml_find_workflow_by_url` — workflows are content-addressed (same URL + git commit = same row), so this is the exact, deterministic match, strictly better than fuzzy `rag_search`.
   - **hybrid** ("Training datasets matching `<description text>`") → structured `deriva_ml_list_datasets(dataset_type=...)` to narrow, then `rag_search` to rank within the warmed result.

   (Vocabulary terms and schema are indexed catalog-wide and searchable immediately — the read-through caveat applies only to the Dataset/Workflow/Execution data rows.)

3. **Present a picker when multiple options appear.** If RAG returns more than one plausible candidate, list 3-5 of them with their canonical name + one-line description + RID (or `table.column` for column hits) and ask the user to pick. Don't choose blindly when reasonable people might disagree. If RAG returns ONE clear top hit (significantly above runners-up), use it but tell the user what you resolved it to in one sentence (`"I'm using the Training Dataset_Type."`). If RAG returns NO useful hits, ask a clarifying question. **Do NOT fabricate a name; do NOT call `create_*` with a guessed identifier.**

4. **Lookup path ends here.** With the canonical entity in hand, call the relevant `lookup_*` / `get_*` / `find_*` tool, or pass the canonical name / RID to whatever operation the user requested.

5. **Create path has one more step.** If you arrived here because the user asked to CREATE a new entity, before actually calling `create_*`, surface the candidates from step 3 to the user explicitly:

   > "I found these similar existing entities: `<list>`. Would modifying or reusing one of these work, or do you want to create a new one?"

   If the user picks an existing one, switch to the lookup path. If the user confirms a new one is needed, proceed to step 6.

6. **Description handling on create.** Every `create_*` / `add_*` tool that accepts a `description` (or `comment`) argument SHOULD receive a non-empty, user-confirmed one — never empty, never placeholder text like `"TODO"`, never a fabricated description without showing the user. The full discipline (gather context → draft → confirm → create) and the autonomous-agent fallback live in the always-on `/deriva:generate-descriptions` (generic entities) and `/deriva-ml:generate-descriptions` (ML entities) skills.

The cost of wrong resolution is data corruption or silent FK errors; the cost of right resolution is one or two extra round-trips. **Always prefer the round-trips.**

## Related always-on skills

Several always-on skills reinforce this workflow:

- **`/deriva:semantic-awareness`** *(deriva-skills)* — **owns the find-before-create discipline**; teaches the synonym/abbreviation/spelling-variant search expansion that step 2 relies on. The discipline applies to ML entities (Datasets, Workflows, Features) as well as generic catalog entities.
- **`/deriva:generate-descriptions`** *(deriva-skills)* — description-generation guidance for generic catalog entities (tables, columns, vocabularies, vocabulary terms).
- **`/deriva-ml:generate-descriptions`** *(this plugin)* — description-generation guidance for DerivaML entities (Datasets, Workflows, Executions, Features, Assets, Experiments). The deriva-skills and this plugin's description skills cover non-overlapping entity sets and share the same generic workflow and quality bar.

This skill links them together into one workflow; the always-on skills cover each half in more depth.
