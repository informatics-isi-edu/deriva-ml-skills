# Denormalization Guide

Denormalization joins related tables into a single flat table (a "wide table") suitable for ML frameworks. It follows foreign key relationships automatically, handling both direct and multi-hop FK chains.

> **Stateless model:** the new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Quick Reference

**MCP tool — schema exploration (no dataset needed):**
```
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    include_tables=["Image", "Subject", "Diagnosis"]
)
```
Returns column names/types, join path, and global row counts per table — no dataset required.

**MCP tool — dataset-scoped info:**
```
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    include_tables=["Image", "Subject", "Diagnosis"],
    dataset_rid="2-XXXX",
    version="1.0.0"
)
```
Same shape info but with dataset-scoped row counts. Add `limit=50` to also fetch actual rows.

**MCP tool — with row preview:**
```
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    include_tables=["Image", "Subject", "Diagnosis"],
    dataset_rid="2-XXXX",
    version="1.0.0",
    limit=50
)
```
Returns shape info + actual row data (capped at 100).

**Python API (bag-side):**
```python
df = bag.get_denormalized_as_dataframe(include_tables=["Image", "Subject"])

# Memory-efficient streaming
for row in bag.get_denormalized_as_dict(include_tables=["Image", "Subject"]):
    process(row)
```

**Including system columns (provenance).** System columns (`RCT`, `RMT`, `RCB`, `RMB` — created/modified time, created/modified by) are dropped from the wide table by default. Pass `system_columns=` to retain the ones you need — e.g. for grader/annotator attribution, keep the row creator:

```python
df = bag.get_denormalized_as_dataframe(
    include_tables=["Image", "Diagnosis"],
    system_columns=["RCB", "RCT"],   # row creator + creation time per table
)
```

This opt-in is on `get_denormalized_as_dataframe` / `get_denormalized_as_dict` (Dataset and DatasetBag). Most ML feature extraction doesn't need it; reach for it when provenance (who/when produced a row) is part of the analysis.

**Python API — schema shape and size estimates (no bag needed):**
```python
# On a Dataset (live catalog)
info = dataset.describe_denormalized(include_tables=["Image", "Subject"])

# Or on a downloaded bag — same signature
info = bag.describe_denormalized(include_tables=["Image", "Subject"])
```
Returns `columns`, `join_path`, `tables` (with `row_count`, `is_asset`, `asset_bytes`), `total_rows`, `total_asset_bytes`, `total_asset_size`.

**Column naming:**

| Source | Pattern | Example |
|--------|---------|---------|
| Catalog (MCP tool, `Dataset.get_denormalized_as_dataframe`) | `Table_Column` | `Image_Filename`, `Subject_Age` |
| Bag (`DatasetBag.get_denormalized_as_dataframe`) | `Table.Column` | `Image.Filename`, `Subject.Age` |

## Decisions Before Calling Denormalize

**Denormalize is a relational join.** It emits one row for every matching combination across the joined tables — there is no "row per anchor" knob. If you ask for a wide table joining `Image` to a feature table that has 7 feature values per image, you get 7 × (image count) rows, with image columns repeated. That's a correct denormalize result, but it's almost never the shape an analyst actually wants for a per-anchor wide table. Decide which of the three shapes below you want **before** calling, then pick the corresponding pattern.

### Shape A — One row per anchor, anchor + child columns inlined

Use when you want one row per Image/Subject/whatever with values from related tables in extra columns — the classic "wide DataFrame for analysis."

**Works cleanly only when each related table has at most one row per anchor.** Examples that fit: `Image ⋈ Acquisition_Metadata` (one acquisition row per image), `Subject ⋈ Demographics` (one demographics row per subject). The join emits one row per anchor naturally.

**Doesn't work for multi-write features.** If `Image_Classification` has been written by multiple Executions (e.g. 1 ground-truth + 6 prediction executions = 7 rows per image), don't include that feature table in `include_tables`. Use Shape C instead — denormalize the anchor, fetch features separately, then join in pandas.

```python
# Shape A — cross-sectional analysis frame
df = dataset.get_denormalized_as_dataframe(
    include_tables=["Image", "Acquisition_Metadata"],
)
# Row count == number of Image members. Acquisition_Metadata columns
# inlined; image columns appear once per image.
```

### Shape B — One row per child entity (e.g. one row per annotation event)

Use when you want every annotation, prediction, or measurement event as its own row — the "provenance browse" or "every-write-as-a-row" shape. Each child row carries the anchor's columns, repeated.

This is **the default `row_per` auto-inference for multi-write features**, and it's the correct call when you want to see all writes side by side.

```python
# Shape B — one row per annotation
df = dataset.get_denormalized_as_dataframe(
    include_tables=["Image", "Execution_Image_Image_Classification"],
)
# For a feature with 7 writers per image, this is 7 × image_count rows.
# Each row carries image columns + one feature value + its producing Execution.
# Group/pivot in pandas if you want a wide-per-anchor view.
```

### Shape C — One row per anchor, features fetched separately

Use when you want Shape A's shape but you need data from a multi-write feature. Don't ask denormalize to inline it — call `feature_values()` separately, select/aggregate to one row per anchor in your code, then join.

```python
# Step 1: anchor-only wide frame (Shape A pattern)
anchors = dataset.get_denormalized_as_dataframe(
    include_tables=["Image"],
)

# Step 2: fetch the feature values via the feature API
labels = pd.DataFrame(
    r.model_dump() for r in ml.feature_values("Image", "Image_Classification")
)

# Step 3: select / aggregate / pivot to one row per anchor
gt_only = labels[labels["Confidence"].isna()]  # ground truth (no predicting model)
# or:  latest = labels.sort_values("RCT").drop_duplicates("Image", keep="last")
# or:  pivoted = labels.pivot(index="Image", columns="Execution", values="Image_Class")

# Step 4: join
df = anchors.merge(gt_only, left_on="Image_RID", right_on="Image", how="left")
```

The `feature_values()` API is the right tool for "give me the values of this feature." The `create-feature` skill documents selection patterns (by execution, by latest write, by confidence threshold) — reuse those for step 3.

### Decision summary

| Question | Answer | Shape |
|---|---|---|
| Do you want one row per anchor (Image, Subject, etc.)? | Yes; child tables have ≤1 row per anchor | A |
| Do you want one row per annotation/measurement event? | Yes | B |
| Do you want one row per anchor but feature has multiple writers per anchor? | Use feature_values() and join in pandas | C |
| Do you want longitudinal columns (`obs_t1`, `obs_t2`)? | Pivot in pandas after Shape B | C |
| Just need the column list, no data? | `list_denormalized_columns()` | (any) |
| Just need size estimates? | `describe()` / `deriva_ml_bag_info` | (any) |

The cost of mis-picking is silent count inflation (Shape A used on multi-write data emits N × anchor rows; analysts who don't sanity-check anchor counts get wrong denominators). When in doubt, run `dataset.list_dataset_members()` to anchor your expected count, then check the denormalize row count matches.

## Discovering Columns Before Denormalizing

Call `deriva_ml_denormalize_dataset` with just `include_tables` (no dataset RID, no limit) to preview the schema shape without fetching any data. This is fast and helps you:
- See what columns a denormalization would produce
- Verify FK paths resolve correctly before running expensive queries
- Find the correct column name for `stratify_by_column` in `split_dataset` (Python API)
- Debug ambiguous FK path errors without waiting for data
- Estimate total data size before committing to a download

**MCP tool (no dataset needed):**
```
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    include_tables=["Image", "Subject", "Diagnosis"]
)
```

Returns:
```json
{
  "mode": "catalog_shape",
  "include_tables": ["Image", "Subject", "Diagnosis"],
  "tables": {
    "Image": {"row_count": 3200, "is_asset": true, "asset_bytes": 45000000},
    "Subject": {"row_count": 1500, "is_asset": false, "asset_bytes": 0},
    "Diagnosis": {"row_count": 2800, "is_asset": false, "asset_bytes": 0}
  },
  "total_rows": 7500,
  "total_asset_bytes": 45000000,
  "total_asset_size": "45.0 MB"
}
```

The top-level discriminator is `mode` (one of `catalog_shape`, `dataset_describe`, `dataset_preflight_required`), NOT `status`. Catalog-wide calls (no `dataset_rid`) return `mode: "catalog_shape"` with the size estimate above. Dataset-scoped calls return `mode: "dataset_describe"` with additional fields describing the resolved denormalization plan (e.g., `columns`, `join_path`, `row_per`).

**Python API (from a bag):**
```python
# Returns list of (column_name, column_type) tuples
columns = bag.list_denormalized_columns(include_tables=["Image", "Subject"])
# [("Image.RID", "ermrest_rid"), ("Image.Filename", "text"), ...]
```

**Python API (from SDK — no bag needed):**
```python
# Shape + size estimates on a Dataset (or a downloaded bag — same signature)
info = dataset.describe_denormalized(include_tables=["Image", "Subject"])
```

These call the same FK path analysis as the full denormalization but skip the data fetch entirely.

## How FK Traversal Works

Denormalization starts from a **primary table** — the first table in `include_tables` that has dataset members. It then joins other tables by following FK relationships.

### Direct FK joins

The simplest case: two tables connected by a single FK.

```
Schema:  Image --FK--> Subject
Query:   include_tables=["Image", "Subject"]
Result:  Each Image row joined with its Subject
```

Tables don't need to be explicit dataset members to appear in the output. If Image is the only table with dataset members, Subject records are fetched by following the FK from each Image to its Subject.

### Multi-hop FK chains

When tables aren't directly connected, denormalize follows chains of FKs through intermediate tables.

```
Schema:  Image --FK--> Observation --FK--> Subject
Query:   include_tables=["Image", "Observation", "Subject"]
Result:  Each Image joined with its Observation, then each Observation joined with its Subject
```

The algorithm:
1. Start with primary table members (Image records from the dataset)
2. Follow FK from Image to Observation — fetch matching Observation records
3. Follow FK from Observation to Subject — fetch matching Subject records
4. Combine all columns into a single wide row per Image

All intermediate tables must be listed in `include_tables`. If you request `["Image", "Subject"]` but the only FK path goes through Observation, you need to include Observation.

### Association table traversal (M:N joins)

Many-to-many relationships use association tables. Denormalize traverses them transparently — association table columns do NOT appear in the output.

```
Schema:  Observation <--FK-- ClinicalRecord_Observation --FK--> ClinicalRecord
Query:   include_tables=["Image", "Observation", "ClinicalRecord"]
Result:  Image → Observation → (through association) → ClinicalRecord
         Association table columns excluded from output
```

### Outer join semantics

Denormalize uses outer join semantics. If an Image has no Observation FK set (null), the Observation columns in that row will all be null. No rows are dropped — every primary table member always appears in the output.

```python
df = bag.get_denormalized_as_dataframe(include_tables=["Image", "Observation"])
# Row count == number of Image dataset members (never fewer)
# Images with null Observation FK → Observation columns are null
```

## Ambiguous FK Paths

When multiple FK paths exist between the same pair of tables, denormalize raises a `DerivaMLException` asking you to disambiguate.

### When it happens

```
Schema:  Image --FK--> Subject           (direct FK)
         Image --FK--> Observation --FK--> Subject  (multi-hop)
```

Here, Subject is reachable from Image via two different paths. Requesting `["Image", "Subject"]` is ambiguous — which path should be used for the join?

### The error

```
DerivaMLException: Ambiguous path between Image and Subject: found 2 FK paths:
  Image → Subject
  Image → Observation → Subject
Include an intermediate table to disambiguate (e.g., add Observation to include_tables).
```

### How to resolve

Include the intermediate table to tell denormalize which path to use:

```python
# Ambiguous — raises error
df = bag.get_denormalized_as_dataframe(include_tables=["Image", "Subject"])

# Disambiguated — uses Image → Observation → Subject path
df = bag.get_denormalized_as_dataframe(include_tables=["Image", "Observation", "Subject"])
```

When you include Observation, denormalize uses the multi-hop path (Image → Observation → Subject) because all intermediate tables on that path are present in `include_tables`.

### Checking for ambiguity

If you're unsure whether a schema has ambiguous paths, try the query. The error message lists all paths and suggests which intermediate tables to add. You can also inspect the schema:

```
# Via MCP — check FK relationships
rag_search("what tables reference Subject?")
```

## Best Practices

### Only include tables you need

Each table in `include_tables` adds columns and potentially triggers FK chain lookups. Including unnecessary tables:
- Increases query time (especially for multi-hop chains that require catalog fetches)
- Adds columns that clutter the DataFrame
- Can trigger ambiguous path errors for tables you don't even care about

### Start with the member table

The first table in `include_tables` that has dataset members becomes the primary table. The output has one row per primary table member. If you list a non-member table first, it may produce no results.

```python
# Good — Image has members, drives the output
df = bag.get_denormalized_as_dataframe(include_tables=["Image", "Subject"])

# Risky — if Observation has no members, result may be empty
df = bag.get_denormalized_as_dataframe(include_tables=["Observation", "Image"])
```

### Verify FK integrity

After denormalization, you can verify FK relationships in the output:

```python
df = bag.get_denormalized_as_dataframe(include_tables=["Image", "Observation"])

# Check FK values match
valid = df.dropna(subset=["Image.Observation", "Observation.RID"])
for _, row in valid.iterrows():
    assert row["Image.Observation"] == row["Observation.RID"]
```

## Troubleshooting

### All joined columns are null

**Symptom:** Denormalize returns rows but all columns from a joined table are null.

**Cause:** The joined table's records are not FK-reachable from the primary table members. This can happen when:
- The FK column on the primary table is null for all members
- The joined table has no records matching the FK values
- The FK path requires intermediate tables not listed in `include_tables`

**Fix:** Check that the FK column has values and include any intermediate tables in the path.

### DerivaMLException: Ambiguous path

**Symptom:** `DerivaMLException` raised with "Ambiguous path between X and Y".

**Cause:** Multiple FK paths exist between two tables in `include_tables`.

**Fix:** Read the error message — it lists all paths and suggests intermediate tables to add. Include the intermediate table for the path you want.

### Empty result (no rows)

**Symptom:** Denormalize returns an empty DataFrame.

**Cause:** No table in `include_tables` has dataset members. Denormalize needs at least one table with members to drive the output.

**Fix:** Ensure at least one table in `include_tables` is a registered element type with members in this dataset. Check with `deriva_ml_list_dataset_members(hostname=..., catalog_id=..., dataset_rid=...)`.

### Row count doesn't match expectations

**Symptom:** More or fewer rows than expected.

**Cause:** Row count equals the number of primary table members (the first table in `include_tables` with members). It is NOT the count of the joined table. One-to-many or many-to-many joins do not duplicate rows — each primary member appears exactly once.

**Fix:** Check `deriva_ml_list_dataset_members(hostname=..., catalog_id=..., dataset_rid=...)` for the primary table to confirm the expected count.
