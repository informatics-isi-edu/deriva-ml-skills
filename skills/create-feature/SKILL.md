---
name: create-feature
description: "ALWAYS use this skill when creating features, adding labels or annotations to records, setting up classification categories, querying or exploring feature values, or working with feature values in DerivaML. Covers: feature-vs-column decision, discovering existing features, single vs multi-column design, creating vocabularies and features, adding feature values with provenance, querying/browsing feature values, selecting among multiple annotations, caching, and how features integrate with datasets. Triggers on: 'create feature', 'add labels', 'annotate images', 'classification', 'ground truth', 'confidence score', 'feature values', 'what features exist', 'explore annotations', 'show feature values', 'query features', 'what are the labels', 'list annotations', 'browse features', 'feature preview'."
disable-model-invocation: false
---

# Creating and Populating Features in DerivaML

Features link domain objects (e.g., Image, Subject) to structured values — controlled vocabulary terms, computed values, or assets — with full provenance tracking through executions.

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly.

## Phase 1: Assess

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

## Phase 4: Add Feature Values

Adding values requires knowing what columns a feature has, which are required, and what values are valid. The full inspect → discover-valid-values → add → commit walkthrough lives in `references/workflow.md` under "Add Feature Values"; this section names the rule.

### Script vs MCP rule

| Situation | Approach |
|-----------|----------|
| Verifying a new feature works (1-5 test values) | MCP tools directly — quick and disposable |
| Production annotations, batch labels, model predictions | Committed script — provides code provenance in the execution record |

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

The most common production pattern: a domain expert hands you a CSV of ground-truth values (image RIDs + diagnosis labels, sample IDs + quality scores, etc.) and you load them into a Feature. Walk this end-to-end so the resulting feature values are fully reproducible.

**The canonical entry point is the bundled template** `skills/create-feature/scripts/populate_feature_values.py`. Copy it into the user's project (typically `src/scripts/`), edit the CSV path and the feature name, commit, then run with `deriva-ml-run`. The script encodes the validate → execute → commit pattern with full provenance.

For tasks that need additional work beyond a flat-CSV load (e.g., declaring the source CSV as a `LocalFile` input of the execution, custom validation, multi-column features), here's the same pattern fleshed out — copy as a starting point and adapt:

```python
# src/scripts/ingest_image_quality.py
"""Load Image_Quality feature values from a ground-truth CSV.

The CSV is declared as a LocalFile input on the execution, so anyone
walking the provenance chain (`deriva_ml_get_lineage(rid=<feature_value_rid>)`)
sees Execution → Workflow (this script's git commit) → input File (the CSV).
The LocalFile is registered as a referenced File row + Input edge — the CSV
bytes are NOT uploaded to Hatrac (right for source files that should stay local).
"""
from pathlib import Path
import argparse
import pandas as pd
from deriva_ml import DerivaML, ExecutionConfiguration
from deriva_ml.execution import LocalFile

def main(hostname: str, catalog_id: str, csv_path: Path) -> int:
    ml = DerivaML(hostname=hostname, catalog_id=catalog_id, check_auth=True)

    # 1. Validate the CSV up front — fail loudly before any catalog mutation.
    df = pd.read_csv(csv_path)
    required_cols = {"Image_RID", "Quality_Score"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    # Validate that referenced RIDs exist. For 100s of rows this is cheap;
    # for 100k rows, batch the existence check.
    existing_rids = {a.asset_rid for a in ml.list_assets("Image")}
    unknown = set(df["Image_RID"]) - existing_rids
    if unknown:
        raise ValueError(f"CSV references {len(unknown)} unknown Image RIDs: "
                         f"{sorted(unknown)[:5]}{'...' if len(unknown) > 5 else ''}")

    # 2. Create a Workflow for this script and an Execution that consumes the CSV.
    #    The workflow's source-code URL + git commit is captured by deriva-ml from
    #    the script's git context. The CSV is declared as a LocalFile input so the
    #    full source-of-truth chain survives — the framework registers it as a
    #    referenced File row + Input edge (role from context), WITHOUT uploading
    #    the bytes to Hatrac.
    workflow = ml.create_workflow(
        name="Image Quality Ingest",
        workflow_type="Data_Load",   # add this term to Workflow_Type if missing
        description=f"Load Image_Quality feature values from {csv_path.name}",
    )
    config = ExecutionConfiguration(
        workflow=workflow,
        assets=[LocalFile(path=str(csv_path))],   # source CSV → File row + Input edge
    )

    # 3. Build feature records, then write them inside the Execution context.
    ImageQuality = ml.feature_record_class("Image", "Image_Quality")
    records = [
        ImageQuality(Image=row["Image_RID"], Quality_Score=row["Quality_Score"])
        for _, row in df.iterrows()
    ]

    with ml.create_execution(config) as exe:
        # The CSV's provenance (File row + Input edge) is recorded by the
        # framework from the LocalFile declared above — nothing to capture here.
        exe.add_features(records)
        print(f"Added {len(records)} Image_Quality values "
              f"in execution {exe.execution_rid}")

    # Upload after the context exits — this is where assets and feature values
    # become visible. See /deriva-ml:execution-lifecycle for the lifecycle rules.
    exe.commit_output_assets(clean_folder=True)
    return 0

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--hostname", required=True)
    p.add_argument("--catalog-id", required=True)
    p.add_argument("--csv", type=Path, required=True)
    a = p.parse_args()
    raise SystemExit(main(a.hostname, a.catalog_id, a.csv))
```

**Run it after committing:**

```bash
git add src/scripts/ingest_image_quality.py && git commit -m "feat: image-quality ingest script"
uv run python src/scripts/ingest_image_quality.py \
    --hostname data.example.org --catalog-id 1 --csv ./labels/quality_2026Q2.csv
```

The git commit is mandatory — `ml.create_workflow(...)` raises `DerivaMLDirtyWorkflowError` if the working tree is dirty. Without the commit, the workflow's source-code URL has nothing reproducible to point at. `--allow-dirty` is only for local debugging iterations where you accept degraded provenance; never for the run that produces values that anyone will reference later.

**What you get afterward:** every feature value links to the execution, the execution links to the workflow (this script at this git commit), and the execution has the CSV declared as a `LocalFile` input (a referenced `File` row + Input edge). `deriva_ml_get_lineage(rid=<any feature value RID>)` walks the full chain back to the CSV. If a year from now someone asks "what data produced these labels?", the answer is in the catalog, not in someone's downloads folder.

#### If the script crashes mid-ingest

The Execution is recoverable. See `/deriva-ml:troubleshoot-execution` "Salvage a Failed Execution" — the three-branch decision tree (salvage staged work via `salvage_execution.py`, recovery execution from inputs, or recovery execution that claims survivors as inputs) applies directly. The CSV's `LocalFile` Input edge stays recorded even if some feature values failed to upload.

## Phase 5: Query and Explore Feature Values

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
