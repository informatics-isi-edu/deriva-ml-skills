---
name: route-project-setup
description: "Use this skill whenever the user asks about DerivaML versions, updates, environment setup, or troubleshooting data exports — including 'check versions', 'am I up to date', 'update deriva-ml', 'bag export problems', 'missing data in bag', 'materialization issues'. Also covers setting up the DerivaML development environment: installing Jupyter kernels, configuring nbstripout, authenticating with Deriva/Globus, setting up pyproject.toml, managing uv dependencies, and establishing coding standards and Git workflow."
---

# Project Setup — Environment, Versions, and Standards

You are a router skill. Based on the user's request, load the appropriate specialized skill.


## Stateless model

Every MCP tool routed from here is stateless — it takes `hostname=` and `catalog_id=` arguments explicitly. There is no `connect_catalog` step or "active catalog" state. Substitute your catalog's host and ID in every tool example shown by the routed skills.


## Routing Rules

Analyze the user's intent and read the matching skill:

### Environment setup for notebooks
- **Setting up Jupyter environment, installing kernels, uv sync --group=jupyter, configuring nbstripout, Deriva/Globus authentication, PyTorch dependencies** → Read and follow `../setup-notebook-environment/SKILL.md`

### Version checking and updates
- **Checking if the core Deriva ecosystem is up to date, deriva-py version, deriva-mcp-core MCP server version, deriva-skills (deriva plugin) version** → Read and follow `/deriva:check-deriva-versions` *(tier-1, deriva-skills)*. If the user does not have the `deriva-skills` plugin installed, the script can still be invoked directly from this plugin's `check-deriva-ml-versions` skill — it knows about the entire ecosystem.
- **Checking if the DerivaML ecosystem is up to date, deriva-ml Python lib version, deriva-ml-mcp plugin version, deriva-ml-skills plugin version** → Read and follow `../check-deriva-ml-versions/SKILL.md`. Run the tier-1 check first when both plugins are installed; tier-2 components depend on tier-1.

### Coding standards and project setup
- **Project setup from scratch, pyproject.toml structure, uv configuration, Git workflow, Google docstrings, ruff linting, type hints, version bumping** → Read and follow `/deriva:coding-guidelines` *(tier-1, deriva-skills)*. The standards apply to any DerivaML / Deriva project regardless of tier.

### Troubleshooting data exports
- **Missing data in downloaded dataset bags, FK traversal issues, materialization problems, bag export timeouts, Python API bag inspection** → Read and follow `../debug-bag-contents/SKILL.md`

## Important

After identifying the correct skill, read its SKILL.md file completely and follow its instructions. Do not attempt to handle the request from this routing skill alone.
