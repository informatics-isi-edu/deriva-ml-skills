---
type: Table
title: Workflow
kind: core
description: A versioned reference to the code that runs an ML step, content-addressed by (URL, Checksum).
---

# Workflow

A **versioned reference to the code** that knows how to run an ML step. Workflows
are content-addressed by `(URL, Checksum)` — the same script at the same git
commit always resolves to the same Workflow row, so two executions that share a
Workflow row are guaranteed to have run identical source.

Each [Execution](Execution.md) links back to exactly one Workflow row, making
the producing code recoverable for any result in the catalog. Workflows are
typed via the [Workflow_Workflow_Type](Workflow_Workflow_Type.md) association
(`Training`, `Prediction`, `Analysis`, ...).

Workflow rows are written by the DerivaML library during execution setup; they
are not intended for direct manual creation.

## Foreign Keys

This is a system-managed table. It has no outbound foreign keys to other
deriva-ml tables.

## Notable columns

- `Name` — short human-readable label used in execution listings and citations;
  not required to be unique.
- `Description` (markdown) — longer description of what the workflow does, what
  inputs it expects, and what outputs it produces.
- `URL` — location of the workflow code (typically a GitHub URL pinned to a
  specific commit hash, or a notebook URL). One half of the content address.
- `Checksum` — git commit hash (or other content hash) of the code at `URL`.
  Together with `URL` this uniquely identifies the executable code.
- `Version` — semantic version string of the workflow (e.g. `1.2.0`).
  Independent from `Checksum`; used for human-readable release tracking when
  the workflow code is itself published as a versioned package.
