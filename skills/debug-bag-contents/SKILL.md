---
name: debug-bag-contents
description: "Diagnose missing data in DerivaML dataset bag (BDBag) exports — FK traversal issues, missing tables, materialization problems, export timeouts. Use when a downloaded dataset bag is missing expected records, images, or feature values."
disable-model-invocation: true
---

# Debugging Dataset Bag Contents

When a dataset bag export is missing expected data, follow this step-by-step diagnostic process to identify and fix the issue.

---

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Recommended First Step: Discover with rag_search

Before diving into specific resources, use `rag_search` to understand the catalog's schema and data landscape. This provides context that makes subsequent debugging more effective:

```
rag_search("dataset element types and FK paths", doc_type="catalog-schema")
rag_search("dataset bag export traversal", doc_type="user-guide")
```

This helps you understand which tables exist, how they relate via foreign keys, and what element types are registered -- all essential context for diagnosing missing bag data. After this initial discovery, use the specific tools listed below for targeted investigation.

## Step 1: Check Dataset Members

Dataset members are the explicit records that belong to a dataset. If data is missing from a bag, the first question is whether the right members are in the dataset.

- **Tool**: `deriva_ml_get_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")` for the dataset's summary and member counts.
- **Tool**: `deriva_ml_list_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>")` to get the full list of members, grouped by table.
- Verify that the records you expect are listed as members. If they are missing, add them with `deriva_ml_add_dataset_members(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", members={"Image": ["2-IMG1", ...]})`.

---

## Step 2: Check Element Type Registration

Every table that contributes members to a dataset must be registered as a **dataset element type**. If a table is not registered, its members will be silently excluded from the bag.

- **Tool**: `deriva_ml_list_dataset_element_types(hostname="data.example.org", catalog_id="1")` to see which tables are registered as element types in the catalog.
- **Tool**: `deriva_ml_add_dataset_element_type(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", element_table="<table>")` to register a table as an element type if it is missing.
- Common tables that should be registered: `Subject`, `Observation`, `Image` (or other asset tables), and any custom tables whose records appear as dataset members.

---

## Step 3: Preview Bag Export Paths

Before downloading a full bag, preview what the export will contain.

- **Tool**: `deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", version="1.0.0")` returns row counts, asset sizes, and the projected manifest per table.
- This preview shows which tables will be included and how many rows each will have, without actually downloading anything.
- Compare the preview counts against your expectations to spot discrepancies early.

---

## Step 4: Understand FK Path Traversal

The bag export algorithm uses foreign key (FK) path traversal to determine which related records to include. Understanding this is critical for diagnosing missing data.

### Key rules:
1. **Starting points are dataset members only from registered element types.** Records in tables that are not registered as element types will not serve as starting points for traversal, even if they are dataset members.
2. **FK traversal follows both directions.** From each starting point record, the export follows foreign keys both outward (this table references another) and inward (another table references this one).
3. **Vocabulary table endpoints are exported separately.** Vocabulary/controlled-vocabulary tables encountered during traversal are collected and exported in their own section of the bag, not inline with the data tables.
4. **Traversal depth is bounded.** The export does not follow FK chains indefinitely. It follows direct FK relationships from the member records.

### How traversal works in practice:
- If `Subject` is a registered element type and you have Subject members, the export will:
  - Include those Subject records.
  - Follow FKs from Subject to related tables (e.g., Subject_Phenotype).
  - Follow FKs pointing back to Subject from other tables (e.g., Image.Subject_RID -> Subject).
  - Export vocabulary terms referenced by any included records.

---

## Step 5: Diagnose Common Scenarios

Match your symptom to one of the enumerated scenarios — images missing from a Subject-only dataset, Observation data missing, denormalize "Ambiguous path" errors, denormalize returning null joined columns, missing vocabulary terms. For the full scenario catalog (symptom → diagnosis → fix) and the matching fix recipes, see `references/scenarios.md`.

---

## Step 6: Download and Validate the Bag

Compare expected vs. actual bag contents by diffing what the catalog says is in the dataset against what `DatasetBag` actually serves. This is a manual two-call comparison — the deriva-ml Python API doesn't ship a one-shot validator.

**Expected side (from the catalog):**

```python
# What the catalog says belongs in this dataset+version
expected = ml.lookup_dataset(dataset_rid).list_dataset_members(version="<version>")
# expected is keyed by element table; values are lists of {RID, ...} records
```

**Actual side (from the downloaded bag):**

```python
bag = ml.lookup_dataset(dataset_rid).download_dataset_bag(version="<version>")
# Per-table introspection — what actually made it into the bag
for table_name in bag.list_tables():
    rows = bag.get_table_as_dict(table_name)
    actual_rids = {r["RID"] for r in rows}
    # Diff against expected[table_name] to find missing / extra RIDs
```

For each table, compute:

- **Missing RIDs**: `expected_rids - actual_rids` — records that should be in the bag but aren't. Usually the symptom of FK paths the export missed, or `exclude_tables=` filtering them out.
- **Extra RIDs**: `actual_rids - expected_rids` — records the export pulled in through FK traversal that weren't dataset members. Usually fine, but worth checking when a bag is unexpectedly large.

The missing-RIDs side is the diagnostic that matters; that's what tells you which records are being dropped and from which tables.

> **BagIt-level structural validation** (manifest checksums, file integrity) is a separate concern — use `bdbag --validate fast <path>` or `bdbag --validate full <path>` on the downloaded bag directory. See `/deriva:download-bag` *(deriva-skills)* for the BagIt-tool surface.

---

## Step 7: Check FK Paths for All Element Types

For each registered element type, examine the FK paths that the export will follow.

- **Tool**: `deriva_ml_list_dataset_element_types(hostname, catalog_id)` to see element types and the projected FK paths each will follow.
- Look for:
  - **Missing links**: Tables you expect to be reachable but are not connected by FKs.
  - **Indirect paths**: FK chains that go through intermediate tables, which may not be traversed if those intermediates are not included.
  - **Circular references**: These are handled correctly but may cause confusion when reading the path graph.

---

## Step 8: Fix Common Issues

The concrete fix procedures live alongside the scenarios they resolve: deep-join timeouts (increase `timeout`, prune with `exclude_tables`, or flatten by adding direct members), missing element type registration, stale dataset version (release the dev period per ADR-0003), and records that exist but aren't FK-linked. For the matching fix recipes — with the exact `download_dataset_bag` / `DatasetSpecConfig` / `deriva_ml_*` calls — see the "Fixes" section of `references/scenarios.md`.

---

## Quick Diagnostic Checklist

Use this checklist when data is missing from a bag:

1. **Are the records dataset members?**
   - `deriva_ml_list_dataset_members(hostname=..., catalog_id=..., dataset_rid=...)` -- check if expected records appear.
   - If not: `deriva_ml_add_dataset_members`.

2. **Is the table a registered element type?**
   - `deriva_ml_list_dataset_element_types(hostname, catalog_id)`.
   - If not: `deriva_ml_add_dataset_element_type`.

3. **Is there a direct FK path?**
   - Inspect the schema (`get_table`, `rag_search`) for the element type.
   - If not: add intermediate records as members, or restructure FKs.

4. **Does validation show the discrepancy?**
   - Diff `ml.lookup_dataset(rid).list_dataset_members(version=...)` (expected) against per-table `bag.get_table_as_dict(...)` calls (actual) — see Step 6 for the recipe.

5. **Is the version current?**
   - If `current_version` is a dev label (`<release>.post1.devN`) — members or features changed since the last release. Call `deriva_ml_release_dataset(...)` to mint a new release that captures the current state, then re-download.

6. **Is the download timing out?**
   - First try increasing the timeout: `timeout=[10, 1800]` (30 min read timeout).
   - If that's not enough, use `exclude_tables` to prune expensive FK branches.
   - Or add intermediate records as direct members to flatten the joins.

7. **Preview before full download.**
   - `deriva_ml_bag_info(hostname=..., catalog_id=..., dataset_rid=..., version=...)` -- shows row counts, asset sizes, and manifest before downloading.

## Reference Resources

- `deriva://docs/datasets` — Full guide to bag export traversal, FK paths, and troubleshooting. Read this for detailed examples and edge cases beyond what this skill covers.
- `deriva://catalog/{h}/{c}/deriva-ml/dataset/{rid}/bag-preview` — Preview bag contents before downloading
- `deriva_ml_list_dataset_element_types(hostname, catalog_id)` — Check which element types are registered

## Related Tools

| Tool | Purpose |
|------|---------|
| `deriva_ml_list_dataset_members` | List all members of a dataset |
| `deriva_ml_add_dataset_members` | Add records to a dataset |
| `deriva_ml_delete_dataset_members` | Remove records from a dataset |
| `deriva_ml_add_dataset_element_type` | Register a table as dataset element type |
| Python API `bag.list_tables()` + `bag.get_table_as_dict(table)` | Diff actual bag contents against `ml.lookup_dataset(rid).list_dataset_members(version=...)` for the expected set (see Step 6 for the recipe) |
| `deriva_ml_release_dataset` | Promote a dev period to a released version (per ADR-0003) |
| `deriva_ml_get_dataset_spec` | View dataset specification |
| `deriva_ml_bag_info` | Preview row counts, asset sizes, and manifest before downloading |
| Python API `dataset.download_dataset_bag(version)` | Download the dataset bag (supports `exclude_tables` and `timeout`) |
| `deriva_ml_denormalize_dataset` | Schema shape + size estimates (no dataset needed), or flatten dataset for analysis |
| `query_attribute` | Inspect FK column values via filtered queries |
| `get_table` | Check table schema and FK relationships |
