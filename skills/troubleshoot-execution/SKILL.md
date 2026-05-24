---
name: troubleshoot-execution
description: "ALWAYS use when a DerivaML execution fails, errors, gets stuck, produces unexpected results, OR when an execution failed mid-way and the user needs to recover/salvage partial results (uploads that succeeded, assets that staged, feature values that were written before the failure). Covers errors specific to the deriva-ml execution lifecycle (asset_file_path, commit_output_assets, stuck Running status, dataset version mismatch, missing features), the salvage decision (commit-retry vs commit-as-is vs abort vs new recovery execution), and the recovery-execution pattern (creating a new execution that claims the failed run's surviving outputs as inputs). Also covers checking and updating the three DerivaML components (deriva-ml Python lib, deriva-ml-mcp MCP server, deriva-ml-skills plugin) — version mismatches between them are a common cause of confusing errors. For generic catalog errors (auth, permissions, invalid RID, missing record), see the troubleshoot-deriva-errors skill in the deriva-skills plugin (which carries the equivalent versioning section for the foundation: deriva-py, deriva-mcp-core, deriva plugin). Triggers on: 'execution failed', 'execution stuck', 'salvage', 'recover', 'partial upload', 'training failed at upload time', 'what got uploaded', 'rerun or salvage', 'recovery execution', 'asset_file_path', 'commit_output_assets', 'pending upload', 'dataset version mismatch', 'feature not found', 'check ml versions', 'am I up to date deriva-ml', 'update deriva-ml', 'what version of deriva-ml', 'upgrade derivaml packages'."
user-invocable: false
disable-model-invocation: true
---

# Troubleshooting DerivaML Executions

This guide covers errors specific to the **DerivaML execution lifecycle** — the things that can only break when you're using `deriva-ml` and `deriva-ml-mcp` (Python API patterns like `ml.create_execution()`, `exe.asset_file_path()`, `exe.commit_output_assets()`; MCP execution-status tools; dataset versioning; feature value uploads).

> **Generic catalog errors** (auth, permissions, invalid RID, missing record, vocabulary term not found, connect failures) are NOT covered here. See the **`/deriva:troubleshoot-deriva-errors`** skill *(deriva-skills)* for those — those errors surface in any Deriva catalog operation and don't require the execution machinery to reproduce.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly; lifecycle tools also take an explicit `execution_rid`. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Symptom → Section

Jump straight to the right section if you already know what's wrong:

| Symptom | Section |
|---------|---------|
| `exe.asset_file_path()` or other `exe.*` call errors about "no active execution" | "No Active Execution" |
| Execution finished but asset files don't appear in the catalog | "Files Not Uploaded" |
| `deriva_ml_get_dataset(rid)` errors / returns empty for a dataset RID you expected to exist | "Dataset Not Found" |
| Bag contents or `denormalize_dataset` output doesn't match what you expected | "Version Mismatch" |
| `deriva_ml_add_feature_values` or feature-related calls error about a missing feature | "Feature Not Found" |
| `exe.commit_output_assets()` hangs or times out | "Upload Timeout" |
| Execution status shows `Running` but the process has crashed or ended | "Execution Stuck in Running" |
| Error mentions a missing `Workflow_Type`, `Dataset_Type`, or `Asset_Type` term | "ML Vocabulary Term Not Found" |
| Training ran for hours, failed partway, and you need to recover survivors | "Salvage a Failed Execution" |
| "Tool not found" / "unknown parameter" / docs and behavior disagree | "Versioning and updates" |

If your situation isn't in the table, read top to bottom — the sections are short.

---

## Problem: "No Active Execution"

**Symptom**: Tools that require an execution context (Python API `exe.asset_file_path()`, `exe.commit_output_assets()`) fail with an error about no active execution.

**Cause**: The execution was not properly started, or you are outside the execution context.

**Solution**:
- In Python, always use the context manager pattern:
  ```python
  from deriva_ml import DerivaML, ExecutionConfiguration

  with ml.create_execution(config) as exe:
      # All execution work goes here
  ```
- With MCP tools, ensure you called `deriva_ml_start_execution(hostname, catalog_id, execution_rid)` before attempting execution-scoped operations. The execution_rid must be the one returned by `deriva_ml_create_execution`.
- If the execution was started but the error persists, the execution may have been committed or aborted. Check with `deriva_ml_get_execution(hostname, catalog_id, execution_rid)`.

---

## Problem: "Files Not Uploaded"

**Symptom**: Execution completes but asset files are not visible in the catalog.

**Cause**: Python API `exe.commit_output_assets()` was not called, or files were written to the wrong path.

**Solution**:
1. Call `commit_output_assets()` **after** the `with` block exits in Python, not inside it. With MCP tools, call it after `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)`. If your execution was uploaded from the CLI (`deriva-ml-run`, `deriva-ml-upload`), the CLI now (v1.39+) drives `commit_output_assets()` itself and transitions the execution to `Uploaded` — earlier versions left CLI-uploaded executions stuck at `Stopped` (see [ADR-0009](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0009-unified-commit-output-assets.md)).
2. Ensure files are written to the **exact path** returned by `asset_file_path()`. Writing to any other directory will cause the upload to miss those files.
3. Verify the file actually exists at the path before uploading:
   ```python
   path = exe.asset_file_path("Execution_Asset", "output.csv")
   # Write file to `path`
   # Verify: os.path.exists(path) should be True
   ```
4. Check that the execution is still in `Running` status when you attempt the upload. If it was already committed or aborted, uploads will not work.

---

## Problem: "Dataset Not Found"

**Symptom**: Attempting to use a dataset RID returns an error or empty result.

**Cause**: Wrong catalog connection, dataset was deleted, or the RID is incorrect.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("your dataset description", doc_type="catalog-data")` to find datasets by description, type, or purpose. This is the best way to discover the correct RID when you are unsure.
- Verify you are passing the correct `hostname` and `catalog_id` arguments — a tool call against the wrong catalog will quietly miss the record.
- Call `deriva_ml_list_datasets(hostname, catalog_id)` to list available datasets.
- Confirm the RID resolves to a dataset by calling `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)`. If it errors / returns empty, the RID is wrong, the dataset was deleted, or it lives in a different catalog.
- If the dataset was recently created, it should be visible immediately -- there is no propagation delay.
- If the RID resolves to a non-dataset table, that's a generic record-not-found case — see the `/deriva:troubleshoot-deriva-errors` skill *(deriva-skills)*.

---

## Problem: "Version Mismatch"

**Symptom**: Dataset contents do not match expectations, or a workflow references an outdated dataset version.

**Cause**: The dataset was modified after the version was pinned, or version tracking was not used.

**Solution**:
- Check the dataset's version history with `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)`.
- Per ADR-0003 (deriva-ml 1.34+), dataset mutations flip `current_version` to a dev label (`<last_release>.post1.devN`). Call `deriva_ml_release(hostname, catalog_id, dataset_rid, bump="minor", description="...")` to promote the dev period to a released version that experiments can pin to.
- When referencing datasets in workflow configs, **always pin to a released version** (no `.devN` suffix) — dev labels are mutable and break reproducibility.
- Use `deriva_ml_get_dataset_spec(hostname, catalog_id, dataset_rid)` to see the current dataset specification and version.

---

## Problem: "Feature Not Found"

**Symptom**: Attempting to add feature values fails because the feature does not exist.

**Cause**: The feature was not created, or the name does not match exactly.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("your feature description", doc_type="catalog-schema")` to find features by name, target table, or vocabulary. This is the best way to discover exact feature names before calling tools.
- Call `deriva_ml_list_features(hostname, catalog_id)` to list existing features.
- Feature names are case-sensitive. Verify exact spelling with `deriva_ml_get_feature(hostname, catalog_id, target_table, feature_name)`.
- **Tool**: `deriva_ml_create_feature(hostname, catalog_id, ...)` to create the feature if it does not exist.
- Ensure the feature is associated with the correct table.

---

## Problem: "Upload Timeout"

**Symptom**: Python API `exe.commit_output_assets()` hangs or times out.

**Cause**: Large files, network issues, or server limits.

**Solution**:
- Check your network connectivity.
- For large files, consider breaking them into smaller batches.
- The server may have upload size limits. Check with your catalog administrator.
- Retry by re-calling `commit_output_assets()` — the bag-commit pipeline is idempotent under `match_by_columns` dedup, so already-uploaded rows are a no-op and only the failed entries are re-attempted. Transient network issues are the most common cause.
- **Tool**: `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to check if partial uploads succeeded.

---

## Problem: "Execution Stuck in Running"

**Symptom**: An execution shows status `Running` but the process has ended or crashed.

**Cause**: The execution context was not properly closed (e.g., crash without cleanup, not using context manager).

> **Note (v1.39+ behavior change):** CLI-uploaded executions (`deriva-ml-upload`, `deriva-ml-run`) now transition `Stopped → Pending_Upload → Uploaded` correctly. Earlier versions left CLI uploads stuck at `Stopped` even after the bytes were in hatrac — that bug is fixed under the unified `commit_output_assets` API (see [ADR-0009](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0009-unified-commit-output-assets.md)). If you're still seeing a stuck `Stopped` execution from a CLI upload, check that deriva-ml is at v1.39 or later.

**Solution**: pick the right transition based on whether there's salvageable work.

- **Best practice for next time**: always use the context manager (`with ml.create_execution(config) as exe:`) — it cleans up on both success and failure.
- **First, inspect** with `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to see the current state and what (if anything) staged or uploaded before the crash.
- **Then choose**:
  - **`deriva_ml_commit_execution(hostname, catalog_id, execution_rid)`** — drains staged outputs and advances `Running → Stopped → Pending_Upload → Uploaded`. **Use this when there is salvageable work.** Commit accepts Running, Stopped, and Pending_Upload states; if the run did some real work before crashing (uploaded some assets, staged some feature values), commit makes those visible. The drain is idempotent — if some rows previously failed mid-upload, re-running picks them up via `match_by_columns` dedup while leaving the already-uploaded ones alone. Even partial successes are usually worth committing.
  - **`deriva_ml_abort_execution(hostname, catalog_id, execution_rid, reason="<short explanation>")`** — transitions to `Aborted` and **destroys staged outputs**. Use this only when the staged work is bad (wrong inputs, corrupted state, code bug whose outputs you don't want in the catalog). The `reason` is recorded in the audit log.
- **If commit succeeds but you also want to keep going** (more inputs to process, more outputs to write), see "Salvage a Failed Execution" below — committing puts the execution into a terminal state, so further work goes into a new execution.

---

## Problem: "ML Vocabulary Term Not Found"

**Symptom**: An execution-related operation fails because a required vocabulary term does not exist (e.g., a missing `Workflow_Type`, `Dataset_Type`, or `Asset_Type` term).

**Cause**: The DerivaML built-in vocabulary needs to be extended with a domain-specific term.

**Solution**:
- All DerivaML built-in vocabularies live in the `deriva-ml` schema and are extended with the generic `add_term` tool:
  - `Dataset_Type` → `add_term(hostname, catalog_id, schema="deriva-ml", table="Dataset_Type", name=..., description=...)`
  - `Workflow_Type` → `add_term(hostname, catalog_id, schema="deriva-ml", table="Workflow_Type", name=..., description=...)`
  - `Asset_Type` → `add_term(hostname, catalog_id, schema="deriva-ml", table="Asset_Type", name=..., description=...)`
- For other vocabularies (custom domain vocabs), use `add_term` with the appropriate schema and table.
- For the generic "vocabulary term not found" troubleshooting flow (search-first via `rag_search`, synonym-aware lookup), see the `/deriva:troubleshoot-deriva-errors` skill *(deriva-skills)*.

---

## Salvage a Failed Execution

**Symptom**: A long-running execution failed mid-way. You need to figure out what survived (uploads that succeeded, assets that staged, feature values that wrote) and decide whether to recover the survivors or start over.

**Trigger phrases**: "training ran 4 hours and failed at upload time, what made it?", "execution failed, can I salvage anything?", "rerun or recover?", "the run crashed mid-feature-write."

The salvage flow has three steps, in order: **diagnose**, **decide**, **execute**.

### Step 1: Diagnose — what is the execution's current state?

```
deriva_ml_get_execution(hostname=..., catalog_id=..., execution_rid="<rid>")
```

Look at the `status` field. The seven legal states and what each one means for salvage:

| Status | Terminal? | What happened | What you can do |
|--------|:--:|---------------|------------------|
| `Created` | No | Execution was registered but `start_execution` was never called. No work happened. | Start it (`deriva_ml_start_execution`) and run normally, OR abort if no longer needed. Nothing to salvage. |
| `Running` | No | The execution started and the process either is still running, crashed, or never closed cleanly. | If the process is dead, see "Execution Stuck in Running" above. Either commit (salvage staged work) or abort (destroy it). |
| `Stopped` | No | The execution finished its work but `commit_execution` was not called. Outputs are staged but invisible. | Commit to make staged outputs visible. **This is the most common salvageable state.** |
| `Pending_Upload` | No | Commit drained the catalog row writes but the asset-file uploads are queued or partially failed. | Commit again to re-attempt the file uploads — the bag-commit pipeline is idempotent under `match_by_columns` dedup, so re-running picks up the failed rows and leaves the already-uploaded ones alone. |
| `Uploaded` | Yes | Terminal success. Already finalized. | If you wrote new outputs after `Uploaded` was reached, calling commit again cycles `Uploaded → Pending_Upload → Uploaded` for the new entries (additive-upload entry point). Otherwise nothing to do. |
| `Failed` | **Yes** | An exception was caught during the run; the state machine moved the execution to terminal-failure. **Anything that uploaded before the failure is already in the catalog. Anything still staged at the moment of failure stays staged but cannot be drained — `commit_execution` rejects `Failed` executions.** | Cannot recover this execution's staged work. Inspect what made it via `pending_summary()` (see below) and `deriva_ml_get_execution`, then start a new recovery execution (Branches C/D below). |
| `Aborted` | Yes | Explicit `abort_execution` call. Staged outputs were destroyed at abort time. | Cannot be salvaged. The aborted execution row stays in the catalog as a provenance record but its staged work is gone. Start a new execution. |

The salvageable states are `Created`, `Running`, `Stopped`, `Pending_Upload`, `Uploaded` — the five that `commit_execution` accepts. **`Failed` and `Aborted` are terminal failures: anything that uploaded before is preserved in the catalog, but anything still staged is unrecoverable from the failed execution itself. Recovery from those states means a new execution.**

To understand what specifically staged or failed before the crash, use the Python API on the resumed execution:

```python
from deriva_ml import DerivaML
ml = DerivaML(hostname=..., catalog_id=...)
exe = ml.resume_execution(execution_rid="<rid>")
summary = exe.pending_summary()
print(summary.render())
```

`pending_summary()` returns a per-table breakdown: how many rows are staged, how many uploaded, how many failed, plus the failure messages for the failed ones. This is the authoritative read of "what's salvageable." (There's no MCP-tool wrapper for `pending_summary` yet — it's Python-only.)

### Step 2: Decide — commit, abort, or recovery execution?

Four branches, depending on whether the staged work is salvageable and whether you need follow-on work. Each has different meanings for the catalog and your provenance trail:

**Branch A — Commit-retry (execution is in `Stopped`, `Running`, or `Pending_Upload`; failure was transient).** If the staged work is correct and the failure cause was network/timeout/transient I/O, **commit again**:

```
deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid="<rid>")
```

This drains the staged work and re-attempts any rows or assets that previously errored. The bag-commit pipeline is idempotent under `match_by_columns` dedup, so already-uploaded rows are a no-op and only the failed entries are re-attempted (no separate `retry_failed=` flag needed — that was the v1.38 surface and is gone in v1.39, see [ADR-0009](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0009-unified-commit-output-assets.md)). The execution transitions to `Uploaded`. The provenance trail is the most natural — same execution, same workflow, same input lineage; the only "evidence" of the failure is the catalog audit log and the time gap between start and commit.

Use this when:
- Execution status is `Stopped`, `Running`, or `Pending_Upload` (NOT `Failed` — that's terminal; commit will reject).
- Failure cause was something the system can recover from on retry (network blip, server overload, file lock).
- The staged outputs are what you want — you wouldn't re-run the model with different inputs.
- You're not changing code or config.

**Branch B — Commit-as-is, then continue work in a new execution.** If the staged work is partially useful (e.g., 80 of 100 inference outputs were generated and you want them in the catalog) and you're done with this execution but need more work after, **commit what's there**:

```
deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid="<rid>")
```

Then create a new execution for the remaining work — see Branch C or D for the recovery-execution pattern. Note both RIDs in `experiment-decisions.md` so the relationship is recoverable later (the catalog does not auto-link executions to their recovery successors; that lineage lives in your notes).

Use this when:
- Execution is in `Stopped` / `Pending_Upload` (a salvageable state).
- The salvageable work is real and you want it in the catalog.
- The remaining work needs different code, config, or inputs.

**Branch C — Recovery execution (failed run's outputs are bad, but its inputs are still good).** If the execution is in `Failed` or `Aborted`, OR if the staged outputs are wrong (model bug, wrong hyperparameters, corrupted training data), the failed execution itself can't be drained — but the **inputs** it consumed are still valid. The pattern: leave the bad execution as-is (or abort if it's still non-terminal), then **create a new execution that consumes the same inputs**:

```
# 1. If the bad execution is still non-terminal (Stopped, Running, Pending_Upload),
#    abort it to discard its staged outputs. Skip if it's already Failed or Aborted —
#    those terminal states have already finalized themselves.
deriva_ml_abort_execution(hostname=..., catalog_id=..., execution_rid="<bad-rid>",
                          reason="bug in <component>; recovery in execution <new-rid>")

# 2. Create a recovery execution with the same inputs
recovery = deriva_ml_create_execution(
    hostname=..., catalog_id=...,
    workflow_rid="<same-workflow-rid>",
    dataset_rids=["<dataset-rid>@<version>"],   # same datasets, pinned versions
    asset_rids=["<asset-rid-1>", "<asset-rid-2>"],  # same input assets
    description="Recovery for failed <bad-rid>: <root cause>",
)
new_rid = recovery["execution_rid"]

# 3. Run normally
deriva_ml_start_execution(hostname=..., catalog_id=..., execution_rid=new_rid)
# ... do the work ...
deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid=new_rid)
```

Capture the relationship in `experiment-decisions.md`:

```
## Recovery: <new-rid> replaces failed <bad-rid>

- **Failed**: <bad-rid> (<short root cause>)
- **Recovery**: <new-rid> with same workflow, same dataset versions, same input assets
- **Why abort vs retry**: <reason>
```

The `maintain-experiment-notes` skill auto-fires when you do this and will append the entry. The link is your responsibility — `deriva_ml_get_lineage` walks data-flow parents (what produced what) but does not know "execution X is the recovery for execution Y."

**Branch D — Recovery execution that claims the failed run's surviving outputs.** A subtler case: the failed run *did* produce some valid assets (e.g., it generated 80 prediction files before crashing on file 81), and you want to **re-use those 80 in a follow-on execution rather than re-generating them**.

The pattern depends on the failed run's state:

- If the failed run is in `Stopped` / `Pending_Upload` (non-terminal), commit it first so the surviving outputs become visible (Branch A pattern), then proceed.
- If the failed run is in `Failed` (terminal), only assets that uploaded *before* the failure are in the catalog. Anything still staged at the moment of failure is lost. Identify what made it via `pending_summary()` and `deriva_ml_get_execution`, then proceed.
- If the failed run is in `Aborted`, no outputs survived — you cannot use Branch D, fall back to Branch C.

```
# 1. (only if non-terminal) commit so the survivors become visible
deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid="<bad-rid>")

# 2. Find what survived (works regardless of terminal state)
exe_summary = deriva_ml_get_execution(hostname=..., catalog_id=..., execution_rid="<bad-rid>")
# Inspect its assets via the asset-execution association — see "Trace an artifact's provenance" below.
# Or in Python: ml.resume_execution(rid).pending_summary() shows what staged vs uploaded vs failed.

# 3. Create a recovery execution that consumes the survivors as inputs
recovery = deriva_ml_create_execution(
    hostname=..., catalog_id=...,
    workflow_rid="<follow-on-workflow>",
    asset_rids=["<surviving-asset-1>", "<surviving-asset-2>", ...],
    description="Recovery: continues from <bad-rid>'s surviving outputs",
)
```

This preserves both runs in the lineage chain — `deriva_ml_get_lineage` on the recovery execution's outputs will show the failed execution as a producing-execution ancestor for the surviving assets it re-used.

Use this when:
- Re-running the failed work would be expensive (long compute time, scarce compute, large data).
- The survivors are validatable (you can confirm asset 1-80 are correct) and only the failure portion needs a redo.

### Step 3: Execute — and document the choice

Whichever branch you pick, two follow-ups apply:

1. **Capture the decision in `experiment-decisions.md`.** Even the routine "transient failure → commit-retry" case is worth a one-line note ("Run X failed at upload due to network blip; retry succeeded"). For Branches B/C/D the relationship between the failed execution and the recovery execution lives only in your notes.
2. **Verify the result.** Call `deriva_ml_get_execution` on the failed execution to confirm its terminal state — `Uploaded` if you committed it (Branches A/B), `Aborted` if you discarded it (Branch C with the abort step), or unchanged `Failed` / `Aborted` if you left it as-is. Then call `deriva_ml_get_execution` on the recovery execution (Branches B/C/D) and confirm it's progressing normally. Use `deriva_ml_get_lineage` on a recovery output to confirm the provenance chain looks right.

**What you should NOT do:**

- Don't `update_record` the execution's `Status` column directly. The state machine is enforced by the lifecycle tools; bypassing it leaves the execution in an inconsistent state (the underlying upload-outputs side effect doesn't run).
- Don't try to "undo" an abort. Once `Aborted`, the staged outputs are gone — the failed execution is now a permanent provenance row. Recovery means a new execution.
- Don't reuse the failed execution's RID anywhere downstream as if it succeeded. If you commit-as-is (Branch B), only the rows that actually uploaded count as outputs of that execution.

---

## Reference Resources

- `references/execution-lifecycle.md` — Full execution lifecycle reference: workflow creation, execution configuration, upload tuning (timeouts, chunk sizes, retries), source code detection, nested executions, the recovery-execution pattern, and dry run debugging. Read this for the complete execution workflow and parameter details.
- `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` — Inspect execution state, status, and metadata
- `deriva://storage/execution-dirs` — Check execution working directories

## General Debugging Tips (Execution-Specific)

### Inspect Execution State

- **Tool**: `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to see full execution metadata, status, inputs, and outputs.
- **Tool**: Python API `exe.working_dir` to find the local working directory and inspect files directly.

### Review Recent Executions

- Call `deriva_ml_list_executions(hostname, catalog_id)` to see the latest execution activity, statuses, and any patterns of failure.
- **Tool**: `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)` to see descendants if the execution is the parent of a multirun or pipeline.
- **Tool**: `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)` to find ancestors if this is a nested step.

> **Orchestration vs data-flow:** the `list_execution_children` / `list_execution_parents` calls above walk the **orchestration** graph (which Execution called which — `Execution_Execution` table). For the **data-flow** graph (what produced this output? which dataset trained the model?), use `deriva_ml_get_lineage(hostname, catalog_id, rid=...)` instead — see "Trace an artifact's provenance" below.

### Trace an artifact's provenance

When the question is "where did this output come from?" or "why does this prediction look wrong?", walk the data-flow chain in one call:

```
deriva_ml_get_lineage(hostname="data.example.org", catalog_id="1", rid="<asset-or-feature-or-dataset-rid>")
```

Returns a tree of producing executions back to the root: which Execution produced this artifact, which Datasets and Assets it consumed, which Executions produced those, recursively. Replaces what would otherwise be 5-15 round-trips through typed reads.

Pass any artifact RID (Dataset, Asset, Feature value, or Execution); the tool auto-detects the type. Pass `depth=N` to cap the walk; default is unbounded. Cycle-safe.

This is the right tool when:
- A model prediction looks wrong and you want to confirm which training dataset version it came from.
- A feature value disagrees with what you expected and you want to identify which annotation execution wrote it.
- Reproducing a result requires confirming the exact (dataset RID, dataset version, workflow RID, workflow git commit) tuple that produced an asset.

#### Worked example: from a prediction asset back to the workflow's git commit

A common ML-developer question: "I want to reproduce this prediction. What dataset version was used, and what code (git commit) produced it?" The lineage tool gets you most of the way there, but the **workflow's URL and git checksum are not in the lineage payload** — `WorkflowSummary` in the response only carries `rid` and `name`. To get the URL + commit hash you need a second call. The full two-step pattern:

```
# Step 1 — walk the lineage from the asset
deriva_ml_get_lineage(hostname="data.example.org", catalog_id="1", rid="2-PRED1")
```

The response shape is `{"root": {...}, "lineage": {...}, "executions_visited": N, "walked_complete": true, ...}`. The `lineage` field is a tree of `LineageNode`s. Each node has:

- `execution.rid`, `execution.description`, `execution.status`
- `execution.workflow.rid`, `execution.workflow.name` — but NOT URL or checksum
- `consumed_datasets` — list of `{rid, description, version}`
- `consumed_assets` — list of `{rid, filename, asset_table}`
- `parents` — recursively, the producing executions of consumed datasets and assets

So the lineage tells you "asset `2-PRED1` was produced by execution `2-EXE1`, which consumed dataset `1-ABCD` at version `1.2.0` and was driven by workflow `2-WF01` named 'ResNet50 Training'." But not the git URL or commit.

```
# Step 2 — fetch the workflow record(s) named in the lineage
ReadMcpResourceTool(server="<name>", uri="deriva://catalog/data.example.org/1/ml/workflow/2-WF01")
```

The workflow resource returns the full record including `URL` (the source-code URL, typically a GitHub blob URL pinned to a commit, e.g. `https://github.com/org/repo/blob/abc123/train.py`) and `Checksum` (the git commit hash). The URL is the reproducible-code reference; the checksum is the integrity check.

**End-to-end summary table you can render for the user** (after both calls):

| Field | Source |
|-------|--------|
| Prediction asset RID | The starting RID you passed |
| Producing execution | `lineage.execution.rid` (immediate producer in the tree) |
| Training dataset | `lineage.consumed_datasets[0].rid` |
| Training dataset version | `lineage.consumed_datasets[0].version` |
| Workflow | `lineage.execution.workflow.rid` + `.name` |
| Code URL | workflow resource → `URL` field |
| Code git commit | workflow resource → `Checksum` field |

If the prediction depends on an upstream chain (the training execution itself consumed a dataset produced by a preprocessing execution, etc.), the same fields apply at each `parents` level of the tree.

**For per-row feature-value provenance** (e.g. "which execution wrote *this specific* `Image_Quality` value?"), pass the feature value's RID — every feature value has an RID and the tool walks it the same way. See `/deriva-ml:create-feature` for how feature values get their producing-execution link in the first place.

### Verify Working Directory

- **Tool**: Python API `exe.working_dir` returns the local filesystem path for the active execution.
- Inspect this directory to verify:
  - Input files were downloaded correctly.
  - Output files were written to the correct locations.
  - No unexpected files or directory structures.

### Clean Up

- **Resource**: Read `deriva://storage/execution-dirs` to list local execution working directories. Remove unneeded directories manually to free disk space.

## Versioning and updates

If an execution starts failing "out of nowhere" — especially "tool not found", "unknown parameter", or behavior that doesn't match the documentation — the cause is often a version mismatch between the three DerivaML components (the `deriva-ml` Python library, the `deriva-ml-mcp` MCP server, and the `deriva-ml` Claude Code plugin). They each have their own update path; there is no unified update command.

This mirrors the equivalent section in `/deriva:troubleshoot-deriva-errors` (deriva-skills), which covers the three foundation components (`deriva-py`, `deriva-mcp-core`, `deriva` plugin). When in doubt about which side is stale, check both — the DerivaML components depend on the deriva-skills foundation, so foundation versions should be current first.

**The short version of the fix:**

- **Check** which version is running:
  - MCP server: `server_status(hostname=...)` — returns the running framework version plus the list of loaded plugins. The `deriva-ml-mcp` plugin appears in that list with its version.
  - Python library: `uv pip show deriva-ml` (in your project venv).
  - Claude Code plugin: `cat ~/.claude/plugins/cache/deriva-plugins/deriva-ml/*/plugin.json` — the `version` field.
- **Update the plugin** by setting `"autoUpdate": true` in `~/.claude/settings.json` (for the `deriva-plugins` marketplace) and restarting Claude Code.
- **Update the MCP server** by `docker pull ghcr.io/informatics-isi-edu/deriva-ml-mcp:latest && docker restart deriva-ml-mcp` (Docker), or `uv lock --upgrade-package deriva-ml-mcp && uv sync` then restart the server (native install).
- **Update deriva-ml** in the project that uses it: `uv lock --upgrade-package deriva-ml && uv sync`.

### Why no single "update everything" command

The three DerivaML components live in different worlds (just like the three foundation components): the plugin updates through Claude Code's marketplace machinery, the MCP server updates through whatever deployment owns it (Docker, native install, etc.), and the Python library updates through standard Python tooling. The MCP server can't be restarted from inside Claude (the connection is stateful and would die mid-update), so MCP updates are inherently a user-driven step.

Keep all three reasonably current together. Bumping just one occasionally produces "this tool exists in the server but the plugin doesn't know about it" errors — the surfaces are designed to evolve together. And keep the foundation (`deriva-py`, `deriva-mcp-core`, `deriva` plugin) current too — DerivaML depends on the foundation, so a stale foundation can cause DerivaML errors that look like ML bugs.

### When errors might point at a version issue

Some error patterns are specific to version mismatch:

- **"Tool not found"** when the LLM tries to call an MCP tool whose name is documented in the plugin's skill — the server is older than the plugin.
- **"Unknown parameter"** in a successful tool call — the plugin's documented signature is newer than the server's.
- **Plugin documentation references a workflow that doesn't work** — the plugin is older than the server.
- **`deriva-ml` errors that mention a method that should exist** — the project's locked deriva-ml is older than what the catalog deployment expects.

If errors started right after an update of one component, verify the other two are also current. A server upgrade may have introduced a tool the plugin's docs don't yet cover; a plugin update may reference a server feature the running server doesn't have yet.

## Related Skills

- **`troubleshoot-deriva-errors`** *(deriva-skills)* — Generic catalog errors (auth, permissions, invalid RID, missing record, vocabulary term not found, connect failures). Always check this first if the error doesn't smell execution-specific — many "execution failures" are actually catalog-state issues.
- **`execution-lifecycle`** *(this plugin)* — The forward path: how to start, monitor, and complete executions correctly.
- **`dataset-lifecycle`** *(this plugin)* — Dataset versioning context for the "Version Mismatch" problem.
