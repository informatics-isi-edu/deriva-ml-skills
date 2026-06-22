---
name: design-experiment
description: "ALWAYS use BEFORE configuring an experiment or building a dataset in DerivaML — the design-first phase that captures goals, requirements, validation criteria, and analysis plan into a standardized Markdown document the configuration (or dataset construction) then implements. Owns the experiment-design/ and dataset-design/ directory conventions and the two parallel design-doc templates. The design doc is the up-front CONTRACT (the plan before you build); tacit-knowledge.md stays the running journal (what you learned during/after) — the two cross-link. This skill is the first phase of both experiment-lifecycle (Phase 1) and dataset-lifecycle (Phase 1: Design); they hand off here. Triggers on: 'design an experiment', 'plan an experiment', 'design a dataset', 'plan a dataset', 'what's my hypothesis', 'capture goals and requirements', 'validation criteria', 'analysis plan', 'before I configure', 'before I build the dataset', 'write a design doc', 'experiment-design', 'dataset-design'. Do NOT use for: the running decision journal (that's capture-tacit-knowledge), writing the hydra config (configure-experiment / write-hydra-config), or actually building/splitting the dataset (dataset-lifecycle Phase 4+)."
---

# Design-First: Experiment and Dataset Design

Before you write a config or build a dataset, capture **what you're trying to
achieve and how you'll know you succeeded** — in a standardized document, in
the repo, that the work then implements. This is the design-first phase that
both `/deriva-ml:experiment-lifecycle` and `/deriva-ml:dataset-lifecycle` open
with.

## Why a design doc (and not just `tacit-knowledge.md`)

The two are complementary, not redundant:

- **The design doc is the up-front contract** — the plan you write *before*
  building: goals, requirements, validation criteria, analysis plan. It's a
  durable, reviewable, per-experiment (or per-dataset) artifact. The config
  implements it; the dataset is built to it; the execution records that it ran.
- **`tacit-knowledge.md` is the running journal** — what you *learned* during
  and after: the rationale for decisions, what worked, what surprised you.

They cross-link: the design doc's **Status & links** section points at the
`tacit-knowledge.md` entries its run generated; a journal entry about a
designed experiment links back to its design doc. `capture-tacit-knowledge`
keeps firing exactly as before — design = *before*, capture = *during/after*.

The most expensive failure mode in ML work is building (and running) something
that, regardless of result, doesn't answer the question that motivated it. The
design doc is cheap; finding out you tested the wrong thing after the run is
not.

## When to use which template

| You are about to… | Template | Directory |
|---|---|---|
| Configure and run an experiment | experiment-design | `experiment-design/<slug>.md` |
| Create, split, subsample, or curate a dataset | dataset-design | `dataset-design/<slug>.md` |

Both share the same section skeleton — **Goal/Purpose · Requirements ·
Validation · Analysis/Consumption · Status & links** — so the two read alike.
The full fill-in templates and worked examples are in `references/`:

- `references/experiment-design-template.md`
- `references/dataset-design-template.md`

## The discipline

1. **Write the design doc first.** One `<slug>.md` per experiment/dataset in
   the matching directory. Use the template; fill every section. A section you
   can't fill is a design question you haven't answered yet — answer it now,
   not after the run.
2. **Get it to "Approved"** (the Status field) before moving to configuration
   (experiments) or construction (datasets). For solo work, "Approved" means
   *you* re-read it and it holds together; in a team, it's the review gate.
3. **The config / dataset implements the doc.** When you write the hydra config
   (`/deriva-ml:configure-experiment`) or build the dataset
   (`/deriva-ml:dataset-lifecycle` Phase 4+), cross-check that every
   **Requirement** in the design is satisfied. A requirement with no
   corresponding config/dataset decision is a gap.
4. **Close the loop.** After the run/build, update the doc's **Status & links**
   with the resulting RID(s) / execution(s) / config entries and a link to the
   `tacit-knowledge.md` entries the work produced. The design doc is then a
   complete record: plan → implementation → outcome.

## Slug naming

`<slug>` is a short kebab-case handle matching the experiment/dataset's intent,
e.g. `dropout-vs-baseline.md`, `lr-sweep-2layer.md`, `cifar10-dev-subset.md`.
Keep it stable — the config's experiment name and the doc slug should be easy
to associate.

## Related Skills

- **`/deriva-ml:experiment-lifecycle`** — opens with this skill as its Phase 1
  (hypothesis/design); returns here at the start of each new cycle.
- **`/deriva-ml:dataset-lifecycle`** — opens with this skill as its Phase 1
  (Design) before planning structure.
- **`/deriva-ml:configure-experiment`** / **`/deriva-ml:write-hydra-config`** —
  the config that *implements* an approved experiment-design doc.
- **`/deriva-ml:capture-tacit-knowledge`** (auto-fires) — the during/after
  counterpart. Design = the plan before; capture = what was learned.
- **`/deriva-ml:generate-descriptions`** (auto-fires) — when the design's Goal
  becomes the experiment/dataset `description`, this drafts it.
