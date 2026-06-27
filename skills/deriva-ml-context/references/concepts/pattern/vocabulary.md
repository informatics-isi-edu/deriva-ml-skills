---
type: Pattern
title: Controlled vocabulary
description: How DerivaML uses controlled-vocabulary tables to type its abstractions, and how to extend them.
---

# Controlled vocabulary

A **controlled vocabulary** is a table of standardized terms (each with a `Name`,
`Description`, optional `Synonyms`, and a stable `{project}:{RID}` CURIE) that
*types* a DerivaML entity. Typing entities this way is what makes them findable,
filterable, and stable: a consumer dispatches on `Dataset_Type == "Training"`,
not on a name string, and the CURIE survives catalog clones. Adding a term is the
sanctioned way to introduce a new *kind* of thing — distinct from going around
the abstractions with raw inserts.

## The six fixed `deriva-ml` vocabulary tables

Split by who writes them:

- **User-extensible** (add terms with `add_term`): [Dataset_Type](../table/Dataset_Type.md),
  [Workflow_Type](../table/Workflow_Type.md), [Asset_Type](../table/Asset_Type.md).
- **System-managed** (populated by the machinery — do not extend):
  [Execution_Status](../table/Execution_Status.md) (the execution-state machine),
  [Asset_Role](../table/Asset_Role.md) (the upload/download machinery, Input/Output),
  [Feature_Name](../table/Feature_Name.md) (`create_feature` registers one term per feature).

## Extending vs creating

- **Add a term to an existing vocabulary** — the common case. Use the generic
  `add_term(schema="deriva-ml", table="<Vocab>", name=..., description=...)`. No
  deriva-ml-specific variant exists for adding a term; the generic tool is correct.
- **Create a brand-new vocabulary table** on a deriva-ml catalog — prefer the
  ML-aware `deriva_ml_create_vocabulary` over the generic `create_vocabulary`: it
  scopes the CURIE prefix to the project, defaults to the domain schema, and
  refreshes the Chaise navbar. Then `add_term` for each term.

## Built-in vs domain vocabularies

The six above live in the `deriva-ml` schema. Your own domain vocabularies
(`Sample_Type`, `Tissue_Type`, `Image_Quality`, …) live in the **project's domain
schema** — same physical shape, created via `deriva_ml_create_vocabulary`,
extended with `add_term` using your domain schema name.

For the term-management surface (add/lookup/synonyms, the generic
`create_vocabulary` for non-deriva-ml catalogs), see
`/deriva:manage-vocabulary` *(deriva-skills)*. For DerivaML-specific vocabulary
guidance, see `/deriva-ml:deriva-ml-context` ("Built-in DerivaML vocabularies").
