#!/usr/bin/env python3
"""COPY-ME template: thin orchestrator for a two-step (register/upload) load.

Copy this into your project's ``src/scripts/`` (e.g. ``src/scripts/load_<project>.py``),
edit the CONFIG BLOCK below + the sibling templates' TODO seams, commit, then::

    uv run python src/scripts/load_<project>.py --hostname HOST --create PROJECT --phase all

No pyproject entry point — a one-time loader. Modeled on the CIFAR-10 reference
``load_cifar10.py`` (generalized; no CIFAR specifics here).

Four phases behind ``--phase``:
    schema   — catalog + domain tables + asset table + feature + types (idempotent)
    register — stage source dir -> add_files -> by-reference File dataset (Exec 1, Input)
    upload   — consume the File dataset (materialize=False Input) -> upload bytes as
               hosted assets (Exec 2a, Output) -> add features (Exec 2b)
    cleanup  — remove the local source cache

Organizing the hosted assets into datasets (Complete / Training / Testing,
splits, subsamples) is NOT a loader phase — it is handed off to
/deriva-ml:dataset-lifecycle once this loader finishes.

Prerequisite: deriva-ml >= 1.51.14 (add_files nesting + materialize=False input).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from deriva_ml import DerivaML

from register_phase_template import run_register_phase
from upload_phase_template import run_upload_phase

try:
    from setup_domain_model_template import bootstrap_catalog, setup_domain_model
except ImportError:  # copied without its sibling
    bootstrap_catalog = None  # type: ignore[assignment]
    setup_domain_model = None  # type: ignore[assignment]

# ============================================================================
# CONFIG BLOCK — edit these for your dataset's natural layout.
# ============================================================================
SOURCE_ROOT = Path("~/.cache/my_project/source").expanduser()  # where stage_source lands files
PARTITIONS = ["train", "test"]   # subdirs under SOURCE_ROOT; ["."] for a flat layout
ASSET_TABLE = "Image"            # hosted asset table (created in the schema phase)
FILE_TYPES = ["Image"]           # Asset_Type tag(s) on the registered File rows
FILE_DATASET_TYPE = "Source"     # Dataset_Type term for the register-phase File dataset
LABEL_MANIFEST: str | None = "labels.csv"   # None if labels come from elsewhere


def rename_file(partition: str, path: Path) -> str:  # noqa: ARG001
    """Hook: name the uploaded asset file. Identity = keep the original name."""
    return path.name


# ============================================================================
# ORCHESTRATOR
# ============================================================================


def _find_latest_source_dataset_rid(ml: DerivaML) -> str:
    """Discover the most recent register-phase File dataset (standalone upload).

    When ``--phase upload`` runs in isolation, the RID isn't threaded from
    register — find it from the catalog: newest dataset typed FILE_DATASET_TYPE
    whose ``source_directory`` is the root (``"."``).
    """
    candidates = [
        d
        for d in ml.find_datasets(sort=True)  # newest first
        if FILE_DATASET_TYPE in d.dataset_types and d.source_directory == "."
    ]
    if not candidates:
        raise RuntimeError(
            f"No {FILE_DATASET_TYPE} File dataset found — run '--phase register' first."
        )
    return candidates[0].dataset_rid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--catalog-id", help="Load into an existing catalog.")
    group.add_argument("--create", metavar="PROJECT_NAME",
                       help="Bootstrap a fresh catalog (project name = domain schema).")
    parser.add_argument("--domain-schema",
                       help="Domain schema when connecting with --catalog-id.")
    parser.add_argument("--dry-run", action="store_true",
                       help="Run only the schema phase; skip data writes.")
    parser.add_argument("--phase",
                       choices=["all", "schema", "register", "upload", "cleanup"],
                       default="all",
                       help="Run one phase to resume after a partial failure. Default: all.")
    args = parser.parse_args()

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

    source_rid: str | None = None

    if args.phase in ("all", "schema"):
        if setup_domain_model is None:
            raise NotImplementedError(
                "Copy setup_domain_model_template.py next to this loader and "
                "fill its TODO blocks."
            )
        setup_domain_model(ml)
        if args.phase == "schema":
            print(f"\nSchema phase complete. Catalog ID: {catalog_id}")
            print(f"Resume with: --catalog-id {catalog_id} --phase register")
            return 0

    if args.phase in ("all", "register") and not args.dry_run:
        source_rid = run_register_phase(
            ml, SOURCE_ROOT, PARTITIONS, FILE_DATASET_TYPE, FILE_TYPES, LABEL_MANIFEST,
        )
        if args.phase == "register":
            print(f"\nRegister phase complete. File dataset RID: {source_rid}")
            print(f"Resume with: --catalog-id {catalog_id} --phase upload")
            return 0

    if args.phase in ("all", "upload") and not args.dry_run:
        if source_rid is None:
            source_rid = _find_latest_source_dataset_rid(ml)
        run_upload_phase(ml, source_rid, ASSET_TABLE, FILE_TYPES, PARTITIONS, rename_file)
        if args.phase == "upload":
            print(f"\nUpload phase complete. Catalog ID: {catalog_id}")
            _print_handoff()
            return 0

    if args.phase in ("all", "cleanup") and not args.dry_run:
        shutil.rmtree(SOURCE_ROOT, ignore_errors=True)
        print(f"  Cleanup: removed source cache at {SOURCE_ROOT}")
        if args.phase == "cleanup":
            return 0

    print(f"\nLoad complete. Catalog ID: {catalog_id}")
    _print_handoff()
    return 0


def _print_handoff() -> None:
    """Point the user at the next step: organizing assets into datasets."""
    print(
        "\nNext: organize the uploaded assets into datasets "
        "(Complete / Training / Testing, splits, subsamples) with "
        "/deriva-ml:dataset-lifecycle — that is its job, not the loader's."
    )


if __name__ == "__main__":
    sys.exit(main())
