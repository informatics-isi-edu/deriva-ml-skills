#!/usr/bin/env python3
"""COPY-ME template: the REGISTER phase (step 1 of two-step ingest).

Stages the source directory, then records every file as a by-reference ``File``
row via ``exe.add_files`` — producing a nested **File dataset** that mirrors the
on-disk tree. This runs in its OWN execution: the File dataset is an *Input*
record ("which source files exist / where the bytes came from"); the bytes are
NOT uploaded to Hatrac here. The separate UPLOAD phase (upload_phase_template.py)
consumes this File dataset and uploads the bytes — see that file for why the
split into two executions matters (it records source→upload lineage).

Prerequisite: deriva-ml >= 1.51.14 (the add_files directory-tree nesting that
lets equal-depth partition subdirs nest under a common root). Pin it.
"""

from __future__ import annotations

from pathlib import Path

from deriva_ml import DerivaML
from deriva_ml.core.filespec import FileSpec
from deriva_ml.execution import ExecutionConfiguration

from stage_source_template import stage_source


def run_register_phase(
    ml: DerivaML,
    source_root: Path,
    partitions: list[str],
    file_dataset_type: str,
    file_types: list[str],
    label_manifest: str | None = None,
    root_name: str = "source",
) -> str:
    """Stage the source files and register them as a by-reference File dataset.

    One execution. Returns the root File dataset RID for the upload phase to
    consume.

    Args:
        ml: Connected ``DerivaML`` instance (schema phase already run).
        source_root: Where ``stage_source`` lands the files.
        partitions: Source subdirs (``["."]`` for flat).
        file_dataset_type: ``Dataset_Type`` term for the File dataset (must
            exist in the catalog — add it in the schema phase).
        file_types: ``Asset_Type`` tag(s) for the registered File rows.
        label_manifest: Optional label-manifest filename (staged + registered).
        root_name: Name for the ingest-root dataset.

    Returns:
        The root File dataset RID.
    """
    stage_source(source_root, partitions, label_manifest)

    workflow = ml.create_workflow(
        name=f"Register {root_name} source files",
        workflow_type="Source_Registration",  # TODO: a Workflow_Type term you added in schema
        description="Register source files by reference as a File dataset (Input provenance)",
    )
    config = ExecutionConfiguration(workflow=workflow)

    # create_filespecs walks source_root recursively (picks up every partition
    # subdir + the label manifest), computing MD5 + length per file. It's a
    # generator — collect to a list. Pure local op; no catalog write yet.
    specs = list(
        FileSpec.create_filespecs(
            source_root,
            description="Source files (pre-upload reference)",
            file_types=file_types,
        )
    )

    with ml.create_execution(config) as exe:
        # add_files inserts one File row per spec (tag:// URL, by-reference —
        # NOT uploaded), links them as Inputs of this execution, and returns a
        # Dataset nested to mirror the directory tree (root + one child dataset
        # per partition subdir, each with source_directory set).
        root_ds = exe.add_files(
            specs,
            dataset_types=[file_dataset_type],
            description=f"{root_name} source files registered as upload inputs",
            root_name=root_name,
        )

    print(
        f"  Registered {len(specs)} source files as a File dataset "
        f"({root_ds.dataset_rid}); partitions: {partitions}"
    )
    return root_ds.dataset_rid
