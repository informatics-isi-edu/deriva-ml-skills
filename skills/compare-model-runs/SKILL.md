---
name: compare-model-runs
description: "Evaluates DerivaML training executions — one run or many — and traces a result back to the exact code and data that produced it. Use when scoring a run (confusion matrix, per-class metrics, judging it against its design), ranking runs by accuracy/F1/loss, checking for regressions, aggregating a sweep, or reproducing a result — including right after a run finishes, at the evaluation moment."
when_to_use: "Triggers on: 'which run was best', 'compare these runs', 'did that change help', 'is this a regression', 'aggregate the sweep', 'evaluate this run', 'confusion matrix', 'per-class accuracy', 'did it confirm the hypothesis', 'which runs used this dataset version', 'reproduce this result', 'what exact commit and dataset version produced this', 'why is this metric different from the last run'. Handles all three metric-storage patterns (feature values, JSONL Metrics_File assets, prediction CSV Execution_Assets) and lineage walks via deriva_ml_get_lineage. Not for running an execution (execution-lifecycle) or just looking at what produced an artifact or what values it holds, without scoring or reproducing (explore-results)."
---

# Comparing Model Runs in DerivaML

When users ask "which of my last N runs got the best F1?", "show me the recent training results", or "compare accuracy across these executions," the answer depends on **how the user chose to record their metrics**. DerivaML supports three patterns, and you must pick the right one before retrieving data.

## Stateless model

> The MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Phase 1: Identify which metric-storage pattern is in use

Before you can compare runs, you have to know where the metrics live. DerivaML supports three:

### Pattern A — Metrics as Feature values (scalar columns on a Feature)

The user defined a Feature (e.g., `Metrics` on the `Image` table, or `Run_Metrics` on a domain-specific scoring table) with one or more value columns (`accuracy`, `f1_score`, `loss`, `auc`, etc.). Each execution's `add_features([record])` call inserts ONE row per scoring target.

This pattern is good when:
- Metrics are per-image / per-record (e.g., per-prediction confidence)
- You want catalog-side queryability — `rag_search` can index the values
- You want to use `selector="newest"` / `select_by_workflow` to pick winners across runs

**Discover whether this pattern is in use:** look for a Feature on a relevant table whose value columns include scalar names like `accuracy`, `f1_score`, `loss`, etc.

```
deriva_ml_list_features(hostname="data.example.org", catalog_id="1", target_table="Image")
deriva_ml_get_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Metrics")
```

If the feature has the scalar columns you need, **use Pattern A** (jump to Phase 2A).

### Pattern B — Metrics as JSONL asset files (`Metrics_File` asset type)

The user wrote `with exe.metrics_file().open("a") as f:` inside the training loop. This creates a JSONL asset (default filename `metrics.jsonl`) under the execution's `Execution_Metadata` asset table, with `Asset_Type = "Metrics_File"`. Each line is one JSON record (typically per-epoch or per-eval-cycle).

This pattern is good when:
- Metrics are time-series (epoch / step / eval-cycle)
- The full record is rich (loss + accuracy + per-class breakdowns + learning rate + …)
- You need the file shape for downstream analysis (TensorBoard, W&B export, etc.)

**Discover whether this pattern is in use:** look for `Metrics_File`-typed assets attached to executions.

```
deriva_ml_get_execution(hostname="data.example.org", catalog_id="1", execution_rid="1-EXEC")
```

The response includes a `metadata` list (or similar) with assets attached to the execution. If you see entries with `asset_type` containing `"Metrics_File"`, **use Pattern B** (jump to Phase 2B).

### Pattern C — Prediction CSV as `Execution_Asset` (+ optional summary CSV)

The user (typically via the `deriva-ml-model-template` reference code) writes a tabular CSV per training execution — `prediction_probabilities.csv` is the conventional filename — with one row per test record (`Image_RID`, `Predicted_Class`, `Confidence`, `prob_<classname>` per class). The asset is on the generic `Execution_Asset` table, **not** `Metrics_File`. Optionally a downstream analysis execution (e.g., a ROC notebook) produces a per-experiment summary CSV (`roc_metrics.csv`) with one row per analyzed experiment.

This pattern is good when:
- The metric of interest is computed from per-record data (ROC, AUC, confusion matrix, calibration) — Pattern A's scalar features don't carry per-record rows
- You want raw predictions preserved on the catalog so future analyses can recompute metrics without rerunning training
- A tabular CSV is more ergonomic than JSONL for the DataFrame workflow downstream (pandas / DuckDB / sklearn)

This is the pattern the `deriva-ml-model-template` ships with by default — users starting from the template will hit Pattern C unless they've explicitly switched to A or B.

**Discover whether this pattern is in use:** list assets attached to an execution and look for tabular CSVs on the generic `Execution_Asset` table.

```
deriva_ml_list_assets(hostname="data.example.org", catalog_id="1", execution_rid="1-EXEC")
```

If the response contains an asset with `asset_table == "Execution_Asset"` and a `Filename` like `prediction_probabilities.csv` (a tabular extension on the generic asset table, NOT `Metrics_File`), **use Pattern C** (jump to Phase 2C).

The three identifying markers together:
- Asset table is the generic `Execution_Asset` (not `Metrics_File`)
- `Filename` ends in a tabular extension (`.csv`, `.tsv`, `.parquet`)
- Content is per-record rows rather than per-execution scalar summary

### Patterns may be combined

A project can use any combination — features for per-image confidence, JSONL for per-epoch loss curves, prediction CSVs for ROC analysis. Pick the one that matches the user's question:

- "Which run had the best accuracy?" → a single-row Feature, the final-epoch JSONL record, or a summary CSV — depending on which the user populated
- "Which images did each run misclassify?" → Feature values (per-image) OR the prediction CSV (per-image)
- "Plot training-loss curves across the last 5 runs" → JSONL files
- "Compute ROC / AUC for each run" → prediction CSVs (Pattern C)
- "Show me a leaderboard from a prior comparison" → summary CSV from Pattern C (if one was already written) or feature values (Pattern A)

If you can't tell, **ask the user which pattern they're using**. Don't guess — the metric-storage pattern is observable in the catalog, not something to assume (the general rule: `deriva-ml-context` → "Never guess — ground truth is observable").

## Phase 2A — Compare via feature values (single round-trip)

Use this path when metrics are scalar columns on a Feature.

### Step 1: Find the recent N executions of the workflow

The tool is right here because the query is filtered (by workflow + status) and you want pagination control. For a quick "what executions exist?" snapshot without filters, prefer `ReadMcpResourceTool(server="<name>", uri="deriva://catalog/{h}/{c}/deriva-ml/executions")` — one round trip, no preflight.

> **Comparing a sweep? Confirm it finished first.** `deriva_ml_multirun_status(hostname, catalog_id, workflow_rid)` returns status counts across every execution of the workflow in one aggregation call — `{"counts": {"Uploaded": 18, "Running": 2, "Failed": 1}, "total": 21}`. Lingering `Running` runs mean the ranking below would be premature; a non-zero `Failed` count tells you how many runs to expect missing from the comparison. (Resource form: `deriva://catalog/{h}/{c}/deriva-ml/workflow/{workflow_rid}/multirun-status`.)

```
deriva_ml_list_executions(
    hostname="data.example.org",
    catalog_id="1",
    workflow_rid="1-WF-TRAINING",
    status="Uploaded",
    sort=True,         # newest-first by record creation time (RCT desc)
    limit=5,
)
```

`sort=True` is the key parameter — it returns newest-first. Without it the result is RID-ascending, which is arbitrary. The default `limit=100` is more than you need; pass `limit=N` to bound the response size.

Capture each `rid` from `payload["executions"]` into a Python list.

### Step 2: Fetch feature values for ALL N executions in a single round-trip

```
deriva_ml_list_feature_values(
    hostname="data.example.org",
    catalog_id="1",
    target_table="Image",
    feature_name="Metrics",
    execution_rids=["1-EXEC-A", "1-EXEC-B", "1-EXEC-C", "1-EXEC-D", "1-EXEC-E"],
    limit=1000,
)
```

`execution_rids=` is the v3.1 batch-filter parameter. The catalog query filters server-side, so you get one round-trip instead of N.

The default `max_results=50_000` cap protects you from accidental wholesale materialization. If your filter still produces more than 50K rows (very rare for compare-runs use cases), you'll get an `{"error": "result set exceeds max_results=50000; pass execution_rids=... to narrow"}` envelope. Either narrow the filter further or raise `max_results`.

### Step 3: Aggregate in Python

The wire response is a flat list of records. Group them by execution and extract the metric column the user asked about:

```python
from collections import defaultdict

records = json.loads(response)["records"]
by_execution = defaultdict(list)
for r in records:
    by_execution[r["Execution"]].append(r)

# For each execution, take the metric value (assumes one row per execution
# in this feature; adjust if your feature is multi-row per execution).
ranked = sorted(
    [(rid, recs[0]["accuracy"]) for rid, recs in by_execution.items()],
    key=lambda x: x[1],
    reverse=True,  # best first
)

for rid, score in ranked:
    print(f"  {rid}: accuracy = {score:.4f}")
```

If the feature has multiple rows per execution (e.g., per-image rather than per-execution), you'll need to aggregate (`mean`, `median`, etc.) before ranking. Use `selector="newest"` on `list_feature_values` if "the most recent value per execution" is the right reduction, or do the aggregation in Python.

## Phase 2B — Compare via JSONL asset files (download + parse locally)

Use this path when metrics are stored as `Metrics_File` assets on `Execution_Metadata`.

This pattern requires **local Python execution** — the MCP wire surface is metadata-only by design (downloading file bytes is delegated to the user's local environment). The skill helps you generate the right Python; the user runs it locally and reports back.

### Step 1: Find the recent N executions of the workflow

Same as Phase 2A Step 1. Use `sort=True, limit=N`.

### Step 2: For each execution, identify the Metrics_File asset RID

```
deriva_ml_get_execution(
    hostname="data.example.org",
    catalog_id="1",
    execution_rid="1-EXEC-A",
)
```

The response includes the execution's metadata + output assets. Look for entries where `"Metrics_File" in asset_types` (membership, not equality — DerivaML auto-adds `Output_File` to the list when assets are uploaded via `commit_output_assets()`, so an equality check would silently miss every match; see `work-with-assets` → "Asset_Type auto-tags"). Capture the asset RID for each execution.

You can also use the `deriva://catalog/{h}/{c}/deriva-ml/execution/{rid}` resource — same data, no pagination cost.

### Step 3: Hand off to local Python — download, parse, rank

The MCP server cannot download bytes; the user runs the analysis locally. The full local-Python script — JSONL download loop, final-epoch extraction, ranking, and the plotting variant for loss curves — is in `references/jsonl-asset-pattern.md` (Steps 3–4).

Key points for this path:
- `execution.download_asset(asset_rid)` is an Execution method (no non-execution `ml.download_asset`).
- Parse one JSON object per line; pick the last record for "final epoch" (or ask the user if their convention differs).
- Have the user paste the ranked output back into the conversation.

## Phase 2C — Compare via prediction CSV assets (download + parse locally)

Use this path when each execution writes a tabular `prediction_probabilities.csv` (or similar) as an `Execution_Asset`. This is the default pattern for projects started from the `deriva-ml-model-template`.

Like Pattern B, the MCP wire surface is metadata-only — actual byte downloads happen in local Python. Two things are different from Pattern B:

1. The discovery tool is `deriva_ml_list_assets(execution_rid=...)` (not `deriva_ml_get_execution`), and you filter by `Filename` plus the `Execution_Asset` table marker.
2. Every execution's prediction file shares the same `Filename`, so each download must go into its own per-RID subdirectory to avoid collisions.

### Step 1: Find the recent N executions of the workflow

Same as Phase 2A / 2B Step 1. Use `sort=True, limit=N`.

### Step 2: For each execution, find the prediction-CSV asset RID

```
deriva_ml_list_assets(
    hostname="data.example.org",
    catalog_id="1",
    execution_rid="1-EXEC-A",
)
```

Filter the response for rows where `asset_table == "Execution_Asset"` and `Filename` matches your convention (default: `prediction_probabilities.csv`). Capture the asset RID for each execution.

### Step 3: Hand off to local Python — download, merge with ground truth, rank

Like Pattern B, the MCP server cannot download bytes; the user runs the analysis locally. The recipe has three moving parts specific to Pattern C:

1. **Per-RID download subdirs are REQUIRED** — every execution's prediction file is named identically, so a flat dir would overwrite. Download each through `execution.download_asset(asset_rid=..., dest_dir=working_dir / "per_asset_downloads" / asset_rid, update_catalog=False)`.
2. **Ground truth is an `Image_Classification`-style feature**, and the ground-truth execution is identified by BOTH predicates together — `Execution == gt_execution` AND `Confidence IS NULL` (labeling writes labels without confidence; training executions always write confidence). Merge GT into each prediction df, then compute accuracy / rank.
3. **(Optional) write a per-analysis summary CSV asset** (`roc_metrics.csv` via `execution.asset_file_path(MLAsset.execution_asset, ...)`) if the comparison is recurring, so the next run reads it directly without recomputing.

For ROC / AUC / confusion-matrix metrics, keep the `prob_<classname>` columns and pass them to `sklearn.metrics.roc_curve` / `auc` / `confusion_matrix`.

The complete local-Python script for all three parts — per-RID download loop, the fingerprint sanity-check, the two-predicate GT merge, the ranking, and the summary-CSV write — is in `references/prediction-csv-pattern.md` (Steps 3–5), which mirrors the model template's canonical `notebooks/roc_analysis.ipynb`. That reference also carries the discovery recipe for finding a prior analysis's summary CSV and the Pattern A migration path.

## Critical rules

1. **Always check which pattern is in use first.** Don't assume features-as-scalars; many projects use JSONL assets or prediction CSVs, and the call sites differ. Projects started from the model template default to Pattern C.
2. **Use `sort=True` on `list_executions`** — without it, "the last 5 runs" requires paging to the end of the result set, which is expensive on large catalogs. `sort=True` returns RCT-desc directly.
3. **Use `execution_rids=`** on `list_feature_values` for cross-execution queries — never loop over per-execution calls. The audit measured this as a 5×→1× round-trip improvement.
4. **Metrics are not execution-row fields.** The Execution row carries provenance (workflow, status, timings, description) — it does not carry metric values. Always write metrics into one of the three patterns above: features (Pattern A), JSONL assets via `exe.metrics_file()` (Pattern B), or prediction CSV assets (Pattern C). The `Description` field on the Execution row is for human-readable run summaries, not numeric metrics.
5. **Hand off file-byte work to local Python.** The MCP server can find which assets exist (`deriva_ml_get_execution`, `deriva_ml_list_assets`) but cannot download bytes — that's `work-with-assets` skill territory.
6. **Stop and ask the user** if the metric column, feature name, or prediction CSV filename isn't obvious. Hallucinating a column like `f1_score` when the user recorded `f1`, or a filename like `predictions.csv` when the user wrote `test_predictions.csv`, will fail the lookup.
7. **For Pattern C, download each asset into its own per-RID subdirectory.** All executions name their prediction file identically (`prediction_probabilities.csv`); a flat download dir will silently overwrite.
8. **Judge the result against the experiment's design, not just the other runs.** "Which run was best" and "did that change help" are comparisons *between* runs; "is this run good / did it confirm the hypothesis" is a comparison against the *plan*. When the experiment has a design doc (`docs/design/experiment/<slug>.md`), read its **Validation** section — the metric, the baseline, and the confirm/refute/inconclusive criteria — and report the comparison against *that*, not just relative ranking. If a metric differs from expectation, the design's hypothesis is what "expected" means; the journal (`tacit-knowledge.md`) and lineage explain what actually happened. Three sources, three jobs: design = intended outcome, journal = what was learned, lineage = the factual data-flow.

## Recovering from common errors

- **`list_feature_values` returns `{"error": "result set exceeds max_results=50000..."}`**: your `execution_rids=` list was too broad, or the feature has hundreds of rows per execution. Narrow the filter (fewer execution RIDs) or raise `max_results=` if you really do want a large materialization.
- **`get_execution` doesn't show a `Metrics_File` asset**: the user used Pattern A (features) or Pattern C (prediction CSV), not Pattern B. Re-check `list_features` and `list_assets`.
- **`list_features` doesn't show a feature with scalar metric columns**: the user used Pattern B (JSONL) or Pattern C (prediction CSV), not Pattern A. Check `get_execution` for a `Metrics_File`, then `list_assets` for a tabular `Execution_Asset`.
- **`list_assets` shows the prediction CSV but the download collides / overwrites**: you forgot the per-RID subdirectory. Pass `dest_dir=working_dir / "per_asset_downloads" / asset_rid` to `download_asset`.
- **The metric column you guessed isn't in the feature schema**: call `deriva_ml_get_feature(...)` and read `value_columns` to see what's actually defined.

## Reference resources

- `references/feature-values-pattern.md` — Worked example for Pattern A with detailed pagination and aggregation handling.
- `references/jsonl-asset-pattern.md` — Worked example for Pattern B with the local Python script template.
- `references/prediction-csv-pattern.md` — Worked example for Pattern C with the per-RID download recipe, ground-truth merge, and the optional summary-CSV migration to Pattern A. The model template's `notebooks/roc_analysis.ipynb` is the canonical implementation in running code.
- `rag_search("metrics", doc_type="catalog-schema")` — Discover whether a catalog has a `Metrics_File` asset type or a `Metrics` feature defined.

## Trace an artifact's provenance

> **Simple "where did this come from?"** — a domain scientist who just wants to *see* what produced an artifact (not reproduce it) starts at `/deriva-ml:explore-results` (Journey 2): the bundled `lineage/{rid}` resource plus the `cite_url` to open the record. The section below is the **developer** depth — the lineage walk → per-run metadata pattern that recovers the code actually run, plus the Python-only closure (`lookup_provenance`), feature-producer (`find_feature_producers`), and HTML-report (`deriva-ml-lineage`) tools.

After comparing runs (or any time the question is "where did this output come from?" or "why does this prediction look wrong?"), walk the data-flow chain in one call:

```
deriva_ml_get_lineage(hostname="data.example.org", catalog_id="1", rid="<asset-or-feature-or-dataset-or-execution-rid>")
```

Returns a tree of producing executions back to the root: which Execution produced this artifact, which Datasets and Assets it consumed, which Executions produced those, recursively. Replaces what would otherwise be 5-15 round-trips through typed reads.

Pass any artifact RID (Dataset, Asset, Feature value, or Execution); the tool auto-detects the type. Pass `depth=N` to cap the walk; default is unbounded. Cycle-safe.

This is the right tool when:

- A model prediction looks wrong and you want to confirm which training dataset version it came from.
- A feature value disagrees with what you expected and you want to identify which annotation execution wrote it.
- Reproducing a result requires confirming the exact (dataset RID, dataset version, workflow RID, workflow git commit) tuple that produced an asset.
- The metric difference between two runs is suspiciously large — often a dataset-version drift (one trained on v0.4.0, another on v0.5.0) or an asset swap (different pretrained checkpoint), and lineage surfaces both immediately.

### Worked example: from a prediction asset back to the code that ran

A common ML-developer question: "I want to reproduce this prediction. What dataset version was used, and what code (git commit) produced it?" The lineage walk answers the dataset half directly. The code half has a trap: **the Workflow record is not per-run code identity.**

```
# Step 1 — walk the lineage from the asset
deriva_ml_get_lineage(hostname="data.example.org", catalog_id="1", rid="2-PRED1")
```

The response shape is `{"root": {...}, "lineage": {...}, "executions_visited": N, "walked_complete": true, "cycle_detected": false, "depth_capped": false}`. The `lineage` field is a tree of `LineageNode`s. Each node has:

- `execution.rid`, `execution.description`, `execution.status`
- `execution.workflow.rid`, `.name`, and (deriva-ml ≥ 1.58) `.url` and `.version` — see the caveat below before trusting the last two
- `consumed_datasets` — list of `{rid, description, version}`
- `consumed_assets` — list of `{rid, filename, asset_table}`
- `parents` — recursively, the producing executions of consumed datasets and assets
- `already_shown` — true when the node was already rendered earlier in the tree (cycle-safety / dedup)

So the lineage tells you "asset `2-PRED1` was produced by execution `2-EXE1`, which consumed dataset `1-ABCD` at version `1.2.0` and was driven by workflow `2-WF01` named 'ResNet50 Training'."

> **Workflow URL / version / checksum are first-registration facts, not per-run facts.** Workflow rows are deduplicated: `create_workflow` reuses an existing row whose `URL` or `Checksum` matches, and `Checksum` is the git **blob** hash of the script file (not a commit hash). So a script whose file content didn't change across many commits keeps pointing at the row — and the commit-pinned `URL` / `Version` — from the *first* run that registered it. This has been observed six months stale in production, pointing at a commit that couldn't even import a module the run demonstrably used. **Never present `workflow.url` / `workflow.version` as "the code this execution ran."**

```
# Step 2 — read the producing execution's run metadata (per-run code identity)
deriva_ml_get_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-EXE1")
```

Every execution records its own run metadata in `Execution_Metadata` (see `/deriva-ml:execution-lifecycle` → authoring "Execution Metadata Auto-Generation"). The `Deriva_Config` asset (`configuration.json`) serializes the workflow **URL / version / checksum as of that run** — the URL is pinned to the commit checked out when the run started. The `Runtime_Env` snapshot's installed-package versions corroborate it, and `Execution_Config` (`uv.lock`) pins the dependency set. Reading those file bytes is local Python (the MCP surface is metadata-only):

```python
rec = ml.lookup_execution("2-EXE1")
for asset in rec.list_metadata():          # deriva-ml ≥ 1.58; Execution_Metadata via a server-side join
    print(asset.asset_rid, asset.filename, asset.asset_types)
    if asset.filename == "configuration.json":
        path = asset.download(dest_dir=Path("run_meta") / asset.asset_rid)
```

Prefer `list_metadata()` over `list_assets()`-and-filter: the latter streams every *output* asset of the run (minutes on a large inference run), and an empty `list_metadata()` result genuinely means "no metadata recorded" — catalog/join failures raise instead of reading as absence.

**End-to-end summary table you can render for the user** (after both steps):

| Field | Source |
|-------|--------|
| Prediction asset RID | The starting RID you passed |
| Producing execution | `lineage.execution.rid` (immediate producer in the tree) |
| Training dataset | `lineage.consumed_datasets[0].rid` |
| Training dataset version | `lineage.consumed_datasets[0].version` |
| Workflow | `lineage.execution.workflow.rid` + `.name` |
| Code URL + commit **as run** | that execution's `configuration.json` (`Deriva_Config`) → workflow `url` / `version` |
| Dependency set | that execution's `uv.lock` (`Execution_Config`) |

If the prediction depends on an upstream chain (the training execution itself consumed a dataset produced by a preprocessing execution, etc.), the same fields apply at each `parents` level of the tree.

### Dataset roots: origin vs. latest writer

When the RID you walk is a **Dataset**, the root carries more than a producer (deriva-ml ≥ 1.58):

- `root.version` — the dataset's current version label (or the pinned one).
- `root.producing_execution` — the **origin**: the author of the *first* recorded `Dataset_Version`, never the execution that last touched it. A later split, migration, or backfill that bumped v4.12.0 → v4.13.0 is not "the producer."
- `root.version_history` — every `Dataset_Version` author, earliest first. This is where later touchers stay visible without being mistaken for the producer.
- `root.origin_recorded` — tri-state. `True` = a real execution is recorded as origin; `False` = the origin is the unknown-provenance sentinel, missing, or there are no version rows; `None` = not a Dataset root. Check `origin_recorded`, not `producing_execution is None`, to tell "unknown provenance" from "no link."

When the origin is unrecorded, the walk seeds from the executions that produced the dataset's member assets instead, so datasets without a recorded origin still return something to trace.

### Shareable HTML report: `deriva-ml-lineage`

When the user wants to *send* the lineage to a reviewer or archive it, render it rather than pasting JSON:

```bash
deriva-ml-lineage --rid 2-PRED1 --host data.example.org --catalog 1 \
    --output lineage.html --json lineage.json
deriva-ml-lineage --input lineage.json --output lineage.html   # re-render offline, no catalog access
```

One self-contained HTML page (inline CSS + SVG walk figure, no JavaScript): root artifact with version and origin badge, the version-attribution trace, the walk tree with each execution's workflow, and feature-producer facts. `--json` is the audit artifact of record. `--no-features` skips the feature-producer scan for a faster render.

### Exhaustive closure: `lookup_provenance` (Python API)

`lookup_lineage` / `deriva_ml_get_lineage` gives a compact trace of one producing chain. For audits, "what could this training run have depended on", or debugging a suspect result, use the **closure** — every execution reachable through any recorded relationship, with an honest list of what couldn't be resolved. Python only (no MCP tool yet; deriva-ml ≥ 1.62):

```python
from deriva_ml.execution import ArcKind

closure = ml.lookup_provenance("2-PRED1")                    # Dataset roots: version="x.y.z" to pin
print(len(closure.executions), len(closure.datasets), len(closure.assets), len(closure.gaps))
print(closure.traversal_complete)

# Fast structural pass — skips the per-dataset binding scans (≈10× faster):
closure = ml.lookup_provenance(rid, arcs=frozenset({
    ArcKind.consumption, ArcKind.version_authorship, ArcKind.member_production}))
```

How to read it:

- **Flat, RID-keyed, deterministic.** `executions` / `datasets` / `assets` are maps; `model_dump()` is byte-identical across calls, so closures diff cleanly.
- **Arcs say *why* an execution is in the closure** — `root`, `consumption`, `version_authorship`, `member_binding`, `member_production`. An execution can carry several. **Arcs are unranked**; don't tell the user one reason is "the real one" unless they give you a policy.
- **Gaps are first-class.** `closure.gaps` lists typed `ProvenanceGap`s (sentinel origins, unpinned inputs, missing/multiple asset producers, workflow-less executions, unresolved RIDs, …). Gaps and `traversal_complete` are independent — check both. `traversal_complete=False` means a budget (`max_executions`, default 500) stopped the walk: partial but honest.
- **Dataset facts are per-version** (`closure.datasets[rid].versions[label]`) — never merge them across versions.
- **Containment is not provenance.** The closure does not walk `Dataset_Dataset` parents; a parent enters only via the consumption arc of the execution that produced the child. For the structural question use `list_dataset_parents` / `list_dataset_children`.
- Slow catalog? `DERIVA_ML_PROVENANCE_WORKERS` (default 8) sets read concurrency; `1` forces sequential. `arcs=` is the bigger lever.

### Which executions labeled this dataset? `find_feature_producers`

A feature value is a *(member, value, execution)* binding — the execution is part of its identity — so the executions that wrote features onto a dataset's members are provenance facts, not guesses. Python only (deriva-ml ≥ 1.58; FK-reachable member scope and snapshot-bound `version=` ≥ 1.61):

```python
for p in ml.find_feature_producers("1-ABCD", version="1.2.0"):   # version= binds to that snapshot
    print(p.execution_rid, p.feature_name, p.element_type, p.value_count)
```

"Members" follows FK-reachability (a subject-partitioned dataset's Image labels count). `execution_rid=None` rows are feature values with no recorded execution — a provenance gap to surface, never drop. With `version=`, labels written after that version are excluded.

**For per-row feature-value provenance** (e.g. "which execution wrote *this specific* `Image_Quality` value?"), pass the feature value's RID — every feature value has an RID and the tool walks it the same way. See `/deriva-ml:create-feature` for how feature values get their producing-execution link in the first place.

## Related skills

- **`execution-lifecycle`** — How executions are created and what metadata they carry. Read this first if the user is running NEW experiments rather than analyzing past ones.
- **`create-feature`** — How to define a Feature for metrics-as-scalars. Useful if the user wants to ADD this pattern to their workflow.
- **`work-with-assets`** — How to download asset bytes locally. Phase 2B's local-Python step is in this skill's domain.
- **`troubleshoot-execution`** — When the recent runs returned by `list_executions` aren't in `Uploaded` state and you need to diagnose why. Routes provenance-tracing questions back to this skill.
