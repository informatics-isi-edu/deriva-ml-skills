# Design-First Phase for the DerivaML Lifecycle

**Date:** 2026-06-22
**Status:** Approved (design); pending implementation
**Author:** Carl Kesselman + Claude

## Problem

The DerivaML lifecycle skills already have a *design step*, but it is thin
and ephemeral — there is no durable, standardized, reviewable artifact that
captures an experiment's (or dataset's) **goals, requirements, validation
criteria, and analysis plan** before configuration/construction begins.

Concretely, in the current skills:

- **`experiment-lifecycle` Phase 1 ("Identify hypothesis")** asks the four
  right questions (question / evidence / success criterion / cost budget) but
  its *deliverable* is "write it in `tacit-knowledge.md`" — a running journal,
  not a standardized per-experiment design document. No template, no
  dedicated location, no review gate.
- **`configure-experiment`** jumps straight to config groups. The only place
  goals are captured structurally is Rule 5 ("goal-oriented descriptions"),
  squeezed into a one-line `description=` field.
- **`dataset-lifecycle` Phase 2 ("Plan")** covers *structure* (splits, types,
  axes) — "how to build it" — but not goals/requirements/validation: "what is
  it for and how will we know it's right."
- **`model-development-workflow` Phase 1** is *schema* design, not
  *experiment* design.

So the up-front design contract an experiment/dataset is built to satisfy is
never recorded as a first-class document. The catalog records *what ran*;
`tacit-knowledge.md` records *why decisions were made along the way*; nothing
records *the plan the work was built to satisfy*.

## Goal

Insert a **design-first phase** before configuration (experiments) and before
construction (datasets) that produces a **standardized Markdown design
document in a versioned repo directory**. The document is the contract: the
config implements it; the dataset is built to it; the execution records that
it ran.

The experiment and dataset design phases are **symmetric** — same activity
("capture goals → requirements → validation → analysis before you build"),
same document skeleton, same discipline, same routing shape — differing only
in entity-specific prompts.

## Design

### New skill: `design-experiment`

A single new skill owns **both** the experiment-design and dataset-design
surfaces (symmetric, DRY — one home for "design before you build,"
parameterized by entity type).

- **Name:** `design-experiment` ("experiment" is the dominant term users
  reach for; matches the `configure-experiment` / `experiment-lifecycle`
  naming family). The `description` carries dataset triggers so it also fires
  for dataset design.
- **Invocation:** user-invocable (`/deriva-ml:design-experiment`) AND
  auto-fires on design phrasing. It is a **guide-shaped** skill (discipline +
  template), so it does NOT get `disable-model-invocation`.
- **Owns:**
  - the two standardized document templates (experiment + dataset),
  - the two directory conventions (`experiment-design/`, `dataset-design/`),
  - the shared design-first discipline (the reusable principle both lifecycles
    reference).

Auto-fires alongside `capture-tacit-knowledge`: **design = before** (the plan),
**capture = during/after** (what was learned). The two are complementary and
explicitly cross-referenced.

### Document templates

Both documents share a section skeleton so learning one teaches the other.
They differ only in entity-specific prompts. One file per design, named
`<slug>.md`.

**`experiment-design/<slug>.md`**

| Section | Captures |
|---|---|
| **Goal** | One-sentence question being tested ("Does X improve Y for purpose C?") |
| **Hypothesis** | Expected outcome + direction |
| **Requirements** | Data (which datasets + versions), assets (weights/checkpoints), vocabularies, compute budget |
| **Validation** | The metric, the baseline, and the three criteria: what *confirms* / *refutes* / *renders inconclusive* the hypothesis |
| **Analysis plan** | How results get evaluated (single-run read vs comparison vs sweep), which tool/feature |
| **Status & links** | Draft / Approved / Run / Concluded · links to the config it drove, the execution RID(s) it produced, the `tacit-knowledge.md` entries from the run |

**`dataset-design/<slug>.md`** (parallel skeleton)

| Section | Captures |
|---|---|
| **Purpose** | What the dataset is *for* (one sentence) |
| **Requirements** | Source data, target size/composition, element types, balance constraints |
| **Structure plan** | Standalone / split / subsample / curated; the three-axis `Dataset_Type` tags planned |
| **Validation** | How correctness is verified — class balance, no train/test leakage, bag parity, count checks |
| **Consumption** | Who uses it downstream (which experiments/configs), version-pinning expectation |
| **Status & links** | Draft / Approved / Built / Released · links to the produced RID+version, `configs/datasets.py` entry, `tacit-knowledge.md` |

### Relationship to `tacit-knowledge.md`

The design doc is the **up-front contract** (the plan *before*);
`tacit-knowledge.md` stays the **running journal** (what we learned
*during/after*). They are complementary and cross-link:

- The design doc's "Status & links" section points at the `tacit-knowledge.md`
  entries its run generated.
- A `tacit-knowledge.md` entry that references a designed experiment/dataset
  links back to its design doc.

The design doc does NOT replace `tacit-knowledge.md`, and capture discipline
is unchanged — the SessionStart/UserPromptSubmit hooks and
`capture-tacit-knowledge` continue exactly as today.

### Directory conventions

- `experiment-design/` — top-level repo directory, one `<slug>.md` per
  experiment design.
- `dataset-design/` — top-level repo directory, one `<slug>.md` per dataset
  design.

These live in the user's ML project repo (versioned alongside `configs/`,
`src/`, `tacit-knowledge.md`), not in the plugin.

### Lifecycle wiring (routing edits)

1. **`experiment-lifecycle` Phase 1 — rewritten.** From "identify hypothesis →
   write to `tacit-knowledge.md`" to **"author the experiment-design doc via
   `/deriva-ml:design-experiment`."** The four hypothesis questions become the
   doc's sections. The inter-phase gate becomes: the design doc is **Approved**
   before advancing to Phase 2 (Create configuration). The routing-summary
   table's Phase-1 row points at `design-experiment`.

2. **`dataset-lifecycle` — new Phase 0 (Design).** A parallel design section
   inserted *before* the current Phase 2 ("Plan"), handing off to the same
   `design-experiment` skill, producing a `dataset-design/<slug>.md`. The
   existing Phase 2 becomes the *implementation* of that design (structure,
   types). Renumbering: the current phases stay as-is by name; the new section
   is "Phase 0 — Design" to avoid renumbering churn, OR an explicit "Design"
   phase placed before "Assess/Plan" (implementation decides the cleanest
   numbering; the content placement is fixed: design precedes plan).

3. **`configure-experiment` — one-line pointer.** At the top of "Setup Steps":
   the config implements an **approved experiment-design doc**; cross-check
   that every *Requirement* in the design is satisfied by the config groups
   before running. Does not duplicate the template — references
   `design-experiment`.

4. **`model-development-workflow` — note.** Cycle-zero's first real
   (non-validation) experiment still gets a design doc. Phase 7 ("Iterate")
   already routes to `experiment-lifecycle`; add a sentence that the first
   hypothesis-driven experiment authors a design doc via `design-experiment`.

### Cross-references

- All four touched skills get `design-experiment` added to their **Related
  Skills** sections.
- `design-experiment`'s own Related Skills point at `experiment-lifecycle`
  (Phase 1 consumer), `dataset-lifecycle` (Phase 0 consumer),
  `configure-experiment` (implements the design), and `capture-tacit-knowledge`
  (the during/after counterpart).
- `CLAUDE.md` skill inventory updated: skill count (30 → 31), and the new
  skill listed under the appropriate invocation-model section
  (user-command + auto-fire guide).

## Non-goals / YAGNI

- **No MCP tool, no script.** The design doc is authored by the agent following
  the skill, written with the Write tool into the repo. No catalog
  interaction, no Python helper — a design doc is prose, not a catalog entity.
- **No catalog-side design entity.** Designs are repo artifacts, not catalog
  records. (The *experiment* and *dataset* they describe become catalog
  entities when run/built; the design that motivated them stays in the repo,
  like `configs/` and `tacit-knowledge.md`.)
- **No enforcement mechanism.** Nothing blocks a run that lacks a design doc;
  the discipline is guidance (like the rest of the lifecycle gates), not a
  hard gate in code.
- **No migration of existing `tacit-knowledge.md` content.** The journal stays
  as-is; design docs are forward-looking.

## Skill anatomy (for implementation)

```
skills/design-experiment/
  SKILL.md                      # discipline + both templates inline (or short) + routing
  references/
    experiment-design-template.md   # the full experiment-design skeleton + worked example
    dataset-design-template.md       # the full dataset-design skeleton + worked example
```

The SKILL.md carries the discipline and the section skeletons; the
`references/` files carry the full fill-in templates and a worked example each
(so the SKILL.md stays scannable and the templates are copy-pasteable).

## Affected files

| File | Change |
|---|---|
| `skills/design-experiment/SKILL.md` | NEW — the skill |
| `skills/design-experiment/references/experiment-design-template.md` | NEW |
| `skills/design-experiment/references/dataset-design-template.md` | NEW |
| `skills/experiment-lifecycle/SKILL.md` | Phase 1 rewrite + routing table + Related Skills |
| `skills/dataset-lifecycle/SKILL.md` | new Design phase + Related Skills |
| `skills/configure-experiment/SKILL.md` | one-line pointer at Setup Steps |
| `skills/model-development-workflow/SKILL.md` | one sentence in Phase 7 / Iterate |
| `CLAUDE.md` | skill count + inventory listing for the new skill |

## Release

This is a `skills/` change → after merge it needs the standard release tail:
`bump-version` (minor — a new skill is a feature) + meta-marketplace pin and
`deriva-ml--v<version>` tag. The new skill ships automatically via the
`skills/` glob in the release tar; no `release.yml` change.
