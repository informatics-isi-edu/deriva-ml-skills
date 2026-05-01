---
name: coding-guidelines
description: "Coding standards and project setup for DerivaML projects — uv/pyproject.toml configuration, Git workflow, Google docstrings, ruff linting, type hints. Use when setting up a new project or establishing development practices."
disable-model-invocation: true
---

# Coding Guidelines for DerivaML Projects

This skill covers the recommended workflow, coding standards, and best practices for developing DerivaML-based machine learning projects.

## Repository Setup

### Start with Your Own Repository

Every DerivaML project should live in its own Git repository. Do not develop inside the DerivaML library itself.

```bash
mkdir my-ml-project
cd my-ml-project
git init
uv init
```

### Use `uv` as the Package Manager

DerivaML projects use `uv` for dependency management. Always:

- Define dependencies in `pyproject.toml`.
- Use `uv add` to add dependencies (not `pip install`).
- **Commit `uv.lock`** to version control. This ensures reproducible environments across machines and over time.

```bash
uv add deriva-ml
uv add torch torchvision  # ML framework deps
```

### Typical `pyproject.toml` Structure

```toml
[project]
name = "my-ml-project"
dynamic = ["version"]
requires-python = ">=3.12"
dependencies = [
    "deriva-ml>=0.5.0",
]

[dependency-groups]
jupyter = ["jupyterlab", "papermill"]
dev = ["pytest", "ruff"]

[tool.setuptools_scm]
# Version derived from git tags

[project.scripts]
load-my-data = "scripts.load_data:main"
```

## Environment Management

- Use `uv sync` to install the project in development mode.
- Use `uv sync --group=jupyter` when you need Jupyter support.
- Use `uv run` to execute commands within the project environment.
- Never install packages globally for project work.

## Git Workflow

### Prerequisites

Install the [GitHub CLI (`gh`)](https://cli.github.com/) for creating pull requests, reviewing diffs, and merging from the terminal. Claude Code can use `gh` to handle the full PR workflow for you.

```bash
# macOS
brew install gh

# Then authenticate
gh auth login
```

### Branch Strategy

- Use feature branches for all work: `git checkout -b feature/add-segmentation-model`.
- Keep `main` clean and passing.
- Use pull requests for code review — even for solo developers, PRs create a permanent record of what changed and why.

### Commit Before Running

**Always commit your code before running an experiment.** DerivaML records the git state (commit hash, branch, dirty status) in the execution metadata. If you run with uncommitted changes:

- The execution is marked as having a dirty working tree.
- Reproducing the exact run later becomes difficult or impossible.

### Version Bumping

Use `bump-version` (via the MCP tool or CLI) before production runs:

```bash
uv run bump-version patch  # 0.1.0 -> 0.1.1
```

Versioning conventions:
- **patch**: Bug fixes, small parameter tweaks.
- **minor**: New experiment configurations, new model architectures.
- **major**: Breaking changes to the training pipeline or data format.

Commit the version bump before running.

## Coding Standards

- **Docstrings**: Use Google-style docstrings for all public functions and classes.
- **Type hints**: Use modern Python typing (3.11+) on all function signatures. Prefer `X | None` over `Optional[X]`.
- **Formatting and linting**: Use `ruff` for linting and formatting, configured in `pyproject.toml`.
- **Semantic versioning**: Bump versions with `uv run bump-version patch|minor|major` before production runs.

For docstring templates, type hint examples, ruff rule sets, and the versioning table, see `references/coding-standards.md`.

## Notebook Guidelines

Never commit notebook outputs to Git -- install `nbstripout` to strip them automatically. Keep each notebook focused on one task, and ensure it runs end-to-end with Restart & Run All.

For Jupyter / DerivaML environment setup and execution-tracked notebook workflows, see the `setup-notebook-environment` and `run-notebook` skills in the `deriva-ml-skills` plugin (tier-2).

## Experiments and Data *(deriva-ml-skills, tier-2)*

The following guidelines apply when you have the `deriva-ml-skills` plugin installed and are running ML experiments. They are reproduced here because they're closely related to general project hygiene; the linked skills live in the tier-2 plugin.

- Define experiment configs in hydra-zen — see `write-hydra-config` and `configure-experiment` in `deriva-ml-skills`
- Always test with `dry_run=True` before production runs — see `execution-lifecycle` in `deriva-ml-skills`
- Never commit data files to Git -- store in Deriva catalogs and pin dataset versions — see `dataset-lifecycle` in `deriva-ml-skills`
- Wrap all data operations in executions for provenance — see `execution-lifecycle` in `deriva-ml-skills`

## Extensibility

Prefer inheritance and composition over modifying DerivaML library code:

```python
from deriva_ml import DerivaML

class MyProjectML(DerivaML):
    """Extended DerivaML with project-specific helpers."""

    def load_training_data(self, dataset_rid: str) -> pd.DataFrame:
        ...
```

## Summary Checklist

- [ ] Own repository with `uv` and committed `uv.lock`
- [ ] GitHub CLI (`gh`) installed for PR workflow
- [ ] Feature branches and pull requests
- [ ] Google docstrings and type hints on all public APIs
- [ ] `nbstripout` installed for notebooks
- [ ] No data files in Git -- store in Deriva catalogs
- [ ] Version bumped and committed before production runs
