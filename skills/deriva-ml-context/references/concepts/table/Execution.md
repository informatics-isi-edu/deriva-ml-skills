---
type: Table
title: Execution
kind: core
description: One run of a Workflow against specific input Datasets, producing output Datasets, Features, and Assets.
---

# Execution

One **run of a [Workflow](Workflow.md)** against specific input Datasets,
producing output Datasets, Features, and Assets. Carries the execution state
machine (`Status`) and a timing breakdown across three lifecycle phases
(`Download_Duration`, `Execution_Duration`, `Upload_Duration`).

The backing table of the DerivaML **Execution** abstraction. Provenance edges
connect an Execution to its inputs (via `Dataset_Execution`) and outputs (via
`Dataset_Version.Execution`, `Execution_Asset_Execution`,
`Execution_Metadata_Execution`). Nested (child) executions are tracked in
[Execution_Execution](Execution_Execution.md).

## Foreign Keys

- `Workflow` → [Workflow](Workflow.md) — the versioned code that ran this
  execution; content-addressed by `(URL, Checksum)`.
- `Status` → [Execution_Status](Execution_Status.md) — current state in the
  execution state machine.

## Notable columns

- `Description` (markdown) — human-readable purpose, hyperparameters worth
  calling out, or anything a reader scanning an execution list should know.
- `Status_Detail` — free-form context for the current Status: typically the
  most recent stage message, error text on `Failed`, or a progress indicator
  on long-running phases.
- `Execution_Duration` — ISO 8601 duration string for the algorithm phase
  (inside the `with ml.create_execution()` block, excluding download and
  upload).
- `Download_Duration` — ISO 8601 duration string for the initialization phase
  (downloading input datasets and assets).
- `Upload_Duration` — ISO 8601 duration string for the commit phase (writing
  output bags, uploading assets to Hatrac, finalizing catalog rows).
