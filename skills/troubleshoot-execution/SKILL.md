---
name: troubleshoot-execution
description: "Use when a DerivaML execution fails, errors, gets stuck, produces unexpected results, OR when an execution failed mid-way and the user needs to recover/salvage partial results (uploads that succeeded, assets that staged, feature values that were written before the failure), OR — proactively, with no failure in sight — when the user wants to check whether their DerivaML components are up to date (a one-shot installed-vs-latest check via the bundled scripts/check_versions.py). Covers errors specific to the deriva-ml execution lifecycle (asset_file_path, commit_output_assets, stuck Running status, dataset version mismatch, missing features), the salvage decision (commit-retry vs commit-as-is vs abort vs new recovery execution), and the recovery-execution pattern (creating a new execution that claims the failed run's surviving outputs as inputs). Also covers checking and updating the three DerivaML components (deriva-ml Python lib, deriva-ml-mcp plugin, deriva-ml-skills plugin) — version mismatches between them are a common cause of confusing errors, and the version check is useful on its own even when nothing has broken. For generic catalog errors (auth, permissions, invalid RID, missing record), see the troubleshoot-deriva-errors skill in the deriva-skills plugin (which carries the equivalent versioning section for the foundation: deriva-py, deriva-mcp-core, deriva plugin). Triggers on: 'execution failed', 'execution stuck', 'salvage', 'recover', 'partial upload', 'training failed at upload time', 'what got uploaded', 'rerun or salvage', 'recovery execution', 'asset_file_path', 'commit_output_assets', 'pending upload', 'dataset version mismatch', 'feature not found', 'check ml versions', 'am I up to date deriva-ml', 'update deriva-ml', 'what version of deriva-ml', 'upgrade derivaml packages'."
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
| `exe.add_features(records)` or feature-related calls error about a missing feature | "Feature Not Found" |
| `exe.commit_output_assets()` hangs or times out | "Upload Timeout" |
| Execution status shows `Running` but the process has crashed or ended | "Execution Stuck in Running" |
| Error mentions a missing `Workflow_Type`, `Dataset_Type`, or `Asset_Type` term | "ML Vocabulary Term Not Found" |
| Training ran for hours, failed partway, and you need to recover survivors | "Salvage a Failed Execution" |
| `DerivaMLSchemaPinned` raised on `refresh_schema()` | "Schema Pinned Errors" |
| `DerivaMLSchemaRefreshBlocked` raised on `refresh_schema()` | "Schema Pinned Errors" |
| `DerivaMLOfflineError` raised on `refresh_schema()` / `diff_schema()` / catalog read | "Offline Mode Errors" |
| `DerivaMLConfigurationError: offline mode requires a cached schema...` | "Offline Mode Errors" |
| "Tool not found" / "unknown parameter" / docs and behavior disagree | "Versioning and updates" |
| "where did this prediction come from" / "what code produced this asset" / "what dataset version trained this model" — provenance question, not an error | → `/deriva-ml:compare-model-runs` → "Trace an artifact's provenance" |

If your situation isn't in the table, read top to bottom — the sections are short.

---

## Problem: "No Active Execution"

**Symptom**: Tools that require an execution context (Python API `exe.asset_file_path()`, `exe.commit_output_assets()`) fail with an error about no active execution.

**Cause**: The execution was not properly started, or you are outside the execution context.

**Solution**:
- Always use the context manager pattern from a bundled template:
  ```python
  from deriva_ml import DerivaML
  from deriva_ml.execution import ExecutionConfiguration

  with ml.create_execution(config, workflow=workflow,
                           dry_run=args.dry_run) as exe:
      # All execution work goes here
  ```
- If the error persists, the execution may already be in a terminal state. Check with `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` — the status field will be `Stopped`, `Failed`, `Aborted`, or `Uploaded`.
- See `skills/execution-lifecycle/scripts/basic_execution.py` for the canonical authoring template.

---

## Problem: "Files Not Uploaded"

**Symptom**: Execution completes but asset files are not visible in the catalog.

**Cause**: Python API `exe.commit_output_assets()` was not called, or files were written to the wrong path.

**Solution**:
1. Call `exe.commit_output_assets()` **after** the `with` block exits, not inside it. The CLI (`deriva-ml-run`, `deriva-ml-upload`) drives `commit_output_assets()` itself and transitions the execution to `Uploaded`. For ad-hoc salvage of an execution that exited the `with` block but never committed, use `skills/execution-lifecycle/scripts/salvage_execution.py`.
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
- Per ADR-0003, dataset mutations flip `current_version` to a dev label (`<last_release>.post1.devN`). Call `deriva_ml_release_dataset(hostname, catalog_id, dataset_rid, bump="minor", description="...")` to promote the dev period to a released version that experiments can pin to.
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

**Solution**: use the bundled `skills/execution-lifecycle/scripts/crash_recovery.py` template — it handles the `Running → Pending_Upload` transition that the state machine accepts as the crash-recovery path.

```bash
# Recover (commit any staged work):
uv run python src/scripts/crash_recovery.py \
    --hostname data.example.org --catalog-id 1 \
    --execution-rid <rid>

# Or abandon staged work:
uv run python src/scripts/crash_recovery.py \
    --hostname data.example.org --catalog-id 1 \
    --execution-rid <rid> \
    --abort
```

**Best practice for next time**: always use the context manager (`with ml.create_execution(config, workflow=workflow) as exe:`) — it cleans up on both success and failure. The bundled `basic_execution.py` template encodes this pattern. The only way to get stuck in `Running` is a hard crash before `__exit__` runs (OOM, SIGKILL, host reboot).

If the execution is already in a non-`Running` state (`Stopped`, `Failed`, `Pending_Upload`), use `salvage_execution.py` instead — see "Salvage a Failed Execution" below.

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
- **If the vocabulary table itself doesn't exist yet**, create it with `deriva_ml_create_vocabulary(hostname=..., catalog_id=..., vocab_name=..., comment=...)`. See `deriva-ml-context` → "Creating a new vocabulary" for the rationale (the ML-aware tool applies the curie prefix, default schema, and navbar refresh that the generic `create_vocabulary` skips).
- For the generic "vocabulary term not found" troubleshooting flow (search-first via `rag_search`, synonym-aware lookup), see the `/deriva:troubleshoot-deriva-errors` skill *(deriva-skills)*.

---

## Problem: "Schema Pinned Errors"

**Symptom 1**: `DerivaMLSchemaPinned` raised when calling `ml.refresh_schema()` (with or without `force=True`).

**Cause**: The local schema cache is pinned — some earlier code called `ml.pin_schema(reason=...)` to freeze the schema view for a long-running run. `force=True` does NOT bypass a pin (intentional — pin is the heavier discipline).

**Solution**:
- Check who pinned and why: `ml.pin_status()` returns the `pin_reason` and `pinned_at` timestamp.
- If the pin is no longer needed (the run that motivated it has finished), call `ml.unpin_schema()` then re-attempt the refresh.
- If the pinned snapshot is still the right view, skip the refresh — the cache is already serving what you want.

**Symptom 2**: `DerivaMLSchemaRefreshBlocked` raised on `ml.refresh_schema()` (without `force=True`).

**Cause**: The workspace has pending rows (staged / leasing / leased / uploading / failed). Refreshing would replace the schema cache, and the pending rows might reference columns or types that no longer exist in the new schema, causing catalog-insert failures on the next upload.

**Solution**:
- **Preferred:** drain the pending work first with `ml.commit_pending_executions()`, then refresh.
- Otherwise, pass `force=True` to refresh anyway — but understand that staged rows may now have stale column references.

For background on pinning and the dirty-tree-vs-schema-pin pairing, see `execution-lifecycle/references/concepts.md` → "Schema Pinning for Long Runs".

---

## Problem: "Offline Mode Errors"

**Symptom 1**: `DerivaMLOfflineError` raised on `ml.refresh_schema()`, `ml.diff_schema()`, or any direct catalog read.

**Cause**: The DerivaML instance was constructed with `mode=ConnectionMode.offline`, which forbids network calls. The operation needs the live catalog.

**Solution**:
- For schema refresh / diff: construct a separate online instance against the same `working_dir` and call from there.
- For a one-off read: drop back to online mode for that call.
- For sustained online work: re-construct without `mode=ConnectionMode.offline` (the default is online).

**Symptom 2**: `DerivaMLConfigurationError: offline mode requires a cached schema at <path>; run online once first (with the same working_dir) to populate the cache.`

**Cause**: Offline mode was requested against a workspace that has no schema cache yet. Offline mode reads from the cache and skips all network — it cannot bootstrap from scratch.

**Solution**: run an online `DerivaML(hostname=..., catalog_id=..., working_dir=<same path>)` once to populate the cache, then re-attempt offline.

**Symptom 3**: `DerivaMLConfigurationError: cached schema at <path> is for X/Y, but __init__ was called with A/B.`

**Cause**: The workspace cache belongs to a different `(hostname, catalog_id)`. DerivaML refuses to serve a mismatched cache because table / column names that match by string may have completely different meanings across catalogs.

**Solution**: use a different `working_dir` per catalog (the simplest discipline — one workspace per catalog), or run online against the new catalog with the same `working_dir` to overwrite the cache.

For the full offline-mode contract — what operations stage to SQLite, what triggers the upload drain — see `execution-lifecycle/references/concepts.md` → "Offline Mode".

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
| `Created` | No | The execution row was registered but the work never started. | Re-run the committed script (a fresh execution; the existing `Created` row can be garbage-collected). |
| `Running` | No | The process either is still running, crashed, or never closed cleanly. | If the process is dead, see "Execution Stuck in Running" above — use `crash_recovery.py`. |
| `Stopped` | No | The work finished but `commit_output_assets()` was never called. Outputs are staged but invisible. | Run `salvage_execution.py` to commit. **This is the most common salvageable state.** |
| `Pending_Upload` | No | `commit_output_assets()` started but partially failed mid-upload. | Run `salvage_execution.py` to resume — the bag-commit pipeline is idempotent under `match_by_columns` dedup, so already-uploaded rows are a no-op and only the failed entries are re-attempted. |
| `Uploaded` | Yes | Terminal success. Already finalized. | Nothing to do. |
| `Failed` | **Yes** | An exception was caught during the run, or the commit phase exhausted its retries. Anything that uploaded before the failure is in the catalog; the rest is unrecoverable from this execution. | Inspect what made it via `pending_summary()` and `deriva_ml_get_execution`, then start a new recovery execution (Branches B/C below). |
| `Aborted` | Yes | Explicit `exe.abort()` call. Staged rows are preserved (not discarded) for inspection. | The execution row stays in the catalog as a provenance record. To re-use the staged work, resume via `ml.resume_execution(rid)` and continue; otherwise start a new execution. |

The salvageable, non-terminal states are `Stopped` and `Pending_Upload` — both accept `salvage_execution.py`. `Running` needs `crash_recovery.py` to transition out first. `Failed` and `Uploaded` are terminal — `Failed` requires a recovery execution; `Uploaded` is done.

To understand what specifically staged or failed before the crash, use the Python API on the resumed execution:

```python
from deriva_ml import DerivaML
ml = DerivaML(hostname=..., catalog_id=...)
exe = ml.resume_execution(execution_rid="<rid>")
summary = exe.pending_summary()
print(summary)
# .rows, .files, .failed_rows, .failed_files
```

`pending_summary()` returns a per-table breakdown: how many rows are staged, how many uploaded, how many failed, plus the failure messages for the failed ones. This is the authoritative read of "what's salvageable."

#### Bulk discovery: find every stale execution on this machine

When you're triaging "what runs from the last week didn't finish?" rather than one named RID, use the workspace-level finder:

```python
ml = DerivaML(hostname=..., catalog_id=...)
incomplete = ml.find_incomplete_executions()
# Returns ExecutionSnapshot rows for any execution whose local working
# directory still has staged work (Stopped / Pending_Upload / orphaned Running)
for snap in incomplete:
    print(snap.execution_rid, snap.status, snap.working_dir)
```

`find_incomplete_executions()` is **local working-dir scoped** — it only sees runs whose staged work is still on *this* machine. For a **catalog-wide** view of every execution stranded in a non-terminal state (regardless of where it ran), use the read-only provenance audit:

```python
report = ml.audit_provenance()
# report.violations includes stranded non-terminal executions and null-producer
# artifacts; report.known_degraded lists sentinel-attributed (compliant) state.
for v in report.violations:
    print(v)
```

Under the provenance contract a non-terminal execution (`Created`/`Running`/`Pending_Upload`) is a **violation**, not just a recoverable state — the audit is how you find them all. (It only reports; it never mutates. Salvage/abort the rows yourself with the recipes above.)

To **commit every salvageable run in one pass** (instead of running `salvage_execution.py` N times), call the workspace-level commit:

```python
report = ml.commit_pending_executions(execution_rids=None, clean_folder=False)
# Pass execution_rids=[...] to scope to a subset; omit (or None) to commit all
# UploadReport: total_uploaded, total_failed, per_table, errors
```

`commit_pending_executions` is the same idempotent commit-pipeline as `commit_output_assets()`, applied across every locally-staged execution. Use it after a long break to clean up accumulated staged work, or after a batch job to flush several runs in one round trip.

### Step 2: Decide — salvage, recovery, or both?

Three branches, depending on whether the staged work is salvageable and whether you need follow-on work.

**Branch A — Salvage the staged work** (execution is in `Stopped` or `Pending_Upload`; failure was transient).

If the staged outputs are correct and the failure cause was network/timeout/transient I/O, run the salvage template:

```bash
uv run python src/scripts/salvage_execution.py \
    --hostname data.example.org --catalog-id 1 \
    --execution-rid <rid>
```

This drains the staged work, re-attempts any rows or assets that previously errored, and transitions the execution to `Uploaded`. Idempotent — re-call to resume if the salvage itself fails partway.

Use this when:
- Execution status is `Stopped` or `Pending_Upload`.
- Failure cause was something the system can recover from on retry (network blip, server overload, file lock).
- The staged outputs are what you want — you wouldn't re-run the model with different inputs.
- You're not changing code or config.

**Branch B — Recovery execution from valid inputs** (the failed run's outputs are bad, but its inputs are still good).

If the execution is in `Failed`, OR if the staged outputs are wrong (model bug, wrong hyperparameters, corrupted training data), the failed execution's outputs can't be salvaged — but the **inputs** it consumed are still valid. The pattern: leave the bad execution in its terminal state, then re-run the committed script with the same inputs (and any fixes) to create a fresh recovery execution.

Before re-running, check the blast radius: if the bad run DID upload outputs and downstream executions already consumed them, those runs inherit the problem. `deriva_ml_find_executions_consuming(hostname, catalog_id, rid=<output-rid>)` on each uploaded output answers it in one call per artifact (see "Check downstream consumption" below).

```bash
# Re-run the script that produced the failed execution. New RID; same inputs.
uv run python src/scripts/<task>.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type <type> \
    --dataset-rid <same-dataset-rid> \
    # any fixes go here ...
```

Capture the relationship in `tacit-knowledge.md`:

```
## Recovery: <new-rid> replaces failed <bad-rid>

- **Failed**: <bad-rid> (<short root cause>)
- **Recovery**: <new-rid> with same workflow, same dataset versions, same input assets
- **What changed**: <code fix, config change, or "nothing — retry of transient failure">
```

The `capture-tacit-knowledge` skill auto-fires when you do this and will append the entry. The link is your responsibility — `deriva_ml_get_lineage` walks data-flow parents (what produced what) but does not know "execution X is the recovery for execution Y."

**Branch C — Recovery execution that claims the failed run's surviving outputs.** A subtler case: the failed run *did* produce some valid assets (e.g., it generated 80 prediction files before crashing on file 81), and you want to **re-use those 80 in a follow-on execution rather than re-generating them**.

The pattern depends on the failed run's state:

- If the failed run is in `Stopped` / `Pending_Upload`, salvage it first (Branch A) so the surviving outputs become visible.
- If the failed run is in `Failed` (terminal), only assets that uploaded *before* the failure are in the catalog. Anything still staged at the moment of failure is lost. Identify what made it via `pending_summary()` and `deriva_ml_get_execution`, then proceed.
- If the failed run is in `Aborted`, the staged work is preserved — `ml.resume_execution(rid)` followed by `commit_output_assets()` will commit it.

Then write a follow-on script (typically a copy of `basic_execution.py` with the surviving asset RIDs hardcoded into the `ExecutionConfiguration(assets=[...])`) and run it. The follow-on execution consumes the survivors as inputs:

```python
config = ExecutionConfiguration(
    description="Continues from <bad-rid>'s surviving outputs",
    assets=["<surviving-asset-1>", "<surviving-asset-2>", ...],
)
```

`deriva_ml_get_lineage` on the recovery execution's outputs will show the failed execution as a producing-execution ancestor for the surviving assets it re-used.

Use this when:
- Re-running the failed work would be expensive (long compute time, scarce compute, large data).
- The survivors are validatable (you can confirm asset 1-80 are correct) and only the failure portion needs a redo.

### Step 3: Execute — and document the choice

Whichever branch you pick, two follow-ups apply:

1. **Capture the decision in `tacit-knowledge.md`.** Even the routine "transient failure → salvage" case is worth a one-line note ("Run X failed at upload due to network blip; salvage succeeded"). For Branches B/C the relationship between the failed execution and the recovery execution lives only in your notes.
2. **Verify the result.** Call `deriva_ml_get_execution` on the failed execution to confirm its terminal state — `Uploaded` if you salvaged it (Branch A), unchanged `Failed`/`Aborted` if you left it as-is. Then call `deriva_ml_get_execution` on the recovery execution (Branches B/C) and confirm it's progressing normally. Use `deriva_ml_get_lineage` on a recovery output to confirm the provenance chain looks right.

**What you should NOT do:**

- Don't try to flip the `Status` column directly via `update_entities`. The state machine is enforced by the Python API; bypassing it leaves the execution in an inconsistent state (the underlying upload side effect doesn't run).
- Don't try to "undo" an abort that you no longer want. The aborted execution is a permanent provenance row. To recover, resume it (`ml.resume_execution(rid)`) and commit the staged work, or create a new execution.
- Don't reuse the failed execution's RID anywhere downstream as if it succeeded. Only the rows that actually uploaded count as outputs of that execution.

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

- Call `deriva_ml_list_executions(hostname, catalog_id, sort=True)` to see the latest execution activity (newest-first by RCT), statuses, and any patterns of failure. Without `sort=True`, results are RID-ascending — "the last 5 runs" then requires paging to the end of the result set.
- **Cross-workflow filter:** pass `workflow_type="Training"` (or any `Workflow_Type` vocab value) to scope to one class of run across every workflow that produced it — e.g., `deriva_ml_list_executions(hostname, catalog_id, workflow_type="Inference", sort=True)`. This is the one-call answer to "show me every inference execution" without enumerating workflows first. Mutually compatible with `workflow_rid=` (both narrow the result), and with `status=` to filter on `Running` / `Failed` / `Aborted` / etc.
- **Tool**: `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)` to see descendants if the execution is the parent of a multirun or pipeline.
- **Tool**: `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)` to find ancestors if this is a nested step.

> **Orchestration vs data-flow:** the `list_execution_children` / `list_execution_parents` calls above walk the **orchestration** graph (which Execution called which — `Execution_Execution` table). For the **data-flow** graph (what produced this output? which dataset trained the model?), use `deriva_ml_get_lineage(hostname, catalog_id, rid=...)` instead — see `/deriva-ml:compare-model-runs` → "Trace an artifact's provenance" for the worked end-to-end pattern (lineage walk → workflow URL + git commit).

### Check sweep health in one call

When the question is "how is my multirun doing?" — N runs of one workflow, some finished, some not — don't page `deriva_ml_list_executions` and count statuses client-side. `deriva_ml_multirun_status(hostname, catalog_id, workflow_rid)` aggregates server-side and returns `{"counts": {"Uploaded": 18, "Running": 2, "Failed": 1}, "total": 21}`. A non-zero `Failed` count routes you back to the Symptom → Section table above for the failing runs; lingering `Running` entries hours after the sweep should have finished route to "Execution Stuck in Running".

### Check downstream consumption (forward lineage)

`deriva_ml_get_lineage` walks **backward** (what produced this?). The forward question — "did any execution CONSUME this artifact as an input?" — is `deriva_ml_find_executions_consuming(hostname, catalog_id, rid)` with a Dataset or asset RID. Two triage uses:

- **Blast radius of a bad run.** If a failed/buggy execution's outputs were already consumed by downstream runs, those runs are built on bad inputs and need recovery too. Check each output asset/dataset of the bad run before declaring the incident closed.
- **"Safe to delete?"** An empty `consumers` list means no execution ever recorded consuming the artifact — reasonable green light for cleanup. Non-empty means it is upstream of real runs; prefer deprecation over deletion. (Empty means no *recorded* consumption — ad-hoc reads outside an execution context leave no edge.) The impact-analysis recipes live in `/deriva-ml:schema-evolution-impact`.

### Compare feature values across recent executions

When triaging "did my last few runs produce reasonable predictions / metrics?", batch-fetch the feature values across all the candidate executions in **one** call rather than looping per-execution:

```
deriva_ml_list_feature_values(hostname="data.example.org", catalog_id="1",
    target_table="Image",
    feature_name="Predicted_Class",
    execution_rids=["1-EXEC-A", "1-EXEC-B", "1-EXEC-C"])
```

The `execution_rids=` filter runs server-side, returning rows from any of the listed executions. One round trip instead of N. The default 50,000-row cap protects against accidental wholesale materialization; if you blow through it, narrow the filter (fewer execution RIDs, or pair with `selector="newest"`) or raise `max_results=`. See `/deriva-ml:compare-model-runs` for the full pattern.

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

- **Check installed-vs-latest for all three components in one shot** with the bundled script:
  ```bash
  uv run python skills/troubleshoot-execution/scripts/check_versions.py --project /path/to/your/ml/project
  ```
  It runs a discovery chain before trusting anything — **(1)** the project is a git repo, **(2)** it has a `pyproject.toml` (the deriva-ml uv convention), **(3)** it has a `.venv/` — failing loud with the fix to apply (e.g. "run `uv sync`") at the first unmet step. It then reads the installed `deriva-ml` by running the **venv's own** Python (`<venv>/bin/python -c "import deriva_ml…"`), NOT `uv pip show` — so it works even when `uv` isn't on PATH (whether `uv` is available is *reported*, not required). It reads the `deriva-ml-skills` plugin from the Claude Code cache, then compares each against the latest published version on GitHub, queried live from the right source: highest git **tag** for the library and the `deriva-ml-mcp` plugin (both ship tags, no GitHub Releases), highest GitHub **release** for the `deriva-ml-skills` plugin. Prints `current` / `behind` / `unknown` per component. No network or `gh` needed to *run* — without them the latest columns degrade to `unknown` (with a reason); only a definitive "behind" sets exit 1, a failed precondition sets exit 2. The MCP server's *running* version is only knowable live (via `server_status`), so the script shows the latest published plugin version and points you at that tool for the running one. This is the replacement for the deleted `check-deriva-ml-versions` skill — a thin reference script, not a skill, so it can't go stale by hardcoding "latest" (it always queries live).
- **Check** a single component manually:
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
