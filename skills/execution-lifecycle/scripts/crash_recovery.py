#!/usr/bin/env python3
"""Recover an execution stuck in `Running` after a hard crash.

When to use:
    The execution's process died without a clean `__exit__` (OOM,
    SIGKILL, host reboot, kernel panic). The execution row is still
    `Running` in the catalog but no process is touching it; staged
    rows in the workspace SQLite registry are intact.

The fix is a direct `Running → Pending_Upload` transition. The state
machine accepts this as a legal crash-recovery path. After the
transition, `commit_output_assets()` drives the upload as normal.

When NOT to use:
    - The execution exited normally (status `Stopped` or `Failed`):
      use `salvage_execution.py` instead — `commit_output_assets()`
      already accepts those states without an explicit transition.
    - You want to abandon the staged work: use `--abort` mode below to
      transition to `Aborted` and discard.
"""

from __future__ import annotations

import argparse
import sys

from deriva_ml import DerivaML
from deriva_ml.execution.state_store import ExecutionStatus


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--execution-rid", required=True,
                        help="The crashed execution's RID. Must be in `Running` "
                             "status and exist in the local workspace registry.")
    parser.add_argument("--abort", action="store_true",
                        help="Abandon staged work instead of recovering. "
                             "Transitions Running → Aborted and discards "
                             "staged rows on commit.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ml = DerivaML(args.hostname, args.catalog_id)
    execution = ml.resume_execution(args.execution_rid)

    if execution.status != ExecutionStatus.Running:
        print(f"ERROR: Execution {args.execution_rid} is in status "
              f"{execution.status}, not Running. For non-Running "
              f"recovery, see salvage_execution.py.", file=sys.stderr)
        return 1

    pending = execution.pending_summary()
    print(f"Crashed execution {args.execution_rid}:")
    print(f"  Status:         {execution.status}")
    print(f"  Pending rows:   {pending.rows}")
    print(f"  Pending files:  {pending.files}")

    if args.abort:
        if args.dry_run:
            print("[DRY RUN] Would transition Running → Aborted.")
            return 0
        execution.abort()
        print(f"Aborted execution {args.execution_rid}.")
        return 0

    if args.dry_run:
        print("[DRY RUN] Would transition Running → Pending_Upload "
              "and commit staged outputs.")
        return 0

    # Direct Running → Pending_Upload transition (legal per the
    # crash-recovery path in the state machine).
    execution.update_status(ExecutionStatus.Pending_Upload)
    print(f"Transitioned {args.execution_rid} to Pending_Upload.")

    report = execution.commit_output_assets()
    print(f"Recovery: {report.total_uploaded} uploaded, "
          f"{report.total_failed} failed")
    if report.errors:
        for err in report.errors:
            print(f"  ERROR: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
