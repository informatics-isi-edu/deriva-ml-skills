# Design-First Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `design-experiment` skill that owns a symmetric design-first phase for experiments and datasets (capture goals/requirements/validation/analysis into a standardized Markdown doc before configuration/construction), and wire it into the existing lifecycle skills.

**Architecture:** One new guide-shaped skill carries two parallel document templates (experiment + dataset) sharing a section skeleton, the two directory conventions (`experiment-design/`, `dataset-design/`), and the shared design-first discipline. Four existing skills get routing edits pointing at it; `CLAUDE.md` gets the inventory update. No code, no tests in the executable sense — these are Markdown skills, so "verification" per task = frontmatter parses, cross-references resolve, templates are copy-paste-valid, counts are consistent.

**Tech Stack:** Markdown (SKILL.md + references), YAML frontmatter. No Python, no build step. Verification via `python3` one-liners for YAML/JSON validity and `grep` for cross-reference resolution.

## Global Constraints

- **Skill is guide-shaped:** `design-experiment` is user-invocable AND auto-fires. Do NOT add `disable-model-invocation`. (Per spec: it guides proactively.)
- **Design doc = up-front contract; `tacit-knowledge.md` = running journal.** Never conflate them; the two cross-link. Capture discipline (hooks, `capture-tacit-knowledge`) is unchanged.
- **Symmetry is load-bearing:** experiment-design and dataset-design share the same section skeleton (Goal/Purpose · Requirements · Validation · Analysis/Consumption · Status & links). A reader who learns one must recognize the other.
- **No new MCP tool, no script, no catalog entity, no hard enforcement gate, no migration of existing journal content.** (Spec non-goals.)
- **Directories live in the user's ML project repo**, not in the plugin: `experiment-design/` and `dataset-design/`, one `<slug>.md` per design.
- **Cross-reference annotation convention:** references to deriva-skills land as `/deriva:<name>` *(deriva-skills)*; references within this plugin as `/deriva-ml:<name>`.
- **Release tail (after merge):** `bump-version` **minor** (new skill = feature) + meta-marketplace pin + `deriva-ml--v<version>` tag. Not part of these tasks; noted for the close-out.

---

### Task 1: Create the `design-experiment` skill (SKILL.md)

**Files:**
- Create: `skills/design-experiment/SKILL.md`

**Interfaces:**
- Produces: the `/deriva-ml:design-experiment` command and auto-fire triggers; the directory conventions `experiment-design/` and `dataset-design/`; references to `references/experiment-design-template.md` and `references/dataset-design-template.md` (created in Tasks 2–3).
- Consumes: nothing (first task).

- [ ] **Step 1: Write the SKILL.md**

Create `skills/design-experiment/SKILL.md` with exactly this content:

```markdown
---
name: design-experiment
description: "ALWAYS use BEFORE configuring an experiment or building a dataset in DerivaML — the design-first phase that captures goals, requirements, validation criteria, and analysis plan into a standardized Markdown document the configuration (or dataset construction) then implements. Owns the experiment-design/ and dataset-design/ directory conventions and the two parallel design-doc templates. The design doc is the up-front CONTRACT (the plan before you build); tacit-knowledge.md stays the running journal (what you learned during/after) — the two cross-link. This skill is the first phase of both experiment-lifecycle (Phase 1) and dataset-lifecycle (Phase 1: Design); they hand off here. Triggers on: 'design an experiment', 'plan an experiment', 'design a dataset', 'plan a dataset', 'what's my hypothesis', 'capture goals and requirements', 'validation criteria', 'analysis plan', 'before I configure', 'before I build the dataset', 'write a design doc', 'experiment-design', 'dataset-design'. Do NOT use for: the running decision journal (that's capture-tacit-knowledge), writing the hydra config (configure-experiment / write-hydra-config), or actually building/splitting the dataset (dataset-lifecycle Phase 3+)."
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
   (`/deriva-ml:dataset-lifecycle` Phase 3+), cross-check that every
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
```

- [ ] **Step 2: Verify the frontmatter parses**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && python3 -c "
import re, sys, pathlib
t = pathlib.Path('skills/design-experiment/SKILL.md').read_text()
m = re.match(r'^---\n(.*?)\n---\n', t, re.DOTALL)
assert m, 'no frontmatter block'
import yaml  # PyYAML may be absent; fall back to a structural check
" 2>/dev/null && echo "yaml-parse-attempted" || echo "skip yaml lib"
```
Then the lib-free structural check (this is the authoritative one):
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && python3 -c "
import re, pathlib
t = pathlib.Path('skills/design-experiment/SKILL.md').read_text()
m = re.match(r'^---\n(.*?)\n---\n', t, re.DOTALL)
assert m, 'no frontmatter'
fm = m.group(1)
assert re.search(r'^name: design-experiment\$', fm, re.M), 'name wrong/missing'
assert 'description:' in fm, 'no description'
assert 'disable-model-invocation' not in fm, 'must NOT be disable-model-invocation (guide-shaped)'
print('frontmatter OK')
"
```
Expected: `frontmatter OK`

- [ ] **Step 3: Verify it is auto-discovered as a skill (dir + SKILL.md present)**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && test -f skills/design-experiment/SKILL.md && echo "skill file present"
```
Expected: `skill file present`

- [ ] **Step 4: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/design-experiment/SKILL.md && git commit -m "feat(design-experiment): add the design-first skill (SKILL.md)"
```

---

### Task 2: Create the experiment-design template

**Files:**
- Create: `skills/design-experiment/references/experiment-design-template.md`

**Interfaces:**
- Consumes: referenced by `SKILL.md` (Task 1) at `references/experiment-design-template.md`.
- Produces: the canonical experiment-design section skeleton (Goal · Hypothesis · Requirements · Validation · Analysis plan · Status & links) that Task 4's experiment-lifecycle Phase 1 rewrite points users at.

- [ ] **Step 1: Write the template file**

Create `skills/design-experiment/references/experiment-design-template.md` with exactly this content:

```markdown
# Experiment Design Template

Copy this into `experiment-design/<slug>.md` and fill every section. Each
section maps to a question the experiment must answer *before* it runs. A
section you can't fill is a design gap — close it now.

---

## Template (copy below this line)

```markdown
# Experiment Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Run | Concluded -->
**Date:** <YYYY-MM-DD>

## Goal

The single question this experiment tests, in one sentence.
"Does <X> improve <Y> for <purpose C>?" Be specific enough that the answer
is checkable.

## Hypothesis

The expected outcome and its direction. "Dropout 0.25 reduces overfitting,
raising test accuracy on the small labeled split by ≥3% vs the unregularized
baseline."

## Requirements

- **Data:** which dataset(s) + pinned version(s) the run consumes
  (e.g. `cifar10_labeled_split` @ `2.0.0`).
- **Assets:** pretrained weights / checkpoints by RID, if any.
- **Vocabularies:** any vocabulary terms the config relies on.
- **Compute budget:** rough GPU-hours / wall-clock / max cycles before
  stopping regardless of result.

## Validation

- **Metric:** the exact metric and how it's computed (e.g. top-1 test
  accuracy on the held-out split).
- **Baseline:** what this is compared against (a prior execution RID, a
  fixed threshold).
- **Confirms the hypothesis if:** <criterion>
- **Refutes the hypothesis if:** <criterion>
- **Inconclusive if:** <criterion> — and what you'd change to make a
  follow-up conclusive.

## Analysis plan

How results get evaluated: single-run read of feature values
(`deriva_ml_list_feature_values`), multi-run comparison
(`/deriva-ml:compare-model-runs`), or a sweep
(`deriva_ml_multirun_status`). Name the tool and the feature/metric.

## Status & links

- **Config:** the experiment name + `configs/experiments.py` entry that
  implements this design.
- **Executions:** RID(s) produced by the run(s).
- **tacit-knowledge.md:** link to the journal entries this run generated.
```

---

## Worked example

```markdown
# Experiment Design: dropout vs unregularized baseline

**Slug:** dropout-vs-baseline
**Status:** Approved
**Date:** 2026-06-22

## Goal
Does adding dropout 0.25 to the 2-layer CNN reduce overfitting on the small
labeled CIFAR-10 split?

## Hypothesis
Dropout 0.25 narrows the train/test accuracy gap and raises top-1 test
accuracy by ≥3% vs the current unregularized baseline (execution 6-ABC1).

## Requirements
- **Data:** `cifar10_small_labeled_split` @ `1.0.0`
- **Assets:** none (train from scratch)
- **Vocabularies:** Workflow_Type `Training` (exists)
- **Compute budget:** ≤ 2 GPU-hours; at most 3 cycles.

## Validation
- **Metric:** top-1 accuracy on the test partition, written as the
  `Test_Accuracy` feature.
- **Baseline:** execution `6-ABC1` (unregularized), test accuracy 0.61.
- **Confirms if:** dropout run's test accuracy ≥ 0.64 AND train/test gap
  shrinks.
- **Refutes if:** test accuracy ≤ baseline, or gap unchanged/wider.
- **Inconclusive if:** within ±1% of baseline — rerun on the full split.

## Analysis plan
Single-run read of `Test_Accuracy` via `deriva_ml_list_feature_values`, then
a two-run comparison against `6-ABC1` via `/deriva-ml:compare-model-runs`.

## Status & links
- **Config:** `dropout_quick` in `configs/experiments.py`
- **Executions:** (filled after the run)
- **tacit-knowledge.md:** (filled after the run)
```
```

- [ ] **Step 2: Verify the file exists and is non-empty Markdown**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && test -s skills/design-experiment/references/experiment-design-template.md && head -1 skills/design-experiment/references/experiment-design-template.md
```
Expected: prints `# Experiment Design Template`

- [ ] **Step 3: Verify all six skeleton sections are present**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for s in "## Goal" "## Hypothesis" "## Requirements" "## Validation" "## Analysis plan" "## Status & links"; do grep -q "$s" skills/design-experiment/references/experiment-design-template.md && echo "found: $s" || echo "MISSING: $s"; done
```
Expected: six `found:` lines, no `MISSING:`.

- [ ] **Step 4: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/design-experiment/references/experiment-design-template.md && git commit -m "feat(design-experiment): add experiment-design template + worked example"
```

---

### Task 3: Create the dataset-design template

**Files:**
- Create: `skills/design-experiment/references/dataset-design-template.md`

**Interfaces:**
- Consumes: referenced by `SKILL.md` (Task 1) at `references/dataset-design-template.md`.
- Produces: the dataset-design section skeleton (Purpose · Requirements · Structure plan · Validation · Consumption · Status & links) — parallel to the experiment skeleton — that Task 5's dataset-lifecycle Design phase points at.

- [ ] **Step 1: Write the template file**

Create `skills/design-experiment/references/dataset-design-template.md` with exactly this content:

```markdown
# Dataset Design Template

Copy this into `dataset-design/<slug>.md` and fill every section. Parallel in
shape to the experiment-design template — same skeleton, dataset-specific
prompts. A section you can't fill is a design gap; close it before building.

---

## Template (copy below this line)

```markdown
# Dataset Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Built | Released -->
**Date:** <YYYY-MM-DD>

## Purpose

What this dataset is *for*, in one sentence. The downstream use that
justifies building it.

## Requirements

- **Source data:** which catalog table(s) / existing dataset(s) members come
  from.
- **Target size & composition:** how many members, class balance, any
  inclusion/exclusion filters.
- **Element types:** which tables contribute members
  (`deriva_ml_list_dataset_element_types`); register missing ones first.
- **Balance constraints:** per-class minimums, stratification column, etc.

## Structure plan

- **Pattern:** standalone / split (train/test/val) / subsample / curated
  subset / manual nesting.
- **Dataset_Type tags (three axes):** Role (Training/Testing/…), Content
  (Labeled/…/domain tags), Origin (Split/Split_Partition/Subsample — set by
  the producing operation). List the tags you intend each output to carry.

## Validation

How you'll verify the dataset is correct *before* relying on it:
- class balance check (counts per class within tolerance),
- no train/test leakage (member RIDs disjoint across partitions),
- bag parity (downloaded bag RIDs == catalog member RIDs),
- expected total member count.

## Consumption

Who uses this downstream: which experiments/configs reference it, and the
version-pinning expectation (always a released label, never dev/"current" in
`configs/datasets.py`).

## Status & links

- **RID + version:** the produced dataset RID and released version.
- **configs/datasets.py:** the `DatasetSpecConfig` entry that pins it.
- **tacit-knowledge.md:** link to journal entries from the build.
```

---

## Worked example

```markdown
# Dataset Design: CIFAR-10 dev subset

**Slug:** cifar10-dev-subset
**Status:** Approved
**Date:** 2026-06-22

## Purpose
A small, class-balanced CIFAR-10 subset for rapid pipeline validation and
small-data runs, so full-scale compute isn't spent debugging plumbing.

## Requirements
- **Source data:** `cifar10_complete` @ `1.0.0` (Image members).
- **Target size & composition:** 500 images, 50 per class, all 10 classes.
- **Element types:** `Image` (already registered).
- **Balance constraints:** exactly 50 per `Diagnosis`/class label; stratify on
  the class column.

## Structure plan
- **Pattern:** subsample (single stratified output, no partitioning).
- **Dataset_Type tags:** Role `Complete`, Content `Labeled` + `CIFAR_10`,
  Origin `Subsample` (auto-applied by `subsample`).

## Validation
- Counts: 50 ± 0 per class, 500 total.
- Leakage: N/A (single output, not a split).
- Bag parity: downloaded bag Image RIDs == `list_dataset_members` Image RIDs.

## Consumption
- Used by the `*_quick` / small-data experiments in `configs/experiments.py`.
- Pinned in `configs/datasets.py` as a released version (e.g. `0.1.0`), never
  a dev label.

## Status & links
- **RID + version:** (filled after the build)
- **configs/datasets.py:** (filled after the build)
- **tacit-knowledge.md:** (filled after the build)
```
```

- [ ] **Step 2: Verify the file exists and is non-empty Markdown**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && test -s skills/design-experiment/references/dataset-design-template.md && head -1 skills/design-experiment/references/dataset-design-template.md
```
Expected: prints `# Dataset Design Template`

- [ ] **Step 3: Verify all six skeleton sections are present**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for s in "## Purpose" "## Requirements" "## Structure plan" "## Validation" "## Consumption" "## Status & links"; do grep -q "$s" skills/design-experiment/references/dataset-design-template.md && echo "found: $s" || echo "MISSING: $s"; done
```
Expected: six `found:` lines, no `MISSING:`.

- [ ] **Step 4: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/design-experiment/references/dataset-design-template.md && git commit -m "feat(design-experiment): add dataset-design template + worked example"
```

---

### Task 4: Rewire experiment-lifecycle Phase 1

**Files:**
- Modify: `skills/experiment-lifecycle/SKILL.md` (Phase 1 block lines ~28–39; routing table line ~129; auto-fires line ~137; Related skills ~139)

**Interfaces:**
- Consumes: the `design-experiment` skill + `experiment-design/` convention (Task 1).
- Produces: nothing downstream (terminal edit).

- [ ] **Step 1: Replace the Phase 1 body**

Find this block (lines ~28–39):

```markdown
### Phase 1 — Identify hypothesis

The phase no other skill owns. Before writing any config, settle:
```
…through…
```markdown
**Deliverable:** the hypothesis written down in `tacit-knowledge.md`. The `capture-tacit-knowledge` skill auto-fires when you make decisions during this phase and will capture them; the lifecycle's job is to make sure you actually *make* the decision before moving on.
```

Replace the heading and the **Deliverable** paragraph (keep the four-question bullet list between them intact) so the block reads:

Change the heading line from:
```markdown
### Phase 1 — Identify hypothesis
```
to:
```markdown
### Phase 1 — Design (identify hypothesis)
```

And replace the `**Deliverable:**` paragraph with:

```markdown
**Deliverable:** an experiment-design document. Hand off to `/deriva-ml:design-experiment` to author `experiment-design/<slug>.md` — the four questions above become its Goal, Validation, and Requirements sections. The design doc is the up-front contract this cycle's config will implement; `tacit-knowledge.md` remains the running journal (`capture-tacit-knowledge` auto-fires for the decisions you make here). The lifecycle's job is to make sure the design doc reaches **Approved** before you move to Phase 2.
```

- [ ] **Step 2: Update the inter-phase gate sentence at the end of Phase 1**

The paragraph after the deliverable (starting "If you can't answer the four questions above, do not advance to phase 2.") stays — it reinforces the gate. No change needed there; it now reads as "the design doc must be complete." Verify it's still present:

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -q "do not advance to phase 2" skills/experiment-lifecycle/SKILL.md && echo "gate sentence intact"
```
Expected: `gate sentence intact`

- [ ] **Step 3: Update the routing-summary table row**

Change line ~129 from:
```markdown
| 1. Identify hypothesis | This skill (no other home) |
```
to:
```markdown
| 1. Design (identify hypothesis) | `/deriva-ml:design-experiment` (authors the design doc) |
```

- [ ] **Step 4: Add design-experiment to the auto-fires line and Related skills**

In the "Auto-fires alongside this lifecycle" line (~137), it currently lists `capture-tacit-knowledge`, `dataset-lifecycle`, `generate-scripts`. Leave it — `design-experiment` is a hand-off, not an alongside-auto-fire. Instead add to **Related skills** (after line ~139), as the first bullet:

```markdown
- **`/deriva-ml:design-experiment`** — Phase 1 hands off here to author the `experiment-design/<slug>.md` contract before any config is written. Returns here for Phase 2.
```

- [ ] **Step 5: Verify cross-references resolve and Phase 1 reads correctly**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -c "design-experiment" skills/experiment-lifecycle/SKILL.md && grep -q "Phase 1 — Design (identify hypothesis)" skills/experiment-lifecycle/SKILL.md && echo "phase1 retitled" && grep -q "experiment-design/<slug>.md" skills/experiment-lifecycle/SKILL.md && echo "doc convention referenced"
```
Expected: a count ≥ 2, then `phase1 retitled`, then `doc convention referenced`.

- [ ] **Step 6: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/experiment-lifecycle/SKILL.md && git commit -m "feat(experiment-lifecycle): Phase 1 hands off to design-experiment for the design doc"
```

---

### Task 5: Add a Design phase to dataset-lifecycle

**Files:**
- Modify: `skills/dataset-lifecycle/SKILL.md` (insert new phase before line 14 "## Phase 1: Assess"; renumber Assess→2, Plan→3, Create→4, Version→5, Use→6; update Related Skills ~267)

**Interfaces:**
- Consumes: the `design-experiment` skill + `dataset-design/` convention (Task 1).
- Produces: nothing downstream (terminal edit).

- [ ] **Step 1: Insert the new Design phase before "## Phase 1: Assess"**

Immediately before the line `## Phase 1: Assess` (line 14), insert:

```markdown
## Phase 1: Design

Before assessing or building, capture what the dataset is *for* and how you'll
know it's correct. Hand off to `/deriva-ml:design-experiment` to author
`dataset-design/<slug>.md` — Purpose, Requirements (source, size, composition,
element types, balance), Structure plan (standalone / split / subsample /
curated, and the three-axis `Dataset_Type` tags), Validation (balance, no
leakage, bag parity, counts), and Consumption (which experiments pin it).

The design doc is the up-front contract the build implements; get it to
**Approved** before creating anything. `tacit-knowledge.md` stays the running
journal (`capture-tacit-knowledge` auto-fires for decisions made here). For a
quick reuse/extend/create triage with no new structure, the design can be a
few lines — but a new split, subsample, or curated subset earns a full doc,
because its validation criteria (leakage, balance) are exactly what gets
skipped otherwise.

```

- [ ] **Step 2: Renumber the existing phase headings**

Apply these exact heading replacements (each is a single unique line):
- `## Phase 1: Assess` → `## Phase 2: Assess`
- `## Phase 2: Plan` → `## Phase 3: Plan`
- `## Phase 3: Create` → `## Phase 4: Create`
- `## Phase 4: Version` → `## Phase 5: Version`
- `## Phase 5: Use` → `## Phase 6: Use`

- [ ] **Step 3: Fix internal cross-references to renamed phases**

Search for in-document references to the old phase numbers and update them. Known references:
- The text "see `/deriva-ml:create-feature` "Integration with Datasets" for the symmetric statement" — no phase number, skip.
- Phase 3 → "Proactively offer to update `src/configs/datasets.py`" is referenced from Phase 5 (now 6) text: `(see "Proactively offer to update \`src/configs/datasets.py\`" in Phase 3)`. Update "Phase 3" → "Phase 4" there.
- "See the `dataset-lifecycle` skill, Phase 4." appears in OTHER skills (model-development-workflow) referring to the Version phase — handle in Task 6's grep sweep, not here.

Run to find any remaining stale intra-doc phase refs:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -nE "in Phase [0-9]|Phase [0-9]\b" skills/dataset-lifecycle/SKILL.md
```
Update any that point at the wrong renumbered phase (the `configs/datasets.py` one in particular: Phase 3 → Phase 4).

- [ ] **Step 4: Add design-experiment to Related Skills**

After `## Related Skills` (~267), add as the first bullet:
```markdown
- **`/deriva-ml:design-experiment`** — Phase 1 hands off here to author the `dataset-design/<slug>.md` contract before assessing or building. The dataset-design template is parallel to the experiment-design one.
```

- [ ] **Step 5: Verify renumbering is clean (no dup/missing phase numbers)**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -E "^## Phase [0-9]:" skills/dataset-lifecycle/SKILL.md
```
Expected exactly, in order:
```
## Phase 1: Design
## Phase 2: Assess
## Phase 3: Plan
## Phase 4: Create
## Phase 5: Version
## Phase 6: Use
```

- [ ] **Step 6: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/dataset-lifecycle/SKILL.md && git commit -m "feat(dataset-lifecycle): add Phase 1 Design handing off to design-experiment"
```

---

### Task 6: Pointer edits in configure-experiment + model-development-workflow, and fix stale phase refs

**Files:**
- Modify: `skills/configure-experiment/SKILL.md` (top of "## Setup Steps", line ~55; Related Skills ~217)
- Modify: `skills/model-development-workflow/SKILL.md` (Phase 7 ~313; any "dataset-lifecycle … Phase 4" ref)

**Interfaces:**
- Consumes: `design-experiment` (Task 1), the renumbered dataset-lifecycle phases (Task 5).
- Produces: nothing downstream.

- [ ] **Step 1: Add the design-doc pointer to configure-experiment Setup Steps**

Immediately after the `## Setup Steps` heading (line ~55) and before the numbered "1. Clone the model template…", insert:

```markdown
> **The config implements an approved experiment-design doc.** Before writing config groups, you should have an `experiment-design/<slug>.md` at **Approved** (see `/deriva-ml:design-experiment`). As you fill the groups below, cross-check that every **Requirement** in that design — the datasets/versions, assets, vocabularies — is satisfied by a config entry. A requirement with no config home is a gap to close before running.

```

- [ ] **Step 2: Add design-experiment to configure-experiment Related Skills**

After `## Related Skills` (~217), add as the first bullet:
```markdown
- **`design-experiment`** — Authors the `experiment-design/<slug>.md` this config implements. Write the design first; the config satisfies its Requirements.
```

- [ ] **Step 3: Add the design-doc note to model-development-workflow Phase 7**

In `## Phase 7: Iterate` (~313), which already routes to `experiment-lifecycle`, add a sentence. Find the Phase 7 body and append this paragraph at its end (before the next `##` heading):

```markdown
The first hypothesis-driven experiment after cycle zero authors an
`experiment-design/<slug>.md` via `/deriva-ml:design-experiment` — the
design-first phase `experiment-lifecycle` opens with. Cycle zero validated the
plumbing; from here every experiment starts with a design doc.
```

- [ ] **Step 4: Fix the stale dataset-lifecycle phase reference in model-development-workflow**

Task 5 renumbered dataset-lifecycle's Version phase from 4 to 5. Find the reference (known to exist near line ~304: "See the `dataset-lifecycle` skill, Phase 4."):

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -n "dataset-lifecycle.*Phase [0-9]\|Phase [0-9].*dataset-lifecycle" skills/model-development-workflow/SKILL.md
```
If it references the Version phase as "Phase 4", change it to "Phase 5". (Verify by context that the reference is about versioning/release, which moved 4→5.)

- [ ] **Step 5: Repo-wide sweep for any other stale dataset-lifecycle phase references**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -rn "dataset-lifecycle" skills/*/SKILL.md skills/*/references/*.md 2>/dev/null | grep -iE "phase [0-9]"
```
For each hit, confirm it points at the correct renumbered phase (Assess 1→2, Plan 2→3, Create 3→4, Version 4→5, Use 5→6) and fix if stale. If no hits, note "no other stale refs".

- [ ] **Step 6: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/configure-experiment/SKILL.md skills/model-development-workflow/SKILL.md && git commit -m "feat(lifecycle): point configure-experiment + model-dev-workflow at design-experiment; fix renumbered phase refs"
```

---

### Task 7: Update CLAUDE.md inventory

**Files:**
- Modify: `CLAUDE.md` (skill count "30 skills" → "31 skills"; add `design-experiment` to the user-command + auto-fire inventory section)

**Interfaces:**
- Consumes: the `design-experiment` skill exists (Task 1).
- Produces: nothing downstream.

- [ ] **Step 1: Bump the skill count**

Replace every occurrence of `30 skills` with `31 skills`:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -n "30 skills" CLAUDE.md
```
For each line found, change `30 skills` → `31 skills`. (There are 3 occurrences per the earlier scan.)

- [ ] **Step 2: List the new skill in the inventory**

In the "User commands (`/deriva-ml:<name>`)" subsection of the Skill Organization section, add `design-experiment` under an appropriate grouping. Find the "Experiments / configs:" line:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -n "Experiments / configs:" CLAUDE.md
```
Change that line from:
```markdown
- Experiments / configs: `configure-experiment`, `write-hydra-config`
```
to:
```markdown
- Experiments / configs: `design-experiment` (also auto-fires — the design-first phase, owns experiment-design/ + dataset-design/), `configure-experiment`, `write-hydra-config`
```

Then, in the "Auto-invoked guides" subsection, add a bullet:
```markdown
- `design-experiment` — auto-fires before configuring an experiment or building a dataset (dual-mode: also slash-typeable). Owns the design-first phase: the standardized design doc that precedes config/construction.
```

- [ ] **Step 3: Verify count consistency**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && actual=$(ls -d skills/*/ | wc -l | tr -d ' ') && echo "actual skills: $actual" && grep -c "31 skills" CLAUDE.md && ! grep -q "30 skills" CLAUDE.md && echo "no stale 30-skills refs"
```
Expected: `actual skills: 31`, a count of 31-skills mentions, then `no stale 30-skills refs`.

- [ ] **Step 4: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add CLAUDE.md && git commit -m "docs(CLAUDE): inventory design-experiment skill (30 -> 31)"
```

---

### Task 8: Whole-feature verification sweep

**Files:**
- No edits (verification only). Fixes go back to whichever task's file is wrong.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: a green final state.

- [ ] **Step 1: Every SKILL.md frontmatter still parses**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for f in skills/design-experiment skills/experiment-lifecycle skills/dataset-lifecycle skills/configure-experiment skills/model-development-workflow; do python3 -c "
import re, pathlib
t = pathlib.Path('$f/SKILL.md').read_text()
m = re.match(r'^---\n(.*?)\n---\n', t, re.DOTALL)
assert m, 'no frontmatter in $f'
assert 'name:' in m.group(1) and 'description:' in m.group(1), 'missing name/description in $f'
print('$f OK')
"; done
```
Expected: five `... OK` lines.

- [ ] **Step 2: Every `/deriva-ml:design-experiment` cross-reference points at a real skill dir**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && test -d skills/design-experiment && grep -rl "design-experiment" skills/*/SKILL.md && echo "all references resolve to skills/design-experiment/"
```
Expected: lists the referencing SKILL.md files, then the confirmation line.

- [ ] **Step 3: No stale `30 skills`; dataset-lifecycle phases sequential**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && ! grep -rq "30 skills" CLAUDE.md && echo "count OK" && grep -E "^## Phase [0-9]:" skills/dataset-lifecycle/SKILL.md | grep -oE "Phase [0-9]" | tr '\n' ' '
```
Expected: `count OK` then `Phase 1 Phase 2 Phase 3 Phase 4 Phase 5 Phase 6 `

- [ ] **Step 4: Templates are copy-paste-valid (balanced code fences)**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for f in skills/design-experiment/references/experiment-design-template.md skills/design-experiment/references/dataset-design-template.md; do n=$(grep -c '```' "$f"); echo "$f: $n fences ($([ $((n % 2)) -eq 0 ] && echo balanced || echo UNBALANCED))"; done
```
Expected: both report an even number of fences = `balanced`.

- [ ] **Step 5: Final commit if any fixes were made (otherwise skip)**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git status --porcelain
```
If anything is uncommitted from fixes during this sweep:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add -A && git commit -m "fix(design-first): verification-sweep corrections"
```

---

## Self-Review (completed during plan authoring)

**Spec coverage:** every spec section maps to a task — new skill (Task 1), two templates (Tasks 2–3), the four wiring edits (Tasks 4–6), CLAUDE.md inventory (Task 7), cross-reference integrity (Task 6 sweep + Task 8). Non-goals (no MCP/script/catalog-entity/enforcement/migration) are respected — no task adds any of those.

**Placeholder scan:** the "(filled after the run/build)" markers inside the *worked examples* are intentional — they model how a real design doc's Status section looks before the run. They are example content, not plan placeholders. No "TBD/TODO/implement later" in the plan steps themselves.

**Type/name consistency:** the skill name `design-experiment`, the directory names `experiment-design/` + `dataset-design/`, and the six-section skeletons are used identically across Tasks 1–8. The dataset phase renumbering (Assess 1→2 … Use 5→6) is applied in Task 5 and verified for downstream refs in Task 6 and Task 8.

**The one flagged ambiguity (dataset phase numbering)** is resolved: the design phase becomes "Phase 1: Design" and the existing five phases shift by one, verified sequential in Task 5 Step 5 and Task 8 Step 3.
