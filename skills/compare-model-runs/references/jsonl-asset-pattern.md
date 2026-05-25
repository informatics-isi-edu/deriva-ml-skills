# Pattern B: Comparing Runs via JSONL Asset Files

This is the worked example for the metrics-as-asset-file pattern, where the user wrote `with exe.metrics_file().open("a") as f:` inside the training loop, producing JSONL files attached to executions as `Metrics_File`-typed assets on the `Execution_Metadata` asset table.

## When to use

- Time-series metrics (per-epoch, per-step, per-eval-cycle)
- Rich nested records (loss + accuracy + per-class breakdowns + LR + …)
- Need the file shape for downstream tools (TensorBoard, W&B export)

## When NOT to use

- Per-image / per-record one-shot metrics → use Pattern A (features)
- You need to query metrics from the catalog itself → use Pattern A

## The MCP boundary

The MCP server cannot download asset bytes — that requires a local filesystem
on the calling user's machine. So this pattern always involves a hand-off:

1. **MCP-side (you):** find which assets to download. List the recent
   executions, get each execution's metadata to find the `Metrics_File`
   asset RIDs.
2. **Local Python (the user runs):** download bytes, parse JSONL,
   aggregate, paste results back.

Don't try to do step 2 via the MCP wire — you'll fail.

## Full worked example: "Plot training loss across the last 5 runs"

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

Capture the execution RIDs.

### Step 2: For each execution, find the Metrics_File asset RID

```
deriva_ml_get_execution(
    hostname="data.example.org",
    catalog_id="1",
    execution_rid="1-EXEC-Z",
)
```

The response includes the execution's metadata files (typically in a `metadata` or `outputs` field). Filter for `"Metrics_File" in asset_types` — membership, not equality, because DerivaML auto-adds `Output_File` to every uploaded asset's `asset_types` list (see `work-with-assets` → "Asset_Type auto-tags" for the full contract):

```python
import json

execution_to_metrics_asset = {}
for exec_rid in recent_rids:
    response = await deriva_ml_get_execution(
        hostname="data.example.org",
        catalog_id="1",
        execution_rid=exec_rid,
    )
    payload = json.loads(response)
    metadata_files = payload.get("metadata") or []
    for f in metadata_files:
        if "Metrics_File" in (f.get("asset_types") or []):
            execution_to_metrics_asset[exec_rid] = f["rid"]
            break
```

If a particular execution has no `Metrics_File` asset, the user either didn't call `exe.metrics_file()` in that run, or the upload didn't complete. Skip it or report the gap.

### Step 3: Generate the local Python script for the user to run

The user runs this in a Jupyter notebook or local shell — NOT via MCP:

```python
import json
import pandas as pd
import matplotlib.pyplot as plt
from deriva_ml import DerivaML

ml = DerivaML(hostname="data.example.org", catalog_id="1")

# From step 2 (paste in the dict the LLM produced)
execution_to_metrics_asset = {
    "1-EXEC-Z": "1-ASSET-METRICS-Z",
    "1-EXEC-Y": "1-ASSET-METRICS-Y",
    "1-EXEC-X": "1-ASSET-METRICS-X",
    "1-EXEC-W": "1-ASSET-METRICS-W",
    "1-EXEC-V": "1-ASSET-METRICS-V",
}

dfs = []
for exec_rid, asset_rid in execution_to_metrics_asset.items():
    local_path = ml.download_asset(asset_rid)
    records = []
    with open(local_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    df = pd.DataFrame(records)
    df["execution_rid"] = exec_rid
    dfs.append(df)

all_metrics = pd.concat(dfs, ignore_index=True)

# Plot training loss curves -- one line per execution
fig, ax = plt.subplots(figsize=(10, 6))
for exec_rid, df in all_metrics.groupby("execution_rid"):
    ax.plot(df["epoch"], df["train_loss"], label=exec_rid, alpha=0.7)
ax.set_xlabel("Epoch")
ax.set_ylabel("Train Loss")
ax.legend()
plt.show()

# Summary table -- final-epoch metrics per run
summary = (
    all_metrics
    .sort_values("epoch")
    .groupby("execution_rid")
    .last()
    .reset_index()
    [["execution_rid", "epoch", "train_loss", "val_loss", "val_accuracy"]]
)
print(summary)
```

### Step 4: User pastes results back

When the user runs the script, they get a plot + a summary table. They paste the summary text back into the conversation. Present the ranking to them in the conversation:

```
Run             | Epoch | Train Loss | Val Loss | Val Acc
1-EXEC-Z        | 50    | 0.041      | 0.182    | 0.94
1-EXEC-Y        | 50    | 0.038      | 0.195    | 0.93
1-EXEC-X        | 50    | 0.045      | 0.178    | 0.945  ← best val_acc
...
```

## "Just give me the final number, not the curve" shortcut

If the user only wants the final-epoch metric (not the curves), simplify the local script:

```python
results = {}
for exec_rid, asset_rid in execution_to_metrics_asset.items():
    local_path = ml.download_asset(asset_rid)
    records = []
    with open(local_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    final = records[-1] if records else {}
    results[exec_rid] = final.get("val_accuracy")  # or "f1", "loss", etc.

ranked = sorted(results.items(), key=lambda x: x[1] or 0, reverse=True)
for rid, score in ranked:
    print(f"  {rid}: val_accuracy = {score}")
```

The "final record is the final result" assumption is the user's recording
convention — confirm with them if you're not sure. Some users write a final
"summary" record; others stop after the last epoch and the final record IS
the summary.

## Pitfalls

- **Don't try to download bytes via the MCP wire.** The MCP server has no
  local filesystem; it can only return asset metadata. Always hand off to
  local Python.
- **The `Metrics_File` asset_type must be present.** If the user wrote to a
  generic file via `asset_file_path()` without the type tag, you won't find
  it via type filter. Check the execution's metadata listing for any
  `.jsonl`-named asset and ask the user if it's the metrics file.
- **JSONL parsing assumes one JSON object per line.** If the user wrote
  comma-separated JSON or a single JSON array, the `for line in f:` parser
  fails. Check the file format if parsing errors appear in the user's
  output.
- **`download_asset` requires the user's auth.** If the user is running the
  script in a fresh environment, they may need to authenticate first. Refer
  them to the `setup-notebook-environment` skill.
