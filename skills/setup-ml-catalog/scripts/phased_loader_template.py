#!/usr/bin/env python3
"""COPY-ME template: a thin three-phase orchestrator for a from-scratch load.

This is a template, not a finished script. Copy it into your project's
``src/scripts/`` (e.g. ``src/scripts/load_<project>.py``), fill in the
``# TODO: your domain`` blocks in each phase function, commit it (provenance
records the git hash), then run via::

    uv run python src/scripts/load_<project>.py --hostname HOST --catalog-id ID --phase all

There is **no pyproject entry point** for this — it is a one-time loader you
run by hand. Modeled on the CIFAR-10 reference ``load_cifar10.py`` in the
external ``deriva-ml-model-template`` repo; generalized for any domain.

When to use:
    Branch 1 ("From scratch") of /deriva-ml:setup-ml-catalog. You have raw
    data (files, CSVs, an external source) and want a fresh catalog
    populated programmatically. This orchestrator wires three resumable
    phases — schema, assets, datasets — behind one ``--phase`` switch.

Pattern:
    The loader is a thin entry point. Each phase is its own function; the
    only job of ``main`` is to route ``--phase`` to the right one(s). Keep
    domain logic OUT of ``main`` and inside the phase functions so a phase
    can be run (and re-run) in isolation.

Resumability:
    Phasing exists so a partial failure resumes from the failed phase
    rather than from the top. If the ``assets`` phase dies halfway, you
    re-run ``--phase assets`` (or ``--phase datasets`` once assets are in)
    without paying for the ``schema`` phase again. ``--phase schema``
    prints the catalog id on completion so a first-run ``--create`` user
    can resume against ``--catalog-id`` without hunting for it.

Idempotency expectations (per phase):
    - schema   — fully idempotent (check-before-create; safe to re-run).
    - assets   — mostly idempotent (Hatrac uploads are content-addressed;
                 row inserts should upsert / truncate-then-write — see the
                 CIFAR reference's ``_truncate_*`` guard for the feature
                 rows so retries don't accumulate duplicate labels).
    - datasets — re-running typically creates new dataset *versions*, not
                 duplicate datasets. Re-run with that in mind.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from deriva_ml import DerivaML

# Reuse the sibling schema template for the schema phase. If you copied
# setup_domain_model_template.py to _<project>_schema.py, update this import
# to match. (Kept as a stub-with-import here so the template reads as one
# coherent unit; split into modules in your real loader if you prefer.)
try:
    from setup_domain_model_template import bootstrap_catalog, setup_domain_model
except ImportError:  # template copied without its sibling — define stubs inline
    bootstrap_catalog = None  # type: ignore[assignment]
    setup_domain_model = None  # type: ignore[assignment]


# ============================================================================
# PHASE 1 — SCHEMA. Idempotent. Delegates to the schema template.
# ============================================================================


def setup_schema_phase(ml: DerivaML) -> None:
    """Install the domain model (vocab, asset table, element type, feature).

    Idempotent — check-before-create throughout. See the sibling
    ``setup_domain_model_template.py`` for the worked implementation.

    Args:
        ml: Connected ``DerivaML`` instance.
    """
    if setup_domain_model is None:
        # TODO: your domain — copy setup_domain_model_template.py alongside
        # this file (or inline its body here) and wire it up.
        raise NotImplementedError(
            "Copy setup_domain_model_template.py next to this loader and fill "
            "its TODO blocks, then import setup_domain_model from it."
        )
    setup_domain_model(ml)


# ============================================================================
# PHASE 2 — ASSETS. Mostly idempotent.
# The canonical ingest is TWO STAGES IN ONE EXECUTION:
#   2a. add_files(...)        — register the SOURCE files BY REFERENCE as
#                               execution INPUTS (provenance: "where did
#                               these bytes come from"). No Hatrac copy.
#   2b. asset_file_path(...)  — upload the bytes INTO Hatrac as typed asset
#                               rows, recorded as execution OUTPUTS.
#   then commit_output_assets() AFTER the with-block flushes the uploads.
#
# Do NOT re-implement the file-ingest mechanics here. The bundled templates
# in /deriva-ml:work-with-assets own them:
#   - register_files_template.py  (the add_files INPUT-registration path)
#   - upload_asset.py             (the asset_file_path OUTPUT-upload path)
# Copy those for the heavy lifting; this function just shows the shape.
#
# Prerequisite: the add_files directory-tree nesting needs
# deriva-ml >= 1.51.14 (below that you get flat sibling File datasets with
# no common parent). Pin it in your pyproject.toml.
# ============================================================================


def run_assets_phase(ml: DerivaML) -> dict[str, Any]:
    """Register source files as inputs, then upload bytes as output assets.

    The two stages share ONE execution so the uploaded assets carry
    provenance back to the exact source files they were derived from.

    Args:
        ml: Connected ``DerivaML`` instance (schema phase already run).

    Returns:
        A stats dict (counts of files registered / assets uploaded).
    """
    from pathlib import Path

    from deriva_ml.core.filespec import FileSpec
    from deriva_ml.execution import ExecutionConfiguration

    # TODO: your domain — where your raw source files live, and the asset
    # table + types they upload into. Stage the exact subset you mean to
    # register under a clean root first (symlinks avoid a second byte copy)
    # so the registered provenance equals exactly what you upload.
    source_dir = Path("TODO/path/to/source/files")
    asset_table = "My_Asset"  # TODO: matches setup_domain_model
    workflow_type = "Data_Load"  # TODO: a Workflow_Type term

    workflow = ml.create_workflow(
        name=f"Load {asset_table} assets",
        workflow_type=workflow_type,
        description=f"Register source files and upload them as {asset_table} assets",
    )
    config = ExecutionConfiguration(workflow=workflow)

    registered = 0
    uploaded = 0
    with ml.create_execution(config) as exe:
        # --- Stage 2a: register source files BY REFERENCE as INPUTS ---------
        # See work-with-assets/register_files_template.py for the full
        # treatment (FileSpec.create_filespecs walks recursively, computes
        # MD5 + length; add_files inserts File rows + links them as inputs +
        # returns a nested Dataset mirroring the directory tree).
        specs = list(
            FileSpec.create_filespecs(
                source_dir,
                description="Source files (pre-upload reference)",
                file_types=[asset_table],  # TODO: your Asset_Type tag(s)
            )
        )
        root_ds = exe.add_files(specs, description="Source files as execution inputs")
        registered = len(specs)
        print(f"  Registered {registered} source files as inputs "
              f"(root File dataset {root_ds.dataset_rid})")

        # --- Stage 2b: upload the bytes INTO Hatrac as OUTPUT assets --------
        # See work-with-assets/upload_asset.py for the full treatment.
        for src_path in specs_to_paths(source_dir):
            exe.asset_file_path(
                asset_name=asset_table,
                file_name=str(src_path),
                asset_types=[asset_table],  # TODO: your Asset_Type tag(s)
                copy_file=True,
            )
            uploaded += 1

    # commit_output_assets runs AFTER the with-block: it uploads the staged
    # bytes to Hatrac, writes the asset rows, and tags them Output_File.
    report = exe.commit_output_assets(clean_folder=True)
    print(f"  Uploaded {report.total_uploaded} asset(s), {report.total_failed} failed.")

    # TODO: your domain — add the per-row features/labels here, typically in
    # a SEPARATE execution for clean annotation provenance (see the CIFAR
    # reference's add_classification_features). Use /deriva-ml:create-feature.

    return {"files_registered": registered, "assets_uploaded": uploaded}


def specs_to_paths(source_dir):  # type: ignore[no-untyped-def]
    """Yield the source file paths under ``source_dir`` (TODO: your walk).

    Placeholder so the template runs as a coherent unit. Replace with the
    actual iteration over your staged source files (the same set you passed
    to ``create_filespecs``).
    """
    from pathlib import Path

    yield from (p for p in Path(source_dir).rglob("*") if p.is_file())


# ============================================================================
# PHASE 3 — DATASETS. Re-running creates new versions, not duplicates.
# ============================================================================


def run_datasets_phase(ml: DerivaML) -> dict[str, str]:
    """Create the Dataset hierarchy and add members.

    Build the Complete / Training / Testing / Split datasets (and any
    subsamples) and populate them. Re-running typically creates new dataset
    *versions* rather than duplicate datasets — plan retries accordingly.

    Args:
        ml: Connected ``DerivaML`` instance (assets phase already run).

    Returns:
        A mapping of dataset name -> RID for the datasets created.
    """
    # TODO: your domain — create datasets and add the asset rows as members.
    # This is /deriva-ml:dataset-lifecycle territory: create_dataset,
    # add_dataset_members, split_dataset, subsample. See the CIFAR reference's
    # _cifar10_datasets.py for a worked Complete -> Split -> Train/Test build.
    raise NotImplementedError(
        "Fill in the dataset hierarchy for your domain — see "
        "/deriva-ml:dataset-lifecycle and the CIFAR _cifar10_datasets.py."
    )


# ============================================================================
# ORCHESTRATOR — route --phase to the right phase function(s).
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--catalog-id", help="Load into an existing catalog.")
    group.add_argument(
        "--create",
        metavar="PROJECT_NAME",
        help="Bootstrap a fresh catalog first (project name = domain schema).",
    )
    parser.add_argument(
        "--domain-schema",
        help="Domain schema name when connecting with --catalog-id "
        "(defaults to the catalog's default schema).",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Run only the schema phase shape; skip data writes.")
    parser.add_argument(
        "--phase",
        choices=["all", "schema", "assets", "datasets"],
        default="all",
        help="Run a single phase to resume after a partial failure. "
        "schema=idempotent; assets=upload+features; datasets=hierarchy. "
        "Default: all.",
    )
    args = parser.parse_args()

    # --- Connect (or create) the catalog ------------------------------------
    if args.create:
        if bootstrap_catalog is None:
            raise NotImplementedError(
                "Copy setup_domain_model_template.py next to this loader so "
                "--create can call bootstrap_catalog."
            )
        ml = bootstrap_catalog(args.hostname, args.create)
        catalog_id = ml.catalog.catalog_id
    else:
        ml = DerivaML(
            hostname=args.hostname,
            catalog_id=str(args.catalog_id),
            domain_schemas={args.domain_schema} if args.domain_schema else None,
            check_auth=True,
        )
        catalog_id = args.catalog_id

    # --- Route --phase ------------------------------------------------------
    if args.phase in ("all", "schema"):
        setup_schema_phase(ml)
        if args.phase == "schema":
            # Echo the catalog id so a --create first run can resume against
            # --catalog-id without re-running just to recover it.
            print(f"\nSchema phase complete. Catalog ID: {catalog_id}")
            print(f"Resume with: --catalog-id {catalog_id} --phase assets")
            return 0

    if args.phase in ("all", "assets") and not args.dry_run:
        run_assets_phase(ml)

    if args.phase in ("all", "datasets") and not args.dry_run:
        run_datasets_phase(ml)

    print(f"\nLoad complete. Catalog ID: {catalog_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
