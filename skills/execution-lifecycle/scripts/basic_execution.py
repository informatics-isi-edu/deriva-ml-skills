#!/usr/bin/env python3
"""Run a basic DerivaML execution that produces output assets.

Copy this template to your project (typically `src/scripts/<task>.py`),
edit the parameters and the work block, commit the script, then run via
`deriva-ml-run`. The committed script's git URL + checksum become the
workflow's reproducibility anchor.

When to use:
    Any one-shot execution that produces output assets (predictions,
    model weights, plots, derived datasets) and needs catalog
    provenance. For nested runs, see `nested_execution.py`. For
    re-running after a crash, see `crash_recovery.py`. For salvaging a
    Failed/Stopped run, see `salvage_execution.py` (or the
    `troubleshoot-execution` skill's `salvage_runner.py`).

Pattern:
    1. Create a workflow (content-addressed by URL + commit hash).
    2. Open an Execution via the context manager.
    3. Inside the `with` block: do the work, stage outputs via
       `execution.asset_file_path()` / `execution.add_features()` /
       `execution.create_dataset()` / etc.
    4. After the `with` block: `execution.commit_output_assets()`.
       The context manager only sets status to `Stopped` on exit;
       `commit_output_assets()` is what uploads and transitions
       `Stopped → Pending_Upload → Uploaded`.
"""

from __future__ import annotations

import argparse
import sys

from deriva_ml import DerivaML
from deriva_ml.execution import ExecutionConfiguration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True,
                        help="Catalog hostname, e.g. data.example.org")
    parser.add_argument("--catalog-id", required=True,
                        help="Catalog ID, e.g. 1")
    parser.add_argument("--workflow-type", required=True,
                        help="Workflow_Type vocabulary term (e.g. Model_Training, "
                             "Inference, ETL). The term must already exist in the "
                             "catalog — add it via add_term if needed.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate the configuration without making catalog "
                             "changes. The execution row, workflow row, and asset "
                             "uploads are all skipped.")
    # --- task-specific arguments below ---
    # parser.add_argument("--input-rid", required=True, help="...")
    args = parser.parse_args()

    ml = DerivaML(args.hostname, args.catalog_id)

    workflow = ml.create_workflow(
        name="<task name>",
        workflow_type=args.workflow_type,
        description="<one-line description of what this workflow does>",
    )

    config = ExecutionConfiguration(
        description="<one-line description of this particular run>",
    )

    with ml.create_execution(config, workflow=workflow,
                             dry_run=args.dry_run) as execution:
        # ----------------------------------------------------------------
        # Task-specific work goes here. Examples:
        #
        #   path = execution.asset_file_path(
        #       "Execution_Asset", "predictions.csv",
        #       asset_types="Predictions",
        #   )
        #   path.write_text(my_predictions_csv)
        #
        #   feature = ml.lookup_feature("Image", "Classification")
        #   RecordClass = feature.feature_record_class()
        #   execution.add_features([
        #       RecordClass(Image=image_rid, Classification=label)
        #       for image_rid, label in predictions.items()
        #   ])
        #
        #   execution.create_dataset(
        #       dataset_types=["Inference"],
        #       description="Predictions from <model> over <input dataset>",
        #   )
        # ----------------------------------------------------------------
        ...

    # Commit AFTER the `with` block. The context manager set status to
    # Stopped; this call uploads staged bytes, writes asset rows, and
    # transitions Stopped → Pending_Upload → Uploaded. Idempotent on
    # re-call after partial failure.
    if not args.dry_run:
        execution.commit_output_assets()

    return 0


if __name__ == "__main__":
    sys.exit(main())
