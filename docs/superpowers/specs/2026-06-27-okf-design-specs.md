# Design: OKF-conformant design specifications in `docs/design/`

**Date:** 2026-06-27
**Status:** Draft (awaiting user review)
**Skill touched:** `design-experiment` (owner), `validate-project-setup` (validation row)

## Problem

DerivaML projects capture up-front specifications as design docs at
`docs/design/{experiment,dataset,feature,model}/<slug>.md`, authored by the
`design-experiment` skill (the Specify phase of the Specify → Build → Validate
arc). Today these are structured *prose* — a `# <Kind> Design: <title>` heading
followed by a bold-text header block:

```markdown
# Dataset Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Built | Validated | Released -->
**Date:** <YYYY-MM-DD>

## Purpose
...
```

The header fields (`Slug`, `Status`, `Date`) are semantically structured but not
machine-parseable, so the design corpus is not self-describing to tooling: an
external agent or knowledge-catalog tool can't reliably discover *what* each
file is, its lifecycle state, or navigate the corpus as a unit.

## Goal

Make the four design-doc types conform to the **Open Knowledge Format (OKF)**
([spec](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md))
— Markdown + YAML frontmatter — so the `docs/design/` tree is a self-describing
**OKF bundle** consumable by external OKF tooling, while keeping all
human-readable prose intact.

Two sub-goals, both confirmed in brainstorming:

1. **Conformance** — the design docs satisfy the OKF document contract.
2. **External interop** — an OKF consumer (the Google knowledge-catalog tooling
   or any OKF-aware agent) can read and navigate the corpus without
   DerivaML-specific knowledge.

Explicitly **out of scope** (ruled out in brainstorming):

- **No `resource`/RID linkage in frontmatter** (OKF goal "make specs
  catalog-linked" was declined). See the `resource` decision below.
- **No validator script** (`check_okf.py`). Conformance is by convention +
  the `validate-project-setup` checklist, not an automated gate.
- **No `log.md`** (OKF's reserved update-history file). `tacit-knowledge.md`
  already is the project's update journal; a second `log.md` would split the
  record.

## How OKF maps onto DerivaML design docs

OKF is deliberately lightweight: Markdown files with a small YAML frontmatter
contract, organized as a directory-tree "bundle". The relevant facts (from the
spec):

- Frontmatter: **`type` is the only required field**; `title`, `description`,
  `resource`, `tags`, `timestamp` are *recommended*. Extra keys are permitted;
  consumers MUST tolerate unknown `type` values.
- `type` — "a short string identifying the kind of concept… for routing,
  filtering, and presentation." Values are not centrally registered.
- `resource` — "a URI that uniquely identifies the underlying asset the concept
  describes. **Absent for concepts that describe abstract ideas rather than
  physical resources.**"
- A **bundle** is "a directory tree of markdown files"; OKF defines **no
  manifest file**. Two filenames are reserved: **`index.md`** (directory
  listing) and `log.md` (update history).
- Conventional body headings (SHOULD-use-when-applicable): `# Schema`,
  `# Examples`, `# Citations`.

### Frontmatter contract (the four templates)

Each template's prose header is replaced by a YAML frontmatter block. Worked
mapping for the dataset template:

```yaml
---
type: Dataset Design          # REQUIRED (OKF). One of: Dataset Design |
                              #   Experiment Design | Feature Design | Model Design
title: CIFAR-10 dev subset    # ← the existing "# Dataset Design: <title>" line
description: >                 # recommended; the one-line Purpose
  500-image stratified subset of cifar10_complete for rapid dev iteration.
tags: [dataset, subsample, cifar-10]   # recommended; entity kind + structure + domain
timestamp: 2026-06-26          # ← the existing **Date:** field (ISO date)
status: Draft                  # DerivaML EXTENSION key. Draft|Approved|Built|Validated|Released
slug: cifar10-dev-subset       # DerivaML EXTENSION key (kebab id)
---

# Dataset Design: CIFAR-10 dev subset

## Purpose
...
```

Notes:

- The `# <Kind> Design: <title>` H1 **stays** (human-facing, and OKF bodies are
  ordinary Markdown). `title`/`timestamp` in frontmatter duplicate what the H1
  and old `**Date:**` carried — that duplication is intentional: the H1 is for
  humans, the frontmatter for tools.
- `status` and `slug` are **DerivaML extension keys**, not OKF vocabulary. OKF
  permits extra frontmatter keys, so this is spec-legal and preserves the
  existing lifecycle (`Status` already drives the Specify→…→Released arc and is
  checked by other skills). They are kept as first-class keys rather than folded
  into `tags` because they are queried structurally (a tool asking "which
  designs are still Draft?").
- The experiment/feature/model templates use the same block; only `type` and the
  example values differ. Their existing `Status` line omits `Released` — preserve
  that per-type in the frontmatter too: the `status` key's allowed-values comment
  reads `Draft|Approved|Built|Validated|Released` only on the **dataset** template
  and `Draft|Approved|Built|Validated` on the other three, matching today's
  prose-header comments exactly.

### `resource`: always absent (the load-bearing decision)

A DerivaML design doc is a **specification of intent** — it describes an entity
the project *plans* to build, authored before that entity exists. Per the OKF
spec, `resource` is "absent for concepts that describe abstract ideas rather
than physical resources." A spec is an abstract idea, not a physical resource —
**even after the entity is built**, because the doc continues to describe the
*intent*, not the artifact.

Therefore `resource` is **omitted entirely** from all four templates, at every
lifecycle status. Artifact linkage (the produced RID + version) stays where it
already lives: the prose **"Status & links"** section and `tacit-knowledge.md`.
This formalizes a clean conceptual boundary the project already has:

| Side | Artifact | Nature |
|---|---|---|
| **Spec (before)** | `docs/design/<entity>/<slug>.md` | abstract — intent, requirements, success criteria |
| **Journal (during/after)** | `tacit-knowledge.md` | concrete — what happened, decisions, RIDs |
| **Catalog (the thing)** | the entity at its RID | concrete — the physical resource |

OKF's abstract-vs-`resource` distinction maps exactly onto the spec-vs-artifact
line. Each template will carry a short comment recording *why* `resource` is
omitted, so a future editor doesn't "helpfully" add it.

### Body headings: light-touch OKF alignment

The body stays as-is, with one gentle alignment where it's a clean fit:

- The existing **"Worked example"** section → renamed to **`## Examples`** (OKF's
  conventional heading; the content is already concrete usage examples).
- Where a template lists external references / upstream sources, those map to
  OKF's **`## Citations`** if and only if such a section already exists — do not
  invent one.
- All domain sections (Purpose/Goal, Requirements, Structure plan, Validation,
  Consumption, Upstream designs, Status & links) **stay unchanged** — OKF does
  not prescribe body structure, so these are fine as domain-specific sections.

OKF's `# Schema` heading is **not** adopted — it's for an asset's columns/fields,
which isn't what these specs describe.

### Bundle: an `index.md` at `docs/design/`

`docs/design/` is already a directory tree of conformant docs, so it is
implicitly an OKF bundle. To make it *navigable* by an OKF consumer (the "+
manifest" the user asked for — realized as OKF's reserved `index.md`, since OKF
has no separate manifest file), add **`docs/design/index.md`**: a directory
listing naming the four entity subdirectories and what each holds, plus (as
designs are authored) a line per design doc. The `design-experiment` skill
maintains it — adding/updating a line whenever it authors a design.

The `index.md` itself carries minimal OKF frontmatter (`type: Index`,
`title`, `description`).

### Explicit OKF declaration (required)

Conformance must be **stated, not just implied**. The corpus declares that it
follows OKF in three discoverable places, in decreasing prominence:

1. **`docs/design/index.md`** (primary) — the bundle root carries a one-line
   statement in its body, e.g.: *"These design documents follow the
   [Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
   — Markdown + YAML frontmatter. Each `<entity>/<slug>.md` is an OKF concept
   document (`type: <Kind> Design`)."* This is the first thing an OKF consumer
   (or human) lands on when opening the bundle.
2. **`design-experiment` SKILL.md** — a sentence in the skill body stating that
   the design docs it authors are OKF-conformant and linking the spec, so the
   authoring agent knows the contract it's upholding and why.
3. **Each template** — a short comment near the frontmatter naming OKF and
   linking the spec, so a doc read in isolation (without the index) is
   self-identifying.

The link target is the OKF spec URL above. This requirement is what makes the
corpus *self-describing about its own format*, which is the point of adopting a
named open format rather than an ad-hoc convention.

## Files changed

| File | Change |
|---|---|
| `skills/design-experiment/references/dataset-design-template.md` | Replace prose header with OKF frontmatter (incl. `resource`-omitted comment) in both the template and worked example; rename "Worked example"→`## Examples`. |
| `skills/design-experiment/references/experiment-design-template.md` | Same, `type: Experiment Design`. |
| `skills/design-experiment/references/feature-design-template.md` | Same, `type: Feature Design`. |
| `skills/design-experiment/references/model-design-template.md` | Same, `type: Model Design`. |
| `skills/design-experiment/SKILL.md` | Document the OKF frontmatter contract, the four `type` values, the `resource`-is-abstract rule, the body-heading alignment, the `docs/design/index.md` upkeep step (authoring a design adds/updates its index line), and an explicit "these design docs follow OKF" statement linking the spec. |
| `skills/validate-project-setup/SKILL.md` | The `docs/design/` checklist row gains an "OKF frontmatter present (`type` at minimum)" validation point. Keep "not yet used is normal on a new project". |
| `docs/design/index.md` | **Not created by this change** — it's authored per-project by `design-experiment` on first design. The template/skill documents its shape; the plugin repo doesn't ship a project's `docs/design/`. |

Note the last row: the plugin **ships skills**, not a user's `docs/design/`
tree. So this change updates *templates and skill instructions*; the actual
frontmatter and `index.md` materialize in each user project when
`design-experiment` runs. The CIFAR example repo's existing design docs are a
separate (downstream) update, not part of this plugin change.

## Cross-references to keep consistent

`design-experiment` is referenced by the lifecycle skills (dataset/experiment/
feature/model) and `validate-project-setup`. The change is additive (frontmatter
+ an index convention), so existing cross-references to "the design doc" remain
valid; no skill needs its routing changed. Grep for skills that quote the design
doc's *header shape* (`**Status:**`, `**Slug:**`) and update any that show the
old prose-header form to the frontmatter form.

## Verification

- All four templates parse as valid YAML frontmatter + Markdown.
- `type` present on every template (required-field conformance).
- `resource` absent on every template; the omission-rationale comment present.
- The explicit "follows OKF" declaration (with spec link) present in all three
  places: `docs/design/index.md` body, `design-experiment` SKILL.md, and each
  template.
- `design-experiment` SKILL.md documents the contract and the `index.md` step;
  `description` frontmatter unchanged (no trigger change needed).
- No dangling cross-references introduced (grep for old header-shape quotes).
- `validate-project-setup` checklist updated, "absent is normal early" preserved.

## Risks / open points

- **Frontmatter duplication** (`title`/`timestamp` vs the H1/old date) is
  accepted, not a defect — humans read the H1, tools read frontmatter.
- **OKF is young.** The spec may evolve; the contract adopted here is the small
  stable core (`type` + recommended fields + `index.md`), which is the least
  likely to churn.
- **`status` as an extension key** could in principle collide with a future OKF
  `status` field. Low risk; if OKF adds one, the semantics (lifecycle state)
  likely align. Revisit if OKF formalizes `status`.
