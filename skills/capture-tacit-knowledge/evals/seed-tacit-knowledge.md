---
type: Log
title: "Tacit Knowledge — EyeAI CIFAR pilot"
description: >
  The why behind this project's DerivaML decisions — rationale, dead ends, and
  cross-discipline consequences that the catalog records but does not explain.
  Append-only; each entry is a dated tk-… decision record.
tags: [tacit-knowledge, provenance, deriva-ml]
---

# Tacit Knowledge

This file records the *why* behind decisions about this project's models and
data. The catalog is the source of truth for *what* exists; this file is the
source of truth for *why*. Append-only.

<a id="tk-012"></a>
### tk-012 — Training pinned to animals-only subset ([dataset 7KE v0.3.0](https://localhost/id/96/7KE@2P-ABCD))
**When:** 2026-05-20T10:15:00-07:00
**By:** Carl Kesselman (carl@isi.edu)

Cut the training set down to the six animal classes and dropped the four vehicle
classes. On the full 10-class CIFAR the vehicle classes carried so much
intra-class appearance variance (angle, lighting, background) that the variance
dominated the signal and the model spent capacity fitting vehicle noise instead
of the animal boundaries we actually care about for this pilot. Weighed keeping
all 10 classes with class weighting, but the animals-only cut was cleaner for a
first baseline. **Weighed alternatives:** full 10-class with reweighting
(rejected — variance still leaked); vehicles-only (rejected — not the target).

<a id="tk-018"></a>
### tk-018 — QC status kept separate from diagnostic annotations ([feature 9PQ4](https://localhost/id/96/9PQ4@2P-XYZW))
**When:** 2026-05-26T14:32:00-07:00
**By:** Dr. Pathologist (https://auth.globus.org/...), Carl Kesselman (carl@isi.edu)

Added a dedicated `Image_QC_Status` feature (vocabulary 9PR0) for slide quality
rather than extending `Image_Annotation` with quality terms like "blurry."
Kept QC concerns separate from diagnostic concerns: the two review workflows
have different reviewers, different criteria, and different downstream consumers,
so collapsing them into one vocabulary would entangle the queues and make it
impossible to filter "unusable image" from "no diagnostic finding." A future
request to add a quality term (blurry, low-contrast, artifact) belongs in
`Image_QC_Status`, not `Image_Annotation`.
