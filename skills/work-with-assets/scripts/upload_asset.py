#!/usr/bin/env python3
"""Upload one or more local files as catalog assets.

When to use:
    You have local files (model checkpoints, preprocessed data, plots,
    arbitrary blobs) you want recorded as catalog assets with full
    provenance back to a workflow.

Pattern:
    1. Open an execution.
    2. For each file: `execution.asset_file_path(asset_table, file_path)`
       to register it for upload.
    3. Exit the `with` block.
    4. `execution.commit_output_assets()` uploads bytes to Hatrac,
       writes asset rows to the catalog, and adds the directional
       `Output_File` Asset_Type tag automatically.

Asset table:
    The target asset table must already exist in the catalog. Built-in
    options: `Execution_Asset` (general-purpose) and `Execution_Metadata`
    (for execution-specific config/log files). For domain-specific
    asset tables (e.g. `Image`, `Model_Weights`), create the table via
    `create_asset()` first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from deriva_ml import DerivaML
from deriva_ml.execution import ExecutionConfiguration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--workflow-type", required=True,
                        help="Workflow_Type term (e.g. 'Asset_Upload', 'ETL', "
                             "'Model_Training' if this run produced the assets).")
    parser.add_argument("--asset-table", required=True,
                        help="Target asset table (e.g. 'Execution_Asset', "
                             "'Image', 'Model_Weights'). Must already exist.")
    parser.add_argument("--asset-type",
                        help="Optional asset_types tag to attach. Must be a "
                             "term in the Asset_Type vocabulary.")
    parser.add_argument("--description",
                        help="Per-asset description (applied to every file).")
    parser.add_argument("--file", required=True, action="append", type=Path,
                        help="Local file path to upload. Repeatable for multiple files.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    missing = [str(p) for p in args.file if not p.exists()]
    if missing:
        print(f"ERROR: missing files: {missing}", file=sys.stderr)
        return 1

    ml = DerivaML(args.hostname, args.catalog_id)

    workflow = ml.create_workflow(
        name=f"Upload {len(args.file)} file(s) to {args.asset_table}",
        workflow_type=args.workflow_type,
        description=f"Upload local files as {args.asset_table} assets",
    )
    config = ExecutionConfiguration(
        description=f"Uploading {len(args.file)} file(s) to {args.asset_table}",
    )

    with ml.create_execution(config, workflow=workflow,
                             dry_run=args.dry_run) as execution:
        for src_path in args.file:
            staged = execution.asset_file_path(
                args.asset_table,
                src_path,
                asset_types=args.asset_type,
                copy_file=True,
                description=args.description,
            )
            print(f"  staged: {src_path}  →  {staged}")

    if not args.dry_run:
        report = execution.commit_output_assets()
        print(f"Uploaded {report.total_uploaded} asset(s), "
              f"{report.total_failed} failed.")
        return 0 if report.total_failed == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
