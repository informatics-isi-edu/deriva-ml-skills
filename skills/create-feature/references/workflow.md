# Feature Workflow Reference

Step-by-step MCP tool and Python API examples for creating and populating features. For background concepts (feature types, multivalued features, selection), see the `concepts/` bundle (`concepts/design.md` for types & multivalued, `concepts/selectors.md` for selection).

> Every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them.

## Table of Contents

1. [Check Existing Features](#check-existing-features)
2. [Create a Vocabulary](#create-a-vocabulary-if-needed)
3. [Create the Feature](#create-the-feature)
4. [Add Feature Values](#add-feature-values) — MCP tools and Python API
5. [Query Feature Values](#query-feature-values) — Fetching and selecting
6. [Managing Features](#managing-features) — Delete, list
7. [Complete Example](#complete-example) — End-to-end MCP workflow
8. [Complete Example: Python API](#complete-example-python-api)
9. [Worked Example: Bulk-Populate from a CSV](#worked-example-bulk-populate-feature-values-from-a-csv) — With a LocalFile-input execution

---

## Check Existing Features

Before creating a new feature, review what already exists.

- Call `deriva_ml_list_features(hostname="data.example.org", catalog_id="1")` to list all features with their target tables and column schemas.
- Call `deriva_ml_get_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis")` for details on a specific feature.
- Check existing feature values with `deriva_ml_list_feature_values(hostname=..., catalog_id=..., target_table="Image", selector="newest")` to see what annotations already exist.

## Create a Vocabulary (if needed)

If your feature needs a new set of terms, create the vocabulary first.

Use `deriva_ml_create_vocabulary` to create the vocab table, then `add_term` for each term. See `deriva-ml-context` → "Creating a new vocabulary" for the rationale (curie prefix, default schema, navbar refresh) and when to fall back to the generic `create_vocabulary`.

In brief:
1. Call `deriva_ml_create_vocabulary(hostname="data.example.org", catalog_id="1", vocab_name="<vocab_name>", comment=...)`.
   - Optional: `schema=...` (defaults to the deriva-ml domain schema), `update_navbar=False` to skip the navbar refresh during batch creation.
2. Call `add_term(hostname="data.example.org", catalog_id="1", schema="<schema>", table="<vocab_name>", name=..., description=..., synonyms=[...])` for each term. (`add_term` lives in deriva-mcp-core; there is no ML-specific variant.)

**Always provide meaningful descriptions for terms.** They appear in the UI and help annotators understand what each label means.

## Create the Feature

Call `deriva_ml_create_feature` with:
- `hostname`, `catalog_id`
- `target_table`: the target table whose records will be labeled (e.g., `"Image"`)
- `feature_name`: unique name for the feature (e.g., `"Tumor_Classification"`)
- `comment`: description of what this feature represents
- `terms` (optional): list of vocabulary table names whose terms can be values (e.g., `["Tumor_Grade"]`)
- `assets` (optional): list of asset table names that can be referenced (e.g., `["Mask_Image"]`)
- `metadata` (optional): list of additional columns — see `concepts/design.md` for format details

At least one of `terms` or `assets` is required.

This creates the feature record and a `Execution_{TargetTable}_{FeatureName}` association table.

### Examples

**Term-based feature** (classification labels): call with `target_table`: `"Image"`, `feature_name`: `"Tumor_Classification"`, `terms`: `["Tumor_Grade"]`.

**Asset-based feature** (segmentation masks): call with `target_table`: `"Image"`, `feature_name`: `"Segmentation_Mask"`, `assets`: `["Mask_Image"]`. (Asset tables are created via the generic `create_table` tool with the standard hatrac column shape — see `/deriva:create-table` *(deriva-skills)*.)

**Mixed feature** (labels with overlays): include both `terms` and `assets`.

**Feature with metadata** (confidence scores): add `metadata`: `[{"name": "confidence", "type": {"typename": "float4"}}]`.

## Add Feature Values

Feature values require an active execution for provenance tracking. Every label assignment is tied to the execution that created it.

### Bundled script template

The canonical entry point is `skills/create-feature/scripts/populate_feature_values.py`. Copy it into the user's project (typically `src/scripts/populate_<feature>.py`), edit the CSV path / feature name, commit, then run via `deriva-ml-run`. The template handles workflow creation, execution context, validation, `add_features()` staging, and commit — all with the typed argparse skeleton and `--dry-run` flag.

```bash
# 1. Copy + customize
cp skills/create-feature/scripts/populate_feature_values.py \
   src/scripts/populate_tumor_classification.py
# Edit the script: set target_table, feature_name, CSV column mapping.

# 2. Commit so the workflow URL + commit hash resolve to real code
git add src/scripts/populate_tumor_classification.py
git commit -m "feat(scripts): populate Tumor_Classification feature values"

# 3. Run dry-first
uv run python src/scripts/populate_tumor_classification.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Annotation \
    --csv ./labels/tumor_grades.csv \
    --target-table Image --feature-name Tumor_Classification \
    --dry-run

# 4. Production run (drop --dry-run)
uv run python src/scripts/populate_tumor_classification.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Annotation \
    --csv ./labels/tumor_grades.csv \
    --target-table Image --feature-name Tumor_Classification
```

Inside the template, the work block builds typed `FeatureRecord` objects, calls `execution.add_features(records)` to stage them, and the post-`with`-block `execution.commit_output_assets()` flushes them to the catalog. Pydantic validates each row against the feature's term vocabulary; mismatched terms raise `DerivaMLInvalidTerm` immediately.

For multi-column features, edit the `RecordClass(**row)` instantiation in the loop to map CSV columns to the feature's columns. For asset-based features, set the asset reference column to the asset RID.

### Python API with context manager

```python
from deriva_ml import DerivaML, ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)
workflow = ml.lookup_workflow_by_url("https://github.com/my-org/my-repo")

config = ExecutionConfiguration(
    workflow=workflow,
    description="Expert pathologist tumor grading"
)

with ml.create_execution(config) as exe:
    # Look up the feature and get its record class
    feature = exe.catalog.lookup_feature("Image", "Tumor_Classification")
    RecordClass = feature.feature_record_class()

    # Create feature records
    records = [
        RecordClass(Image="2-IMG1", Tumor_Grade="Grade II"),
        RecordClass(Image="2-IMG2", Tumor_Grade="Grade III"),
    ]

    # Bulk add from a results dict
    for image_rid, grade in labeling_results.items():
        records.append(RecordClass(Image=image_rid, Tumor_Grade=grade))

    # Add all records in batch (execution RID set automatically)
    exe.add_features(records)
    # Feature values are uploaded automatically on context exit
```

## Query Feature Values

### Preferred: Use the typed feature tool

Always prefer the dedicated `deriva_ml_list_feature_values` tool over generic table queries:

Call `deriva_ml_list_feature_values` with:
- `hostname`, `catalog_id`
- `target_table`: the target table (e.g., `"Image"`)
- `feature_name` (optional): fetch only a specific feature
- `selector`: `"newest"` / `"first"` / `"latest"` / `"majority_vote"` to pick one value per record
- `workflow`: a Workflow RID or Workflow_Type name to filter by source workflow
- `execution`: an Execution RID to filter by a specific execution run

Only one of `selector`, `workflow`, or `execution` may be specified. See `concepts/selectors.md` for the full Python API including custom selectors.

### Fallback: Filtered queries on the feature value table

When you need to filter feature values by specific column values (e.g., "all images with Grade III"), query the feature value table directly with `get_entities` for whole-row reads, or `query_attribute` for column projection / FK joins:

```python
# Whole-row read filtered by feature column
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="<schema>", table="Execution_Image_Tumor_Classification",
    filters={"Tumor_Grade": "Grade III"},
)

# Or scope to a specific image
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="<schema>", table="Execution_Image_Tumor_Classification",
    filters={"Image": "2-IMG1"},
)

# Project specific columns or join — use query_attribute with path syntax
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="<schema>:Execution_Image_Tumor_Classification/Tumor_Grade=Grade%20III",
    attributes=["RID", "Image", "Tumor_Grade", "Confidence"],
)
```

This is the case where reaching past the dedicated feature-value tool is appropriate — that tool doesn't support arbitrary column filters.

## Managing Features

To **delete a feature**, call `deriva_ml_delete_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Diagnosis")`. This removes the feature and its value table — existing data will be lost.

To **list all features**, call `deriva_ml_list_features(hostname="data.example.org", catalog_id="1")`.

## Complete Example

End-to-end MCP workflow: create a vocabulary, create a feature, and add values.

**Step 1:** Create the vocabulary.

Call `deriva_ml_create_vocabulary(hostname="data.example.org", catalog_id="1", vocab_name="Cell_Type", comment="Cell type classifications for microscopy images")`. (Effects per `deriva-ml-context` → "Creating a new vocabulary": lands in the deriva-ml domain schema, terms carry `{project}:{RID}` curies, navbar refreshes.)

Then call `add_term` for each term (from deriva-mcp-core — no ML-specific variant):
- `add_term(hostname="data.example.org", catalog_id="1", schema="<schema>", table="Cell_Type", name="Epithelial", description="Epithelial cells lining surfaces and cavities")`
- `add_term(...table="Cell_Type", name="Stromal", description="Connective tissue support cells")`
- `add_term(...table="Cell_Type", name="Immune", description="Immune system cells including lymphocytes and macrophages")`
- `add_term(...table="Cell_Type", name="Necrotic", description="Dead or dying cells")`

**Step 2:** Create the feature.

Call `deriva_ml_create_feature(hostname="data.example.org", catalog_id="1", target_table="Image", feature_name="Cell_Classification", terms=["Cell_Type"], comment="Primary cell type visible in microscopy image")`.

**Step 3:** Add values within an execution.

Copy `skills/create-feature/scripts/populate_feature_values.py` to `src/scripts/populate_cell_classification.py`. Edit the `target_table` and `feature_name` arguments (already CLI-driven), or hardcode for this specific use case. Stage a CSV with columns `Image` (the target table's RID column) and `Cell_Type` (the feature's term column), commit the script, then run:

```bash
uv run python src/scripts/populate_cell_classification.py \
    --hostname data.example.org --catalog-id 1 \
    --workflow-type Annotation \
    --csv ./annotations/cell_types_batch1.csv \
    --target-table Image --feature-name Cell_Classification
```

The script's `with ml.create_execution(...) as exe:` block stages the values via `exe.add_features(records)`; `exe.commit_output_assets()` post-context flushes them to the catalog. Each value carries provenance back to the committed script (workflow URL + git commit) and the execution.

## Complete Example: Python API

```python
from deriva_ml import DerivaML, ExecutionConfiguration

ml = DerivaML(hostname, catalog_id)

# 1. Create vocabulary and terms
ml.create_vocabulary("Cell_Type", comment="Cell type classifications")
ml.add_term("Cell_Type", "Epithelial", description="Epithelial cells lining surfaces")
ml.add_term("Cell_Type", "Stromal", description="Connective tissue support cells")
ml.add_term("Cell_Type", "Immune", description="Immune system cells")

# 2. Create the feature
ml.create_feature("Image", "Cell_Classification",
                   terms=["Cell_Type"],
                   comment="Primary cell type visible in microscopy image")

# 3. Add values within an execution
workflow = ml.create_workflow(
    name="Expert Cell Annotation",
    workflow_type="Annotation",
    description="Expert cell type annotation"
)

with ml.create_execution(ExecutionConfiguration(workflow=workflow)) as exe:
    feature = exe.catalog.lookup_feature("Image", "Cell_Classification")
    RecordClass = feature.feature_record_class()

    records = [
        RecordClass(Image="2-IMG1", Cell_Type="Epithelial"),
        RecordClass(Image="2-IMG2", Cell_Type="Immune"),
    ]
    exe.add_features(records)
    # Feature values are uploaded automatically on context exit
```

## Worked example: bulk-populate feature values from a CSV

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
    ml = DerivaML(hostname=hostname, catalog_id=catalog_id)
    # Confirm auth before the first catalog op (clear failure now, not a 401
    # mid-populate). `check_auth=` is not a DerivaML kwarg; the check is this call.
    if not ml.is_authenticated():
        raise SystemExit(f"Not authenticated to {hostname} — run: deriva-globus-auth-utils login --host {hostname}")

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

### If the script crashes mid-ingest

The Execution is recoverable. See `/deriva-ml:troubleshoot-execution` "Salvage a Failed Execution" — the three-branch decision tree (salvage staged work via `salvage_execution.py`, recovery execution from inputs, or recovery execution that claims survivors as inputs) applies directly. The CSV's `LocalFile` Input edge stays recorded even if some feature values failed to upload.
