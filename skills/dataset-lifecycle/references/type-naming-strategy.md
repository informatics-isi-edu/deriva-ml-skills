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

DerivaML ships `Dataset_Type` pre-populated with terms covering two independent dimensions.

### Dimension: Partition Role

What role does this dataset play in an ML workflow?

| Type | Meaning |
|------|---------|
| `Training` | Data for model training |
| `Testing` | Data for model evaluation |
| `Validation` | Data for hyperparameter tuning |
| `Complete` | Full dataset before any splitting |
| `Split` | Parent container that holds split children |

`Training`/`Testing`/`Validation` are mutually exclusive within a record — a dataset is one of these, not several. `Complete` and `Split` describe structural roles distinct from partitions: `Complete` means "the full dataset before splitting"; `Split` means "the parent container that holds split children." A dataset that is `Complete` is usually neither `Training` nor `Testing` — it predates the partition.

### Dimension: Annotation Status

Does this dataset have ground truth labels?

| Type | Meaning |
|------|---------|
| `Labeled` | Records have ground truth feature annotations |
| `Unlabeled` | Records lack feature annotations |

This dimension is genuinely independent of partition role. A training set can be labeled (supervised learning) or unlabeled (self-supervised learning). Don't assume `Training` implies `Labeled` — many real workflows need the unlabeled-training combination, and the built-in vocabulary deliberately allows it.

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

### Let `deriva_ml_split_dataset` handle partition types automatically

`deriva_ml_split_dataset` assigns `Training`, `Testing`, `Validation`, and `Split` to the children it creates — you don't apply those tags manually. Pass *additional* types via the `*_types` parameters:

- `training_types=["Labeled"]` → tag the training child with `Labeled` on top of the auto-assigned `Training`
- `testing_types=["Unlabeled"]` → tag the testing child with `Unlabeled`
- `validation_types=["Labeled"]` → tag the validation child with `Labeled`

Manually adding `Training` to a split-produced child would create a duplicate. Manually adding `Labeled` is exactly what the `*_types` parameters are for.

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
