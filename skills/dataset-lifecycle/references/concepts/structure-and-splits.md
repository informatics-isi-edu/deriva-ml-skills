---
type: Concept
title: Dataset structure, splitting, and subsampling
description: Standalone vs nested vs split structure, the split_dataset primitive (two-way, three-way, strategies, partition unit), and the subsample primitive.
---

# Dataset structure, splitting, and subsampling

## Dataset Structure: Standalone, Nested, and Splits

Before creating a dataset, decide its structure. The right choice depends on how the dataset relates to other data in the catalog.

### Decision guide

| Situation | Structure | How |
|-----------|-----------|-----|
| Building a new collection from scratch | Standalone dataset | `deriva_ml_create_dataset` |
| Need train/test/val partitions from existing data | Split children | Script that opens an execution and calls `split_dataset(ml, source_rid, exe, ...)` |
| Curating a focused subset for a specific experiment | New standalone dataset | `deriva_ml_create_dataset` + `deriva_ml_add_dataset_members` with selected RIDs |
| Grouping related datasets together | Manual nesting | `deriva_ml_create_dataset` + `deriva_ml_add_dataset_members(parent_rid, members={"Dataset": [child_rid]})` |
| Creating a versioned snapshot for reproducibility | Any structure | Create, populate, then pin version in config |

### Nested datasets

Datasets can contain other datasets as children, forming hierarchies. The most common use is train/test/validation splits:

```
Complete Dataset (type: Complete, Labeled)
└── Split (type: Split — created by split_dataset)
    ├── Training (type: Training, Labeled — 70%)
    ├── Validation (type: Validation, Labeled — 10%)
    └── Testing (type: Testing, Labeled — 20%)
```

Child datasets are independent — they have their own RIDs, versions, and types. The parent-child relationship is purely organizational. Child datasets automatically inherit their parent's element types.

`split_dataset` creates nested datasets automatically. You can also nest manually — children are members of the parent's `Dataset` element type:

```
# MCP — add a child dataset by adding it as a member of the Dataset element type
deriva_ml_add_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="1-PAR", members={"Dataset": ["1-CHD"]})
```

Children are members of the parent's element-type `Dataset`.

```python
# Python API
parent_dataset.add_dataset_members(
    members=[child1.dataset_rid, child2.dataset_rid]
)
```

## Splitting Datasets

`split_dataset` partitions a dataset into training, testing, and optionally validation subsets. It follows scikit-learn conventions (`test_size`, `train_size`, `val_size`, `shuffle`, `seed`) and creates a proper dataset hierarchy with full provenance tracking.

### Two-way split (default)

```
Split (parent, type: "Split")
├── Training (type: "Training")
└── Testing (type: "Testing")
```

### Three-way split (when `val_size` is provided)

```
Split (parent, type: "Split")
├── Training (type: "Training")
├── Validation (type: "Validation")
└── Testing (type: "Testing")
```

### Splitting strategies

- **Random** (default): Shuffles members and splits at the boundary. Fast for any size. Dispatches to the built-in `random_split` selector.
- **Stratified**: Maintains class distribution across partitions. Requires `stratify_by_column` and `include_tables`.
- **Predicate-based** (custom `selection_fn`): A callable that takes the denormalized DataFrame and returns the partition assignment for each row. Use this when the train/test boundary is defined by a value in the data — e.g., "CIFAR's canonical split: rows where `Image.Split == 'train'` go to training, the rest to testing." The `_cifar10_datasets.py` worked example in `deriva-ml-model-template` uses this path.

### Key parameters

- `dry_run=true` — preview the split plan without modifying the catalog.
- `seed` — random seed for reproducibility (default: 42).
- `*_types=["Labeled"]` — content-axis types to propagate to each partition. `Training`/`Testing`/`Validation` plus `Split_Partition` are auto-assigned — don't list them here.
- `stratify_by_column` — denormalized column name format: `{TableName}_{ColumnName}`.
- `stratify_missing` — how to handle nulls in the stratify column: `"error"` (default), `"drop"`, or `"include"`.
- `selection_fn` — caller-supplied callable for predicate-based splits. Python-only (not crossable through MCP).
- `partition_by` — `"element"` or `"row"`. Controls the granularity at which the split partitions rows across Training/Testing/Validation. See "Partition unit" below.

### Partition unit (`partition_by`)

`split_dataset` and `subsample` both partition along one of two granularities, selected by `partition_by`:

| `partition_by` | What it does | Element-RID disjointness |
|----------------|--------------|--------------------------|
| `"element"` | Dedupes the denormalized DataFrame to one row per `element_table` RID **before** partitioning. Every member is assigned to exactly one partition. | **Asserted after partitioning.** A failure indicates a bug. |
| `"row"` | Partitions denormalized rows directly. The same element RID may legitimately appear in multiple partitions when the denormalization fans out per-element (e.g., one Image with three Annotator features produces three rows). | **Not asserted** — fan-out is the point of `"row"`. |

When `row_per` equals (or auto-resolves to) `element_table`, the two modes are equivalent and `partition_by` can be omitted (it's auto-resolved). Pass it explicitly when `row_per != element_table` — the call will error otherwise, because the two modes give materially different partitions and the right answer is caller-specific.

### Source recorded as execution input, not as `Dataset_Dataset` parent

`split_dataset` does NOT create a `Dataset_Dataset` edge from `source_dataset_rid` to the Split (or to any of its Training/Testing/Validation children). The source is recorded as an **input of the producing execution** via `Execution.add_input_dataset`, and the Split + partitions are recorded as that execution's outputs.

The walkable provenance path is therefore:

```
source --[input of]--> execution --[output]--> Split / Training / Testing / Validation
```

This means:

- `source.list_dataset_children()` (and the `deriva_ml_list_dataset_relations` MCP tool) will **NOT** list the Split.
- `execution.list_input_datasets()` returns the source.
- `dataset.producing_execution.list_input_datasets()` reaches the source from any Split child.
- A lineage walk (`deriva_ml_get_lineage`) reaches splits from the source and vice versa.

The same design applies to `subsample` — source is an execution input, subsample is an execution output, no `Dataset_Dataset` edge.

This matches [ADR-0001](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0001-lineage-walks-data-flow-not-orchestration.md) — *lineage walks data flow, not orchestration*. Nesting a split under its source would re-partition the source's own members and flip the source's version every time someone re-splits it, which is the wrong cardinality for a "the source is an input I consumed" relationship.

For the full parameter reference, MCP tool examples, and Python API, see `workflow.md`. The `subsample` primitive (stratified subsampling of a single dataset, no partitioning) is documented in the same place.

## Subsampling Datasets

`subsample(ml, source_dataset_rid, exe, size=, ...)` is the **peer primitive** to `split_dataset`. Where `split_dataset` partitions a source into two or three non-overlapping children, `subsample` produces **one output dataset** whose member set is a stratified random subset of the source's members. Mirrors sklearn's `resample(stratify=y, replace=False, n_samples=N)` semantics: stratified sample without replacement.

### When to use `subsample` vs `split_dataset`

| Goal | Reach for | Why |
|------|-----------|-----|
| Train / test / validation partitions of a source | `split_dataset` | Multiple non-overlapping outputs; partition assignment by position, predicate, or stratification |
| Smaller variant of a single dataset (for rapid dev iteration, debugging, baseline runs) | `subsample` | One output; stratified random subset; no partition role assigned by the operation itself |
| "Quick dev subset" of an existing Training dataset | `subsample(training_rid, exe, size=400, dataset_types=["Training", "Labeled"])` | Caller propagates role and content tags; `Subsample` origin tag is auto-added |
| Pre-existing labeled / unlabeled split, want a smaller mirror for debugging | Call `subsample` once per child of the existing Split | Each call produces an independent subsample; the source/subsample relationship lives in execution provenance, not in a `Dataset_Dataset` hierarchy |

There is intentionally **no `subsample_split` primitive** that parallel-subsamples each child of an existing Split and returns a mirror Split hierarchy — `subsample` is the more fundamental operation; composing it across the children of a Split is a few lines of caller code. (Documented as an explicit non-goal in the deriva-ml `2026-06-01-split-partition-tag-and-subsample-design` spec.)

### Key parameters

- `size` — `int` for an absolute count, `float ∈ (0, 1)` for a fraction of the source's size.
- `stratify_by_column` — optional; when set, preserves class proportions. Requires `include_tables`.
- `stratify_missing` — `"error"` (default), `"drop"`, or `"include"`, same semantics as `split_dataset`.
- `dataset_types` — caller-supplied additional tags. `Subsample` is always appended automatically (deduplicated defensively if the caller also passes it). Typical pattern: `dataset_types=["Training", "Labeled"]` to keep the role + content axes coherent with the source.
- `partition_by` — same `"element"` / `"row"` choice as `split_dataset`. Most subsamples should be `"element"` (one row per element RID); `"row"` is for unusual cases where per-element fan-out matters.
- `dry_run` — preview without mutating the catalog.

The full parameter table is in `workflow.md` § "Subsampling Datasets".
