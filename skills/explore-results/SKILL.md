---
name: explore-results
description: "Read-only inspection of existing DerivaML results without writing code — the domain-scientist read path. Use when the user wants to know what a RID is, where a result came from, what labels or feature values exist on records, which records a model got wrong, or wants a Chaise link to a record."
when_to_use: "Triggers on: 'what is RID X', 'describe this RID', 'where did this prediction come from', 'what produced this', 'what dataset version is behind this', 'trace this asset', 'show me the labels', 'what annotations exist', 'consensus labels', 'browse the feature values', 'show me the images the model got wrong', 'which records were misclassified', 'see this in Chaise', 'open this record', 'give me a link'. Not for authoring (create-feature, execution-lifecycle, dataset-lifecycle), scoring or comparing runs, or reproducing a result from its exact commit and dataset versions (compare-model-runs), or the first-MCP-call cold start (using-deriva-mcp)."
---

# Explore Results in a DerivaML Catalog

The read-only companion for **domain scientists** — inspect a result, trace where
it came from, browse labels, open a record in the browser. Everything here is
observation: this skill never creates or modifies catalog state (for that, see
the authoring skills it points to).

> Every tool and resource below takes the catalog's `hostname=` and `catalog_id=`
> explicitly. **Read-side rule:** fetch the `deriva://…` resource *first* — one
> fetch returns the entity plus its bundled children — and reach for a
> `deriva_ml_*` tool only where the resource doesn't answer the question (the full
> resource table is in `/deriva-ml:using-deriva-mcp`).

## Always render a RID as a click-through link

This rule applies across the plugin. Anywhere a RID appears in Markdown — chat
output **and** any document (design docs, `tacit-knowledge.md`, `Experiments.md`,
READMEs, PRs) — write `[label](cite-url)`, never a bare RID. Take the URL from the
resource row's `cite_url`, or `ml.cite(rid)` when writing from Python. If neither
yields one, use the bare RID and say the link is missing — never construct a URL.
URL forms and snapshot pinning: `references/citation-links.md`.

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

For a **dataset**, the root's producer is its *origin* (the first version's author), and
`root.version_history` lists who touched each later version — so "who made this dataset"
and "who last changed it" are different answers; say which one you're giving. If
`root.origin_recorded` is `false`, say the origin wasn't recorded rather than "nothing
produced it." When the user wants something to **share or archive**, offer the one-page
HTML report: `deriva-ml-lineage --rid <RID> --host <host> --catalog <id> --output lineage.html`.

This is the **domain-scientist entry** to lineage — "what produced this?", answered
simply, then the `cite_url` to see it. When the question is the **developer**
reproduction one — *"what git commit + dataset version produced this, so I can
reproduce it"* — that needs the lineage-walk → per-run-metadata pattern,
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

**"Which images did the model get wrong?"** When the run stored its predictions as
feature values, read them for that run (`execution_rids=[<run RID>]`), then read
the ground-truth feature (`selector="newest"`). Match by record RID and list the
records where the two differ, each with its `cite_url` so the user can open the
image. If the predictions live only in a CSV execution asset, or the set is too
large to read this way, the job is computing rather than browsing; hand it to
`/deriva-ml:compare-model-runs` (prediction-CSV pattern).

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
