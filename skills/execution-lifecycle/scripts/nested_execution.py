#!/usr/bin/env python3
"""Run a parent execution that orchestrates multiple child executions.

Use for any workflow that decomposes into independently-trackable
sub-runs — parameter sweeps, sequential pipeline stages, fan-out
batch processing, etc. Each child gets its own catalog Execution row,
its own outputs, and its own provenance lineage; the parent row
groups them together via `add_nested_execution()`.

Pattern:
    1. Open the parent execution (this script's main `with` block).
    2. Inside the parent, loop over your work units. For each:
        a. Open a child execution context manager.
        b. Run the child work, stage outputs.
        c. Exit the child's `with` block (status → Stopped).
        d. Link the child to the parent with
           `parent.add_nested_execution(child)`.
        e. Commit the child's outputs.
    3. Exit the parent's `with` block.
    4. Commit the parent's outputs (typically a summary asset).

Naming conventions:
    - The parent's workflow_type is usually the orchestrating concept
      (e.g. "Hyperparameter_Sweep", "Multirun", "Pipeline").
    - Each child's workflow_type is the individual task
      (e.g. "Model_Training" for each point in a sweep).
"""

from __future__ import annotations

import argparse
import sys

from deriva_ml import DerivaML
from deriva_ml.execution import ExecutionConfiguration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--parent-workflow-type", required=True,
                        help="Workflow_Type term for the parent (e.g. "
                             "'Hyperparameter_Sweep', 'Multirun')")
    parser.add_argument("--child-workflow-type", required=True,
                        help="Workflow_Type term for each child run (e.g. "
                             "'Model_Training', 'Inference')")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ml = DerivaML(args.hostname, args.catalog_id)

    # Parent workflow: describes the orchestration as a whole.
    parent_workflow = ml.create_workflow(
        name="<parent task name>",
        workflow_type=args.parent_workflow_type,
        description="<what the parent run orchestrates>",
    )
    parent_config = ExecutionConfiguration(
        description="<one-line description of this parent run>",
    )

    # Child workflow: shared across all children of this parent. The
    # individual child Execution rows distinguish them.
    child_workflow = ml.create_workflow(
        name="<child task name>",
        workflow_type=args.child_workflow_type,
        description="<what each child run does>",
    )

    # ----- Work units to fan out over -----------------------------------
    # Replace this with whatever drives the sweep — a grid of
    # hyperparameters, a list of input dataset RIDs, etc.
    work_units: list[dict] = [
        # {"learning_rate": 1e-3, "batch_size": 32},
        # {"learning_rate": 1e-4, "batch_size": 32},
        # ...
    ]
    if not work_units:
        print("ERROR: configure `work_units` above before running.", file=sys.stderr)
        return 1

    with ml.create_execution(parent_config, workflow=parent_workflow,
                             dry_run=args.dry_run) as parent_exe:

        for i, unit in enumerate(work_units):
            child_config = ExecutionConfiguration(
                description=f"Child {i}: {unit}",
            )
            with ml.create_execution(child_config, workflow=child_workflow,
                                     dry_run=args.dry_run) as child_exe:
                # ----- Child work: do the unit-specific task ------------
                # e.g. train one model, run one inference batch, etc.
                # Stage outputs via child_exe.asset_file_path() / etc.
                ...

            # Link child → parent. Pass `sequence=i` if order matters
            # (sequential pipeline); omit for parallel runs.
            parent_exe.add_nested_execution(child_exe, sequence=i)

            # Commit the child's outputs now so each child's catalog
            # state advances independently. Failed children don't block
            # later children.
            if not args.dry_run:
                child_exe.commit_output_assets()

        # ----- Parent work (optional): aggregate child results ----------
        # e.g. write a summary CSV combining the child reports:
        #   summary_path = parent_exe.asset_file_path(
        #       "Execution_Asset", "sweep_summary.csv",
        #       asset_types="Summary",
        #   )
        #   summary_path.write_text(my_aggregate_csv)
        ...

    # Commit the parent's own outputs after the parent context exits.
    if not args.dry_run:
        parent_exe.commit_output_assets()

    return 0


if __name__ == "__main__":
    sys.exit(main())
