---
name: manage-deriva-storage
description: "Use whenever the user asks about DerivaML LOCAL storage — listing or finding which datasets/bags AND cached assets (model weights, files) are on disk, checking local disk usage, cleaning up or deleting cached bags / cached assets / execution working directories, pre-fetching (warming) datasets or assets into the local cache, or understanding the cache-dir vs working-dir distinction (including a relocated cache_dir that is not under ~/.deriva-ml). Fire even on read-only phrasings the user won't word as 'manage storage' — 'what datasets are cached', 'list my cached bags', 'are my model weights cached', 'what's in my cache', 'how much disk is DerivaML using', 'free up space', 'is dataset X cached', 'delete the cached weights', 'where is my cache'. Triggers on: 'disk full', 'clean up cache', 'what's cached', 'cached datasets', 'cached assets', 'cached model weights', 'storage', 'free space', 'delete old data', 'cache management', 'prefetch dataset', 'warm cache', 'working directory', 'cache directory', 'cache_dir', '~/.deriva-ml'. Do NOT trigger for: catalog-side object storage / hatrac or catalog asset RECORDS (that's work-with-assets), downloading a bag for the first time (that's dataset-lifecycle), or a git/OS 'working directory' unrelated to DerivaML's local cache."
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
| `cache/bags/{checksum}/Dataset_{RID}/` | Downloaded dataset bags (BDBags), content-addressed by checksum | Python API `dataset.download_dataset_bag(version)`, `exe.download_dataset_bag(spec)`, or the bundled `${skill_base_dir}/scripts/warm_cache.py` template |
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
only when you've confirmed the default). The bundled `inspect_storage.py`
script (below) takes `--cache-dir` for exactly this.

### List everything by species (Python API, deriva-ml ≥ 1.46)

The lead path is the typed introspection API — one call per storage
species, no directory spelunking. The fastest way to run it is the bundled
read-only script, **`inspect_storage.py`, which ships inside this skill's
own directory**. Run it in place — do NOT search the user's project for it,
and do NOT copy it in; it is read-only (it never writes or deletes), so
there is nothing to customize or commit. Use the script's path from this
skill's `Base directory` (shown in the skill header when the skill loads):

```bash
# ${skill_base_dir} is this skill's directory — the path in the skill's
# "Base directory:" header, e.g. .../deriva-ml-skills/skills/manage-deriva-storage
uv run python ${skill_base_dir}/scripts/inspect_storage.py \
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

> **Unreadable cache directories.** A cache populated under a different user,
> on a restrictive shared mount, or left half-written by an interrupted run can
> contain a directory the current user can't read. The deriva-ml layer skips
> most such entries, but a permission-denied directory *inside* a bag can still
> raise `PermissionError` / `OSError` during the size walk. **Don't let that
> abort the whole report.** The bundled `inspect_storage.py` already catches
> per-species read errors and continues with a warning; if you call the API
> directly, wrap each `list_*` / `get_storage_summary` call in
> `try/except (PermissionError, OSError)` and report the unreadable path rather
> than crashing. The fix for the user is to correct the directory's permissions
> or remove it (deleting the whole `cache/` directory is safe — index and bags
> leave together), then re-run.

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

> **Run the `warm_cache.py` script — do NOT hand-write inline cache-warming Python.** This is the one bypass to actively resist: the script gives you `--dry-run`, `--metadata-only`, `--cache-dir`, and a stable CLI, and (when committed) makes the warm step reproducible — a one-off `ml.cache_dataset(...)` snippet gives none of that and leaves no trace. (This is about *script vs. inline*, a separate question from *where you run the script* — see the two run modes just below. Read-only *inspection* — `inspect_storage.py` / a quick `ml.list_cached_bags()` — is exempt: run in place, inline is fine. This rule is about *warming*.)
>
> | Rationalization (STOP — you're about to bypass) | Reality |
> |---|---|
> | "I already know how to call `ml.cache_dataset()`" | Knowing the API is exactly the trap. The script wraps it with `--dry-run`, `--metadata-only`, `--cache-dir`, and a stable CLI you don't have to reconstruct. |
> | "Inline Python is faster / fewer steps" | Running the bundled script in place (Mode 1 below) is just as fast and needs no copying — you get the CLI for free with no extra steps. |
> | "Writing it inline avoids copying a file" | You don't have to copy it — run it in place from `${skill_base_dir}` (Mode 1). Copying is only for when you want it committed (Mode 2). |
>
> If you catch yourself reaching for inline `cache_dataset` / `download_dataset_bag` to warm the cache: stop and run `warm_cache.py` instead (in place is fine).

`warm_cache.py` has **two run modes** — and "use the script" (the rule above) does NOT mean "you must copy it first." These are independent decisions:

**Mode 1 — run it in place, now (the default for a one-off warm).** When the user just wants the cache warmed for the work at hand, **you run the bundled script directly from this skill's directory — don't hand the command off to the user, and don't copy anything.** Same as `inspect_storage.py`:

```bash
uv run python ${skill_base_dir}/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0
```

The single `--dataset-rid` above is just the one-dataset case. **For two or more datasets, don't repeat this command — pass all the pairs to one call** (see "Warming several datasets" below).

**Mode 2 — copy into the project, for reproducibility.** When the warm step is part of the experiment's repeatable setup (it'll run again — before each training run, in CI, across a sweep), copy it from `${skill_base_dir}/scripts/warm_cache.py` into `src/scripts/` and commit it, then run the copied version:

```bash
uv run python src/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0
```

Both modes run the *same* script — the only difference is whether it gets committed. Mode 1 is the right default when the user asks you to warm the cache; reach for Mode 2 when the warm belongs in the project's permanent setup. Either way: it's the script, not a hand-written `cache_dataset()` snippet (see the rule above).

**Warming several datasets — pass them all to one invocation (the preferred way).** When more than one dataset needs warming, give a single `warm_cache.py` call repeated `--dataset-rid` / `--version` pairs (same order) — **not** one run per dataset, and **not** several runs in parallel. One call is preferable on every axis:

- It warms each dataset with the library's built-in ~8-way asset concurrency, one after another — which already saturates a typical uplink. Parallel processes (or `&`-backgrounded runs) just split the same bandwidth and contend, so they're no faster and usually slower.
- A bad RID (deleted catalog, dev-label version) is reported and **skipped**, and the remaining datasets still warm — you get one consolidated pass/fail summary instead of N separate exit codes to babysit.
- It's one command to read, log, and (in Mode 2) commit.

So the rule: **more than one dataset → one `warm_cache.py` call with all the pairs.** Reach for separate invocations only when the datasets genuinely belong to different catalogs (different `--hostname`/`--catalog-id`).

```bash
uv run python ${skill_base_dir}/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 1.0.0 \
    --dataset-rid 3WSE --version 2.1.0 \
    --dataset-rid 9QPM --version 0.4.0
```

**Progress.** For a multi-GB warm, the script reports per-dataset progress by default — `Materializing: 120/4210 files (3%)` lines — so it isn't a silent wait. The progress is **throttled**: by default one line at most every 15 s (tune with `--progress-interval SECONDS`; `0` = every update), with the first and final (100%) lines always shown, so a long warm reports on a steady cadence instead of spamming a line per file. It is **file-count** progress, not bytes/percent (the library exposes file counts only; true byte progress would need a deriva-ml change — tracked at [deriva-ml#314](https://github.com/informatics-isi-edu/deriva-ml/issues/314)), so the percentage is *files done*, which can be lumpy when a few large files dominate. Pass `--quiet` to suppress progress entirely.

Note for the agent: the script does not draw a live, redrawing progress bar — it emits discrete throttled lines, which is the right shape when Claude runs it through the Bash tool (captured output, not a live terminal). Relay the latest line's milestone to the user rather than expecting an animated bar.

**What the output looks like** (so you can relay status to the user, not dump raw text):

```
[1/3] 28CT v1.0.0
    Image                                       4210 rows,     1834.2 MB assets
    Subject                                      512 rows,        0.0 MB assets
  Materializing: 120/4210 files (3%)
  Materializing: 2380/4210 files (57%)
  Materializing: 4210/4210 files (100%)
  cached. {'status': 'cached_materialized', ...}
[2/3] 3WSE v2.1.0
  ! preview failed, skipping: 404 ... catalog 27
[3/3] 9QPM v0.4.0
    ...
  cached. {...}

1 of 3 dataset(s) failed:
  - 3WSE v2.1.0: 404 ... catalog 27
```

Read it as: `[i/N] <rid> <version>` headers track which dataset; a `! ... skipping` / `! cache failed` line means *that* dataset failed but the rest continued; the final `X of N dataset(s) failed:` block (and exit code 1) is the consolidated result. Report the substance to the user (e.g. *"2 of 3 cached; 9QPM failed — its catalog is gone"*), not the raw stream.

**Keeping a record of a long warm.** There's no `--log-file` flag — you don't need one. For a long multi-GB / many-dataset warm where the user steps away, capture the stream with the shell:

```bash
uv run python ${skill_base_dir}/scripts/warm_cache.py ... 2>&1 | tee warm-cache.log
```

`tee` shows progress live *and* writes `warm-cache.log` for later review. Only do this for genuinely long warms; a quick one-off doesn't need a log file cluttering the directory.

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

The template wraps this underlying call — `ml.cache_dataset(spec, materialize=True)`:

```python
from deriva_ml.dataset.aux_classes import DatasetSpec
spec = DatasetSpec(rid="28CT", version="0.9.0")
ml.cache_dataset(spec, materialize=True)
```

Shown so you recognize what the script runs — **not as an invitation to skip it.** Per the red-flags table above, warming goes through `warm_cache.py` (run it in place for a one-off, or copy + commit it for repeatable setup). The only time the bare call is appropriate is a genuinely throwaway exploration in a notebook you will not commit — and even then, running the script in place is just as easy.

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
3. **Pre-fetch** — run `warm_cache.py --dataset-rid <rid> --version <version>` to download anything that's `not_cached` (in place from `${skill_base_dir}/scripts/` for a one-off, or your committed `src/scripts/` copy if this experiment's setup is repeatable)
4. **Verify** — `deriva_ml_bag_info(...)` — confirm `cached_materialized`
5. **Run** — copy `skills/execution-lifecycle/scripts/basic_execution.py`, commit it, and run with `deriva-ml-run`. Downloads inside the execution hit cache instantly.

## Storage Manager Web App

For a visual dashboard of storage usage, use the Storage Manager app:

```
start_app(hostname="data.example.org", catalog_id="1", app_id="storage-manager")
```

This launches a web UI that shows all cached data with filters, sizes, and bulk delete. Requires the `deriva-ml-apps` repo to be built.

## Reference Resources

- `${skill_base_dir}/scripts/inspect_storage.py` — Read-only script bundled **inside this skill's directory**; run it in place (don't copy it into the project). Lists cached bags / assets / execution dirs + summary; takes `--hostname --catalog-id [--cache-dir] [--species]`. Resolves a relocated cache via `--cache-dir`.
- `ml.list_cached_bags()` / `ml.list_cached_assets()` / `ml.get_storage_summary()` — Typed inspection of every storage species (Python API, deriva-ml ≥ 1.46)
- `ml.delete_cached_bag(rid, version=None)` / `ml.delete_cached_asset(rid, md5=None)` — Targeted, index-coherent deletion
- `ml.clear_cache(older_than_days=None)` / `ml.clean_execution_dirs(...)` / `ml.gc_executions(...)` — Bulk cleanup
- Bash `ls -la ~/.deriva-ml/` — Quick visual scan (don't `rm -rf` inside `cache/` — use the deletion APIs)
- `deriva_ml_bag_info` — Check cache status, size, and manifest for a specific dataset version
- `${skill_base_dir}/scripts/warm_cache.py` — Pre-fetches one or more dataset bags into the local cache (no execution required). Accepts repeated `--dataset-rid`/`--version` pairs (warmed sequentially, per-RID error isolation); shows throttled file-count progress with a percentage by default (`--progress-interval SECONDS` to tune the cadence, `--quiet` to silence). **Two run modes:** run it in place from this skill's directory for a one-off warm (Mode 1 — the default; you run it, don't hand it off), or copy it into `src/scripts/` and commit it when the warm belongs in the project's repeatable setup (Mode 2). Either way it's the script, not inline `cache_dataset()`.

## Related Skills

- **`execution-lifecycle`** — Pre-flight checklist includes cache warming
- **`dataset-lifecycle`** — Downloading and working with BDBags
- **`configure-experiment`** — Setting `cache_dir` in hydra-zen configs
- **`work-with-assets`** — Asset caching with `AssetSpec(cache=True)`
