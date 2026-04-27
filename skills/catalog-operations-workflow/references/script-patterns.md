# Script Pattern Templates for Catalog Operations

Reusable Python script templates for common DerivaML catalog operations. Each pattern follows the Develop, Test, Commit, Run workflow described in the parent skill.

## Table of Contents

- [Base Script Template](#base-script-template)
- [Dataset Creation](#dataset-creation)
- [Dataset Splitting](#dataset-splitting)
- [Feature Creation and Population](#feature-creation-and-population)
- [ETL / Data Loading](#etl--data-loading)

---

## Base Script Template

The foundation for all catalog operation scripts. Every script should follow this structure.

```python
#!/usr/bin/env python
"""<Description of what this script does>."""

import argparse
import sys

from deriva_ml import DerivaML
from deriva_ml.execution import ExecutionConfiguration


def ensure_vocab_terms(ml: DerivaML, vocab_table: str, terms: dict[str, str]) -> None:
    """Ensure vocabulary terms exist, creating any that are missing.

    Catalog clones may not have all vocabulary terms from the source catalog.
    Always call this before using terms in create_dataset, create_workflow, etc.

    Args:
        ml: Connected DerivaML instance.
        vocab_table: Vocabulary table name (e.g., "Workflow_Type", "Dataset_Type").
        terms: Dict mapping term name to description for each required term.
    """
    existing = {t.name for t in ml.list_vocabulary_terms(vocab_table)}
    for name, description in terms.items():
        if name not in existing:
            print(f"  Creating {vocab_table} term: {name}")
            ml.add_term(vocab_table, name, description)


def main():
    parser = argparse.ArgumentParser(description="<Script description>")
    parser.add_argument("--hostname", required=True, help="Deriva server hostname")
    parser.add_argument("--catalog-id", required=True, help="Catalog ID")
    parser.add_argument("--schema", default=None,
                        help="Domain schema name (auto-detected if single schema)")
    parser.add_argument("--workflow-type", default="Data_Management",
                        help="Workflow type (created if not in catalog)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Test without creating records")
    args = parser.parse_args()

    # Connect to catalog.
    try:
        ml = DerivaML(hostname=args.hostname, catalog_id=args.catalog_id)
    except Exception as e:
        print(f"ERROR: Failed to connect to {args.hostname} catalog {args.catalog_id}: {e}",
              file=sys.stderr)
        return 1

    # Set default schema: use --schema if provided, auto-detect if single schema,
    # error if multiple schemas and no --schema.
    if args.schema:
        ml.default_schema = args.schema
    elif len(ml.domain_schemas) == 1:
        ml.default_schema = next(iter(ml.domain_schemas))
    else:
        print(f"ERROR: Multiple domain schemas found: {ml.domain_schemas}. "
              f"Use --schema to specify.", file=sys.stderr)
        return 1

    # Ensure all required vocabulary terms exist before using them.
    # Catalog clones often have empty vocabulary tables.
    ensure_vocab_terms(ml, "Workflow_Type", {
        args.workflow_type: "Description of this workflow type",
    })
    ensure_vocab_terms(ml, "Dataset_Type", {
        "Complete": "A dataset containing all available records of a given type.",
        # Add any other dataset types your script uses here.
    })

    workflow = ml.create_workflow(
        name="My Operation",
        workflow_type=args.workflow_type,
        description="..."
    )

    config = ExecutionConfiguration(
        description="...",
    )

    # The workflow is passed to create_execution, not to ExecutionConfiguration.
    with ml.create_execution(config, workflow=workflow, dry_run=args.dry_run) as execution:
        # Perform operations
        ...

    execution.upload_execution_outputs()

if __name__ == "__main__":
    sys.exit(main())
```

Key elements:
- `argparse` with `--hostname`, `--catalog-id`, `--schema`, `--workflow-type`, and `--dry-run` as standard CLI arguments
- **No hardcoded values** for workflow types, schema names, or table names — accept from CLI or auto-detect
- Set `ml.default_schema` with auto-detection when there is exactly one domain schema
- **Ensure all vocabulary terms exist** before use — call `ensure_vocab_terms` for every vocabulary table you reference (Workflow_Type, Dataset_Type, etc.). Catalog clones often have empty vocabulary tables
- When adding members, use `{table: [rids]}` dict form with `validate=False` for large datasets — the flat list form triggers expensive per-RID table resolution
- `ExecutionConfiguration` takes `description` (and optionally `datasets`, `assets`); the `workflow` goes to `create_execution()` separately
- `ml.pathBuilder()` is a **method call** (not a property) — use `pb = ml.pathBuilder()`
- `pb.schemas[schema].tables[table].entities()` returns a lazy iterator — wrap with `list()` to materialize
- `execution.upload_execution_outputs()` is called **after** the `with` block — the execution object remains valid for upload after the context closes
- Wrap `DerivaML()` in try/except for connection errors
- **Do NOT add CLI entry points** in `pyproject.toml` for these scripts. They are one-time catalog operations, not reusable tools. Run with `uv run python src/scripts/<script>.py`.

---

## Dataset Creation

Create a new dataset and populate it with members.

```python
# Query records using pathBuilder (method call, not property).
pb = ml.pathBuilder()
table = pb.schemas[ml.default_schema].tables[args.table]
entities = list(table.entities())  # list() to materialize the lazy iterator
all_rids = [e["RID"] for e in entities]

if not all_rids:
    print(f"ERROR: No records found in {args.table}. Aborting.")
    return 1

if args.dry_run:
    print(f"[DRY RUN] Would create dataset with {len(all_rids)} members")
    return 0

with ml.create_execution(config, workflow=workflow, dry_run=args.dry_run) as execution:
    dataset = execution.create_dataset(
        dataset_types=["Complete"],
        description=f"All {len(all_rids)} records from {args.table}.",
    )

    # Use dict form {table: [rids]} with validate=False for large datasets.
    # The flat list form triggers per-RID table resolution which is slow and
    # can fail if the RID resolver doesn't cover the target table.
    dataset.add_dataset_members(
        {args.table: all_rids}, validate=False
    )

execution.upload_execution_outputs()
```

---

## Dataset Splitting

Split an existing dataset into train/val/test partitions with optional stratification.

```python
from deriva_ml.dataset.split import split_dataset

# Derive the stratify column name from the schema:
#   Feature table: Execution_Image_Image_Classification
#   Column: Image_Class
#   Denormalized name: Execution_Image_Image_Classification_Image_Class

splits = split_dataset(
    ml,
    source_dataset_rid="1-ABC4",
    test_size=0.1,
    val_size=0.1,
    stratify_by_column="Execution_Image_Image_Classification_Image_Class",
    stratify_missing="drop",  # "error" (default), "drop", or "include"
    include_tables=["Image", "Execution_Image_Image_Classification"],
    seed=42,
)
```

---

## Feature Creation and Population

Create a new feature and populate it with values.

```python
with ml.create_execution(config, workflow=workflow, dry_run=args.dry_run) as execution:
    ml.create_feature(
        table_name="Image",
        feature_name="Severity",
        terms=["Severity_Grade"],
        comment="Severity grading for chest X-ray findings.",
    )

    feature = ml.lookup_feature("Image", "Severity")
    RecordClass = feature.feature_record_class()

    records = []
    for image_rid, severity in annotations.items():
        records.append(RecordClass(Image=image_rid, Severity_Grade=severity))
    execution.add_features(records)

execution.upload_execution_outputs()
```

---

## ETL / Data Loading

Load data from an external source, transform it, and insert into the catalog.

```python
with ml.create_execution(config, workflow=workflow, dry_run=args.dry_run) as execution:
    # Load data from external source
    data = load_external_data(args.source)

    # pathBuilder() is a method call — returns a path builder instance.
    pb = ml.pathBuilder()
    table = pb.schemas[ml.default_schema].tables["TargetTable"]
    table.insert(transform(data))

execution.upload_execution_outputs()
```
