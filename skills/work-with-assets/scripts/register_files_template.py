#!/usr/bin/env python3
"""Register a local directory of files as by-reference `File` inputs.

When to use:
    You have a directory of *source* files (the raw images/CSVs/scans a
    run consumed or that the catalog should record the ORIGIN of) and you
    want the catalog to hold a first-class record of *which files* — by
    reference (URL + MD5 + length), WITHOUT copying the bytes into Hatrac.
    Each file becomes a `File`-table row linked to the execution as an
    **Input**.

    This is the third file-ingest path; pick deliberately:

      - `add_files` (THIS script) — register external/local files BY
        REFERENCE as execution **Inputs**. Bytes stay where they are. Use
        for source-data provenance ("where did these come from").
      - `asset_file_path` + `commit_output_assets` (see upload_asset.py) —
        copy bytes INTO Hatrac as a typed asset table, recorded as
        execution **Outputs**. Use for files the run produced / that you
        want hosted, labelable, and splittable.
      - `LocalFile` in an ExecutionConfiguration — declare ONE local input
        file via the hydra config seam (resolves to a `File` row at
        execution start). Use when the input is wired through configs.

Pattern (what this script does):
    1. Open an execution (workflow + git commit = provenance).
    2. `FileSpec.create_filespecs(directory, ...)` walks the directory
       recursively, computing MD5 + length per file. Local paths are
       normalized to `tag://` origin URIs (an identity token, not a live
       fetch URL).
    3. `exe.add_files(specs, ...)` inserts one `File` row per file and
       returns a `Dataset` — a nested tree mirroring the directory layout
       (one dataset per sub-directory, parent dataset over the root) — and
       links that **File dataset** as an Input of this execution (a single
       Dataset↔Execution input edge for the root, not a per-file edge).
       Datasets are auto-tagged with the built-in `File` + `Directory`
       Dataset_Type terms.

Version requirement:
    Needs **deriva-ml >= 1.51.14**. 1.51.12 added the `resolve_rids`
    chunking that keeps a large `add_files` call from failing with an
    HTTP-414 (the member-resolution query is otherwise unbatched);
    1.51.14 added the directory-tree nesting that makes equal-depth
    sibling directories (e.g. `train`, `test`) nest under a common root
    dataset. Below 1.51.14 the result is flat sibling datasets with no
    parent. Pin accordingly in your project's pyproject.toml.

Staging tip:
    `create_filespecs` walks recursively, so point it at exactly the
    files you mean to register. If your source tree is larger than the
    subset you care about, stage the subset under a clean root first
    (symlinks avoid a second byte copy) and point this script there — the
    registered provenance then equals exactly the files you intend.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from deriva_ml import DerivaML
from deriva_ml.core.filespec import FileSpec
from deriva_ml.execution import ExecutionConfiguration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--workflow-type", required=True,
                        help="Workflow_Type term for this run (e.g. 'Data_Load', "
                             "'File_Registration'). Must exist in the vocabulary.")
    parser.add_argument("--directory", required=True, type=Path,
                        help="Local directory to register. Walked recursively; "
                             "every file becomes a by-reference File row.")
    parser.add_argument("--file-type", action="append", default=[],
                        help="Asset_Type term to tag each File with (e.g. 'Image'). "
                             "Repeatable. 'File' is always added automatically.")
    parser.add_argument("--dataset-type", action="append", default=[],
                        help="Extra Dataset_Type term for the File datasets. "
                             "Repeatable. 'File' + 'Directory' are added automatically.")
    parser.add_argument("--description", default="Registered source files",
                        help="Description recorded on each File and the datasets.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"ERROR: not a directory: {args.directory}", file=sys.stderr)
        return 1

    ml = DerivaML(args.hostname, args.catalog_id)

    # create_filespecs computes MD5 + length per file and is a generator —
    # it streams, so a huge tree is never fully materialized in memory.
    specs = list(
        FileSpec.create_filespecs(
            args.directory,
            description=args.description,
            file_types=args.file_type or None,
        )
    )
    if not specs:
        print(f"No files found under {args.directory}", file=sys.stderr)
        return 1
    print(f"Found {len(specs)} files under {args.directory}")

    workflow = ml.create_workflow(
        name=f"Register {len(specs)} files from {args.directory.name}",
        workflow_type=args.workflow_type,
        description=f"Register local files under {args.directory} as File inputs",
    )
    config = ExecutionConfiguration(
        description=f"Registering {len(specs)} source files by reference",
    )

    with ml.create_execution(config, workflow=workflow,
                             dry_run=args.dry_run) as execution:
        # add_files inserts the File rows and returns the root File dataset
        # (nested to mirror the directory structure), linking that dataset as
        # an Input of this execution (one Dataset↔Execution edge, not per-file).
        root_ds = execution.add_files(
            specs,
            dataset_types=args.dataset_type or None,
            description=args.description,
        )
        print(f"  Root File dataset: {root_ds.dataset_rid} "
              f"(source_directory={root_ds.source_directory!r})")
        for child in root_ds.list_dataset_children():
            if child.is_directory:
                print(f"    child dir dataset: {child.dataset_rid} "
                      f"(source_directory={child.source_directory!r})")

    # add_files writes File rows and links them as inputs within the `with`
    # block; there are no output-asset bytes to commit for this path. The
    # context manager finalizes the execution status on exit.
    if args.dry_run:
        print("Dry run — no File rows written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
