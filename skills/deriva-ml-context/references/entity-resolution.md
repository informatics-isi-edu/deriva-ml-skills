# Entity Resolution: Expanded Rationale and Examples

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
- **workflow dedup / "is this workflow already here?"** → `deriva_ml_find_workflow_by_url` — workflows are content-addressed (same URL + git commit = same row), so this is the exact, deterministic match, strictly better than fuzzy `rag_search`.
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
| Workflow dedup | `deriva_ml_find_workflow_by_url` — content-addressed, strictly better than fuzzy |
| Execution by status/type | `deriva_ml_list_executions(status=..., workflow_type=...)` |
| Multiple RAG candidates | Show a 3–5 item picker with canonical name + description + RID; let the user pick |
| No RAG hits | Ask a clarifying question — do NOT fabricate |

The "do NOT fabricate" row is the entity-resolution instance of the SKILL's
canonical rule (deriva-ml-context → "Never guess — ground truth is observable"):
a name you can't resolve is a name to look up or ask about, never to invent.

The find-before-create discipline that governs all of these choices is owned by
`/deriva:semantic-awareness` *(deriva-skills, auto-loaded)*.
