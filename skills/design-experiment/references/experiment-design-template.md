# Experiment Design Template

Copy this into `experiment-design/<slug>.md` and fill every section. Each
section maps to a question the experiment must answer *before* it runs. A
section you can't fill is a design gap — close it now.

---

## Template (copy below this line)

```markdown
# Experiment Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Built | Validated -->
**Date:** <YYYY-MM-DD>

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

The design docs this experiment builds on: the `model-design` of the model it
runs and the `dataset-design` of the dataset it consumes. Naming them makes the
dependency traceable at the spec layer.

## Status & links

- **Config:** the experiment name + `configs/experiments.py` entry that
  implements this design.
- **Executions:** RID(s) produced by the run(s).
- **tacit-knowledge.md:** link to the journal entries this run generated.
```

---

## Worked example

```markdown
# Experiment Design: dropout vs unregularized baseline

**Slug:** dropout-vs-baseline
**Status:** Approved
**Date:** 2026-06-22

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
- Model design: `cifar10-2layer-cnn` (the model this experiment runs).
- Dataset design: `cifar10-dev-subset` (the dataset it consumes).

## Status & links
- **Config:** `dropout_quick` in `configs/experiments.py`
- **Executions:** (filled after the run)
- **tacit-knowledge.md:** (filled after the run)
```
