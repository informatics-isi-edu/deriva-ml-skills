# DerivaML Skills Plugin

[Claude Code](https://claude.ai/claude-code) skills plugin for [DerivaML](https://github.com/informatics-isi-edu/deriva-ml) ML workflows. Provides 30 skills covering the full ML development cycle on top of Deriva catalogs: dataset / execution / experiment lifecycles, features, asset management, Hydra-zen configs, model development, project setup validation, and execution-specific troubleshooting.

The plugin requires the [`deriva-skills`](https://github.com/informatics-isi-edu/deriva-skills) plugin (for generic Deriva catalog operations the DerivaML skills cross-reference) and a [`deriva-mcp-core`](https://github.com/informatics-isi-edu/deriva-mcp-core) server with the [`deriva-ml-mcp`](https://github.com/informatics-isi-edu/deriva-ml-mcp) plugin loaded (for the `deriva_ml_*` MCP tools). The install procedure below brings in both plugins; the MCP server you set up separately.

## Installation

Install via the [`deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins) marketplace:

```bash
# Add the marketplace (one-time) — covers both deriva and deriva-ml
/plugin marketplace add informatics-isi-edu/deriva-plugins

# Install both plugins — deriva-ml assumes deriva is loaded for cross-references
/plugin install deriva
/plugin install deriva-ml
```

You also need a Deriva MCP server with the `deriva-ml-mcp` plugin loaded. See the [`deriva-mcp-core`](https://github.com/informatics-isi-edu/deriva-mcp-core) deployment docs.

> **Migrating from the old per-repo marketplaces?** Earlier versions were installed via `/plugin marketplace add informatics-isi-edu/deriva-skills` and `/plugin marketplace add informatics-isi-edu/deriva-ml-skills`. Both single-plugin marketplaces have been retired. To migrate, first remove both old caches:
> ```
> /plugin marketplace remove deriva-plugins      # was the deriva-skills marketplace
> /plugin marketplace remove deriva-ml-plugins   # was the deriva-ml-skills marketplace
> ```
> Note the name collision: the *new* unified marketplace is also internally named `deriva-plugins`, so the old `deriva-plugins` cache must be removed before re-adding from the new repo. Then run the three commands above.

## Updating

Enable `"autoUpdate": true` in `~/.claude/settings.json` for the `deriva-plugins` marketplace and restart Claude Code; new versions will be picked up automatically.

For checking what's currently installed and walking through updates, the versioning content lives in two troubleshooting skills:

- `/deriva:troubleshoot-deriva-errors` *(deriva-skills)* — "Versioning and updates" section covers the foundation: deriva-py, deriva-mcp-core, the deriva plugin
- `/deriva-ml:troubleshoot-execution` *(this plugin)* — "Versioning and updates" section covers the DerivaML layer: deriva-ml, deriva-ml-mcp, deriva-ml-skills

Check the foundation first; the DerivaML stack depends on it.

## Available Skills

The plugin ships two layers of skills with different invocation models. **User commands** are tools you invoke directly (or that fire when you ask Claude something matching them); **auto-invoked guides** are background disciplines that watch what you're doing and inject framing before mistakes happen.

### User commands

Invoke directly with `/deriva-ml:<skill-name>`, or by asking Claude something that maps to one of them.

| Category | Command | Description |
|----------|---------|-------------|
| **Lifecycle (auto-fires too)** | `/deriva-ml:dataset-lifecycle` | Create, populate, split, version, browse, download datasets |
| | `/deriva-ml:execution-lifecycle` | Pre-flight validation, run experiments, execution provenance, state machine |
| | `/deriva-ml:experiment-lifecycle` | The seven-phase experiment cycle: hypothesis → configure → identify assets → run → update assets → evaluate → repeat |
| **Datasets** | `/deriva-ml:debug-bag-contents` | Diagnose missing data in dataset bag exports |
| **Features** | `/deriva-ml:create-feature` | Create features with vocabulary or scalar value domains; add per-row values |
| | `/deriva-ml:compare-model-runs` | Rank/compare metrics across model training executions |
| **Assets** | `/deriva-ml:work-with-assets` | File assets — upload, download, provenance, types |
| | `/deriva-ml:manage-deriva-storage` | Storage Manager (a built-in Deriva-ML-Apps app) |
| **Schema / curation** | `/deriva-ml:schema-evolution-impact` | Impact analysis before schema or data changes — which datasets, features, executions reference the target |
| **Experiments / configs** | `/deriva-ml:configure-experiment` | Set up DerivaML experiment project structure |
| | `/deriva-ml:write-hydra-config` | Write and validate hydra-zen config files |
| **Models** | `/deriva-ml:new-model` | Scaffold a new model function and wire it into configs/workflows |
| | `/deriva-ml:model-development-workflow` | End-to-end model development workflow |
| **Notebooks** | `/deriva-ml:setup-notebook-environment` | Set up Jupyter environment for DerivaML |
| | `/deriva-ml:run-notebook` | Develop and run notebooks with execution tracking |
| **Project setup** | `/deriva-ml:setup-derivaml-project` | Bootstrap a new DerivaML project: repo init, `pyproject.toml` template, `gh` install, coding conventions |
| | `/deriva-ml:validate-project-setup` | Validate the project conforms to the deriva-ml-model-template shape |
| **Apps + visualization** | `/deriva-ml:create-web-app` | Build and register custom web apps for DerivaML data |
| | `/deriva-ml:browse-erd` | Launch the ERD browser for the connected catalog |
| **Help / orientation** | `/deriva-ml:help` | General orientation: what is DerivaML, how to use it, where to start |
| **Troubleshooting** | `/deriva-ml:troubleshoot-execution` | Execution-lifecycle errors AND DerivaML versioning/updates |

### Auto-invoked guides (background disciplines, not commands)

These are skills that **Claude loads on its own** when the situation calls for them. They do not appear in the `/deriva-ml:` slash-command picker, and you should not type them as commands — they're internal disciplines that "look over the ML developer's shoulder" to inject the right framing before mistakes happen, capture decisions as they're made, and route catalog mutations through the right provenance-preserving paths.

| Skill | When Claude loads it |
|-------|----------------------|
| `deriva-ml-context` | Always — establishes the DerivaML domain frame, the five abstractions, and the inheritance-with-override rule that governs when to use a deriva-ml surface vs the underlying deriva surface |
| `dataset-lifecycle` | When the user is working with datasets (creating, splitting, versioning, browsing) — guides through the lifecycle phases proactively |
| `execution-lifecycle` | When the user is running experiments — guides through the state machine and upload discipline |
| `experiment-lifecycle` | When the user is designing or running an experiment cycle — names the seven phases and the cross-step disciplines |
| `create-feature` | When the user is creating or working with features — guides through the assess/design/create phases and the feature-vs-column decision |
| `run-notebook` | When the user is creating, developing, or running a DerivaML Jupyter notebook — guides through the three-stage development cycle and `run_notebook()` provenance machinery (also slash-typable) |
| `capture-tacit-knowledge` | After significant decisions in any phase — captures rationale to tacit-knowledge.md |
| `generate-descriptions` | When creating any DerivaML entity without a user-supplied description |

You'll see the auto-invoked skills' effects in Claude's behavior (it asks "should we name a hypothesis first?" when starting an experiment; it captures the decision to tacit-knowledge.md; it walks the dataset-creation phases in order); you won't see them as commands you can invoke.

## Which plugin's skill to reach for

The two plugins are designed to be used together. As a rough guide:

**`deriva-skills` covers generic Deriva catalog operations** — what works on any Deriva catalog, ML or otherwise:
- Schema and table operations
- Generic vocabulary CRUD (e.g., your project's `Sample_Type` or `Tissue_Type`)
- Querying / browsing catalog data
- Chaise display annotations — interactive MCP-tool path (`/deriva:customize-display`). The type-safe Python builder path (`/deriva-ml:use-annotation-builders`) lives in this plugin because it requires the `deriva-ml` Python package.
- Generic catalog troubleshooting (auth, RIDs, missing records)
- Loading row data and uploading assets via `deriva-upload-cli`

**`deriva-ml-skills` (this plugin) covers the DerivaML domain layer** — the abstractions DerivaML adds on top of a catalog:
- The five DerivaML abstractions: Datasets, Workflows, Executions, Features, Assets
- The four DerivaML built-in vocabularies: `Dataset_Type`, `Workflow_Type`, `Asset_Type`, `Execution_Status_Type`
- Experiment configuration (Hydra-zen), model development, training workflows
- Execution-state-machine debugging

> **Override rule.** When you're working in a deriva-ml catalog, everything that applies in a Deriva catalog applies here too — by default reach for `deriva-skills`. **But** if a deriva-ml surface exists for the operation — a `/deriva-ml:<skill>`, a `deriva_ml_*` MCP tool/prompt/resource, or a deriva-ml Python object — prefer it over the equivalent deriva surface (`/deriva:<skill>`, `deriva-mcp-core` tool, or `deriva-py` call). The five abstractions above are where the override mostly lands; everywhere else the deriva default applies. The auto-invoked `deriva-ml-context` skill carries the rule plugin-wide; ADR-0001 records the design decision.

## Development

Load the plugin from a local path without installing:

```bash
claude --plugin-dir /path/to/deriva-ml-skills
```

## Related Projects

- [`deriva-skills`](https://github.com/informatics-isi-edu/deriva-skills) — Companion plugin for generic Deriva catalog operations (required — install alongside this one)
- [`deriva-mcp-core`](https://github.com/informatics-isi-edu/deriva-mcp-core) — Core MCP framework + generic Deriva catalog tools
- [`deriva-ml-mcp`](https://github.com/informatics-isi-edu/deriva-ml-mcp) — DerivaML MCP plugin (loaded by deriva-mcp-core); required for these skills' MCP tools
- [`deriva-ml`](https://github.com/informatics-isi-edu/deriva-ml) — Core Python library for ML workflows on Deriva
- [`deriva-py`](https://github.com/informatics-isi-edu/deriva-py) — Python SDK for Deriva scientific data management

## License

Apache 2.0
