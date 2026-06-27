#!/usr/bin/env python3
"""COPY-ME template: the UPLOAD phase (step 2 of two-step ingest).

Consumes the File dataset produced by the REGISTER phase and uploads the bytes
into Hatrac as typed asset rows. This is a SEPARATE execution from register, on
purpose:

  - register's add_files recorded WHICH source files exist (Inputs).
  - upload's asset_file_path + commit_output_assets records WHICH bytes were
    uploaded to Hatrac (Outputs), and declares the register File dataset as a
    DatasetSpec(materialize=False) INPUT of this execution.

That cross-execution Input declaration is the catalog-recorded lineage edge from
source files to hosted assets — an uploaded asset traces back to the exact
source file it came from. One execution cannot express this edge; hence two.

materialize=False is REQUIRED on the input: the File rows carry tag:// URLs
(by-reference), which cannot be materialized into a bag.

The per-row features/labels are added in a SECOND execution (2b) for clean
annotation provenance — the same feature-population pattern documented by
/deriva-ml:create-feature and its populate_feature_values.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from deriva_ml import DerivaML
from deriva_ml.dataset.aux_classes import DatasetSpec
from deriva_ml.execution import ExecutionConfiguration


def tag_url_to_path(url: str) -> Path:
    """Resolve a ``tag://`` File URL back to its local filesystem path.

    ``FileSpec`` rewrites local paths to ``tag://{host},{date}:file://{path}``.
    This recovers ``{path}`` so the upload phase can read the staged bytes.
    """
    after_colon = url.split(":file://", 1)[-1] if ":file://" in url else urlparse(url).path
    return Path(after_colon)


def run_upload_phase(
    ml: DerivaML,
    source_dataset_rid: str,
    asset_table: str,
    asset_types: list[str],
    partitions: list[str],
    rename_file: Callable[[str, Path], str] | None = None,
) -> dict[str, Any]:
    """Upload the registered source files into Hatrac as typed assets.

    Args:
        ml: Connected ``DerivaML`` instance.
        source_dataset_rid: Root File dataset RID from the register phase.
        asset_table: Hosted asset table name (created in the schema phase).
        asset_types: ``Asset_Type`` tag(s) for the uploaded assets.
        partitions: Source partitions to iterate (``["."]`` for flat). Matched
            against each child dataset's ``source_directory``.
        rename_file: Optional ``(partition, local_path) -> new_name`` hook;
            ``None`` keeps the original filename.

    Returns:
        Stats dict ``{"assets_uploaded": int, "features_added": int}``.
    """
    if rename_file is None:
        def rename_file(partition: str, path: Path) -> str:  # noqa: ARG001
            return path.name

    source_ds = ml.lookup_dataset(source_dataset_rid)

    workflow = ml.create_workflow(
        name=f"Upload {asset_table} assets",
        workflow_type="Asset_Upload",  # TODO: a Workflow_Type term you added in schema
        description=f"Upload registered source files as {asset_table} assets",
    )
    # Declare the File dataset as a materialize=False INPUT — the lineage edge.
    config = ExecutionConfiguration(
        workflow=workflow,
        datasets=[
            DatasetSpec(
                rid=source_dataset_rid,
                version=source_ds.current_version,
                materialize=False,
            )
        ],
    )

    # Map partition -> its child File dataset (source_directory identifies it).
    children = {
        c.source_directory: c
        for c in source_ds.list_dataset_children()
        if getattr(c, "is_directory", False)
    }

    uploaded = 0
    with ml.create_execution(config) as exe:
        for partition in partitions:
            part_ds = source_ds if partition == "." else children.get(partition)
            if part_ds is None:
                print(f"  WARNING: no child dataset for partition {partition!r}; skipping")
                continue
            members = part_ds.list_dataset_members()
            for file_rec in members.get("File", []):
                local_path = tag_url_to_path(file_rec["URL"])
                # TODO: skip the label manifest / non-asset files here if your
                #   layout registers them alongside the assets.
                exe.asset_file_path(
                    asset_name=asset_table,
                    file_name=str(local_path),
                    asset_types=asset_types,
                    copy_file=True,
                    rename_file=rename_file(partition, local_path),
                )
                uploaded += 1

    # commit_output_assets runs AFTER the with-block: uploads staged bytes to
    # Hatrac, writes asset rows, tags them Output_File, transitions the
    # execution Stopped -> Pending_Upload -> Uploaded.
    report = exe.commit_output_assets(clean_folder=True)
    print(f"  Uploaded {report.total_uploaded} {asset_table} asset(s).")

    features_added = _add_features(ml, asset_table)
    return {"assets_uploaded": uploaded, "features_added": features_added}


def _add_features(ml: DerivaML, asset_table: str) -> int:
    """SECOND execution (2b): attach per-row features/labels to the uploaded assets.

    Separate execution = clean annotation provenance, distinct from the upload.
    This is the feature-population pattern documented by /deriva-ml:create-feature
    (see its populate_feature_values.py). Fill the TODO for your feature.

    Args:
        ml: Connected ``DerivaML`` instance.
        asset_table: The asset table whose rows you just uploaded.

    Returns:
        Count of feature rows added.
    """
    # TODO: your domain — build feature records for the assets you uploaded and
    #   add them in their own execution. The shape:
    #
    #   workflow = ml.create_workflow(name=..., workflow_type="Data_Load",
    #                                 description="Add <Feature> labels")
    #   config = ExecutionConfiguration(workflow=workflow)
    #   FeatureRecord = ml.feature_record_class(asset_table, "<Feature_Name>")
    #   records = [FeatureRecord(<asset_table>=a.asset_rid, <Term_Col>=<value>)
    #              for a in ml.list_assets(asset_table)]
    #   with ml.create_execution(config) as exe:
    #       exe.add_features(records)
    #   exe.commit_output_assets(clean_folder=True)
    #
    # If a prior loader run wrote ground-truth feature rows, truncate them first
    # so retries don't accumulate duplicates (see the CIFAR reference's
    # _truncate_loader_classification_rows, filtered to the GT partition).
    # Return 0 here until you implement it; not all loads add features.
    return 0
