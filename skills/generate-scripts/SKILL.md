---
name: generate-scripts
description: "Use this skill whenever Claude needs to generate a Python script that interacts with a Deriva catalog — whether for data exploration, bulk data access, loading data, creating features, uploading assets, or any operation that exceeds what MCP tools can return (>100 rows). Covers two script categories: exploration scripts (ephemeral, for previewing/analyzing data) and catalog-modifying scripts (committed, with execution provenance). Triggers on: 'write a script', 'generate a script', 'fetch all records', 'get all features', 'load data into catalog', 'bulk insert', 'upload results', 'I need more than 100 rows', 'cache the data', 'run this analysis', 'compute metrics across all images'. Also triggers implicitly when preview_table or preview_denormalized_dataset returns truncated results and the user needs the full dataset."
disable-model-invocation: true
---

# Script Generation for DerivaML

When MCP tools return truncated results (preview_table and preview_denormalized_dataset cap at 100 rows), or when operations need to modify the catalog (load data, create features, upload assets), Claude generates Python scripts that use the DerivaML Python API directly.

> **RAG-first:** Before generating a script, use `rag_search()` to discover relevant catalog entities (tables, features, datasets, vocabulary terms) so the generated script references the correct names, RIDs, and column types.

> **Note:** This skill generates Python scripts that use the DerivaML Python API directly, not MCP tools. Methods like `ml.cache_table()`, `ml.working_data`, `dataset.cache_denormalized()`, `ml.cache_features()`, `ml.denormalize_info()`, `dataset.denormalize_info()`, `ml.create_workflow()`, `ml.create_execution()`, and `execution.asset_file_path()` are all Python API methods available in scripts and notebooks, not MCP tools.

## Two Categories of Scripts

### Category 1: Exploration Scripts (Ephemeral)

**Purpose:** Fetch bulk data, compute statistics, produce plots, analyze distributions.

**Rules:**
- Do NOT commit to repo — these are throwaway
- Do NOT create executions — no provenance needed
- DO use the working data cache (`ml.cache_table()`, `ml.cache_features()`, etc.)
- DO print summary output so Claude can read the results
- Save to a temporary file or run inline

**Template:**
```python
from deriva_ml import DerivaML
import pandas as pd

ml = DerivaML.from_context()

# Fetch and cache (idempotent — reuses cached data on repeat runs)
df = ml.cache_table("Image")
print(f"Total images: {len(df)}")
print(df.describe())

# Or denormalize a dataset
dataset = ml.lookup_dataset("28CT")
wide = dataset.cache_denormalized(["Image", "Image_Diagnosis"], version="1.0.0")
print(wide["Image_Diagnosis.Diagnosis_Image"].value_counts())

# Or fetch features
labels = ml.cache_features("Image", "Classification")
print(f"Labeled images: {len(labels)}")
print(labels["Diagnosis_Type"].value_counts())
```

**When to use exploration scripts:**
- User asks "how many images have each diagnosis?"
- User asks "show me the distribution of ages"
- User asks "what does the denormalized data look like?"
- preview_table returned 100 rows but user needs counts/stats on the full table
- Any read-only analysis that doesn't change the catalog

### Category 2: Catalog-Modifying Scripts (Committed)

**Purpose:** Load data, create features, upload assets, produce outputs that go into the catalog.

**Rules:**
- **MUST be committed to the repo** before running (code provenance)
- **MUST create an execution** (provenance tracking)
- **MUST be documented** in experiment-decisions.md (via maintain-experiment-notes skill)
- Save to `scripts/` directory in the project
- Use the execution context manager pattern

**Template:**
```python
#!/usr/bin/env python
"""Load diagnosis labels into the catalog.

This script reads diagnosis labels from a CSV file and adds them as
feature values on the Image table. Creates an execution for provenance.

Usage:
    uv run python scripts/load_diagnoses.py
"""
from pathlib import Path

from deriva_ml import DerivaML
from deriva_ml.execution import ExecutionConfiguration

ml = DerivaML.from_context()

# Create execution for provenance
workflow = ml.create_workflow(name="Load Diagnoses", workflow_type="Data Import")
config = ExecutionConfiguration(workflow=workflow)
execution = ml.create_execution(config)

with execution.execute() as exe:
    # Load source data
    import pandas as pd
    labels = pd.read_csv("data/diagnoses.csv")

    # Add feature values
    for _, row in labels.iterrows():
        ml.add_feature_value(
            "Image", "Diagnosis",
            target_rid=row["Image_RID"],
            value=row["Diagnosis_Label"],
        )

    # Register any output files
    # path = exe.asset_file_path("Report", "summary.json")
    # ... write to path ...

# Upload AFTER the with block
exe.upload_execution_outputs()

print(f"Loaded {len(labels)} diagnosis labels")
print(f"Execution: {execution.execution_rid}")
```

**When to use catalog-modifying scripts:**
- Loading data from external files (CSV, JSON) into catalog tables
- Computing and storing feature values (labels, scores, predictions)
- Uploading model weights or other assets
- Any operation that writes to the catalog

## Script Lifecycle

### For Exploration Scripts:
1. Claude generates the script inline or as a temp file
2. Script runs, prints results
3. Claude reads the output and responds to user
4. Script is not saved long-term

### For Catalog-Modifying Scripts:
1. Claude generates the script in `scripts/` directory
2. Claude commits the script: `git add scripts/load_diagnoses.py && git commit`
3. Claude runs the script: `uv run python scripts/load_diagnoses.py`
4. Claude documents in experiment-decisions.md (maintain-experiment-notes skill):
   - What the script does
   - Why it was created
   - What execution RID was produced
5. Script stays in repo for reproducibility

## Working Data Cache Pattern

All scripts should use the working data cache for bulk reads:

```python
ml = DerivaML.from_context()

# These are idempotent — fetch once, cache in SQLite, reuse on subsequent calls
subjects = ml.cache_table("Subject")
features = ml.cache_features("Image", "Classification")
wide = ml.lookup_dataset("28CT").cache_denormalized(["Image", "Diagnosis"])

# Check what's cached
print(ml.working_data.list_tables())

# Query cached data with SQL (no catalog contact)
old_subjects = ml.working_data.query("SELECT * FROM Subject WHERE Age > 60")

# Force re-fetch if data changed
subjects = ml.cache_table("Subject", force=True)

# Clear cache when done
ml.working_data.clear()
```

## Connection Context

All scripts use `DerivaML.from_context()` which reads `.deriva-context.json` written by the MCP `connect_catalog` tool. This file contains hostname, catalog_id, default_schema, and working_dir.

**Never hardcode connection details in scripts.** Always use `from_context()`.

## Script Naming Conventions

| Type | Location | Naming |
|------|----------|--------|
| Exploration | Inline or `/tmp/` | `explore_*.py` |
| Data loading | `scripts/` | `load_*.py` |
| Feature computation | `scripts/` | `compute_*.py` |
| Asset generation | `scripts/` | `generate_*.py` |
| Data migration | `scripts/` | `migrate_*.py` |

## Decision: Exploration vs. Catalog-Modifying

Ask yourself: **Does this script change the catalog?**

| Action | Category | Needs Commit? | Needs Execution? |
|--------|----------|---------------|------------------|
| Count records | Exploration | No | No |
| Compute statistics | Exploration | No | No |
| Plot distributions | Exploration | No | No |
| Fetch and analyze features | Exploration | No | No |
| Insert records | Catalog-modifying | **Yes** | **Yes** |
| Add feature values | Catalog-modifying | **Yes** | **Yes** |
| Upload assets | Catalog-modifying | **Yes** | **Yes** |
| Create datasets | Catalog-modifying | **Yes** | **Yes** |
| Modify vocabulary terms | Catalog-modifying | **Yes** | **Yes** |

## Related Skills

- **maintain-experiment-notes** — Document catalog-modifying scripts in experiment-decisions.md
- **execution-lifecycle** — Execution context manager pattern for provenance
- **coding-guidelines** — Code style, git workflow, commit conventions
- **work-with-assets** — Asset upload patterns (Python API)
- **dataset-lifecycle** — Dataset operations that scripts may perform
