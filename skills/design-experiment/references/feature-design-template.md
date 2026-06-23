# Feature Design Template

Copy this into `feature-design/<slug>.md` and fill every section. Parallel in
shape to the experiment/dataset templates — same skeleton, feature-specific
prompts. A section you can't fill is a design gap; close it before creating the
feature.

---

## Template (copy below this line)

```markdown
# Feature Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Built | Validated -->
**Date:** <YYYY-MM-DD>

## Purpose

What this feature captures and *why it's needed*, in one sentence. The decision
this feature's values will inform (a label for training, a confidence score for
filtering, ground truth for evaluation).

## Requirements

- **Target table / element:** which table's records the feature attaches to.
- **Feature type:** scalar value, controlled-vocabulary term, or asset; single
  vs multi-column.
- **Vocabulary:** if term-based, the controlled vocabulary + terms it draws from
  (create the vocabulary first if it doesn't exist).
- **Who/what writes the values:** human annotation, a model's predictions, a
  derived computation — and the provenance (which Execution).

## Validation

How you'll confirm the feature serves its stated Purpose:
- value coverage (every intended record got a value, or the expected subset),
- value sanity (terms are from the vocabulary; scores in range),
- provenance present (each value links to a producing Execution),
- the downstream consumer can actually read it (e.g. a stratified split or a
  training loop finds the values where it expects them).

## Upstream designs

The design docs this feature builds on, if any. This depends on the feature's
**role**, and the distinction keeps the dependency graph acyclic:

- **Input feature** (ground truth / labels a model trains on, or a column a
  split keys on): usually **none** — input features sit near the bottom of the
  tree, and the *model-design* that consumes them names *them* upstream (not the
  other way around). Leave this empty.
- **Output / prediction feature** (the model emits it — predicted label,
  confidence score): name the `model-design` that **produces** it. This feature
  is *downstream* of that model. The model-design records this as an output, NOT
  as one of its own upstream dependencies — so there is no cycle (the model
  points down to its output feature; the output feature points up to its
  producing model; nothing points back).

## Status & links

- **Feature name + target table:** the created feature.
- **Vocabulary:** the controlled vocabulary RID/name, if term-based.
- **tacit-knowledge.md:** link to journal entries from creating/populating it.
```

---

## Worked example

```markdown
# Feature Design: image quality label

**Slug:** image-quality-label
**Status:** Approved
**Date:** 2026-06-22

## Purpose
A per-image quality label (good/blurry/occluded) so low-quality images can be
filtered out of training sets and flagged for re-acquisition.

## Requirements
- **Target table / element:** Image.
- **Feature type:** controlled-vocabulary term, single-column.
- **Vocabulary:** new `Image_Quality` vocabulary, terms: good, blurry, occluded.
- **Who/what writes the values:** human annotation pass, recorded under an
  annotation Execution.

## Validation
- Coverage: every Image in the curated set has a quality label.
- Sanity: all values are one of the three vocabulary terms.
- Provenance: each value links to the annotation Execution.
- Consumer: a stratified split on `Image_Quality` finds the values.

## Upstream designs
None (human-annotated, not model-produced).

## Status & links
- **Feature name + target table:** (filled after creation)
- **Vocabulary:** (filled after creation)
- **tacit-knowledge.md:** (filled after creation)
```
