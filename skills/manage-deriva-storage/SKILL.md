---
name: manage-deriva-storage
description: "Use whenever the user asks about DerivaML LOCAL storage — listing or finding which datasets/bags AND cached assets (model weights, files) are on disk, checking local disk usage, cleaning up or deleting cached bags / cached assets / execution working directories, pre-fetching (warming) datasets or assets into the local cache, or understanding the cache-dir vs working-dir distinction (including a relocated cache_dir that is not under ~/.deriva-ml). Fire even on read-only phrasings the user won't word as 'manage storage' — 'what datasets are cached', 'list my cached bags', 'are my model weights cached', 'what's in my cache', 'how much disk is DerivaML using', 'free up space', 'is dataset X cached', 'delete the cached weights', 'where is my cache'. Triggers on: 'disk full', 'clean up cache', 'what's cached', 'cached datasets', 'cached assets', 'cached model weights', 'storage', 'free space', 'delete old data', 'cache management', 'prefetch dataset', 'warm cache', 'working directory', 'cache directory', 'cache_dir', '~/.deriva-ml'. Do NOT trigger for: catalog-side object storage / hatrac or catalog asset RECORDS (that's work-with-assets), downloading a bag for the first time (that's dataset-lifecycle), or a git/OS 'working directory' unrelated to DerivaML's local cache."
disable-model-invocation: false
---

# Managing DerivaML Local Storage

DerivaML stores downloaded datasets, execution working directories, and cached assets on the local filesystem. This skill covers browsing, cleaning up, pre-fetching, and configuring that storage.

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
**read-only** `inspect_storage.py` script, run in place from this skill's
own directory (don't copy it in):

```bash
uv run python ${skill_base_dir}/scripts/inspect_storage.py \
    --hostname dev.eye-ai.org --catalog-id 5 \
    --cache-dir /fast-ssd/deriva-cache   # omit --cache-dir for the default location
```

For the full per-species API recipes (`list_cached_bags()`,
`list_cached_assets()`, `list_execution_dirs()`, `get_storage_summary()`),
the bash `ls`/`du` fallback, and the **unreadable-cache-directory**
permission-error handling, see `references/inspection.md`.

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

> **Don't `rm -rf` inside `cache/` by hand.** Bags are tracked in
> `cache/index.sqlite`; raw deletion under `cache/bags/` leaves stale
> index entries that misreport cache status until the next
> `clear_cache()` repairs them. The deletion APIs remove the
> index entry and the on-disk directory together. (Deleting the
> *entire* `~/.deriva-ml/{host}/{catalog}/cache/` directory is safe —
> index and bags leave together.)

**What's safe to delete:**
- Cached dataset bags — can always be re-downloaded from the catalog
- Cached assets — can be re-downloaded
- Completed execution directories — outputs already uploaded to catalog

**What's NOT safe to delete:**
- Execution directories where `exe.commit_output_assets()` (Python API) was never called — those outputs are **only** on local disk

For the full cleanup recipes — targeted delete (`delete_cached_bag` /
`delete_cached_asset`), bulk-by-age (`clear_cache`),
`clean_execution_dirs`, and bulk garbage-collect (`gc_executions`, always
scoped to `status=ExecutionStatus.Uploaded`) — see `references/cleanup.md`.

## Phase 2b: Find and Resume Incomplete Executions

Execution working directories may contain outputs that were never uploaded — from interrupted runs, crashes, or forgotten `exe.commit_output_assets()` (Python API) calls. These are the **only** local data that can't be re-downloaded from the catalog. **Confirm what's staged-but-uncommitted before deleting any execution directory** — `find_incomplete_executions()` (not a bare `ls`) tells you which directories hold un-uploaded work.

For the full resume-and-salvage recipes — `find_incomplete_executions()`,
`deriva_ml_get_execution` status checks, single-execution resume
(`resume_execution` + `commit_output_assets`), the all-at-once
`commit_pending_executions`, and post-upload cleanup with `gc_executions` —
see `references/cleanup.md` ("Phase 2b" section).

## Phase 3: Pre-fetch — Warm the Cache

Download datasets or assets into the local cache **without creating an execution**. Useful before long-running experiments to avoid download delays mid-run.

> **Run the `warm_cache.py` script — do NOT hand-write inline cache-warming Python.** This is the one bypass to actively resist: the script gives you `--dry-run`, `--metadata-only`, `--cache-dir`, and a stable CLI, and (when committed) makes the warm step reproducible — a one-off `ml.cache_dataset(...)` snippet gives none of that and leaves no trace. (Read-only *inspection* — `inspect_storage.py` / a quick `ml.list_cached_bags()` — is exempt; this rule is about *warming*.) If you catch yourself reaching for inline `cache_dataset` / `download_dataset_bag` to warm the cache: stop and run `warm_cache.py` instead (in place is fine).

The common one-off (run it in place, don't copy, don't hand it off):

```bash
uv run python ${skill_base_dir}/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0
```

**More than one dataset → one `warm_cache.py` call with all the
`--dataset-rid`/`--version` pairs** (warmed sequentially with per-RID error
isolation), not one run per dataset and not parallel runs.

For the full cache-warming recipes — the two run modes (run-in-place vs.
copy-and-commit for reproducibility), the multi-dataset invocation, the
throttled file-count progress flags (`--progress-interval`, `--quiet`), how
to read the output, `tee`-logging a long warm, `--metadata-only`,
single-asset download (`exe.download_asset`), and verifying with
`deriva_ml_bag_info` — see `references/cache-warming.md`.

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
