---
type: Concept
title: Dataset versioning and identification
description: Characterization & validation roadmap, the ADR-0003 dev/release version model, and the RID + version DatasetSpec identity pair.
---

# Dataset versioning and identification

## Characterization & validation (roadmap, not yet implemented)

> **Status:** The four operations below — `characterize_dataset`, `compare_datasets`, `validate_split`, `validate_subsample` — are **specified but not yet implemented** in deriva-ml as of v1.42.0. The validation layer is a follow-up PR to the v1.42.0 `Split_Partition` + `subsample` work; the design is sketched in [deriva-ml spec `2026-06-01-split-partition-tag-and-subsample-design.md` §10](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/superpowers/specs/2026-06-01-split-partition-tag-and-subsample-design.md).
>
> Until those land, the validation that *does* exist is `split_dataset`'s built-in write-time disjointness assertion (for `partition_by="element"`) and the `is_dirty()` / `release_diff()` / `compare_versions()` drift-detection methods documented above. This section will be filled in when the upstream APIs ship; do not pre-emptively use names like `characterize_dataset(...)` in scripts until then.

When the follow-up PR lands, this section will document:

- **`characterize_dataset(dataset_rid, version=...)`** — class-distribution summary, member counts per element type, per-feature value distributions. Useful for sanity-checking what a dataset actually contains before training.
- **`compare_datasets(dataset_rid_a, dataset_rid_b, ...)`** — diff two datasets (or two versions of the same dataset) along the same dimensions. Detects class-distribution drift, member-set drift, and feature-value drift.
- **`validate_split(split_rid)`** — post-hoc validation of a Split hierarchy: confirms disjointness, checks fraction targets, surfaces stratification drift between partitions.
- **`validate_subsample(subsample_rid)`** — confirms a subsample's relationship to its source, including stratification fidelity.

All four are read-shaped operations and are good fits for MCP tool wrappers (no live `Execution` context required) — once the Python API ships, the deriva-ml-mcp-plugin will likely expose them as `characterize_dataset` etc. under the usual `deriva_ml_` tool prefix. Track [deriva-ml task #48](https://github.com/informatics-isi-edu/deriva-ml/) for status.

## Dataset Versioning (ADR-0003 dev/release model)

Per [ADR-0003](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0003-dataset-dev-versioning-model.md), datasets carry a **two-state PEP 440 version** at any moment:

- **Released** (`0.4.0`) — frozen catalog snapshot, citable, reproducible. Created by `deriva_ml_release_dataset`.
- **Dev** (`0.4.0.post1.dev3`) — mutable working state between releases. The PEP 440 dev-release suffix marks "drift since the last release"; dev rows have no snapshot, so cite URLs resolve to the live catalog.

PEP 440 release segments (the X.Y.Z portion):

| Segment | Bump when | Examples |
|-----------|-------------------|----------|
| **Major** (X.0.0) | Breaking changes, schema modifications | Table columns added/removed, restructured tables |
| **Minor** (0.X.0) | New data, new features, non-breaking additions | Members added, new feature annotations, split created |
| **Patch** (0.0.X) | Bug fixes, metadata corrections | Fixed mislabeled records, corrected metadata, typo fixes |

DerivaML assigns version `0.1.0` (released) when a dataset is created. After that, mutations flip to dev, and `deriva_ml_release_dataset` is the only operation that mints a new released version.

### Released versions are snapshots; dev versions follow live state

Each **released** version is tied to a catalog snapshot timestamp. When you download a specific released version, you get the exact data that existed when that version was created — not the current state. This is the foundation of reproducibility: the same dataset RID + released version always produces the same data.

**Dev versions have no snapshot.** They resolve to whatever the catalog has right now. Two reads of the same dev label at different times may differ if the catalog drifted between them. Dev labels are notational, not citational.

**If you've modified data since the last release** (added features, updated records, corrected labels via the dataset API), those changes are NOT included in any released version — they live on the dev row. Call `deriva_ml_release_dataset` to promote the dev period to a new released version that captures the current state.

### Mutations land on dev

The "every mutation lands on dev" rule:

| Operation | Effect on `current_version` |
|---|---|
| `deriva_ml_add_dataset_members` | Flip to `<last_release>.post1.dev1` (or advance `.devN` if dev row exists) |
| `deriva_ml_delete_dataset_members` | Flip to dev (advance `.devN`) |
| `split_dataset` | Flip to dev (advance `.devN`) |
| Adding a feature value (via `exe.add_features()` from the `populate_feature_values.py` template) | Drift is **not** auto-detected; if you want to record it, call `dataset.mark_dev(description)` from the Python API |
| `deriva_ml_release_dataset(bump, description)` | Promote dev row to released `<bumped>.<from>.<last_release>` |

**Things that do NOT flip the dataset to dev:**

- Execution-output assets (model weights, prediction CSVs, training logs, plots) — linked to the producing execution, not to dataset members.
- Reads (`deriva_ml_get_dataset`, `deriva_ml_list_dataset_members`, `deriva_ml_bag_info`).
- Cache warm-ups via the bundled `skills/manage-deriva-storage/scripts/warm_cache.py` template — it only populates the local cache directory and never touches catalog state.

### Drift detection (Python API only)

deriva-ml exposes three drift-detection methods on `Dataset`:

- `dataset.is_dirty() -> bool` — fast predicate.
- `dataset.release_diff() -> dict[str, int]` — per-table change counts since the last release.
- `dataset.compare_versions(v_a, v_b) -> dict[str, int]` — per-table counts between any two endpoints.

These don't appear on the MCP tool surface; reach for them from notebook code or scripts.

### Release descriptions

Always provide a description when calling `deriva_ml_release_dataset`. Good release notes explain what changed, why, and the impact:

- "Added severity grading feature (mild/moderate/severe) to all 12,450 images. Required for new stratified training pipeline"
- "Fixed 47 mislabeled pneumonia images identified in audit review. Retraining recommended for any model trained on v1.1.0"
- "Added 2,000 new COVID-19 images from March 2026 collection. Increases COVID class from 3,200 to 5,200 images"

Bad descriptions: "Updated", "New version", "Changes", or empty.

### Dataset history

Every version increment is recorded in the dataset's history — a chronological log of all versions with their snapshot timestamps, descriptions, and the execution that created them.

```python
# Python API
history = dataset.dataset_history()
for entry in history:
    print(f"Version {entry.dataset_version}: {entry.description} (snapshot: {entry.snapshot})")
```

Each `DatasetHistory` entry contains:
- `dataset_version` — the version number (e.g., `0.3.0`)
- `snapshot` — catalog snapshot timestamp (ties this version to an exact catalog state)
- `description` — why this version was created
- `execution_rid` — which execution created it (provenance)
- `minid` — permanent identifier URL, if registered

### Versioning rules for experiments

1. **Always use explicit versions for real experiments.** Never use "current" or omit the version in production configs. The only acceptable use of "current" is for debugging and dry runs.
2. **Increment after catalog changes.** If you modify anything that affects dataset contents, increment before running experiments.
3. **Update configs immediately after incrementing.** The config file should always reference the version you intend to use.
4. **Commit configs before running.** The git commit hash in the execution record should match the config state.

### Pre-experiment checklist

Before running any experiment:
- [ ] Dataset version is explicitly specified (not "current")
- [ ] Config file is updated with the correct version
- [ ] Config changes are committed to git

After any catalog modification:
- [ ] Version has been incremented with a descriptive message
- [ ] All affected config files are updated to the new version
- [ ] Config changes are committed to git

### Common versioning mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Running without explicit version | Results not reproducible | Always specify version in config |
| Expecting catalog changes in old versions | Old versions are frozen snapshots | Increment version to capture changes |
| Empty or vague version descriptions | Cannot understand version history | Write specific, informative descriptions |
| Not updating config after increment | Experiments still use old version | Update config immediately after incrementing |
| Not committing config before running | Git hash doesn't match config state | Always commit, then run |

## Identifying a Dataset: RID + Version

A dataset is uniquely identified by its **RID** (Resource Identifier), like any catalog record. But because datasets evolve over time, the combination of **RID + version** is what identifies a specific, reproducible snapshot of the data.

This pair is captured in a **DatasetSpec** — the standard way to reference a dataset in code:

```python
from deriva_ml.dataset import DatasetSpec, DatasetSpecConfig

# Python API
DatasetSpec(rid="28EA", version="0.4.0")

# Hydra-zen configuration (version is required)
DatasetSpecConfig(rid="28EA", version="0.4.0")
```

Use the `deriva_ml_get_dataset_spec` MCP tool to generate the correct `DatasetSpecConfig` string for a dataset, including its current version. The `deriva_ml_get_dataset` tool also shows the current version.

### Binding to a specific version

```python
# Get current version
current = dataset.current_version  # e.g., "1.2.0"

# Pass version= to operate at a specific version (keyword-only)
members = dataset.list_dataset_members(version="1.0.0")  # members at v1.0.0
```
