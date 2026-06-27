---
type: Table
title: Execution_Execution
kind: association
description: Self-association expressing execution nesting — parent (sweep/multirun) and child (individual run).
---

# Execution_Execution

Self-referential association on [Execution](Execution.md) expressing execution
nesting. The `Execution` column is the **parent** (typically a sweep or
multirun controller); `Nested_Execution` is one of its **children**
(an individual run within that sweep).

`Sequence` optionally orders children within a parent for sequential runs; a
`NULL` value indicates parallel siblings with no defined order.

## Foreign Keys

Both columns reference the same table:

- `Execution` → [Execution](Execution.md) — the parent (containing) execution.
- `Nested_Execution` → [Execution](Execution.md) — the child (nested) execution.

## Notable columns

- `Sequence` (int, nullable) — ordinal position of this child within its
  parent. `NULL` means the child is one of a set of parallel siblings with
  no defined ordering.
