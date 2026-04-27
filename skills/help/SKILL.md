---
name: help
description: "Use this skill when the user asks general questions about DerivaML, Deriva, deriva-mcp, or what they can do with these tools — including 'what is DerivaML', 'how do I use Deriva', 'what can you help me with', 'how does this work', or 'where do I start'. Also trigger for broad orientation questions about catalogs, datasets, experiments, hydra-zen configuration, ML workflows, or the MCP server when the user seems to be asking 'how do I approach this' rather than requesting a specific action. ALWAYS prefer this skill for general 'what/how/why' questions about the DerivaML ecosystem before routing to more specific skills."
---

# DerivaML Capabilities Guide

When the user asks what's possible or needs orientation, present the following guide. Tailor your response to their context — if they mention a specific area, focus on that section. If they're brand new, give the full overview.

## What I Can Help You With

### Set Up Your Environment
- Set up a new DerivaML project from a template
- Install Jupyter kernels and configure notebook dependencies
- Authenticate with Deriva/Globus
- **Check if your DerivaML ecosystem is up to date** — two version checks:
  - `/deriva:check-deriva-versions` *(tier-1, deriva-skills)* covers the foundation: deriva-py + deriva-mcp-core + the deriva plugin
  - `/deriva-ml:check-deriva-ml-versions` *(this plugin)* covers the DerivaML layer: deriva-ml + deriva-ml-mcp + deriva-ml-skills (this plugin)

  Run the tier-1 check first; the tier-2 stack depends on it. Or just ask *"check versions"*.
- Configure linting, docstrings, and coding standards

**Just ask:** *"help me set up my environment"*, *"am I up to date?"*, or *"check deriva versions"*

### Define Your Catalog Structure
- Create tables for your domain data (images, subjects, samples, etc.)
- Create asset tables for storing files (images, model weights, CSVs)
- Add columns, foreign keys, and constraints
- Set up controlled vocabularies with terms and synonyms
- Customize how tables appear in the Chaise web UI

**Just ask:** *"create a table for patient images"* or *"set up a vocabulary for diagnosis types"*

### Explore Your Catalog
- **Discover what's in your catalog** using natural language search — tables, features, vocabularies, datasets, and experiments are all indexed and searchable via `rag_search`
- Query and filter catalog tables
- Look up records by RID
- Count records, sample data, browse vocabularies

| Question | How to find out |
|----------|----------------|
| "What tables exist?" | `rag_search("tables and their purpose", doc_type="catalog-schema")` |
| "What features are defined?" | `rag_search("feature definitions", doc_type="catalog-schema")` |
| "What datasets are available?" | `rag_search("datasets", doc_type="catalog-data")` |
| "What vocabulary terms can I use?" | `rag_search("vocabulary terms", doc_type="catalog-schema")` |
| "How do I create a dataset?" | `rag_search("how to create a dataset", include_schema=False, include_data=False)` |

**Just ask:** *"what's in this catalog?"*, *"show me the first 20 images where Diagnosis is Normal"*, or *"what features exist on Image?"*

### Organize Data for ML
- Create datasets and add members from catalog tables
- Split datasets into training/testing/validation partitions
- Create features for labeling and annotation (classification, ground truth, confidence scores)
- Manage dataset versions for reproducibility
- Download and prepare data for ML frameworks (denormalize, BDBag, restructure for PyTorch)
- Track asset provenance — find which execution created a file

**Just ask:** *"create a labeled dataset and split it 80/20"* or *"denormalize my dataset into a DataFrame"*

### Run Experiments
- Run ML experiments with full provenance tracking
- Configure experiment presets and hyperparameter sweeps
- Do dry runs to test configuration before committing
- Run Jupyter notebooks with execution tracking
- Create new model functions and wire them into the project
- Write and validate Hydra-Zen configuration files

**Just ask:** *"run the cifar10_quick experiment"* or *"create a new model for image classification"*

### Troubleshoot Problems
- Debug execution failures (authentication, timeouts, missing files)
- Fix stuck executions
- Diagnose missing data in dataset exports
- Resolve version mismatches

**Just ask:** *"my execution is stuck in Running"* or *"my dataset bag is missing images"*

### Write Scripts for Catalog Operations
- Generate Python scripts for batch data loading, ETL, and feature population
- Scripts include provenance tracking and dry-run support
- Committed scripts ensure reproducibility

**Just ask:** *"write a script to load annotations from a CSV"*

## Tips

- **Start with `rag_search`** for any "what is" or "what exists" question — it searches schema, data, and docs in one call
- **You don't need to know command names** — just describe what you want in plain language
- **I'll guide you through the steps** — each capability includes best practices and common pitfalls
- **Start with a connected catalog** — most operations need a catalog connection first. Just say *"connect to my catalog"*
- **Use dry runs** when experimenting — add "dry run" to any request to preview without making changes
