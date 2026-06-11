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

The canonical reference is the **`load_cifar10` script** in `deriva-ml-model-template` at `src/scripts/load_cifar10.py`. It demonstrates the right shape: a thin orchestrator that wires three resumable phases (schema → assets → datasets), each in its own module. Copy that structure for your own loader.

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

`load_cifar10`'s `_cifar10_schema.py` has a full working example of this for the CIFAR-10 domain.

### Step 4: Phase your loader

The `load_cifar10` script's three-phase structure is the recommended shape for any from-scratch loader:

| Phase | What it does | Idempotent? |
|-------|-------------|-------------|
| **schema** | Creates the domain tables (Subject, Image, etc.), workflow types, dataset types, Chaise annotations. | Yes — re-running on a catalog that already has the schema is safe. |
| **assets / images** | Uploads files (assets) to Hatrac, inserts catalog rows, populates per-row features (labels, classes). | Mostly — Hatrac uploads are content-addressed and idempotent; row inserts use upsert patterns. |
| **datasets** | Creates the Dataset hierarchy (Training, Testing, Complete, splits, subsets) and adds members. | Re-running typically creates new dataset versions, not duplicate datasets. |

Wire them with a `--phase {all,schema,images,datasets}` CLI argument so a partial failure can be resumed without re-running the earlier phases. The orchestrator (in `load_cifar10.py`) does this with a single `argparse` switch.

### Step 5: Verify

After the loader finishes, sanity-check from a fresh `DerivaML(...)` session:

```python
ml = DerivaML(hostname=..., catalog_id=..., domain_schemas={"my_project"})

# The four built-in vocabularies should be populated
for v in ["Asset_Type", "Workflow_Type", "Dataset_Type", "Execution_Status"]:
    terms = list_vocabulary_terms(hostname=..., catalog_id=..., schema="deriva-ml", table=v)
    print(f"{v}: {len(terms)} terms")

# At least one Dataset, Workflow, Execution should exist (if the loader created them)
print(ml.find_datasets())
print(ml.find_workflows())
```

If `find_datasets()` returns nothing and you expected datasets, your `datasets` phase didn't run or didn't commit — check the loader logs.

---

## Branch 2: From existing data (clone a slice)

This branch produces a destination catalog populated from a source catalog. The destination ends up self-contained (its own catalog ID, its own schema, its own data) and intentionally smaller — only the slice you asked for makes it across.

The tool is **`clone_via_bag()`** (Python API only — no MCP wrapper). It runs a two-step pipeline: walk the source from a set of anchors and write a bag to disk, then load that bag into the destination. The bag in the middle is real (an on-disk artifact you can inspect, re-load, or archive separately), which makes the operation debuggable and resumable.

The destination catalog must already exist. Create it first (Branch 1 Step 1 + 2, then skip the data-loading steps).

### Step 1: Pick your roots

The anchors decide what makes it into the slice. The walker traverses FK closure from each anchor — everything reachable is included, everything not reachable is excluded.

The 90% case is a **Dataset-rooted slice** (`root_rid` convenience):

```python
from deriva_ml.catalog.clone_via_bag import clone_via_bag

result = clone_via_bag(
    source_hostname="src.example.org",
    source_catalog_id="1",
    dest_hostname="dst.example.org",
    dest_catalog_id="42",  # must already exist
    root_rid="1-ABCD",     # Dataset RID — everything reachable from this Dataset
)
```

For other shapes, build the anchors explicitly with `RIDAnchor`:

| Slice intent | Anchor expression |
|--------------|-------------------|
| One Dataset (the convenience case) | `root_rid="1-ABCD"` (equivalent to `anchors=[RIDAnchor(table="Dataset", rids=["1-ABCD"])]`) |
| Several Datasets, pooled into one destination | `anchors=[RIDAnchor(table="Dataset", rids=["1-A", "1-B", "1-C"])]` |
| All data tied to specific Subjects | `anchors=[RIDAnchor(table="Subject", rids=["S1", "S2", "S3"])]` |
| Everything from specific Experiments | `anchors=[RIDAnchor(table="Experiment", rids=["E1", "E2"])]` |
| Everything produced by a specific Workflow | `anchors=[RIDAnchor(table="Workflow", rids=["W1"])]` |
| Multiple roots of different shapes | `anchors=[RIDAnchor(table="Dataset", rids=["1-A"]), RIDAnchor(table="Subject", rids=["S1"])]` |

`RIDAnchor` is the right tool for the vast majority of slicing tasks. `clone_via_bag` accepts richer `Anchor` types (`QueryAnchor` etc.) — see deriva-bag's documentation if your root set is defined by a query rather than a known RID list.

### Step 2: Provenance comes automatically (this is not a knob)

The slice **always includes the executions that produced the data**, the workflows behind those executions, the upstream datasets those executions consumed, and (recursively) the executions that produced *those* — back along the provenance chain until there are no more upstream rows.

This is not configurable in this skill's recipe. Partial provenance is broken provenance: a destination ML catalog where `deriva_ml_get_lineage` traces hit dead ends is not a usable ML catalog, it's a viewing snapshot. If you want a viewing snapshot, that's a different goal and not what `clone_via_bag` is for.

The mechanism: `clone_via_bag` defaults `terminal_tables` to `{("deriva-ml", "Execution"), ("deriva-ml", "Workflow")}`. This sounds restrictive but isn't — it means the walker **follows outbound FKs** of Execution and Workflow rows (so input datasets, source-code URLs, parent workflows come along) while **not following inbound FKs** (which would over-fetch: from one Execution that touched 1000 rows across the catalog, inbound traversal would pull in all 1000 even if your anchors only cared about a handful). The asymmetry is the design.

Don't override `terminal_tables` — the default is what produces a working ML catalog with bounded scope.

### Step 3: Asset mode (the real decision)

Asset files (images, model weights, prediction CSVs) live in Hatrac, not in the catalog rows. The clone has two options for them:

| `asset_mode` | What it does | Right when |
|--------------|-------------|------------|
| `AssetMode.UPLOAD_IF_MISSING` *(default)* | For each asset, check the destination's Hatrac via HEAD; upload bytes only if missing or MD5 differs. Destination ends up **self-contained** — its rows point at its own Hatrac. | Cross-institution sharing, demo catalogs, any case where source and destination are different deployments. **Default; usually right.** |
| `AssetMode.ROWS_ONLY` | Insert/reconcile asset rows with the bag's `URL` column unchanged — no bytes transferred. Destination's rows reference the **source's** Hatrac URLs. | Source and destination share a Hatrac (same deployment, e.g., same-server alias of the source). Saves bandwidth. **Use only when you can guarantee the source's Hatrac stays reachable from destination users.** |

```python
from deriva.bag.traversal import AssetMode, FKTraversalPolicy

# UPLOAD_IF_MISSING is the default; this is explicit for illustration:
policy = FKTraversalPolicy(asset_mode=AssetMode.UPLOAD_IF_MISSING)

result = clone_via_bag(
    source_hostname="src.example.org",
    source_catalog_id="1",
    dest_hostname="dst.example.org",
    dest_catalog_id="42",
    root_rid="1-ABCD",
    policy=policy,
)
```

### Step 4: Dangling-FK behavior

A "dangling FK" is a row in the bag whose FK reference points at something that didn't make it into the slice. Common case: a Subject-rooted slice reaches the Dataset that Subject belongs to (call it D), then reaches the `Dataset_Dataset` association row recording that D is *nested in* a parent Dataset P. P wasn't in your anchor scope, so the `Dataset_Dataset` row's FK to P dangles.

`clone_via_bag` defaults `dangling_fk_strategy` to `DanglingFKStrategy.DELETE` — drop those association rows at load time so the destination converges on a self-coherent subgraph. This is the right default: legitimate dangling FKs from anchor-scoped slices are expected, not a bug.

If you suspect your roots are under-specified (you're seeing the destination catalog missing things you thought would be there), switch to `FAIL` for one clone to make the dangling-FK paths visible, then widen the anchor set accordingly:

```python
from deriva.bag.traversal import DanglingFKStrategy

policy = FKTraversalPolicy(dangling_fk_strategy=DanglingFKStrategy.FAIL)
# clone_via_bag will now abort on the first orphan with a message
# naming the table and FK column — useful diagnostic, not a long-term default.
```

### Step 5: Slice size

A complete-provenance slice can be **larger than the user initially expects**. A Dataset anchor doesn't just pull in the Dataset's contents — it pulls in the producing executions, their input datasets (recursively), workflows, vocabularies, and (with the default `asset_mode`) all the asset files.

This is the cost of cloning into a *working* ML catalog rather than a viewing snapshot. The walker terminates naturally (eventually there's nothing further upstream), but a Dataset that's the output of 5 generations of executions chained together can clone substantially more than its own member rows.

The bag-on-disk intermediate is useful here: after the build phase, check the bag's reported row counts before the load phase actually runs. The walker writes a manifest you can inspect.

### Step 6: Run the clone

```python
from pathlib import Path
from deriva_ml.catalog.clone_via_bag import clone_via_bag

result = clone_via_bag(
    source_hostname="src.example.org",
    source_catalog_id="1",
    dest_hostname="dst.example.org",
    dest_catalog_id="42",
    root_rid="1-ABCD",
    output_dir=Path("./clone-1-to-42"),   # bag lives here
    # policy=...                          # omit for the recommended defaults
)
print(f"Bag at: {result.bag_path}")
print(f"Rows inserted: {result.load_report.total_rows_inserted}")
```

`clone_via_bag` returns a `CloneViaBagResult` with the on-disk bag path and a per-table load report. Both are useful for debugging if anything doesn't look right at the destination.

### Step 7: Promote the destination (if the source wasn't a deriva-ml catalog)

If the source was a plain Deriva catalog (no `deriva-ml` schema), the destination won't have one either — the clone copies what was there, not what wasn't. In that case, install the ML schema after cloning:

```python
from deriva.core import get_credential, DerivaServer
from deriva_ml.schema.create_schema import create_ml_schema, initialize_ml_schema

server = DerivaServer("https", "dst.example.org", credentials=get_credential("dst.example.org"))
catalog = server.connect_ermrest("42")
create_ml_schema(catalog, schema_name="deriva-ml", project_name="my_project")
initialize_ml_schema(catalog.getCatalogModel(), schema_name="deriva-ml")
```

`create_ml_schema` adds the deriva-ml schema; **if it already exists, the schema is DROPPED with CASCADE.** Only call this on a destination that has no deriva-ml schema yet. `initialize_ml_schema` is safe to call repeatedly — it inserts the standard vocabulary terms (Asset_Type, Asset_Role, Dataset_Type, Workflow_Type) and skips ones that already exist.

The more common case — source was already a deriva-ml catalog — needs no promotion. The clone brought the schema along.

### Step 8: Verify

Same checks as Branch 1, plus a lineage smoke test that confirms the provenance walk worked:

```python
ml = DerivaML(hostname="dst.example.org", catalog_id="42",
              domain_schemas={"my_project"})

# Pick any asset in the destination and walk its lineage
asset_rid = "<any asset RID from the slice>"
lineage = deriva_ml_get_lineage(hostname="dst.example.org", catalog_id="42",
                                rid=asset_rid)
# Should return a tree rooted at the producing execution, walking back
# through inputs without hitting unknown-RID errors.
```

If `get_lineage` returns errors about missing RIDs (executions or datasets that don't exist in the destination), your slice is incomplete — debug by re-running with `dangling_fk_strategy=FAIL` to see where the breakage is.

---

## Failure modes (both branches)

- **Auth errors** during `create_ml_catalog` or `clone_via_bag`: re-run `deriva-globus-auth-utils login --host <hostname>` for both source and destination if Branch 2.
- **Branch 1 schema phase fails partway**: the script is idempotent for `--phase schema`. Re-run that phase only — don't re-run `--phase all`.
- **Branch 2 bag-build fails partway**: the bag-on-disk persists. Re-running `clone_via_bag` with the same `output_dir` will rebuild the bag from scratch by default. To re-use a partial bag, inspect `result.bag_path` from the previous run and consult the bag-loader docs for the partial-resume path.
- **Branch 2 load phase fails with dangling-FK errors** (when `dangling_fk_strategy=FAIL`): your anchor set is too narrow. Widen it (e.g., add the parent Dataset, the upstream Workflow). Re-run.
- **`create_ml_schema` errors with "schema already exists"**: it doesn't — it WARNS and drops the existing schema with CASCADE. If you're seeing an error, something else is wrong (auth, connectivity, server version mismatch).

---

## Reference

| Tool / helper | Where | Purpose |
|---|---|---|
| `create_ml_catalog(hostname, project_name, catalog_alias=None)` | `deriva_ml.schema.create_schema` (Python) | Create a fresh catalog with ACLs + deriva-ml schema in one call. Branch 1 entry point. |
| `create_ml_schema(catalog, schema_name="deriva-ml", project_name=None)` | `deriva_ml.schema.create_schema` (Python) | Add the deriva-ml schema to an existing catalog. **DROPS** the schema with CASCADE if already present. Use for promoting a plain Deriva catalog to deriva-ml. |
| `initialize_ml_schema(model, schema_name="deriva-ml")` | `deriva_ml.schema.create_schema` (Python) | Populate the four standard vocabularies (Asset_Type, Asset_Role, Dataset_Type, Workflow_Type). Safe to call repeatedly. |
| `set_catalog_provenance(catalog, name, description, workflow_url)` | `deriva_ml.catalog.provenance` (Python) | Record how the catalog was created. Call once after `create_ml_catalog`. |
| `clone_via_bag(source_hostname, source_catalog_id, dest_hostname, dest_catalog_id, root_rid=None, anchors=None, output_dir=None, policy=None)` | `deriva_ml.catalog.clone_via_bag` (Python) | Slice-clone. Branch 2 entry point. |
| `RIDAnchor(table, rids)` | `deriva.bag.anchors` (Python) | Specify slice roots by table + RID list. |
| `FKTraversalPolicy(asset_mode, dangling_fk_strategy, ...)` | `deriva.bag.traversal` (Python) | Override `clone_via_bag` defaults. The deriva-ml defaults are usually right; override only with reason. |
| `AssetMode.UPLOAD_IF_MISSING` / `AssetMode.ROWS_ONLY` | `deriva.bag.traversal` (Python) | Whether the destination gets its own asset bytes or references the source's Hatrac. |
| `DanglingFKStrategy.DELETE` / `FAIL` / `NULLIFY` | `deriva.bag.traversal` (Python) | What to do with orphan FK rows at load time. |
| `clone_catalog` / `clone_catalog_async` | `deriva-mcp-core` MCP | Whole-catalog same-server clone. **Not for this skill's workflows** — see "Why not `clone_catalog`?" above. |
| `load_cifar10` script + `_cifar10_schema.py` / `_cifar10_assets.py` / `_cifar10_datasets.py` | `deriva-ml-model-template` repo | Reference implementation of Branch 1. Copy the structure. |

## Related Skills

- **`/deriva-ml:setup-derivaml-project`** *(this plugin)* — Sets up the code repo (uv, pyproject.toml, conventions) that will read/write whichever catalog you set up here. Independent; do these in either order.
- **`/deriva-ml:dataset-lifecycle`** *(this plugin)* — Once the catalog is populated, this is where dataset work starts.
- **`/deriva-ml:execution-lifecycle`** *(this plugin)* — Running workflows against the new catalog.
- **`/deriva-ml:troubleshoot-execution`** *(this plugin)* — If something during the loader phases produces a failed Execution and you need to recover. Covers the salvage workflow.
- **`/deriva:create-table`** *(deriva-skills)* — The schema operations you'll need inside the `schema` phase of a from-scratch loader (Branch 1 Step 3).
- **`/deriva:manage-vocabulary`** *(deriva-skills)* — For any project-specific vocabularies your loader adds beyond the four built-in deriva-ml ones.
