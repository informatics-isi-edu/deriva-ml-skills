---
type: Concept
title: Feature vs column decision
description: What a feature is, when to use a feature vs a column on the target table, and annotated examples.
---

# Feature vs column decision

Background on features in DerivaML. For the step-by-step guide, see `workflow.md`.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## What is a Feature?

A feature links domain objects (e.g., Image, Subject) to a set of values — which could be controlled vocabulary terms, computed values, or assets. It is the primary way to attach structured meaning to records in DerivaML.

Common uses include:
- **Classification labels** — human-assigned or model-predicted categories (e.g., tumor grade, cell type, diagnosis)
- **Model predictions** — inference results from a classifier or detector
- **Quality scores** — numeric assessments (e.g., image quality, focus score, confidence)
- **Transformed data** — processed versions of source records (e.g., normalized images, cropped regions)
- **Statistical values** — computed aggregates (e.g., max intensity, mean pixel value, cell count)
- **Segmentation masks** — pixel-level or region annotations linked as assets
- **Review annotations** — status tracking with reviewer provenance

Each feature has:
- **A name** — identifies the annotation dimension (e.g., "Tumor_Classification", "Image_Quality")
- **A target table** — which domain table's records are being annotated (e.g., Image, Subject)
- **Value columns** — controlled vocabulary terms, asset references, or both
- **Optional metadata columns** — additional structured data like confidence scores or reviewer references
- **A description** — what the feature measures, what values it takes, its role in the workflow

Every feature value is associated with an **execution**, which provides full provenance. This means you can differentiate between multiple values for the same record by execution RID, workflow, execution description, timestamp, or any other execution attribute. For example, you can distinguish labels from "Pathologist A's review" vs "Model v2 predictions" vs "QC pipeline run #47".

Features are inherently **multivalued**: a single record can accumulate multiple values for the same feature over time (e.g., labels from different annotators or model runs), and the same term can be applied to many records. This is by design — it enables inter-annotator agreement analysis, model comparison, and audit trails. When you need a single value per record, use feature selection (see [selectors.md](selectors.md)).

## When to Use a Feature vs a Column

Not every piece of metadata belongs in a feature. Features have overhead (a separate table, execution requirement, provenance tracking) that's justified when you need their properties. Use this to decide:

**Use a feature when:**
- The value needs **provenance** — you need to know *who* assigned it (which execution, which annotator, which model run)
- The value is **multivalued** — the same record can have multiple values from different sources (multiple annotators, successive model runs)
- The value comes from a **controlled vocabulary** — ensuring consistency across annotators and experiments
- The value will be used for **ML training labels** — features integrate with dataset bags, denormalization, and Python API `bag.restructure_assets()`
- The value may **change over time** — features accumulate history, columns overwrite

**Use a column on the table when:**
- The value is **intrinsic to the record** — it's a property of the object itself, not an annotation about it (e.g., image dimensions, file format, collection date)
- There's **only ever one value** — no need for multi-annotator or multi-run support
- **No provenance needed** — you don't care who set it or when
- The value is **immutable** — it won't change after initial creation (e.g., patient age at enrollment)

**Examples:**

| Value | Feature or Column? | Why |
|-------|:---:|-----|
| Diagnosis label | Feature | Multiple annotators, controlled vocabulary, ML training label |
| Image quality score | Feature | Different reviewers may score differently, provenance matters |
| Model prediction probability | Feature | Different model runs produce different values |
| Image width in pixels | Column | Intrinsic property, single value, never changes |
| File format (PNG, DICOM) | Column | Intrinsic, immutable |
| Collection date | Column | Intrinsic to the record |
| Segmentation mask | Feature | Asset-based, tied to a specific model execution |
