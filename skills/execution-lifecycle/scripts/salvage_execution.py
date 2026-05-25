#!/usr/bin/env python3
"""Salvage a partially-completed execution by committing its staged outputs.

When to use:
    An execution exited the `with` block (status `Stopped` or `Failed`)
    but `commit_output_assets()` either was never called or partially
    failed. Staged feature values and asset files exist in the
    workspace SQLite registry; this script drives the upload phase
    against them.

When NOT to use:
    - The execution is in `Aborted` status: outputs are abandoned, not
      salvageable via this path. Investigate why and decide whether to
      create a fresh execution from the same inputs.
    - You want to abandon the staged work entirely: call
      `deriva-ml gc-executions --status Failed` to drop the
      registry rows and clean up the working directory.

The `commit_output_assets()` call is idempotent — re-running after a
partial failure picks up only the rows that still need committing.
"""

from __future__ import annotations

import argparse
import sys

from deriva_ml import DerivaML


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--execution-rid", required=True,
                        help="The Execution RID to salvage. Must exist in the "
                             "local workspace SQLite registry (i.e. originated "
                             "from this machine).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print pending-row summary without committing.")
    args = parser.parse_args()

    ml = DerivaML(args.hostname, args.catalog_id)

    # Re-hydrate the Execution from the workspace registry. This
    # reconciles SQLite ↔ catalog state and returns a fresh Execution
    # object ready to commit.
    execution = ml.resume_execution(args.execution_rid)

    pending = execution.pending_summary()
    print(f"Execution {args.execution_rid} (status: {execution.status}):")
    print(f"  Pending rows:   {pending.rows}")
    print(f"  Pending files:  {pending.files}")
    print(f"  Failed rows:    {pending.failed_rows}")
    print(f"  Failed files:   {pending.failed_files}")

    if pending.rows == 0 and pending.files == 0 and pending.failed_rows == 0 and pending.failed_files == 0:
        print("Nothing to salvage — workspace is clean for this execution.")
        return 0

    if args.dry_run:
        print("[DRY RUN] Skipping commit_output_assets.")
        return 0

    print(f"Committing staged outputs for {args.execution_rid}...")
    report = execution.commit_output_assets()
    print(f"Salvage report: {report.total_uploaded} uploaded, {report.total_failed} failed")
    if report.errors:
        for err in report.errors:
            print(f"  ERROR: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
