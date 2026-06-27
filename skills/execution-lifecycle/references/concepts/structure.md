---
type: Concept
title: Execution structure
description: How executions are represented in the catalog — RIDs, record structure, and parent-child nesting.
---

# Execution structure

## Executions in the Catalog

An execution is a catalog record that captures a unit of work — a model training run, a data analysis, a notebook evaluation, a feature annotation pass. Executions are the fundamental unit of provenance in DerivaML. They are persistent, queryable entities stored in the catalog alongside your data.

Every execution record answers: "What work was done? With what inputs? What was produced? What code and configuration were used?"

Executions are represented in the `Execution` table in the `deriva-ml` schema. Like all catalog records, each execution has a unique **RID** that permanently identifies it.

## Execution RIDs

Every execution has a unique RID (Resource IDentifier) — a short, immutable string like `2-YYYY` or `3-AB4C`. This RID is the primary way to reference an execution:

- **In MCP tools**: Pass `execution_rid` to `deriva_ml_get_execution`, `deriva_ml_list_execution_children`, `deriva_ml_list_execution_parents`, `deriva_ml_get_lineage`, etc.
- **In provenance queries**: Asset and dataset provenance records reference execution RIDs
- **In the web UI**: Each execution has a Chaise page at its RID-based URL
- **In citation**: `cite(hostname, catalog_id, rid)` generates a permanent URL for an execution
- **In nested relationships**: Parent-child links between executions use RIDs

RIDs are assigned by the catalog when the execution record is created and never change.

## Execution Structure

An execution record in the catalog has these relationships:

```
Execution
├── Workflow (FK)           — what kind of work was performed
├── Status (FK)             — current state (Running, Completed, Failed, ...)
├── Description             — human-readable purpose (supports Markdown)
├── Start/Stop timestamps   — when the work ran
├── Input Datasets          — which datasets were consumed (association table)
├── Input Assets            — which assets were consumed (association table)
├── Output Assets           — which files were produced (association table)
├── Code provenance         — git commit hash and repository URL
├── Configuration           — Hydra config choices and parameters
└── Nested Executions       — parent-child relationships (association table)
```

The input and output links are tracked through association tables with role information ("Input" or "Output"), so you can trace provenance in both directions — from an execution to its artifacts, or from an artifact back to the execution that created it.

**Querying executions:**
- Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` for full details (workflow, status, datasets, assets, timestamps).
- Read `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/execution/{execution_rid}` for the same content as a resource.
- Call `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)` then inspect its `executions` field to find all executions that used a dataset.
- Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` to find the producer execution; use `deriva_ml_find_workflow_executions(...)` for the broader query.
- Call `deriva_ml_list_assets(hostname, catalog_id, execution_rid=...)` to enumerate the output assets a past execution produced (the `Execution_Asset` rows it owns). This is the one-shot equivalent of walking `Execution → Execution_Asset_Execution → Execution_Asset` in the path-builder — prefer the MCP tool for lookups, use the path-builder when you need to join further.

**The ExecutionRecord class** in the Python API is the lightweight read-only representation of an execution record. It's returned by lookup and query methods:

```python
record = ml.lookup_execution("2-YYYY")
print(record.execution_rid)   # "2-YYYY"
print(record.status)          # "Completed"
print(record.description)     # "Train CNN on batch 1"
print(record.workflow_rid)    # "1-WXYZ"
```

`ExecutionRecord` is also what you get back from provenance queries like `asset.list_executions()` and `ml.find_executions()`.

`ExecutionRecord` is **read-only** — it carries the metadata fields above but not the asset/dataset/feature *link methods* that the live `Execution` handle (returned by `ml.create_execution(...)` and threaded through training code) carries. Once the live handle has gone out of scope, use the MCP queries listed above (or the equivalent path-builder traversals) to walk to the execution's linked records; don't expect `record.execution_assets()` or similar live-handle methods on the lookup result.

## Nested Executions

Executions can be organized into parent-child relationships for multi-step work:

```
Parent execution (e.g., "Hyperparameter Sweep")
├── Child 1 (e.g., "lr=0.001")
├── Child 2 (e.g., "lr=0.01")
└── Child 3 (e.g., "lr=0.1")
```

Common use cases:
- **Parameter sweeps** — parent represents the sweep, children are individual runs
- **Pipelines** — parent represents the pipeline, children are stages (preprocessing, training, evaluation)
- **Cross-validation** — parent represents the CV experiment, children are individual folds
- **Multi-experiment comparisons** — parent groups related experiments (e.g., "compare architectures")

Each child is a full execution with its own RID, inputs, outputs, and provenance. The parent-child link is tracked via an association table with an optional `sequence` number for ordering.

Use `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)` to walk down the tree and `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)` to walk up.

### How multiruns create nested executions

The `deriva-ml-run` CLI automatically creates nested executions when using `multirun_config` or `--multirun`:

```bash
uv run deriva-ml-run +multirun=lr_sweep
```

This creates:
1. A **parent execution** for the sweep — its description comes from `multirun_config`'s `description` field
2. One **child execution** per parameter combination — each with its own config, inputs, outputs, and status

The parent's RID is the single reference point for the entire sweep. All children are accessible via `deriva_ml_list_execution_children`.

### Manual nesting with the bundled template

For custom multi-step workflows, copy `skills/execution-lifecycle/scripts/nested_execution.py` and edit. The template encodes the canonical pattern:

```python
with ml.create_execution(parent_config, workflow=parent_workflow,
                         dry_run=args.dry_run) as parent_exe:
    for i, unit in enumerate(work_units):
        child_config = ExecutionConfiguration(description=f"Child {i}: {unit}")
        with ml.create_execution(child_config, workflow=child_workflow,
                                 dry_run=args.dry_run) as child_exe:
            # ... child work ...
            ...

        parent_exe.add_nested_execution(child_exe, sequence=i)
        if not args.dry_run:
            child_exe.commit_output_assets()

if not args.dry_run:
    parent_exe.commit_output_assets()
```

Each child is its own execution with its own inputs and outputs; the parent's `add_nested_execution(child)` writes the parent → child link. Each child's `commit_output_assets()` runs after its own `with` block exits; the parent's runs last so the parent's summary outputs (if any) commit after the children.

### Navigating nested execution hierarchies

**MCP tools:**

| Tool | Direction | Parameters |
|------|-----------|-----------|
| `deriva_ml_list_execution_children` | Parent → Children | `hostname`, `catalog_id`, `execution_rid`, `recurse=True` for all descendants |
| `deriva_ml_list_execution_parents` | Child → Parent | `hostname`, `catalog_id`, `execution_rid`, `recurse=True` for all ancestors |

**MCP resources:**

| Resource | What it returns |
|----------|----------------|
| `deriva://catalog/{h}/{c}/deriva-ml/execution/{rid}` | Execution details including status, workflow, timing, inputs, outputs |

Nested-execution navigation lives on the MCP surface, not as Execution
methods — there is no `execution.list_execution_children(...)` /
`execution.list_execution_parents(...)` on the Python `Execution` object.
Use the MCP tools (or the matching resources) to walk the tree:

```text
# From parent to children
deriva_ml_list_execution_children(hostname, catalog_id, execution_rid="PARENT_RID")
deriva_ml_list_execution_children(hostname, catalog_id, execution_rid="PARENT_RID", recurse=True)

# From child to parent
deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid="CHILD_RID")
```

Each call returns the related execution RIDs; pass each RID to
`deriva_ml_get_execution(hostname, catalog_id, execution_rid=...)` to fetch
its status, workflow, and description.

### Analyzing sweep results

After a multirun completes, the typical analysis flow is:

1. `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid="PARENT_RID")` — get all children
2. For each child, call `deriva_ml_get_execution(hostname, catalog_id, execution_rid=child_rid)` — get config parameters and results
3. Compare results across children (metrics, output assets)
4. Optionally, create a summary notebook that reads all children's outputs

The `run-notebook` skill covers how to build analysis notebooks that consume execution results.
