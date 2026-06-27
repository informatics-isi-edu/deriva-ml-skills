---
type: Table
title: Feature_Name
kind: vocabulary
description: Controlled vocabulary registry of feature names across all feature tables in the catalog.
---

# Feature_Name

Registry of **feature names** for the catalog. Every feature defined on a
target table — via `create_feature` — adds a term here. The vocabulary ensures
that the feature name space is audited and searchable rather than free-form
text scattered across individual feature tables.

Every feature table (`Execution_{Target}_{Feature}`) carries a FK to a
`Feature_Name` term. For the feature-table shape and the full
`create_feature` workflow, see `/deriva-ml:create-feature`.

## Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

## Seeded terms

No terms are seeded at schema initialization. Terms are added dynamically:
each call to `create_feature` registers a new name in this vocabulary as part
of creating the corresponding feature table. The term set therefore reflects the
feature definitions installed in a given catalog.
