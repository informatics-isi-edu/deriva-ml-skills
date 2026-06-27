# Model Design Template

Copy this into `docs/design/model/<slug>.md` and fill every section. Parallel in
shape to the other design templates. The Requirements section is the source the
model-layer configuration (hyperparameters, architecture, the `model_config`
group) is derived from — write it so a config could be scaffolded from it.

---

## Template (copy below this line)

```markdown
---
type: Model Design
title: <one-line title>
description: >
  <one-line goal>
tags: [model, <architecture>, <domain>]
timestamp: <YYYY-MM-DD>
status: Draft   # Draft | Approved | Built | Validated
slug: <kebab-case-slug>
# This document follows the Open Knowledge Format (OKF):
#   https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
# `resource` is intentionally omitted — a design doc is an abstract specification,
#   not a physical resource. Artifact linkage lives in tacit-knowledge.md +
#   the "Status & links" section below.
---

# Model Design: <one-line title>

## Goal

What this model is for, in one sentence — the prediction task it performs and
the decision its outputs inform.

## Requirements

The source the model-layer config is derived from:
- **Architecture:** model family / structure (e.g. 2-layer CNN, ResNet50).
- **Hyperparameters:** the knobs and their intended defaults (learning rate,
  batch size, epochs, regularization) — these become the `model_config` group.
- **Input features:** which features the model trains on (the labels/annotations
  it *consumes*) — name the `feature-design`s. These are upstream dependencies
  (see Upstream designs).
- **Output features:** the features the model *produces* (predicted labels,
  confidence scores), if any. These are model *outputs*, not dependencies — list
  them here, but do NOT list them under Upstream designs (that would create a
  cycle). Each output feature's own `feature-design` names this model-design as
  its producer.
- **Input assets:** any pretrained checkpoint / starting weights the model is
  built with (enters via the model-layer config — `configs/assets.py`).

## Validation

How you'll confirm the model meets its Goal (beyond "the code runs"):
- the target metric and the threshold that counts as success,
- the dataset/split it's validated on,
- sanity checks (loss converges, no NaN, predictions in range).

## Upstream designs

Link these as **OKF bundle-absolute Markdown links** (`/entity/slug.md`) with a
**relationship verb** in the prose:

- **trains on** [<feature-slug>](/feature/<feature-slug>.md) — each **input**
  feature-design this model consumes (the labels/annotations it trains on). Only
  inputs go here. Do NOT list the model's own *output* (prediction) features —
  those are downstream of this model, recorded under Requirements → Output
  features, and they name this model-design as their producer. Keeping
  inputs-only here is what makes the dependency graph acyclic.
- **extends** [<prior-model-slug>](/model/<prior-model-slug>.md) — any prior
  model-design it extends (a checkpoint lineage), if applicable.

A link to a not-yet-written design is fine (OKF tolerates broken links).

## Status & links

- **Model file + config groups:** the authored model fn and its `model_config`.
- **Workflow:** the registered Workflow.
- **tacit-knowledge.md:** link to journal entries from building it.
```

---

## Examples

```markdown
---
type: Model Design
title: 2-layer CNN for CIFAR-10
description: >
  A small 2-layer CNN that classifies CIFAR-10 images into the 10 classes, as the baseline architecture for the project's experiments.
tags: [model, cnn, cifar-10]
timestamp: 2026-06-22
status: Approved   # Draft | Approved | Built | Validated
slug: cifar10-2layer-cnn
# This document follows the Open Knowledge Format (OKF):
#   https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
# `resource` is intentionally omitted — a design doc is an abstract specification,
#   not a physical resource. Artifact linkage lives in tacit-knowledge.md +
#   the "Status & links" section below.
---

# Model Design: 2-layer CNN for CIFAR-10

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
- **trains on** [class-label](/feature/class-label.md) — the training target.

## Status & links
- **Model file + config groups:** (filled after authoring)
- **Workflow:** (filled after registration)
- **tacit-knowledge.md:** (filled after build)
```
