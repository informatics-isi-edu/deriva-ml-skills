---
name: validate-project-setup
description: "Validate that a DerivaML project repository conforms to the expected shape from deriva-ml-model-template. Use when the user asks 'is my project set up right?', 'does my repo look right?', 'validate my project', 'check project structure', 'why isn't my project working?', or when something is failing in a way that suggests the project structure may not match what DerivaML expects. Walks through the canonical layout (src/configs/, src/models/, src/scripts/, notebooks/, pyproject.toml entry points, tacit-knowledge.md, Experiments.md), reports each item as present, partial, or missing, and suggests fixes for gaps. Conceptual checklist only — no bundled script — so the LLM can adapt to template variations and present results contextually. Triggers on: 'validate project', 'validate project setup', 'is my project set up right', 'is my project set up correctly', 'check my project structure', 'check project layout', 'does my repo look right', 'project shape', 'project conforms', 'is this a deriva-ml project', 'project sanity check', 'audit my project', 'verify project setup'."
disable-model-invocation: true
---

# Validate DerivaML Project Setup

A DerivaML project repository follows the shape established by the [`deriva-ml-model-template`](https://github.com/informatics-isi-edu/deriva-ml-model-template). When that shape is correct, the conventional commands (`uv run deriva-ml-run`, `uv run deriva-ml-run-notebook`) work, the configs compose, the experiments and multiruns can be discovered, and the rest of the deriva-ml-skills plugin works the way it's designed to. When the shape is wrong, things fail in confusing ways — usually with errors that *look* like execution problems but are actually project-structure problems.

This skill is the user-driven sanity check for "does my project look right?" Walk through the canonical layout, report what's present and missing, and suggest fixes. Don't make changes — this is a verification, not a fixer.

## When to use this skill

- The user explicitly asks to validate or audit the project setup.
- A user is onboarding to an existing DerivaML project and wants to know if it's in good shape.
- An experiment or notebook is failing in a way that points at structure rather than logic ("config not found", "entry point not registered", "experiment doesn't compose").
- After a major refactor or migration, to confirm the project still matches the expected shape.

## When not to use this skill

- For environment problems (Jupyter kernel, dependencies, authentication) — that's `/deriva-ml:setup-notebook-environment`.
- For execution-time errors with a working project — that's `/deriva-ml:troubleshoot-execution`.
- For starting a fresh project from zero (initial repo, `pyproject.toml`, `gh` install, coding conventions) — that's `/deriva-ml:setup-derivaml-project`.

## The canonical project shape

The validation walks five categories. For each item, report **present**, **partial** (exists but doesn't match the convention), or **missing**, with a one-line note on what to do about it.

### 1. Top-level repository layout

| Item | Expected | What it is |
|---|---|---|
| `pyproject.toml` | present | Standard Python project metadata; required for `uv` to recognize the project |
| `uv.lock` | present (after first `uv sync`) | Locked dependency versions; commit alongside `pyproject.toml` |
| `src/` | present | Python source tree |
| `notebooks/` | present | Jupyter notebook directory (may be empty if the project doesn't use notebooks) |
| `tests/` | present | Test suite directory |
| `tacit-knowledge.md` | present | Auto-maintained by `capture-tacit-knowledge`; captures decisions over time |
| `docs/design/` | present once any design exists (optional early) | Design docs — the up-front Specify-phase contracts, in per-entity subdirs `docs/design/{experiment,dataset,feature,model}/<slug>.md`. Authored by `design-experiment`; the "before" companion to `tacit-knowledge.md`. Absent on a brand-new project; expected once the user has designed an experiment/dataset/feature/model. Design docs follow OKF (Markdown + YAML frontmatter); when present, each `<entity>/<slug>.md` should open with frontmatter carrying at least `type` (one of `Dataset Design` / `Experiment Design` / `Feature Design` / `Model Design`). A `docs/design/index.md` bundle listing is expected once any design exists. |
| `Experiments.md` | present (optional but strongly recommended) | Human-readable registry of named experiments and multiruns |
| `README.md` | present | Project description (may be the template's default; flag if so) |
| `.gitignore` | present | Should ignore `outputs/`, `multirun/`, `.deriva-ml/`, etc. |

**Common gaps:** missing `tacit-knowledge.md` (suggest creating an empty file with a one-line header so `capture-tacit-knowledge` has somewhere to write); missing `Experiments.md` (offer to scaffold one from `src/configs/experiments.py` and `src/configs/multiruns.py`); missing `tests/` (offer to create the directory with a placeholder `__init__.py`). Do **not** flag a missing `docs/design/` on a new or early project — design docs are authored on demand by `design-experiment`, so their absence is normal until the user designs their first experiment/dataset/feature/model; report it as "not yet used" rather than a gap.

### 2. The `src/configs/` directory

This is the most important part of the validation — most DerivaML problems originate from a malformed config tree.

| Item | Expected | What it is |
|---|---|---|
| `src/configs/__init__.py` | present | Required for the configs to import as a package |
| `src/configs/base.py` | present | Hydra defaults list and base config definition |
| `src/configs/deriva.py` | present | Catalog connection (hostname, catalog ID) |
| `src/configs/datasets.py` | present | `DatasetSpecConfig` registrations for all consumed datasets (with RIDs and pinned versions) |
| `src/configs/assets.py` | present | Asset registrations referenced by experiments |
| `src/configs/workflow.py` | present | Workflow definitions (URL + checksum + type) |
| `src/configs/experiments.py` | present | Named experiments (composition of the above into runnable configs) |
| `src/configs/multiruns.py` | present (optional) | Named sweeps over experiments |
| `src/configs/<model>.py` | one per model | Per-model hyperparameters / architecture configs |

**Common gaps:** missing `__init__.py` (import will fail silently — flag prominently); experiments in `experiments.py` reference dataset RIDs without pinned versions (call out — pinning the version is essential for reproducibility, see `/deriva-ml:write-hydra-config`); `base.py` hydra_defaults list is incomplete (the entries that are missing won't compose).

### 3. The `src/models/` directory

| Item | Expected | What it is |
|---|---|---|
| `src/models/__init__.py` | present | Package marker |
| `src/models/<model_name>.py` | one per model | Each defines a model function callable from a configured experiment |

**Common gaps:** model defined in `src/models/foo.py` but not exported from `__init__.py`; model exists but no corresponding `src/configs/<model>.py` config (the model can't be experimented with without its config).

### 4. `pyproject.toml` entry points and dependencies

| Item | Expected | What to check |
|---|---|---|
| `[project.scripts]` | includes `deriva-ml-run` and `deriva-ml-run-notebook` | These come from `deriva-ml`; if missing, `uv sync` wasn't run or `deriva-ml` isn't a dependency |
| `dependencies` | includes `deriva-ml`, `hydra-zen`, `hydra-core` | Core dependencies for any DerivaML project |
| `[tool.uv.sources]` (optional) | may pin `deriva-ml` to a git source | If pinned, note the source for reproducibility |
| `[dependency-groups]` | may include `jupyter`, `pytorch`, etc. | Optional groups for notebook development and ML frameworks |

**Common gaps:** `uv.lock` is stale relative to `pyproject.toml` (suggest `uv sync`); `deriva-ml` not declared as a dependency (the project will look DerivaML-shaped but won't actually work).

### 5. The `notebooks/` directory (if used)

| Item | Expected | What it is |
|---|---|---|
| `notebooks/` | present | May be empty if the project doesn't use notebooks |
| nbstripout configuration | configured | Each notebook should have output stripping; check for `.git/info/attributes` or repo-level config |
| `notebook_config(...)` registrations | one per notebook | Each notebook should have a corresponding config in `src/configs/<notebook>.py` |

**Common gaps:** notebooks committed with output (suggest `uv run nbstripout --install`); notebooks exist but no `notebook_config` registration (the notebook can't be invoked through the deriva-ml-run-notebook CLI).

## How to walk through the validation

For each of the five categories, do the following in order:

1. List the directory or file (`ls`, `cat`, etc.) to verify it exists.
2. For files (`pyproject.toml`, the configs), read the relevant content and check it matches the expected shape.
3. Note each item as present / partial / missing.
4. After all five categories, report a summary with the gap count and the most important fix to make first.

Do not perform fixes automatically. Surface the gap and let the user decide. If the user wants you to fix gaps, treat each fix as a separate, explicit action with its own confirmation.

## Reporting format

Report results as a checklist by category. Example:

```
DerivaML Project Validation Report

Top-level layout: 7 of 9 present
  ✅ pyproject.toml
  ✅ uv.lock
  ✅ src/
  ✅ notebooks/
  ✅ tests/
  ❌ tacit-knowledge.md — create an empty file with a header so capture-tacit-knowledge has somewhere to write
  ⚠️ Experiments.md — exists but appears stale (last updated before recent experiments added); regenerate from src/configs/experiments.py and src/configs/multiruns.py
  ✅ README.md
  ✅ .gitignore

src/configs/: 7 of 8 expected files present
  ✅ __init__.py, base.py, deriva.py, assets.py, workflow.py, experiments.py, multiruns.py
  ❌ datasets.py — your experiments.py references dataset RIDs but datasets.py doesn't exist; create it with DatasetSpecConfig registrations (see /deriva-ml:write-hydra-config)

[... etc ...]

Summary:
  3 missing items, 1 partial item.
  Most important fix first: create src/configs/datasets.py — without it, no experiment can resolve its dataset references.
```

If everything's present and correct, say so plainly: "Project structure looks good — all five categories pass. You're ready to run experiments."

## Related skills

- **`/deriva-ml:setup-notebook-environment`** — environment-side setup (Jupyter kernels, dependencies, authentication). Different from this skill (which checks repo shape, not environment readiness).
- **`/deriva-ml:configure-experiment`** — when this skill flags a missing or incomplete config tree, hand off here for the config-authoring workflow.
- **`/deriva-ml:write-hydra-config`** — for the per-config-file syntax when fixing flagged gaps in `src/configs/`.
- **`/deriva-ml:experiment-lifecycle`** — once the project shape is validated, this is the cycle the project enables.
- **The template itself**: `https://github.com/informatics-isi-edu/deriva-ml-model-template` — the canonical reference for what a correct shape looks like. Suggest the user read its README and CIFAR10.md when their project diverges substantially from the expected layout.
