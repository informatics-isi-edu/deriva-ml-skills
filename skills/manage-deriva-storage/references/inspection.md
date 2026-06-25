# Storage Inspection Recipes

Deep inspection recipes for Phase 1 (Assess — what's using space). See
`SKILL.md` for the cache-location orientation and the most common one-liner.

## List everything by species (Python API, deriva-ml ≥ 1.46)

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

## Browse all storage (bash fallback)

```
# Bash: ls -la ~/.deriva-ml/
# Bash: du -sh ~/.deriva-ml/*/cache/      # Only the cache
# Bash: du -sh ~/.deriva-ml/*/execution_*  # Only execution working directories
```

Fine for a quick visual scan, but bash can't tell you which bag
belongs to which dataset/version or whether it's fully materialized —
use `list_cached_bags()` for that.
