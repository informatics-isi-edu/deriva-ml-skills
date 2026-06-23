# Dataset Design Template

Copy this into `dataset-design/<slug>.md` and fill every section. Parallel in
shape to the experiment-design template — same skeleton, dataset-specific
prompts. A section you can't fill is a design gap; close it before building.

---

## Template (copy below this line)

```markdown
# Dataset Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Built | Released -->
**Date:** <YYYY-MM-DD>

## Purpose

What this dataset is *for*, in one sentence. The downstream use that
justifies building it.

## Requirements

- **Source data:** which catalog table(s) / existing dataset(s) members come
  from.
- **Target size & composition:** how many members, class balance, any
  inclusion/exclusion filters.
- **Element types:** which tables contribute members
  (`deriva_ml_list_dataset_element_types`); register missing ones first.
- **Balance constraints:** per-class minimums, stratification column, etc.

## Structure plan

- **Pattern:** standalone / split (train/test/val) / subsample / curated
  subset / manual nesting.
- **Dataset_Type tags (three axes):** Role (Training/Testing/…), Content
  (Labeled/…/domain tags), Origin (Split/Split_Partition/Subsample — set by
  the producing operation). List the tags you intend each output to carry.

## Validation

How you'll verify the dataset is correct *before* relying on it:
- class balance check (counts per class within tolerance),
- no train/test leakage (member RIDs disjoint across partitions),
- bag parity (downloaded bag RIDs == catalog member RIDs),
- expected total member count.

## Consumption

Who uses this downstream: which experiments/configs reference it, and the
version-pinning expectation (always a released label, never dev/"current" in
`configs/datasets.py`).

## Upstream designs

A dataset does not depend on a feature, so it names no upstream design. Where a
split reads a feature its *elements* carry, note that element feature here as a
precondition on the members — a reference to a data property, not a build
dependency.

## Status & links

- **RID + version:** the produced dataset RID and released version.
- **configs/datasets.py:** the `DatasetSpecConfig` entry that pins it.
- **tacit-knowledge.md:** link to journal entries from the build.
```

---

## Worked example

```markdown
# Dataset Design: CIFAR-10 dev subset

**Slug:** cifar10-dev-subset
**Status:** Approved
**Date:** 2026-06-22

## Purpose
A small, class-balanced CIFAR-10 subset for rapid pipeline validation and
small-data runs, so full-scale compute isn't spent debugging plumbing.

## Requirements
- **Source data:** `cifar10_complete` @ `1.0.0` (Image members).
- **Target size & composition:** 500 images, 50 per class, all 10 classes.
- **Element types:** `Image` (already registered).
- **Balance constraints:** exactly 50 per `Diagnosis`/class label; stratify on
  the class column.

## Structure plan
- **Pattern:** subsample (single stratified output, no partitioning).
- **Dataset_Type tags:** Role `Complete`, Content `Labeled` + `CIFAR_10`,
  Origin `Subsample` (auto-applied by `subsample`).

## Validation
- Counts: 50 ± 0 per class, 500 total.
- Leakage: N/A (single output, not a split).
- Bag parity: downloaded bag Image RIDs == `list_dataset_members` Image RIDs.

## Consumption
- Used by the `*_quick` / small-data experiments in `configs/experiments.py`.
- Pinned in `configs/datasets.py` as a released version (e.g. `0.1.0`), never
  a dev label.

## Upstream designs
None — a dataset doesn't depend on a feature. The subsample stratifies on the
class label its Image elements already carry (an element-feature precondition,
not a build dependency).

## Status & links
- **RID + version:** (filled after the build)
- **configs/datasets.py:** (filled after the build)
- **tacit-knowledge.md:** (filled after the build)
```
