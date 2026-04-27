---
name: route-run-workflows
description: "Use this skill for configuring DerivaML experiments, running notebooks, writing Hydra-Zen configs, creating new model functions, and troubleshooting execution failures. For running experiments and the execution lifecycle itself, use the execution-lifecycle skill directly. Choose this router when users want to configure, create notebooks, write configs, or debug ML workflows."
---

# ML Workflows — Experiments, Notebooks, Executions, and Configuration

You are a router skill. Based on the user's request, load the appropriate specialized skill.


## Stateless model

Every MCP tool routed from here is stateless — it takes `hostname=` and `catalog_id=` arguments explicitly. There is no `connect_catalog` step or "active catalog" state. Substitute your catalog's host and ID in every tool example shown by the routed skills.


## Routing Rules

Analyze the user's intent and read the matching skill:

### ML data engineering
- **Restructuring assets for PyTorch/TensorFlow, building training DataFrames, DatasetBag API, value selectors for multi-annotator data, file format conversion during restructuring** → Read and follow `../ml-data-engineering/SKILL.md`

### Running notebooks
- **Creating, developing, or running DerivaML Jupyter notebooks, notebook structure, run_notebook(), deriva-ml-run-notebook, papermill parameters** → Read and follow `../run-notebook/SKILL.md`

### Configuration
- **Writing or editing Hydra-Zen config files — DatasetSpecConfig, AssetSpecConfig, builds(), experiment_config, multirun_config, with_description, notebook_config** → Read and follow `../write-hydra-config/SKILL.md`
- **Setting up experiment project structure, understanding config composition, hydra defaults, DerivaModelConfig** → Read and follow `../configure-experiment/SKILL.md`

### Creating new models
- **Creating a new model function, scaffolding model code, wiring a model into configs/workflows/experiments** → Read and follow `../new-model/SKILL.md`

### Troubleshooting
- **DerivaML execution failure, stuck `Running` status, `asset_file_path()` / `upload_execution_outputs()` problems, upload timeout, missing output files, dataset version mismatch, missing feature, ML vocabulary term not found** → Read and follow `../troubleshoot-execution/SKILL.md` (tier-2)
- **Generic catalog errors (auth / permission denied, invalid RID, record not found, generic vocabulary term not found, cannot connect to catalog)** → Read and follow `/deriva:troubleshoot-deriva-errors` *(tier-1, deriva-skills)*. When it's not obvious which troubleshoot skill applies, start with the tier-1 one — many "execution failures" are actually catalog-state issues.

## Important

After identifying the correct skill, read its SKILL.md file completely and follow its instructions. Do not attempt to handle the request from this routing skill alone.
