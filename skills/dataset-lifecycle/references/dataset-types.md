---
type: Concept
title: Dataset types and element types
description: What a dataset is, Dataset_Type vocabulary (three axes — role, content, origin), and element-type registration.
---

# Dataset types and element types

**Contents**

- [What is a Dataset?](#what-is-a-dataset)
- [Dataset Types](#dataset-types)
  - [The three axes of `Dataset_Type`](#the-three-axes-of-dataset_type)
  - [Built-in terms by axis](#built-in-terms-by-axis)
  - [Why the role/origin distinction matters in practice](#why-the-roleorigin-distinction-matters-in-practice)
  - [Types are orthogonal tags](#types-are-orthogonal-tags)
  - [Creating custom types](#creating-custom-types)
  - [When to add a custom type](#when-to-add-a-custom-type)
  - [How `split_dataset` assigns types](#how-split_dataset-assigns-types)
  - [How `subsample` assigns types](#how-subsample-assigns-types)
  - [Composing types](#composing-types)
  - [`Dataset_Type` is the primary signal of what a dataset is for](#dataset_type-is-the-primary-signal-of-what-a-dataset-is-for)
  - [Examples](#examples)
- [Dataset Element Types](#dataset-element-types)
  - [Why element types matter for planning](#why-element-types-matter-for-planning)
  - [Registering element types](#registering-element-types)
  - [Element types and bag exports](#element-types-and-bag-exports)

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

The origin tags deliberately duplicate a fact the execution graph also records: they are a fast signal for filters and discovery, not the truth. The truth is `producing_execution.list_input_datasets()`.

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

> **Need a brand-new vocabulary table?** `add_term` extends an existing vocabulary table; to create a new one (a domain-specific vocabulary like `Tumor_Grade`), use `deriva_ml_create_vocabulary(...)`. See `deriva-ml-context/references/built-in-vocabularies.md` ("Creating a new vocabulary") for the rationale (curie prefix, default schema, navbar refresh) and the canonical call shape.

For the generic vocabulary design rules this builds on (naming, orthogonal tagging, the substitution test, anti-patterns), see `/deriva:entity-naming` † and `/deriva:manage-vocabulary` † *(deriva-skills)*; they apply to every DerivaML vocabulary and to domain vocabularies.

### When to add a custom type

The built-in axes cover role, content (labeled or not), and origin. Real catalogs almost always need additional dimensions. Common categories that emerge in practice:

- **Content or modality** — what kind of data is in the dataset? (`Fundus`, `OCT`, `CT`, `MRI` for imaging modality; `Genomic`, `Clinical`, `Imaging` for data domain)
- **Source or provenance** — where did the data come from? (`Cohort_A`, `Cohort_B`; `Synthetic`, `Real_World`; `External`, `Internal`)
- **Purpose or stage** — what's the dataset for? (`Pilot`, `Production`; `Augmented`, `Preprocessed`; `Benchmark`)
- **Quality or curation level** — `Curated`, `Raw`; `Expert_Reviewed`, `Auto_Generated`

Before adding a custom type to `Dataset_Type`, two checks:

1. **Does this dimension belong here, or in its own vocabulary?** DerivaML keeps everything in `Dataset_Type` for simplicity, but the same anti-pattern that punishes overloaded vocabularies applies — when a dimension is large or distinctive, splitting it out as e.g. a separate `Image_Modality` vocabulary that records reference via FK is often cleaner than piling more terms into `Dataset_Type`. `/deriva:manage-vocabulary` † *(deriva-skills)* covers the trade-off ("Orthogonal vocabularies" section in its SKILL.md).
2. **Run the substitution test** against existing terms. The deriva-skills reference covers the test in detail. Specifically for `Dataset_Type`: anything that swaps cleanly with `Training`, `Testing`, `Validation`, `Labeled`, `Unlabeled`, etc. is a near-duplicate and should probably be a synonym, not a new term.

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

### Composing types

#### A well-typed dataset reads like a description

When you list a dataset's types in declaration order, you should get a coherent near-sentence:

```
Types: [Complete, Labeled]            → "the complete labeled dataset"
Types: [Training, Labeled, Fundus]    → "a labeled fundus training set"
Types: [Testing, Augmented]           → "an augmented testing set"
```

If the type list doesn't read as coherent, that's a signal something is wrong — either the dataset is under-tagged (a relevant dimension is missing) or one of the types is encoding a hierarchy (the `TrainingLabeled` anti-pattern surfacing as a single tag that *sounds* coherent but should have been two independent tags).

### `Dataset_Type` is the primary signal of what a dataset is for

Type definition and type consumption are symmetric. The types you assign in this phase are the catalog's **primary, structured record of what a dataset is for** — and any consumer asking "what should I use this dataset for?" should look at `Dataset_Type` first. A person browsing the catalog, a CLI picking the right bag for an experiment, a notebook deciding which dataset to load, a training-loop dispatching across multiple inputs — all of them are answering the same question, and the catalog's typing mechanism is what they should be answering it from.

The dataset **description** is a legitimate secondary signal — it's the human-readable prose that explains the *why* and the nuance that controlled vocabularies can't encode. A reader can consult the description for context the types don't carry (composition details, curation history, sampling rationale). But description is **advisory**, not authoritative: it's free-text that can drift, that no consumer can reliably dispatch on, and that exists to supplement the typed dimensions, not to replace them. **Prefer modeling purpose with one or more `Dataset_Type` terms.** If a distinction matters enough that code or a person will route on it, it belongs in the vocabulary; if it's only ever read by humans for context, the description is the right home.

The anti-patterns this principle exists to rule out — each is a workaround that the typed vocabulary already covers properly:

- **Dispatching on dataset name.** `if dataset.name.startswith("train"): ...`, or `if "validation" in dataset.name: ...`. Names are human-readable handles, not contracts. Renaming a dataset breaks the consumer; using a non-conforming name silently bypasses it. The catalog's vocabulary exists precisely so name strings don't have to be load-bearing.
- **Dispatching on a private translation table.** A hand-maintained dict that maps catalog terms into a consumer-local vocabulary (`{"Training": "train_lane", "Testing": "test_lane"}`). The dict ossifies: when someone `add_term`s a new `Dataset_Type` value (e.g., `Validation`, `Calibration`), the consumer silently treats it as unknown and either errors confusingly or — worse — drops the dataset and produces a result that looks fine. The catalog's vocabulary is the only translation table that should exist; add new types by extending it, and the consumer registers handlers against catalog terms directly.
- **Dispatching on out-of-band metadata.** File path conventions, sidecar JSON, RID-prefix heuristics, position in an input list ("the first bag is training"), the contents of an unrelated config file. These signal that the catalog wasn't trusted to carry the answer; the convention will diverge and a future reader won't know which side is authoritative.
- **Parsing the description for routing keywords.** Description is human prose — phrasing varies (`"holdout set"`, `"held-out for evaluation"`, `"never seen during training"` all mean the same thing) — and substring or regex matches on it are as brittle as name matching. If purpose needs to drive a decision, lift it into the vocabulary; leave the description for the nuance the types can't capture.

If the type is missing or wrong on a dataset you're trying to consume, the right move is **not** to add a workaround in the consumer — it's to fix the catalog. `deriva_ml_update_dataset(dataset_types=[...])` is cheap; the next reader inherits a correct answer instead of having to reinvent your workaround.

Two implementation conventions that follow from this principle:

- **Separate role terms from qualifiers.** `Training`/`Testing`/`Validation` are partition roles; `Complete` and `Split` are structural roles; `Labeled` and the domain tags are content (see "A well-typed dataset reads like a description" above). A consumer deciding what to *do* with a dataset is dispatching on the role term; the qualifiers describe properties of the dataset but don't change the decision.
- **Unknown types should fail loudly, not silently drop.** When a consumer encounters a `Dataset_Type` it has no handler for, the right behavior is a clear error or warning that names the unrecognized type — never a silent skip. A consumer that filters out unknown types without saying so will produce results that look correct but are missing data, and the failure mode is invisible until someone goes looking.

### Examples

#### Good: an ophthalmology imaging catalog

**Vocabulary structure:** `Dataset_Type` extended with two domain dimensions on top of the built-in axes.

| Dimension | Types | Rationale |
|-----------|-------|-----------|
| Partition role (built-in) | `Training`, `Testing`, `Validation`, `Complete`, `Split` | Mutually exclusive role of the dataset in an ML workflow |
| Annotation status (built-in) | `Labeled`, `Unlabeled` | Independent of partition role |
| Imaging modality | `Fundus`, `OCT`, `External_Photo` | Domain-specific, mutually exclusive |
| Curation level | `Expert_Reviewed`, `Auto_Generated` | How annotations were produced |

**Well-typed datasets in this catalog:**

| Dataset | Types | Reading |
|---------|-------|---------|
| All labeled fundus images | `Complete`, `Labeled`, `Fundus` | "The complete labeled fundus collection" |
| Training split with expert labels | `Training`, `Labeled`, `Fundus`, `Expert_Reviewed` | "An expert-reviewed labeled fundus training set" |
| Unlabeled OCT for prediction | `Testing`, `Unlabeled`, `OCT` | "An unlabeled OCT testing set" |
| Quick dev subset | `Training`, `Labeled`, `Fundus` | "Same dimensions as the full training set, just fewer members" |

Each dataset reads coherently because each tag describes a different dimension. Filtering composes naturally — "show me all labeled fundus datasets" is a query across two independent tags, not enumeration of compound terms.

#### Bad: the same catalog with compound tags

If the catalog had encoded all dimensions as compound terms in `Dataset_Type`:

| Type | Problem |
|------|---------|
| `TrainingLabeledFundus` | Three dimensions in one tag |
| `TestingOCT` | Two dimensions in one tag |
| `FundusExpertTraining` | Three dimensions, unclear ordering |
| `UnlabeledPrediction` | Mixes annotation status with workflow stage |

This vocabulary needs 2 × 3 × 2 = 12 compound terms to cover the same space that 9 independent terms cover. Adding a fourth dimension (e.g., 3 cohort sources) requires 36 compound terms vs 12 independent ones — combinatorial explosion. Filtering "all labeled datasets" requires enumerating every compound containing `Labeled`. This is the compound-tag anti-pattern from the deriva-skills reference, in concrete form.

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
deriva_ml_add_dataset_element_type(hostname="data.example.org", catalog_id="1", table_name="Image")
```

```python
# Python API
ml.add_dataset_element_type("Image")
```

**Key points:**
- Registration is idempotent — calling it again for an already-registered table is harmless
- Common tables to register: `Subject`, `Image` (or other asset tables), `Observation`, and any custom domain tables whose records should be dataset members
- Element types also determine the starting points for FK traversal during bag export (see `bags.md`)

### Element types and bag exports

During bag export, only tables registered as element types that have members in the dataset serve as starting points for FK traversal. Unregistered tables are traversed normally if reached via FK paths, but cannot contribute starting points. This means:

- A table must be an element type *and* have members for its records to be traversal roots
- A registered element type with *no members* in a dataset acts as a traversal boundary — the export won't follow FK paths through it
- This prevents expensive joins that would return empty results

See `bags.md` for the full FK traversal algorithm.
