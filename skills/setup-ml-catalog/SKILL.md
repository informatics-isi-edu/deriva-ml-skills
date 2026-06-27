---
name: setup-ml-catalog
description: "Use when a user wants to set up a DerivaML catalog — either from scratch (create a fresh catalog, install the deriva-ml schema, load data programmatically) or from existing data (clone a slice of a source catalog into a new destination catalog with the deriva-ml schema). This is the skill for the bootstrap moment of a deriva-ml catalog, complementary to setup-derivaml-project which sets up the *code* repo that reads from / writes to such a catalog. Triggers on: 'set up an ML catalog', 'create a new ML catalog', 'bootstrap a catalog', 'initialize deriva-ml schema', 'install deriva-ml schema in existing catalog', 'set up a fresh catalog from CIFAR-style data', 'load my data into a new catalog', 'clone a slice into a new catalog', 'clone a dataset to another server', 'cross-institution catalog setup', 'share my dataset as a new catalog', 'spin up a demo catalog from production', 'promote a non-ML catalog to deriva-ml'."
disable-model-invocation: true
---

# Set Up a DerivaML Catalog

This skill covers the **bootstrap moment** for a deriva-ml catalog — getting a working ML catalog populated and ready for `/deriva-ml:dataset-lifecycle`, `/deriva-ml:execution-lifecycle`, and the rest of the lifecycle skills to operate against.

Two entry paths, depending on where your data is coming from:

| Branch | When to use | Key tool |
|--------|-------------|----------|
| **From scratch** | You have raw data (files, CSVs, an external source) and want a fresh catalog populated programmatically. | `create_ml_catalog()` Python helper + a phased loader script (the `load_cifar10` pattern). |
| **From existing data** | You want a new catalog that contains a slice of an existing source catalog — for sharing with collaborators, building a demo catalog from production data, or carving off a self-contained training subset. | `clone_via_bag()` Python API with anchors that define the slice. |

**Complementary skills:**
- `/deriva-ml:setup-derivaml-project` — sets up the *code repo* (uv, pyproject.toml, conventions) that will read/write the catalog. Independent; do these in either order.
- `/deriva-ml:dataset-lifecycle` — once the catalog exists and has data, this is where you start the actual ML work.
- `/deriva:create-table` *(deriva-skills)* — for adding domain-specific tables (Subject, Image, Specimen, etc.) inside whichever ML catalog you set up here.

Once the catalog is up and the domain tables exist, hand off to those skills.

## Why not `clone_catalog`?

There is an MCP tool called `clone_catalog` (and an async variant). It duplicates a whole catalog on the same server at the Deriva layer. It is the right tool for making a working copy, a test catalog, or a same-server whole-catalog mirror — but it is **not the right tool for the workflows in this skill**:

- It can't slice by RID (you get the whole source catalog or nothing, minus optional schema-level excludes).
- It can't cross servers (source and destination must share a host).
- It is not ML-aware. A clone of a non-ML catalog still isn't an ML catalog — the deriva-ml schema and vocabularies are not added.

For "set up a fresh ML catalog from scratch" or "set up a fresh ML catalog populated from existing data," use the branches below.

---

## Prerequisites (both branches)

- **Auth to the destination server.** `deriva-globus-auth-utils login --host <hostname>` for the destination. For Branch 2 you also need read access to the source.
- **A Python environment with `deriva-ml` installed.** `uv add deriva-ml` or `uv sync` from a project that already lists it.
- **A project name** for the destination catalog. This doubles as the domain schema name (where your project-specific tables — Subject, Image, etc. — will live). Lowercase, underscores rather than dashes, short and recognizable. Example: `cifar10_demo`, `kidney_fibrosis_2026`.
- **(Branch 2 only) A clear answer to "what is the slice?"** — see "Step 1: Pick your roots" below.

---

## Branch 1: From scratch

This skill ships **copy-me template scripts** under `scripts/` — copy them into your project's `src/scripts/`, fill the `# TODO: your domain` blocks, commit, and run via `uv run python src/scripts/<name>.py` (no pyproject entry point — these are one-time loaders):

- **`scripts/loader_orchestrator_template.py`** — a four-phase orchestrator (`--phase {all,schema,register,upload,cleanup}`) that wires the two-execution ingest model.
- **`scripts/stage_source_template.py`** — stub for staging the source directory; fill `stage_source()` per its docstring layout contract.
- **`scripts/register_phase_template.py`** — Execution 1: `add_files` source files as a by-reference File dataset.
- **`scripts/upload_phase_template.py`** — Execution 2: consume the File dataset as `DatasetSpec(materialize=False)` Input, upload bytes as Output assets, add features.
- **`scripts/setup_domain_model_template.py`** — the schema-phase body: create the domain vocabulary, the asset table, register it as a dataset element type, and define the feature. Includes an optional `create_ml_catalog` + `set_catalog_provenance` bootstrap for the from-nothing case.

The external `load_cifar10` script in `deriva-ml-model-template` (`src/scripts/load_cifar10.py` + its `_cifar10_schema.py` / `_cifar10_assets.py` / `_cifar10_datasets.py` modules) is the worked **reference implementation** these templates generalize from — read it for a complete, domain-filled example, but start from the bundled templates here.

### Step 1: Create the catalog and install the deriva-ml schema

`create_ml_catalog()` creates an empty ERMrest catalog, applies the deriva-ml ACL policy, installs the deriva-ml schema (all the tables for Dataset / Workflow / Execution / Feature / Asset), and returns the catalog object. One call:

```python
from deriva_ml.schema.create_schema import create_ml_catalog

catalog = create_ml_catalog(
    hostname="ml.example.org",
    project_name="my_project",  # becomes the domain schema name
    # catalog_alias="my-project",  # optional human-readable alias
)
catalog_id = catalog.catalog_id
print(f"Created catalog {catalog_id} on ml.example.org")
```

The catalog is now usable but contains only the deriva-ml schema. Your domain tables don't exist yet.

### Step 2: Connect via `DerivaML` and record provenance

```python
from deriva_ml import DerivaML
from deriva_ml.catalog.provenance import set_catalog_provenance

ml = DerivaML(
    hostname="ml.example.org",
    catalog_id=str(catalog_id),
    domain_schemas={"my_project"},
    check_auth=True,
)

set_catalog_provenance(
    ml.catalog,
    name=f"My Project ({catalog_id})",
    description="Brief catalog purpose",
    workflow_url="https://github.com/<org>/<repo>/blob/main/scripts/load_my_data.py",
)
```

The `workflow_url` is **the script that's about to populate the catalog**. Recording it now means the catalog itself remembers how it was set up. Use a committed git URL, not a local path.

### Step 3: Create your domain tables

These are the project-specific tables — `Subject`, `Image`, `Specimen`, etc. The deriva-ml schema doesn't know about them; you create them in the domain schema (which `create_ml_catalog` already provisioned, named after `project_name`).

This is `/deriva:create-table` territory — that skill has the worked recipes for standard tables, asset tables, and association tables. The pattern for the schema phase of your loader:

```python
def setup_domain_model(ml: DerivaML) -> None:
    """Create Subject, Image, and the associations between them."""
    # Use the schema operations from the deriva-skills `/deriva:create-table`
    # skill — same `create_table` / `add_column` / FK-definition pattern.
    ...
```

The bundled **`scripts/setup_domain_model_template.py`** is a runnable, idempotent (check-before-create) version of this — copy it and fill the `# TODO: your domain` blocks for your vocabulary, asset table, element type, and feature. `load_cifar10`'s `_cifar10_schema.py` is the worked CIFAR-10 example it generalizes from.

### Step 4: Phase your loader

The bundled **`scripts/loader_orchestrator_template.py`** gives you a copy-me four-phase orchestrator. It is the recommended shape for any from-scratch loader:

| Phase | What it does | Idempotent? |
|-------|-------------|-------------|
| **schema** | Creates the domain tables, asset table, feature, workflow/dataset types, Chaise annotations. | Yes — re-running on a catalog that already has the schema is safe. |
| **register** | Stages the source directory, then `exe.add_files(...)` records the files as a by-reference **File dataset** (Input provenance; bytes NOT uploaded). Its own execution. | Re-running creates a new File dataset version. |
| **upload** | Consumes the File dataset as a `DatasetSpec(materialize=False)` **Input**, uploads the bytes into Hatrac as hosted assets (Output), then adds features. Two executions — asset upload (2a), then features (2b). | Mostly — Hatrac uploads are content-addressed. The feature step (2b) ships as a `_add_features` stub; when you implement it, truncate prior loader feature rows first (the pattern is in the stub's comments) so retries don't duplicate labels. |
| **cleanup** | Removes the local source cache. | Yes. |

The template wires these behind a single `--phase {all,schema,register,upload,cleanup}` switch so a partial failure resumes without re-running earlier phases. `--phase schema` prints the catalog id so a `--create` first run can resume against `--catalog-id`.

Adapt the loader to your dataset by editing its **config block** (`SOURCE_ROOT`, `PARTITIONS` — a list, `["."]` for a flat layout — `ASSET_TABLE`, `FILE_TYPES`, `FILE_DATASET_TYPE`, `LABEL_MANIFEST`, the `rename_file` hook) and filling the `stage_source()` stub in `scripts/stage_source_template.py` (its docstring states the layout contract). The register/upload phases are generic and need no edit for a standard layout. The sibling templates: `scripts/register_phase_template.py` (Exec 1) and `scripts/upload_phase_template.py` (Exec 2).

**Then hand off to `/deriva-ml:dataset-lifecycle`** to organize the now-hosted assets into Complete / Training / Testing datasets, splits, and subsamples — that is its job, not the loader's.

#### The canonical ingest: register, then upload — two executions

File ingest is **two separate executions**, and the split is what records source→asset lineage in the catalog:

1. **register (Execution 1)** — `FileSpec.create_filespecs(SOURCE_ROOT)` + `exe.add_files(specs, dataset_types=[FILE_DATASET_TYPE], ...)` inserts one `File` row per source file (`tag://` URL + MD5 + length, **no bytes copied**) and links them as **Inputs**, producing a nested File dataset that mirrors the source directory tree. This records *which source files exist*.
2. **upload (Execution 2)** — declares that File dataset as a `DatasetSpec(rid=..., version=..., materialize=False)` **Input**, then `exe.asset_file_path(asset_name=ASSET_TABLE, ...)` + (post-`with`) `exe.commit_output_assets()` uploads the bytes into Hatrac as typed **Output** assets. A second execution then adds the features.

The `materialize=False` Input declaration is the **catalog-recorded lineage edge** from the source File dataset to the upload execution — an uploaded asset traces back to the exact source file it came from. A single execution cannot express this edge; that is why it is two. (`materialize=False` is **required** — the File rows' `tag://` URLs cannot be materialized into a bag.)

Don't re-implement the mechanics — `/deriva-ml:work-with-assets` owns them: `register_files_template.py` (the `add_files` Input path) and `upload_asset.py` (the `asset_file_path` Output path). The loader's `register_phase_template.py` / `upload_phase_template.py` wire them into the two-execution shape.

> **Prerequisite — deriva-ml >= 1.51.14.** The `add_files` directory-tree nesting needs ≥ 1.51.14, and the upload phase's `DatasetSpec(materialize=False)` input requires the same line. Pin it in your `pyproject.toml`.

### Step 5: Verify

After the loader finishes, sanity-check from a fresh `DerivaML(...)` session:

```python
ml = DerivaML(hostname=..., catalog_id=..., domain_schemas={"my_project"})

# The five seeded built-in vocabularies should be populated
for v in ["Asset_Type", "Asset_Role", "Workflow_Type", "Dataset_Type", "Execution_Status"]:
    terms = list_vocabulary_terms(hostname=..., catalog_id=..., schema="deriva-ml", table=v)
    print(f"{v}: {len(terms)} terms")

# At least one Dataset, Workflow, Execution should exist (if the loader created them)
print(ml.find_datasets())
print(ml.find_workflows())
```

If `find_datasets()` returns nothing and you expected hosted assets, check that the `upload` phase ran and committed — check the loader logs. Datasets themselves (grouping uploaded assets) are created via `/deriva-ml:dataset-lifecycle`, not by this loader.

---

## Branch 2: From existing data (clone a slice)

This branch produces a destination catalog populated from a source catalog. The destination ends up self-contained (its own catalog ID, its own schema, its own data) and intentionally smaller — only the slice you asked for makes it across.

The tool is **`clone_via_bag()`** (Python API only — no MCP wrapper). It runs a two-step pipeline: walk the source from a set of anchors and write a bag to disk, then load that bag into the destination. The bag in the middle is real (an on-disk artifact you can inspect, re-load, or archive separately), which makes the operation debuggable and resumable.

The destination catalog must already exist. Create it first (Branch 1 Step 1 + 2, then skip the data-loading steps).

**Decide before you start — what is the slice?** The anchors decide what makes it into the slice: the walker traverses FK closure from each anchor, so everything reachable is included and everything not reachable is excluded. Three things shape the result, and you should have an answer to each before running:

- **Roots** — the 90% case is one Dataset (`root_rid="1-ABCD"`). Other shapes (several Datasets pooled, all data for specific Subjects/Experiments, everything from a Workflow) use explicit `RIDAnchor` lists.
- **Asset mode** — `AssetMode.UPLOAD_IF_MISSING` (default) makes the destination self-contained with its own Hatrac bytes; `AssetMode.ROWS_ONLY` references the source's Hatrac (only safe when source and destination share a Hatrac).
- **Provenance is not a knob** — the slice **always** pulls in the producing executions, their workflows, and the upstream datasets they consumed, recursively. This is why a slice can be larger than expected, and why partial provenance is not an option (`clone_via_bag` builds a *working* ML catalog, not a viewing snapshot).

The defaults (`UPLOAD_IF_MISSING`, complete-provenance `terminal_tables`, `DanglingFKStrategy.DELETE`) are tuned to produce a working ML catalog — override only with reason.

**Full step-by-step recipe → `references/clone-via-bag.md`.** Steps 1-8 (pick roots / `RIDAnchor` table, provenance mechanism + `terminal_tables`, asset-mode decision, dangling-FK behavior, slice size, running the clone, promoting a non-ML source, verifying lineage) and the Branch-2-specific failure modes all live there. Read it once you've chosen this branch.

---

## Failure modes (both branches)

- **Auth errors** during `create_ml_catalog` or `clone_via_bag`: re-run `deriva-globus-auth-utils login --host <hostname>` for both source and destination if Branch 2. (Most common failure.)
- **Branch 1 schema phase fails partway**: the script is idempotent for `--phase schema`. Re-run that phase only — don't re-run `--phase all`.
- **Branch 2 deep failure modes** (bag-build partial-resume, dangling-FK errors under `FAIL`, `create_ml_schema` "schema already exists"): see "Branch 2 failure modes" in `references/clone-via-bag.md`.

---

## Reference

| Tool / helper | Where | Purpose |
|---|---|---|
| `create_ml_catalog(hostname, project_name, catalog_alias=None)` | `deriva_ml.schema.create_schema` (Python) | Create a fresh catalog with ACLs + deriva-ml schema in one call. Branch 1 entry point. |
| `create_ml_schema(catalog, schema_name="deriva-ml", project_name=None)` | `deriva_ml.schema.create_schema` (Python) | Add the deriva-ml schema to an existing catalog. **DROPS** the schema with CASCADE if already present. Use for promoting a plain Deriva catalog to deriva-ml. |
| `initialize_ml_schema(model, schema_name="deriva-ml")` | `deriva_ml.schema.create_schema` (Python) | Populate the five seeded standard vocabularies (Asset_Type, Asset_Role, Dataset_Type, Workflow_Type, Execution_Status). Safe to call repeatedly. (`Feature_Name` is a sixth vocabulary table, populated per-feature at runtime by `create_feature` — not seeded here.) |
| `set_catalog_provenance(catalog, name, description, workflow_url)` | `deriva_ml.catalog.provenance` (Python) | Record how the catalog was created. Call once after `create_ml_catalog`. |
| `clone_via_bag(source_hostname, source_catalog_id, dest_hostname, dest_catalog_id, root_rid=None, anchors=None, output_dir=None, policy=None)` | `deriva_ml.catalog.clone_via_bag` (Python) | Slice-clone. Branch 2 entry point. |
| `RIDAnchor(table, rids)` | `deriva.bag.anchors` (Python) | Specify slice roots by table + RID list. |
| `FKTraversalPolicy(asset_mode, dangling_fk_strategy, ...)` | `deriva.bag.traversal` (Python) | Override `clone_via_bag` defaults. The deriva-ml defaults are usually right; override only with reason. |
| `AssetMode.UPLOAD_IF_MISSING` / `AssetMode.ROWS_ONLY` | `deriva.bag.traversal` (Python) | Whether the destination gets its own asset bytes or references the source's Hatrac. |
| `DanglingFKStrategy.DELETE` / `FAIL` / `NULLIFY` | `deriva.bag.traversal` (Python) | What to do with orphan FK rows at load time. |
| `clone_catalog` / `clone_catalog_async` | `deriva-mcp-core` MCP | Whole-catalog same-server clone. **Not for this skill's workflows** — see "Why not `clone_catalog`?" above. |
| `loader_orchestrator_template.py` | this skill's `scripts/` | **Copy-me four-phase orchestrator** for Branch 1 (`--phase {all,schema,register,upload,cleanup}`). Fill the config block and the `stage_source_template.py` stub. |
| `stage_source_template.py` | this skill's `scripts/` | Stub for staging the source directory before registration. Fill the `stage_source()` body; the docstring states the layout contract. |
| `register_phase_template.py` | this skill's `scripts/` | Execution 1 — `add_files` source files as a by-reference File dataset (Input provenance; no bytes copied). |
| `upload_phase_template.py` | this skill's `scripts/` | Execution 2 — consumes the File dataset as `DatasetSpec(materialize=False)` Input, uploads bytes into Hatrac as Output assets, then adds features. |
| `setup_domain_model_template.py` | this skill's `scripts/` | Schema-phase body: create domain vocabulary, asset table, element type, and feature. Fill the `# TODO: your domain` blocks. |
| `load_cifar10` script + `_cifar10_schema.py` / `_cifar10_assets.py` / `_cifar10_datasets.py` | `deriva-ml-model-template` repo (external) | Reference implementation of Branch 1. The bundled templates above are the copy-me starting point; this is the worked, domain-filled example they generalize from. |

## Related Skills

- **`/deriva-ml:setup-derivaml-project`** *(this plugin)* — Sets up the code repo (uv, pyproject.toml, conventions) that will read/write whichever catalog you set up here. Independent; do these in either order.
- **`/deriva-ml:dataset-lifecycle`** *(this plugin)* — Once the catalog is populated, this is where dataset work starts.
- **`/deriva-ml:work-with-assets`** *(this plugin)* — Owns the file-ingest mechanics the register and upload phases use: `register_files_template.py` (`add_files` input registration) and `upload_asset.py` (`asset_file_path` output upload).
- **`/deriva-ml:execution-lifecycle`** *(this plugin)* — Running workflows against the new catalog.
- **`/deriva-ml:troubleshoot-execution`** *(this plugin)* — If something during the loader phases produces a failed Execution and you need to recover. Covers the salvage workflow.
- **`/deriva:create-table`** *(deriva-skills)* — The schema operations you'll need inside the `schema` phase of a from-scratch loader (Branch 1 Step 3).
- **`/deriva:manage-vocabulary`** *(deriva-skills)* — For any project-specific vocabularies your loader adds beyond the built-in deriva-ml ones.
