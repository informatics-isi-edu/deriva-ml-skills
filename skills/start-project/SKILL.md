---
name: start-project
description: "Takes a user from nothing to a project ready for its first DerivaML training run — prerequisites, an experiment repository created from deriva-ml-model-template, a DerivaML catalog (new, or an existing one checked and adopted), the repo pointed at the catalog, the first data model and data, then a hand-off to model-development-workflow. Use when someone starts a new DerivaML project, adopts an existing catalog for ML work, or asks how to get started."
when_to_use: "Triggers on: 'start a new deriva-ml project', 'set up deriva-ml', 'new ML project', 'bootstrap deriva-ml', 'how do I get started', 'onboard to an existing project', 'use catalog N for a new model project', 'I have images and labels but no project yet', 'create a repo for deriva-ml', 'use the model template'. Not for adding data to a project that already has its repo and catalog (dataset-lifecycle), iterating on a working pipeline (experiment-lifecycle), or a project whose repo and catalog already work (model-development-workflow)."
---

# Start a DerivaML Project

This skill owns the **order** of a cold start and the decisions between steps;
the mechanics of each step live in the template's README or in the skill named
at that step. Skills marked † run only when the user types them — tell the user
which command to type and why, then continue once it has run.

Ask the user up front for what you can't look up:

- the Deriva host, and whether a catalog already exists (and its ID);
- the project name and the GitHub owner for the new repository;
- where the data is today (files on disk, an existing catalog, or both), and for
  labeled data, the label values and **the unit that must not be split across
  train and test** (for example patient or eye when one subject has several
  images).

## Before you start: prerequisites

Check each one; don't assume it.

- **Tools:** `git`, `uv`, and the GitHub CLI `gh` (authenticated with
  `gh auth login`).
- **A Deriva server:** if there is none, the template README points to
  `deriva-docker` for a local one. Logging in comes after the repo exists
  (Phase 1), because the login command runs inside the project environment.
- **The MCP server connected:** if no `deriva_ml_*` tools are available, the
  template README §4 covers connecting it. Load `/deriva-ml:using-deriva-mcp`
  before the first MCP call.

## Phase 1: The experiment repository

**New project — create it from the template**, never from `uv init`. The
template brings the hydra-zen config scaffolds, entry points, CI, design-doc
folders, and the tacit-knowledge journal (`tacit-knowledge.md` plus its index in
`docs/tacit-knowledge/`):

```bash
gh repo create <owner>/<project> --private --clone \
  --template informatics-isi-edu/deriva-ml-model-template
cd <project> && uv sync
uv run deriva-globus-auth-utils login --host <host>
```

Then follow the template README §2–6 (GitHub Pages, optional `jupyter` /
`pytorch` groups) and confirm the skeleton resolves:

```bash
uv run deriva-ml-run --list-configs
uv run deriva-ml-run +experiment=default --cfg job
```

**Existing repo** → the user runs `/deriva-ml:validate-project-setup` † to compare
it with the template layout. If it lacks `docs/tacit-knowledge/`, seed it:

```bash
uv run --no-project python \
  ${CLAUDE_PLUGIN_ROOT}/skills/capture-tacit-knowledge/scripts/seed_tk_topics.py \
  --repo-root . --project-name "<Project Name>"
```

Conventions every project follows: `uv` for everything (commit `uv.lock`),
Google-style docstrings, `ruff`, no data files in git (the catalog is the data
store), and **commit before running** — executions record the commit, so a
dirty tree breaks provenance (`DERIVA_ML_ALLOW_DIRTY=true` only for local
iteration).

## Phase 2: The catalog

**No catalog yet:**

1. Write the dataset and feature design docs first (`/deriva-ml:design-experiment`)
   — they decide the domain tables, vocabularies, and label features the catalog
   needs.
2. The user runs `/deriva-ml:setup-ml-catalog` †. In one pass it creates the
   catalog, installs the `deriva-ml` schema, creates the domain tables, and runs
   the phased loader: register the files, upload them, and write the labels as
   feature values from an import or curation execution. Creating a catalog is
   hard to undo, which is why it stays user-run.
3. Confirm authentication: `deriva_ml_check_authentication(hostname, catalog_id)`.

**An existing catalog** — confirm authentication, then inspect it before building
on it (full URIs are `deriva://catalog/{hostname}/{catalog_id}/…`):

1. **Is it a DerivaML catalog?** Read `deriva://catalog/{hostname}/{catalog_id}/schema`
   (or `get_schema`) and look for a `deriva-ml` schema. If it's missing, the user
   runs `/deriva-ml:setup-ml-catalog` † to install it or to clone the data into a
   new DerivaML catalog.
2. **What is already there?** Domain and asset tables (`/deriva-ml:browse-erd` †
   for a diagram), vocabularies
   (`deriva://catalog/{hostname}/{catalog_id}/deriva-ml/vocabularies/{schema}`), and
   datasets (`deriva://catalog/{hostname}/{catalog_id}/deriva-ml/datasets`).
3. **Are the labels features?** Check
   `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/features/{table}`. Labels
   stored as plain columns have no provenance. Ask the user whether to use them as
   they are (and record that choice in `tacit-knowledge.md`) or re-express them as a
   feature populated by an import execution (`/deriva-ml:create-feature`).
4. **Whose catalog is it?** Model work writes to the catalog — datasets,
   executions, feature values, and sometimes new tables. If other people own it,
   ask before the first write of any kind, and offer
   `/deriva-ml:setup-ml-catalog` † to clone a slice into a catalog of your own.

## Phase 3: Point the repo at the catalog

Set the connection (hostname, catalog ID) in `src/configs/deriva.py`. For an
existing catalog, ask which of its datasets the project should use, then populate
the dataset and asset configs from it — `/deriva-ml:write-hydra-config`
("bootstrap configs from an existing catalog").

## Phase 4: Datasets

Create, split, and release the datasets the first model needs with
`/deriva-ml:dataset-lifecycle`, splitting by the unit that must not leak (patient
or eye, not image, when a subject has several images). Wire the released versions
into `src/configs/datasets.py`.

For an existing catalog, add anything Phase 2 found missing first: domain tables
(`/deriva:create-table` †, or the `create_table` MCP tool), vocabularies
(`deriva_ml_create_vocabulary` then `add_term`; rules in
`/deriva:manage-vocabulary` †), asset tables (`/deriva-ml:work-with-assets`), and
features (`/deriva-ml:create-feature`). Later data additions go through
`/deriva-ml:work-with-assets` or `/deriva-ml:generate-scripts`.

## Phase 5: Ready to run, then hand off

The project is ready for its first run when all of these hold:

- `uv run deriva-ml-run --list-configs` resolves, and the working tree is committed;
- authentication to the catalog checks out;
- the catalog has the `deriva-ml` schema;
- at least one **released** dataset version is wired into `src/configs/datasets.py`.

From here, `/deriva-ml:model-development-workflow` takes over: the model design,
a small development dataset, then dry run → small run → full run. Record each
setup decision (catalog choice, label handling, split unit) in
`tacit-knowledge.md` as it is made.

## Common mistakes

- Building a repo with `uv init` instead of from the template — it misses the
  config scaffolds, entry points, and tacit-knowledge files.
- Assuming an existing catalog is a DerivaML catalog without checking for the
  `deriva-ml` schema.
- Writing to someone else's catalog without asking.
- Treating plain label columns as if they carried provenance.
- Splitting by image when several images come from one subject — the test set
  then leaks into training.
- Running before committing, so the execution records a commit that doesn't
  match the code.
