---
type: StateMachine
title: Execution status machine
description: The execution status lifecycle (Created → Running → Stopped → Pending_Upload → Uploaded, plus terminal Failed/Aborted) and how transitions are driven.
---

# Execution status machine

## Execution Statuses

| Status | Meaning |
|--------|---------|
| `Created` | Record created in catalog, no work started |
| `Running` | Work in progress inside the context manager |
| `Stopped` | Algorithm finished successfully; outputs staged but not yet committed |
| `Failed` | Encountered an error (set by `__exit__` on exception, or by `update_status`) |
| `Pending_Upload` | `commit_output_assets()` has started uploading staged outputs |
| `Uploaded` | All staged outputs successfully committed to the catalog |
| `Aborted` | Manually stopped; staged work preserved for inspection/recovery |

Values are defined as the `ExecutionStatus` `StrEnum` in `deriva_ml.execution.state_store`.

### Status State Machine

```
Created → Running → Stopped → Pending_Upload → Uploaded
              ↓        ↓                       ↗ ↓
              ↓     Failed → Pending_Upload    ↑ Failed
              ↓                                ↑
              └──→ Pending_Upload (crash recovery)
Created → Aborted
Running → Aborted
```

| Transition | When It Occurs |
|-----------|----------------|
| `Created` → `Running` | Context manager `__enter__`; records `start_time` |
| `Running` → `Stopped` | Context manager `__exit__` on clean exit; records `stop_time` |
| `Running` → `Failed` | Context manager `__exit__` on exception; records the error message and propagates the exception |
| `Stopped` → `Pending_Upload` → `Uploaded` | `exe.commit_output_assets()` succeeds — uploads staged bytes, writes asset rows |
| `Stopped` → `Pending_Upload` → `Failed` | `commit_output_assets()` fails mid-upload; idempotent, re-call to resume |
| `Running` → `Pending_Upload` | **Crash recovery** path: a process died mid-execution without `__exit__` running. Re-hydrate via `ml.resume_execution(rid)` then call `exe.update_status(ExecutionStatus.Pending_Upload)` followed by `commit_output_assets()`. See `crash_recovery.py` bundled template. |
| `Created` → `Aborted` or `Running` → `Aborted` | `exe.abort()`. Staged rows are preserved (not discarded), so the user can inspect them and decide whether to salvage via `resume_execution` or clean up via `gc_executions`. |

`commit_output_assets()` is the single per-execution commit primitive (ADR-0009). It must be called **after** the `with` block exits — the context manager only sets status to `Stopped`/`Failed`, never commits. The call is idempotent: re-running after a partial failure picks up the failed rows and leaves already-uploaded ones alone.

For mid-run progress reporting (e.g. "epoch 12 of 20"), write JSON-lines to a metrics file via `exe.metrics_file().open("a")`. The catalog does not store free-form progress messages on the Execution row.

**The lifecycle in code:** Executions are authored in user-local Python via the `with ml.create_execution(config, workflow=workflow, dry_run=...) as exe:` context manager. The skills in this plugin ship runnable templates under `skills/<name>/scripts/` — copy the template, edit parameters, commit, then run with `deriva-ml-run`. The committed script's git URL + checksum become the workflow's reproducibility anchor. MCP tools (`deriva_ml_get_execution`, `deriva_ml_list_executions`, `deriva_ml_get_lineage`, etc.) are the read-side observation surface.

## Re-Running an Aborted Execution

> **Known gap:** there is no dedicated tool to restore an aborted execution. The pattern is to inspect the prior execution and create a fresh one with the same configuration.

When you need to re-run work after a failure or abort:

1. **Inspect the prior execution.** Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to retrieve the workflow RID, dataset RIDs, asset RIDs, and description from the original.
2. **Decide whether to retry.** If the failure was transient (network, timeout) re-running with the same config is the right move. If the failure was a code or config bug, fix it first.
3. **Re-run the committed script.** Use the same template (and the same dataset / asset / workflow parameters) that produced the original execution. The new run creates a fresh execution record with a new RID; the prior execution remains in its terminal state for provenance. If the failure happened *after* the work block but before commit (status `Stopped`/`Failed` with staged work), use `skills/execution-lifecycle/scripts/salvage_execution.py` instead — same execution RID, resume the commit phase.

### Finding execution RIDs to inspect

- **From the catalog**: Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` if you know the RID, or `get_entities(hostname, catalog_id, schema="deriva-ml", table="Execution", filters=...)` to search by workflow, status, or description (or `query_attribute` with a `path` expression for column projection / FK joins).
- **From local storage**: Read `deriva://storage/execution-dirs` to see execution working directories that still exist locally. Each entry includes the execution RID, a label, size, and modification time.
- **From provenance**: Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` to find which execution produced an asset, or `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)` and inspect its `executions` field to find executions that used it.
- **From the web UI**: Browse executions in Chaise and copy the RID from the record page.
