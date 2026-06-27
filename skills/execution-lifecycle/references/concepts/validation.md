---
type: Concept
title: Execution validation
description: Pre-flight checks before running an experiment, schema pinning for long runs on shared catalogs, and offline mode for disconnected or throttled environments.
---

# Execution validation

## Pre-Flight Validation

Before running an experiment, several checks prevent runtime failures and data issues.

### Why pre-flight matters

Experiments fail at runtime when:
- Dataset RIDs in the config don't exist or point to wrong versions
- Asset RIDs (model weights, etc.) are invalid
- Bags are too large to download during execution
- Network issues during materialization

All of these can be caught before the execution context manager opens.

### The pre-flight checklist

| Step | Tool / Template | What it checks |
|------|------|---------------|
| Validate RIDs | `deriva_ml_get_dataset` / `get_entities` | All dataset and asset RIDs exist (check by typed lookup) |
| Check cache | `deriva_ml_bag_info` | Dataset sizes, cache status (`not_cached`, `cached_metadata_only`, `cached_materialized`, `cached_incomplete`); also doubles as a version-existence check |
| Warm cache | `skills/manage-deriva-storage/scripts/warm_cache.py` | Pre-fetches bags into local cache (no execution row) |
| Git clean | `git status` | No uncommitted changes (for CLI runs) |
| Config check | `--cfg job` | Resolved Hydra config is correct (for CLI runs) |

### Cache status values

The `deriva_ml_bag_info` tool returns a `cache_status` field:

| Status | Meaning | Action |
|--------|---------|--------|
| `not_cached` | No local copy | Run `warm_cache.py` if large |
| `cached_metadata_only` | Table data present, assets not fetched | Run `warm_cache.py` (default materialize=True) |
| `cached_materialized` | Fully downloaded and validated | Ready to use — no action needed |
| `cached_incomplete` | Was cached but assets are missing | Run `warm_cache.py` to re-materialize |

### Prefetching strategy

For large datasets (>1 GB), warm the cache ahead of time rather than downloading during the execution. The bundled `skills/manage-deriva-storage/scripts/warm_cache.py` template handles this:

```bash
uv run python src/scripts/warm_cache.py \
    --hostname data.example.org --catalog-id 1 \
    --dataset-rid 28CT --version 0.9.0
```

Equivalent Python-API call (what the template runs under the hood):

```python
info = ml.bag_info(DatasetSpec(rid="28CT", version="0.9.0"))
print(f"Size: {info['total_asset_size']}, Cache: {info['cache_status']}")
if info["cache_status"] == "not_cached":
    ml.cache_dataset(DatasetSpec(rid="28CT", version="0.9.0"))
```

## Schema Pinning for Long Runs

DerivaML caches the catalog schema locally so reads don't pay a `/schema` round-trip on every call. By default, `refresh_schema()` re-fetches the cache when needed (e.g., after a known out-of-band mutation). **Pinning** the schema freezes that cache at its current snapshot so nothing — not even `refresh_schema(force=True)` — can replace it while the pin is held. This is the right discipline when a long-running experiment must see a stable schema view even if the catalog is migrating underneath.

### When to pin

- **Long training run on a shared catalog.** A schema migration landing mid-training (column rename, table split, FK retarget) can break the model's view of the data between epoch 12 and epoch 13. Pinning at the start of the run guarantees every read in the run sees the same shape.
- **Multi-step pipeline that must agree on schema.** When a sweep parent and its children all read the same target tables, pinning the parent's schema ensures children inherit a consistent view (the workspace's SQLite cache is shared across executions in the same `working_dir`).
- **Offline reproduction of a historical run.** If you cloned the catalog at a specific snaptime and want to run analysis against it, pin to freeze the analysis's view of that snapshot.

### How to pin

```python
from deriva_ml import DerivaML
ml = DerivaML(hostname=..., catalog_id=...)

# Freeze the local cache. Returns a SchemaDiff if the live catalog
# has already drifted from the cache (online mode only); None if
# the cache and live are in sync, or always None in offline mode.
drift = ml.pin_schema(reason="ResNet50 training v0.4.2 — Aug 2026 run")
if drift is not None:
    print("Live schema has moved on; pin was applied to cached snapshot.")
    print(drift)  # structural diff (added / removed tables / columns / FKs)
```

`pin_schema(reason=...)` stores the reason alongside the pin; you can read it later with `ml.pin_status()`. The reason field is the operational log entry — it's what answers "why is this pinned?" three months later.

### Working with a pin

| Method | Effect |
|---|---|
| `ml.pin_status()` | Returns `PinStatus(pinned, pinned_at, pin_reason, pinned_snapshot_id)` — current pin state |
| `ml.diff_schema()` | Returns the structural diff between cached and live schemas (online mode only) — use to see what the migration changed without breaking the pin |
| `ml.unpin_schema()` | Clears the pin. After unpinning, `refresh_schema()` is allowed again |
| `ml.refresh_schema(force=True)` while pinned | **Raises `DerivaMLSchemaPinned`** — `force=True` does NOT bypass a pin. Call `unpin_schema()` first |

### Composition with the dirty-tree rule

Pinning the schema is the **environment-side** discipline; the git-clean-tree rule (`DerivaMLDirtyWorkflowError`) is the **code-side** discipline. Both should be in place for any production run — together they guarantee the run is reproducible as (committed code) × (frozen catalog shape). Either alone leaves a reproducibility gap.

### Common errors

- `DerivaMLSchemaPinned` — `refresh_schema()` or `refresh_schema(force=True)` was called while a pin is held. Resolution: `ml.unpin_schema()` first, or skip the refresh if the pinned snapshot is still the right view.
- `DerivaMLSchemaRefreshBlocked` — `refresh_schema()` (without `force=True`) was called while the workspace has pending rows. Resolution: commit the pending work first (`ml.commit_pending_executions()`), or `force=True` if you accept the risk that staged rows may reference columns that disappeared.

## Offline Mode

`ConnectionMode.offline` lets a DerivaML instance operate against a previously-cached schema with **no network calls** except RID leases and the final upload. Every write — execution creation, status transitions, feature values, asset registrations — stages into the workspace's local SQLite and stays there until you drain it with `ml.commit_pending_executions()`.

### When to use offline mode

- **Laptop / disconnected work.** Author and run an execution on a plane; upload when you land. The execution's full state (status, staged outputs, feature values) survives in the workspace SQLite until you reconnect.
- **Throttled / unreliable network.** Batch jobs on a cluster where the per-call network hop to the catalog dominates wall time. Offline mode amortizes the cost into one bulk upload.
- **Replay against a frozen catalog snapshot.** Combined with a pinned schema, offline mode gives you a fully reproducible run with no network dependency on the live catalog.

### How to enter offline mode

```python
from deriva_ml import ConnectionMode, DerivaML

ml = DerivaML(
    hostname="data.example.org", catalog_id="1",
    mode=ConnectionMode.offline,
    # working_dir must contain a schema cache from a prior online run
    working_dir="/path/to/workspace",
)
assert ml.mode is ConnectionMode.offline
```

**Prerequisite:** the workspace's schema cache must already exist (populated by a prior online `DerivaML.__init__` or `refresh_schema()` against the same `(hostname, catalog_id)`). Offline mode refuses to bootstrap from scratch — there's no live catalog to fetch a schema from. Trying to start offline against an unpopulated workspace raises `DerivaMLConfigurationError`.

`DerivaML.from_context()` does **not** take a `mode` argument — to start offline, construct `DerivaML(...)` explicitly.

### What works offline

| Operation | Offline behavior |
|---|---|
| `ml.create_execution(config) as exe:` | Works. Execution row stages to SQLite; status transitions stage too. |
| `exe.add_features(records)` | Works. Feature values stage to SQLite. |
| `exe.asset_file_path(...)` | Works. Files stage in the local working directory as usual. |
| `exe.create_dataset(...)` | Works. Dataset row stages to SQLite. |
| Read-side calls (`ml.find_datasets()`, `ml.lookup_feature(...)`, etc.) | Work — served from the cached schema and any locally-staged rows. |
| `ml.refresh_schema()` | **Raises `DerivaMLOfflineError`** — refresh requires online mode. |
| `ml.diff_schema()` | **Raises `DerivaMLOfflineError`** — diff needs live catalog. |
| `exe.commit_output_assets()` | Drains this one execution's staged rows + asset files. Requires network at call time. |
| `ml.commit_pending_executions()` | Drains every staged execution in one pass. The canonical "back online — flush everything" call. |

### Composing offline mode with the upload drain

The full pattern for offline-then-online:

```python
# 1. Initial online cache population (one-time, with network).
ml = DerivaML(hostname=..., catalog_id=...,
              working_dir="/workspace/project-x")
# Schema cache now populated under /workspace/project-x.

# 2. Switch to offline. Run N executions over time without network.
ml_offline = DerivaML(hostname=..., catalog_id=...,
                       mode=ConnectionMode.offline,
                       working_dir="/workspace/project-x")
for config in configs_to_run:
    with ml_offline.create_execution(config) as exe:
        do_work(exe)
    # No commit_output_assets() yet — let everything stage.

# 3. Reconnect. Drain everything in one pass.
ml_online = DerivaML(hostname=..., catalog_id=...,
                      working_dir="/workspace/project-x")
report = ml_online.commit_pending_executions(
    execution_rids=None,        # None = drain every staged execution
    clean_folder=False,         # True to also wipe working dirs after success
)
print(report)  # UploadReport: total_uploaded, total_failed, per_table, errors
```

### Common errors

- `DerivaMLOfflineError` — A read that requires the live catalog was called in offline mode (`refresh_schema`, `diff_schema`, or any direct `ml.catalog.get(...)` call). Resolution: drop back to online mode for that call, or skip it.
- `DerivaMLConfigurationError: offline mode requires a cached schema...` — The workspace has no schema cache. Resolution: run online once with the same `working_dir` to populate it.
- `DerivaMLConfigurationError: cached schema is for X/Y, but __init__ was called with A/B` — The workspace cache is for a different `(hostname, catalog_id)`. Resolution: use a different `working_dir` per catalog, or refresh online against the new catalog.
