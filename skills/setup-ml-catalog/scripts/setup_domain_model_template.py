#!/usr/bin/env python3
"""COPY-ME template: the schema phase of a from-scratch DerivaML loader.

This is a template, not a finished script. Copy it into your project's
``src/scripts/`` (e.g. ``src/scripts/_<project>_schema.py``), fill in the
``# TODO: your domain`` blocks for *your* vocabulary / asset table /
feature, commit it (provenance records the git hash), then run via::

    uv run python src/scripts/_<project>_schema.py --hostname HOST --catalog-id ID

There is **no pyproject entry point** for this — it is a one-time loader you
run by hand. Modeled on the CIFAR-10 reference ``_cifar10_schema.py`` in the
external ``deriva-ml-model-template`` repo; generalized for any domain.

When to use:
    The "schema" phase of a from-scratch catalog load (the first of the
    four phases the loader orchestrator runs: schema / register / upload /
    cleanup). Run this once against a fresh or existing ML catalog to install
    your domain model — the vocabulary, the asset table, the dataset
    element-type registration, and the feature — before any data is loaded.

Pattern:
    1. (Optional bootstrap) ``create_ml_catalog`` to make a fresh catalog,
       then ``set_catalog_provenance`` to record how it was created.
    2. ``create_vocabulary`` + ``add_term`` to install the controlled
       vocabulary your feature/labels draw from.
    3. ``create_asset`` to create the domain asset table (the thing you
       will upload bytes into in the upload phase).
    4. ``add_dataset_element_type`` to make that asset table a first-class
       dataset member type.
    5. ``create_feature`` to define the per-row labels/scores attached to
       the asset table.
    6. ``add_term`` for the loader's Workflow_Type / Dataset_Type terms that
       are not built in (so the register/upload phases' workflow types and the
       source File dataset's type resolve on a fresh catalog).

Idempotency:
    Every step is check-before-create, mirroring the CIFAR reference's
    ``setup_domain_model``. Re-running against a catalog that already has
    the schema is safe — existing vocabularies, terms, the asset table,
    and the feature are detected and skipped. This is what makes
    ``--phase schema`` resumable in the orchestrator.
"""

from __future__ import annotations

import argparse
import sys

from deriva_ml import DerivaML

# ColumnDefinition + BuiltinTypes live in deriva-ml's core model modules —
# the exact import path the CIFAR reference uses. ColumnDefinition describes
# extra (non-vocabulary) feature columns; BuiltinTypes enumerates the ermrest
# column types (float4, text, int4, boolean, ...).
from deriva_ml.core.ermrest import ColumnDefinition
from deriva_ml.core.enums import BuiltinTypes


# ============================================================================
# OPTIONAL BOOTSTRAP — create the catalog itself.
# Use this only when starting from nothing (no catalog yet). If you already
# have a catalog id, skip straight to setup_domain_model() and connect with a
# plain DerivaML(...). The orchestrator template (loader_orchestrator_template.py)
# calls one or the other depending on --create vs --catalog-id.
# ============================================================================


def bootstrap_catalog(hostname: str, project_name: str) -> DerivaML:
    """Create a fresh ML catalog and record its provenance.

    Creates an empty ERMrest catalog, applies the deriva-ml ACL policy,
    installs the full deriva-ml schema, then records *how* the catalog was
    created so the catalog itself remembers its origin.

    Args:
        hostname: Destination server (e.g. ``"ml.example.org"``).
        project_name: Becomes the domain schema name. Lowercase, underscores
            (not dashes), short and recognizable — e.g. ``"kidney_2026"``.

    Returns:
        A connected ``DerivaML`` bound to the new catalog and domain schema.

    Example:
        >>> ml = bootstrap_catalog("ml.example.org", "my_project")  # doctest: +SKIP
        >>> ml.catalog.catalog_id  # doctest: +SKIP
        '42'
    """
    from deriva_ml.schema.create_schema import create_ml_catalog
    from deriva_ml.catalog.provenance import set_catalog_provenance

    catalog = create_ml_catalog(
        hostname=hostname,
        project_name=project_name,  # becomes the domain schema name
        # catalog_alias=project_name,  # optional human-readable alias
    )
    catalog_id = catalog.catalog_id
    print(f"Created catalog {catalog_id} on {hostname}")

    ml = DerivaML(
        hostname=hostname,
        catalog_id=str(catalog_id),
        domain_schemas={project_name},
        check_auth=True,
    )

    set_catalog_provenance(
        ml.catalog,
        name=f"{project_name} ({catalog_id})",
        # TODO: your domain — one-line description of the catalog's purpose.
        description="Brief catalog purpose",
        # The workflow_url is THIS loader script, committed. Recording it now
        # means the catalog remembers how it was set up. Use a committed git
        # URL, not a local path.
        workflow_url="https://github.com/<org>/<repo>/blob/main/src/scripts/load_<project>.py",
    )
    print("Recorded catalog provenance")
    return ml


# ============================================================================
# THE SCHEMA PHASE — install the domain model. Idempotent.
# ============================================================================


def setup_domain_model(ml: DerivaML) -> None:
    """Install the domain vocabulary, asset table, element type, and feature.

    Check-before-create at every step, so re-running on a catalog that
    already has the schema is a no-op for the parts that exist.

    Args:
        ml: Connected ``DerivaML`` instance (domain schema already provisioned
            by ``create_ml_catalog`` / your project name).

    Example:
        >>> ml = DerivaML("ml.example.org", "42", domain_schemas={"my_project"})  # doctest: +SKIP
        >>> setup_domain_model(ml)  # doctest: +SKIP
    """
    # ---- 1. Vocabulary -----------------------------------------------------
    # TODO: your domain — name the controlled vocabulary your feature draws
    # its terms from (CIFAR used "Image_Class" with the 10 class names).
    vocab_name = "My_Label"  # TODO
    vocab_terms: list[tuple[str, str, list[str]]] = [
        # (term_name, description, synonyms)
        # TODO: your domain — list every term. Example shape:
        ("positive", "The positive class", ["pos", "yes"]),
        ("negative", "The negative class", ["neg", "no"]),
    ]

    # Check existing vocabularies across both schemas before creating.
    existing_vocabs = {
        v.name
        for schema in [ml.ml_schema, ml.default_schema]
        for v in ml.model.schemas[schema].tables.values()
        if ml.model.is_vocabulary(v)
    }
    if vocab_name not in existing_vocabs:
        print(f"Creating {vocab_name} vocabulary...")
        ml.create_vocabulary(
            vocab_name=vocab_name,
            comment="TODO: your domain — what this vocabulary classifies",
        )
    else:
        print(f"{vocab_name} vocabulary already exists")

    existing_terms = {t.name for t in ml.list_vocabulary_terms(vocab_name)}
    for term_name, description, synonyms in vocab_terms:
        if term_name not in existing_terms:
            ml.add_term(
                table=vocab_name,
                term_name=term_name,
                description=description,
                synonyms=synonyms,
            )
            print(f"  Added term: {term_name}")
        else:
            print(f"  Term exists: {term_name}")

    # ---- 2. Asset table ----------------------------------------------------
    # TODO: your domain — name the asset table that will hold your binary
    # files (CIFAR used "Image"). Add extra columns via column_defs if your
    # asset rows carry structured metadata beyond the built-in asset columns.
    asset_table = "My_Asset"  # TODO

    existing_tables = {
        t.name for t in ml.model.schemas[ml.default_schema].tables.values()
    }
    if asset_table not in existing_tables:
        print(f"Creating {asset_table} asset table...")
        ml.create_asset(
            asset_name=asset_table,
            column_defs=[],  # TODO: your domain — extra ColumnDefinition(...) if needed
            comment="TODO: your domain — what these assets are",
        )
    else:
        print(f"{asset_table} asset table already exists")

    # ---- 3. Register asset table as a dataset element type -----------------
    # Makes rows of the asset table eligible to be dataset members.
    element_types = {t.name for t in ml.list_dataset_element_types()}
    if asset_table not in element_types:
        print(f"Enabling {asset_table} as a dataset element type...")
        ml.add_dataset_element_type(asset_table)

    # ---- 4. Feature --------------------------------------------------------
    # TODO: your domain — the per-row label/score attached to asset rows.
    # `terms` lists vocabulary columns; `metadata` lists extra typed columns
    # (ColumnDefinition); `optional` names columns that may be null.
    feature_name = "My_Classification"  # TODO
    confidence_column = ColumnDefinition(
        name="Confidence",
        type=BuiltinTypes.float4,
        nullok=True,
        comment="Prediction confidence/probability (0-1)",
    )
    try:
        ml.create_feature(
            target_table=asset_table,
            feature_name=feature_name,
            comment="TODO: your domain — what this feature records",
            terms=[vocab_name],
            metadata=[confidence_column],
            optional=["Confidence"],
        )
        print(f"Created {feature_name} feature")
    except Exception as e:  # noqa: BLE001
        # create_feature raises if the feature already exists — treat that as
        # idempotent success, re-raise anything else.
        if "already exists" in str(e).lower():
            print(f"{feature_name} feature already exists")
        else:
            raise

    # ---- 5. Loader vocabulary terms (Workflow_Type / Dataset_Type) ---------
    # The two-step loader (loader_orchestrator_template.py + register/upload
    # phases) tags its workflows and its source File dataset with terms that
    # are NOT built in to a fresh deriva-ml catalog — `initialize_ml_schema`
    # seeds Workflow_Type {Ingest, Training, Testing, Prediction, ...} and
    # Dataset_Type {File, Directory, Complete, Training, Labeled, ...}, but not
    # `Source_Registration` / `Asset_Upload` / `Data_Load` / `Source`. Without
    # this step, `create_workflow(workflow_type=...)` and
    # `add_files(dataset_types=[...])` fail term lookup on the default copy-me
    # path. Seed them here (idempotent — add_term is check-before-create at the
    # catalog level).
    #
    # TODO: keep these names in sync with the orchestrator config
    # (FILE_DATASET_TYPE) and the phase templates' workflow_type= values. If you
    # prefer the built-ins, set the loader to use `Ingest` (Workflow_Type) and
    # `File` (Dataset_Type) and you can drop the matching rows below.
    loader_workflow_types = [
        ("Source_Registration", "Register source files by reference (register phase)."),
        ("Asset_Upload", "Upload source bytes into Hatrac as assets (upload phase)."),
        ("Data_Load", "Attach per-row features/labels to uploaded assets."),
    ]
    loader_dataset_types = [
        ("Source", "A by-reference File dataset of registered source files."),
    ]
    existing_wf_types = {t.name for t in ml.list_vocabulary_terms("Workflow_Type")}
    for name, desc in loader_workflow_types:
        if name not in existing_wf_types:
            ml.add_term(table="Workflow_Type", term_name=name, description=desc)
            print(f"  Added Workflow_Type term: {name}")
    existing_ds_types = {t.name for t in ml.list_vocabulary_terms("Dataset_Type")}
    for name, desc in loader_dataset_types:
        if name not in existing_ds_types:
            ml.add_term(table="Dataset_Type", term_name=name, description=desc)
            print(f"  Added Dataset_Type term: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hostname", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--catalog-id", help="Install into an existing catalog.")
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
                        help="Print what would be created without writing.")
    args = parser.parse_args()

    if args.create:
        if args.dry_run:
            print(f"[dry-run] Would create catalog '{args.create}' on {args.hostname}")
            return 0
        ml = bootstrap_catalog(args.hostname, args.create)
    else:
        ml = DerivaML(
            hostname=args.hostname,
            catalog_id=str(args.catalog_id),
            domain_schemas={args.domain_schema} if args.domain_schema else None,
            check_auth=True,
        )

    if args.dry_run:
        print("[dry-run] Would install domain vocabulary, asset table, "
              "element type, and feature (fill the TODO blocks first).")
        return 0

    setup_domain_model(ml)
    print("Schema phase complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
