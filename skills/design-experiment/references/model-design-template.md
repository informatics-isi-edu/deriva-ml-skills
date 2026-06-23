# Model Design Template

Copy this into `model-design/<slug>.md` and fill every section. Parallel in
shape to the other design templates. The Requirements section is the source the
model-layer configuration (hyperparameters, architecture, the `model_config`
group) is derived from — write it so a config could be scaffolded from it.

---

## Template (copy below this line)

```markdown
# Model Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Built | Validated -->
**Date:** <YYYY-MM-DD>

## Goal

What this model is for, in one sentence — the prediction task it performs and
the decision its outputs inform.

## Requirements

The source the model-layer config is derived from:
- **Architecture:** model family / structure (e.g. 2-layer CNN, ResNet50).
- **Hyperparameters:** the knobs and their intended defaults (learning rate,
  batch size, epochs, regularization) — these become the `model_config` group.
- **Input features:** which features the model trains on (the labels/annotations
  it consumes — name the `feature-design`s). The model's prediction outputs, if
  they become features, name the feature they populate.
- **Input assets:** any pretrained checkpoint / starting weights the model is
  built with (enters via the model-layer config — `configs/assets.py`).

## Validation

How you'll confirm the model meets its Goal (beyond "the code runs"):
- the target metric and the threshold that counts as success,
- the dataset/split it's validated on,
- sanity checks (loss converges, no NaN, predictions in range).

## Upstream designs

- **Feature designs** this model consumes (labels it trains on; features its
  predictions populate).
- Any prior `model-design` it extends (a checkpoint lineage).

## Status & links

- **Model file + config groups:** the authored model fn and its `model_config`.
- **Workflow:** the registered Workflow.
- **tacit-knowledge.md:** link to journal entries from building it.
```

---

## Worked example

```markdown
# Model Design: 2-layer CNN for CIFAR-10

**Slug:** cifar10-2layer-cnn
**Status:** Approved
**Date:** 2026-06-22

## Goal
A small 2-layer CNN that classifies CIFAR-10 images into the 10 classes, as the
baseline architecture for the project's experiments.

## Requirements
- **Architecture:** 2 conv layers (32→64 channels) + 2 FC layers.
- **Hyperparameters:** lr=0.001, batch=128, epochs=50, dropout=0.0 (baseline) —
  the `model_config` group.
- **Input features:** the `class-label` feature on Image (the training target).
- **Input assets:** none (trained from scratch).

## Validation
- Metric: top-1 test accuracy; success ≥ 0.60 on the small labeled split.
- Validated on `cifar10_small_labeled_split` test partition.
- Sanity: loss converges, no NaN, softmax outputs sum to 1.

## Upstream designs
- Feature design: `class-label` (the training target).

## Status & links
- **Model file + config groups:** (filled after authoring)
- **Workflow:** (filled after registration)
- **tacit-knowledge.md:** (filled after build)
```
