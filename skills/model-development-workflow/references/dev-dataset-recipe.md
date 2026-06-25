# Development Dataset Recipe

The fast-path recipe for creating a small, throwaway development dataset during
the model-development bootstrap (Phase 3 of `/deriva-ml:model-development-workflow`).
This is the dataset you'll use for tiers 1 and 2.

For the dataset's own design, structure, typing, and versioning decisions —
and whenever the dev dataset becomes something you'll reuse or cite — route
through `/deriva-ml:dataset-lifecycle`, which is the canonical home for dataset
creation.

## What "representative" means

A development dataset should:
- Have **50–200 records** (enough to test pipelines, small enough to iterate fast)
- Include **all classes** in your classification task (at least 5–10 per class)
- Cover **edge cases** you know about (missing values, unusual formats)
- Be **labeled** if your workflow needs labels

## How to create it

```
# 1. Register Image as a dataset element type
deriva_ml_add_dataset_element_type(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<dev_dataset>",
    element_table="Image",
)

# 2. Create the development dataset
deriva_ml_create_dataset(
    hostname="data.example.org",
    catalog_id="1",
    description="Development subset: 100 chest X-rays, ~20 per diagnosis class, for pipeline validation",
    dataset_types=["Development"],
)

# 3. Add a representative sample of members
# Query to find records spanning all classes:
deriva_ml_denormalize_dataset(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<source>",
    include_tables=["Image", "Image_Diagnosis"],
    limit=200,
)
# Pick records that cover all classes, then:
deriva_ml_add_dataset_members(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<dev_dataset>",
    members=[...selected RIDs...],
)
```

## Create a "Development" dataset type

If your catalog doesn't have a "Development" type yet, use the generic `add_term` tool against the `Dataset_Type` vocabulary:

```
add_term(
    hostname="data.example.org",
    catalog_id="1",
    schema="deriva-ml",
    table="Dataset_Type",
    name="Development",
    description="Small representative subset used for pipeline development, debugging, and rapid iteration. Not for production training.",
    synonyms=["Dev", "Debug"],
)
```

## Pin to a released version

After populating the development subset (which will have flipped `current_version` to a dev label per ADR-0003), call `deriva_ml_release_dataset` to mint a citable release that configs can pin to:

```
deriva_ml_release_dataset(
    hostname="data.example.org",
    catalog_id="1",
    dataset_rid="<dev_dataset>",
    bump="minor",
    description="Initial development subset with balanced class representation",
)
```

Use `deriva_ml_get_dataset_spec(hostname="data.example.org", catalog_id="1", dataset_rid="<dev_dataset>")` to get the `DatasetSpecConfig` for your config files. Always pin configs to a released label (no `.devN` suffix) — dev labels are mutable.
