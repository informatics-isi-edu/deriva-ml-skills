---
type: Index
title: Dataset lifecycle concepts
description: OKF bundle for DerivaML dataset concepts — types, element types, structure, splits, subsampling, versioning, navigation, consumption, and lifecycle operations.
---

# Dataset lifecycle concepts

- [Dataset types and element types](dataset-types.md) — what a dataset is, the three-axis Dataset_Type vocabulary (role / content / origin), element-type registration.
- [Structure, splitting, and subsampling](structure-and-splits.md) — standalone vs nested vs split structure, the split_dataset primitive, the subsample primitive, partition unit.
- [Versioning and identification](versioning.md) — characterization & validation roadmap, the ADR-0003 dev/release version model, RID + version DatasetSpec identity.
- [Discovering, navigating, using, and downloading](navigation.md) — pre-creation discovery, read-side exploration (members, hierarchies, element types, provenance), consumption patterns, BDBag download details.
- [Lifecycle operations](lifecycle-ops.md) — deleting datasets, full operations summary tables (creation/modification, navigation/discovery, download/export).
