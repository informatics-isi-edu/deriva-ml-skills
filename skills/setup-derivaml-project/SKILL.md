---
name: setup-derivaml-project
description: "Use when starting a brand-new DerivaML project from zero — creating the repository, initializing uv and git, writing the first pyproject.toml with the deriva-ml dependency, installing the GitHub CLI for the PR workflow, and adopting the project conventions (Google docstrings, type hints, ruff). Triggers on: 'start a new deriva-ml project', 'create new deriva-ml project', 'bootstrap deriva-ml', 'set up new project', 'initialize project', 'pyproject.toml for deriva-ml', 'starter pyproject', 'new repo for deriva-ml'."
disable-model-invocation: true
---

# Set Up a New DerivaML Project

This skill covers the **bootstrap moment** — the one-time setup of a fresh DerivaML project from scratch. After bootstrap, three other skills carry the lifetime conventions: `/deriva-ml:setup-notebook-environment` for the dev environment, `/deriva-ml:validate-project-setup` for verifying the layout matches the template, and the lifecycle skills (`dataset-lifecycle`, `execution-lifecycle`, `experiment-lifecycle`) for actual work.

Don't develop inside the DerivaML library itself. Every DerivaML project gets its own Git repository.

> **Setting up the *catalog* the project will work against?** That's a separate concern — see `/deriva-ml:setup-ml-catalog` for creating a fresh DerivaML catalog from scratch (with a phased loader script) or cloning a slice of an existing source catalog into a new destination. The two skills are independent; do them in either order. This skill sets up the *code*; that one sets up the *catalog*.

## Step 1: Initialize the repository

```bash
mkdir my-ml-project
cd my-ml-project
git init
uv init
```

DerivaML projects use `uv` for dependency management. Use `uv add` to add dependencies (not `pip install`). **Commit `uv.lock`** to version control — this ensures reproducible environments across machines and over time.

```bash
uv add deriva-ml
uv add torch torchvision  # ML framework deps
```

## Step 2: Configure `pyproject.toml`

A typical starter configuration:

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

Key choices:

- **`dynamic = ["version"]`** with `[tool.setuptools_scm]` — version is derived from git tags. The `bump-version` CLI manages tags; you never edit a version string by hand.
- **`[dependency-groups]`** — separate `jupyter` and `dev` groups keep the base install lean. Install on demand: `uv sync --group=jupyter`.
- **`[project.scripts]`** — for catalog-operations scripts that should get a CLI entry point. Most one-off scripts in `src/scripts/` should NOT have entry points (they're one-time operations, not reusable tools); see `/deriva-ml:generate-scripts` for the pattern.

## Step 3: Install the GitHub CLI

Required for the PR-based workflow that DerivaML projects follow. With `gh` installed, Claude can create PRs, review diffs, and merge directly from the terminal — making the PR loop lightweight even for solo developers.

```bash
# macOS
brew install gh

# Then authenticate
gh auth login
```

For the full git workflow conventions (feature branches, PR-even-solo discipline, commit-before-running), see `/deriva-ml:model-development-workflow` under "Git workflow".

## Step 4: Adopt the coding conventions

DerivaML projects follow these conventions:

- **Docstrings**: Google-style on all public functions and classes.
- **Type hints**: Modern Python typing (3.12+). Prefer `X | None` over `Optional[X]`.
- **Formatting and linting**: `ruff` for linting and formatting, configured in `pyproject.toml`.
- **Notebook hygiene**: Install `nbstripout` (covered in `/deriva-ml:setup-notebook-environment`) so notebook outputs never get committed.
- **No data files in Git**: Store data in Deriva catalogs and pin dataset versions in experiment configs. The catalog IS the data store; the repo is for code.

## Step 5: Seed the tacit-knowledge system

Every DerivaML project accumulates *why*-knowledge in a tacit-knowledge system (the
append-only Log + a derived retrieval index + a topic CV + a domain-background bundle).
Scaffold all of it in one step:

```bash
uv run python \
  <deriva-ml-skills>/skills/capture-tacit-knowledge/scripts/seed_tk_topics.py \
  --repo-root . --project-name "<Project Name>"
```

Then **augment the seed topic CV with project-specific guesses**: read the repo, the
catalog's controlled vocabularies, and the project's domain, and propose 5–15
project-specific topic terms (authored to the `term-naming-strategy` discipline) into
`docs/tacit-knowledge/topics.md` under the matching axis heading. Present the combined
seed + augmentation for the user to review before committing — the CV is human-gated.
See `/deriva-ml:capture-tacit-knowledge` → `references/index-and-retrieval.md` for how
the CV is used.

## Step 6: Verify and move on

After bootstrap, run `/deriva-ml:validate-project-setup` to confirm the project conforms to the expected layout (`src/configs/`, `src/models/`, `src/scripts/`, `notebooks/`, `pyproject.toml` entry points, `tacit-knowledge.md`, `Experiments.md`).

The next steps are typically:

1. `/deriva-ml:setup-notebook-environment` — install Jupyter kernel, configure nbstripout, authenticate with Deriva/Globus
2. `/deriva-ml:validate-project-setup` — verify the layout
3. `/deriva-ml:dataset-lifecycle`, `/deriva-ml:experiment-lifecycle`, `/deriva-ml:new-model` — actual work
