---
name: create-feature
description: "ALWAYS use this skill when creating features, adding labels or annotations to records, setting up classification categories, querying or exploring feature values, or working with feature values in DerivaML. Covers: feature-vs-column decision, discovering existing features, single vs multi-column design, creating vocabularies and features, adding feature values with provenance, querying/browsing feature values, selecting among multiple annotations, caching, and how features integrate with datasets. Triggers on: 'create feature', 'add labels', 'annotate images', 'classification', 'ground truth', 'confidence score', 'feature values', 'what features exist', 'explore annotations', 'show feature values', 'query features', 'what are the labels', 'list annotations', 'browse features', 'feature preview'."
disable-model-invocation: false
---

# Creating and Populating Features in DerivaML

Features link domain objects (e.g., Image, Subject) to structured values — controlled vocabulary terms, computed values, or assets — with full provenance tracking through executions.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly.

## Phase 1: Specify

Before assessing or creating, capture what the feature is for and how you'll
know it serves that purpose. Hand off to `/deriva-ml:design-experiment` to
author `docs/design/feature/<slug>.md` — Purpose (the decision the values inform),
Requirements (target table, type, vocabulary, who writes the values),
Validation (coverage, value sanity, provenance, the consumer can read it), and
Upstream designs. Get it to **Approved** before creating anything;
`tacit-knowledge.md` stays the running journal. A trivial single-term label can
be a few lines, but a feature a model or split will depend on earns a full
design — its Validation criteria are exactly what gets skipped otherwise.

This is the Specify phase of the universal Specify → Build → Validate arc.
Phases 2–5 below are Build; Phase 6 (now reframed) is Validate.

## Phase 2: Assess

Before creating a feature, determine whether one is needed and whether it already exists.

### Is this a feature or a column?

Features have overhead (separate table, execution requirement, provenance). Use a feature when you need provenance, multivalued support, or controlled vocabulary terms. Use a column when the value is intrinsic to the record and immutable. See `references/concepts.md` under "When to Use a Feature vs a Column" for the full decision guide.

> **Already decided wrong?** If an existing target table has a column that should really be a feature (or vice versa), that's a non-additive schema change — use `/deriva:evolve-schema` *(deriva-skills)* for the migration runbook (backfill, FK rewire, drop the old column under a snaptime). Don't try to "convert" in place by silently adding both shapes; pick one and migrate.

### Search existing features

**Start with `rag_search`** to discover features by concept, not just name:
```
rag_search("diagnosis label classification", doc_type="catalog-schema")
```

Then use the typed tools for full structured details. For "all features on a target table" snapshots, prefer the resource read; for feature values (which can be large, paginated, or selector-driven), use the tool:

```
# Snapshot all features defined on the Image table (one round trip)
ReadMcpResourceTool(server="<name>", uri="deriva://catalog/{h}/{c}/deriva-ml/features/Image")

# Or paginated equivalents — use the tool when you need to drill or filter:
deriva_ml_list_features(hostname, catalog_id)                                                    # All features (paginated)
deriva_ml_get_feature(hostname, catalog_id, target_table="Image", feature_name="Diagnosis")       # Specific feature details
deriva_ml_list_feature_values(hostname, catalog_id, target_table="Image", feature_name="Diagnosis", selector="newest")  # Existing values
```

```python
features = ml.find_features("Image")
feature = ml.lookup_feature("Image", "Diagnosis")
```

**Before creating, ask:**
- Does a feature with this purpose already exist? `/deriva:semantic-awareness` *(deriva-skills, auto-fires)* carries the find-before-you-create discipline — the search applies to ML entities (Features) as well as generic catalog entities. `deriva_ml_create_feature` also warns about near-duplicates at create time.
- Can the existing feature be extended with new vocabulary terms?
- Is this really a feature, or should it be a column on the table? `/deriva:semantic-awareness` covers the EAV-vs-wide-table dual extreme — features map naturally to the middle ground (typed columns + FK-to-vocab), but if you find yourself reaching for one giant feature with many free-text fields, or one EAV-shaped feature whose `Value` carries every kind of label, step back and rethink.

## Phase 3: Design the feature structure

### Choose the feature type

| Type | Parameter | Use case |
|------|-----------|----------|
| Term-based | `terms=["Vocab_Name"]` | Classification labels, categories |
| Asset-based | `assets=["Asset_Table"]` | Segmentation masks, annotation overlays |
| Mixed | both `terms` and `assets` | Labels with associated files |
| With metadata | `metadata=[...]` | Confidence scores, reviewer references |

### Single vs multi-column

- **One feature, multiple term columns** — when values are always assigned together in the same annotation act (e.g., diagnosis + severity in one clinical assessment)
- **Separate features** — when values are assigned independently by different processes (e.g., quality scored by QC, diagnosis by pathologist)

The test: if you always set them at the same time in the same execution, they belong together.

### Naming

- Use PascalCase with underscores: `Tumor_Classification`, `Image_Quality`
- Name the annotation act, not the vocabulary: `Diagnosis` (not `Diagnosis_Type`)
- Be specific: `Cell_Classification` (not just `Classification`)

For the full design guide, see `references/concepts.md` under "Designing a Feature."

## Phase 4: Create the Feature Definition

### Standard workflow

1. **Create vocabulary + terms** (if term-based). Use `deriva_ml_create_vocabulary` to create the vocabulary table, then `add_term` (from deriva-mcp-core) for each term:
   ```
   deriva_ml_create_vocabulary(hostname, catalog_id, vocab_name="Diagnosis_Type", comment="...")
   add_term(hostname, catalog_id, schema="<schema>", table="Diagnosis_Type", name="Normal", description="...")
   ```
   See `deriva-ml-context` → "Creating a new vocabulary" for the rationale (curie prefix, default schema, navbar refresh) and when to fall back to the generic `create_vocabulary` from deriva-mcp-core.

2. **Create the feature**:
   ```
   deriva_ml_create_feature(hostname, catalog_id,
                             target_table="Image", feature_name="Diagnosis",
                             terms=["Diagnosis_Type"],
                             comment="Clinical diagnosis for this image")
   ```

For the full MCP and Python API examples (term-based, asset-based, mixed, with metadata), see `references/workflow.md`.

### Description guidance

Every feature needs a description explaining what it measures, what values it takes, and its role.

**Good:** "Diagnostic classification of chest X-ray images. Values from the Diagnosis vocabulary (normal, pneumonia, COVID-19). Primary ground truth label for training classification models"

**Bad:** "Classification" or "Labels" or empty

Since features are multivalued, note whether it's intended for ground truth, model predictions, or computed metrics. For description templates and quality guidelines, see `/deriva-ml:generate-descriptions` *(auto-loaded)*.

## Phase 5: Add Feature Values

Adding values requires knowing what columns a feature has, which are required, and what values are valid. The full inspect → discover-valid-values → add → commit walkthrough lives in `references/workflow.md` under "Add Feature Values"; this section names the rule.

### Writing values: always through an execution

There is **no MCP tool that writes feature values** — `deriva_ml_add_feature_values` was removed in v0.5.0. The MCP feature surface is read-only (`deriva_ml_list_feature_values`, `deriva_ml_get_feature`, `deriva_ml_find_features_referencing`). Every write — even a 1-value smoke test — goes through `exe.add_features(records)` inside a `with ml.create_execution(...) as exe:` block. Read the values back afterward with `deriva_ml_list_feature_values`.

| Situation | Approach |
|-----------|----------|
| Verifying a new feature works (1-5 test values) | A short throwaway script (or `--allow-dirty` ad-hoc run) calling `exe.add_features([record])` — disposable, but still inside an execution |
| Production annotations, batch labels, model predictions | Committed script — same `exe.add_features(...)` path, run via `deriva-ml-run` for code provenance |

**For production data, always write a script first.** The execution record captures the git hash of the committed code. Without a committed script, the execution has provenance (who, when, what) but no code link (how). Use `/deriva-ml:generate-scripts` or `/deriva-ml:dataset-lifecycle`'s script templates to generate the script, commit it, then run via `deriva-ml-run`. Running an uncommitted script raises `DerivaMLDirtyWorkflowError` — use `--allow-dirty` only for debugging iterations (degraded provenance).

### Common mistakes

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Adding values without an execution | Error — provenance required | Use a bundled script template (e.g. `create-feature/scripts/populate_feature_values.py`) so the work runs inside the canonical `with ml.create_execution(...) as exe:` context manager |
| Generating inline Python in the model turn | Workflow has no committed URL; provenance lies about reproducibility | Always copy a bundled template into `src/scripts/`, edit, commit, then run via `deriva-ml-run` |
| Using wrong term name | Error — must match vocabulary exactly | `rag_search("{vocab} terms", doc_type="catalog-schema")` or `list_vocabulary_terms(...)` |
| Missing required column | Error — required fields must be present | `rag_search("{feature} columns", doc_type="catalog-schema")` or `deriva_ml_get_feature(...)` |
| One execution per label | Works but clutters provenance | Batch labels from same source into one execution |
| Passing boolean as string `"true"`/`"false"` | Pydantic validation error | Pass as native bool: `true` / `false` (no quotes) |
| Forgetting `exe.commit_output_assets()` after the `with` block | Execution stays in `Stopped` and values stay staged | The bundled templates always call `commit_output_assets()` post-context. If you write your own script, do the same. On failure inside the `with` block, the context manager auto-transitions to `Failed`; run `salvage_execution.py` to drain anything that successfully staged. |
| CSV ingest without capturing the source file | Provenance traces to Execution but not to *what data* | Declare the CSV as a `LocalFile` input in `ExecutionConfiguration(assets=[LocalFile(path=...)])` (see the worked example below) — registers a referenced `File` row + Input edge, no Hatrac upload |
| Capturing a *source/input* CSV via `asset_file_path` + copy | Uploads the bytes to Hatrac and mis-frames an input as an output asset | For an **input** file use `LocalFile` (reference, no upload). Reserve `asset_file_path` + `commit_output_assets` for files the run **produces** |

### Worked example: bulk-populate feature values from a CSV

The most common production pattern: a domain expert hands you a CSV of ground-truth values and you load them into a Feature via a committed script. The canonical entry point is the bundled template `skills/create-feature/scripts/populate_feature_values.py` (copy → edit CSV path + feature name → commit → run via `deriva-ml-run`). For the full end-to-end walkthrough — including the `LocalFile`-input variant that records the source CSV in provenance, the run/commit commands, what the lineage chain looks like afterward, and crash recovery — see `references/workflow.md` under "Worked example: bulk-populate feature values from a CSV".

## Phase 6: Validate against the design

Confirm the feature serves the Purpose in its `feature-design` doc — not just
that values were written:
- **Coverage** — every intended record got a value (or the expected subset did).
- **Value sanity** — terms are from the declared vocabulary; numeric scores in
  range.
- **Provenance** — each value links to its producing Execution
  (`deriva_ml_list_feature_values(..., execution_rids=[...])`).
- **Consumer can read it** — the downstream use named in the design (a
  stratified split, a training loop) actually finds the values where it expects.

Record the outcome in the design doc's Status & links (Status → Validated) and
in `tacit-knowledge.md`. Then proceed to query/explore (next section) for
ongoing use.

## Phase 7: Query and Explore Feature Values

Feature queries fall into two categories. **Always choose the right one — never use preview tools to retrieve feature values.**

### Rule: "get values" = Python API; "explore shape" = preview

- **User asks to get, retrieve, list, or show feature values** → ALWAYS use the Python API via a script. Even for small numbers of values. Results stay out of context and are cached for reuse.
- **User asks exploratory questions** ("what features exist?", "what does this feature look like?", "what columns does it have?") → Preview tools (`get_table_sample_data`, `deriva_ml_denormalize_dataset`, `deriva_ml_list_features`, `deriva_ml_get_feature`) are fine for a small sample.

**NEVER use `query_attribute` or `get_table_sample_data` with large limits to retrieve feature values.** This dumps raw records into the conversation context, which is wasteful and doesn't support selectors or caching.

For the exploratory-preview MCP tool examples and the full Python API retrieval pattern (`ml.feature_values(table, feature_name, selector=...)` and the `materialize_limit=` / `execution_rids=` filters), see `references/workflow.md` under "Query Feature Values".

### Resolve multiple values with selectors

When a record has values from multiple annotators or model runs, use a selector to pick one. Built-in selectors include `select_newest`, `select_by_execution`, `select_by_workflow`, `select_majority_vote`. For the full guide — built-in selectors, custom selector functions, the cache-key warning, common pitfalls — see `references/feature-selectors.md`.

**Before retrieving in the multi-value case, ask the user which values they want.** Quick provenance check:

```python
all_values = list(ml.feature_values("Image", "Scouts_Pick"))
executions = set(r.Execution for r in all_values)
print(f"Total values: {len(all_values)}, from {len(executions)} execution(s): {executions}")
```

If multiple executions contributed, present only the relevant selector options based on the provenance check (e.g., offer "by workflow type" only if executions span different workflow types; offer "majority vote" only if multiple annotators have the same target).

> **Heads-up for analysts asking for "a wide table with the labels inlined".** If a feature has been written by multiple executions, including its feature table in `Dataset.get_denormalized_as_dataframe(include_tables=[...])` produces one row per *annotation*, not one row per anchor — the join's correct relational semantics, but almost never what the caller wanted. The right pattern is to denormalize the anchor on its own, fetch feature values via `ml.feature_values(...)`, apply a selector to collapse to one row per anchor, and join in pandas. See `/deriva-ml:ml-data-engineering` denormalize-guide "Decisions Before Calling Denormalize" → Shape C.

## Integration with Datasets

- **In dataset bags** — feature values for dataset members are automatically included in BDBag exports
- **In `deriva_ml_denormalize_dataset`** — include feature tables to see labels alongside data. Column names: `{FeatureTableName}_{ColumnName}`
- **Dataset versioning** — adding feature values to dataset members does NOT automatically flip the dataset to a dev version. Per ADR-0003, only the dataset-mutation tools (`add_dataset_members`, `delete_dataset_members`, dataset-type changes) auto-flip to dev; feature drift is invisible to that detection. To record feature drift, call `dataset.mark_dev(description)` from the Python API to declare a dev period, then `deriva_ml_release_dataset(...)` to mint a release that captures the new feature values
- **In `split_dataset`** (Python API, run from a script) — the `stratify_by_column` parameter references feature columns in denormalized format

**Drift notification (handoff grammar).** Writing feature values to records that
are members of a *released* Dataset drifts that dataset's content — the same
members now carry different data. This is not a build dependency (a dataset
doesn't depend on the feature); it's a drift the dataset must record. When you
populate values on members of a released dataset, **proactively offer** to flip
it to a dev version (`dataset.mark_dev(description)`) and route to
`/deriva-ml:dataset-lifecycle` Phase 6 (Version) for the release once the drift
period is done. Don't wait to be asked.

## Reference Resources

- `references/concepts.md` — Feature types, design guidance, naming, multivalued features, selection, Python API, integration
- `references/workflow.md` — Step-by-step MCP and Python API examples for create / add-values / query
- `references/feature-selectors.md` — Complete guide to writing and using feature selectors
- `deriva://docs/features` — Full user guide to features in DerivaML
- `deriva://catalog/{h}/{c}/deriva-ml/features/{table}` — Snapshot of features defined on a target table (one round trip; preferred for "what features exist on X?")
- `deriva_ml_list_features(hostname, catalog_id)` — Paginated browse across all target tables (use when you need to filter or drill beyond the per-table snapshot)
- `deriva_ml_get_feature(hostname, catalog_id, target_table, feature_name)` — Feature details and column schema
- `deriva_ml_list_feature_values(hostname, catalog_id, target_table, feature_name, selector=...)` — Feature values with selectors and per-execution / per-workflow filtering (no resource equivalent; values are too large/selector-driven for a snapshot)
- `deriva_ml_create_vocabulary(hostname, catalog_id, vocab_name, comment="", schema=None, update_navbar=True)` — ML-aware vocabulary creation. See `deriva-ml-context` → "Creating a new vocabulary" for the rationale (curie prefix, default schema, navbar refresh) and when to prefer this over the generic `create_vocabulary`.

## Related Skills

- **`/deriva:manage-vocabulary`** *(deriva-skills)* — Create and manage the controlled vocabularies that features reference.
- **`/deriva:evolve-schema`** *(deriva-skills)* — When the target table's shape needs to change (split, merge, retype, drop columns), feature values referencing those columns ride along — see the migration runbook for the snapshot + backfill + dangling-FK patterns.
- **`/deriva-ml:dataset-lifecycle`** — Features annotate records in datasets. Feature values are included in bag exports and affect dataset versioning.
- **`/deriva-ml:ml-data-engineering`** — Consuming feature values for ML training — restructuring, DataFrames, value selectors.
