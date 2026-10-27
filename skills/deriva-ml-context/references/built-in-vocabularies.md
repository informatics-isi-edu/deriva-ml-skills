# Built-in DerivaML vocabularies

The built-in vocabularies in the `deriva-ml` schema hold the system and experiment terms that classify DerivaML entities: datasets, workflows, assets, and executions each carry terms from them. That classification is what makes entities **findable, filterable, and stable** — a consumer dispatches on `Dataset_Type == "Training"`, not on a name string, and the term's `{project}:{RID}` CURIE survives catalog clones. Extending a vocabulary (adding a term) is therefore the sanctioned way to add a new *kind* of thing, distinct from going around the abstractions with raw inserts.

The `deriva-ml` schema has **six** controlled-vocabulary tables, split by who writes them:

**User-extensible** — add terms via the generic `add_term` tool, passing `schema="deriva-ml"` and the `table=`:

| Vocabulary | How to add a term | Notes |
|---|---|---|
| `Dataset_Type` | `add_term(hostname=..., catalog_id=..., schema="deriva-ml", table="Dataset_Type", name=..., description=...)` | Tag your dataset with this term via `deriva_ml_create_dataset(dataset_types=[...])` |
| `Workflow_Type` | `add_term(hostname=..., catalog_id=..., schema="deriva-ml", table="Workflow_Type", name=..., description=...)` | Pass to `deriva_ml_create_workflow(workflow_type=...)` |
| `Asset_Type` | `add_term(hostname=..., catalog_id=..., schema="deriva-ml", table="Asset_Type", name=..., description=...)` | Tag specific assets via `deriva_ml_update_asset(...)` |

> **After adding terms, reindex for discoverability.** `add_term` (and `delete_term`)
> fire **no** RAG re-index hook — so a new term is FK-usable *immediately* (you can
> tag a dataset/workflow/asset with it right away) but will **not** surface in
> `rag_search` until you run the MCP tool `deriva_ml_reindex_vocabularies`. This is a
> **discoverability refresh, not a correctness step**. It applies wherever terms are
> added: a session `add_term`, a `create-feature` vocabulary, or a from-scratch
> loader's term-seeding (the loader case runs it as an explicit post-load step,
> since the loader's Python `ml.add_term` likewise doesn't reindex — see
> `/deriva-ml:setup-ml-catalog`). Creating the vocabulary *table* itself via
> `deriva_ml_create_vocabulary` *does* self-reindex; only per-term `add_term` needs
> the manual refresh.

**System-managed — do NOT extend** (populated by the machinery, not by you):

| Vocabulary | Managed by |
|---|---|
| `Execution_Status` | the execution-state machine — values `Created`, `Running`, `Stopped`, `Failed`, `Pending_Upload`, `Uploaded`, `Aborted`, driven by the `with ml.create_execution(...) as exe:` context manager + `exe.commit_output_assets()`. |
| `Asset_Role` | the upload/download machinery — `Input` / `Output`, set on each asset's `*_Execution` association automatically. |
| `Feature_Name` | `deriva_ml_create_feature` / `create_feature` — one term per feature you create, registered for you. |

For the per-table detail (FKs, full seeded-term lists) see `ml-schema.md` (the "Vocabulary" tables); for the mechanism — controlled-vocab-as-extension-point, `add_term` vs `create_vocabulary`, built-in vs domain vocabs — see `ml-schema.md` → "Pattern: controlled vocabulary".

The inheritance rule still applies: even though you are using the generic `add_term` for the term itself (no deriva-ml override exists for it), the **lifecycle of Datasets / Workflows / Executions / Features / Assets** must go through the `deriva_ml_*` tools.

For all *other* vocabularies (your own domain vocabs like `Sample_Type`, `Tissue_Type`, `Image_Quality`), use the same generic `add_term` documented in `/deriva:manage-vocabulary` — pass your domain schema name instead of `"deriva-ml"`.

## Creating a new vocabulary: prefer `deriva_ml_create_vocabulary`

When you need to **create** a brand-new vocabulary table on a deriva-ml-loaded catalog, prefer the ML-aware `deriva_ml_create_vocabulary` over the generic `create_vocabulary` from deriva-mcp-core. Both produce a table of the same physical shape, but the ML version automatically:

- scopes the curie prefix to the deriva-ml project name (so terms get stable `{project}:{RID}` identifiers that survive catalog clones),
- defaults to the domain schema (so the new vocab lands next to your other domain entities, not in `public`),
- refreshes the catalog navbar so the new vocab is visible in Chaise immediately.

```
deriva_ml_create_vocabulary(hostname=..., catalog_id=...,
    vocab_name="Tumor_Grade", comment="Histological tumor grading scale")
```

Then call `add_term` (from deriva-mcp-core — no ML-specific variant) for each term. The generic `create_vocabulary` remains the right call on **non-deriva-ml catalogs**; reach for it via `/deriva:manage-vocabulary` *(deriva-skills)*.
