---
name: explore-results
description: "Use when a user wants to READ or INSPECT existing results in a DerivaML catalog without writing code — the domain-scientist read path. Fire on: inspecting a specific RID / result / artifact ('what is RID X', 'describe this RID', 'what is this'), tracing where something came from ('where did this prediction come from', 'what produced this', 'what dataset version is behind this', 'trace this asset'), browsing labels/annotations on records ('show me the labels', 'what annotations exist', 'what are the consensus labels', 'browse the feature values', 'feature preview'), and opening a record in the browser ('see this in Chaise', 'open this record', 'give me a link to this'). This skill is READ-ONLY — it inspects, it never creates or modifies. Do NOT use for: authoring (creating features/datasets/executions, adding labels → /deriva-ml:create-feature, /deriva-ml:execution-lifecycle, /deriva-ml:dataset-lifecycle); comparing MULTIPLE runs or regression checks (→ /deriva-ml:compare-model-runs); the first-MCP-call cold-start orientation (→ /deriva-ml:using-deriva-mcp); generic 'what is DerivaML' framing (→ the always-on deriva-ml-context)."
---

# Explore Results in a DerivaML Catalog

The read-only companion for **domain scientists** — inspect a result, trace where
it came from, browse labels, open a record in the browser. Everything here is
observation: this skill never creates or modifies catalog state (for that, see
the authoring skills it points to).

> Every tool and resource below takes the catalog's `hostname=` and `catalog_id=`
> explicitly. **Read-side rule:** fetch the `deriva://…` resource *first* — one
> fetch returns the entity plus its bundled children — and reach for a
> `deriva_ml_*` tool only where the resource doesn't answer the question (see
> `/deriva-ml:deriva-ml-context` → "Read-side questions: fetch the resource first").

## Journey 1 — "What is this RID?"

A bare RID whose kind you don't yet know is the one case that starts with a
**tool**, not a resource (you can't pick the right `deriva://…/{entity}/{rid}`
until you know the entity type):

```
deriva_ml_describe_rid(hostname, catalog_id, rid="<rid>")
```

It resolves the RID to its entity kind + a summary. From there, fetch the matching
resource for detail — `ml/dataset/{rid}` (→ Journey 3 for its labels),
`ml/execution/{rid}` (→ Journey 2 for what it produced), `ml/asset/{rid}` — and
read the `cite_url` it returns (→ Journey 4).

## Journey 2 — "Where did this come from?"

Provenance for any artifact (a prediction, a trained-model asset, a dataset
version, a feature value). Lead with the bundled lineage resource:

```
ReadMcpResourceTool(server="<name>",
  uri="deriva://catalog/{hostname}/{catalog_id}/deriva-ml/lineage/{rid}")
```

It returns the provenance chain — which Execution produced the artifact, what it
consumed, recursively. For traversal the resource doesn't cover, or to see a
producing run's full inputs/outputs, use `deriva_ml_get_lineage(hostname,
catalog_id, rid=...)` and `deriva_ml_get_execution(hostname, catalog_id,
execution_rid=...)`.

This is the **domain-scientist entry** to lineage — "what produced this?", answered
simply, then the `cite_url` to see it. When the question is the **developer**
reproduction one — *"what git commit + dataset version produced this, so I can
reproduce it"* — that needs the two-step lineage-walk → workflow-record pattern,
which is owned by `/deriva-ml:compare-model-runs` → "Trace an artifact's
provenance". And when the question is **across runs** — "which run was best", "is
this a regression" — that's `/deriva-ml:compare-model-runs` too. Hand those off;
don't reinvent them here.

## Journey 3 — "Show me the labels / what annotations exist"

Browsing feature values (labels, annotations, scores) on a table's records — the
read side of features. (Authoring features and *adding* values is
`/deriva-ml:create-feature`; this is reading what's there.)

First see what features exist on the table:

```
ReadMcpResourceTool(server="<name>",
  uri="deriva://catalog/{hostname}/{catalog_id}/deriva-ml/features/{table}")
```

Then read the values, choosing a **selector** for the common domain-scientist asks:

```
deriva_ml_list_feature_values(hostname, catalog_id,
  target_table="<table>", feature_name="<feature>", selector="newest")
```

- `selector="newest"` — the latest label per record (most recent annotation).
- `selector="majority_vote"` — the consensus label when multiple annotators or
  runs labeled the same record.
- omit the selector to see *all* values (every annotator's row) for a record.

For how feature values get their producing-execution link, and the full selector
catalog, see `/deriva-ml:create-feature`.

## Journey 4 — "Let me see it in the browser"

Every read above returns a per-row **`cite_url`** — a stable link that opens the
record in **Chaise**, the catalog's web UI. Surface it so a non-coder can click
through to the record instead of reading JSON:

> "Here's the record in Chaise: `<cite_url>`"

To see the whole catalog's shape (tables and how they relate) rather than one
record, use `/deriva-ml:browse-erd`.

## What this skill does NOT do

- **Create or change anything** — features (`/deriva-ml:create-feature`), datasets
  (`/deriva-ml:dataset-lifecycle`), runs (`/deriva-ml:execution-lifecycle`), assets
  (`/deriva-ml:work-with-assets`).
- **Compare multiple runs / regressions** — `/deriva-ml:compare-model-runs`.
- **The deep reproduce-this-result lineage walk** (git commit + dataset version) —
  `/deriva-ml:compare-model-runs` → "Trace an artifact's provenance".
