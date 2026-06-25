# DerivaML Python Idioms — worked detail

Extended detail for two conventions whose *rules* live inline in the
`deriva-ml-context` skill body: carrying structure end-to-end, and the
`find_*` vs `list_*` accessor split. The skill body carries the rule and the
quick table; this file carries the worked examples and the exhaustive
call tables. Read it when you want the fully-worked illustration.

## Contents

- [Carry structure — worked examples](#carry-structure--worked-examples)
- [`find_*` vs `list_*` — full call table](#find_-vs-list_--full-call-table)

## Carry structure — worked examples

The rule (in the skill body): **when data has a known shape, carry it in a
container that knows the shape**, end-to-end — don't downgrade a typed
`Execution` to a dict, a DataFrame to a list-of-dicts, or a `@dataclass` to a
tuple. Each downgrade trades a real schema for stringly-typed lookups, and every
downstream call site pays the cost. These two examples show the downgrade
failure mode concretely.

**Worked example.** You're ranking three executions by top-1 accuracy. Wrong: build a `list[dict]` where each entry is `{"rid": ..., "accuracy": ..., "epochs": ...}` and access via `entry.get("accuracy", 0)`. Right: define `@dataclass class RankingEntry: rid: str; accuracy: float; epochs: int` and access via `entry.accuracy`. The dataclass version catches a typo at the point of construction; the dict version ships a silent zero into your sorted list.

**Worked example 2.** `denormalize_dataset()` hands you a DataFrame with columns like `Image_RID`, `Diagnosis_Type`, `Confidence`. Wrong: `df.to_dict(orient="records")` and iterate with `row.get("Confidence", 0)`. Right: stay in DataFrame land — `df["Confidence"].fillna(0)`, `df.groupby("Diagnosis_Type")`, `df.merge(predictions_df, on="Image_RID")`. You only leave the DataFrame when you need a scalar (a final summary number) or when the shape genuinely changes (one row out of many).

## `find_*` vs `list_*` — full call table

The rule (in the skill body): **`find_*`** searches the catalog for entities of
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
