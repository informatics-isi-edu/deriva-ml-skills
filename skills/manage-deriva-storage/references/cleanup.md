# Cleanup Recipes

Deep cleanup recipes for Phase 2 (Clean Up — free disk space) and
Phase 2b (find and resume incomplete executions). See `SKILL.md` for the
safety framing — **preview before delete, confirm discipline, what's safe
vs. not safe to delete** — which stays inline there, not here.

> **Note:** Every storage-management operation in this skill is a **Python API method** on the `DerivaML` class (deriva-ml ≥ 1.46), run **on the local machine** — from scripts, notebooks, or `uv run python`. There are deliberately **no MCP tools or resources** for local storage: the MCP server does not share this machine's filesystem, so an MCP surface would manage the wrong host's disk. See `deriva-ml-mcp-plugin/docs/adr/0001-local-storage-management-out-of-mcp-scope.md` for the decision record.

## Delete cached data (targeted)

```python
ml.delete_cached_bag("28CT")                   # every cached version of a dataset
ml.delete_cached_bag("28CT", version="1.2.0")  # one version only
ml.delete_cached_asset("3WSE")                 # every cached copy of an asset
ml.delete_cached_asset("3WSE", md5="<md5>")    # one specific copy
```

All return `{"…_removed": n, "bytes_freed": n}` and are idempotent —
deleting something that isn't cached returns zeros rather than
raising. Deletion is purely local and never touches the catalog.

## Delete cached data (bulk, by age)

```python
ml.clear_cache()                    # everything in the cache
ml.clear_cache(older_than_days=30)  # only old entries
```

Bags age by their recorded build time; assets by directory mtime.

> **Don't `rm -rf` inside `cache/` by hand.** Bags are tracked in
> `cache/index.sqlite`; raw deletion under `cache/bags/` leaves stale
> index entries that misreport cache status until the next
> `clear_cache()` repairs them. The deletion APIs above remove the
> index entry and the on-disk directory together. (Deleting the
> *entire* `~/.deriva-ml/{host}/{catalog}/cache/` directory is safe —
> index and bags leave together.)

## Clean execution working directories

```python
ml.clean_execution_dirs(older_than_days=30, exclude_rids=["<active-rid>"])
```

## Bulk garbage-collect old executions

For executions that already uploaded successfully (status `Uploaded`), the right cleanup call is `gc_executions` — it scopes by status and age, and optionally removes the working directory in the same pass:

```python
from datetime import timedelta
from deriva_ml.execution.state_store import ExecutionStatus

ml = DerivaML(hostname=..., catalog_id=...)

# Drop the SQLite registry rows + working dirs for every Uploaded
# execution older than 30 days. The catalog rows are untouched —
# only the local workspace is cleaned.
n = ml.gc_executions(
    status=ExecutionStatus.Uploaded,
    older_than=timedelta(days=30),
    delete_working_dir=True,
)
print(f"cleaned {n} old executions")
```

By default `gc_executions` only removes the registry (SQLite) rows. Pass `delete_working_dir=True` to also `rm -rf` the on-disk execution root. **Always pair with `status=ExecutionStatus.Uploaded`** unless you have a specific reason to also remove `Stopped` / `Pending_Upload` directories (their staged outputs would be unrecoverable). The call never touches the catalog — executions that uploaded stay in the catalog regardless of local gc.

## Phase 2b: Find and Resume Incomplete Executions

Execution working directories may contain outputs that were never uploaded — from interrupted runs, crashes, or forgotten `exe.commit_output_assets()` (Python API) calls. These are the **only** local data that can't be re-downloaded from the catalog.

### Find incomplete executions

The Python-API workspace finder is the lead path — it walks the execution directories AND consults the catalog to identify what's salvageable in one call:

```python
ml = DerivaML(hostname=..., catalog_id=...)
incomplete = ml.find_incomplete_executions()
for snap in incomplete:
    print(snap.execution_rid, snap.status, snap.working_dir)
```

Each returned `ExecutionSnapshot` carries the RID, status (`Stopped`, `Pending_Upload`, orphaned `Running`), and local working directory path. No more guessing whether a directory's contents have been uploaded yet.

The bash equivalent (`ls -la ~/.deriva-ml/<host>/<catalog>/execution_*`) is still useful as a quick visual scan, but it doesn't tell you which directories represent staged-but-uncommitted work versus already-uploaded work.

### Check execution status in the catalog

For a specific execution from the list (or one whose RID came from elsewhere):

```
deriva_ml_get_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")
```

A status of `Stopped` or `Pending_Upload` means there's local staged work that has not made it to the catalog.

### Resume and upload

**For one execution:** inspect via `deriva_ml_get_execution(hostname=..., catalog_id=..., execution_rid="<rid>")` or use `ml.resume_execution(rid)` in Python to re-hydrate the staged work, then call `commit_output_assets()` on the resumed execution. For broader salvage flows (Stopped, Failed, crash recovery), see `skills/execution-lifecycle/scripts/salvage_execution.py` and `crash_recovery.py`.

**For every salvageable execution at once** (after a long break, after a batch run, or as periodic cleanup):

```python
report = ml.commit_pending_executions(execution_rids=None, clean_folder=False)
# Omit execution_rids to commit all; pass a list to scope to a subset.
# clean_folder=True wipes each working dir after a successful commit.
# Returns an UploadReport (total_uploaded, total_failed, per_table, errors).
```

`commit_pending_executions` is idempotent under the same `match_by_columns` dedup as `commit_output_assets()`, so re-running it after a partial failure picks up the failed rows and leaves already-uploaded ones alone. This is the right call when several runs accumulated staged work over a session.

For brand-new work (not resuming), copy `basic_execution.py` and run it; the relationship to the prior run lives in `tacit-knowledge.md`, not in the catalog automatically.

### After successful upload, clean up

Once outputs are safely in the catalog, the local execution
directory and registry row can be removed with `gc_executions`
(scoped to uploaded executions so staged-but-uncommitted work is
never touched):

```python
# Python API — not an MCP tool
from deriva_ml.execution.state_store import ExecutionStatus

ml.gc_executions(status=ExecutionStatus.Uploaded, delete_working_dir=True)
```
