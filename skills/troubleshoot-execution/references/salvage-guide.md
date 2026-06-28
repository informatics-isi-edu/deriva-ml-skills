# Salvaging a failed or stranded execution

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
