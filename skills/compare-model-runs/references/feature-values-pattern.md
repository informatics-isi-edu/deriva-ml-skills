# Pattern A: Comparing Runs via Feature Values

This is the worked example for the metrics-as-feature-values pattern, where the user has defined a Feature with scalar columns like `accuracy`, `f1_score`, `loss`, etc., and each execution writes one row per scoring target.

## When to use

- Per-image / per-record metrics (e.g., per-prediction confidence)
- Catalog-side queryable (RAG can index the values)
- Want to use selectors (`newest`, `by_workflow`) to pick winners

## When NOT to use

- Per-epoch / per-step time-series metrics → use Pattern B (JSONL)
- Rich nested per-eval-cycle records → use Pattern B

## Full worked example: "Find the best F1 of my last 5 training runs"

Assume:
- The workflow RID is `1-WF-CNN-TRAIN`
- The feature is `Performance` on the `Image` table
- The metric column is `f1_score` (a `float8` value column)
- One row per execution (a "summary" feature, written once at end-of-training)

### Step 1: Identify the recent N executions

```
deriva_ml_list_executions(
    hostname="data.example.org",
    catalog_id="1",
    workflow_rid="1-WF-CNN-TRAIN",
    status="Uploaded",
    sort=True,
    limit=5,
)
```

The response is a paginated `executions` list. Each entry has `rid`, `status`, `start_time`, `stop_time`, etc. Capture the RIDs:

```python
import json
recent = json.loads(response)["executions"]
recent_rids = [e["rid"] for e in recent]
# e.g., ["1-EXEC-Z", "1-EXEC-Y", "1-EXEC-X", "1-EXEC-W", "1-EXEC-V"]
```

If `sort=True` returned fewer than 5 (e.g., the workflow only has 3 successful runs), `recent_rids` is just those.

### Step 2: Pull values for all of them in one call

```
deriva_ml_list_feature_values(
    hostname="data.example.org",
    catalog_id="1",
    target_table="Image",
    feature_name="Performance",
    execution_rids=["1-EXEC-Z", "1-EXEC-Y", "1-EXEC-X", "1-EXEC-W", "1-EXEC-V"],
    limit=1000,
)
```

If the feature has one row per execution (the "summary" pattern), the returned `count` is at most 5. If there's one row per (execution, image) (the "per-image" pattern), it's 5 × image_count — possibly thousands. Either way, the default `max_results=50_000` cap is fine for normal compare-runs use.

### Step 3: Aggregate

For one-row-per-execution features:

```python
records = json.loads(response)["records"]
ranked = sorted(
    [(r["Execution"], r["f1_score"]) for r in records],
    key=lambda x: x[1],
    reverse=True,  # best first
)
for rid, score in ranked:
    print(f"  {rid}: f1 = {score:.4f}")
```

For per-image features (one row per image, per execution), aggregate per-execution first:

```python
from collections import defaultdict
import statistics

records = json.loads(response)["records"]
by_exec = defaultdict(list)
for r in records:
    by_exec[r["Execution"]].append(r["f1_score"])

ranked = sorted(
    [(rid, statistics.mean(scores)) for rid, scores in by_exec.items()],
    key=lambda x: x[1],
    reverse=True,
)
```

Common reductions: `mean`, `median`, `min` (worst case), `max`, count of "passes-threshold" labels. Pick what matches the user's question. If they ask "which run was best on average," `mean` is the right choice; "which run had the worst case," `min`.

## Selector shortcut: pick the newest value per (execution, target)

If the feature has multiple rows per (execution, target) — e.g., the same execution wrote three iterations of a value — use the `newest` selector to pick the most recent one before aggregation:

```
deriva_ml_list_feature_values(
    hostname="...",
    catalog_id="1",
    target_table="Image",
    feature_name="Performance",
    execution_rids=[...],
    selector="newest",
    limit=1000,
)
```

The catalog-side reduction happens before pagination, so the response is smaller and clearer.

## Pitfalls

- **The metric column name must match exactly.** If the feature is `f1` and you ask for `f1_score`, you'll get a KeyError when accessing `r["f1_score"]`. Always verify with `deriva_ml_get_feature(...)` first.
- **The `Execution` field is the FK column on the feature row** — usually exposed as `r["Execution"]` (or sometimes the more specific column name in the feature record class). If your feature record has a custom Execution-FK column name, adjust accordingly.
- **`max_results=50_000` may be too low** for catalogs with millions of feature rows AND broad `execution_rids` lists. If you genuinely need more, pass `max_results=200_000` etc. — but consider whether you really want to materialize that much data into the LLM context.
- **Pagination cursoring under `execution_rids=` filter** still works — `next_after_rid` advances within the filtered set. But for compare-runs use cases, you usually want all of it in one page (`limit=1000`), not actual pagination.
