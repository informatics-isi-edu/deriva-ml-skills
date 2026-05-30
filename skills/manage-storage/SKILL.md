---
name: manage-storage
description: "ALWAYS use this skill when managing DerivaML local storage — checking disk usage, cleaning up cached datasets or execution directories, pre-fetching datasets into cache, diagnosing what's using space, or understanding cache vs working directory. Triggers on: 'disk full', 'clean up cache', 'what's cached', 'storage', 'free space', 'delete old data', 'cache management', 'prefetch dataset', 'warm cache', 'working directory', 'cache directory', '~/.deriva-ml'."
disable-model-invocation: true
---

# Managing DerivaML Local Storage

DerivaML stores downloaded datasets, execution working directories, and cached assets on the local filesystem. This skill covers browsing, cleaning up, pre-fetching, and configuring that storage.

> **RAG-first:** Start with `rag_search("storage cache dataset", doc_type="catalog-data")` to discover relevant datasets and executions before managing storage. This helps identify which cached items correspond to which catalog entities.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Understanding the Storage Layout

All DerivaML local data lives under a **working directory**, typically `~/.deriva-ml/{hostname}/{catalog_id}/`. Within that:

| Directory | Contents | Grows from |
|-----------|----------|------------|
| `cache/` | Downloaded dataset bags (BDBags), keyed by RID + checksum | Python API `dataset.download_dataset_bag(version)`, `exe.download_dataset_bag(spec)`, or the bundled `scripts/warm_cache.py` |
| `cache/assets/` | Individually cached assets (model weights, etc.), keyed by RID + MD5 | `AssetSpec(cache=True)` |
| `execution_{RID}/` | Execution working directories — staged output files, logs | Created when the `with ml.create_execution(...) as exe:` context manager opens (see `execution-lifecycle/scripts/`) |
| Other dirs | Hydra configs, client exports, temporary files | Various |

### Cache vs Working Directory

These are **different concepts** that users often confuse:

| | Cache directory | Working directory |
|---|---|---|
| **Purpose** | Stores downloaded data for reuse | Base for all DerivaML operations |
| **Location** | `{working_dir}/cache/` | `~/.deriva-ml/{host}/{catalog}/` by default |
| **Configurable?** | Yes — `cache_dir` parameter in DerivaML config | Yes — `working_dir` parameter |
| **Shared across executions?** | Yes — multiple executions reuse the same cached bags | No — each execution gets its own directory |
| **Safe to delete?** | Yes — can be re-downloaded from catalog | Caution — may contain un-uploaded execution outputs |

**When to configure a custom cache directory:**
- Shared compute clusters where `~/.deriva-ml` is on a small home partition
- When you want the cache on fast local SSD instead of network storage
- When multiple users should share a single cache to avoid duplicate downloads

In Python:
```python
ml = DerivaML(hostname, catalog_id, cache_dir="/fast-ssd/deriva-cache")
```

In hydra-zen config:
```python
default_deriva(hostname="...", catalog_id="...", cache_dir="/fast-ssd/deriva-cache")
```

## Phase 1: Assess — What's Using Space

### Browse all storage

```
# Bash: ls -la ~/.deriva-ml/
```

Returns every cached bag, execution directory, and other artifact.

**Filter by category:**

```
# Bash: du -sh ~/.deriva-ml/*/cache/      # Only cached dataset bags
# Bash: du -sh ~/.deriva-ml/*/execution_*  # Only execution working directories
```

### Check a specific dataset's cache status

For the **current released version** of a dataset, the lead path is the bag-preview resource (one round trip, no parameters):

```
deriva://catalog/data.example.org/1/deriva-ml/dataset/28CT/bag-preview
```

For a **pinned version** or to **exclude tables** from the preview, use the `deriva_ml_bag_info` tool:

```
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="28CT", version="0.9.0")
```

Both return the same shape:
- `cache_status`: one of `not_cached`, `cached_metadata_only`, `cached_materialized`, `cached_incomplete`
- `total_asset_bytes` / `total_asset_size`: how much space the bag uses
- `tables`: per-table row counts and asset sizes
- `cache_path`: where it lives on disk
- Manifest preview

Both work whether or not the bag is already cached.

### Estimate download size before caching

Either the bag-preview resource (current version) or `deriva_ml_bag_info` tool (pinned version) works for un-cached bags — when the bag isn't local, the response uses catalog metadata to estimate size.

## Phase 2: Clean Up — Free Disk Space

> **Note:** The cleanup methods below (`ml.clean_storage()`) are **Python API methods** on the `DerivaML` class, not MCP tools. They must be called from Python scripts or notebooks. For MCP-based storage inspection, use the resources `deriva://storage/summary`, `deriva://storage/cache`, and `deriva://storage/execution-dirs`.

### Preview what would be deleted (dry run)

```
# Python API: ml.clean_storage(rids=["28CT"], confirm=false)
```

Returns a preview of matching entries without deleting anything. A single RID may match multiple entries (e.g., a dataset cached at several versions, or an execution working directory).

### Delete cached data

```
# Python API: ml.clean_storage(rids=["28CT", "3WSE"], confirm=true)
```

**What's safe to delete:**
- Cached dataset bags — can always be re-downloaded from the catalog
- Cached assets — can be re-downloaded
- Completed execution directories — outputs already uploaded to catalog

**What's NOT safe to delete:**
- Execution directories where `exe.commit_output_assets()` (Python API) was never called — those outputs are **only** on local disk

### Bulk cleanup workflow

1. Bash: `ls -la ~/.deriva-ml/` — see everything
2. Identify old or large entries
3. Bash: `du -sh ~/.deriva-ml/cache/*` — check sizes
4. Bash: `rm -rf ~/.deriva-ml/cache/...` — delete

### Bulk garbage-collect old executions

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

Once outputs are safely in the catalog, the local execution directory can be deleted:

```python
# Python API — not an MCP tool
ml.clean_storage(rids=["<execution_rid>"], confirm=True)
```

## Phase 3: Pre-fetch — Warm the Cache

Download datasets or assets into the local cache **without creating an execution**. Useful before long-running experiments to avoid download delays mid-run.

### Cache a dataset bag

Use the bundled `skills/manage-storage/scripts/warm_cache.py` template. Copy it into the user's project (typically `src/scripts/`), then run:

```bash
uv run python src/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0
```

Downloads the full bag (including materialized assets) into the cache. Subsequent calls to `exe.download_dataset_bag(spec)` with the same RID and version reuse the cached copy.

### Cache metadata only (no asset files)

Add `--metadata-only` to skip asset bytes:

```bash
uv run python src/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0 \
    --metadata-only
```

Useful for inspecting schema and row counts before committing to a full download.

For ad-hoc Python use without the template:

```python
from deriva_ml.dataset.aux_classes import DatasetSpec
spec = DatasetSpec(rid="28CT", version="0.9.0")
ml.cache_dataset(spec, materialize=True)
```

### Cache an individual asset

Individual-asset download is a Python-API operation. Pass the asset RID to `Execution.download_asset()` from inside an execution context, or call it through a bundled script template — there is no MCP tool that warms a single asset to the user's machine.

```python
exe.download_asset("3WSE")  # pre-trained model weights, etc.
```

### Verify cache after pre-fetching

```
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="28CT", version="0.9.0")
```

Confirm `cache_status` is `cached_materialized`.

## Pre-flight Pattern (Before Running Experiments)

The recommended pre-flight sequence:

1. **Validate** — call `get_entities(hostname=..., catalog_id=..., schema=..., table=..., filters={"RID": "<rid>"})` per candidate dataset/asset RID and confirm a non-empty result.
2. **Check cache** — `deriva_ml_bag_info(hostname=..., catalog_id=..., dataset_rid=..., version=...)` — see what's already cached
3. **Pre-fetch** — run `scripts/warm_cache.py --dataset-rid <rid> --version <version>` to download anything that's `not_cached`
4. **Verify** — `deriva_ml_bag_info(...)` — confirm `cached_materialized`
5. **Run** — copy `skills/execution-lifecycle/scripts/basic_execution.py`, commit it, and run with `deriva-ml-run`. Downloads inside the execution hit cache instantly.

## Storage Manager Web App

For a visual dashboard of storage usage, use the Storage Manager app:

```
start_app(hostname="data.example.org", catalog_id="1", app_id="storage-manager")
```

This launches a web UI that shows all cached data with filters, sizes, and bulk delete. Requires the `deriva-ml-apps` repo to be built.

## Reference Resources

- Bash `ls -la ~/.deriva-ml/` — Browse all local storage
- Bash `rm -rf ~/.deriva-ml/...` — Remove cached items by RID
- `deriva_ml_bag_info` — Check cache status, size, and manifest for a specific dataset version
- `scripts/warm_cache.py` — Bundled template for pre-fetching a dataset bag into the local cache (no execution required)

## Related Skills

- **`execution-lifecycle`** — Pre-flight checklist includes cache warming
- **`dataset-lifecycle`** — Downloading and working with BDBags
- **`configure-experiment`** — Setting `cache_dir` in hydra-zen configs
- **`work-with-assets`** — Asset caching with `AssetSpec(cache=True)`
