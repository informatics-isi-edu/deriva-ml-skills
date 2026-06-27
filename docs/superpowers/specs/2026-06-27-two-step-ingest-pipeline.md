# Design: two-step register/upload ingest pipeline (skills + templates)

**Date:** 2026-06-27
**Status:** Draft (awaiting user review)
**Skills touched:** `setup-ml-catalog` (loader templates + Branch 1 prose), `work-with-assets` (script note + the stale "one execution" line). `dataset-lifecycle` is the hand-off target — verified, not edited.

## Problem

The v1.11.5 ingest templates and skill prose teach that registering source
files and uploading their bytes happen **in one execution** (`setup-ml-catalog`
SKILL.md "The canonical ingest: register-then-upload in one execution";
`work-with-assets` "two stages in one execution"; `phased_loader_template.py`'s
single `run_assets_phase`). The **current** `deriva-ml-cifar-example` (on
`main`) has since restructured the pipeline into **two separate executions**:

- a **`register`** phase (its own execution) that stages the source directory and
  calls `exe.add_files(...)` to record the files as a by-reference **File
  dataset** (Input provenance, no Hatrac upload), and
- an **`upload`** phase (its own execution) that consumes that File dataset as a
  `DatasetSpec(materialize=False)` **Input** and calls
  `asset_file_path` + `commit_output_assets` to produce **hosted assets**
  (Output), then adds features.

The two executions are deliberate: the cross-execution Input edge is what records
**source-File-dataset → upload-execution lineage** in the catalog — an `Image`
asset can be traced back to the exact source files it came from. The v1.11.5
one-execution guidance is now **wrong**, and the templates don't match the
structure a user will see in the example.

This change generalizes the new structure into CIFAR-agnostic templates and
corrects the skill prose.

## Goal

1. **Correct** the one-execution guidance → two executions, with the lineage-edge
   rationale, in both `setup-ml-catalog` and `work-with-assets`.
2. Ship **per-stage, CIFAR-agnostic loader templates** mirroring the example's
   module shape (orchestrator + stage_source + register + upload), driven by a
   **config block + a `stage_source()` contract** so they adapt to the directory
   structure natural for the dataset being loaded.
3. End the loader's scope at hosted assets; **hand off** dataset organization to
   `/deriva-ml:dataset-lifecycle`.

Out of scope: any change to `dataset-lifecycle` itself; shipping CIFAR-specific
code; the cifar-example repo (a separate, downstream consumer).

## The pipeline (4 phases)

The loader runs **4 phases** behind one `--phase` switch. (The example has a
5th, `datasets`; we deliberately omit it — see "Hand-off" below.)

| Phase | Executions | What it does | Idempotent? |
|---|---|---|---|
| `schema` | none | catalog + domain tables + asset table + feature + vocab/types | yes (check-before-create) |
| **`register`** | **1** | `stage_source()` → `FileSpec.create_filespecs(SOURCE_ROOT)` → `exe.add_files(...)` → a by-reference **File dataset** (Input provenance; bytes NOT uploaded) | re-running creates a new File dataset version |
| **`upload`** | **2** (2a + 2b) | **2a:** consume the File dataset as `DatasetSpec(materialize=False)` Input → `asset_file_path` + (post-`with`) `commit_output_assets` → **hosted assets (Output)**. **2b:** `add_features` for labels (the same feature-population pattern `/deriva-ml:create-feature` and its `populate_feature_values.py` already document — the template references it rather than reinventing). | mostly (Hatrac content-addressed; 2b truncates prior loader feature rows first) |
| `cleanup` | none | remove the local source cache | yes |

**Why two executions for ingest (the load-bearing correction).** Register's
`add_files` records *which source files* exist (by reference, as Inputs of the
register execution). Upload's `asset_file_path`+`commit_output_assets` records
*which bytes were uploaded to Hatrac* (as Outputs of the upload execution), and
declares the register phase's File dataset as a `DatasetSpec(materialize=False)`
**Input** of the upload execution. That Input declaration is the catalog-recorded
lineage edge from source files to hosted assets. One execution cannot express
this edge — hence two. `materialize=False` is **required** on that input: the
File rows carry `tag://` URLs (by-reference), which cannot be materialized into a
bag.

### Hand-off to `dataset-lifecycle`

Once `upload` finishes, the catalog holds hosted assets + features. Organizing
them into datasets (Complete / Training / Testing, splits, subsamples) is owned
by `/deriva-ml:dataset-lifecycle` and already covered by its bootstrap/split
recipes. The loader does **not** implement a `datasets` phase — it ends at
`upload`/`cleanup` and **hands off**: the `upload` completion banner and the
`setup-ml-catalog` prose point at `/deriva-ml:dataset-lifecycle` as the next
step. This keeps a crisp responsibility line — **loader = raw data into the
catalog as hosted assets; dataset-lifecycle = compose those into datasets** — and
avoids duplicating that skill's surface.

## Template file set

All in `skills/setup-ml-catalog/scripts/`, all CIFAR-agnostic, all copy-me
(config block + `# TODO` seams), all matching the existing template house style
(argparse where applicable, `uv run python src/scripts/<name>.py`, no pyproject
entry point — one-time loaders).

| Template | Role | Status |
|---|---|---|
| `loader_orchestrator_template.py` | thin `--phase {all,schema,register,upload,cleanup}` router; carries the shared config block; threads the File-dataset RID register→upload; discovers it via `ml.find_datasets(...)` when `upload` runs standalone; ends with a hand-off banner → `/deriva-ml:dataset-lifecycle` | **rework** of `phased_loader_template.py` (renamed; 3→4 phase; drop the datasets phase; drop the one-execution framing) |
| `stage_source_template.py` | stubbed `stage_source()` — all `# TODO: your data source`; docstring states the **layout contract** | **new** |
| `register_phase_template.py` | Exec 1: `create_filespecs(SOURCE_ROOT)` → `add_files(dataset_types=[FILE_DATASET_TYPE], root_name=..., file_types=FILE_TYPES)` → File dataset; returns its RID | **new** |
| `upload_phase_template.py` | Exec 2a (`asset_file_path`+`commit_output_assets`, consuming File dataset as `DatasetSpec(materialize=False)` Input) + Exec 2b (`add_features`) | **new** |
| `setup_domain_model_template.py` | schema phase | **keep** (from v1.11.5) |

In `skills/work-with-assets/scripts/`:
- `register_files_template.py` — **keep**, add a docstring note that it is Exec 1
  of the two-execution ingest and cross-link the upload side.
- `upload_asset.py` — **keep** as-is (the generic `asset_file_path` path the upload
  phase builds on).

The current `phased_loader_template.py` is replaced by
`loader_orchestrator_template.py`; the `setup-ml-catalog` SKILL.md pointer to the
old name must be updated (cross-ref the verification step checks).

## Configurability (adapt to any layout)

A user adapts by editing a **config block** + the `stage_source()` stub — never
the phase logic.

```python
SOURCE_ROOT       = Path("~/.cache/<project>/source").expanduser()  # where stage_source lands files
PARTITIONS        = ["train", "test"]   # subdirs under SOURCE_ROOT; ["."] for a flat (no-partition) layout
ASSET_TABLE       = "Image"             # hosted asset table (created in the schema phase)
FILE_TYPES        = ["Image"]           # Asset_Type tag(s) on the registered File rows
FILE_DATASET_TYPE = "Source"            # Dataset_Type term for the register-phase File dataset
LABEL_MANIFEST    = "labels.csv"        # optional; None if labels come from elsewhere
def rename_file(partition, path): return path.name   # hook; identity = keep original filename
```

Flow:
- **register** walks `SOURCE_ROOT` with `create_filespecs` (recursive — picks up
  whatever the `PARTITIONS` subdirs contain) → `add_files`. The nested File
  dataset mirrors the on-disk tree automatically; partitions need no special
  handling beyond existing as subdirs.
- **upload** iterates `PARTITIONS`, pulls each partition child dataset's File
  members (`source_ds.list_dataset_children()` filtered by `source_directory`),
  resolves each `tag://` URL to a local path, and calls
  `asset_file_path(asset_name=ASSET_TABLE, asset_types=FILE_TYPES, rename_file=...)`.
  A flat layout (`PARTITIONS=["."]`) iterates the root.
- **labels** — when `LABEL_MANIFEST` is set, the manifest is registered as a File
  in the register phase and read back from the File dataset in upload (so no
  in-memory label state crosses the execution boundary). A `# TODO` seam covers
  "labels come from filenames / a sidecar / the catalog instead."

**The `stage_source()` contract** (the one place bespoke source logic lives):

> `stage_source()` must populate `SOURCE_ROOT/<each PARTITION>/` with the files to
> ingest and, if `LABEL_MANIFEST` is used, write it into `SOURCE_ROOT`. *How* —
> download, copy, extract, decode — is the user's code. Everything downstream
> (register, upload) is generic and needs no edit for a standard layout.

CIFAR specifics (Toronto URL, pickle decode, the `train_<class>_<stem>.png`
rename, `train`/`test` partition names) are cited as **one worked instance** in
comments — never shipped in the templates.

## Skill-body edits

**`setup-ml-catalog/SKILL.md` (Branch 1):**
- Rewrite "register-then-upload in one execution" → **two executions**, with the
  source→upload lineage-edge rationale and the `materialize=False` requirement.
- Update the phase table to `schema / register / upload / cleanup`; drop
  `datasets`; add the `/deriva-ml:dataset-lifecycle` hand-off line.
- Update template pointers to the new file set (replacing `phased_loader_template.py`).
- Keep the deriva-ml ≥ 1.51.14 floor (still applies to `add_files` nesting); add
  `materialize=False` as a required note on the upload-consumes-File-dataset step.
- `Related Skills`: keep `/deriva-ml:work-with-assets`; add the explicit
  `/deriva-ml:dataset-lifecycle` hand-off.

**`work-with-assets/SKILL.md`:**
- Fix the "two stages in one execution" line — reframe `add_files` (Exec 1, Input)
  and `asset_file_path` (Exec 2, Output) as two executions linked by consuming the
  File dataset. The 3-way decision table stays.

**Frontmatter** of both skills stays byte-identical (the v1.11.5 descriptions
already cover register/upload/ingest triggers; no trigger change needed).

## Verification

- New/reworked templates compile (`py_compile`) and build to verified deriva-ml
  signatures: `add_files(files, dataset_types=, description=, chunk_size=, *, root_name=)`,
  `FileSpec.create_filespecs(path, description, file_types)`,
  `DatasetSpec(rid=, version=, materialize=False)`, `asset_file_path(...)`,
  `commit_output_assets(...)`, `add_features(...)`, `lookup_dataset(...)`,
  `list_dataset_children(...)` — each checked against the library, not assumed.
- **Zero CIFAR-isms** in the new templates: grep for `cifar`, `toronto`, `train_`,
  `pickle`, and the CIFAR class names → empty (CIFAR only as cited comment examples).
- The stale "one execution" claim is gone from both skills (grep).
- The `phased_loader_template.py` → `loader_orchestrator_template.py` rename leaves
  no dangling pointer in any skill (grep).
- The 4-phase set + the dataset-lifecycle hand-off present in `setup-ml-catalog`;
  deriva-ml ≥ 1.51.14 + `materialize=False` notes present.
- Both skills' `name`/`description` frontmatter byte-identical.
- A flat layout (`PARTITIONS=["."]`) is documented as supported (config-block comment).

## Risks / open points

- **More template surface** (+3 files). Mitigated by each being small and
  single-purpose, mirroring what the user sees in the example.
- **The example may keep evolving.** The templates generalize the *structure*
  (two executions, register/upload split, File-dataset-as-Input), which is the
  stable part; CIFAR specifics are not shipped, so example churn in the
  data-source layer doesn't affect the templates.
- **`materialize=False` is version-sensitive** alongside the existing ≥ 1.51.14
  `add_files`-nesting floor; documented as a prerequisite.
