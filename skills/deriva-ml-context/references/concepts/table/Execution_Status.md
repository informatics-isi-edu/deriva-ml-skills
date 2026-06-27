---
type: Table
title: Execution_Status
kind: vocabulary
description: Controlled vocabulary describing the lifecycle state of an Execution.
---

# Execution_Status

Controlled vocabulary describing the **lifecycle state** of an
[Execution](Execution.md). Terms are managed by the execution state machine
and used as the FK target for `Execution.Status`.

For the full state-machine transitions and lifecycle semantics, see
`/deriva-ml:execution-lifecycle`.

## Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

## Seeded terms

Seven terms are seeded at schema initialization:

| Name | Description |
|------|-------------|
| `Created` | Execution row has been created; work has not started. |
| `Running` | Execution algorithm is actively running. |
| `Stopped` | Algorithm finished successfully; output assets not yet uploaded. |
| `Pending_Upload` | Algorithm succeeded; asset upload to the catalog is in progress. |
| `Uploaded` | Execution ran to success and all outputs are persisted to the catalog. |
| `Failed` | Execution encountered an unrecoverable error. |
| `Aborted` | Execution was canceled by the user before reaching a terminal state. |

Do not extend this vocabulary without coordinating with the deriva-ml execution
lifecycle — additional states require matching state-machine logic in the
library.
