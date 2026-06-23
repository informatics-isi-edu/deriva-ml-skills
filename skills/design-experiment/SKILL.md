---
name: design-experiment
description: "ALWAYS use BEFORE configuring an experiment or building a dataset in DerivaML — the design-first phase that captures goals, requirements, validation criteria, and analysis plan into a standardized Markdown document the configuration (or dataset construction) then implements. Owns the docs/design/{experiment,dataset,feature,model}/ directory conventions and the four parallel design-doc templates. The design doc is the up-front CONTRACT (the plan before you build); tacit-knowledge.md stays the running journal (what you learned during/after) — the two cross-link. This skill is the first phase (Specify) of all four lifecycles — experiment-lifecycle, dataset-lifecycle, create-feature, and model-development-workflow; they each hand off here. Triggers on: 'design an experiment', 'plan an experiment', 'design a dataset', 'plan a dataset', 'what's my hypothesis', 'capture goals and requirements', 'validation criteria', 'analysis plan', 'before I configure', 'before I build the dataset', 'write a design doc', 'experiment-design', 'dataset-design', 'design a feature', 'design a model', 'feature-design', 'model-design'. Do NOT use for: the running decision journal (that's capture-tacit-knowledge), writing the hydra config (configure-experiment / write-hydra-config), or actually building/splitting the dataset (dataset-lifecycle Phase 4+)."
---

# Design-First: Experiment, Dataset, Feature, and Model Design

Before you build anything — a config, a dataset, a feature, or a model —
capture **what you're trying to achieve and how you'll know you succeeded** —
in a standardized document, in the repo, that the work then implements. This is
the design-first (Specify) phase that all four lifecycle skills open with:
`/deriva-ml:experiment-lifecycle`, `/deriva-ml:dataset-lifecycle`,
`/deriva-ml:create-feature`, and `/deriva-ml:model-development-workflow`.

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
| Configure and run an experiment | experiment-design | `docs/design/experiment/<slug>.md` |
| Create, split, subsample, or curate a dataset | dataset-design | `docs/design/dataset/<slug>.md` |
| Create a feature (label, score, annotation) | feature-design | `docs/design/feature/<slug>.md` |
| Author or substantially change a model | model-design | `docs/design/model/<slug>.md` |

All four share the same section skeleton — **Goal/Purpose · Requirements ·
Validation · (entity-specific) · Upstream designs · Status & links** — so they
read alike across entities. The full fill-in templates and worked examples are
in `references/`:

- `references/experiment-design-template.md`
- `references/dataset-design-template.md`
- `references/feature-design-template.md`
- `references/model-design-template.md`

## The discipline

1. **Write the design doc first.** One `<slug>.md` per experiment / dataset /
   feature / model in the matching `docs/design/<entity>/` directory. Use the
   template; fill every section. A section you can't fill is a design question
   you haven't answered yet — answer it now, not after the run.
2. **Get it to "Approved"** (the Status field) before moving to configuration
   (experiments) or construction (datasets/features/models). For solo work,
   "Approved" means *you* re-read it and it holds together; in a team, it's the
   review gate.

> **Match the doc's weight to the work — don't let this become ceremony.** A
> full design doc earns its cost for *durable, expensive, or hypothesis-bearing*
> work: a new experiment hypothesis, a new split/subsample, a feature a model or
> split will depend on, a new or substantially-changed model. For *cheap,
> reversible* work — a quick parameter tweak on an existing experiment
> (`lr=3e-4` rerun), a one-off dev/debug/smoke run, reusing a dataset unchanged,
> a trivial single-term label — a **one-line design note** (goal + success
> criterion, written *before you start*) is enough; skip the full doc. For cheap
> work that one-liner can live as a dated entry in `tacit-knowledge.md` rather
> than a separate design doc — but it is still a *design note written up front*,
> not a during/after journal entry; the placement is pragmatic, the timing is
> unchanged. The test: *would a future teammate (or reviewer) need this written
> down to trust or reproduce the result?* If no, stay lightweight. The lifecycle
> skills carry this same fast-path rule at their Specify phase.
3. **The config / dataset implements the doc.** When you write the hydra config
   (`/deriva-ml:configure-experiment`) or build the dataset
   (`/deriva-ml:dataset-lifecycle` Phase 4+), cross-check that every
   **Requirement** in the design is satisfied. A requirement with no
   corresponding config/dataset decision is a gap.
4. **Close the loop.** After the run/build, update the doc's **Status & links**
   with the resulting RID(s) / execution(s) / config entries and a link to the
   `tacit-knowledge.md` entries the work produced. The design doc is then a
   complete record: plan → implementation → outcome.

**Before building, look for an existing design.** When you start configuring
or building something, first check the matching `docs/design/<entity>/`
directory for an existing `<slug>.md` and read it — don't re-derive a plan
that's already written. If none exists, that's the signal to author one now.

**Upstream designs (the spec dependency tree).** Each design doc names the
design docs it builds on, mirroring the entity dependency graph: an
experiment-design names the model-design + dataset-design it uses; a
model-design names the feature-designs it consumes. A dataset-design does NOT
name a feature as a dependency (a dataset doesn't depend on features) — where a
split reads a feature its *elements* carry, note that element feature as a
precondition, not an upstream design. This makes genuine build dependencies
traceable at the spec layer.

## Slug naming

`<slug>` is a short kebab-case handle matching the entity's intent,
e.g. `dropout-vs-baseline.md` (experiment), `lr-sweep-2layer.md` (experiment),
`cifar10-dev-subset.md` (dataset), `image-quality-label.md` (feature),
`cifar10-2layer-cnn.md` (model).
Keep it stable — the config's experiment name and the doc slug should be easy
to associate.

## Related Skills

- **`/deriva-ml:experiment-lifecycle`** — opens with this skill as its Phase 1
  (hypothesis/design); returns here at the start of each new cycle.
- **`/deriva-ml:dataset-lifecycle`** — opens with this skill as its Phase 1
  (Design) before planning structure.
- **`/deriva-ml:create-feature`** — opens with this skill as its Phase 1
  (Specify) to author the `feature-design` before creating the feature.
- **`/deriva-ml:model-development-workflow`** — opens with this skill as its
  Phase 1 (Specify) to author the `model-design` before bootstrapping.
- **`/deriva-ml:new-model`** — authors the model from an approved `model-design`
  (the Build side; this skill is the Specify side).
- **`/deriva-ml:configure-experiment`** / **`/deriva-ml:write-hydra-config`** —
  the config that *implements* an approved experiment-design (and the model
  layer that implements a model-design).
- **`/deriva-ml:capture-tacit-knowledge`** (auto-fires) — the during/after
  counterpart. Design = the plan before; capture = what was learned.
- **`/deriva-ml:generate-descriptions`** (auto-fires) — when the design's Goal
  becomes the experiment/dataset `description`, this drafts it.
