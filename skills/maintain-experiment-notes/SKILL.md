---
name: maintain-experiment-notes
description: "ALWAYS invoke this skill as part of completing any action where the user made a choice that a future team member would need to understand. The purpose is to capture tacit knowledge — the reasoning behind decisions that would otherwise be lost when context switches or people move on. This includes: creating or splitting datasets, creating features or vocabularies, adding vocabulary terms, running experiments or models, choosing hyperparameters, changing catalog structure (tables, columns, FKs), writing or modifying hydra-zen configs, loading data into a catalog, bumping package versions, creating or cloning catalogs, interpreting experiment results, or resolving a problem with a non-obvious fix. Invoke it in the SAME response where you perform the action — not in a later turn. If you just called create_feature, split_dataset, create_table, create_vocabulary, add_term, create_catalog, clone_catalog, load-cifar10, deriva-ml-run, bump-version, or made a code change that reflects a design decision, this skill applies. Even if the user did not ask you to document anything, silently append the decision and rationale to experiment-decisions.md. Do NOT invoke for routine read-only operations (queries, listing, browsing schemas) that involve no choice."
user-invocable: false
---

# Capture Experiment Design Decisions

Automatically record experiment design decisions and their rationale in `experiment-decisions.md` in the project root. This file is a shared, persistent record of *why* the experiment was designed the way it was — not a session log. When a new team member checks out the repository, reading this file should give them the full context behind every significant choice.

## What This Is NOT

This is not a session log, a task list, or a changelog. It does not track who did what or when sessions started and ended. It captures *decisions and reasoning* — the kind of institutional knowledge that normally lives only in someone's head and is lost when they move on.

## When to Write

Append an entry after any of these events:

- **Dataset composition**: Why these members were included/excluded, why this size, why these types
- **Split strategy**: Why this split ratio, why stratified, why patient-level vs image-level
- **Feature selection**: Why this feature was created (or reused), what it represents, why this vocabulary
- **Architecture/model choice**: Why this model, why these hyperparameters, what alternatives were considered
- **Running experiments**: What was run, what the key results were, what was learned, what to try next
- **Catalog structure changes**: Why a table was added/extended, why a column was added, why a FK was created
- **Configuration choices**: Why this hydra-zen config, why these overrides, why this multirun setup
- **Data loading**: Why this data source, why this subset size, any filtering or transformation choices
- **Version bumping**: Why bumping now, what milestone or set of changes warranted a release
- **Catalog management**: Why a new catalog was created or cloned, what it's for, why this alias
- **Problem resolution**: What went wrong and why the chosen fix was correct (not just "fixed it")

Do NOT write entries for routine operations that don't involve a choice — querying data, reading schemas, listing datasets. Only capture moments where an alternative existed and a direction was chosen.

## How to Write

Append to `experiment-decisions.md` silently — do not ask the user for permission or tell them you're updating it. This should be invisible. If the file doesn't exist, create it with the header.

Each entry is a short block:

```markdown
### <Concise decision title>

<1-3 sentences explaining what was decided and why. Include the alternatives that were considered and rejected. Reference catalog entities by RID where relevant.>
```

Keep entries concise. The goal is density of reasoning, not completeness of description. Someone scanning the file should quickly understand the shape of the decisions.

## File Structure

```markdown
# Experiment Design Decisions

Accumulated rationale for experiment design choices in this project.
Each entry captures what was decided and why.

---

### Patient-level splitting to prevent data leakage

Split dataset `2-B4C8` at the patient level (stratified by Subject RID) rather than
random image-level splitting. Multiple images per patient would leak information
between train and test if split at the image level. Used 80/20 ratio with seed 42.

### Reused Disease_Classification feature instead of creating Diagnosis

User requested a "Diagnosis" feature on Image, but Disease_Classification (RID: 2-XXXX)
already exists with 3,200 values and 8 disease terms. Creating a separate feature
would fragment annotations. Added "Fundus_Dystrophy" as a new term to the existing
vocabulary instead.

### Learning rate 0.001 selected from sweep

Sweep over [0.0001, 0.001, 0.01, 0.1] showed 0.001 achieved best validation AUC (0.94)
while 0.01 showed training instability after epoch 15. 0.0001 converged too slowly
for the 50-epoch budget.

### Added Enrollment_Date to Subject instead of creating Patient table

User requested a Patient table with Name, Age, Gender, Enrollment_Date. Subject table
(RID: 1-4W2G) already has Name, Age, Gender with 1,247 records and 8 incoming FKs.
Creating a duplicate table would orphan all existing relationships. Added Enrollment_Date
column to Subject instead.
```

## Relationship to Other Files

- **`experiments.md`**: Describes *what* each experiment configuration does (parameters, inputs, outputs). The experiment-decisions file explains *why* those configurations exist.
- **CLAUDE.md**: Project-level instructions for Claude. Reference experiment-decisions.md from CLAUDE.md so new sessions pick up context.
- **Hydra configs**: Define the experiment parameters. The decisions file explains why those parameter values were chosen.

## Keeping the File in Git

`experiment-decisions.md` **must be tracked in the git repository** — it's part of the project's permanent record. Before writing the first entry, verify it's not gitignored:

1. Check that `experiment-decisions.md` is not in `.gitignore`
2. If the file doesn't exist yet, create it and `git add experiment-decisions.md` immediately
3. Never place it in a directory that's gitignored (e.g., `outputs/`, `.cache/`, `dist/`)

The file belongs in the **project root** alongside `CLAUDE.md`, `pyproject.toml`, and other project-level files.

## Commit Prompting

The decisions file is only useful to the team if it gets committed. After writing 3 or more entries during a session, or when the conversation reaches a natural pause (the user has finished a workflow, is about to start something new, or the topic shifts), suggest committing:

> "You've accumulated several experiment design decisions this session. Want me to commit `experiment-decisions.md` so the team has the rationale on record?"

If the user says yes, commit just `experiment-decisions.md` with a message like "Record experiment design decisions" — do not bundle it with unrelated changes. If the user says no or not yet, don't ask again until more entries are added.

Do not prompt after every single entry — that would be annoying. Wait for a batch to accumulate or a natural break in the work.

## Writing Guidelines

- Lead with the decision, not the process that led to it
- Always state what was *rejected* and why — "chose X over Y because Z"
- Reference RIDs for catalog entities so entries are traceable
- Include quantitative evidence when available (accuracy numbers, counts, sizes)
- Keep each entry to 2-5 lines — these should be scannable
- Don't duplicate information that's already in experiment descriptions or config files
- Write in past tense — these are settled decisions, not plans
