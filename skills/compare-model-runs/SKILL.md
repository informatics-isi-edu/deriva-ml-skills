---
name: compare-model-runs
description: "Use when comparing metrics across multiple ML training executions in DerivaML — ranking model runs by accuracy/F1/loss, finding the best of N recent runs, identifying performance regressions, or aggregating results across a sweep. Covers three metric-storage patterns: features-as-scalars (`deriva_ml_list_feature_values(execution_rids=...)` for one-round-trip catalog query), metrics-as-JSONL-asset files (`Metrics_File` asset, download + parse locally), and prediction-CSV-as-`Execution_Asset` (per-execution tabular CSV plus optional per-analysis summary CSV — the deriva-ml-model-template's default pattern). ALSO use for **artifact provenance tracing** — when the question is 'where did this prediction come from', 'what code produced this asset', 'what dataset version trained this model', or 'why is this metric different from the last run' — `deriva_ml_get_lineage` walks the full data-flow chain in one call; the worked example shows the two-step pattern (lineage walk → workflow resource fetch) that yields the workflow's git URL + commit hash. Auto-fires at the evaluation moment — after a run finishes, on questions like 'which run was best', 'did that change help', 'is this a regression'. Do NOT use for running an execution (use execution-lifecycle) or reading a single run's outputs without comparison (use deriva_ml_list_feature_values directly)."
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

If you can't tell, **ask the user which pattern they're using**. Don't guess.

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

### Step 3: Generate the local Python script

Tell the user to run something like this in a notebook or local Python session (the MCP server has no local filesystem from the calling user's perspective, so it cannot do this for them):

```python
import json

# The analysis runs inside its own execution, so the downloads are
# recorded as inputs. `execution` is created via run_notebook(...) —
# see the `run-notebook` skill. `download_asset` is an Execution
# method; there is no non-execution `ml.download_asset`.

execution_to_metrics_asset = {
    "1-EXEC-A": "1-ASSET-A",
    "1-EXEC-B": "1-ASSET-B",
    # ... fill in from Step 2 results
}

results = {}
for exec_rid, asset_rid in execution_to_metrics_asset.items():
    # Download the JSONL file (recorded as an input of this execution)
    local_path = execution.download_asset(asset_rid)

    # Parse one JSON object per line
    records = []
    with open(local_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # Pick out the metric of interest -- conventionally the LAST record
    # (final epoch) is the "final" result, but the actual aggregation
    # depends on the user's recording convention.
    final = records[-1] if records else {}
    results[exec_rid] = final.get("accuracy")  # or "f1", "loss", etc.

# Rank
ranked = sorted(results.items(), key=lambda x: x[1] or 0, reverse=True)
for rid, score in ranked:
    print(f"  {rid}: accuracy = {score}")
```

### Step 4: Have the user paste the output back

Once the user runs the script and pastes the results back into the conversation, present the ranking to them. If the metric column isn't `"accuracy"`, ask which field they recorded.

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

### Worked example: from a prediction asset back to the workflow's git commit

A common ML-developer question: "I want to reproduce this prediction. What dataset version was used, and what code (git commit) produced it?" The lineage tool gets you most of the way there, but the **workflow's URL and git checksum are not in the lineage payload** — the lineage-specific `WorkflowSummary` only carries `rid` and `name` (intentionally compact; drill into the full record with a second call). The full two-step pattern:

```
# Step 1 — walk the lineage from the asset
deriva_ml_get_lineage(hostname="data.example.org", catalog_id="1", rid="2-PRED1")
```

The response shape is `{"root": {...}, "lineage": {...}, "executions_visited": N, "walked_complete": true, "cycle_detected": false, "depth_capped": false}`. The `lineage` field is a tree of `LineageNode`s. Each node has:

- `execution.rid`, `execution.description`, `execution.status`
- `execution.workflow.rid`, `execution.workflow.name` — but NOT URL or checksum
- `consumed_datasets` — list of `{rid, description, version}`
- `consumed_assets` — list of `{rid, filename, asset_table}`
- `parents` — recursively, the producing executions of consumed datasets and assets
- `already_shown` — true when the node was already rendered earlier in the tree (cycle-safety / dedup)

So the lineage tells you "asset `2-PRED1` was produced by execution `2-EXE1`, which consumed dataset `1-ABCD` at version `1.2.0` and was driven by workflow `2-WF01` named 'ResNet50 Training'." But not the git URL or commit.

```
# Step 2 — fetch the workflow record(s) named in the lineage
ReadMcpResourceTool(server="<name>", uri="deriva://catalog/data.example.org/1/deriva-ml/workflow/2-WF01")
```

The workflow resource returns the full record including `url` (the source-code URL, typically a GitHub blob URL pinned to a commit, e.g. `https://github.com/org/repo/blob/abc123/train.py`) and `checksum` (the git commit hash). The URL is the reproducible-code reference; the checksum is the integrity check.

**End-to-end summary table you can render for the user** (after both calls):

| Field | Source |
|-------|--------|
| Prediction asset RID | The starting RID you passed |
| Producing execution | `lineage.execution.rid` (immediate producer in the tree) |
| Training dataset | `lineage.consumed_datasets[0].rid` |
| Training dataset version | `lineage.consumed_datasets[0].version` |
| Workflow | `lineage.execution.workflow.rid` + `.name` |
| Code URL | workflow resource → `url` field |
| Code git commit | workflow resource → `checksum` field |

If the prediction depends on an upstream chain (the training execution itself consumed a dataset produced by a preprocessing execution, etc.), the same fields apply at each `parents` level of the tree.

**For per-row feature-value provenance** (e.g. "which execution wrote *this specific* `Image_Quality` value?"), pass the feature value's RID — every feature value has an RID and the tool walks it the same way. See `/deriva-ml:create-feature` for how feature values get their producing-execution link in the first place.

## Related skills

- **`execution-lifecycle`** — How executions are created and what metadata they carry. Read this first if the user is running NEW experiments rather than analyzing past ones.
- **`create-feature`** — How to define a Feature for metrics-as-scalars. Useful if the user wants to ADD this pattern to their workflow.
- **`work-with-assets`** — How to download asset bytes locally. Phase 2B's local-Python step is in this skill's domain.
- **`troubleshoot-execution`** — When the recent runs returned by `list_executions` aren't in `Uploaded` state and you need to diagnose why. Routes provenance-tracing questions back to this skill.
