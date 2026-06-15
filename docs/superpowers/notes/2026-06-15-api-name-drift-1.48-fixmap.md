# deriva-ml-skills ↔ deriva-ml 1.48 API-name drift — verified fix map

**Date:** 2026-06-15
**Basis:** deriva-ml checked out at v1.48.0 (`/Users/carl/GitHub/DerivaML/deriva-ml`).
Every mapping below verified against 1.48 source + `hasattr` runtime checks.
The venv's `__version__` reports `1.43.2` (stale setuptools_scm metadata) but
imports the v1.48.0 `src/` editable install.

This sweep was triggered by the deriva-ml 1.48 update. The drift predates 1.48
in several cases (denormalize family, feature_values retirement) — it had
simply never been audited.

## Tier 1 — clean renames (safe; method exists on the same class, new name)

Apply to EVERY occurrence (Python-call form only — `bag.`/`dataset.`/`ml.` prefixed
or prose naming the Python method; do NOT touch `deriva_ml_*` MCP-tool names).

| Wrong (Python method) | Correct 1.48 method | On classes |
|---|---|---|
| `denormalize_as_dataframe` | `get_denormalized_as_dataframe` | Dataset, DatasetBag |
| `denormalize_as_dict` | `get_denormalized_as_dict` | Dataset, DatasetBag |
| `denormalize_columns` | `list_denormalized_columns` | Dataset, DatasetBag |
| `denormalize_info` | `describe_denormalized` | Dataset, DatasetBag |

Note: `ml.denormalize_info(...)` occurrences are doubly wrong — `describe_denormalized`
is NOT on the `DerivaML` facade. Rewrite to `dataset.describe_denormalized(...)` /
`bag.describe_denormalized(...)` (operate on a Dataset/DatasetBag, not `ml`).

Single-occurrence clean renames:
| Site | Wrong | Correct |
|---|---|---|
| dataset-lifecycle/SKILL.md:206 | `ml.find_dataset("2-XXXX")` | `ml.lookup_dataset("2-XXXX")` |
| create-feature/references/workflow.md:110 | `ml.find_workflow_by_url(url)` | `ml.lookup_workflow_by_url(url)` |
| dataset-lifecycle/references/concepts.md:839 | `dataset.list_dataset_relations()` (Python col) | `dataset.list_dataset_children()` / `list_dataset_parents()` |
| execution-lifecycle/references/concepts.md:287,288,291 | `execution.list_execution_children/parents(...)` (Python) | MCP-tool-only: rewrite as `deriva_ml_list_execution_children/parents(...)` calls or note they are MCP tools, not Execution methods |

## Tier 2 — signature/shape rewrites (NOT find/replace; rewrite the call)

### §1b — `fetch_table_features` and Python `list_feature_values` retired → `feature_values`
1.48 method (identical on DerivaML, Dataset, DatasetBag):
```
feature_values(table, feature_name, selector=None, materialize_limit=None, execution_rids=None) -> Iterable[FeatureRecord]
```
- `bag.fetch_table_features("Image")` → needs a feature_name; rewrite per context to
  `bag.feature_values("Image", "<FeatureName>")`. Where the example fetched "all features
  on a table" generically, note that 1.48 reads ONE feature per call (loop over feature names).
- `ml.list_feature_values("Image","Scouts_Pick")` → `ml.feature_values("Image","Scouts_Pick")`
  (return is now an iterator of FeatureRecord, not a list of dicts — adjust surrounding prose).
- Keep the MCP tool `deriva_ml_list_feature_values` references AS-IS (real tool).

### §1h — `select_by_workflow` is a selector FACTORY, not an `ml` instance method
Wrong: `ml.select_by_workflow(records, wf)`.
Correct: pass it as the `selector` to `feature_values`:
```
ml.feature_values("Image", "Diagnosis", selector=FeatureRecord.select_by_workflow(workflow_rid))
```
`FeatureRecord.select_by_workflow(workflow, *, container=...)` returns a callable selector.
(create-feature/references/concepts.md:361,373,398,412,413)

### §1c — `ml.download_asset(rid)` does not exist (download_asset is Execution-only)
There is NO non-execution `DerivaML.download_asset` in 1.48. Rewrite each `ml.download_asset`
to `exe.download_asset(rid)` inside an execution context, OR `ml.download_dir()` +
the execution pattern, per surrounding context. Sites: work-with-assets/SKILL.md:21,41 +
references/concepts.md:64,102,204 + references/restructure-guide.md:213 + references/workflow.md:97 +
scripts/download_asset.py:11; compare-model-runs/SKILL.md:201 + references/jsonl-asset-pattern.md:101,154 +
references/prediction-csv-pattern.md:129,282,285; execution-lifecycle/references/concepts.md:318.
NOTE: compare-model-runs:282-285 deliberately contrasts `ml.` vs `execution.` download — that
framing is now invalid (only the execution form exists); rewrite the contrast accordingly.

### §3 — `dataset.set_version()` / `ds.find_version()` do not exist
1.48 binds a version via a `version=` kwarg on operations, or `DatasetSpec(rid=, version=)`.
- `versioned = dataset.set_version("1.0.0"); versioned.list_dataset_members()`
  → `dataset.list_dataset_members(version="1.0.0")`
  (dataset-lifecycle/references/concepts.md:508,719)
- `ds.find_version("1.0.0")` (dataset-lifecycle/SKILL.md:207) → there is no version-lookup
  returning a bound object; rewrite to pass `version=` to the subsequent operation, or use
  `DatasetSpec(rid=ds.dataset_rid, version="1.0.0")` where a spec is consumed.

### §ambiguous prose — `ml.find_workflow_executions()`
execution-lifecycle/references/concepts.md:86 (prose). Real DerivaML method is
`list_workflow_executions` / `find_executions`. Rewrite the Python framing to
`ml.list_workflow_executions(workflow)` (the MCP tool `deriva_ml_find_workflow_executions`
stays as-is everywhere else).

## DO NOT TOUCH (verified correct — renaming would BREAK content)
- All `deriva_ml_*` MCP-tool names (list_dataset_relations, find_workflow_by_url,
  list_execution_children/parents, list_feature_values, list_features, etc. — real tools).
- `exe.`/`execution.`-prefixed: commit_output_assets, asset_file_path, download_asset,
  metrics_file, update_status, abort, add_nested_execution, list_input_datasets — all real.
- `ml.find_datasets()` (plural) — real. `FeatureRecord.select_by_workflow` as a selector — real.
- `deriva-ml-context:181,185` "there is no `ml.list_features()`" — intentional, correct.
