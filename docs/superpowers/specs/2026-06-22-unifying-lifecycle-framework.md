# Unifying Lifecycle Framework for DerivaML Skills

**Date:** 2026-06-22
**Status:** Approved (framework); Phase B (manifestation) implemented — see
`docs/superpowers/plans/2026-06-22-unifying-framework-phase-b.md` and the skill
edits on this branch
**Author:** Carl Kesselman + Claude

## Purpose

The DerivaML plugin has four "lifecycle" skills — for **Experiment**,
**Dataset**, **Feature**, and **Model**. They grew independently and diverged
in shape. A recent change (the `design-experiment` skill) added a spec-first
"design" phase to the *experiment* and *dataset* lifecycles, but the *feature*
and *model* lifecycles still start at implementation with no goal-capture and
no validation-against-goal.

This document identifies the **common underlying framework** all four share,
names it once so the skills can speak a shared vocabulary, and defines how that
framework should **manifest as concrete modifications to the existing skills**
(Phase B). The unifying premise: a user works with the LLM to develop a
**specification** (goals / hypothesis / objectives, requirements, validation,
and any entity-specific sections), then hands off to **implementation**, with
**configuration** derived from requirements, **execution**, and **validation**
against the spec — and the four entities **hand off to each other** because they
depend on each other (experiments rely on datasets, models, and
configurations; models rely on features). A dataset does **not** depend on a
feature: a dataset is a collection of *elements*, and those elements may have
features associated with them — so the dataset/feature relationship is
containment-of-feature-bearing-elements, not a build dependency.

This framework is grounded in an assessment of the four lifecycles as they
exist today (see "Assessment evidence" below); it describes a shape that is
*already partially built*, not a speculative imposition.

## The universal arc: Specify → Build → Validate

Every DerivaML entity moves through three universal phases. The arc is a
**shared vocabulary**, not a rigid template — the *Build* phase's internals
differ per entity, and that divergence is expected and correct.

| Phase | What it is | Universal? |
|---|---|---|
| **Specify** | A standardized design document capturing goals/hypothesis/objectives, requirements, validation criteria, and entity-specific sections. The user develops it collaboratively with the LLM *before* building. | Yes — all four |
| **Build** | Entity-specific internals: implement, and where applicable configure + execute. The four diverge in mechanics here but share the role. | Yes (internals vary) |
| **Validate** | Check the built artifact against the spec's stated criteria. | Yes — all four |

### Why three phases, not five

An earlier candidate arc was Specify → Implement → Configure → Execute →
Validate. It was collapsed to three because **Configure and Execute are not
universal peer phases** — they are *Build* internals that only some entities
have (see "Configuration" below). Forcing all four through a five-phase
template would create empty "Configure" phases on Feature and Dataset. The
three-phase spine fits all four without unnatural structure; the finer
internal structure lives inside each skill's *Build* phase.

### Per-entity manifestation of the arc

| Entity | Specify | Build (internals) | Validate |
|---|---|---|---|
| **Experiment** | hypothesis design doc *(exists)* | compose experiment-layer config → run execution | vs hypothesis *(exists)* |
| **Dataset** | dataset design doc *(exists)* | create/split/subsample members (build script) | balance / no-leakage / bag-parity / counts *(exists)* |
| **Feature** | feature design doc *(to add)* | create feature def + vocab → populate values | vs the feature's stated purpose *(to add)* |
| **Model** | model design doc *(to add)* | author model fn → model-layer config → train | strengthen beyond correctness-only *(to add)* |

The Experiment and Dataset rows are already conformant (the `design-experiment`
work delivered their Specify and Validate). The Feature and Model rows are the
gap Phase B closes.

## Configuration: two layers, not a universal phase

Configuration is **not** a phase every entity fills. It is a shared concern
with **two layers**, located along the entity dependency graph:

- **Model layer (intrinsic config):** hyperparameters, architecture, the
  model's own hydra-zen config groups. *Owned by the model lifecycle.* Answers
  "what is this model and how is it parameterized?"
- **Experiment layer (compositional config):** which model + which dataset +
  which parameter values to run, and the sweep/multirun composition. *Owned by
  the experiment lifecycle*, composing **over** the model layer. Answers "which
  configured run(s) do I execute to test the hypothesis?"

**Feature and Dataset have no configuration artifact** — their shape lives
entirely in their spec (a feature's type/cardinality, a dataset's
size/stratify-column/filters are spec content, not a separate config file).

This maps onto the existing hydra-zen structure, which is evidence the
framework describes reality rather than imposing it: the `model_config` group
is the model layer; the `experiment` / `multiruns` groups are the experiment
layer composing model + dataset + workflow together.

### Assets: where they enter the framework

An **asset** (model weights, a prediction CSV, a plot, a reference file) is not
a fifth lifecycle entity — it has no Specify→Build→Validate arc and no design
doc. It is a file with a RID that plays **two distinct roles**:

- **Asset as input — enters through configuration.** An input asset is consumed
  by being *referenced in a config*, at whichever of the two layers owns it:
  - *Model layer* — an intrinsic asset the model is built with (a pretrained
    checkpoint / starting weights), referenced from the model's config
    (`configs/assets.py`, wired into the model config group). Part of "what
    this model is."
  - *Experiment layer* — an asset a *particular run* consumes (a specific
    checkpoint to fine-tune from, a reference file), referenced from the
    experiment's compositional config.
  So **configuration is the asset-consumption surface** — config carries not
  just hyperparameters and dataset RIDs but also the asset RIDs bound to a
  model or a run. This is exactly the canonical handoff grammar: "produce a RID
  → offer to wire it into `configs/assets.py`" *is* an asset handoff, with the
  config file as the consumer's surface. It also reinforces the
  generable-from-requirements aspiration: a model-design requirement naming a
  pretrained checkpoint generates that asset config entry.

- **Asset as output — produced by execution (the Build phase).** A run emits
  assets (trained weights, predictions, plots, evaluation summaries) as named
  outputs. These become *configurable inputs to the next* model or experiment
  (the execution→experiment "wire output RIDs into `configs/assets.py`"
  handoff). **One overlap to keep in mind:** a model's *prediction* outputs are
  simultaneously **assets** (the prediction file) and **feature values** (the
  predicted labels written to the records) — the same execution output is
  reachable both as an asset RID and as feature values on the elements.

So assets appear in the framework on the produce→consume edges as the payload
that flows, with configuration as the surface they enter through — never as a
node that runs the arc.

**External file inputs (`LocalFile`) are the one asset-shaped input without a
RID.** A source CSV or labels file on disk is declared as a `LocalFile` /
`LocalFileConfig` input (see `/deriva-ml:work-with-assets`): the framework
registers it as a referenced `File` row (path + MD5) and links it to the
execution at run time — the bytes are not uploaded to Hatrac, so there is **no
catalog asset RID to "wire into `configs/assets.py`" ahead of time.** The
configuration still names it (a `LocalFileConfig` entry in the `assets` group),
so configuration remains the consumption surface; the difference is the
payload is a *declared path*, not a pre-existing RID. The produce→consume
grammar's "register in the consumer's config surface" step holds; only its
"produce a RID first" precondition does not apply to external inputs.

### Aspiration: config generable from requirements

The framework's directional goal is that **both config layers be generable
from the spec's Requirements section** — the experiment's requirements (which
dataset, which model, which hyperparameters to vary) generate the
experiment-layer composition; the model's requirements generate its config
groups. Today the realized link is **traceability** (the Configure step
cross-checks that every requirement in the spec is satisfied by a config
entry — `configure-experiment` already does this post-`design-experiment`).
**Generation is the direction, not the current state.** The Requirements
section of each design-doc template should be structured with this aspiration
in mind, so the derivation can tighten over time.

## The canonical handoff grammar

The entities depend on each other. The dependency graph (A → B means "A
depends on / is built from B"):

```
Experiment ── depends on ──▶ Model ── depends on ──▶ Feature
     │
     └── depends on ──▶ Dataset ──contains──▶ Elements ──may have──▶ Features
```

- An **experiment** is built from a model, a dataset, and configurations.
- A **model** depends on its **input** features — the labels/annotations it
  trains on. Those are upstream of the model. A model's **output** (prediction)
  features are a different relationship: they are *produced by* the model, so
  they are **downstream** of it, not dependencies. The dependency edge is
  Model → input-Feature only; the prediction feature points *up* to its
  producing model. This input/output split is what keeps the graph acyclic — a
  prediction feature and its model never both name each other as upstream. (See
  "The spec dependency tree" for how the design docs encode this.)
- A **dataset** is **not** built from features. A dataset is a collection of
  *elements* (members from element-type tables); those elements may have
  features associated with them. The dataset/feature relationship is
  containment-of-feature-bearing-elements, not a build dependency — which is
  why the Feature↔Dataset interactions below are **drift notifications** and
  **element-property reads**, not produce→consume handoffs.

### One grammar for every edge

Every cross-entity handoff follows a single pattern:

> When entity **A** produces something entity **B** needs, **A offers to
> register it in B's consumption surface** — a config entry, a dataset version
> bump, or a feature definition — **and names the spec linkage**: B's design
> doc records the dependency. When A is itself a design-doc'd entity (model,
> dataset, feature), B names A's design doc upstream. When A is **not** a
> design-doc'd node — an **Execution** producing output assets, the most common
> case — there is no A-side doc to name; the linkage closes entirely on B's
> side: B's design doc **Status & links** records the produced execution RID and
> the output-asset RIDs it consumes. The closure requirement is the same (the
> dependency is written down at the spec layer); only the place it's written is
> B's Status & links, not an A→B upstream pointer.

The existing, well-crystallized handoffs are the template:

- **Dataset → Experiment:** "produce a RID + version → proactively offer to
  wire it into `src/configs/datasets.py`" (B's consumption surface = the config
  file). Already implemented in `dataset-lifecycle`.
- **Execution → Experiment:** "produce output asset RIDs → offer to wire into
  `src/configs/assets.py`." Already implemented in `execution-lifecycle`.

Phase B closes the gaps. The two true **produce→consume handoffs** below adopt
the grammar directly; the two Feature↔Dataset interactions are *not* build
handoffs (a dataset doesn't depend on features) and get the appropriate
flavor — a **drift notification** and an **element-property read**:

| Gap edge | Kind | Today | Phase B closes it by |
|---|---|---|---|
| **Model → Feature** (predictions) | produce→consume handoff | not routed | `model`/`new-model` Specify routes to `create-feature` for the prediction-feature definition |
| **Feature → Experiment** (metric features) | produce→consume handoff | inline query, no setup gate | the metric feature is named as a Specify-time prerequisite for evaluation |
| **Feature ⇒ Dataset** (version-on-write) | drift notification (a feature value written to a member *element* drifts its containing dataset) | a rule the developer must remember (`mark_dev` after writing feature values) | `create-feature` *notifies* and offers the dataset dev-flip/release at the write-values moment, routing to `dataset-lifecycle` |
| **Feature ← Dataset** (stratify reads element feature) | element-property read (a split reads a feature carried by the elements, not a dataset dependency) | implicit (`stratify_by_column` references a feature column on the elements) | `dataset-lifecycle` Specify checks the *elements* carry the needed feature and routes to `create-feature` if missing |

## The spec dependency tree

Because handoffs name the spec linkage, the design docs form a **tree mirroring
the entity dependency graph**:

- an `experiment-design/<slug>.md` names the `model-design` + `dataset-design`
  it builds on;
- a `model-design/<slug>.md` names the **input** `feature-design`s it consumes
  (the labels it trains on) as upstream. It does **not** name its own **output**
  (prediction) features as upstream — those are downstream of the model. Each
  prediction `feature-design` instead names *this* model-design as its producer.
  Inputs point up to features; outputs point up to the model; nothing points
  back — the tree stays acyclic;
- a `dataset-design/<slug>.md` does **not** name a feature-design as a
  dependency (a dataset doesn't depend on features). Where a split reads a
  feature carried by its elements, the dataset-design notes that **element
  feature** as a precondition on its members — a reference to a property of the
  data, not an upstream design it's built from.

This makes the genuine build dependencies traceable at the **spec layer**, not
just the config/RID layer. A reader of an experiment design can walk down to the
model design and the features it consumes, and across to the dataset design.
(The design docs remain repo artifacts under their respective `*-design/`
directories;
`tacit-knowledge.md` remains the running journal — see the design-experiment
spec for that contract, which this framework extends rather than changes.)

## Manifestation in the skills (Phase B scope)

The framework is not a doc that sits beside the skills — it **manifests as
modifications to them**. Phase B (its own plan, after this doc is approved):

1. **All four lifecycle skills** adopt the **Specify → Build → Validate**
   vocabulary in their phase structure (relabel/reframe; Experiment and Dataset
   are mostly conformant, Feature and Model are restructured).
2. **`design-experiment` extended** to own all four design-doc types — add
   `feature-design` and `model-design` templates alongside the existing
   `experiment-design` and `dataset-design`; add the corresponding directory
   conventions (`feature-design/`, `model-design/`).
3. **Feature and Model lifecycles gain a Specify phase** (author the design
   doc first) **and a Validate phase** (check against the spec — for a feature,
   "does it serve its stated purpose?"; for a model, beyond correctness toward
   the model-design's success criteria).
4. **The canonical handoff grammar applied to every edge**, closing the four
   gap edges in the table above with the offer-and-name-the-linkage pattern.
5. **The spec dependency tree** wired in: each design-doc template gains an
   "Upstream designs" section naming the design docs it builds on.
6. **This framework doc referenced** from each lifecycle skill (a short pointer:
   "this skill is the «Build» phase of the «X» lifecycle per the unifying
   framework").

## What is deliberately NOT a lifecycle node

The framework has exactly **four lifecycle entities** — Experiment, Dataset,
Feature, Model — each with a goal-driven Specify→Build→Validate arc and a design
doc. Several other DerivaML concepts are intentionally **not** nodes; they are
Build-phase internals or supporting structures, because they have no
goal/hypothesis to specify and nothing to validate against beyond correctness:

- **Execution** — the *Execute* step inside Build. A run is the mechanism by
  which an experiment's or model's Build happens; it has no design doc of its
  own.
- **Workflow** — provenance machinery (the catalog record tying an execution to
  a git commit). Consumed by execution; not a goal-driven artifact.
- **Vocabulary** — a supporting structure a Feature's Build creates (the terms
  a feature's values draw from). It is reused and evolves, but it is specified
  *within* a feature's design, not on its own arc.
- **Asset** — a file with a RID that flows on the produce→consume edges and
  enters via the configuration surface (see "Assets" above). Not a node.

Treating any of these as a fifth entity with its own design doc would force the
unnatural structure this framework avoids — the same error as claiming a dataset
depends on a feature. If a future concept genuinely has goals, requirements, and
validation criteria of its own, *that* is the test for promoting it to a node.

## Non-goals

- **Not** a rigid five-phase template forced onto every entity (the three-phase
  spine + entity-specific Build internals is deliberate).
- **Not** auto-generation of configs from requirements *yet* — that is the
  stated aspiration; the realized mechanism is traceability.
- **Not** a change to the `design-experiment` ↔ `tacit-knowledge.md` contract
  (design doc = up-front contract, journal = running record) — this framework
  extends the design-doc surface to two more entity types; the contract is
  unchanged.
- **Not** a catalog-side artifact — design docs and the framework are repo
  concerns, like `configs/` and `tacit-knowledge.md`.
- **No MCP tool, no script** — the framework is conceptual + skill-structural.

## Assessment evidence (what grounds this framework)

A phase-by-phase assessment of the four lifecycles (2026-06-22) established:

- **A common arc already exists** — Experiment and Dataset express
  Specify→Build→Validate fully (post-`design-experiment`); Feature
  (Assess→Design→Create→Add→Query) and Model
  (Schema→DevData→Validate-features→DryRun→SmallRun→ProdRun→Iterate) start at
  implementation with no spec-first gate and weak/no validate-against-goal.
- **The handoff pattern is ~80% consistent** — "produce a RID → offer to wire
  into a config" + "route to a named specialist" are crystallized for
  dataset→experiment and execution→experiment; the gaps are specific and
  nameable — two true produce→consume handoffs (model→feature predictions,
  feature→experiment metrics) plus two Feature↔Dataset interactions that are
  *not* build dependencies (the version-on-write drift notification and the
  stratify element-feature read).
- **Configuration is genuinely a model+experiment concern** — Feature and
  Dataset have no config artifact; the model layer (`model_config`) and
  experiment layer (`experiment`/`multiruns`) already exist in the hydra-zen
  structure.

The framework names what the assessment found and prescribes completing it
uniformly.
