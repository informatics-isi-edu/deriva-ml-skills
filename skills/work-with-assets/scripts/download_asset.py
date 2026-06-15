#!/usr/bin/env python3
"""Download a catalog asset to a local directory with execution provenance.

When to use:
    You need a catalog asset (model weights, image, blob) on your
    local filesystem, and you want the download recorded as an input
    of an execution. The execution row provides the audit trail
    answering "what consumed this asset?".

    `download_asset` is an Execution method — there is no
    non-execution `ml.download_asset`. For an exploratory one-off
    pull, open a throwaway execution and call
    `execution.download_asset(asset_rid, dest_dir)`; the execution row
    is what carries the "what consumed this asset?" provenance.

Pattern:
    1. Open an execution.
    2. For each asset RID: `execution.download_asset(rid, dest_dir)`.
       deriva-ml auto-adds the `Input_File` Asset_Type tag and writes
       `Asset_Role="Input"` on the resulting `{Asset}_Execution`
       association row.
    3. Use the returned `AssetFilePath` inside the with-block work.
    4. Exit. (No `commit_output_assets()` needed unless this same
       execution also produces outputs.)
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
                        help="Workflow_Type term (e.g. 'Inference', 'Analysis').")
    parser.add_argument("--asset-rid", required=True, action="append",
                        help="Asset RID to download. Repeatable.")
    parser.add_argument("--dest-dir", type=Path,
                        help="Destination directory. Defaults to "
                             "execution.working_dir / 'downloads' / <asset_rid>.")
    parser.add_argument("--use-cache", action="store_true",
                        help="Re-use the local DerivaML asset cache if available "
                             "(symlinks into dest_dir instead of re-downloading).")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ml = DerivaML(args.hostname, args.catalog_id)

    workflow = ml.create_workflow(
        name=f"Download {len(args.asset_rid)} asset(s)",
        workflow_type=args.workflow_type,
        description=f"Download asset(s) as execution inputs: {args.asset_rid}",
    )
    config = ExecutionConfiguration(
        description=f"Downloading {len(args.asset_rid)} asset(s)",
    )

    with ml.create_execution(config, workflow=workflow,
                             dry_run=args.dry_run) as execution:
        if args.dry_run:
            print(f"[DRY RUN] Would download: {args.asset_rid}")
            return 0
        for rid in args.asset_rid:
            # Canonical pattern: per-asset subdirectory keyed by RID,
            # collision-free by construction (matches the platform default).
            dest = (args.dest_dir or execution.working_dir / "downloads") / rid
            dest.mkdir(parents=True, exist_ok=True)
            path = execution.download_asset(rid, dest_dir=dest, use_cache=args.use_cache)
            print(f"  downloaded: {rid}  →  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
