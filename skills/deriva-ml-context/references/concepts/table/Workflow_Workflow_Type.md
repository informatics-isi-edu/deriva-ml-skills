---
type: Table
title: Workflow_Workflow_Type
kind: association
description: Many-to-many tag assignments between workflows and workflow types.
---

# Workflow_Workflow_Type

Many-to-many association between [Workflow](Workflow.md) and
[Workflow_Type](Workflow_Type.md). A workflow can carry multiple types
simultaneously (for example `Training` + `Feature_Creation`).

## Foreign Keys

Both columns reference tables in this cluster:

- `Workflow` → [Workflow](Workflow.md) — the workflow being tagged.
- `Workflow_Type` → [Workflow_Type](Workflow_Type.md) — the vocabulary term
  applied to that workflow.

## Notable columns

This is a pure association table. Beyond the two FK columns (and the ERMrest
system columns) it carries no additional data columns.
