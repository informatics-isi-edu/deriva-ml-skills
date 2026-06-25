# Branch 2 deep-dive: `clone_via_bag()` (clone a slice)

This is the full step-by-step mechanical recipe for Branch 2 of `setup-ml-catalog` — cloning a slice of an existing source catalog into a new destination catalog. The branch-selection decision (when you'd choose `clone_via_bag` over Branch 1 "from scratch", and why not `clone_catalog`) stays in `SKILL.md`; this file is the deep recipe once you've chosen this branch.

This branch produces a destination catalog populated from a source catalog. The destination ends up self-contained (its own catalog ID, its own schema, its own data) and intentionally smaller — only the slice you asked for makes it across.

The tool is **`clone_via_bag()`** (Python API only — no MCP wrapper). It runs a two-step pipeline: walk the source from a set of anchors and write a bag to disk, then load that bag into the destination. The bag in the middle is real (an on-disk artifact you can inspect, re-load, or archive separately), which makes the operation debuggable and resumable.

The destination catalog must already exist. Create it first (Branch 1 Step 1 + 2 in `SKILL.md`, then skip the data-loading steps).

## Step 1: Pick your roots

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

## Step 2: Provenance comes automatically (this is not a knob)

The slice **always includes the executions that produced the data**, the workflows behind those executions, the upstream datasets those executions consumed, and (recursively) the executions that produced *those* — back along the provenance chain until there are no more upstream rows.

This is not configurable in this skill's recipe. Partial provenance is broken provenance: a destination ML catalog where `deriva_ml_get_lineage` traces hit dead ends is not a usable ML catalog, it's a viewing snapshot. If you want a viewing snapshot, that's a different goal and not what `clone_via_bag` is for.

The mechanism: `clone_via_bag` defaults `terminal_tables` to `{("deriva-ml", "Execution"), ("deriva-ml", "Workflow")}`. This sounds restrictive but isn't — it means the walker **follows outbound FKs** of Execution and Workflow rows (so input datasets, source-code URLs, parent workflows come along) while **not following inbound FKs** (which would over-fetch: from one Execution that touched 1000 rows across the catalog, inbound traversal would pull in all 1000 even if your anchors only cared about a handful). The asymmetry is the design.

Don't override `terminal_tables` — the default is what produces a working ML catalog with bounded scope.

## Step 3: Asset mode (the real decision)

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

## Step 4: Dangling-FK behavior

A "dangling FK" is a row in the bag whose FK reference points at something that didn't make it into the slice. Common case: a Subject-rooted slice reaches the Dataset that Subject belongs to (call it D), then reaches the `Dataset_Dataset` association row recording that D is *nested in* a parent Dataset P. P wasn't in your anchor scope, so the `Dataset_Dataset` row's FK to P dangles.

`clone_via_bag` defaults `dangling_fk_strategy` to `DanglingFKStrategy.DELETE` — drop those association rows at load time so the destination converges on a self-coherent subgraph. This is the right default: legitimate dangling FKs from anchor-scoped slices are expected, not a bug.

If you suspect your roots are under-specified (you're seeing the destination catalog missing things you thought would be there), switch to `FAIL` for one clone to make the dangling-FK paths visible, then widen the anchor set accordingly:

```python
from deriva.bag.traversal import DanglingFKStrategy

policy = FKTraversalPolicy(dangling_fk_strategy=DanglingFKStrategy.FAIL)
# clone_via_bag will now abort on the first orphan with a message
# naming the table and FK column — useful diagnostic, not a long-term default.
```

## Step 5: Slice size

A complete-provenance slice can be **larger than the user initially expects**. A Dataset anchor doesn't just pull in the Dataset's contents — it pulls in the producing executions, their input datasets (recursively), workflows, vocabularies, and (with the default `asset_mode`) all the asset files.

This is the cost of cloning into a *working* ML catalog rather than a viewing snapshot. The walker terminates naturally (eventually there's nothing further upstream), but a Dataset that's the output of 5 generations of executions chained together can clone substantially more than its own member rows.

The bag-on-disk intermediate is useful here: after the build phase, check the bag's reported row counts before the load phase actually runs. The walker writes a manifest you can inspect.

## Step 6: Run the clone

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

## Step 7: Promote the destination (if the source wasn't a deriva-ml catalog)

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

## Step 8: Verify

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

## Branch 2 failure modes

- **Auth errors** during `clone_via_bag`: re-run `deriva-globus-auth-utils login --host <hostname>` for both source and destination.
- **Bag-build fails partway**: the bag-on-disk persists. Re-running `clone_via_bag` with the same `output_dir` will rebuild the bag from scratch by default. To re-use a partial bag, inspect `result.bag_path` from the previous run and consult the bag-loader docs for the partial-resume path.
- **Load phase fails with dangling-FK errors** (when `dangling_fk_strategy=FAIL`): your anchor set is too narrow. Widen it (e.g., add the parent Dataset, the upstream Workflow). Re-run.
- **`create_ml_schema` errors with "schema already exists"**: it doesn't — it WARNS and drops the existing schema with CASCADE. If you're seeing an error, something else is wrong (auth, connectivity, server version mismatch).
