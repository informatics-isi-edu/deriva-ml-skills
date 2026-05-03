---
name: create-feature
description: "ALWAYS use this skill when creating features, adding labels or annotations to records, setting up classification categories, querying or exploring feature values, or working with feature values in DerivaML. Covers: deciding whether a feature is needed vs a column, discovering existing features, designing single vs multi-column features, creating vocabularies and features, adding feature values with provenance, querying and browsing feature values (preview via MCP for shape, full retrieval via Python API for analysis), selecting among multiple annotations (newest, by workflow, custom selectors), caching feature values for reuse, and understanding how features integrate with datasets. Triggers on: 'create feature', 'add labels', 'annotate images', 'classification', 'ground truth', 'confidence score', 'feature values', 'what features exist', 'explore annotations', 'show feature values', 'query features', 'what are the labels', 'list annotations', 'browse features', 'feature preview'."
disable-model-invocation: false
---

# Creating and Populating Features in DerivaML

Features link domain objects (e.g., Image, Subject) to structured values — controlled vocabulary terms, computed values, or assets — with full provenance tracking through executions.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly.

## Phase 1: Assess

Before creating a feature, determine whether one is needed and whether it already exists.

### Is this a feature or a column?

Features have overhead (separate table, execution requirement, provenance). Use a feature when you need provenance, multivalued support, or controlled vocabulary terms. Use a column when the value is intrinsic to the record and immutable. See `references/concepts.md` under "When to Use a Feature vs a Column" for the full decision guide.

### Search existing features

**Start with `rag_search`** to discover features by concept, not just name:
```
rag_search("diagnosis label classification", doc_type="catalog-schema")
```

Then use the typed tools for full structured details:
```
deriva_ml_list_features(hostname, catalog_id)                                                    # All features (structured JSON)
deriva_ml_get_feature(hostname, catalog_id, target_table="Image", feature_name="Diagnosis")       # Specific feature details
deriva_ml_list_feature_values(hostname, catalog_id, target_table="Image", feature_name="Diagnosis", selector="newest")  # Existing values
```

```python
features = ml.find_features("Image")
feature = ml.lookup_feature("Image", "Diagnosis")
```

**Before creating, ask:**
- Does a feature with this purpose already exist? `/deriva:semantic-awareness` *(tier-1, deriva-skills, auto-fires)* carries the find-before-you-create discipline — the search applies to ML entities (Features) as well as generic catalog entities. `deriva_ml_create_feature` also warns about near-duplicates at create time.
- Can the existing feature be extended with new vocabulary terms?
- Is this really a feature, or should it be a column on the table? `/deriva:semantic-awareness` covers the EAV-vs-wide-table dual extreme — features map naturally to the middle ground (typed columns + FK-to-vocab), but if you find yourself reaching for one giant feature with many free-text fields, or one EAV-shaped feature whose `Value` carries every kind of label, step back and rethink.

## Phase 2: Design

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

## Phase 3: Create the Feature Definition

### Standard workflow

1. **Create vocabulary + terms** (if term-based; see `/deriva:manage-vocabulary` *(tier-1, deriva-skills)* for the generic vocabulary CRUD surface):
   ```
   create_vocabulary(hostname, catalog_id, schema="<schema>", table="Diagnosis_Type", comment="...")
   add_term(hostname, catalog_id, schema="<schema>", table="Diagnosis_Type", name="Normal", description="...")
   ```

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

## Phase 4: Add Feature Values

Adding values requires knowing what columns a feature has, which are required, and what values are valid. The full inspect → discover-valid-values → add → commit walkthrough lives in `references/workflow.md` under "Add Feature Values"; this section names the rule.

### Script vs MCP rule

| Situation | Approach |
|-----------|----------|
| Verifying a new feature works (1-5 test values) | MCP tools directly — quick and disposable |
| Production annotations, batch labels, model predictions | Committed script — provides code provenance in the execution record |

**For production data, always write a script first.** The execution record captures the git hash of the committed code. Without a committed script, the execution has provenance (who, when, what) but no code link (how). Use `/deriva-ml:catalog-operations-workflow` or `/deriva-ml:dataset-lifecycle`'s script templates to generate the script, commit it, then run via `deriva-ml-run`. Running an uncommitted script raises `DerivaMLDirtyWorkflowError` — use `--allow-dirty` only for debugging iterations (degraded provenance).

### Common mistakes

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Adding values without an execution | Error — provenance required | `deriva_ml_create_execution` + `deriva_ml_start_execution` first |
| Using MCP tools for production batch annotations | Works but no code provenance | Write and commit a script, run via `deriva-ml-run` |
| Using wrong term name | Error — must match vocabulary exactly | `rag_search("{vocab} terms", doc_type="catalog-schema")` or `list_vocabulary_terms(...)` |
| Missing required column | Error — required fields must be present | `rag_search("{feature} columns", doc_type="catalog-schema")` or `deriva_ml_get_feature(...)` |
| One execution per label | Works but clutters provenance | Batch labels from same source into one execution |
| Passing boolean as string `"true"`/`"false"` | Pydantic validation error | Pass as native bool: `true` / `false` (no quotes) |
| Forgetting `deriva_ml_commit_execution` | Execution stays "running" | Always commit (or `deriva_ml_abort_execution` on failure) after adding values |

## Phase 5: Query and Explore Feature Values

Feature queries fall into two categories. **Always choose the right one — never use preview tools to retrieve feature values.**

### Rule: "get values" = Python API; "explore shape" = preview

- **User asks to get, retrieve, list, or show feature values** → ALWAYS use the Python API via a script. Even for small numbers of values. Results stay out of context and are cached for reuse.
- **User asks exploratory questions** ("what features exist?", "what does this feature look like?", "what columns does it have?") → Preview tools (`get_table_sample_data`, `deriva_ml_denormalize_dataset`, `deriva_ml_list_features`, `deriva_ml_get_feature`) are fine for a small sample.

**NEVER use `query_attribute` or `get_table_sample_data` with large limits to retrieve feature values.** This dumps raw records into the conversation context, which is wasteful and doesn't support selectors or caching.

For the exploratory-preview MCP tool examples and the full Python API retrieval pattern (`ml.cache_features`, `ml.fetch_table_features`, `ml.list_feature_values`), see `references/workflow.md` under "Query Feature Values".

### Resolve multiple values with selectors

When a record has values from multiple annotators or model runs, use a selector to pick one. Built-in selectors include `select_newest`, `select_by_execution`, `select_by_workflow`, `select_majority_vote`. For the full guide — built-in selectors, custom selector functions, the cache-key warning, common pitfalls — see `references/feature-selectors.md`.

**Before retrieving in the multi-value case, ask the user which values they want.** Quick provenance check:

```python
all_values = list(ml.list_feature_values("Image", "Scouts_Pick"))
executions = set(r.Execution for r in all_values)
print(f"Total values: {len(all_values)}, from {len(executions)} execution(s): {executions}")
```

If multiple executions contributed, present only the relevant selector options based on the provenance check (e.g., offer "by workflow type" only if executions span different workflow types; offer "majority vote" only if multiple annotators have the same target).

## Integration with Datasets

- **In dataset bags** — feature values for dataset members are automatically included in BDBag exports
- **In `deriva_ml_denormalize_dataset`** — include feature tables to see labels alongside data. Column names: `{FeatureTableName}_{ColumnName}`
- **Dataset versioning** — adding feature values does NOT update existing versions. Call `deriva_ml_increment_dataset_version` after adding features to make them visible in new versions
- **In `deriva_ml_split_dataset`** — the `stratify_by_column` parameter references feature columns in denormalized format

## Reference Resources

- `references/concepts.md` — Feature types, design guidance, naming, multivalued features, selection, Python API, integration
- `references/workflow.md` — Step-by-step MCP and Python API examples for create / add-values / query
- `references/feature-selectors.md` — Complete guide to writing and using feature selectors
- `deriva://docs/features` — Full user guide to features in DerivaML
- `deriva_ml_list_features(hostname, catalog_id)` — Browse all existing features (target tables, types, columns)
- `deriva_ml_get_feature(hostname, catalog_id, target_table, feature_name)` — Feature details and column schema
- `deriva_ml_list_feature_values(hostname, catalog_id, target_table, feature_name, selector=...)` — Feature values with selectors and per-execution / per-workflow filtering

## Related Skills

- **`/deriva:manage-vocabulary`** *(tier-1, deriva-skills)* — Create and manage the controlled vocabularies that features reference.
- **`/deriva-ml:dataset-lifecycle`** — Features annotate records in datasets. Feature values are included in bag exports and affect dataset versioning.
- **`/deriva-ml:ml-data-engineering`** — Consuming feature values for ML training — restructuring, DataFrames, value selectors.
