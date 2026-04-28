---
name: compare-model-runs
description: "ALWAYS use this skill when comparing metrics across multiple ML training executions in DerivaML — ranking model runs by accuracy/F1/loss, finding the best of N recent runs, identifying performance regressions, or aggregating results across a sweep. Covers both metric-storage patterns: features-as-scalars (use `deriva_ml_list_feature_values(execution_rids=...)` for one-round-trip catalog query) and metrics-as-JSONL-asset files (download via Python, parse locally). Triggers on: 'compare runs', 'best model', 'rank executions', 'last 5 runs', 'find best F1', 'compare accuracy across', 'recent training runs', 'model comparison', 'sweep results', 'leaderboard', 'metrics across runs', 'which run got the best', 'training history'."
disable-model-invocation: false
---

# Comparing Model Runs in DerivaML

When users ask "which of my last N runs got the best F1?", "show me the recent training results", or "compare accuracy across these executions," the answer depends on **how the user chose to record their metrics**. DerivaML supports two patterns, and you must pick the right one before retrieving data.

## Stateless model

> The MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Phase 1: Identify which metric-storage pattern is in use

Before you can compare runs, you have to know where the metrics live. DerivaML supports two:

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

### Both patterns may be in use

A project can use both — features for per-image confidence, JSONL for per-epoch loss curves. Pick the one that matches the user's question:

- "Which run had the best accuracy?" → look at the final-epoch JSONL record OR a single-row Feature, depending on which the user populated
- "Which images did each run misclassify?" → Feature values (per-image)
- "Plot training-loss curves across the last 5 runs" → JSONL files

If you can't tell, **ask the user which pattern they're using**. Don't guess.

## Phase 2A — Compare via feature values (single round-trip)

Use this path when metrics are scalar columns on a Feature.

### Step 1: Find the recent N executions of the workflow

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

The response includes the execution's metadata + output assets. Look for entries where `asset_type == "Metrics_File"`. Capture the asset RID for each execution.

You can also use the `deriva://catalog/{h}/{c}/ml/execution/{rid}` resource — same data, no pagination cost.

### Step 3: Generate the local Python script

Tell the user to run something like this in a notebook or local Python session (the MCP server has no local filesystem from the calling user's perspective, so it cannot do this for them):

```python
import json
from deriva_ml import DerivaML

ml = DerivaML(hostname="data.example.org", catalog_id="1")

execution_to_metrics_asset = {
    "1-EXEC-A": "1-ASSET-A",
    "1-EXEC-B": "1-ASSET-B",
    # ... fill in from Step 2 results
}

results = {}
for exec_rid, asset_rid in execution_to_metrics_asset.items():
    # Download the JSONL file
    local_path = ml.download_asset(asset_rid)

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

## Critical rules

1. **Always check which pattern is in use first.** Don't assume features-as-scalars; many projects use JSONL assets and the call sites differ.
2. **Use `sort=True` on `list_executions`** — without it, "the last 5 runs" requires paging to the end of the result set, which is expensive on large catalogs. `sort=True` returns RCT-desc directly.
3. **Use `execution_rids=`** on `list_feature_values` for cross-execution queries — never loop over per-execution calls. The audit measured this as a 5×→1× round-trip improvement.
4. **Do NOT** call `deriva_ml_update_execution(status=..., message=...)` to record metrics — that tool only accepts `description=`. Metrics are written to features (Pattern A) or JSONL assets (Pattern B), not to execution status fields.
5. **Hand off file-byte work to local Python.** The MCP server can find which assets exist (`deriva_ml_get_execution`) but cannot download bytes — that's `work-with-assets` skill territory.
6. **Stop and ask the user** if the metric column or feature name isn't obvious. Hallucinating a column like `f1_score` when the user recorded `f1` will fail the lookup.

## Recovering from common errors

- **`list_feature_values` returns `{"error": "result set exceeds max_results=50000..."}`**: your `execution_rids=` list was too broad, or the feature has hundreds of rows per execution. Narrow the filter (fewer execution RIDs) or raise `max_results=` if you really do want a large materialization.
- **`get_execution` doesn't show a `Metrics_File` asset**: the user used Pattern A (features), not Pattern B. Switch paths.
- **`list_features` doesn't show a feature with scalar metric columns**: the user used Pattern B (JSONL), not Pattern A. Switch paths.
- **The metric column you guessed isn't in the feature schema**: call `deriva_ml_get_feature(...)` and read `value_columns` to see what's actually defined.

## Reference resources

- `references/feature-values-pattern.md` — Worked example for Pattern A with detailed pagination and aggregation handling.
- `references/jsonl-asset-pattern.md` — Worked example for Pattern B with the local Python script template.
- `rag_search("metrics", doc_type="catalog-schema")` — Discover whether a catalog has a `Metrics_File` asset type or a `Metrics` feature defined.

## Related skills

- **`execution-lifecycle`** — How executions are created and what metadata they carry. Read this first if the user is running NEW experiments rather than analyzing past ones.
- **`create-feature`** — How to define a Feature for metrics-as-scalars. Useful if the user wants to ADD this pattern to their workflow.
- **`work-with-assets`** — How to download asset bytes locally. Phase 2B's local-Python step is in this skill's domain.
- **`troubleshoot-execution`** — When the recent runs returned by `list_executions` aren't in `Uploaded` state and you need to diagnose why.
