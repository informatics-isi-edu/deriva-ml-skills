---
name: schema-evolution-impact
description: "Impact analysis BEFORE changing or deleting anything in a DerivaML catalog — dropping/altering a table or column, deleting a vocabulary table or term, retiring an asset table, or deleting a dataset/asset row. Enumerates what references the target (datasets holding members, feature definitions carrying FKs, executions that consumed it) so the change is informed, not hopeful. Use when the user asks 'what breaks if I change/drop X', 'is it safe to delete this', 'who uses this table/column', 'which datasets contain rows from X', 'which features reference this vocabulary', 'can I remove this asset table', 'clean up unused tables', or any schema-migration planning question. Triggers on: 'safe to delete', 'what breaks', 'impact analysis', 'who references', 'drop a column', 'remove a table', 'retire', 'unused', 'schema migration', 'rename a column'."
disable-model-invocation: true
---

# Impact Analysis Before Schema Evolution

Before you alter or delete anything in a deriva-ml catalog, enumerate what
references it. A DerivaML catalog cross-links aggressively — datasets hold
members from domain tables, feature association tables carry foreign keys
into vocabulary and asset tables, and executions record which datasets and
assets they consumed. A "harmless" drop can orphan dataset members, break
feature definitions, or erase the provenance story of published results.

The deriva-ml MCP plugin ships three reverse-lookup tools for exactly this
question. Run the relevant ones FIRST, read the counts, then decide.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly.
> Substitute your catalog's hostname and catalog ID.

## The three reverse-lookup tools

| Question | Tool | Granularity |
|---|---|---|
| Which datasets currently hold members of this table? | `deriva_ml_find_datasets_referencing(hostname, catalog_id, table, column=None)` | table / column |
| Which feature definitions reference this table (as target, vocabulary, or asset)? | `deriva_ml_find_features_referencing(hostname, catalog_id, table, column=None)` | table / column |
| Which executions consumed this specific Dataset or asset as an input? | `deriva_ml_find_executions_consuming(hostname, catalog_id, rid)` | one row (RID) |

The first two answer schema-level questions ("can I change the *shape*?");
the third answers instance-level questions ("can I delete this *row*?").
The third also has a resource form for read-only clients:
`deriva://catalog/{hostname}/{catalog_id}/deriva-ml/lineage-forward/{rid}`.

All three return `count == 0` with an empty list as the normal "nothing
references this" answer — that is your green light, not an error.

## Recipes by change type

**Dropping or altering a column.** Run both table-level tools with
`column=` set:

```
deriva_ml_find_datasets_referencing(hostname="...", catalog_id="...",
                                    table="Image", column="Acquisition_Date")
deriva_ml_find_features_referencing(hostname="...", catalog_id="...",
                                    table="Image", column="Acquisition_Date")
```

`find_features_referencing(column=...)` only reports features whose FK
references that specific column — for ordinary value columns (no inbound
FK) expect features to come back empty, and the real exposure to be
downstream code that reads the column (denormalize outputs, training
scripts). Those are outside the catalog's knowledge; grep your project
repo too.

**Dropping a whole table.** Run both tools with just `table=`. Then check
whether the table is a registered dataset element type
(`deriva_ml_list_dataset_element_types`) — a table can be registered as an
element type yet currently have zero dataset members, and dropping it
leaves a dangling registration.

**Deleting a vocabulary table (or pruning its terms).** Vocabulary tables
are the most common FK target for features:

```
deriva_ml_find_features_referencing(hostname="...", catalog_id="...",
                                    table="ImageQuality")
```

A non-empty result means feature VALUES exist (or can exist) that point at
this vocabulary — deleting it breaks every one of those feature
definitions. For pruning individual terms, the feature-level check tells
you which feature tables to inspect for rows using the term
(`deriva_ml_list_feature_values` on each referencing feature).

**Retiring an asset table.** Same two table-level checks (asset tables can
be dataset members AND feature FK targets), plus the instance-level
question for any row you'd delete: `deriva_ml_find_executions_consuming`
on the asset RID. An asset that a recorded execution consumed is part of
the provenance chain of that execution's outputs — deleting it breaks the
story behind published results.

**Deleting a Dataset or a single asset row.** This is the pure
forward-lineage question:

```
deriva_ml_find_executions_consuming(hostname="...", catalog_id="...",
                                    rid="1-ABCD")
```

Empty `consumers` means no execution ever recorded consuming it. Non-empty
means the row is upstream of real runs — prefer deprecating in place
(description update, dataset type tag) over deletion. Note this is the
forward complement of `deriva_ml_get_lineage`, which walks backward from
an artifact to its producers.

**Deleting a feature definition.** `deriva_ml_delete_feature` already
guards against silent value loss. Before invoking it, the impact question
is the values themselves: page `deriva_ml_list_feature_values` for the
feature and decide whether the labels/scores are dispensable.

## Interpreting the results honestly

- **Empty means "no RECORDED reference."** `find_executions_consuming`
  only sees inputs that executions registered. A script that fetched data
  ad hoc (outside an execution context) left no edge. Empty is strong
  evidence, not proof.
- **Counts are current state.** `find_datasets_referencing` reports
  datasets that hold members NOW. A versioned dataset whose older version
  contained rows from the table still references those rows historically
  — released dataset versions are immutable bags, so deleting the
  underlying rows breaks re-download of those versions.
- **Don't fall back to raw queries first.** If you need reference
  structure these tools don't cover (arbitrary FK fan-in on a non-ML
  table), use the generic schema surface (`list_foreign_keys`, core's
  schema resources) — and only then raw `get_entities` probing, per the
  ordered strategy in `deriva_ml_getting_started`.

## Related skills

- **`/deriva-ml:dataset-lifecycle`** — dataset versioning and member
  management; what "a dataset references this table" implies for releases.
- **`/deriva-ml:create-feature`** — feature anatomy (target / vocabulary /
  asset FKs); read it to understand WHY a feature shows up in
  `find_features_referencing`.
- **`/deriva-ml:work-with-assets`** — asset-table shape, including
  `deriva_ml_create_asset_table` for the create side of the lifecycle.
- **`/deriva:manage-vocabulary`** *(deriva-skills)* — term-level CRUD on
  vocabulary tables once the impact check clears.
- **`/deriva-ml:troubleshoot-execution`** — the forward-lineage tool also
  appears there for diagnosing "what depended on this failed run's
  outputs".
