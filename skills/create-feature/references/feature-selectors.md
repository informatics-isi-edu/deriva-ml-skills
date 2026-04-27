# Feature Selectors

How to choose, use, and write feature selectors in DerivaML.

> **Stateless model:** the new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## What is a selector?

A selector is a function that picks one feature value when a record has multiple values for the same feature. This happens when:
- Multiple annotators label the same image
- Multiple model runs produce predictions for the same record
- A relabeling pass creates new values alongside old ones

Without a selector, the API returns ALL values — including duplicates per record.

## Built-in selectors

All selectors live on `FeatureRecord` and work everywhere: catalog queries (`deriva_ml_list_feature_values`, `list_feature_values`), bag queries, and Python API `bag.restructure_assets()`.

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

# Static selectors
features = ml.fetch_table_features("Image", selector=FeatureRecord.select_newest)
features = ml.fetch_table_features("Image", selector=FeatureRecord.select_first)

# Factory selectors — call them to get a selector function
features = ml.fetch_table_features("Image",
    selector=FeatureRecord.select_by_execution("3-XYZ"))

# Majority vote — auto-detects column for single-term features
feat = ml.lookup_feature("Image", "Diagnosis")
RecordClass = feat.feature_record_class()
features = ml.fetch_table_features("Image",
    feature_name="Diagnosis",
    selector=RecordClass.select_majority_vote())

# Or specify column explicitly
features = ml.fetch_table_features("Image",
    feature_name="Diagnosis",
    selector=FeatureRecord.select_majority_vote("Diagnosis_Type"))
```

**With bag restructuring** — same selectors work:

```python
bag.restructure_assets(
    output_dir="./data", group_by=["Diagnosis"],
    value_selector=FeatureRecord.select_newest,
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

```python
from deriva_ml.feature import FeatureRecord

def select_highest_confidence(records: list[FeatureRecord]) -> FeatureRecord:
    """Pick the annotation with the highest confidence score."""
    return max(records, key=lambda r: getattr(r, "Confidence", 0) or 0)
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
    """Score by 70% confidence + 30% recency."""
    max_conf = max(getattr(r, "Confidence", 0) or 0 for r in records)
    def score(r):
        conf = (getattr(r, "Confidence", 0) or 0) / max(max_conf, 1e-9)
        rct = r.RCT or "1970-01-01"
        recency = len(rct)  # rough proxy — longer timestamps are more recent
        return 0.7 * conf + 0.3 * (recency / 30)
    return max(records, key=score)
```

### Using custom selectors

**Python API** — pass directly:

```python
features = ml.fetch_table_features("Image",
    feature_name="Diagnosis",
    selector=select_highest_confidence)

bag.restructure_assets(
    output_dir="./data", group_by=["Diagnosis"],
    value_selector=select_highest_confidence)
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
