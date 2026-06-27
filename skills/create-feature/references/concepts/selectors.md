---
type: Concept
title: Feature selectors
description: How to choose, use, and write feature selectors in DerivaML — built-in selectors, the MCP tool, Python API, custom selector functions, and common pitfalls.
---

# Feature selectors

How to choose, use, and write feature selectors in DerivaML.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## What is a selector?

A selector is a function that picks one feature value when a record has multiple values for the same feature. This happens when:
- Multiple annotators label the same image
- Multiple model runs produce predictions for the same record
- A relabeling pass creates new values alongside old ones

Without a selector, the API returns ALL values — including duplicates per record.

When you need to *use* feature values — for training a model, computing metrics, or building a DataFrame — you typically need exactly one value per record. **Feature selection** is the process of choosing which value to keep when multiple exist for the same record and feature.

The choice depends on your use case:
- **Newest** — use the most recent value regardless of source (good for "latest state")
- **By workflow** — use values from a specific workflow type, e.g., only expert annotations or only model predictions
- **By execution** — use values from a specific execution run, e.g., comparing Run A vs Run B

## Feature Selection

### MCP tool: deriva_ml_list_feature_values

The single feature-values tool exposes both the all-values shape and the deduplication options. Returns a JSON dict mapping feature names to lists of feature value records.

Call `deriva_ml_list_feature_values` with:
- `hostname`, `catalog_id`
- `target_table` (required): the target table (e.g., `"Image"`)
- `feature_name` (optional): fetch only a specific feature; if omitted, fetches all features on the table
- One of the following selection options (mutually exclusive):
  - `selector="newest"` / `"first"` / `"latest"` / `"majority_vote"` — built-in selectors
  - `workflow` — a Workflow RID or Workflow_Type name. Filters to values from executions of that workflow, then picks newest
  - `execution` — an Execution RID. Filters to values from that specific execution

If none of `selector`, `workflow`, or `execution` is specified, all values are returned (including duplicates).

### Python API

```python
from deriva_ml.feature import FeatureRecord

# One feature per call. Returns an iterator of FeatureRecord.
# Newest by creation time
features = ml.feature_values("Image", "Diagnosis", selector=FeatureRecord.select_newest)

# Filter by execution RID, then pick newest
features = ml.feature_values(
    "Image",
    "Diagnosis",
    selector=FeatureRecord.select_by_execution("3WY2"),
)

# Materialize the iterator to a list when you need to iterate more than once
values = list(ml.feature_values("Image", "Diagnosis"))
values = list(ml.feature_values(
    "Image", "Diagnosis",
    selector=FeatureRecord.select_newest,
))
```

**Workflow-based selection** uses the `FeatureRecord.select_by_workflow`
selector factory, which needs catalog access — pass it as the `selector`
arg. The `container` is the object you call `feature_values` on (it resolves
the workflow's execution list eagerly via `container.list_workflow_executions`):

```python
# Picks the newest record from any execution of the "Training" workflow,
# one survivor per target RID.
selected = list(ml.feature_values(
    "Image", "Classification",
    selector=FeatureRecord.select_by_workflow("Training", container=ml),
))
```

The MCP tool's `workflow` parameter handles this selection automatically.

**Custom selectors** can implement any logic. The example below is specific to features that have a `Confidence` column — direct attribute access fails loudly (`AttributeError`) if applied to a feature without one, which is what you want:

```python
def select_best(records):
    return max(records, key=lambda r: r.Confidence or 0)

features = ml.feature_values("Image", "Diagnosis", selector=select_best)
```

### Predefined selectors

All selectors live on `FeatureRecord` and work everywhere — catalog queries, bag queries, and Python API `bag.restructure_assets()`. The MCP tool maps string names to selectors automatically.

| Selector | Type | What it does |
|----------|------|-------------|
| `FeatureRecord.select_newest` | Static | Most recent by RCT (creation time) |
| `FeatureRecord.select_first` | Static | Earliest by RCT (original annotation) |
| `FeatureRecord.select_latest` | Static | Alias for `select_newest` (API symmetry) |
| `FeatureRecord.select_by_execution(rid)` | Factory | Filter by execution RID, then newest |
| `RecordClass.select_majority_vote(col)` | Factory | Most common value for column; ties by newest RCT. Auto-detects column for single-term features |
| `FeatureRecord.select_by_workflow(wf, container=ml)` | Factory | Filter by workflow type/RID, then newest. Pass as a `selector=` param. Needs catalog access (resolves the workflow's executions via `container`) |

Import:
```python
from deriva_ml.feature import FeatureRecord
```

### Which selection method should I use?

| I want to... | MCP tool parameter | Python API |
|--------------|-------------------|-----------|
| Latest value per record | `selector="newest"` | `selector=FeatureRecord.select_newest` |
| Earliest value (original) | `selector="first"` | `selector=FeatureRecord.select_first` |
| Majority vote across annotators | `selector="majority_vote"` (requires `feature_name`) | `selector=RecordClass.select_majority_vote()` |
| Values from a workflow type | `workflow="Annotation"` | `selector=FeatureRecord.select_by_workflow("Annotation", container=ml)` |
| Values from a specific workflow RID | `workflow="2-ABC1"` | `selector=FeatureRecord.select_by_workflow("2-ABC1", container=ml)` |
| Values from one execution | `execution="3-XYZ"` | `selector=FeatureRecord.select_by_execution("3-XYZ")` |
| Single feature only | `feature_name="Diagnosis"` | `ml.feature_values("Image", "Diagnosis")` |
| Custom logic | Write a Python script | `selector=my_custom_function` |
| No deduplication | Omit selection params | Omit `selector` |

### Writing custom selectors

When the predefined selectors don't fit, write a Python callable with signature `(list[FeatureRecord]) -> FeatureRecord`. The same signature works for both catalog queries and bag Python API `bag.restructure_assets()`.

`FeatureRecord` is a Pydantic model — its column names are attributes, accessed with the dot operator. The example below is **specific to features that have a `Confidence` column**; if applied to a feature without one, `r.Confidence` raises `AttributeError`, which is the right failure mode (use the right selector for the feature, don't paper over the mismatch).

```python
from deriva_ml.feature import FeatureRecord

# Custom selector: highest confidence
def select_highest_confidence(records: list[FeatureRecord]) -> FeatureRecord:
    return max(records, key=lambda r: r.Confidence or 0)

# Works with catalog queries
features = ml.feature_values(
    "Image", "Diagnosis",
    selector=select_highest_confidence,
)

# Same selector works as a per-feature selector in restructure_assets
bag.restructure_assets(
    asset_table="Image", output_dir="./ml_data",
    targets={"Diagnosis": select_highest_confidence},
)
```

When the MCP tool's built-in selectors are insufficient, write the script, test it, commit it for provenance, then run it. This follows the `generate-scripts` pattern.

### Common pitfalls

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Passing multiple selection options | Error — `selector`, `workflow`, `execution` are mutually exclusive | Pick one |
| Using `selector="newest"` in Python | Wrong — MCP uses strings, Python uses callables | Use `selector=FeatureRecord.select_newest` |
| Expecting `select_by_workflow` on a bag | Fails — needs live catalog access | Use `FeatureRecord.select_first` or filter by execution RID |
| `majority_vote` without `feature_name` | Error — needs to know which feature to look up column info | Always specify `feature_name` with `majority_vote` |
| No selector, surprised by duplicates | Returns ALL values including multiple per record | Add `selector="newest"` or another selection option |
| `workflow="Training"` vs `workflow="2-ABC1"` | Both work — auto-detected as type name vs RID | Just pass whichever you have |
| Using `deriva_ml_list_feature_values` for one feature | Works but returns a dict | Use `ml.feature_values()` (Python API) for an iterator of `FeatureRecord` |

## Built-in selectors

All selectors live on `FeatureRecord` and work everywhere: catalog queries (`deriva_ml_list_feature_values`, `feature_values`), bag queries, and Python API `bag.restructure_assets()`.

| Selector | Type | What it does | When to use |
|----------|------|-------------|-------------|
| `FeatureRecord.select_newest` | Static | Most recent by RCT | Default choice — latest annotation wins |
| `FeatureRecord.select_first` | Static | Earliest by RCT | Preserve original annotation, ignore revisions |
| `FeatureRecord.select_latest` | Static | Alias for `select_newest` | Same as newest, symmetric with `select_first` |
| `FeatureRecord.select_by_execution(rid)` | Factory | Filter to one execution, then newest | Get results from a specific model run |
| `RecordClass.select_majority_vote(col)` | Factory | Most common value; ties by newest RCT | Consensus labeling (multiple annotators) |

### Using built-in selectors

**With MCP tools** — pass the selector name as a string:

```
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis", selector="newest")
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis", selector="first")
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis", selector="majority_vote")
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", execution="3-XYZ")
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1", target_table="Image", workflow="Training")
```

**With Python API** — pass the callable directly:

```python
from deriva_ml.feature import FeatureRecord

# Static selectors (one feature per call; returns an iterator of FeatureRecord)
features = ml.feature_values("Image", "Diagnosis", selector=FeatureRecord.select_newest)
features = ml.feature_values("Image", "Diagnosis", selector=FeatureRecord.select_first)

# Factory selectors — call them to get a selector function
features = ml.feature_values("Image", "Diagnosis",
    selector=FeatureRecord.select_by_execution("3-XYZ"))

# Majority vote — auto-detects column for single-term features
feat = ml.lookup_feature("Image", "Diagnosis")
RecordClass = feat.feature_record_class()
features = ml.feature_values("Image", "Diagnosis",
    selector=RecordClass.select_majority_vote())

# Or specify column explicitly
features = ml.feature_values("Image", "Diagnosis",
    selector=FeatureRecord.select_majority_vote("Diagnosis_Type"))
```

**With bag restructuring** — same selectors work as per-feature selectors in the `targets` dict:

```python
bag.restructure_assets(
    output_dir="./data",
    targets={"Diagnosis": FeatureRecord.select_newest},
)
```

### Mutual exclusivity

`selector`, `workflow`, and `execution` are mutually exclusive on the MCP tool. Pick one.

## Writing custom selectors

When built-in selectors don't fit, write a Python callable with signature:

```python
def my_selector(records: list[FeatureRecord]) -> FeatureRecord:
    ...
```

The function receives all values for one target record and must return exactly one.

### Available attributes on FeatureRecord

Every `FeatureRecord` has:
- **Named feature columns** — attributes matching the feature's column names (e.g., `.Diagnosis_Type`, `.Confidence`, `.Quality_Score`)
- `.Execution` — RID of the execution that produced this value (or `None`)
- `.Feature_Name` — name of the feature
- `.RCT` — ISO 8601 creation timestamp (or `None`). Lexicographic comparison works for ordering

### Example: highest confidence

Direct attribute access on the Pydantic record — `r.Confidence` raises `AttributeError` if applied to a feature without that column, which is the right failure mode (use a selector matched to the feature):

```python
from deriva_ml.feature import FeatureRecord

def select_highest_confidence(records: list[FeatureRecord]) -> FeatureRecord:
    """Pick the annotation with the highest confidence score.

    Requires the feature to have a Confidence column.
    """
    return max(records, key=lambda r: r.Confidence or 0)
```

### Example: specific annotator workflow

```python
def select_expert_annotation(records: list[FeatureRecord]) -> FeatureRecord:
    """Prefer values from 'Expert Review' executions, fall back to newest."""
    experts = [r for r in records if r.Execution and "expert" in str(r.Execution).lower()]
    if experts:
        return FeatureRecord.select_newest(experts)
    return FeatureRecord.select_newest(records)
```

### Example: weighted confidence + recency

```python
from datetime import datetime

def select_weighted(records: list[FeatureRecord]) -> FeatureRecord:
    """Score by 70% confidence + 30% recency.

    Requires the feature to have a Confidence column.
    """
    max_conf = max((r.Confidence or 0) for r in records)
    def score(r):
        conf = (r.Confidence or 0) / max(max_conf, 1e-9)
        rct = r.RCT or "1970-01-01"
        recency = len(rct)  # rough proxy — longer timestamps are more recent
        return 0.7 * conf + 0.3 * (recency / 30)
    return max(records, key=score)
```

### Using custom selectors

**Python API** — pass directly:

```python
features = ml.feature_values("Image", "Diagnosis",
    selector=select_highest_confidence)

bag.restructure_assets(
    output_dir="./data",
    targets={"Diagnosis": select_highest_confidence},
)
```

**MCP tool** — custom selectors can't be passed as strings. Write a Python script that uses the deriva-ml API, commit it for provenance, and run it.

## Common patterns

| Scenario | Selector |
|----------|----------|
| Single annotator per record | No selector needed — but `select_newest` is safe |
| Multiple human annotators | `select_majority_vote` for consensus |
| Human labels + model predictions | `workflow="Annotation"` for human-only, or write custom to prefer humans |
| Relabeling pass | `select_newest` — latest corrections override |
| Preserve original labels | `select_first` — ignore later changes |
| One model run only | `execution="3-XYZ"` to filter to that run |
| A/B model comparison | Run `select_by_execution` twice with different execution RIDs |
| QC pipeline | Custom — filter by execution status or workflow type |

## Common pitfalls

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Using `selector="newest"` in Python | Wrong — MCP uses strings, Python uses callables | Use `selector=FeatureRecord.select_newest` |
| `majority_vote` without `feature_name` | Error — needs to know which feature to look up column | Always specify `feature_name` with `majority_vote` |
| Expecting `select_by_workflow` on a bag | Fails — needs live catalog access | Use `FeatureRecord.select_first` or filter by execution RID |
| No selector, surprised by duplicates | Returns ALL values including multiple per record | Add `selector="newest"` or another selection |
| Custom selector returns None | Error — must return a FeatureRecord | Always return a record, even as fallback |
| Selector that doesn't handle empty list | Error — shouldn't happen but defend | Built-ins handle this; custom should too |
