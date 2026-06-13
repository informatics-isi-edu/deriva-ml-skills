---
name: manage-deriva-storage
description: "Use whenever the user asks about DerivaML LOCAL storage — listing or finding which datasets/bags are cached on disk, checking local disk usage, cleaning up or deleting cached bags and execution working directories, pre-fetching (warming) datasets into the local cache, or understanding the cache-dir vs working-dir distinction (including a relocated cache_dir that is not under ~/.deriva-ml). Fire even on read-only phrasings the user won't word as 'manage storage' — 'what datasets are cached', 'list my cached bags', 'what's in my cache', 'how much disk is DerivaML using', 'free up space', 'is dataset X cached', 'where is my cache'. Triggers on: 'disk full', 'clean up cache', 'what's cached', 'cached datasets', 'storage', 'free space', 'delete old data', 'cache management', 'prefetch dataset', 'warm cache', 'working directory', 'cache directory', 'cache_dir', '~/.deriva-ml'. Do NOT trigger for: catalog-side object storage / hatrac, downloading a bag for the first time (that's dataset-lifecycle), or a git/OS 'working directory' unrelated to DerivaML's local cache."
disable-model-invocation: false
---

# Managing DerivaML Local Storage

DerivaML stores downloaded datasets, execution working directories, and cached assets on the local filesystem. This skill covers browsing, cleaning up, pre-fetching, and configuring that storage.

> **RAG-first:** Start with `rag_search("storage cache dataset", doc_type="catalog-data")` to discover relevant datasets and executions before managing storage. This helps identify which cached items correspond to which catalog entities.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Understanding the Storage Layout

All DerivaML local data lives under a **working directory**, typically `~/.deriva-ml/{hostname}/{catalog_id}/`. Within that:

| Directory | Contents | Grows from |
|-----------|----------|------------|
| `cache/bags/{checksum}/Dataset_{RID}/` | Downloaded dataset bags (BDBags), content-addressed by checksum | Python API `dataset.download_dataset_bag(version)`, `exe.download_dataset_bag(spec)`, or the bundled `scripts/warm_cache.py` |
| `cache/index.sqlite` | The bag-cache index — maps dataset RIDs to cached bags. **Never edit or delete by hand**; the deletion APIs below keep it in sync with the disk | Maintained automatically |
| `cache/assets/{RID}_{md5}/` | Individually cached assets (model weights, etc.), keyed by RID + MD5 | `AssetSpec(cache=True)` |
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

### First: resolve where the cache actually is

**Before listing or deleting anything, establish the cache location — do
not assume `~/.deriva-ml`.** The cache directory is configurable
(`DerivaML(..., cache_dir=...)`, or `cache_dir=` in a hydra-zen
`default_deriva(...)`), and a relocated cache is common: shared clusters
where home is a small partition, a fast local SSD, or a shared multi-user
cache. If you operate on the default location while the real cache is
elsewhere, you will confidently report an empty or wrong cache — a silent,
plausible-looking error. **Only `deriva-ml` knows the real location** (it
reads `cache/index.sqlite` at the configured `cache_dir`); a hand-run
`ls ~/.deriva-ml` is a guess that breaks the moment the cache is relocated.

Resolve in this order:

1. **The user named it** (in the request, e.g. "my cache is on
   `/fast-ssd/deriva-cache`") → use that `cache_dir`.
2. **The project config sets it** — check `src/configs/` for a
   `default_deriva(...)` / `DerivaML(...)` call with `cache_dir=`. Use that.
3. **Neither, and it's ambiguous** → ask: *"Is your cache in the default
   `~/.deriva-ml`, or did you set a custom `cache_dir`?"* Don't ask when the
   default is clearly in use (no custom config, no signal otherwise) — only
   when a wrong guess would mislead.

Then pass the resolved location as `cache_dir=` on every call below (omit it
only when you've confirmed the default). The bundled
`scripts/inspect_storage.py` takes `--cache-dir` for exactly this.

### List everything by species (Python API, deriva-ml ≥ 1.46)

The lead path is the typed introspection API — one call per storage
species, no directory spelunking. The fastest way to run it is the bundled
read-only script:

```bash
uv run python src/scripts/inspect_storage.py \
    --hostname dev.eye-ai.org --catalog-id 5 \
    --cache-dir /fast-ssd/deriva-cache   # omit --cache-dir for the default location
```

Or call the API directly (pass `cache_dir=` when the cache is relocated;
omit it for the default):

```python
ml = DerivaML(hostname, catalog_id, cache_dir="/fast-ssd/deriva-cache")  # omit cache_dir for default

# Every cached bag, newest first — CachedBag records
for bag in ml.list_cached_bags():
    print(bag.dataset_rid, bag.version, bag.status.value, bag.size_bytes, bag.path)

# Every cached asset — CachedAsset records
for asset in ml.list_cached_assets():
    print(asset.rid, asset.md5, asset.size_bytes, asset.path)

# Execution working directories
for d in ml.list_execution_dirs():
    print(d["execution_rid"], d["size_mb"], d["path"])

# One summary across all three species
summary = ml.get_storage_summary()
print(summary["bag_count"], summary["bag_size_mb"])      # cached bags
print(summary["asset_count"], summary["asset_size_mb"])  # cached assets
print(summary["execution_dir_count"], summary["execution_size_mb"])
print(summary["total_size_mb"])
```

(`bag_size_mb` / `asset_size_mb` break down `cache_size_mb` by
species — they are subsets of it, not additive with it.)

### Browse all storage (bash fallback)

```
# Bash: ls -la ~/.deriva-ml/
# Bash: du -sh ~/.deriva-ml/*/cache/      # Only the cache
# Bash: du -sh ~/.deriva-ml/*/execution_*  # Only execution working directories
```

Fine for a quick visual scan, but bash can't tell you which bag
belongs to which dataset/version or whether it's fully materialized —
use `list_cached_bags()` for that.

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
- `cache_status`: one of `not_cached`, `cached_metadata_only`, `cached_materialized`, `cached_holey` (a bag whose asset bytes are partly missing; older releases called this `cached_incomplete`, which remains a compatible alias)
- `total_asset_bytes` / `total_asset_size`: how much space the bag uses
- `tables`: per-table row counts and asset sizes
- `cache_path`: where it lives on disk
- Manifest preview

Both work whether or not the bag is already cached.

### Estimate download size before caching

Either the bag-preview resource (current version) or `deriva_ml_bag_info` tool (pinned version) works for un-cached bags — when the bag isn't local, the response uses catalog metadata to estimate size.

## Phase 2: Clean Up — Free Disk Space

> **Note:** Every storage-management operation in this skill is a **Python API method** on the `DerivaML` class (deriva-ml ≥ 1.46), run **on the local machine** — from scripts, notebooks, or `uv run python`. There are deliberately **no MCP tools or resources** for local storage: the MCP server does not share this machine's filesystem, so an MCP surface would manage the wrong host's disk. See `deriva-ml-mcp-plugin/docs/adr/0001-local-storage-management-out-of-mcp-scope.md` for the decision record.

### Preview what would be deleted

List first, delete second — the listing calls from Phase 1 are the
dry run:

```python
# What would delete_cached_bag("28CT") remove?
[b for b in ml.list_cached_bags() if b.dataset_rid == "28CT"]
```

A single dataset RID may match multiple cached bags (one per version).

### Delete cached data (targeted)

```python
ml.delete_cached_bag("28CT")                   # every cached version of a dataset
ml.delete_cached_bag("28CT", version="1.2.0")  # one version only
ml.delete_cached_asset("3WSE")                 # every cached copy of an asset
ml.delete_cached_asset("3WSE", md5="<md5>")    # one specific copy
```

All return `{"…_removed": n, "bytes_freed": n}` and are idempotent —
deleting something that isn't cached returns zeros rather than
raising. Deletion is purely local and never touches the catalog.

### Delete cached data (bulk, by age)

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

**What's safe to delete:**
- Cached dataset bags — can always be re-downloaded from the catalog
- Cached assets — can be re-downloaded
- Completed execution directories — outputs already uploaded to catalog

**What's NOT safe to delete:**
- Execution directories where `exe.commit_output_assets()` (Python API) was never called — those outputs are **only** on local disk

### Clean execution working directories

```python
ml.clean_execution_dirs(older_than_days=30, exclude_rids=["<active-rid>"])
```

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

Once outputs are safely in the catalog, the local execution
directory and registry row can be removed with `gc_executions`
(scoped to uploaded executions so staged-but-uncommitted work is
never touched):

```python
# Python API — not an MCP tool
from deriva_ml.execution.state_store import ExecutionStatus

ml.gc_executions(status=ExecutionStatus.Uploaded, delete_working_dir=True)
```

## Phase 3: Pre-fetch — Warm the Cache

Download datasets or assets into the local cache **without creating an execution**. Useful before long-running experiments to avoid download delays mid-run.

### Cache a dataset bag

Use the bundled `skills/manage-deriva-storage/scripts/warm_cache.py` template. Copy it into the user's project (typically `src/scripts/`), then run:

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

- `scripts/inspect_storage.py` — Bundled read-only script: lists cached bags / assets / execution dirs + summary; takes `--hostname --catalog-id [--cache-dir] [--species]`. Resolves a relocated cache via `--cache-dir`.
- `ml.list_cached_bags()` / `ml.list_cached_assets()` / `ml.get_storage_summary()` — Typed inspection of every storage species (Python API, deriva-ml ≥ 1.46)
- `ml.delete_cached_bag(rid, version=None)` / `ml.delete_cached_asset(rid, md5=None)` — Targeted, index-coherent deletion
- `ml.clear_cache(older_than_days=None)` / `ml.clean_execution_dirs(...)` / `ml.gc_executions(...)` — Bulk cleanup
- Bash `ls -la ~/.deriva-ml/` — Quick visual scan (don't `rm -rf` inside `cache/` — use the deletion APIs)
- `deriva_ml_bag_info` — Check cache status, size, and manifest for a specific dataset version
- `scripts/warm_cache.py` — Bundled template for pre-fetching a dataset bag into the local cache (no execution required)

## Related Skills

- **`execution-lifecycle`** — Pre-flight checklist includes cache warming
- **`dataset-lifecycle`** — Downloading and working with BDBags
- **`configure-experiment`** — Setting `cache_dir` in hydra-zen configs
- **`work-with-assets`** — Asset caching with `AssetSpec(cache=True)`
