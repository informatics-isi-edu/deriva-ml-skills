# Unifying Lifecycle Framework — Phase B Manifestation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Manifest the unifying lifecycle framework (Specify → Build → Validate; two-layer configuration; one canonical handoff grammar; spec dependency tree) in the existing DerivaML skills — extending `design-experiment` to own all four design-doc types, giving the Feature and Model lifecycles the spec-first + validate-against-goal phases they lack, and applying the handoff grammar across the cross-entity edges.

**Architecture:** Builds directly on the shipped `design-experiment` skill (which already owns `experiment-design/` + `dataset-design/`). Phase B adds two more templates (`feature-design`, `model-design`) and two directory conventions, then reframes the Feature and Model lifecycle skills under the universal arc and wires the canonical handoff grammar onto the gap edges. Experiment and Dataset lifecycles are already conformant and get only light arc-vocabulary framing + a framework-doc pointer. These are Markdown skill files — no executable code; per-task verification = frontmatter parses, the arc/section is present, cross-references resolve to real skill dirs, templates are fence-balanced.

**Tech Stack:** Markdown (SKILL.md + references), YAML frontmatter. No Python, no build step. Verification via `python3` one-liners (frontmatter/fence checks) and `grep` (cross-reference resolution).

## Global Constraints

- **The framework spec is authoritative:** `docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md`. Every task conforms to it. Quote it when in doubt.
- **Four lifecycle entities only:** Experiment, Dataset, Feature, Model. Execution, Workflow, Vocabulary, Asset are NOT nodes — do not give them design docs or arcs.
- **A dataset does NOT depend on a feature.** Feature↔Dataset interactions are a *drift notification* (version-on-write) and an *element-property read* (stratify), NOT produce→consume build handoffs. Do not write "dataset depends on feature."
- **Assets enter via the configuration surface** (model-layer or experiment-layer config), not as a node. Output assets are produced by execution's Build phase. A model's prediction output is simultaneously an asset and feature values.
- **Configuration is two layers:** model-intrinsic (`model_config`) + experiment-compositional (`experiment`/`multiruns`). Feature and Dataset have no config artifact.
- **Design doc = up-front contract; `tacit-knowledge.md` = running journal.** Unchanged by this work; the new design docs cross-link to the journal exactly as `experiment-design`/`dataset-design` do.
- **Canonical handoff grammar:** when A produces something B needs, A offers to register it in B's consumption surface (config entry / dataset version / feature def) AND names the spec linkage (B's design doc records its dependency on A's design doc).
- **Guide-shaped skills auto-fire** (no `disable-model-invocation`); the lifecycle skills are dual-mode. Do not add blocking flags.
- **Cross-reference annotation:** deriva-skills refs as `/deriva:<name>` *(deriva-skills)*; this plugin as `/deriva-ml:<name>`.
- **Release tail (after merge, not a task):** `bump-version` minor + meta-marketplace pin + `deriva-ml--v<version>` tag.

---

### Task 1: Add the `feature-design` template to design-experiment

**Files:**
- Create: `skills/design-experiment/references/feature-design-template.md`

**Interfaces:**
- Consumes: the existing template style in `skills/design-experiment/references/experiment-design-template.md` and `dataset-design-template.md` (Task reads them for the shared skeleton).
- Produces: `references/feature-design-template.md` — referenced by Task 3 (design-experiment SKILL.md update) and Task 5 (create-feature Specify phase).

- [ ] **Step 1: Read the two existing templates for the shared skeleton**

Run: `sed -n '1,40p' skills/design-experiment/references/experiment-design-template.md` and the dataset one. Confirm the shared shape: a "Template (copy below this line)" block + a "Worked example" block, both fenced ```markdown, sections = Goal/Purpose · Requirements · Validation · (entity-specific) · Status & links.

- [ ] **Step 2: Write the feature-design template file**

Create `skills/design-experiment/references/feature-design-template.md` with this content (parallel skeleton, feature-specific prompts):

```markdown
# Feature Design Template

Copy this into `feature-design/<slug>.md` and fill every section. Parallel in
shape to the experiment/dataset templates — same skeleton, feature-specific
prompts. A section you can't fill is a design gap; close it before creating the
feature.

---

## Template (copy below this line)

```markdown
# Feature Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Created | Validated -->
**Date:** <YYYY-MM-DD>

## Purpose

What this feature captures and *why it's needed*, in one sentence. The decision
this feature's values will inform (a label for training, a confidence score for
filtering, ground truth for evaluation).

## Requirements

- **Target table / element:** which table's records the feature attaches to.
- **Feature type:** scalar value, controlled-vocabulary term, or asset; single
  vs multi-column.
- **Vocabulary:** if term-based, the controlled vocabulary + terms it draws from
  (create the vocabulary first if it doesn't exist).
- **Who/what writes the values:** human annotation, a model's predictions, a
  derived computation — and the provenance (which Execution).

## Validation

How you'll confirm the feature serves its stated Purpose:
- value coverage (every intended record got a value, or the expected subset),
- value sanity (terms are from the vocabulary; scores in range),
- provenance present (each value links to a producing Execution),
- the downstream consumer can actually read it (e.g. a stratified split or a
  training loop finds the values where it expects them).

## Upstream designs

The design docs this feature builds on, if any (usually none — features are
near the bottom of the dependency tree). If a model's predictions populate this
feature, name the `model-design` that produces them.

## Status & links

- **Feature name + target table:** the created feature.
- **Vocabulary:** the controlled vocabulary RID/name, if term-based.
- **tacit-knowledge.md:** link to journal entries from creating/populating it.
```

---

## Worked example

```markdown
# Feature Design: image quality label

**Slug:** image-quality-label
**Status:** Approved
**Date:** 2026-06-22

## Purpose
A per-image quality label (good/blurry/occluded) so low-quality images can be
filtered out of training sets and flagged for re-acquisition.

## Requirements
- **Target table / element:** Image.
- **Feature type:** controlled-vocabulary term, single-column.
- **Vocabulary:** new `Image_Quality` vocabulary, terms: good, blurry, occluded.
- **Who/what writes the values:** human annotation pass, recorded under an
  annotation Execution.

## Validation
- Coverage: every Image in the curated set has a quality label.
- Sanity: all values are one of the three vocabulary terms.
- Provenance: each value links to the annotation Execution.
- Consumer: a stratified split on `Image_Quality` finds the values.

## Upstream designs
None (human-annotated, not model-produced).

## Status & links
- **Feature name + target table:** (filled after creation)
- **Vocabulary:** (filled after creation)
- **tacit-knowledge.md:** (filled after creation)
```
```

- [ ] **Step 3: Verify the file exists, sections present, fences balanced**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && test -s skills/design-experiment/references/feature-design-template.md && for s in "## Purpose" "## Requirements" "## Validation" "## Upstream designs" "## Status & links"; do grep -q "$s" skills/design-experiment/references/feature-design-template.md && echo "found: $s" || echo "MISSING: $s"; done && n=$(grep -c '```' skills/design-experiment/references/feature-design-template.md); echo "fences: $n ($([ $((n % 2)) -eq 0 ] && echo balanced || echo UNBALANCED))"
```
Expected: five `found:` lines, no `MISSING:`, `fences: 4 (balanced)`.

- [ ] **Step 4: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/design-experiment/references/feature-design-template.md && git commit -m "feat(design-experiment): add feature-design template"
```

---

### Task 2: Add the `model-design` template to design-experiment

**Files:**
- Create: `skills/design-experiment/references/model-design-template.md`

**Interfaces:**
- Consumes: same shared skeleton as Task 1.
- Produces: `references/model-design-template.md` — referenced by Task 3 and Task 6 (model lifecycle Specify phase). The model-design template is the one whose Requirements section feeds the model-layer configuration (per the framework's generable-from-requirements aspiration).

- [ ] **Step 1: Write the model-design template file**

Create `skills/design-experiment/references/model-design-template.md` with this content:

```markdown
# Model Design Template

Copy this into `model-design/<slug>.md` and fill every section. Parallel in
shape to the other design templates. The Requirements section is the source the
model-layer configuration (hyperparameters, architecture, the `model_config`
group) is derived from — write it so a config could be scaffolded from it.

---

## Template (copy below this line)

```markdown
# Model Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Built | Validated -->
**Date:** <YYYY-MM-DD>

## Goal

What this model is for, in one sentence — the prediction task it performs and
the decision its outputs inform.

## Requirements

The source the model-layer config is derived from:
- **Architecture:** model family / structure (e.g. 2-layer CNN, ResNet50).
- **Hyperparameters:** the knobs and their intended defaults (learning rate,
  batch size, epochs, regularization) — these become the `model_config` group.
- **Input features:** which features the model trains on (the labels/annotations
  it consumes — name the `feature-design`s). The model's prediction outputs, if
  they become features, name the feature they populate.
- **Input assets:** any pretrained checkpoint / starting weights the model is
  built with (enters via the model-layer config — `configs/assets.py`).

## Validation

How you'll confirm the model meets its Goal (beyond "the code runs"):
- the target metric and the threshold that counts as success,
- the dataset/split it's validated on,
- sanity checks (loss converges, no NaN, predictions in range).

## Upstream designs

- **Feature designs** this model consumes (labels it trains on; features its
  predictions populate).
- Any prior `model-design` it extends (a checkpoint lineage).

## Status & links

- **Model file + config groups:** the authored model fn and its `model_config`.
- **Workflow:** the registered Workflow.
- **tacit-knowledge.md:** link to journal entries from building it.
```

---

## Worked example

```markdown
# Model Design: 2-layer CNN for CIFAR-10

**Slug:** cifar10-2layer-cnn
**Status:** Approved
**Date:** 2026-06-22

## Goal
A small 2-layer CNN that classifies CIFAR-10 images into the 10 classes, as the
baseline architecture for the project's experiments.

## Requirements
- **Architecture:** 2 conv layers (32→64 channels) + 2 FC layers.
- **Hyperparameters:** lr=0.001, batch=128, epochs=50, dropout=0.0 (baseline) —
  the `model_config` group.
- **Input features:** the `class-label` feature on Image (the training target).
- **Input assets:** none (trained from scratch).

## Validation
- Metric: top-1 test accuracy; success ≥ 0.60 on the small labeled split.
- Validated on `cifar10_small_labeled_split` test partition.
- Sanity: loss converges, no NaN, softmax outputs sum to 1.

## Upstream designs
- Feature design: `class-label` (the training target).

## Status & links
- **Model file + config groups:** (filled after authoring)
- **Workflow:** (filled after registration)
- **tacit-knowledge.md:** (filled after build)
```
```

- [ ] **Step 2: Verify the file exists, sections present, fences balanced**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && test -s skills/design-experiment/references/model-design-template.md && for s in "## Goal" "## Requirements" "## Validation" "## Upstream designs" "## Status & links"; do grep -q "$s" skills/design-experiment/references/model-design-template.md && echo "found: $s" || echo "MISSING: $s"; done && n=$(grep -c '```' skills/design-experiment/references/model-design-template.md); echo "fences: $n ($([ $((n % 2)) -eq 0 ] && echo balanced || echo UNBALANCED))"
```
Expected: five `found:` lines, no `MISSING:`, `fences: 4 (balanced)`.

- [ ] **Step 3: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/design-experiment/references/model-design-template.md && git commit -m "feat(design-experiment): add model-design template"
```

---

### Task 3: Extend the design-experiment skill to own all four design-doc types

**Files:**
- Modify: `skills/design-experiment/SKILL.md`

**Interfaces:**
- Consumes: the four templates in `references/` (experiment + dataset exist; feature + model from Tasks 1–2).
- Produces: the `feature-design/` and `dataset-design/` + `experiment-design/` + `model-design/` directory conventions documented; the four-way "When to use which template" table that Tasks 5–6 route into.

- [ ] **Step 1: Read the current SKILL.md "When to use which template" table and discipline**

Run: `sed -n '35,75p' skills/design-experiment/SKILL.md`. The current table has two rows (experiment, dataset). The discipline section references the two templates.

- [ ] **Step 2: Expand the "When to use which template" table to four rows**

Replace the current two-row table:
```markdown
| You are about to… | Template | Directory |
|---|---|---|
| Configure and run an experiment | experiment-design | `experiment-design/<slug>.md` |
| Create, split, subsample, or curate a dataset | dataset-design | `dataset-design/<slug>.md` |
```
with the four-row version:
```markdown
| You are about to… | Template | Directory |
|---|---|---|
| Configure and run an experiment | experiment-design | `experiment-design/<slug>.md` |
| Create, split, subsample, or curate a dataset | dataset-design | `dataset-design/<slug>.md` |
| Create a feature (label, score, annotation) | feature-design | `feature-design/<slug>.md` |
| Author or substantially change a model | model-design | `model-design/<slug>.md` |
```

- [ ] **Step 3: Update the references list to name all four templates**

Find the `references/` list (currently names experiment-design-template.md and dataset-design-template.md) and add the two new ones:
```markdown
- `references/experiment-design-template.md`
- `references/dataset-design-template.md`
- `references/feature-design-template.md`
- `references/model-design-template.md`
```

- [ ] **Step 4: Add the spec-dependency-tree note to the discipline section**

After the discipline's numbered list, add this paragraph:
```markdown
**Upstream designs (the spec dependency tree).** Each design doc names the
design docs it builds on, mirroring the entity dependency graph: an
experiment-design names the model-design + dataset-design it uses; a
model-design names the feature-designs it consumes. A dataset-design does NOT
name a feature as a dependency (a dataset doesn't depend on features) — where a
split reads a feature its *elements* carry, note that element feature as a
precondition, not an upstream design. This makes genuine build dependencies
traceable at the spec layer. See the framework spec
`docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md`.
```

- [ ] **Step 4b: Backfill "Upstream designs" into the two existing templates**

The `feature-design` and `model-design` templates (Tasks 1–2) have an "##
Upstream designs" section, but the already-shipped `experiment-design` and
`dataset-design` templates do not — make all four consistent. In
`skills/design-experiment/references/experiment-design-template.md`, inside the
template block (before "## Status & links"), add:
```markdown
## Upstream designs

The design docs this experiment builds on: the `model-design` of the model it
runs and the `dataset-design` of the dataset it consumes. Naming them makes the
dependency traceable at the spec layer.
```
In `skills/design-experiment/references/dataset-design-template.md`, inside the
template block (before "## Status & links"), add:
```markdown
## Upstream designs

A dataset does not depend on a feature, so it names no upstream design. Where a
split reads a feature its *elements* carry, note that element feature here as a
precondition on the members — a reference to a data property, not a build
dependency.
```
Re-verify both still fence-balance (each gains no new fence; the section is
inside the existing template fence).

- [ ] **Step 5: Update the description frontmatter to cover all four entities**

The current description mentions experiment + dataset design. Add feature + model triggers. Find the `Triggers on:` list in the description and add: `'design a feature', 'design a model', 'feature-design', 'model-design'`. Keep the description otherwise intact (it already auto-fires; do not add blocking flags).

- [ ] **Step 6: Verify the skill parses and references resolve**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && python3 -c "
import re, pathlib
m = re.match(r'^---\n(.*?)\n---\n', pathlib.Path('skills/design-experiment/SKILL.md').read_text(), re.DOTALL)
assert m and 'name: design-experiment' in m.group(1) and 'disable-model-invocation' not in m.group(1)
print('frontmatter OK')
" && for t in experiment dataset feature model; do test -f "skills/design-experiment/references/$t-design-template.md" && echo "template exists: $t" || echo "MISSING template: $t"; done && grep -c "feature-design/<slug>.md\|model-design/<slug>.md" skills/design-experiment/SKILL.md
```
Expected: `frontmatter OK`, four `template exists:` lines, a count ≥ 2.

- [ ] **Step 7: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/design-experiment/SKILL.md && git commit -m "feat(design-experiment): own all four design-doc types + spec dependency tree"
```

---

### Task 4: Light arc-vocabulary framing for experiment-lifecycle and dataset-lifecycle

**Files:**
- Modify: `skills/experiment-lifecycle/SKILL.md`
- Modify: `skills/dataset-lifecycle/SKILL.md`

**Interfaces:**
- Consumes: the framework spec (the arc vocabulary).
- Produces: a framework-doc pointer + arc framing in both already-conformant lifecycles. No phase renumbering (these already have Specify via design-experiment and Validate).

- [ ] **Step 1: Add a framework pointer to experiment-lifecycle**

Read `sed -n '1,12p' skills/experiment-lifecycle/SKILL.md`. After the opening paragraph (before "## The seven phases"), add:
```markdown
> **This lifecycle realizes the universal Specify → Build → Validate arc** (see
> `docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md`): Phase 1
> (design) is Specify; Phases 2–5 (configure → identify assets → run) are Build;
> Phases 6–7 (evaluate → repeat) are Validate. Configuration here is the
> *experiment layer* — composing a model + dataset + parameter values over the
> model-layer config.
```

- [ ] **Step 2: Add a framework pointer to dataset-lifecycle**

Read `sed -n '1,18p' skills/dataset-lifecycle/SKILL.md`. After the opening description (before "## Phase 1: Design"), add:
```markdown
> **This lifecycle realizes the universal Specify → Build → Validate arc** (see
> `docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md`): Phase 1
> (Design) is Specify; Phases 2–4 (assess → plan → create) are Build; Phase 5
> (version) + the validation checks are Validate. A dataset has no configuration
> artifact — its shape lives in its design. A dataset does not depend on
> features; its elements may carry them.
```

- [ ] **Step 3: Verify both parse and the pointers resolve**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for n in experiment-lifecycle dataset-lifecycle; do python3 -c "
import re, pathlib
m = re.match(r'^---\n(.*?)\n---\n', pathlib.Path('skills/$n/SKILL.md').read_text(), re.DOTALL)
assert m and 'name:' in m.group(1)
print('$n frontmatter OK')
"; grep -q "Specify → Build → Validate" skills/$n/SKILL.md && echo "  $n: arc pointer present" || echo "  $n: MISSING arc pointer"; done && test -f docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md && echo "framework doc exists"
```
Expected: two `frontmatter OK`, two `arc pointer present`, `framework doc exists`.

- [ ] **Step 4: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/experiment-lifecycle/SKILL.md skills/dataset-lifecycle/SKILL.md && git commit -m "feat(lifecycle): frame experiment + dataset lifecycles under the universal arc"
```

---

### Task 5: Give the Feature lifecycle a Specify phase + Validate phase + handoff grammar

**Files:**
- Modify: `skills/create-feature/SKILL.md`

**Interfaces:**
- Consumes: the `feature-design` template (Task 1), the design-experiment four-way table (Task 3), the framework spec.
- Produces: a Specify-first Feature lifecycle with a Validate phase, plus the drift-notification handoff to dataset-lifecycle.

- [ ] **Step 1: Add a "Phase 0: Specify" before the current Phase 1: Assess**

Read `sed -n '1,52p' skills/create-feature/SKILL.md`. Insert immediately before `## Phase 1: Assess`:
```markdown
## Phase 0: Specify

Before assessing or creating, capture what the feature is for and how you'll
know it serves that purpose. Hand off to `/deriva-ml:design-experiment` to
author `feature-design/<slug>.md` — Purpose (the decision the values inform),
Requirements (target table, type, vocabulary, who writes the values),
Validation (coverage, value sanity, provenance, the consumer can read it), and
Upstream designs. Get it to **Approved** before creating anything;
`tacit-knowledge.md` stays the running journal. A trivial single-term label can
be a few lines, but a feature a model or split will depend on earns a full
design — its Validation criteria are exactly what gets skipped otherwise.

This is the Specify phase of the universal Specify → Build → Validate arc (see
`docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md`). Phases 1–4
below are Build; Phase 5 (now reframed) is Validate.
```

- [ ] **Step 2: Add a Validate phase after Phase 4 (Add Feature Values)**

Read `sed -n '238,267p' skills/create-feature/SKILL.md` (the current Phase 5: Query and the Integration section). The current "Phase 5: Query and Explore" is a Build/consume activity, not validation. Insert a NEW phase before it:
```markdown
## Phase 5: Validate against the design

Confirm the feature serves the Purpose in its `feature-design` doc — not just
that values were written:
- **Coverage** — every intended record got a value (or the expected subset did).
- **Value sanity** — terms are from the declared vocabulary; numeric scores in
  range.
- **Provenance** — each value links to its producing Execution
  (`deriva_ml_list_feature_values(..., execution_rids=[...])`).
- **Consumer can read it** — the downstream use named in the design (a
  stratified split, a training loop) actually finds the values where it expects.

Record the outcome in the design doc's Status & links (Status → Validated) and
in `tacit-knowledge.md`. Then proceed to query/explore (next section) for
ongoing use.
```
Then renumber the existing `## Phase 5: Query and Explore Feature Values` to `## Phase 6: Query and Explore Feature Values`.

- [ ] **Step 3: Add the drift-notification handoff to the Integration with Datasets section**

Read the `## Integration with Datasets` section. It already documents the `mark_dev` rule. Add the offer-and-route language (the framework's drift-notification grammar):
```markdown
**Drift notification (handoff grammar).** Writing feature values to records that
are members of a *released* Dataset drifts that dataset's content — the same
members now carry different data. This is not a build dependency (a dataset
doesn't depend on the feature); it's a drift the dataset must record. When you
populate values on members of a released dataset, **proactively offer** to flip
it to a dev version (`dataset.mark_dev(description)`) and route to
`/deriva-ml:dataset-lifecycle` Phase 5 for the release once the drift period is
done. Don't wait to be asked.
```

- [ ] **Step 4: Verify parse, phases sequential, handoff present**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && python3 -c "
import re, pathlib
m = re.match(r'^---\n(.*?)\n---\n', pathlib.Path('skills/create-feature/SKILL.md').read_text(), re.DOTALL)
assert m and 'name: create-feature' in m.group(1)
print('frontmatter OK')
" && grep -E "^## Phase [0-9]" skills/create-feature/SKILL.md && grep -q "feature-design/<slug>.md" skills/create-feature/SKILL.md && echo "specify handoff present" && grep -q "Drift notification" skills/create-feature/SKILL.md && echo "drift handoff present"
```
Expected: `frontmatter OK`; phases read `Phase 0: Specify`, `Phase 1: Assess`, `Phase 2: Design`, `Phase 3...`, `Phase 4...`, `Phase 5: Validate`, `Phase 6: Query`; `specify handoff present`; `drift handoff present`.

- [ ] **Step 5: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/create-feature/SKILL.md && git commit -m "feat(create-feature): add Specify + Validate phases and the dataset drift handoff"
```

---

### Task 6: Give the Model lifecycle a Specify phase, strengthen Validate, add feature handoff

**Files:**
- Modify: `skills/model-development-workflow/SKILL.md`
- Modify: `skills/new-model/SKILL.md`

**Interfaces:**
- Consumes: the `model-design` template (Task 2), the design-experiment four-way table (Task 3), the framework spec.
- Produces: a Specify-first Model lifecycle; the model→feature (predictions) handoff; the arc framing on the model skills.

- [ ] **Step 1: Add a "Phase 0: Specify" to model-development-workflow before Phase 1: Schema Design**

Read `sed -n '1,51p' skills/model-development-workflow/SKILL.md`. Insert before `## Phase 1: Schema Design`:
```markdown
## Phase 0: Specify

Before designing the schema or writing any model code, capture what the model is
for. Hand off to `/deriva-ml:design-experiment` to author `model-design/<slug>.md`
— Goal (the prediction task), Requirements (architecture, hyperparameters, input
features, input assets), Validation (the target metric + success threshold), and
Upstream designs (the feature-designs the model consumes). The Requirements
section is the source the model-layer configuration is derived from.

This is the Specify phase of the universal Specify → Build → Validate arc (see
`docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md`). The
three-tier development pattern (Phases 1–6) is Build; Phase 7 plus the
validate-against-the-design check is Validate. Configuration here is the *model
layer* (hyperparameters, architecture); the experiment layer that composes this
model with a dataset lives in `/deriva-ml:experiment-lifecycle`.
```

- [ ] **Step 2: Strengthen Phase 7 (Iterate) toward validate-against-the-design**

Read `sed -n '312,330p' skills/model-development-workflow/SKILL.md`. The current Phase 7 is iteration. Add a validation paragraph at its start:
```markdown
**Validate against the model-design first.** Before iterating, check the run's
results against the Validation criteria in the `model-design` doc — did it hit
the target metric and threshold? This is the Validate phase of the arc: success
is measured against the design's stated criteria, not just "the pipeline ran."
Record the verdict in the design doc (Status → Validated) and `tacit-knowledge.md`.
```

- [ ] **Step 3: Add the model→feature (predictions) handoff to Phase 1 of model-development-workflow**

In `## Phase 1: Schema Design`, where it asks "What features attach annotations to records?", add the handoff:
```markdown
**Predictions as features (handoff grammar).** If the model emits predictions
that should be stored as feature values (predicted labels, confidence scores),
that feature must be defined first. Hand off to `/deriva-ml:create-feature` to
author its `feature-design` and create it — the model-design's "Upstream
designs" names that feature. A model's prediction output is simultaneously an
asset (the prediction file) and feature values (on the records).
```

- [ ] **Step 4: Add a framework pointer + Specify reference to new-model**

Read `sed -n '1,22p' skills/new-model/SKILL.md`. After the opening, add:
```markdown
> **Author from an approved model-design.** Before writing the model file, you
> should have a `model-design/<slug>.md` at Approved (see
> `/deriva-ml:design-experiment`). Steps 2–4 here are the model-layer
> configuration; cross-check every Requirement in the design — architecture,
> hyperparameters, input features, input assets — is satisfied by a config
> entry. This skill is the Build phase of the model lifecycle per the framework
> (`docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md`).
```

- [ ] **Step 5: Verify both parse, phases present, handoffs present**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for n in model-development-workflow new-model; do python3 -c "
import re, pathlib
m = re.match(r'^---\n(.*?)\n---\n', pathlib.Path('skills/$n/SKILL.md').read_text(), re.DOTALL)
assert m and 'name:' in m.group(1)
print('$n frontmatter OK')
"; done && grep -q "## Phase 0: Specify" skills/model-development-workflow/SKILL.md && echo "model specify phase present" && grep -q "model-design/<slug>.md" skills/model-development-workflow/SKILL.md && echo "model-design handoff present" && grep -q "Predictions as features" skills/model-development-workflow/SKILL.md && echo "prediction->feature handoff present" && grep -q "model-design/<slug>.md" skills/new-model/SKILL.md && echo "new-model design pointer present"
```
Expected: two `frontmatter OK`, then the four presence confirmations.

- [ ] **Step 6: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/model-development-workflow/SKILL.md skills/new-model/SKILL.md && git commit -m "feat(model): add Specify phase, validate-against-design, and prediction->feature handoff"
```

---

### Task 7: Update CLAUDE.md and create the design-dir conventions in the model template

**Files:**
- Modify: `CLAUDE.md`
- (Model template `feature-design/` + `model-design/` dirs are a SEPARATE follow-up in the deriva-ml-model-template repo, NOT this repo — note only.)

**Interfaces:**
- Consumes: the four-design-doc reality from Tasks 1–6.
- Produces: accurate CLAUDE.md describing design-experiment's four-template scope.

- [ ] **Step 1: Update the design-experiment inventory line in CLAUDE.md**

Find the line listing `design-experiment` (currently says "owns experiment-design/ + dataset-design/"). Update to:
```markdown
- Experiments / configs: `design-experiment` (also auto-fires — the design-first phase, owns experiment-design/ + dataset-design/ + feature-design/ + model-design/), `configure-experiment` (also auto-fires — the lifecycle Phase 2 config seam), `write-hydra-config` (also auto-fires — when editing config files / wiring RIDs)
```

- [ ] **Step 2: Add a framework reference to CLAUDE.md Architecture section**

After the "Skill Organization" intro paragraph, add:
```markdown
The four lifecycle skills (`experiment-lifecycle`, `dataset-lifecycle`,
`create-feature`, `model-development-workflow`) realize a common **Specify →
Build → Validate** arc with one canonical handoff grammar — see
`docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md`.
`design-experiment` owns the Specify phase for all four (one design-doc template
per entity).
```

- [ ] **Step 2b: Note the model-template follow-up**

This repo's CLAUDE.md should note (in the cross-project section or a comment) that the `deriva-ml-model-template` repo needs `feature-design/` and `model-design/` directories added (mirroring the `experiment-design/`/`dataset-design/` dirs added in template PR #62), as a separate follow-up. Add one line under the model-template reference if such a section exists; otherwise skip (the follow-up is tracked here in the plan).

- [ ] **Step 3: Verify CLAUDE.md mentions all four design-doc types**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -c "feature-design/\|model-design/" CLAUDE.md && grep -q "Specify → Build → Validate" CLAUDE.md && echo "framework referenced in CLAUDE.md"
```
Expected: a count ≥ 1, then `framework referenced in CLAUDE.md`.

- [ ] **Step 4: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add CLAUDE.md && git commit -m "docs(CLAUDE): design-experiment owns 4 design-doc types; reference the unifying framework"
```

---

### Task 8: Whole-feature verification sweep

**Files:**
- No edits (verification only). Fixes go back to the owning task.

**Interfaces:**
- Consumes: all prior tasks.

- [ ] **Step 1: All touched SKILL.md frontmatters parse**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for n in design-experiment experiment-lifecycle dataset-lifecycle create-feature model-development-workflow new-model; do python3 -c "
import re, pathlib
m = re.match(r'^---\n(.*?)\n---\n', pathlib.Path('skills/$n/SKILL.md').read_text(), re.DOTALL)
assert m, 'no frontmatter $n'
assert 'name:' in m.group(1) and 'description:' in m.group(1)
print('$n OK')
"; done
```
Expected: six `... OK` lines.

- [ ] **Step 2: All four design templates exist and are fence-balanced**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for t in experiment dataset feature model; do f="skills/design-experiment/references/$t-design-template.md"; n=$(grep -c '```' "$f"); echo "$t: $([ -s "$f" ] && echo exists || echo MISSING), fences $n ($([ $((n % 2)) -eq 0 ] && echo ok || echo UNBALANCED))"; done
```
Expected: four lines, each `exists, fences 4 (ok)`.

- [ ] **Step 3: The arc + handoff vocabulary is present across the four lifecycles**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for n in experiment-lifecycle dataset-lifecycle create-feature model-development-workflow; do grep -q "Specify → Build → Validate" skills/$n/SKILL.md && echo "$n: arc ✓" || echo "$n: arc MISSING"; done
```
Expected: four `arc ✓`.

- [ ] **Step 4: No "dataset depends on feature" overstatement anywhere**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -rniE "dataset.{0,25}(depends on|built from|relies on).{0,15}feature" skills/ && echo "CHECK the above — should be none, or only explicit negations" || echo "✓ no dataset-depends-on-feature overstatement"
```
Expected: `✓ no dataset-depends-on-feature overstatement` (or only explicit "not"/"doesn't" negations if any match).

- [ ] **Step 5: Cross-references resolve to real skill dirs**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && for ref in design-experiment dataset-lifecycle create-feature experiment-lifecycle; do test -d "skills/$ref" && echo "resolves: $ref" || echo "BROKEN ref: $ref"; done
```
Expected: four `resolves:` lines.

- [ ] **Step 6: Final commit if the sweep made fixes (else skip)**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git status --porcelain && (git diff --cached --quiet && git diff --quiet || git commit -am "fix(framework-phase-b): verification-sweep corrections")
```

---

## Self-Review (completed during plan authoring)

**Spec coverage:** every Phase B manifestation item maps to a task — design-experiment owns 4 templates (Tasks 1–3); experiment+dataset arc framing (Task 4); feature Specify+Validate+drift handoff (Task 5); model Specify+Validate+prediction handoff (Task 6); CLAUDE.md + framework reference (Task 7); cross-ref integrity (Task 8). The handoff grammar's four gap edges: model→feature (Task 6 Step 3), feature→experiment metrics (covered by feature Validate naming the consumer, Task 5), feature⇒dataset drift (Task 5 Step 3), feature←dataset stratify element-read (the dataset-lifecycle Specify already routes to create-feature when a stratify feature is missing — light; reinforced by Task 4's dataset arc pointer noting elements-may-carry-features). The spec-dependency-tree: Task 3 Step 4 + the "Upstream designs" section in every template (Tasks 1–2, and experiment/dataset templates already shipped — note: those two existing templates do NOT yet have an "Upstream designs" section; see gap below).

**Gap found during self-review — FIXED inline:** the existing `experiment-design-template.md` and `dataset-design-template.md` (shipped earlier) do NOT have an "Upstream designs" section, but Task 3 Step 4 documents the dependency-tree convention referencing it. Added coverage: Task 3 gains responsibility to also add an "Upstream designs" section to the two existing templates so all four are consistent. (Implementer: in Task 3, after Step 4, also add an "## Upstream designs" section to experiment-design-template.md — naming model-design + dataset-design — and to dataset-design-template.md — noting element-feature preconditions, NOT feature dependencies.)

**Placeholder scan:** the `(filled after …)` markers in the template worked examples are intentional example content (modeling a pre-build design doc), not plan placeholders — consistent with the shipped experiment/dataset templates. No TBD/TODO in plan steps.

**Type/name consistency:** directory names `feature-design/` + `model-design/` and the section skeletons are used identically across Tasks 1–8. The arc string "Specify → Build → Validate" is verified verbatim in Task 8 Step 3. Phase numbering in create-feature (new Phase 0 + renumber Query 5→6) is applied in Task 5 and verified in Task 5 Step 4.
