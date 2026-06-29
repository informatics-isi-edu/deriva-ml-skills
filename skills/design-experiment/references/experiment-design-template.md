# Experiment Design Template

Copy this into `docs/design/experiment/<slug>.md` and fill every section. Each
section maps to a question the experiment must answer *before* it runs. A
section you can't fill is a design gap — close it now.

---

## Template (copy below this line)

```markdown
---
type: Experiment Design
title: <one-line title>
description: >
  <one-line goal>
tags: [experiment, <approach>, <domain>]
timestamp: <YYYY-MM-DD>
status: Draft   # Draft | Approved | Built | Validated
slug: <kebab-case-slug>
# This document follows the Open Knowledge Format (OKF):
#   https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
# `resource` is intentionally omitted — a design doc is an abstract specification,
#   not a physical resource. Artifact linkage lives in tacit-knowledge.md +
#   the "Status & links" section below.
---

# Experiment Design: <one-line title>

## Goal

The single question this experiment tests, in one sentence.
"Does <X> improve <Y> for <purpose C>?" Be specific enough that the answer
is checkable.

## Hypothesis

The expected outcome and its direction. "Dropout 0.25 reduces overfitting,
raising test accuracy on the small labeled split by ≥3% vs the unregularized
baseline."

## Requirements

- **Data:** which dataset(s) + pinned version(s) the run consumes
  (e.g. `cifar10_labeled_split` @ `2.0.0`).
- **Assets:** pretrained weights / checkpoints by RID, if any.
- **Vocabularies:** any vocabulary terms the config relies on.
- **Compute budget:** rough GPU-hours / wall-clock / max cycles before
  stopping regardless of result.

## Validation

- **Metric:** the exact metric and how it's computed (e.g. top-1 test
  accuracy on the held-out split).
- **Baseline:** what this is compared against (a prior execution RID, a
  fixed threshold).
- **Confirms the hypothesis if:** <criterion>
- **Refutes the hypothesis if:** <criterion>
- **Inconclusive if:** <criterion> — and what you'd change to make a
  follow-up conclusive.

## Analysis plan

How results get evaluated: single-run read of feature values
(`deriva_ml_list_feature_values`), multi-run comparison
(`/deriva-ml:compare-model-runs`), or a sweep
(`deriva_ml_multirun_status`). Name the tool and the feature/metric.

## Upstream designs

Link the design docs this experiment builds on, as **OKF bundle-absolute
Markdown links** (`/entity/slug.md` — from the `docs/design/` bundle root), with
a **relationship verb** in the prose (OKF links are untyped; the verb conveys the
edge):

- **runs** [<model-slug>](/model/<model-slug>.md) — the model this experiment runs.
- **consumes** [<dataset-slug>](/dataset/<dataset-slug>.md) — the dataset it consumes.

**Compound experiment?** If this experiment spans several datasets/models, list
*all* of them (repeat `consumes`/`runs`). If it is composed of sibling
experiments, link each with **composed of** [<exp-slug>](/experiment/<exp-slug>.md)
— only link experiments authored earlier, so the dependency graph stays acyclic.
A link to a not-yet-written design is fine (OKF tolerates broken links —
planned-but-unauthored knowledge).

## Status & links

- **Config:** the experiment name + `configs/experiments.py` entry that
  implements this design.
- **Executions:** RID(s) produced by the run(s).
- **Outcome:** the verdict against the **Validation** criteria above —
  **confirmed** / **refuted** / **inconclusive** — in one line, with a link to
  the producing execution. *Link, don't transcribe:* the metrics themselves live
  on the Execution / feature values (read them via
  `deriva_ml_list_feature_values` / `deriva_ml_get_lineage`), and the reasoning /
  what-we-learned lives in `tacit-knowledge.md`. This line just records *which
  way the question resolved* so the doc is self-contained as question → criteria
  → verdict. (Set `status: Validated` once filled.) Leave blank until the run
  concludes.
- **tacit-knowledge.md:** link to the journal entries this run generated.
```

---

## Examples

```markdown
---
type: Experiment Design
title: dropout vs unregularized baseline
description: >
  Does adding dropout 0.25 to the 2-layer CNN reduce overfitting on the small labeled CIFAR-10 split?
tags: [experiment, dropout-regularization, cifar-10]
timestamp: 2026-06-22
status: Approved   # Draft | Approved | Built | Validated
slug: dropout-vs-baseline
# This document follows the Open Knowledge Format (OKF):
#   https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
# `resource` is intentionally omitted — a design doc is an abstract specification,
#   not a physical resource. Artifact linkage lives in tacit-knowledge.md +
#   the "Status & links" section below.
---

# Experiment Design: dropout vs unregularized baseline

## Goal
Does adding dropout 0.25 to the 2-layer CNN reduce overfitting on the small
labeled CIFAR-10 split?

## Hypothesis
Dropout 0.25 narrows the train/test accuracy gap and raises top-1 test
accuracy by ≥3% vs the current unregularized baseline (execution 6-ABC1).

## Requirements
- **Data:** `cifar10_small_labeled_split` @ `1.0.0`
- **Assets:** none (train from scratch)
- **Vocabularies:** Workflow_Type `Training` (exists)
- **Compute budget:** ≤ 2 GPU-hours; at most 3 cycles.

## Validation
- **Metric:** top-1 accuracy on the test partition, written as the
  `Test_Accuracy` feature.
- **Baseline:** execution `6-ABC1` (unregularized), test accuracy 0.61.
- **Confirms if:** dropout run's test accuracy ≥ 0.64 AND train/test gap
  shrinks.
- **Refutes if:** test accuracy ≤ baseline, or gap unchanged/wider.
- **Inconclusive if:** within ±1% of baseline — rerun on the full split.

## Analysis plan
Single-run read of `Test_Accuracy` via `deriva_ml_list_feature_values`, then
a two-run comparison against `6-ABC1` via `/deriva-ml:compare-model-runs`.

## Upstream designs
- **runs** [cifar10-2layer-cnn](/model/cifar10-2layer-cnn.md) — the model this experiment runs.
- **consumes** [cifar10-dev-subset](/dataset/cifar10-dev-subset.md) — the dataset it consumes.

## Status & links
- **Config:** `dropout_quick` in `configs/experiments.py`
- **Executions:** (filled after the run)
- **Outcome:** (filled after the run — e.g. "Confirmed: dropout 0.25 raised test accuracy +3.4% over baseline, see [execution 8KG](…); details in tk-042")
- **tacit-knowledge.md:** (filled after the run)
```
