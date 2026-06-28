---
type: Concept
title: Dataset types and element types
description: What a dataset is, Dataset_Type vocabulary (three axes — role, content, origin), and element-type registration.
---

# Dataset types and element types

Background on datasets in DerivaML. For the step-by-step guide to creating and managing datasets, see `workflow.md`.

> **Stateless model:** the new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

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
- Element types also determine the starting points for FK traversal during bag export (see [Downloading Datasets as Bags](navigation.md#downloading-datasets-as-bags))

### Element types and bag exports

During bag export, only tables registered as element types that have members in the dataset serve as starting points for FK traversal. Unregistered tables are traversed normally if reached via FK paths, but cannot contribute starting points. This means:

- A table must be an element type *and* have members for its records to be traversal roots
- A registered element type with *no members* in a dataset acts as a traversal boundary — the export won't follow FK paths through it
- This prevents expensive joins that would return empty results

See `bags.md` for the full FK traversal algorithm.
