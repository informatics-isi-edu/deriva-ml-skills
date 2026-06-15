# Pattern C: Comparing Runs via Prediction CSV Assets

This is the worked example for the metrics-as-prediction-CSV pattern,
where each training execution writes a tabular `prediction_probabilities.csv`
(or similarly named file) as an `Execution_Asset` with one row per test
record, and a downstream analysis execution optionally produces a per-
experiment summary CSV (`roc_metrics.csv`, etc.).

This is the pattern the `deriva-ml-model-template` ships with by
default. If a user started from the template, they are on Pattern C
unless they have explicitly switched to Pattern A or B.

## Shape on the catalog

Per training execution:

- One `Execution_Asset` row whose `Filename` is something like
  `prediction_probabilities.csv`.
- CSV columns: `Image_RID`, `Predicted_Class`, `Confidence`, plus one
  `prob_<classname>` column per class.
- One row per test image.

Per analysis execution (optional, produced by a downstream notebook or
script):

- One `Execution_Asset` row whose `Filename` is something like
  `roc_metrics.csv`.
- CSV columns: `Experiment`, `Execution_RID`, `Samples`, `Accuracy`,
  plus `AUC_<classname>` per class and `AUC_Micro` / `AUC_Macro`.
- One row per analyzed experiment.

Note: the asset table is the generic `Execution_Asset`, NOT
`Metrics_File`. That is the surest catalog-side marker that you are
on Pattern C and not Pattern B.

## When to use

- Per-record data is intrinsic to the metric (ROC, confusion matrix,
  calibration plots). Pattern A's scalar feature values do not carry
  per-record rows.
- You want to recompute metrics later from raw predictions without
  rerunning training. Pattern B's JSONL can carry per-row data too,
  but a tabular CSV is more ergonomic for DataFrame workflows.
- Downstream analyses will produce derived assets (plots, summary
  CSVs) of their own, and you want the raw predictions preserved for
  forensics.

## When NOT to use

- The only metric you care about is a per-execution scalar
  (`accuracy`, `loss`) and you want catalog-side queryability via
  `list_feature_values` -> use Pattern A.
- Metrics are inherently time-series (per-epoch loss curves, learning
  rate schedules) -> use Pattern B (JSONL).

## Full worked example: "Compute ROC and rank my last 5 CNN runs"

The `notebooks/roc_analysis.ipynb` in the model template is the
canonical working example of this pattern end-to-end. The recipe below
mirrors what that notebook does so you can drive it from an MCP
session and hand off the local-Python steps to the user.

### Step 1: Identify the recent N executions

Same as Patterns A and B.

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

Capture the execution RIDs.

### Step 2: For each execution, find its prediction-CSV `Execution_Asset` RID

`deriva_ml_list_assets` filtered by execution RID is the right tool.
Then filter the response client-side to the rows whose `Filename`
matches your convention.

```
deriva_ml_list_assets(
    hostname="data.example.org",
    catalog_id="1",
    execution_rid="1-EXEC-Z",
)
```

```python
import json

PREDICTION_FILENAME = "prediction_probabilities.csv"

execution_to_prediction_asset = {}
for exec_rid in recent_rids:
    response = await deriva_ml_list_assets(
        hostname="data.example.org",
        catalog_id="1",
        execution_rid=exec_rid,
    )
    payload = json.loads(response)
    assets = payload.get("assets") or []
    for a in assets:
        # Pattern C marker: generic Execution_Asset table + matching Filename.
        if a.get("asset_table") == "Execution_Asset" and a.get("Filename") == PREDICTION_FILENAME:
            execution_to_prediction_asset[exec_rid] = a["rid"]
            break
```

If an execution has no matching asset, the training run either did
not produce a prediction CSV (older code path) or the upload did not
complete. Skip it or report the gap.

### Step 3: Hand off to local Python to download + parse

Like Pattern B, the MCP server cannot download bytes. The user runs
this locally. Two things are different from Pattern B:

1. Each asset must be downloaded into its own per-RID subdirectory
   because every execution's prediction file shares the same
   `Filename` (`prediction_probabilities.csv`). Without per-RID
   directories the downloads collide.
2. The download goes through `execution.download_asset(...)` — an
   Execution method; there is no non-execution `ml.download_asset`.
   The analysis itself is an execution, so `execution.download_asset`
   uses the credential-aware Hatrac path the rest of the execution
   uses and records the download as an input. The analysis notebook's
   `execution` is created via `run_notebook(...)` (see the
   `run-notebook` skill).

```python
import hashlib
from pathlib import Path

import pandas as pd

# From step 2 (paste in the dict the LLM produced)
execution_to_prediction_asset = {
    "1-EXEC-Z": "1-ASSET-PRED-Z",
    "1-EXEC-Y": "1-ASSET-PRED-Y",
    "1-EXEC-X": "1-ASSET-PRED-X",
    "1-EXEC-W": "1-ASSET-PRED-W",
    "1-EXEC-V": "1-ASSET-PRED-V",
}

per_rid_dir = Path(execution.working_dir) / "per_asset_downloads"
per_rid_dir.mkdir(parents=True, exist_ok=True)

dfs = []
for exec_rid, asset_rid in execution_to_prediction_asset.items():
    rid_dir = per_rid_dir / asset_rid
    rid_dir.mkdir(parents=True, exist_ok=True)
    fresh_path = execution.download_asset(
        asset_rid=asset_rid,
        dest_dir=rid_dir,
        update_catalog=False,
    )
    df = pd.read_csv(fresh_path)
    df["execution_rid"] = exec_rid
    df["asset_rid"] = asset_rid
    dfs.append(df)

# Sanity check: two executions should never produce byte-identical
# prediction CSVs. If they do, something is collapsing distinct
# experiments onto the same file -- fail loudly here rather than
# silently produce wrong metrics downstream.
fingerprints = {
    asset_rid: hashlib.md5(Path(p).read_bytes()).hexdigest()
    for asset_rid, p in [(a, df["csv_path"].iloc[0]) for a, df in zip(execution_to_prediction_asset.values(), dfs)]
}
assert len(set(fingerprints.values())) == len(fingerprints), (
    f"Multiple executions returned identical prediction CSVs: {fingerprints}"
)
```

### Step 4: Merge with ground truth and compute the metric

Ground truth lives in an `Image_Classification`-style feature, with
the ground-truth execution identified by `Confidence IS NULL` (the
labeling pass writes labels without confidence scores; training
executions always write confidence). Both filters together are the
contract.

```python
# Pull all Image_Classification feature values, then filter to the
# ground-truth execution.
feature_values = [
    r.model_dump() for r in ml.feature_values("Image", "Image_Classification")
]
feature_df = pd.DataFrame(feature_values)

# Identify the GT execution: the one whose rows all have NULL Confidence.
exec_summary = feature_df.groupby("Execution").agg(
    num_images=("Image", "count"),
    with_confidence=("Confidence", lambda x: x.notna().sum()),
)
gt_execution = exec_summary[exec_summary["with_confidence"] == 0].index[0]

# Both filters: matching execution AND null confidence.
gt_rows = feature_df[
    (feature_df["Execution"] == gt_execution) & feature_df["Confidence"].isna()
][["Image", "Image_Class"]]
gt_lookup = dict(zip(gt_rows["Image"], gt_rows["Image_Class"]))

# Merge into each prediction df.
results = []
for df in dfs:
    df["True_Class"] = df["Image_RID"].map(gt_lookup)
    matched = df.dropna(subset=["True_Class"])
    accuracy = (matched["Predicted_Class"] == matched["True_Class"]).mean()
    results.append({
        "execution_rid": df["execution_rid"].iloc[0],
        "asset_rid": df["asset_rid"].iloc[0],
        "samples": len(matched),
        "accuracy": accuracy,
    })

ranked = sorted(results, key=lambda r: r["accuracy"], reverse=True)
for r in ranked:
    print(f"  {r['execution_rid']}: accuracy = {r['accuracy']:.4f} ({r['samples']} samples)")
```

For ROC / AUC / confusion-matrix metrics that need the full
probability distribution, keep the `prob_<classname>` columns and
pass them to `sklearn.metrics.roc_curve` / `auc` / `confusion_matrix`.
See `notebooks/roc_analysis.ipynb` in the model template for the
full implementation.

### Step 5 (optional): Consolidate into a per-analysis summary CSV asset

If this is a recurring analysis (and not a one-shot grep), writing
the comparison out as its own `Execution_Asset` makes it queryable
later and lets the next analysis pick up where this one left off.

```python
from deriva_ml.core.enums import MLAsset, ExecAssetType

summary_df = pd.DataFrame(ranked)
csv_path = execution.asset_file_path(
    MLAsset.execution_asset, "roc_metrics.csv", ExecAssetType.output_file
)
summary_df.to_csv(csv_path, index=False)
```

The next time someone wants the same comparison, they can list the
analysis workflow's executions, find the most recent `roc_metrics.csv`
asset, and read it directly without recomputing.

## Discovering the summary CSV (when one exists)

If a prior analysis execution already produced a `roc_metrics.csv`,
discovery is the same shape as step 2 but against the analysis
workflow's most recent execution:

```
deriva_ml_list_executions(
    hostname="data.example.org",
    catalog_id="1",
    workflow_rid="1-WF-ROC-ANALYSIS",
    status="Uploaded",
    sort=True,
    limit=1,
)
```

Then `deriva_ml_list_assets(execution_rid=...)`, filter for
`Filename == "roc_metrics.csv"`, hand the asset RID to the user for
a `download_asset` + `pd.read_csv`. The result is already aggregated
per experiment -- no per-record merge needed.

## Pitfalls

- **Per-RID download dirs are required.** Every execution's
  prediction file is named identically (e.g.,
  `prediction_probabilities.csv`). Downloading them all into the
  same directory will overwrite. Always pass
  `dest_dir=working_dir / "per_asset_downloads" / asset_rid`.
- **`download_asset` is an Execution method.** There is no
  non-execution `ml.download_asset`. Inside an analysis notebook
  created with `run_notebook(...)`, call `execution.download_asset`
  -- it uses the credential-aware Hatrac path the rest of the
  execution uses, and records the download as an input. For an
  ad-hoc pull, open a throwaway execution and call
  `execution.download_asset` on it.
- **Ground-truth filter is two predicates, not one.** Filtering by
  `Execution == gt_execution` alone can pick up rows the GT
  execution wrote later with confidence scores. Filtering by
  `Confidence IS NULL` alone can pick up labels from a different
  pass. Use both.
- **Filename matching is convention, not contract.** If the user
  renamed their prediction CSV (e.g., `test_predictions.csv`),
  the `Filename` filter in step 2 misses. Ask the user what filename
  they used, or list all `Execution_Asset` rows for one execution
  and pick the tabular one by inspection.
- **Pattern C does not give you catalog-side queryability.** If the
  user keeps asking variants of "which run had the best X," consider
  recommending a Pattern A augmentation: keep the prediction CSV
  for forensics, AND write a summary feature with the scalar metric
  so future comparisons are one `list_feature_values` call.

## Migration to Pattern A

If a project has lived long enough that catalog-side queries on the
metrics are now valuable, the prediction CSV does not have to go
away. Augment it:

1. Define a `Run_Metrics` feature on a suitable target table with
   scalar columns (`accuracy`, `auc_micro`, etc.).
2. In the analysis execution that already computes the metrics,
   write one feature row per analyzed experiment in addition to the
   `roc_metrics.csv` asset.
3. Future "which run had the best X?" questions go through Pattern A
   (`deriva_ml_list_feature_values`) and skip the download +
   merge entirely; the raw prediction CSVs remain available for any
   analysis that needs per-record data.
