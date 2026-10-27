# DerivaML Python Idioms — worked detail

Python conventions for code that uses the `deriva-ml` library: reading domain
objects by attribute, carrying structure end-to-end, and the `find_*` vs
`list_*` accessor split. Read this before writing analysis or pipeline code
against DerivaML objects.

## Contents

- [Use direct attribute access on domain objects](#use-direct-attribute-access-on-domain-objects)
- [Carry structure, don't decay it](#carry-structure-dont-decay-it)
- [Carry structure — worked examples](#carry-structure--worked-examples)
- [`find_*` vs `list_*` — full call table](#find_-vs-list_--full-call-table)

## Use direct attribute access on domain objects

Datasets, Workflows, Executions, Features, and Assets come back as **typed records** (Pydantic models / DerivaML
domain objects), not raw dicts or row-tuples. Read their fields with the dot
operator:

- `Dataset`: `.dataset_rid`, `.current_version`, `.dataset_types`, `.description`
- `Execution`: `.execution_rid`, `.status`, `.workflow`, `.description`
- `Workflow`: `.workflow_rid`, `.workflow_type`, `.url`, `.checksum`
- `FeatureRecord`: one attribute per feature column (`.Diagnosis_Type`,
  `.Confidence`, …) plus `.Execution`, `.Feature_Name`, `.RCT`
- `Asset`: `.asset_rid`, `.filename`, `.length`, `.md5`, `.asset_types`

`print(obj)` spells out the field names — faster than guessing.

**Do not use `getattr(obj, "name", default)` on these objects.** A wrong name
should raise `AttributeError` so you fix the call; `getattr(d, "version", "?")`
quietly returns `"?"` when the real field is `current_version`, and the bug
ships. Reserve `getattr` for reflecting over genuinely unknown attribute names
(columns a user supplied at runtime, debug-printing arbitrary records).

## Carry structure, don't decay it

**When data has a known shape, carry it in a container that knows the shape**,
end-to-end through the analysis:

| Shape | Container | Why |
|---|---|---|
| One record (a row, a config, a ranking entry) | `@dataclass` or Pydantic `BaseModel` | Named fields, typo-checked at definition, readable `repr()` |
| Many records of one shape (query result, denormalized dataset, prediction table) | `pandas.DataFrame` (or polars) | Named columns, tracked dtypes, first-class join/aggregate. `get_denormalized_as_dataframe()` already returns one — keep it. |
| A few labeled tables that belong together | `@dataclass` of DataFrames, or `dict[str, DataFrame]` if names are dynamic | Outer container shows the relationship; inner frames keep their schemas |
| Genuinely schemaless (arbitrary YAML blobs, MCP responses inspected interactively) | `dict` with `.get(key, default)` — *only* here | No contract, so defensive lookup is correct |

**Don't downgrade**: no DataFrame → list-of-dicts, Pydantic record → dict, or
`@dataclass` → tuple. Each downgrade trades a schema for stringly-typed lookups,
and the symptoms are silent: `row["confidence"]` returning `None` because the
column is `Confidence`, `result.get("status")` masking a renamed field.

## Carry structure — worked examples

These two examples show the downgrade failure mode concretely.

**Worked example.** You're ranking three executions by top-1 accuracy. Wrong: build a `list[dict]` where each entry is `{"rid": ..., "accuracy": ..., "epochs": ...}` and access via `entry.get("accuracy", 0)`. Right: define `@dataclass class RankingEntry: rid: str; accuracy: float; epochs: int` and access via `entry.accuracy`. The dataclass version catches a typo at the point of construction; the dict version ships a silent zero into your sorted list.

**Worked example 2.** `get_denormalized_as_dataframe()` hands you a DataFrame with columns like `Image_RID`, `Diagnosis_Type`, `Confidence`. Wrong: `df.to_dict(orient="records")` and iterate with `row.get("Confidence", 0)`. Right: stay in DataFrame land — `df["Confidence"].fillna(0)`, `df.groupby("Diagnosis_Type")`, `df.merge(predictions_df, on="Image_RID")`. You only leave the DataFrame when you need a scalar (a final summary number) or when the shape genuinely changes (one row out of many).

## `find_*` vs `list_*` — full call table

The rule (full taxonomy in `/deriva-ml:api-naming-conventions`): **`find_*`** searches the catalog for entities of
a kind (the argument is a *filter*); **`list_*`** enumerates things scoped to a
specific parent entity (the first argument *is the scope*, usually required).

- **`find_*`** examples: `ml.find_features()`, `ml.find_features(table)`, `ml.find_datasets()`, `ml.find_workflows()`, `ml.find_executions()`, `ml.find_experiments()`, `ml.find_assets()`, `ml.find_incomplete_executions()`.
- **`list_*`** examples: `ml.list_assets(asset_table)`, `dataset.list_dataset_members(...)`, `dataset.list_dataset_children(...)`, `ml.list_workflow_executions(workflow)`, `ml.list_vocabulary_terms(table)`, `asset.list_executions(...)`.

So:

| What you want | The right call |
|---|---|
| "All features anywhere in the catalog" | `ml.find_features()` |
| "All features on table T" | `ml.find_features(T)` — `T` is a filter, not a scope |
| "All datasets" | `ml.find_datasets()` |
| "All members of dataset D" | `dataset.list_dataset_members()` — D is the scope (it's `self`) |
| "All executions of workflow W" | `ml.list_workflow_executions(W)` — W is the scope |
| "All assets of table T" | `ml.list_assets(T)` — T is the scope |

**There is no `ml.list_features()`.** Features aren't scoped to a parent entity in the way dataset members are scoped to a dataset, so there's no place for a scope-less `list_*` flavor. Use `find_features()` for the catalog-wide enumeration.

Both kinds return iterables of typed records (Pydantic models or DerivaML domain objects), not raw rows. Convert with `list(...)` if you need a concrete list. `feature_values()` is the same shape but named without the `find`/`list` prefix because it returns *values of one feature*, not an enumeration of feature definitions.

When you hit `AttributeError: 'DerivaML' object has no attribute 'list_features'. Did you mean: 'find_features'?` — that's the muscle-memory failure mode. The convention is intentional; the search is `find_features()`.
