# Dataset Concepts

Background on datasets in DerivaML. For the step-by-step guide to creating and managing datasets, see `workflow.md`.

> **Stateless model:** the new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Table of Contents

- [What is a Dataset?](#what-is-a-dataset)
- [Discovering Existing Datasets](#discovering-existing-datasets)
- [Dataset Types](#dataset-types)
- [Dataset Element Types](#dataset-element-types)
- [Dataset Structure: Standalone, Nested, and Splits](#dataset-structure-standalone-nested-and-splits)
- [Splitting Datasets](#splitting-datasets)
- [Subsampling Datasets](#subsampling-datasets)
- [Characterization & validation (roadmap)](#characterization--validation-roadmap-not-yet-implemented)
- [Dataset Versioning](#dataset-versioning)
- [Identifying a Dataset: RID + Version](#identifying-a-dataset-rid--version)
- [Exploring and Navigating Datasets](#exploring-and-navigating-datasets)
- [Using Datasets](#using-datasets)
- [Downloading Datasets as Bags](#downloading-datasets-as-bags)
- [Deleting Datasets](#deleting-datasets)
- [Operations Summary](#operations-summary)

---

## What is a Dataset?

A dataset is a versioned collection of records (members) from one or more catalog tables. Datasets organize data for ML workflows — training sets, evaluation sets, curated subsets — with full provenance tracking.

Each dataset has:
- **An RID** — unique identifier, like any other catalog record
- **Members** — specific records included in the dataset, referenced by RID
- **Element types** — which tables can contribute members
- **Types** — labels describing the dataset's purpose (Training, Testing, etc.)
- **A version** — monotonically increasing, tied to a catalog snapshot for reproducibility
- **A description** — what the dataset contains and why it exists
- **Provenance** — which execution created it, which executions have used it

Datasets can be heterogeneous: a single dataset can contain records from multiple tables (e.g., both Image and Subject records). DerivaML manages the relationships between these records and makes them accessible from all FK paths.

## Discovering Existing Datasets

Before creating a new dataset, check whether an existing one already serves your purpose. Duplicate datasets fragment data and confuse downstream consumers.

**MCP tools and resources:**
```
# Search for datasets by description, type, or purpose (preferred for discovery)
rag_search("your purpose here", doc_type="catalog-data")

# Full structured list of all datasets — preferred typed form
deriva_ml_list_datasets(hostname="data.example.org", catalog_id="1")

# Equivalent resource URI
Read resource: deriva://catalog/{h}/{c}/deriva-ml/datasets

# Get details about a specific dataset
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")

# Query datasets with filters — for whole-row fetches use get_entities;
# use query_attribute when you need column projection or path syntax (comparison ops, joins).
get_entities(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Dataset", filters={"Description": "..."})
```

**Python API:**
```python
# Search datasets
all_datasets = ml.find_datasets()
for ds in all_datasets:
    print(f"{ds.dataset_rid}: {ds.description} (v{ds.current_version})")

# Look up a specific dataset by RID
dataset = ml.lookup_dataset("1-ABC4")
```

**Before creating, ask:**
- Does a dataset with this data already exist? Check descriptions and member counts.
- Can an existing dataset be extended with `deriva_ml_add_dataset_members`?
- Can an existing dataset be split differently via a script that calls `split_dataset(ml, source_rid, exe, ...)`?
- Is the needed data a subset of an existing "Complete" dataset?

## Dataset Types

Dataset types are labels from the `Dataset_Type` controlled vocabulary. They describe the dataset along independent dimensions and are used for organizing, filtering, and discovery. A dataset can have multiple types simultaneously.

### The three axes of `Dataset_Type`

Built-in `Dataset_Type` terms fall along **three orthogonal axes**. A dataset typically carries one tag from each relevant axis. The axes mean different things to readers and operations.

| Axis | What it answers | Built-in terms | Inheritance & propagation |
|------|-----------------|----------------|---------------------------|
| **Role** | What is this dataset *for* in its immediate context? | `Training`, `Testing`, `Validation`, `Complete`, `Split` | **Not inherited** from a parent dataset, **not propagated** to children. `split_dataset` assigns role tags to its children based on each child's position in the split, **regardless** of the source dataset's role. A source tagged `Testing` produces a Training partition tagged `Training`, not `Testing`. |
| **Content** | What *kind of data* does it contain? | `Labeled`, `Unlabeled` (built-in); domain types like `Fundus`, `CIFAR_10`, `Genomic` (user-added) | **May propagate** when the partitioning operation preserves the property — a stratified sample of a `Labeled` dataset is still `Labeled`. Propagation is a caller decision, expressed via `training_types=`, `testing_types=`, `validation_types=` on `split_dataset` and `dataset_types=` on `subsample`. |
| **Origin** | How did this dataset *come to exist*? | `Split` (parent of a split hierarchy), `Split_Partition` (child of a Split), `Subsample` (output of `subsample()`) | **Never inherited.** Always set by the producing operation, never copied. |

### Built-in terms by axis

| Term | Axis | Meaning |
|------|------|---------|
| `Training` | Role | Data for model training |
| `Testing` | Role | Data for model evaluation |
| `Validation` | Role | Data for hyperparameter tuning |
| `Complete` | Role | Full dataset before any splitting |
| `Split` | Role + Origin | The parent container produced by `split_dataset`; holds the Training/Testing/Validation children as `Dataset_Dataset` members. A Split is *not* itself a `Split_Partition` — it is the container. |
| `Split_Partition` | Origin | Auto-applied by `split_dataset` to *every* Training/Testing/Validation child. The discriminator that distinguishes a **corpus-role** `Training` dataset (a training corpus, hand-built or imported) from a **partition-role** `Training` dataset (the training half of a split). Tag hand-built split children with `Split_Partition` too if you want them discoverable through the same filters. |
| `Subsample` | Origin | Auto-applied to the output of `subsample()`. Distinguishes a subsampled dataset from a hand-curated dataset of the same role and content. The source relationship lives in execution provenance, not in `Dataset_Dataset` edges — there is no parent/child hierarchy between a subsample and its source. |
| `Labeled` | Content | Records have ground truth feature annotations |
| `Unlabeled` | Content | Records lack feature annotations |

### Why the role/origin distinction matters in practice

Without the origin axis, the query *"find every training partition of a split"* and the query *"find every training corpus that isn't a partition"* are indistinguishable — both return everything tagged `Training`. With `Split_Partition` and `Subsample` available, the filters become 1-hop:

- *partition-role training* — `Training` ∧ `Split_Partition`
- *corpus-role training* — `Training` ∧ ¬`Split_Partition` ∧ ¬`Subsample`
- *subsampled training data* — `Training` ∧ `Subsample`

### Types are orthogonal tags

Types describe independent dimensions. A dataset gets one or more tags from each relevant dimension. The key principle is that types from different dimensions compose freely — they are not alternatives to each other but describe different aspects of the dataset.

**Example compositions:**

| Dataset | Types | Meaning |
|---------|-------|---------|
| Master collection | `Complete`, `Labeled` | All records, all annotated |
| Training partition | `Training`, `Labeled` | Training split with ground truth |
| Unlabeled prediction set | `Testing` | Inference data, no labels |
| Quick dev subset | `Training`, `Labeled` | Small curated subset for iteration |

The substitution test helps identify whether two types belong on the same dimension: can you swap one for the other? `Training` swaps for `Testing` (same dimension: split role). `Training` does *not* swap for `Labeled` (different dimensions: role vs annotation status). If two types can both apply to the same dataset and aren't alternatives, they describe different dimensions.

### Creating custom types

Custom types are created using the generic `add_term` tool on the `Dataset_Type` vocabulary:

```
add_term(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Dataset_Type", name="Preprocessed", description="...", synonyms=[...])
```

Or in Python: `ml.add_term(MLVocab.dataset_type, ...)`. Before creating, check existing types — the term you need may already exist under a different name. Use `rag_search("dataset types", doc_type="catalog-schema")` to find types by meaning, or `list_vocabulary_terms(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Dataset_Type")` for the full list.

> **Need a brand-new vocabulary table?** `add_term` extends an existing vocabulary table; to create a new one (a domain-specific vocabulary like `Tumor_Grade`), use `deriva_ml_create_vocabulary(...)`. See `deriva-ml-context` → "Creating a new vocabulary" for the rationale (curie prefix, default schema, navbar refresh) and the canonical call shape.

For DerivaML-specific guidance on `Dataset_Type` (built-in dimensions, composing types on a Dataset, worked examples), see `type-naming-strategy.md`. For the **generic vocabulary design principles** that this guidance builds on (orthogonal tagging, dimension identification, naming conventions, anti-patterns, the substitution test, semantic checking) — applicable to all four DerivaML vocabularies and any custom domain vocabulary — see the deriva-skills `manage-vocabulary` skill in `deriva-skills` at `skills/manage-vocabulary/references/term-naming-strategy.md`.

### How `split_dataset` assigns types

The Python API `split_dataset(ml, source_rid, exe, ...)` automatically assigns types to the datasets it creates:

- **Parent dataset** gets type `Split` (origin axis).
- **Training partition** gets `Training` (role) + `Split_Partition` (origin) + any additional `training_types` (content axis, caller-supplied).
- **Testing partition** gets `Testing` (role) + `Split_Partition` (origin) + any additional `testing_types`.
- **Validation partition** gets `Validation` (role) + `Split_Partition` (origin) + any additional `validation_types` (if three-way split).

To mark partitions as having ground truth labels, pass `training_types=["Labeled"]`, etc. — those are content-axis types that propagate from the source's data properties. **Don't** manually pass `Training` / `Testing` / `Validation` in `*_types` — those are auto-assigned and duplicates are de-duped defensively.

### How `subsample` assigns types

The Python API `subsample(ml, source_rid, exe, size=N, ...)` produces a single output dataset:

- The output gets `Subsample` (origin axis), always — applied even if the caller passes `Subsample` in `dataset_types=` (deduplicated defensively).
- The output gets any caller-supplied `dataset_types=` on top — typically a role tag (`Training`, `Testing`) and any content-axis tags worth propagating (`Labeled` if the source is labeled and the stratification preserves that).
- Role-axis tags do **not** inherit from the source. A `Testing` source produces a subsample tagged only with what the caller specifies.

The source/subsample relationship is **not** a `Dataset_Dataset` edge — the source is recorded as an *input of the producing execution*, mirroring `split_dataset`'s design. Reach the source via `subsample_output.producing_execution.list_input_datasets()`, not via `list_dataset_parents()`.

## Dataset Element Types

Before adding records from a table to any dataset, that table must be registered as a **dataset element type**. This is a catalog-level operation — once registered, records from that table can be added to any dataset in the catalog.

Registration creates the association table (`Dataset_{TableName}`) that links datasets to records in that table. Without this association table, the catalog has no way to track which records belong to which datasets.

### Why element types matter for planning

Understanding which element types are available is an early planning step — it determines what kind of data can go into your dataset. Check what's registered before deciding what to include:

```
# MCP — purpose-built tool for element-type discovery
deriva_ml_list_dataset_element_types(hostname, catalog_id)
```

```python
# Python API
element_types = ml.list_dataset_element_types()
for table in element_types:
    print(table.name)
```

### Registering element types

```
# MCP
deriva_ml_add_dataset_element_type(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", element_table="Image")
```

```python
# Python API
ml.add_dataset_element_type("Image")
```

**Key points:**
- Registration is idempotent — calling it again for an already-registered table is harmless
- Common tables to register: `Subject`, `Image` (or other asset tables), `Observation`, and any custom domain tables whose records should be dataset members
- Element types also determine the starting points for FK traversal during bag export (see [Downloading Datasets as Bags](#downloading-datasets-as-bags))

### Element types and bag exports

During bag export, only tables registered as element types that have members in the dataset serve as starting points for FK traversal. Unregistered tables are traversed normally if reached via FK paths, but cannot contribute starting points. This means:

- A table must be an element type *and* have members for its records to be traversal roots
- A registered element type with *no members* in a dataset acts as a traversal boundary — the export won't follow FK paths through it
- This prevents expensive joins that would return empty results

See `bags.md` for the full FK traversal algorithm.

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

- `source.list_dataset_children()` and `list_dataset_relations(source)` will **NOT** list the Split.
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

## Characterization & validation (roadmap, not yet implemented)

> **Status:** The four operations below — `characterize_dataset`, `compare_datasets`, `validate_split`, `validate_subsample` — are **specified but not yet implemented** in deriva-ml as of v1.42.0. The validation layer is a follow-up PR to the v1.42.0 `Split_Partition` + `subsample` work; the design is sketched in [deriva-ml spec `2026-06-01-split-partition-tag-and-subsample-design.md` §10](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/superpowers/specs/2026-06-01-split-partition-tag-and-subsample-design.md).
>
> Until those land, the validation that *does* exist is `split_dataset`'s built-in write-time disjointness assertion (for `partition_by="element"`) and the `is_dirty()` / `release_diff()` / `compare_versions()` drift-detection methods documented above. This section will be filled in when the upstream APIs ship; do not pre-emptively use names like `characterize_dataset(...)` in scripts until then.

When the follow-up PR lands, this section will document:

- **`characterize_dataset(dataset_rid, version=...)`** — class-distribution summary, member counts per element type, per-feature value distributions. Useful for sanity-checking what a dataset actually contains before training.
- **`compare_datasets(dataset_rid_a, dataset_rid_b, ...)`** — diff two datasets (or two versions of the same dataset) along the same dimensions. Detects class-distribution drift, member-set drift, and feature-value drift.
- **`validate_split(split_rid)`** — post-hoc validation of a Split hierarchy: confirms disjointness, checks fraction targets, surfaces stratification drift between partitions.
- **`validate_subsample(subsample_rid)`** — confirms a subsample's relationship to its source, including stratification fidelity.

All four are read-shaped operations and are good fits for MCP tool wrappers (no live `Execution` context required) — once the Python API ships, the deriva-ml-mcp-plugin will likely expose them as `deriva_ml_characterize_dataset`, etc. Track [deriva-ml task #48](https://github.com/informatics-isi-edu/deriva-ml/) for status.

## Dataset Versioning (ADR-0003 dev/release model)

Per [ADR-0003](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0003-dataset-dev-versioning-model.md), datasets carry a **two-state PEP 440 version** at any moment:

- **Released** (`0.4.0`) — frozen catalog snapshot, citable, reproducible. Created by `deriva_ml_release`.
- **Dev** (`0.4.0.post1.dev3`) — mutable working state between releases. The PEP 440 dev-release suffix marks "drift since the last release"; dev rows have no snapshot, so cite URLs resolve to the live catalog.

PEP 440 release segments (the X.Y.Z portion):

| Segment | Bump when | Examples |
|-----------|-------------------|----------|
| **Major** (X.0.0) | Breaking changes, schema modifications | Table columns added/removed, restructured tables |
| **Minor** (0.X.0) | New data, new features, non-breaking additions | Members added, new feature annotations, split created |
| **Patch** (0.0.X) | Bug fixes, metadata corrections | Fixed mislabeled records, corrected metadata, typo fixes |

DerivaML assigns version `0.1.0` (released) when a dataset is created. After that, mutations flip to dev, and `deriva_ml_release` is the only operation that mints a new released version.

### Released versions are snapshots; dev versions follow live state

Each **released** version is tied to a catalog snapshot timestamp. When you download a specific released version, you get the exact data that existed when that version was created — not the current state. This is the foundation of reproducibility: the same dataset RID + released version always produces the same data.

**Dev versions have no snapshot.** They resolve to whatever the catalog has right now. Two reads of the same dev label at different times may differ if the catalog drifted between them. Dev labels are notational, not citational.

**If you've modified data since the last release** (added features, updated records, corrected labels via the dataset API), those changes are NOT included in any released version — they live on the dev row. Call `deriva_ml_release` to promote the dev period to a new released version that captures the current state.

### Mutations land on dev

The "every mutation lands on dev" rule:

| Operation | Effect on `current_version` |
|---|---|
| `deriva_ml_add_dataset_members` | Flip to `<last_release>.post1.dev1` (or advance `.devN` if dev row exists) |
| `deriva_ml_delete_dataset_members` | Flip to dev (advance `.devN`) |
| `split_dataset` | Flip to dev (advance `.devN`) |
| Adding a feature value (via `exe.add_features()` from the `populate_feature_values.py` template) | Drift is **not** auto-detected; if you want to record it, call `dataset.mark_dev(description)` from the Python API |
| `deriva_ml_release(bump, description)` | Promote dev row to released `<bumped>.<from>.<last_release>` |

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

Always provide a description when calling `deriva_ml_release`. Good release notes explain what changed, why, and the impact:

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
from deriva_ml.dataset.aux_classes import DatasetSpec, DatasetSpecConfig

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

# Bind a dataset object to a specific version for version-aware operations
versioned_dataset = dataset.set_version("1.0.0")
members = versioned_dataset.list_dataset_members()  # members at v1.0.0
```

## Exploring and Navigating Datasets

Once a dataset exists, you need to understand what's in it — its structure, contents, hierarchy, and provenance. This section covers the read-side operations.

### Understanding a dataset's structure

Start by checking its metadata — types, element types, version, and description:

```
# MCP — typed call (preferred)
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")
```

```python
# Python API
dataset = ml.lookup_dataset("1-ABC4")
print(f"Description: {dataset.description}")
print(f"Version: {dataset.current_version}")
print(f"Types: {dataset.dataset_types}")
```

### Listing members

Members are the records that belong to a dataset. Results are returned as a JSON object mapping table names to arrays of `{RID}` objects — this grouping by table tells you which element types have data and how many records of each type:

```json
{
  "Image": [{"RID": "2-IMG1"}, {"RID": "2-IMG2"}, ...],
  "Subject": [{"RID": "2-SUB1"}, {"RID": "2-SUB2"}, ...]
}
```

This is the starting point for browsing — the table names tell you which element types to explore with `deriva_ml_denormalize_dataset`.

**MCP tools:**
```
# All members of the current version
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")

# Members at a specific version
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", version="1.0.0")

# Members including all nested child datasets
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", recurse=true)

# Limit results (useful for large datasets)
deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", limit=100)
```

**Python API:**
```python
# Current version — returns dict[str, list[dict]]
members = dataset.list_dataset_members()
for table_name, rids in members.items():
    print(f"{table_name}: {len(rids)} members")

# Specific version
members_v1 = dataset.list_dataset_members(version="1.0.0")
```

`deriva_ml_list_dataset_members` returns only RIDs, not actual record data. To see the data values (demographics, labels, metadata), use `deriva_ml_denormalize_dataset` with the table names discovered here (no dataset RID needed for schema exploration; add `dataset_rid` and `limit` for actual data) — see [Using Datasets](#using-datasets).

### Navigating hierarchies

Datasets form parent-child hierarchies. The most common is the split hierarchy created by `split_dataset`, but you can nest manually too.

**Listing children and parents in one call:**
```
# Both directions in a single call
deriva_ml_list_dataset_relations(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")

# Recurse for the full tree
deriva_ml_list_dataset_relations(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", recurse=true)

# At a specific version
deriva_ml_list_dataset_relations(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", version="1.0.0")
```

`deriva_ml_list_dataset_relations` returns both parents and children together; there is no separate parents-only call.

**When to use recursion:**
- Use `recurse=false` (default) when you only need the immediate level — e.g., listing the Training/Testing/Validation children of a Split dataset
- Use `recurse=true` when you need the full tree — e.g., listing all members across a Complete → Split → Training/Testing hierarchy
- Recursive member listing (`deriva_ml_list_dataset_members(..., recurse=true)`) aggregates members from the dataset and all its descendants

### Checking element types

Element types determine which tables can contribute members. Check what's available before planning a dataset, or verify what an existing dataset can contain:

```
# MCP — catalog-wide registered element types
deriva_ml_list_dataset_element_types(hostname="data.example.org", catalog_id="1")

# Or per-dataset element types (scoped to one dataset)
deriva_ml_list_dataset_element_types(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")
```

```python
# Python API — element types for a specific dataset
element_types = dataset.list_dataset_element_types()
for table in element_types:
    print(table.name)
```

### Provenance

Track which executions created or used a dataset:

```
# MCP — `deriva_ml_get_dataset` includes execution provenance
deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")
```

This returns all executions that used this dataset as an input — useful for understanding a dataset's lineage and which experiments depend on it.

## Using Datasets

Once a dataset is created and versioned, there are several ways to consume it.

### Browse in Chaise (web UI)

Every dataset has a page in the Chaise web interface where you can browse its metadata, types, members, children, and version history. Use `cite()` to generate a shareable URL:

```
# MCP — permanent URL with snapshot timestamp
cite(hostname="data.example.org", catalog_id="1", rid="1-ABC4")

# URL to current state (no snapshot)
cite(hostname="data.example.org", catalog_id="1", rid="1-ABC4", current=true)
```

```python
# Python API
url = ml.cite("1-ABC4")          # permanent snapshot URL
url = ml.cite("1-ABC4", current=True)  # live URL
```

### Reference in experiment configurations

The standard way to use a dataset in an ML experiment is through a Hydra-zen configuration file. The `DatasetSpecConfig` captures the RID and pinned version:

```python
from deriva_ml.dataset.aux_classes import DatasetSpecConfig

# In a config module (e.g., src/configs/datasets.py)
training_data = DatasetSpecConfig(rid="28EA", version="0.4.0")

# With download options
training_data = DatasetSpecConfig(
    rid="28EA",
    version="0.4.0",
    timeout=[10, 1800],          # increase read timeout for large datasets
    exclude_tables=["Study"],     # prune FK graph if needed
)
```

Use the `deriva_ml_get_dataset_spec` MCP tool to generate the correct config string including the current version. See the `write-hydra-config` and `configure-experiment` skills for how dataset configs integrate into experiment configurations.

### Query via MCP tools

For interactive exploration without downloading:

```
# Explore schema shape (no dataset needed)
deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=["Image", "Subject"])

# Denormalize with dataset-scoped info + row data
deriva_ml_denormalize_dataset(hostname="data.example.org", catalog_id="1", include_tables=["Image", "Subject"], dataset_rid="1-ABC4", limit=50)

# Query individual tables (whole rows from one table by FK -> use get_entities)
get_entities(hostname="data.example.org", catalog_id="1", schema="<schema>", table="Image", filters={"Subject": "2-SUB1"})
```

### Download as a BDBag

For production training pipelines and reproducible experiments, download the dataset as a self-contained archive:

```
# MCP — preview size + manifest first
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", version="1.0.0")

# Python API: dataset.download_dataset_bag(dataset_rid="1-ABC4", version="1.0.0")
```

```python
# Python API
bag = dataset.download_dataset_bag(version="1.0.0")

# Within an execution
bag = exe.download_dataset_bag(DatasetSpec(rid="1-ABC4", version="1.0.0"))
```

See [Downloading Datasets as Bags](#downloading-datasets-as-bags) for details.

### Use in Python with the Dataset object

The `Dataset` class provides direct access to dataset operations:

```python
dataset = ml.lookup_dataset("1-ABC4")

# Access metadata
print(dataset.description)
print(dataset.current_version)
print(dataset.dataset_types)

# Work with a specific version
v1 = dataset.set_version("1.0.0")
members = v1.list_dataset_members()

# Download and work with the bag
bag = dataset.download_dataset_bag(version="1.0.0")
images_df = bag.get_table_as_dataframe("Image")
subjects_df = bag.get_table_as_dataframe("Subject")
```

## Downloading Datasets as Bags

Datasets can be downloaded as **BDBag** archives — self-describing, checksummed packages containing all member records, related data, asset files, feature values, and vocabulary terms. The same dataset RID + version always produces the same bag.

### What a bag contains

1. **Member records** — CSV files per table for all records that belong to the dataset
2. **Related records** — data from tables reachable via FK paths from member records
3. **Nested datasets** — child datasets included recursively with all their members
4. **Feature values** — all feature annotations for dataset members
5. **Vocabulary terms** — controlled vocabulary terms referenced by included records
6. **Asset files** — binary files (images, model weights) when `materialize=True`
7. **Checksums** — cryptographic checksums for integrity verification

### Working with downloaded bags

```python
bag = dataset.download_dataset_bag(version="1.0.0", materialize=True)

# Access tables as DataFrames
images_df = bag.get_table_as_dataframe("Image")
subjects_df = bag.get_table_as_dataframe("Subject")

# Access the local filesystem path
print(f"Bag path: {bag.path}")
```

### Restructuring assets for ML frameworks

After downloading, organize files into the directory structure expected by ML frameworks (e.g., PyTorch ImageFolder):

```python
bag.restructure_assets(
    asset_table="Image",
    output_dir=Path("./ml_data"),
    targets=["Diagnosis"],
)
```

Creates:
```
ml_data/
  Training/
    Normal/image1.jpg
    Abnormal/image2.jpg
  Testing/
    Normal/image3.jpg
```

By default, symlinks are used to save disk space. Set `use_symlinks=False` to copy files.

### Previewing before download

```
# MCP — `deriva_ml_bag_info` returns the size estimate plus the manifest
deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", version="1.0.0")
```

Returns row counts and asset sizes per table. Use this to verify expected tables, estimate disk space, and decide whether to adjust timeout or use `exclude_tables`.

For full details on FK traversal, materialization, caching, timeout handling, and Hydra-zen configuration options, see `bags.md`.

For diagnosing missing data in bag exports, see the `debug-bag-contents` skill.

## Deleting Datasets

Datasets can be soft-deleted (marked as deleted but data preserved in the catalog):

```
# MCP — delete a single dataset
deriva_ml_delete_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4")

# Delete dataset and all nested children
deriva_ml_delete_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="1-ABC4", recurse=true)
```

```python
# Python API
ml.delete_dataset(dataset)
ml.delete_dataset(dataset, recurse=True)
```

Deletion removes the dataset container and member associations, not the member records themselves. The underlying Image, Subject, etc. records remain in the catalog.

## Operations Summary

### Creation and modification

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Create dataset | `deriva_ml_create_dataset` | `exe.create_dataset()` | Within an execution for provenance |
| Add types | `deriva_ml_update_dataset(dataset_rid, dataset_types=[...])` | `dataset.add_dataset_type()` | Additive labels |
| Remove types | `deriva_ml_update_dataset(dataset_rid, dataset_types=[...])` | `dataset.remove_dataset_type()` | Set-style: pass the reduced list |
| Create custom type | `add_term(schema="deriva-ml", table="Dataset_Type", ...)` | `ml.add_term(MLVocab.dataset_type, ...)` | Generic add_term |
| Register element type | `deriva_ml_add_dataset_element_type` | `ml.add_dataset_element_type()` | Catalog-level, idempotent |
| Add members | `deriva_ml_add_dataset_members` | `dataset.add_dataset_members()` | Auto-increments version |
| Remove members | `deriva_ml_delete_dataset_members` | `dataset.delete_dataset_members()` | |
| Split | *(script only)* | `split_dataset(ml, source_rid, exe, ...)` | Run from a script that opens an execution. Children auto-tagged with `Split_Partition` + role; source recorded as execution input, not Dataset_Dataset parent |
| Subsample | *(script only)* | `subsample(ml, source_rid, exe, size=, ...)` | Single output; stratified by `stratify_by_column`. Output auto-tagged `Subsample`; source recorded as execution input |
| Nest datasets | `deriva_ml_add_dataset_members(parent, members={"Dataset": [child_rid]})` | `parent.add_dataset_members()` | Children are members of element-type Dataset |
| Release a dev period | `deriva_ml_release` | `dataset.release(bump, description)` | Promotes dev → released; errors if no dev row |
| Update description | `deriva_ml_update_dataset(rid, description=...)` | — | Single setter for any updatable field |
| Delete | `deriva_ml_delete_dataset` | `ml.delete_dataset()` | Soft delete, optional recurse |

### Navigation and discovery

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Find datasets | `rag_search("...", doc_type="catalog-data")` or `deriva_ml_list_datasets` | `ml.find_datasets()` | RAG for discovery; typed list for full surface |
| Lookup by RID | `deriva_ml_get_dataset(rid)` | `ml.lookup_dataset(rid)` | Get specific dataset |
| List members | `deriva_ml_list_dataset_members` | `dataset.list_dataset_members()` | Grouped by table; supports `version`, `recurse`, `limit` |
| List relations (parents + children) | `deriva_ml_list_dataset_relations` | `dataset.list_dataset_relations()` | Both directions in one call; supports `recurse`, `version` |
| Check element types | `deriva_ml_list_dataset_element_types` | `ml.list_dataset_element_types()` | Per-dataset or catalog-wide |
| List executions | `deriva_ml_get_dataset` (includes provenance) | — | Provenance: which runs used this dataset |
| Validate RIDs | `get_entities(filters={"RID": "..."})` per candidate table; check for empty result | — | Use generic entity fetch |
| Bag info / size estimate | `deriva_ml_bag_info` | `dataset.estimate_bag_size()` | Preview before download |
| Get version spec | `deriva_ml_get_dataset_spec` | — | Generate `DatasetSpecConfig` string |
| Cite | `cite` | `ml.cite(rid)` | Permanent shareable URL |

### Download and export

| Operation | MCP Tool | Python API | Notes |
|-----------|----------|------------|-------|
| Download bag | Python API `dataset.download_dataset_bag(version)` | `dataset.download_dataset_bag()` | Standalone download |
| Download in execution | Python API `exe.download_dataset_bag()` | `exe.download_dataset_bag()` | Records provenance |
| Restructure assets | Python API `bag.restructure_assets()` | `bag.restructure_assets()` | ML-ready directory layout |
| Validate bag | Python API bag inspection | — | Cross-check bag vs catalog |
| Schema shape + size | `deriva_ml_denormalize_dataset(include_tables=[...])` | `ml.denormalize_info()` / `dataset.denormalize_info()` | No dataset needed for schema-only |
| Denormalize with data | `deriva_ml_denormalize_dataset(..., dataset_rid=..., limit=N)` | `dataset.denormalize_as_dataframe()` | Flat DataFrame for analysis |
