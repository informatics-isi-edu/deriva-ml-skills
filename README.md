# DerivaML Skills Plugin

[Claude Code](https://claude.ai/claude-code) skills plugin for [DerivaML](https://github.com/informatics-isi-edu/deriva-ml) ML workflows. Provides 23 skills covering the full ML development cycle on top of Deriva catalogs: dataset lifecycle, executions, features, asset management, experiments, Hydra-zen configs, model development, and execution-specific troubleshooting.

This is the **tier-2** skills plugin — the surface specific to DerivaML. It depends on the **tier-1** [`deriva-skills`](https://github.com/informatics-isi-edu/deriva-skills) plugin (the core Deriva ecosystem) and the [`deriva-ml-mcp`](https://github.com/informatics-isi-edu/deriva-ml-mcp) MCP plugin. All three are required for full functionality.

## Installation

You need both marketplaces and both plugins:

```bash
# Tier-1 plugin (core Deriva)
/plugin marketplace add informatics-isi-edu/deriva-skills
/plugin install deriva

# Tier-2 plugin (this one)
/plugin marketplace add informatics-isi-edu/deriva-ml-skills
/plugin install deriva-ml
```

You also need a Deriva MCP server with the `deriva-ml-mcp` plugin loaded. See the [`deriva-mcp-core`](https://github.com/informatics-isi-edu/deriva-mcp-core) deployment docs.

## Updating

```
/plugin install deriva-ml
```

Or check the entire DerivaML ecosystem:

```
/deriva:check-deriva-versions          # tier-1 (run first)
/deriva-ml:check-deriva-ml-versions    # tier-2
```

## Available Skills

**User-invocable** — invoke with `/deriva-ml:<skill-name>`:

| Category | Skill | Description |
|----------|-------|-------------|
| **Dataset lifecycle** | `/deriva-ml:dataset-lifecycle` | Create, populate, split, version, browse, download datasets |
| | `/deriva-ml:debug-bag-contents` | Diagnose missing data in dataset bag exports |
| **Execution** | `/deriva-ml:execution-lifecycle` | Pre-flight validation, run experiments, execution provenance |
| | `/deriva-ml:troubleshoot-execution` | Execution-lifecycle errors (asset paths, upload, stuck Running, version mismatch, missing feature) |
| **Features** | `/deriva-ml:create-feature` | Create features with vocabulary or scalar value domains; add per-row values |
| **Assets** | `/deriva-ml:work-with-assets` | File assets — upload, download, provenance, types |
| | `/deriva-ml:manage-storage` | Storage Manager (a built-in Deriva-ML-Apps app) |
| **Experiments** | `/deriva-ml:configure-experiment` | Set up DerivaML experiment project structure |
| | `/deriva-ml:write-hydra-config` | Write and validate hydra-zen config files |
| **Models** | `/deriva-ml:new-model` | Scaffold a new model function and wire it into configs/workflows |
| | `/deriva-ml:model-development-workflow` | End-to-end model development workflow |
| **Notebooks** | `/deriva-ml:setup-notebook-environment` | Set up Jupyter environment for DerivaML |
| | `/deriva-ml:run-notebook` | Develop and run notebooks with execution tracking |
| **Routers** | `/deriva-ml:route-run-workflows` | Router: experiments / notebooks / configs / models / troubleshoot |
| | `/deriva-ml:route-project-setup` | Router: notebook env / version checks / coding guidelines / bag debugging |
| **Maintenance** | `/deriva-ml:check-deriva-ml-versions` | Check the DerivaML ecosystem (deriva-ml, deriva-ml-mcp, deriva-ml-skills) |

**Auto-invoked** — Claude loads these automatically when relevant:

| Skill | When it activates |
|-------|-------------------|
| `deriva-ml-context` | Always-on plugin context: explains the DerivaML abstractions and the steering principle |
| `maintain-experiment-notes` | After significant experiment design decisions |
| `catalog-operations-workflow` | When performing catalog mutations |
| `api-naming-conventions` | When writing DerivaML Python code |
| `ml-data-engineering` | When designing or modifying ML data layouts |
| `generate-scripts` | When generating Python scripts for catalog operations with execution provenance |

## Tier-1 vs Tier-2: When to use which plugin

**Tier-1 (`deriva-skills`)** — the foundation. Use these skills for:
- Schema and table operations on any Deriva catalog
- Generic vocabulary CRUD (e.g., your project's `Sample_Type` or `Tissue_Type`)
- Querying / browsing catalog data
- Chaise display annotations
- Generic catalog troubleshooting (auth, RIDs, missing records)

**Tier-2 (this plugin)** — the DerivaML domain layer. Use these skills for:
- The five DerivaML abstractions: Datasets, Workflows, Executions, Features, Assets
- The four DerivaML built-in vocabularies: `Dataset_Type`, `Workflow_Type`, `Asset_Type`, `Execution_Status_Type` (extend with the dedicated `create_dataset_type_term` / `add_workflow_type` / `add_asset_type` tools)
- Experiment configuration (Hydra-zen), model development, training workflows
- Execution-state-machine debugging

> **Steering principle:** in a deriva-ml-loaded catalog, **the DerivaML abstractions take precedence over the raw catalog primitives** documented in tier-1. Use the `/deriva-ml:` skills and the deriva-ml Python API for the five abstractions, not the raw `insert_records` / `update_record` core tools (which bypass business logic, FK validation, provenance tracking, version management, and RAG re-indexing). The auto-invoked `deriva-ml-context` skill carries this principle plugin-wide.

## Development

Load the plugin from a local path without installing:

```bash
claude --plugin-dir /path/to/deriva-ml-skills
```

## Related Projects

- [`deriva-skills`](https://github.com/informatics-isi-edu/deriva-skills) — Companion **tier-1** plugin: core Deriva catalog skills (required dependency)
- [`deriva-mcp-core`](https://github.com/informatics-isi-edu/deriva-mcp-core) — Core MCP framework + generic Deriva catalog tools
- [`deriva-ml-mcp`](https://github.com/informatics-isi-edu/deriva-ml-mcp) — DerivaML MCP plugin (loaded by deriva-mcp-core); required for these skills' MCP tools
- [`deriva-ml`](https://github.com/informatics-isi-edu/deriva-ml) — Core Python library for ML workflows on Deriva
- [`deriva-py`](https://github.com/informatics-isi-edu/deriva-py) — Python SDK for Deriva scientific data management

## License

Apache 2.0
