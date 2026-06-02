# Dataset Type Naming Strategy

DerivaML-specific guidance for working with the `Dataset_Type` vocabulary — the built-in dimensions it ships with, how to compose multiple types on a single dataset, and worked examples for an imaging-domain catalog.

The **generic vocabulary design principles** that this guidance builds on are documented in the `deriva-skills` plugin and split across two locations:

- **`entity-naming` skill** — naming conventions for any data-modeling entity (PascalCase with underscores, singular form, descriptive, short, specific, FK column conventions, character restrictions). Applies to schemas, tables, columns, vocabulary tables, and vocabulary terms uniformly. Read this first.
- **`manage-vocabulary/references/term-naming-strategy.md`** — vocabulary-term-specific design concerns that build on `entity-naming`: orthogonal tagging principle, identifying dimensions, term descriptions, synonyms, anti-patterns (compound tags, hierarchical encoding, etc.), the substitution test, semantic checking before creating new terms.

Both apply to *any* DerivaML vocabulary (`Dataset_Type`, `Workflow_Type`, `Asset_Type`, `Execution_Status_Type`) — those naming and design rules are not DerivaML-specific.

This file covers what the deriva-skills reference can't: the specific terms `Dataset_Type` ships with, what they mean for ML workflows, how multiple types compose on a single Dataset row, and what a well-typed dataset catalog looks like in practice.

## Table of Contents

- [The Built-in Dimensions](#the-built-in-dimensions)
- [When to Add Custom Types to Dataset_Type](#when-to-add-custom-types-to-dataset_type)
- [Composing Types on a Dataset](#composing-types-on-a-dataset)
- [Examples](#examples)

---

## The Built-in Dimensions

DerivaML ships `Dataset_Type` pre-populated with terms covering **three orthogonal axes** — role, content, and origin. The canonical framing lives in `concepts.md` § "The three axes of `Dataset_Type`"; this file expands on what the axes mean for ML workflows in practice.

### Axis: Role (what is this dataset *for* in its immediate context?)

| Type | Meaning |
|------|---------|
| `Training` | Data for model training |
| `Testing` | Data for model evaluation |
| `Validation` | Data for hyperparameter tuning |
| `Complete` | Full dataset before any splitting |
| `Split` | Parent container that holds split children |

`Training`/`Testing`/`Validation` are mutually exclusive within a record — a dataset is one of these, not several. `Complete` and `Split` describe structural roles distinct from partitions: `Complete` means "the full dataset before splitting"; `Split` means "the parent container that holds split children." A dataset that is `Complete` is usually neither `Training` nor `Testing` — it predates the partition.

**Role tags do not inherit from a parent and do not propagate to children.** A source dataset tagged `Testing` (because it is a testing corpus) produces a Training partition tagged `Training` — `split_dataset` assigns the partition's role from its position in the split, not from the source's role. Role is a property of the dataset's *immediate context*, not something the operation preserves.

### Axis: Content (what *kind of data* does it contain?)

| Type | Meaning |
|------|---------|
| `Labeled` | Records have ground truth feature annotations |
| `Unlabeled` | Records lack feature annotations |

This axis is genuinely independent of role. A training set can be labeled (supervised learning) or unlabeled (self-supervised learning). Don't assume `Training` implies `Labeled` — many real workflows need the unlabeled-training combination, and the built-in vocabulary deliberately allows it.

Domain-specific tags also belong on this axis: `Fundus`, `OCT`, `CIFAR_10`, `Eye_Image_Fundus` — anything that describes a property of the data itself rather than what the dataset is for or how it was produced.

**Content tags may propagate** when the partitioning operation preserves them. A stratified sample of a `Labeled` dataset is still `Labeled`; pass `training_types=["Labeled"]` to `split_dataset` (or `dataset_types=["Labeled"]` to `subsample`) to make the propagation explicit.

### Axis: Origin (how did this dataset *come to exist*?)

| Type | Meaning |
|------|---------|
| `Split` | Parent dataset of a split hierarchy. Auto-applied by `split_dataset` to its parent output. Holds the Training/Testing/Validation children as `Dataset_Dataset` members. |
| `Split_Partition` | Auto-applied by `split_dataset` to every Training/Testing/Validation child. The discriminator that distinguishes a **corpus-role** `Training` dataset from a **partition-role** `Training` dataset. Tag hand-built split children with this too if you want them discoverable through the same filters. |
| `Subsample` | Auto-applied by `subsample()` to its single output. Distinguishes a subsampled dataset from a hand-curated dataset of the same role and content. |

**Origin tags are never inherited.** They are always set by the producing operation, never copied from another dataset. The source relationship for split outputs and subsample outputs lives in **execution provenance** (the source is an input of the producing execution), not in `Dataset_Dataset` edges.

### Why three axes matter

Without the origin axis, the queries *"find every training partition"* and *"find every training corpus that isn't a partition"* are indistinguishable — both return everything tagged `Training`. The three axes make these 1-hop filters:

- *partition-role training* — `Training` ∧ `Split_Partition`
- *corpus-role training* — `Training` ∧ ¬`Split_Partition` ∧ ¬`Subsample`
- *subsampled training data* — `Training` ∧ `Subsample`

The vocabulary deliberately denormalizes a fact that's also reachable through the execution graph — the origin tag is a fast, denormalized signal for filters and discovery, not the truth. The truth lives in `producing_execution.list_input_datasets()`.

## When to Add Custom Types to Dataset_Type

The built-in dimensions cover partition role and annotation status. Real catalogs almost always need additional dimensions. Common categories that emerge in practice:

- **Content or modality** — what kind of data is in the dataset? (`Fundus`, `OCT`, `CT`, `MRI` for imaging modality; `Genomic`, `Clinical`, `Imaging` for data domain)
- **Source or provenance** — where did the data come from? (`Cohort_A`, `Cohort_B`; `Synthetic`, `Real_World`; `External`, `Internal`)
- **Purpose or stage** — what's the dataset for? (`Pilot`, `Production`; `Augmented`, `Preprocessed`; `Benchmark`)
- **Quality or curation level** — `Curated`, `Raw`; `Expert_Reviewed`, `Auto_Generated`

Before adding a custom type to `Dataset_Type`, two checks:

1. **Does this dimension belong here, or in its own vocabulary?** DerivaML keeps everything in `Dataset_Type` for simplicity, but the same anti-pattern that punishes overloaded vocabularies applies — when a dimension is large or distinctive, splitting it out as e.g. a separate `Image_Modality` vocabulary that records reference via FK is often cleaner than piling more terms into `Dataset_Type`. The deriva-skills `manage-vocabulary` skill covers the trade-off ("Orthogonal vocabularies" section in its SKILL.md).
2. **Run the substitution test** against existing terms. The deriva-skills reference covers the test in detail. Specifically for `Dataset_Type`: anything that swaps cleanly with `Training`, `Testing`, `Validation`, `Labeled`, `Unlabeled`, etc. is a near-duplicate and should probably be a synonym, not a new term.

## Composing Types on a Dataset

A `Dataset` row carries one or more `Dataset_Type` tags simultaneously, applied via `dataset_types=[...]` on creation or `deriva_ml_update_dataset(dataset_types=[...])` later. The composition rules from the deriva-skills reference apply (apply at least one type, apply types from each relevant dimension, don't over-tag) — this section covers two DerivaML-specific points the generic guidance can't address.

### A well-typed dataset reads like a description

When you list a dataset's types in declaration order, you should get a coherent near-sentence:

```
Types: [Complete, Labeled]            → "the complete labeled dataset"
Types: [Training, Labeled, Fundus]    → "a labeled fundus training set"
Types: [Testing, Augmented]           → "an augmented testing set"
```

If the type list doesn't read as coherent, that's a signal something is wrong — either the dataset is under-tagged (a relevant dimension is missing) or one of the types is encoding a hierarchy (the `TrainingLabeled` anti-pattern surfacing as a single tag that *sounds* coherent but should have been two independent tags).

### Let `split_dataset` and `subsample` handle the role + origin tags automatically

The Python API auto-assigns role-axis and origin-axis tags. Pass *content-axis* additions via the `*_types` / `dataset_types` parameters:

**`split_dataset(ml, source_rid, exe, ...)`** assigns:

- **Parent dataset**: `Split` (origin axis).
- **Each child** (Training / Testing / Validation): the role tag corresponding to its position, plus `Split_Partition` (origin axis).

Pass *content-axis* additions via `training_types=` / `testing_types=` / `validation_types=`:

- `training_types=["Labeled"]` → tag the training child with `Labeled` on top of the auto-assigned `Training` + `Split_Partition`.
- `testing_types=["Unlabeled"]` → tag the testing child with `Unlabeled`.
- `validation_types=["Labeled"]` → tag the validation child with `Labeled`.

Manually adding `Training`, `Split_Partition`, or `Subsample` to a `*_types` list is a no-op (deduplicated defensively). Manually adding `Labeled` (or any content-axis tag) is exactly what these parameters are for.

**`subsample(ml, source_rid, exe, size=, ...)`** assigns:

- The output dataset: `Subsample` (origin axis), always.

Pass role and content-axis additions via `dataset_types=`:

- `dataset_types=["Training", "Labeled"]` → tag the subsample with `Training` + `Labeled` + the auto-applied `Subsample`. Choose the role tag based on what the subsample is *for* in your workflow; it does **not** inherit from the source.

## Examples

### Good: Ophthalmology imaging catalog

**Vocabulary structure:** `Dataset_Type` extended with two domain dimensions on top of the built-in two.

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

### Bad: The same catalog with compound tags

If the catalog had encoded all dimensions as compound terms in `Dataset_Type`:

| Type | Problem |
|------|---------|
| `TrainingLabeledFundus` | Three dimensions in one tag |
| `TestingOCT` | Two dimensions in one tag |
| `FundusExpertTraining` | Three dimensions, unclear ordering |
| `UnlabeledPrediction` | Mixes annotation status with workflow stage |

This vocabulary needs 2 × 3 × 2 = 12 compound terms to cover the same space that 9 independent terms cover. Adding a fourth dimension (e.g., 3 cohort sources) requires 36 compound terms vs 12 independent ones — combinatorial explosion. Filtering "all labeled datasets" requires enumerating every compound containing `Labeled`. This is the compound-tag anti-pattern from the deriva-skills reference, in concrete form.
