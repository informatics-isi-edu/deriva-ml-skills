# Dataset Type Naming Strategy

Guidelines for designing, naming, and maintaining dataset types in the `Dataset_Type` vocabulary. Types are the primary mechanism for organizing and discovering datasets — getting them right makes catalogs self-describing and queries intuitive.

## Table of Contents

- [The Core Principle: Orthogonal Tagging](#the-core-principle-orthogonal-tagging)
- [Identifying Dimensions](#identifying-dimensions)
- [The Built-in Dimensions](#the-built-in-dimensions)
- [When to Create Custom Types](#when-to-create-custom-types)
- [Naming Conventions](#naming-conventions)
- [Composing Types on a Dataset](#composing-types-on-a-dataset)
- [Anti-Patterns](#anti-patterns)
- [The Substitution Test](#the-substitution-test)
- [Semantic Checking](#semantic-checking)
- [Examples](#examples)

---

## The Core Principle: Orthogonal Tagging

Dataset types describe independent dimensions of a dataset. Each type answers a different question about the dataset. A dataset gets one or more tags from each relevant dimension, and those tags compose freely because they are not alternatives to each other.

This approach comes from faceted classification in information science — the same idea behind Kubernetes labels, library faceted search, and biomedical ontology post-coordination. The alternative — a flat list where "TrainingLabeled" is a single tag — leads to combinatorial explosion and brittle queries.

**The rule:** If two types can both apply to the same dataset and you wouldn't swap one for the other, they belong on different dimensions.

## Identifying Dimensions

A dimension is a single axis of description. All types within a dimension are mutually exclusive (or nearly so) — you'd pick one, not stack several from the same dimension.

To identify dimensions in your type vocabulary:

1. **Group types that compete.** `Training`, `Testing`, `Validation` compete for the same slot — a dataset's partition role. That's one dimension.
2. **Look for types that combine freely.** `Labeled` combines with `Training` or `Testing` without conflict. It's on a different dimension — annotation status.
3. **Watch for types that always co-occur.** If you always apply `Labeled` alongside `Training`, ask whether `Labeled` carries independent information. It does — an unlabeled training set is a valid concept (e.g., for self-supervised learning).
4. **Count the combinations.** If you have 3 partition roles and 2 annotation states, you should have 5 types across 2 dimensions, not 6 compound types in 1 dimension.

## The Built-in Dimensions

DerivaML ships with types that cover two dimensions:

### Dimension: Partition Role

What role does this dataset play in the ML workflow?

| Type | Meaning |
|------|---------|
| Training | Data for model training |
| Testing | Data for model evaluation |
| Validation | Data for hyperparameter tuning |
| Complete | Full dataset before any splitting |
| Split | Parent container that holds split children |

These are largely mutually exclusive — a dataset is typically one of these. (`Complete` and `Split` are structural roles, while `Training`/`Testing`/`Validation` are partition roles within a split.)

### Dimension: Annotation Status

Does this dataset have ground truth labels?

| Type | Meaning |
|------|---------|
| Labeled | Records have ground truth feature annotations |
| Unlabeled | Records lack feature annotations |

This is independent of partition role. A training set can be labeled (supervised learning) or unlabeled (self-supervised learning).

## When to Create Custom Types

The built-in types cover partition role and annotation status. Projects often need additional dimensions. Good candidates for custom types:

**Content or modality** — what kind of data is in the dataset?
- `Fundus`, `OCT`, `CT`, `MRI` (imaging modality)
- `Genomic`, `Clinical`, `Imaging` (data domain)

**Source or provenance** — where did the data come from?
- `Cohort_A`, `Cohort_B` (study cohort)
- `Synthetic`, `Real_World` (data origin)
- `External`, `Internal` (organizational boundary)

**Purpose or stage** — what is the dataset for?
- `Pilot`, `Production` (maturity stage)
- `Augmented`, `Preprocessed` (processing state)
- `Benchmark` (reference standard)

**Quality or curation level**
- `Curated`, `Raw` (curation status)
- `Expert_Reviewed`, `Auto_Generated` (annotation source)

Before creating a custom type, check whether the information belongs as a type at all versus a dataset description or a column on a related table. Types are best for dimensions you'll filter and query by. If you'll never search "show me all Augmented datasets," it might belong in the description instead.

## Naming Conventions

### Term names

- **Use PascalCase**: `Training`, `Expert_Reviewed`, `Cohort_A`
- **Use singular form**: `Training` not `TrainingData` or `TrainingSet`
- **Don't embed the dimension**: `Training` not `RoleTraining` or `Partition_Training`. The dimension is implicit from context.
- **Don't compound dimensions**: `Training` + `Labeled` as two separate types, never `TrainingLabeled` as one type
- **Keep terms short**: they appear in UI columns, filter chips, and code. 1-2 words is ideal
- **Be specific enough to distinguish**: `Fundus` is better than `Image` (too generic, could mean anything)

### Term descriptions

Every type should have a description that explains:
- What the type means
- When to apply it
- What dimension it belongs to (implicitly or explicitly)

Good: `"Dataset used for model training. Applied automatically by split_dataset. Part of the partition role dimension."`

Bad: `"Training data"` or empty.

### Synonyms

Add common alternative names as synonyms so the type is findable regardless of how someone refers to it:
- `Training` → synonyms: `Train`, `train`, `training`
- `Expert_Reviewed` → synonyms: `Expert`, `expert_reviewed`, `Gold_Standard`

Synonyms are particularly important for types that different team members might name differently.

## Composing Types on a Dataset

A well-typed dataset reads like a description when you list its types:

```
Types: [Complete, Labeled]
→ "This is the complete labeled dataset"

Types: [Training, Labeled, Fundus]
→ "This is a labeled fundus training set"

Types: [Testing, Augmented]
→ "This is an augmented testing set"
```

### Guidelines for composition

1. **Apply at least one type.** A dataset with no types is hard to discover and understand.
2. **Apply types from each relevant dimension.** If the dataset has ground truth labels, add `Labeled`. If it's a training partition, add `Training`. Don't rely on the description to carry information that types should express.
3. **Don't over-tag.** If a type doesn't help distinguish this dataset from others, it's noise. Not every dimension needs to be tagged on every dataset.
4. **Let `split_dataset` handle partition types.** It automatically assigns `Training`, `Testing`, `Validation`, and `Split`. You add additional types via `*_types` parameters (e.g., `training_types=["Labeled"]`).

## Anti-Patterns

### Compound tags

Types like `TrainingLabeled`, `TestingUnlabeled`, or `LabeledFundusTraining` encode multiple dimensions in one value. This causes:
- **Combinatorial explosion**: N × M types instead of N + M
- **Brittle queries**: finding "all labeled datasets" requires enumerating every compound containing "Labeled"
- **Vocabulary bloat**: adding a third dimension multiplies the problem

**Fix:** Split into independent types. `TrainingLabeled` → `Training` + `Labeled`.

### Hierarchical encoding

Types like `Training/Labeled/Fundus` or `Training_Labeled` smuggle a hierarchy into a flat vocabulary. This breaks independence and makes the vocabulary brittle when any level changes.

**Fix:** Use multiple types from independent dimensions.

### Overloaded vocabulary

A single `Dataset_Type` vocabulary containing `Training`, `Testing`, `Labeled`, `Fundus`, `Complete`, `Augmented`, `Pilot`, `Expert_Reviewed` — these span at least five dimensions. This isn't wrong (DerivaML uses a single vocabulary), but it's important to recognize the implicit dimensions and document them so users understand which types are alternatives and which compose.

**Fix:** Document the dimensions in type descriptions. Consider a naming pattern that hints at the dimension (e.g., all modality types could share a prefix convention in their descriptions).

### Tags as status vs. classification

Mixing transient states (`In_Review`, `Needs_QC`) with permanent classifications (`Training`, `Fundus`) in the same vocabulary. States change over a dataset's lifecycle; classifications describe intrinsic properties.

**Fix:** Use types for stable classifications. Track transient states in other mechanisms (execution status, description, or a separate column).

### Vocabulary creep

Adding terms for every edge case rather than recognizing a new dimension is needed. If your terms aren't mutually exclusive with existing ones and keep growing, step back and identify the underlying dimension.

## The Substitution Test

A quick test for whether two types belong on the same dimension:

**Can you swap one for the other?**
- `Training` ↔ `Testing` — yes, same dimension (partition role)
- `Labeled` ↔ `Unlabeled` — yes, same dimension (annotation status)
- `Training` ↔ `Labeled` — no, different dimensions

**Would applying both be contradictory?**
- `Training` + `Testing` on the same dataset — contradictory (same dimension, mutually exclusive)
- `Training` + `Labeled` — not contradictory (different dimensions, compose freely)

If two types pass the substitution test (swappable), they're on the same dimension and a dataset should have at most one of them. If they fail (not swappable), they're on different dimensions and can co-occur.

## Semantic Checking

Before creating a new type, the `semantic-awareness` skill automatically searches for existing types that may match — including synonyms, misspellings, abbreviations, and name variants. This prevents duplicates like:

- `Training` vs `TrainingSet` vs `Train` — same concept, different names
- `Expert_Reviewed` vs `ExpertReviewed` vs `Gold_Standard` — same concept, different conventions
- `Xray` vs `X-ray` vs `X_Ray` — same concept, different formatting

If a near-match is found, the right action is usually to add a synonym to the existing type rather than create a new one. For example, if `Training` already exists and someone asks for `TrainingSet`, add `TrainingSet` as a synonym of `Training`.

When creating a genuinely new type, check the existing vocabulary first to understand:
- Which dimensions are already represented
- What naming conventions are established (PascalCase? underscores?)
- Whether the new type fills a gap in an existing dimension or introduces a new one

```
# Search for types by meaning (preferred for discovery)
rag_search("dataset types", doc_type="catalog-schema")

# Full structured list (when you need complete output)
Read resource: deriva://catalog/dataset-types
```

## Examples

### Good: Ophthalmology imaging catalog

**Dimensions and types:**

| Dimension | Types | Rationale |
|-----------|-------|-----------|
| Partition role | `Training`, `Testing`, `Validation`, `Complete`, `Split` | Built-in, mutually exclusive |
| Annotation status | `Labeled`, `Unlabeled` | Built-in, independent of role |
| Imaging modality | `Fundus`, `OCT`, `External_Photo` | Domain-specific, mutually exclusive |
| Curation level | `Expert_Reviewed`, `Auto_Generated` | How annotations were produced |

**Well-typed datasets:**

| Dataset | Types | Reading |
|---------|-------|---------|
| All labeled fundus images | `Complete`, `Labeled`, `Fundus` | Complete labeled fundus collection |
| Training split with expert labels | `Training`, `Labeled`, `Fundus`, `Expert_Reviewed` | Expert-reviewed labeled fundus training set |
| Unlabeled OCT for prediction | `Testing`, `Unlabeled`, `OCT` | Unlabeled OCT testing set |
| Quick dev subset | `Training`, `Labeled`, `Fundus` | Same dimensions as full training, just fewer members |

### Bad: The same catalog with compound tags

| Type | Problem |
|------|---------|
| `TrainingLabeledFundus` | Three dimensions in one tag |
| `TestingOCT` | Two dimensions in one tag |
| `FundusExpertTraining` | Three dimensions, unclear ordering |
| `UnlabeledPrediction` | Mixes annotation status with workflow stage |

This vocabulary would need 2 × 3 × 2 = 12 compound terms to cover the same space that 9 independent terms cover. Adding a fourth dimension (e.g., 3 cohort sources) would require 36 compound terms vs 12 independent ones.
