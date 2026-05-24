#!/usr/bin/env python3
"""Populate feature values from a CSV of labels.

Reads a CSV with one row per target record + label columns, validates
the labels against the feature's vocabulary terms, and adds the values
inside a tracked execution so each value carries provenance back to
this committed script.

When to use:
    - A domain expert handed you a CSV of ground-truth labels and you
      need to attach them to existing catalog records.
    - You're backfilling model predictions for a batch of records
      (workflow_type would typically be "Inference" rather than
      "Annotation").
    - Any other one-shot bulk-add of feature values where the labels
      live in a flat file.

For multi-column features or asset-based features, edit the
RecordClass instantiation in the loop to pass all required columns.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from deriva_ml import DerivaML
from deriva_ml.execution import ExecutionConfiguration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--workflow-type", required=True,
                        help="Workflow_Type term (e.g. Annotation, Inference)")
    parser.add_argument("--dry-run", action="store_true")

    parser.add_argument("--csv", required=True, type=Path,
                        help="Path to the label CSV. First row is the header. "
                             "Required columns: the target_table's RID column "
                             "(e.g. 'Image') plus one column per feature term "
                             "(e.g. 'Diagnosis').")
    parser.add_argument("--target-table", required=True,
                        help="The table the feature is defined on, e.g. 'Image'")
    parser.add_argument("--feature-name", required=True,
                        help="The feature name (PascalCase), e.g. 'Diagnosis'")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        return 1

    ml = DerivaML(args.hostname, args.catalog_id)

    # ----- Pre-flight: validate feature + parse the CSV -----------------
    feature = ml.lookup_feature(args.target_table, args.feature_name)
    RecordClass = feature.feature_record_class()

    with args.csv.open() as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"ERROR: {args.csv} has no data rows", file=sys.stderr)
        return 1

    # The CSV header must include the target table's RID column. By
    # convention, this is named exactly after the table (e.g. 'Image').
    if args.target_table not in rows[0]:
        print(f"ERROR: CSV header is missing the '{args.target_table}' RID column",
              file=sys.stderr)
        print(f"       Found columns: {list(rows[0].keys())}", file=sys.stderr)
        return 1

    print(f"Read {len(rows)} rows from {args.csv}")

    # ----- Execution context: build records, stage, commit --------------
    workflow = ml.create_workflow(
        name=f"Populate {args.feature_name} feature values",
        workflow_type=args.workflow_type,
        description=f"Bulk-load {args.feature_name} from {args.csv.name}",
    )

    config = ExecutionConfiguration(
        description=f"Adding {len(rows)} {args.feature_name} values to {args.target_table}",
    )

    with ml.create_execution(config, workflow=workflow,
                             dry_run=args.dry_run) as execution:
        # Build a typed record per CSV row. Pydantic validates each
        # value against the feature's term vocabulary and column types;
        # mismatched terms raise DerivaMLInvalidTerm immediately.
        records = [RecordClass(**row) for row in rows]
        print(f"Validated {len(records)} feature records")

        if args.dry_run:
            print("[DRY RUN] Skipping add_features call")
            return 0

        execution.add_features(records)
        print(f"Staged {len(records)} feature values for upload")

    # commit_output_assets() drives the upload phase for staged feature
    # values (they ride along with the asset-commit pipeline).
    execution.commit_output_assets()
    return 0


if __name__ == "__main__":
    sys.exit(main())
