---
type: Concept
title: Dataset structure, splitting, and subsampling
description: Standalone vs nested vs split structure, the split_dataset primitive (two-way, three-way, strategies, partition unit), and the subsample primitive.
---

# Dataset structure, splitting, and subsampling

**Contents**

- [Dataset Structure: Standalone, Nested, and Splits](#dataset-structure-standalone-nested-and-splits)
  - [Decision guide](#decision-guide)
  - [Nested datasets](#nested-datasets)
- [Splitting Datasets](#splitting-datasets)
  - [Two-way split (default)](#two-way-split-default)
  - [Three-way split (when `val_size` is provided)](#three-way-split-when-val_size-is-provided)
  - [Splitting strategies](#splitting-strategies)
  - [Key parameters](#key-parameters)
  - [Partition unit (`partition_by`)](#partition-unit-partition_by)
  - [Source recorded as execution input, not as `Dataset_Dataset` parent](#source-recorded-as-execution-input-not-as-dataset_dataset-parent)
- [Splitting by subject (no subject in two partitions)](#splitting-by-subject-no-subject-in-two-partitions)
  - [Checking for leakage](#checking-for-leakage)
- [Subsampling Datasets](#subsampling-datasets)
  - [When to use `subsample` vs `split_dataset`](#when-to-use-subsample-vs-split_dataset)
  - [Key parameters](#key-parameters-1)

## Dataset Structure: Standalone, Nested, and Splits

Before creating a dataset, decide its structure. The right choice depends on how the dataset relates to other data in the catalog.

### Decision guide

| Situation | Structure | How |
|-----------|-----------|-----|
| Building a new collection from scratch | Standalone dataset | `deriva_ml_create_dataset` |
| Need train/test/val partitions from existing data | Split children | Script that opens an execution and calls `split_dataset(ml, source_rid, exe, ...)` |
| Curating a focused subset for a specific experiment | New standalone dataset | Curated-subset script from the template (`curated-subsets.md`) |
| Grouping related datasets together | Manual nesting | `deriva_ml_create_dataset` + `deriva_ml_add_dataset_members(parent_rid, members={"Dataset": [child_rid]})` |
| Creating a versioned snapshot for reproducibility | Any structure | Create, populate, release, then pin the released version in config |

### Nested datasets

Datasets can contain other datasets as children, forming hierarchies. The most common one is the hierarchy `split_dataset` creates:

```
Split (type: Split)
├── Training   (Training, Split_Partition, Labeled — 70%)
├── Validation (Validation, Split_Partition, Labeled — 10%)
└── Testing    (Testing, Split_Partition, Labeled — 20%)
```

The source it was split from (often a `Complete` dataset) is **not** the Split's parent: it is an input of the execution that ran the split (see below).

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
- **Predicate-based** (custom `selection_fn`): A callable that takes the denormalized DataFrame and returns the partition assignment for each row. Use this when the train/test boundary is defined by a value in the data — e.g., "CIFAR's canonical split: rows where `Image.Split == 'train'` go to training, the rest to testing." The `src/scripts/_cifar10_datasets.py` worked example in `deriva-ml-cifar-example` uses this path.

### Key parameters

- `dry_run=true` — preview the split plan without modifying the catalog.
- `seed` — random seed for reproducibility (default: 42).
- `*_types=["Labeled"]` — content-axis types to propagate to each partition. `Training`/`Testing`/`Validation` plus `Split_Partition` are auto-assigned — don't list them here.
- `stratify_by_column` — a denormalized column in dot notation, `Table.Column` (e.g. `Image_Class.Name`); list the options with `dataset.list_denormalized_columns(...)`.
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

The principle: *lineage walks data flow, not orchestration*. Nesting a split under its source would re-partition the source's own members and flip the source's version every time someone re-splits it, which is the wrong cardinality for a "the source is an input I consumed" relationship.

For the full parameter reference and script examples, see `workflow.md` (splitting is script-only; there is no MCP tool for it). The `subsample` primitive (stratified subsampling of a single dataset, no partitioning) is documented in the same place.

## Splitting by subject (no subject in two partitions)

When several records come from one subject — a patient's two eyes, a patient's
repeat scans — splitting by record puts the same patient in train and test, and
the test score is inflated. `split_dataset` partitions **element rows**; it has no
built-in grouping. Two ways to keep each subject in one partition:

- **The members are the subjects.** If the dataset's members are `Subject` rows,
  pass `element_table="Subject"`: each subject lands in exactly one partition, and
  its images follow it through FK traversal when the bag is exported.
- **The members are images.** Pass a group-aware `selection_fn` that assigns whole
  subjects to partitions. Include the subject table in `include_tables` so its RID
  is a column; confirm the column name with
  `dataset.list_denormalized_columns(["Image", "Subject"])`.

```python
import numpy as np
from deriva_ml.dataset.split import split_dataset

def by_subject(df, partition_sizes, seed):
    """Assign whole subjects to partitions so no subject spans two."""
    rng = np.random.default_rng(seed)
    groups = df.groupby("Subject.RID").indices   # subject RID -> row positions
    subjects = list(groups)
    rng.shuffle(subjects)
    names = list(partition_sizes)
    rows = {n: [] for n in names}
    for s in subjects:
        # Give the subject to the partition furthest below its target size.
        n = min(names, key=lambda k: len(rows[k]) / partition_sizes[k])
        rows[n].extend(groups[s])
    return {n: np.array(sorted(v)) for n, v in rows.items()}

result = split_dataset(
    ml, source_rid, exe,
    test_size=0.2, seed=42,
    element_table="Image",
    include_tables=["Image", "Subject"],
    selection_fn=by_subject,
    training_types=["Labeled"], testing_types=["Labeled"],
    split_description="80/20 split by patient; no patient in both partitions",
)
```

Partition sizes come out approximate, because subjects are never divided. To
stratify by class as well, extend the function to balance classes across
subjects; `selection_fn` and `stratify_by_column` can't be combined.

### Checking for leakage

Run this before releasing a split, and record the result in the dataset design
doc's validation section:

```python
def subjects(rid):
    ds = ml.lookup_dataset(rid)
    df = ds.get_denormalized_as_dataframe(["Image", "Subject"],
                                          version=ds.current_version)
    return set(df["Subject.RID"])

train, test = subjects(result.training.rid), subjects(result.testing.rid)
overlap = train & test
assert not overlap, f"{len(overlap)} subjects appear in both partitions"
```

For a validation partition, check each pair. Element RIDs are disjoint by
construction under the default `partition_by="element"`; subject overlap is the
check that matters.

## Subsampling Datasets

`subsample(ml, source_dataset_rid, exe, size=, ...)` is the **peer primitive** to `split_dataset`. Where `split_dataset` partitions a source into two or three non-overlapping children, `subsample` produces **one output dataset** whose member set is a stratified random subset of the source's members. Mirrors sklearn's `resample(stratify=y, replace=False, n_samples=N)` semantics: stratified sample without replacement.

### When to use `subsample` vs `split_dataset`

| Goal | Reach for | Why |
|------|-----------|-----|
| Train / test / validation partitions of a source | `split_dataset` | Multiple non-overlapping outputs; partition assignment by position, predicate, or stratification |
| Smaller variant of a single dataset (for rapid dev iteration, debugging, baseline runs) | `subsample` | One output; stratified random subset; no partition role assigned by the operation itself |
| "Quick dev subset" of an existing Training dataset | `subsample(ml, training_rid, exe, size=400, dataset_types=["Training", "Labeled"])` | Caller propagates role and content tags; `Subsample` origin tag is auto-added |
| Pre-existing labeled / unlabeled split, want a smaller mirror for debugging | Call `subsample` once per child of the existing Split | Each call produces an independent subsample; the source/subsample relationship lives in execution provenance, not in a `Dataset_Dataset` hierarchy |

There is intentionally **no `subsample_split` primitive** that parallel-subsamples each child of an existing Split and returns a mirror Split hierarchy — `subsample` is the more fundamental operation; composing it across the children of a Split is a few lines of caller code.

### Key parameters

- `size` — `int` for an absolute count, `float ∈ (0, 1)` for a fraction of the source's size.
- `stratify_by_column` — optional; when set, preserves class proportions. Requires `include_tables`.
- `stratify_missing` — `"error"` (default), `"drop"`, or `"include"`, same semantics as `split_dataset`.
- `dataset_types` — caller-supplied additional tags. `Subsample` is always appended automatically (deduplicated defensively if the caller also passes it). Typical pattern: `dataset_types=["Training", "Labeled"]` to keep the role + content axes coherent with the source.
- `partition_by` — same `"element"` / `"row"` choice as `split_dataset`. Most subsamples should be `"element"` (one row per element RID); `"row"` is for unusual cases where per-element fan-out matters.
- `dry_run` — preview without mutating the catalog.

The full parameter table is in `workflow.md` § "Subsampling Datasets".
