# Two-Step Register/Upload Ingest Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the v1.11.5 one-execution ingest templates/guidance with a CIFAR-agnostic, two-execution (register + upload) loader template set + corrected skill prose, modeled on the current `deriva-ml-cifar-example`.

**Architecture:** Per-stage copy-me templates in `skills/setup-ml-catalog/scripts/` — a thin orchestrator (`--phase {all,schema,register,upload,cleanup}`) plus `stage_source` (stubbed source layer with a layout contract), `register_phase` (Exec 1: `add_files` → File dataset), `upload_phase` (Exec 2a `asset_file_path`+commit → hosted assets, consuming the File dataset as a `materialize=False` Input; Exec 2b `add_features`). Configurability via a config block + the `stage_source()` contract; dataset organization is handed off to `/deriva-ml:dataset-lifecycle` (no `datasets` phase). Correct the "one execution" claim in `setup-ml-catalog` and `work-with-assets`.

**Tech Stack:** Python copy-me templates + Claude Code SKILL.md (Markdown). No unit-test framework — "tests" are `py_compile` + grep conformance checks (CIFAR-agnostic, signature-faithful, no dangling pointers).

## Global Constraints

- **4 phases only:** `schema` / `register` / `upload` / `cleanup`. NO `datasets` phase — hand off to `/deriva-ml:dataset-lifecycle`.
- **Two executions for ingest:** `register` is its own execution (`add_files`, by-reference File dataset, Input). `upload` is a separate execution (2a: `asset_file_path`+`commit_output_assets`, hosted assets, Output; 2b: `add_features`). The upload execution declares the register File dataset as a `DatasetSpec(rid=..., version=..., materialize=False)` **Input** — this is the source→upload lineage edge. `materialize=False` is REQUIRED (tag:// URLs can't materialize).
- **CIFAR-agnostic:** templates contain NO `cifar`, `toronto`, `train_`, `pickle`, or CIFAR class names except as clearly-labeled "(e.g., CIFAR …)" comment citations.
- **Verified deriva-ml signatures** (use exactly): `FileSpec.create_filespecs(path, description, file_types)`; `exe.add_files(files, dataset_types=None, description="", chunk_size=500, *, root_name=None)`; `DatasetSpec(rid=..., version=..., materialize=False)`; `exe.asset_file_path(asset_name, file_name, asset_types=[...], copy_file=True, rename_file=...)`; `exe.commit_output_assets(clean_folder=True)`; `exe.add_features(records)`; `ml.lookup_dataset(rid)`; `dataset.list_dataset_children()`; `dataset.list_dataset_members()`; `ml.find_datasets(sort=True)`; `ml.create_workflow(name=, workflow_type=, description=)`; `ExecutionConfiguration(workflow=, datasets=[...])`; `with ml.create_execution(config) as exe:`.
- **Config block keys** (shared, top of orchestrator): `SOURCE_ROOT` (Path), `PARTITIONS` (list[str]; `["."]` = flat), `ASSET_TABLE` (str), `FILE_TYPES` (list[str]), `FILE_DATASET_TYPE` (str), `LABEL_MANIFEST` (str | None), `rename_file(partition, path) -> str` (hook).
- **Version floor:** deriva-ml ≥ 1.51.14 (`add_files` directory nesting) — document as a prerequisite; `materialize=False` documented alongside.
- **House style:** module docstring with "When to use" / "Pattern"; copy-me framing (`uv run python src/scripts/<name>.py`, no pyproject entry point); `# TODO: your domain` / `# TODO: your data source` seams; `if __name__ == "__main__": sys.exit(main())` for the orchestrator.
- **SKILL.md `name`/`description` frontmatter of both `setup-ml-catalog` and `work-with-assets` stay byte-identical.**
- Spec: `docs/superpowers/specs/2026-06-27-two-step-ingest-pipeline.md`.

---

### Task 1: `stage_source_template.py` (the source layer + layout contract)

**Files:**
- Create: `skills/setup-ml-catalog/scripts/stage_source_template.py`

**Interfaces:**
- Produces: `stage_source(source_root: Path, partitions: list[str], label_manifest: str | None = None) -> Path` — stubbed; returns `source_root`. The orchestrator (Task 4) and register phase (Task 2) call it. Defines the **layout contract** every downstream phase relies on.

- [ ] **Step 1: Write the template file.**

```python
#!/usr/bin/env python3
"""COPY-ME template: the data-source layer for a from-scratch load.

`stage_source()` is the ONE place your dataset-specific source logic lives —
download, copy, extract, decode — whatever it takes to land your raw files on
disk in the layout the rest of the loader expects. Everything downstream
(register, upload) is generic and needs no edit for a standard layout.

THE LAYOUT CONTRACT (what stage_source MUST produce):

    SOURCE_ROOT/
        <PARTITION>/        # one subdir per entry in PARTITIONS
            <file>          #   e.g. SOURCE_ROOT/train/img_001.png
            ...
        <LABEL_MANIFEST>    # optional: a labels file at the root, if used

  - PARTITIONS is a list you set in the orchestrator config. Common shapes:
      ["train", "test"]   — a train/test split on the source side
      ["."]               — a flat layout (all files directly under SOURCE_ROOT)
  - If you use a label manifest, write it at SOURCE_ROOT/<LABEL_MANIFEST>
    (e.g. a CSV of filename,label). The register phase registers it as a File
    so the upload phase can read it back across the execution boundary — no
    in-memory label state has to cross executions.

(Worked instance: the CIFAR-10 reference downloads the Toronto archive, decodes
the pickles, and writes sampled PNGs into train/ and test/ plus a labels.csv —
all of that lives in ITS stage_source, none of it here.)
"""

from __future__ import annotations

from pathlib import Path


def stage_source(
    source_root: Path,
    partitions: list[str],
    label_manifest: str | None = None,
) -> Path:
    """Populate ``source_root`` with the files to ingest, per the layout contract.

    Replace the body with your data source. The contract: after this returns,
    each ``source_root/<partition>/`` exists and holds the files to ingest, and
    (if ``label_manifest`` is set) ``source_root/<label_manifest>`` exists.

    Args:
        source_root: Root directory to stage files under (created if absent).
        partitions: Subdirectory names to create under ``source_root``. Use
            ``["."]`` for a flat layout.
        label_manifest: Optional filename to write at ``source_root`` (e.g.
            ``"labels.csv"``); ``None`` if labels come from elsewhere.

    Returns:
        ``source_root`` (now populated).
    """
    source_root = Path(source_root).expanduser()
    source_root.mkdir(parents=True, exist_ok=True)
    for partition in partitions:
        (source_root / partition).mkdir(parents=True, exist_ok=True)

    # TODO: your data source — download / copy / extract / decode your raw
    #   files into source_root/<partition>/ for each partition above. If you
    #   use a label manifest, write it to source_root / label_manifest here.
    raise NotImplementedError(
        "Implement stage_source for your data source — see the layout contract "
        "in this module's docstring."
    )

    return source_root  # noqa: W291  (reached once you remove the raise)
```

- [ ] **Step 2: Verify it compiles.**

Run: `python3 -m py_compile skills/setup-ml-catalog/scripts/stage_source_template.py && echo OK`
Expected: `OK`

- [ ] **Step 3: Verify CIFAR-agnostic (CIFAR only in the parenthetical citation).**

Run: `grep -niE "cifar|toronto|pickle|train_" skills/setup-ml-catalog/scripts/stage_source_template.py`
Expected: only the one "Worked instance: the CIFAR-10 reference …" comment line; no code uses these.

- [ ] **Step 4: Commit.**

```bash
git add skills/setup-ml-catalog/scripts/stage_source_template.py
git commit -m "feat(setup-ml-catalog): stage_source template + layout contract"
```

---

### Task 2: `register_phase_template.py` (Exec 1 — add_files → File dataset)

**Files:**
- Create: `skills/setup-ml-catalog/scripts/register_phase_template.py`

**Interfaces:**
- Consumes: `stage_source(source_root, partitions, label_manifest)` from Task 1.
- Produces: `run_register_phase(ml, source_root: Path, partitions: list[str], file_dataset_type: str, file_types: list[str], label_manifest: str | None = None, root_name: str = "source") -> str` — returns the root File dataset RID. The orchestrator (Task 4) and upload phase (Task 3) rely on this RID.

- [ ] **Step 1: Write the template file.**

```python
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
```

- [ ] **Step 2: Verify it compiles.**

Run: `python3 -m py_compile skills/setup-ml-catalog/scripts/register_phase_template.py && echo OK`
Expected: `OK`

- [ ] **Step 3: Verify CIFAR-agnostic.**

Run: `grep -niE "cifar|toronto|pickle|train_|\bclass\b" skills/setup-ml-catalog/scripts/register_phase_template.py`
Expected: no `cifar`/`toronto`/`pickle`/`train_` hits.

- [ ] **Step 4: Commit.**

```bash
git add skills/setup-ml-catalog/scripts/register_phase_template.py
git commit -m "feat(setup-ml-catalog): register-phase template (Exec 1, add_files File dataset)"
```

---

### Task 3: `upload_phase_template.py` (Exec 2a upload + Exec 2b features)

**Files:**
- Create: `skills/setup-ml-catalog/scripts/upload_phase_template.py`

**Interfaces:**
- Consumes: the File dataset RID returned by `run_register_phase` (Task 2).
- Produces: `run_upload_phase(ml, source_dataset_rid: str, asset_table: str, asset_types: list[str], partitions: list[str], rename_file=None) -> dict` — returns a stats dict `{"assets_uploaded": int, "features_added": int}`. The orchestrator (Task 4) calls it.

- [ ] **Step 1: Write the template file.**

```python
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
```

- [ ] **Step 2: Verify it compiles.**

Run: `python3 -m py_compile skills/setup-ml-catalog/scripts/upload_phase_template.py && echo OK`
Expected: `OK`

- [ ] **Step 3: Verify the lineage-edge essentials are present.**

Run: `grep -c "materialize=False" skills/setup-ml-catalog/scripts/upload_phase_template.py && grep -c "commit_output_assets" skills/setup-ml-catalog/scripts/upload_phase_template.py`
Expected: both ≥ 1.

- [ ] **Step 4: Verify CIFAR-agnostic.**

Run: `grep -niE "cifar|toronto|pickle|train_" skills/setup-ml-catalog/scripts/upload_phase_template.py`
Expected: only the `_truncate_loader_classification_rows` CIFAR citation comment; no code uses these.

- [ ] **Step 5: Commit.**

```bash
git add skills/setup-ml-catalog/scripts/upload_phase_template.py
git commit -m "feat(setup-ml-catalog): upload-phase template (Exec 2a upload + 2b features, materialize=False input)"
```

---

### Task 4: `loader_orchestrator_template.py` (rework `phased_loader_template.py`) + delete the old file

**Files:**
- Create: `skills/setup-ml-catalog/scripts/loader_orchestrator_template.py`
- Delete: `skills/setup-ml-catalog/scripts/phased_loader_template.py`

**Interfaces:**
- Consumes: `run_register_phase` (Task 2), `run_upload_phase` (Task 3), and `setup_domain_model` / `bootstrap_catalog` from the existing `setup_domain_model_template.py`.
- Produces: the config block (the seven keys from Global Constraints) + a `--phase {all,schema,register,upload,cleanup}` `main()`.

- [ ] **Step 1: Write the orchestrator template** (config block + 4-phase router; threads the File-dataset RID register→upload; discovers it via `find_datasets` when upload runs standalone; hand-off banner to dataset-lifecycle).

```python
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
```

- [ ] **Step 2: Delete the superseded single-file template.**

```bash
git rm skills/setup-ml-catalog/scripts/phased_loader_template.py
```

- [ ] **Step 3: Verify the orchestrator compiles.**

Run: `python3 -m py_compile skills/setup-ml-catalog/scripts/loader_orchestrator_template.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Verify the 4-phase set + config block + handoff are present and the datasets phase is gone.**

Run: `grep -E 'choices=\[|"\.\"\]|PARTITIONS|dataset-lifecycle' skills/setup-ml-catalog/scripts/loader_orchestrator_template.py | head` then `grep -c "datasets" skills/setup-ml-catalog/scripts/loader_orchestrator_template.py`
Expected: choices line shows `all,schema,register,upload,cleanup` (no `datasets`); PARTITIONS + dataset-lifecycle handoff present; "datasets" appears only in the handoff prose, not as a phase choice.

- [ ] **Step 5: Verify CIFAR-agnostic.**

Run: `grep -niE "cifar|toronto|pickle|train_" skills/setup-ml-catalog/scripts/loader_orchestrator_template.py`
Expected: no hits (the `PARTITIONS = ["train", "test"]` default uses the strings "train"/"test" but not `train_`; confirm the grep for `train_` is clean — the default partition names are fine as generic example values, but flag if a reviewer wants them generic).

- [ ] **Step 6: Commit.**

```bash
git add skills/setup-ml-catalog/scripts/loader_orchestrator_template.py
git commit -m "feat(setup-ml-catalog): loader orchestrator template (4-phase, two-execution); remove phased_loader_template"
```

---

### Task 5: Correct the skill prose (`setup-ml-catalog` + `work-with-assets`)

**Files:**
- Modify: `skills/setup-ml-catalog/SKILL.md` (Step 4 section + phase table + template pointers + Related Skills)
- Modify: `skills/work-with-assets/SKILL.md` (the "two stages in one execution" line)

**Interfaces:**
- Consumes: the template filenames created in Tasks 1–4 (`loader_orchestrator_template.py`, `stage_source_template.py`, `register_phase_template.py`, `upload_phase_template.py`).

- [ ] **Step 1: Rewrite the `setup-ml-catalog` phase table** (replace the `### Step 4` table). Replace the existing three-row table (schema/assets/datasets) and the `--phase {all,schema,assets,datasets}` sentence with:

```markdown
The bundled **`scripts/loader_orchestrator_template.py`** gives you a copy-me four-phase orchestrator. It is the recommended shape for any from-scratch loader:

| Phase | What it does | Idempotent? |
|-------|-------------|-------------|
| **schema** | Creates the domain tables, asset table, feature, workflow/dataset types, Chaise annotations. | Yes — re-running on a catalog that already has the schema is safe. |
| **register** | Stages the source directory, then `exe.add_files(...)` records the files as a by-reference **File dataset** (Input provenance; bytes NOT uploaded). Its own execution. | Re-running creates a new File dataset version. |
| **upload** | Consumes the File dataset as a `DatasetSpec(materialize=False)` **Input**, uploads the bytes into Hatrac as hosted assets (Output), then adds features. Its own execution(s). | Mostly — Hatrac uploads are content-addressed; the feature step truncates prior loader rows first. |
| **cleanup** | Removes the local source cache. | Yes. |

The template wires these behind a single `--phase {all,schema,register,upload,cleanup}` switch so a partial failure resumes without re-running earlier phases. `--phase schema` prints the catalog id so a `--create` first run can resume against `--catalog-id`.

Adapt the loader to your dataset by editing its **config block** (`SOURCE_ROOT`, `PARTITIONS` — a list, `["."]` for a flat layout — `ASSET_TABLE`, `FILE_TYPES`, `FILE_DATASET_TYPE`, `LABEL_MANIFEST`, the `rename_file` hook) and filling the `stage_source()` stub in `scripts/stage_source_template.py` (its docstring states the layout contract). The register/upload phases are generic and need no edit for a standard layout. The sibling templates: `scripts/register_phase_template.py` (Exec 1) and `scripts/upload_phase_template.py` (Exec 2).

**Then hand off to `/deriva-ml:dataset-lifecycle`** to organize the now-hosted assets into Complete / Training / Testing datasets, splits, and subsamples — that is its job, not the loader's.
```

- [ ] **Step 2: Rewrite the "canonical ingest" subsection** (the `#### The canonical ingest: register-then-upload in one execution` block). Replace its heading and body with:

```markdown
#### The canonical ingest: register, then upload — two executions

File ingest is **two separate executions**, and the split is what records source→asset lineage in the catalog:

1. **register (Execution 1)** — `FileSpec.create_filespecs(SOURCE_ROOT)` + `exe.add_files(specs, dataset_types=[FILE_DATASET_TYPE], ...)` inserts one `File` row per source file (`tag://` URL + MD5 + length, **no bytes copied**) and links them as **Inputs**, producing a nested File dataset that mirrors the source directory tree. This records *which source files exist*.
2. **upload (Execution 2)** — declares that File dataset as a `DatasetSpec(rid=..., version=..., materialize=False)` **Input**, then `exe.asset_file_path(asset_name=ASSET_TABLE, ...)` + (post-`with`) `exe.commit_output_assets()` uploads the bytes into Hatrac as typed **Output** assets. A second execution then adds the features.

The `materialize=False` Input declaration is the **catalog-recorded lineage edge** from the source File dataset to the upload execution — an uploaded asset traces back to the exact source file it came from. A single execution cannot express this edge; that is why it is two. (`materialize=False` is **required** — the File rows' `tag://` URLs cannot be materialized into a bag.)

Don't re-implement the mechanics — `/deriva-ml:work-with-assets` owns them: `register_files_template.py` (the `add_files` Input path) and `upload_asset.py` (the `asset_file_path` Output path). The loader's `register_phase_template.py` / `upload_phase_template.py` wire them into the two-execution shape.

> **Prerequisite — deriva-ml >= 1.51.14.** The `add_files` directory-tree nesting needs ≥ 1.51.14, and the upload phase's `DatasetSpec(materialize=False)` input requires the same line. Pin it in your `pyproject.toml`.
```

- [ ] **Step 3: Fix the `work-with-assets` "two stages in one execution" line.** Read the lines around it first:

Run: `grep -n "one execution\|two stages\|register-then-upload" skills/work-with-assets/SKILL.md`

Then replace the phrase "a mature loader often does **two stages in one execution**: `add_files` the source directory first (Input provenance for…" — reframe to two executions:

```markdown
A mature loader does this as **two separate executions**: `add_files` the source directory in one execution (Input provenance — *which source files exist*), then in a second execution consume that File dataset as a `DatasetSpec(materialize=False)` input and `asset_file_path` the bytes into Hatrac (Output). The two-execution split is what records source→asset lineage. See `/deriva-ml:setup-ml-catalog` for the combined loader.
```

(Adapt the exact old wording to what `grep` shows — the surrounding sentence may differ slightly.)

- [ ] **Step 4: Update the `setup-ml-catalog` Reference table + Related Skills.** Replace the `phased_loader_template.py` row with rows for `loader_orchestrator_template.py` + `stage_source_template.py` + `register_phase_template.py` + `upload_phase_template.py`. Confirm `/deriva-ml:dataset-lifecycle` is in Related Skills as the hand-off target (add if absent).

- [ ] **Step 5: Verify frontmatter byte-identical + the correction landed + no stale "one execution".**

Run:
```bash
for s in setup-ml-catalog work-with-assets; do
  echo "$s frontmatter diff:" $(git diff skills/$s/SKILL.md | grep -E "^[-+](name:|description:)" | grep -vE "^[-+][-+]" | wc -l)
done
grep -rn "in one execution\|two stages in one" skills/setup-ml-catalog/SKILL.md skills/work-with-assets/SKILL.md
```
Expected: both frontmatter diffs = 0; no "in one execution" / "two stages in one" hits remain.

- [ ] **Step 6: Commit.**

```bash
git add skills/setup-ml-catalog/SKILL.md skills/work-with-assets/SKILL.md
git commit -m "docs(skills): correct ingest guidance to two executions (register + upload); 4-phase loader + dataset-lifecycle handoff"
```

---

### Task 6: Cross-reference sweep + conformance check

**Files:**
- Audit (read-only, then fix any hits): `skills/**`

- [ ] **Step 1: No dangling pointer to the deleted/renamed template.**

Run: `grep -rn "phased_loader_template" skills/`
Expected: NO hits (every reference updated to `loader_orchestrator_template.py`). If any remain, fix and note them.

- [ ] **Step 2: All five loader templates present + compile.**

Run:
```bash
for f in loader_orchestrator stage_source register_phase upload_phase setup_domain_model; do
  p="skills/setup-ml-catalog/scripts/${f}_template.py"
  python3 -m py_compile "$p" 2>&1 && echo "OK $f" || echo "FAIL $f"
done
```
Expected: `OK` for all five (setup_domain_model_template.py already existed).

- [ ] **Step 3: CIFAR-agnostic across the whole new template set.**

Run: `grep -rniE "cifar|toronto|pickle|kriz" skills/setup-ml-catalog/scripts/*.py`
Expected: only clearly-labeled comment citations ("the CIFAR-10 reference …"); no functional code. Review each hit.

- [ ] **Step 4: The two-execution correction is consistent across both skills.**

Run: `grep -rc "two execution\|two separate execution\|materialize=False" skills/setup-ml-catalog/SKILL.md skills/work-with-assets/SKILL.md`
Expected: setup-ml-catalog ≥ 1 and work-with-assets ≥ 1 for the two-execution framing.

- [ ] **Step 5: Commit any sweep fixes** (skip if none).

```bash
git add -A skills/
git commit -m "docs(skills): cross-reference sweep for two-step ingest restructure"
```

---

## Self-Review

**1. Spec coverage:**
- Correct one-execution → two-execution guidance, both skills → Task 5 Steps 2–3. ✓
- 4 phases (schema/register/upload/cleanup), no datasets phase → Task 4 (orchestrator choices) + Task 5 Step 1. ✓
- register = Exec 1 add_files File dataset (Input) → Task 2. ✓
- upload = Exec 2a asset_file_path+commit (Output) consuming File dataset as `materialize=False` Input + Exec 2b add_features → Task 3. ✓
- CIFAR-agnostic templates → Tasks 1–4 each have a CIFAR-agnostic verify step + Task 6 Step 3. ✓
- Config block + stage_source contract → Task 1 (contract) + Task 4 (config block). ✓
- Per-stage module shape (orchestrator + stage_source + register + upload + kept schema) → Tasks 1–4. ✓
- Hand off to dataset-lifecycle → Task 4 (`_print_handoff`) + Task 5 Step 1 + Related Skills (Step 4). ✓
- Keep register_files_template.py / upload_asset.py → unchanged (not in any task = correctly untouched; Task 5 prose references them). ✓
- deriva-ml ≥ 1.51.14 + materialize=False notes → Task 3 (template) + Task 5 Step 2 (prereq blockquote). ✓
- phased_loader_template.py rename/delete + pointer fix → Task 4 Step 2 + Task 6 Step 1. ✓
- Frontmatter byte-identical → Task 5 Step 5. ✓

**2. Placeholder scan:** The `# TODO: your domain` / `# TODO: your data source` seams are intentional template *content* (the user fills them), not plan placeholders — and each is accompanied by the surrounding real code. The `raise NotImplementedError` in stage_source/_add_features is deliberate (forces the user to supply their source/feature logic) and documented. No "TBD"/"fill in later" in the plan's own prose.

**3. Type consistency:** Function signatures are consistent across tasks: `run_register_phase(...) -> str` (Task 2) is consumed as `source_rid` by the orchestrator (Task 4) and passed to `run_upload_phase(ml, source_dataset_rid, asset_table, asset_types, partitions, rename_file)` (Task 3) — call site in Task 4 matches. `stage_source(source_root, partitions, label_manifest)` (Task 1) is called by `run_register_phase` (Task 2) with the same arg order. Config-block names (`SOURCE_ROOT`, `PARTITIONS`, `ASSET_TABLE`, `FILE_TYPES`, `FILE_DATASET_TYPE`, `LABEL_MANIFEST`, `rename_file`) match the Global Constraints list and their use in Task 4. `DatasetSpec(rid=, version=, materialize=False)` consistent between Task 3 and Task 5 prose.
