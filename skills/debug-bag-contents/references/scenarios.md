# Bag Contents: Scenario Catalog & Fix Recipes

This file holds the deep material for `debug-bag-contents`: the enumerated
"missing data" scenarios (symptom → diagnosis → fix) and the matching concrete
fix recipes. The SKILL.md body keeps the diagnostic flow (Steps 1–4, 6, 7) and
the Quick Diagnostic Checklist inline; come here when a checklist item points
you at a specific scenario or fix.

## Contents

**Scenarios (symptom → cause):**

- [Images missing from a Subject-only dataset](#scenario-images-missing-from-a-subject-only-dataset)
- [Observation data missing](#scenario-observation-data-missing)
- [Denormalize raises "Ambiguous path" error](#scenario-denormalize-raises-ambiguous-path-error)
- [Denormalize returns null for joined columns](#scenario-denormalize-returns-null-for-joined-columns)
- [Vocabulary terms missing](#scenario-vocabulary-terms-missing)

**Fixes:**

- [Deep join timeouts](#deep-join-timeouts) → timeout / exclude_tables / flatten
- [Missing element type registration](#missing-element-type-registration)
- [Stale dataset version](#stale-dataset-version)
- [Records exist but FK not established](#records-exist-but-fk-not-established)

---

## Scenarios: Diagnose Common Cases

### Scenario: Images missing from a Subject-only dataset

**Problem**: Dataset has Subject members but the exported bag does not include the associated Image records.

**Diagnosis**:
- Images are in a separate asset table with an FK to Subject.
- The FK traversal should find Images that reference the Subject members.

**Fix checklist**:
1. Verify the Image table has a direct FK to Subject (not through an intermediate table).
2. If the FK path goes through an intermediate table (e.g., `Observation`), that intermediate table may need to be registered as an element type, or intermediate records need to be added as members.
3. Alternatively, add the Image records directly as dataset members and register the Image table as an element type.

### Scenario: Observation data missing

**Problem**: Observations associated with Subjects are not in the bag.

**Diagnosis**:
- Check whether Observation has a direct FK to Subject.
- If yes, the FK traversal from Subject members should pick up Observations.
- If not, the path may be indirect and not traversed.

**Fix**:
- Add Observation records as explicit dataset members and register `Observation` as an element type.
- Or ensure there is a direct FK link between the tables.

### Scenario: Denormalize raises "Ambiguous path" error

**Problem**: Calling `get_denormalized_as_dataframe(include_tables=["Image", "Subject"])` raises a `DerivaMLException` with "Ambiguous path between Image and Subject".

**Diagnosis**:
- The schema has multiple FK paths between Image and Subject.
- For example: `Image → Subject` (direct FK) AND `Image → Observation → Subject` (multi-hop).
- Denormalize cannot determine which path to use for the join.

**Fix**:
- Read the error message — it lists all paths and suggests intermediate tables.
- Add the intermediate table to `include_tables` to select the desired path:
  ```python
  # Use the multi-hop path through Observation
  df = bag.get_denormalized_as_dataframe(include_tables=["Image", "Observation", "Subject"])
  ```

### Scenario: Denormalize returns null for joined columns

**Problem**: Denormalize returns rows but all columns from a joined table (e.g., Observation) are null.

**Diagnosis**:
- The joined table may not be FK-reachable from the primary table members.
- The FK column on the primary table may be null for all members.
- The FK path may require intermediate tables not listed in `include_tables`.

**Fix**:
1. Check the FK column values: does the primary table actually have non-null FK values pointing to the joined table?
2. If the path goes through intermediate tables, include them in `include_tables`.
3. Verify the joined table has records matching the FK values.

### Scenario: Vocabulary terms missing

**Problem**: Controlled vocabulary values referenced by data records are not in the bag.

**Diagnosis**:
- Vocabulary terms are exported separately from data tables.
- Check that the vocabulary table is properly configured as a vocabulary (not a regular table).

**Fix**:
- Vocabulary terms referenced by included records should be automatically exported. If they are missing, verify the FK relationship between the data table and the vocabulary table is intact.
- Use `get_table(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<vocab_table>")` to confirm the vocabulary table's structure.

---

## Fixes: Common Issues

### Deep join timeouts
**Problem**: FK traversal through many intermediate tables causes slow exports or timeouts.

**Fix — Option A (preferred): Increase the download timeout.**
The default network timeout is (10, 610) seconds — 10s to connect, 610s (~10 min) to read each query response. For large datasets with deep FK joins, increase the read timeout:

```
dataset.download_dataset_bag(version="1.0.0", timeout=[10, 1800])  # Python API
```

This gives the server 30 minutes per query instead of 10. The connect timeout (first value) rarely needs changing.

For Hydra-Zen configs, add `timeout` to `DatasetSpecConfig`:
```python
DatasetSpecConfig(rid="28EA", version="0.4.0", timeout=[10, 1800])
```

**Fix — Option B: Exclude unnecessary tables from the FK graph.**
If you don't need data from certain tables, prune them from the FK traversal:

```
dataset.download_dataset_bag(version="1.0.0", exclude_tables=["Study", "Protocol"])  # Python API
```

This prevents the export from traversing into those tables entirely. Use this when the excluded tables' data is not needed in the bag.

For Hydra-Zen configs:
```python
DatasetSpecConfig(rid="28EA", version="0.4.0", exclude_tables=["Study", "Protocol"])
```

**Fix — Option C: Flatten the traversal by adding direct members.**
Add records from intermediate tables as direct dataset members rather than relying on deep FK traversal. This replaces the deep join with simpler association-based lookups.

### Missing element type registration
**Problem**: Records from a table are added as members but the table is not a registered element type, so those records are ignored during export.

**Fix**:
- **Tool**: `deriva_ml_add_dataset_element_type(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", element_table="<table>")` to register the table.
- Then re-export the bag.

### Stale dataset version
**Problem**: The bag reflects an older version of the dataset, missing recently added members.

**Fix**:
- **Tool (ADR-0003 dev/release model)**: any membership change since the last release will have flipped `current_version` to a dev label (`<last_release>.post1.devN`). Call `deriva_ml_release_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", bump="minor", description="...")` to promote the dev period to a new released version that captures current membership.
- Re-export the bag after releasing — `download_dataset_bag` does not yet accept dev labels (tracked at deriva-ml#89), so the release step is required before the download.

### Records exist but FK not established
**Problem**: Related records exist in the catalog but are not linked via FK to the member records.

**Fix**:
- Check the FK columns on the related records. Ensure they contain the correct RID values pointing to the dataset member records.
- **Tool**: `get_entities(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<table>", filters={...})` to verify FK column values (or `query_attribute` with a `path` expression if you only want specific columns / FK joins).
