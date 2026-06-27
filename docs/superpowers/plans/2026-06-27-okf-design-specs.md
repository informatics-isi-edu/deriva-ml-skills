# OKF-Conformant Design Specs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the four `design-experiment` design-doc templates conform to the Open Knowledge Format (Markdown + YAML frontmatter), with an explicit OKF declaration and an `index.md` bundle convention, so a DerivaML project's `docs/design/` tree is a self-describing OKF bundle.

**Architecture:** Edit the four bundled templates in `skills/design-experiment/references/` to open with an OKF YAML frontmatter block (replacing the prose `**Slug:**/**Status:**/**Date:**` header), keep all prose body sections, and rename "Worked example"→`## Examples`. Update `skills/design-experiment/SKILL.md` to document the contract + the `docs/design/index.md` upkeep step + an explicit "these docs follow OKF" statement. Update `skills/validate-project-setup/SKILL.md`'s `docs/design/` checklist row. The plugin ships *templates and skill instructions only* — the actual frontmatter and `index.md` materialize per project when `design-experiment` runs.

**Tech Stack:** Markdown + YAML frontmatter (Claude Code SKILL.md plugin format). No build step; no Python runtime. "Tests" are conformance checks: YAML frontmatter parses, required `type` present, declaration present, no dangling cross-references.

## Global Constraints

- **OKF frontmatter contract:** `type` is the ONLY required field. Recommended: `title`, `description`, `tags`, `timestamp`. DerivaML extension keys: `status`, `slug`. Extra keys are spec-legal.
- **`resource` field: OMITTED on every template, at every status.** A design doc is an abstract specification, not a physical resource. Each template carries a comment recording *why* it's omitted, so a future editor doesn't add it.
- **`type` values (exact):** `Dataset Design`, `Experiment Design`, `Feature Design`, `Model Design`. The index uses `type: Index`.
- **`status` enum is per-type:** dataset template comment reads `Draft|Approved|Built|Validated|Released`; the other three read `Draft|Approved|Built|Validated` (no `Released`) — matching today's prose-header comments exactly.
- **OKF spec URL (use verbatim in every declaration + comment):** `https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md`
- **Explicit OKF declaration required in three places:** `docs/design/index.md` body, `design-experiment` SKILL.md, and each template (a comment near the frontmatter).
- **Body sections stay unchanged** except: "Worked example" → `## Examples`. Do NOT adopt OKF's `# Schema`. Only rename a section to `## Citations` if such a section already exists (none do — so no `## Citations` rename).
- **Frontmatter `name`/`description` of the SKILL.md files must stay byte-identical** (no trigger change). Only the SKILL.md *body* changes.
- **No validator script, no `log.md`.** (Out of scope per spec.)
- Spec reference: `docs/superpowers/specs/2026-06-27-okf-design-specs.md`.

---

### Task 1: OKF frontmatter on the dataset template

**Files:**
- Modify: `skills/design-experiment/references/dataset-design-template.md`

**Interfaces:**
- Produces: the canonical frontmatter block shape that Tasks 2–4 mirror (only `type`, example values, and the `status` enum differ per template). The block, for reference by later tasks:
  ```yaml
  ---
  type: <Kind> Design
  title: <one-line title>
  description: >
    <one-line purpose>
  tags: [<entity-kind>, <structure>, <domain>]
  timestamp: <YYYY-MM-DD>
  status: Draft   # <enum>
  slug: <kebab-case-slug>
  # OKF: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
  # `resource` intentionally omitted — a design doc is an abstract specification,
  #   not a physical resource. Artifact linkage lives in tacit-knowledge.md +
  #   the "Status & links" section below. Do not add `resource`.
  ---
  ```

- [ ] **Step 1: Read the current template** to capture the exact prose header and the "Worked example" section.

Run: `sed -n '1,40p' skills/design-experiment/references/dataset-design-template.md`
Expected: see the `# Dataset Design Template` wrapper, the `## Template (copy below this line)` marker, then the `# Dataset Design: <one-line title>` + `**Slug:** / **Status:** Draft <!-- Draft | Approved | Built | Validated | Released --> / **Date:**` prose header.

- [ ] **Step 2: Replace the prose header in the TEMPLATE block** with the OKF frontmatter. The template's copy-below section changes from:

```markdown
# Dataset Design: <one-line title>

**Slug:** <kebab-case-slug>
**Status:** Draft   <!-- Draft | Approved | Built | Validated | Released -->
**Date:** <YYYY-MM-DD>

## Purpose
```

to:

```markdown
---
type: Dataset Design
title: <one-line title>
description: >
  <one-line purpose>
tags: [dataset, <structure>, <domain>]
timestamp: <YYYY-MM-DD>
status: Draft   # Draft | Approved | Built | Validated | Released
slug: <kebab-case-slug>
# This document follows the Open Knowledge Format (OKF):
#   https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
# `resource` is intentionally omitted — a design doc is an abstract specification,
#   not a physical resource (even after the dataset is built). Artifact linkage
#   lives in tacit-knowledge.md + the "Status & links" section below.
---

# Dataset Design: <one-line title>

## Purpose
```

(Keep the H1 `# Dataset Design: <one-line title>` — it's the human-facing title; the frontmatter `title` duplicates it for tools, intentionally.)

- [ ] **Step 3: Replace the prose header in the WORKED EXAMPLE block** with concrete frontmatter, mirroring the existing example values (CIFAR-10 dev subset, slug `cifar10-dev-subset`, Approved, date `2026-06-22`):

```markdown
---
type: Dataset Design
title: CIFAR-10 dev subset
description: >
  500-image stratified subset of cifar10_complete for rapid dev iteration.
tags: [dataset, subsample, cifar-10]
timestamp: 2026-06-22
status: Approved   # Draft | Approved | Built | Validated | Released
slug: cifar10-dev-subset
# This document follows the Open Knowledge Format (OKF):
#   https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
# `resource` intentionally omitted — abstract specification, not a physical resource.
---

# Dataset Design: CIFAR-10 dev subset

## Purpose
```

- [ ] **Step 4: Rename "Worked example" heading to `## Examples`** in this file (the section that introduces the worked example). Leave its content unchanged.

Run: `grep -n "Worked example\|## Examples" skills/design-experiment/references/dataset-design-template.md`
Expected: `## Examples` present; no remaining "Worked example".

- [ ] **Step 5: Verify the frontmatter parses as YAML and `type` is present.**

Run: `awk '/^---$/{c++; next} c==1' skills/design-experiment/references/dataset-design-template.md | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d.get('type')=='Dataset Design', d; assert 'resource' not in d; print('OK', d['type'], d['status'])"`
Expected: `OK Dataset Design Draft` (parses, `type` correct, no `resource`).

- [ ] **Step 6: Commit**

```bash
git add skills/design-experiment/references/dataset-design-template.md
git commit -m "feat(design-experiment): OKF frontmatter on dataset-design template"
```

---

### Task 2: OKF frontmatter on the experiment template

**Files:**
- Modify: `skills/design-experiment/references/experiment-design-template.md`

**Interfaces:**
- Consumes: the frontmatter block shape from Task 1.
- Note: this template's `status` enum is `Draft | Approved | Built | Validated` (NO `Released`), and its first body section is `## Goal` (not `## Purpose`).

- [ ] **Step 1: Read the current template header + the worked-example header.**

Run: `grep -n "^**Slug:**\|^**Status:**\|^**Date:**\|Worked example\|# Experiment Design:" skills/design-experiment/references/experiment-design-template.md`
Expected: the prose header lines + the example + a "Worked example" heading.

- [ ] **Step 2: Replace the prose header in the TEMPLATE block** with:

```markdown
---
type: Experiment Design
title: <one-line title>
description: >
  <one-line goal>
tags: [experiment, <approach>, <domain>]
timestamp: <YYYY-MM-DD>
status: Draft   # Draft | Approved | Built | Validated
slug: <kebab-case-slug>
# This document follows the Open Knowledge Format (OKF):
#   https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
# `resource` is intentionally omitted — a design doc is an abstract specification,
#   not a physical resource. Artifact linkage lives in tacit-knowledge.md +
#   the "Status & links" section below.
---

# Experiment Design: <one-line title>

## Goal
```

- [ ] **Step 3: Replace the prose header in the WORKED EXAMPLE block** with concrete frontmatter that mirrors that file's existing example values (read them first with `sed -n '/## Worked example/,/## Goal/p'`, then fill `title`/`slug`/`timestamp`/`status`/`tags`/`description` to match). Use `type: Experiment Design` and the `Draft|Approved|Built|Validated` enum comment.

- [ ] **Step 4: Rename "Worked example" → `## Examples`.** Content unchanged.

- [ ] **Step 5: Verify YAML + `type`.**

Run: `awk '/^---$/{c++; next} c==1' skills/design-experiment/references/experiment-design-template.md | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Experiment Design'; assert 'resource' not in d; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add skills/design-experiment/references/experiment-design-template.md
git commit -m "feat(design-experiment): OKF frontmatter on experiment-design template"
```

---

### Task 3: OKF frontmatter on the feature template

**Files:**
- Modify: `skills/design-experiment/references/feature-design-template.md`

**Interfaces:**
- Consumes: the frontmatter block shape from Task 1.
- Note: `status` enum `Draft | Approved | Built | Validated` (NO `Released`); first body section is `## Purpose`.

- [ ] **Step 1: Read the current header + worked-example values.**

Run: `sed -n '1,45p' skills/design-experiment/references/feature-design-template.md`

- [ ] **Step 2: Replace the TEMPLATE prose header** with:

```markdown
---
type: Feature Design
title: <one-line title>
description: >
  <one-line purpose>
tags: [feature, <kind>, <domain>]
timestamp: <YYYY-MM-DD>
status: Draft   # Draft | Approved | Built | Validated
slug: <kebab-case-slug>
# This document follows the Open Knowledge Format (OKF):
#   https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
# `resource` is intentionally omitted — a design doc is an abstract specification,
#   not a physical resource. Artifact linkage lives in tacit-knowledge.md +
#   the "Status & links" section below.
---

# Feature Design: <one-line title>

## Purpose
```

- [ ] **Step 3: Replace the WORKED EXAMPLE prose header** with concrete frontmatter mirroring that file's existing example (it's the "image quality label" example — read it first, fill values to match; `type: Feature Design`).

- [ ] **Step 4: Rename "Worked example" → `## Examples`.**

- [ ] **Step 5: Verify YAML + `type`.**

Run: `awk '/^---$/{c++; next} c==1' skills/design-experiment/references/feature-design-template.md | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Feature Design'; assert 'resource' not in d; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add skills/design-experiment/references/feature-design-template.md
git commit -m "feat(design-experiment): OKF frontmatter on feature-design template"
```

---

### Task 4: OKF frontmatter on the model template

**Files:**
- Modify: `skills/design-experiment/references/model-design-template.md`

**Interfaces:**
- Consumes: the frontmatter block shape from Task 1.
- Note: `status` enum `Draft | Approved | Built | Validated` (NO `Released`); first body section is `## Goal`.

- [ ] **Step 1: Read the current header + worked-example values.**

Run: `sed -n '1,45p' skills/design-experiment/references/model-design-template.md`

- [ ] **Step 2: Replace the TEMPLATE prose header** with:

```markdown
---
type: Model Design
title: <one-line title>
description: >
  <one-line goal>
tags: [model, <architecture>, <domain>]
timestamp: <YYYY-MM-DD>
status: Draft   # Draft | Approved | Built | Validated
slug: <kebab-case-slug>
# This document follows the Open Knowledge Format (OKF):
#   https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
# `resource` is intentionally omitted — a design doc is an abstract specification,
#   not a physical resource. Artifact linkage lives in tacit-knowledge.md +
#   the "Status & links" section below.
---

# Model Design: <one-line title>

## Goal
```

- [ ] **Step 3: Replace the WORKED EXAMPLE prose header** with concrete frontmatter mirroring that file's existing example (read it first, fill values to match; `type: Model Design`).

- [ ] **Step 4: Rename "Worked example" → `## Examples`.**

- [ ] **Step 5: Verify YAML + `type`.**

Run: `awk '/^---$/{c++; next} c==1' skills/design-experiment/references/model-design-template.md | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Model Design'; assert 'resource' not in d; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add skills/design-experiment/references/model-design-template.md
git commit -m "feat(design-experiment): OKF frontmatter on model-design template"
```

---

### Task 5: Document the OKF contract + index upkeep + declaration in `design-experiment` SKILL.md

**Files:**
- Modify: `skills/design-experiment/SKILL.md`

**Interfaces:**
- Consumes: the frontmatter block shape (Task 1), the four `type` values, the OKF spec URL (Global Constraints).
- Produces: the canonical `docs/design/index.md` shape that Task 7 documents the *content* of; this task documents the upkeep *step* and the index frontmatter.

- [ ] **Step 1: Read the SKILL.md to find where the design-doc location/format is described** (the section that tells the authoring agent where docs go and what they contain).

Run: `grep -nE "^## |^### |docs/design|template|frontmatter|Status" skills/design-experiment/SKILL.md`
Expected: a section describing the design-doc location/template usage — the insertion point.

- [ ] **Step 2: Add an "Open Knowledge Format (OKF)" subsection** to the SKILL.md body stating the contract. Content to add (adapt heading level to fit the file):

```markdown
## Design docs follow the Open Knowledge Format (OKF)

The design documents this skill authors conform to the
[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
— Markdown with YAML frontmatter — so `docs/design/` is a self-describing OKF
bundle. When authoring or updating a design doc:

- Open the file with the OKF frontmatter block from the template: `type`
  (required — one of `Dataset Design` / `Experiment Design` / `Feature Design`
  / `Model Design`), plus `title`, `description`, `tags`, `timestamp`, and the
  DerivaML extension keys `status` and `slug`.
- **Never add a `resource` field.** A design doc is an abstract specification,
  not a physical resource — even after the entity is built. The produced RID +
  version belong in the prose "Status & links" section and `tacit-knowledge.md`,
  not in frontmatter.
- The body stays human-readable Markdown; the worked example uses the `##
  Examples` heading (OKF convention).
```

- [ ] **Step 3: Add the `docs/design/index.md` upkeep step.** Append to the same subsection:

```markdown
**Maintain `docs/design/index.md`.** The bundle root is an OKF `index.md`
(directory listing). When you author a new design doc, add or update its line
in `docs/design/index.md` under the right entity subsection. If `index.md`
doesn't exist yet, create it from the shape in
`references/index-template.md`. It opens with `type: Index` frontmatter and a
one-line statement that the corpus follows OKF (with the spec link).
```

- [ ] **Step 4: Verify the SKILL.md frontmatter (name/description) is unchanged.**

Run: `git diff skills/design-experiment/SKILL.md | grep -E "^[-+](name:|description:)" | grep -vE "^[-+][-+]" | wc -l`
Expected: `0`

- [ ] **Step 5: Verify the OKF spec URL and the four type values are present in the body.**

Run: `grep -c "knowledge-catalog/blob/main/okf/SPEC.md" skills/design-experiment/SKILL.md && grep -c "Dataset Design" skills/design-experiment/SKILL.md`
Expected: both ≥ 1.

- [ ] **Step 6: Commit**

```bash
git add skills/design-experiment/SKILL.md
git commit -m "docs(design-experiment): document OKF contract, resource-omission rule, index upkeep"
```

---

### Task 6: Add the `index.md` template the skill references

**Files:**
- Create: `skills/design-experiment/references/index-template.md`

**Interfaces:**
- Consumes: referenced by Task 5's SKILL.md upkeep step (`references/index-template.md`).
- Produces: the copy-me shape for a project's `docs/design/index.md`.

- [ ] **Step 1: Create the index template** with the explicit OKF declaration (the primary of the three declaration sites) and the bundle listing shape:

```markdown
# docs/design/ index template

Copy the block below to `docs/design/index.md` in a DerivaML project. It is the
OKF bundle root — a directory listing of the design corpus. Add a line per
design doc as they are authored.

## Template (copy below this line)

---
type: Index
title: DerivaML design documents
description: >
  Up-front design specifications for this project's experiments, datasets,
  features, and models.
---

# Design documents

These design documents follow the
[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
— Markdown + YAML frontmatter. Each `<entity>/<slug>.md` is an OKF concept
document with a `type` of `Dataset Design`, `Experiment Design`,
`Feature Design`, or `Model Design`. These are abstract specifications (intent),
so they carry no OKF `resource` field; the produced catalog entities and their
RIDs live in `tacit-knowledge.md` and each doc's "Status & links" section.

## experiment/
<!-- - [<slug>](experiment/<slug>.md) — <one-line description> (Status: <status>) -->

## dataset/
<!-- - [<slug>](dataset/<slug>.md) — <one-line description> (Status: <status>) -->

## feature/
<!-- - [<slug>](feature/<slug>.md) — <one-line description> (Status: <status>) -->

## model/
<!-- - [<slug>](model/<slug>.md) — <one-line description> (Status: <status>) -->
```

- [ ] **Step 2: Verify the index template's frontmatter parses and declares OKF.**

Run: `awk '/^---$/{c++; next} c==1' skills/design-experiment/references/index-template.md | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Index'; print('OK')"` then `grep -c "Open Knowledge Format" skills/design-experiment/references/index-template.md`
Expected: `OK`, and the grep ≥ 1.

- [ ] **Step 3: Commit**

```bash
git add skills/design-experiment/references/index-template.md
git commit -m "feat(design-experiment): add OKF index.md bundle-root template"
```

---

### Task 7: Update `validate-project-setup` checklist row

**Files:**
- Modify: `skills/validate-project-setup/SKILL.md`

**Interfaces:**
- Consumes: the `docs/design/` row already exists in this skill's top-level layout table (it checks `docs/design/` presence and says "not yet used is normal on a new project").

- [ ] **Step 1: Find the `docs/design/` checklist row.**

Run: `grep -n "docs/design" skills/validate-project-setup/SKILL.md`
Expected: the row in the "Top-level repository layout" table + the "Common gaps" note about design docs being "not yet used".

- [ ] **Step 2: Extend the `docs/design/` row's description** to add the OKF conformance check, without changing the "absent is normal early" guidance. Update the table cell to note: *"Design docs follow OKF (Markdown + YAML frontmatter); when present, each `<entity>/<slug>.md` should open with frontmatter carrying at least `type` (`Dataset Design` / `Experiment Design` / `Feature Design` / `Model Design`). A `docs/design/index.md` bundle listing is expected once any design exists."*

- [ ] **Step 3: Preserve the "not yet used" common-gaps note.** Confirm the existing sentence ("Do not flag a missing `docs/design/` on a new or early project … report it as 'not yet used'") is still present and unchanged.

Run: `grep -n "not yet used" skills/validate-project-setup/SKILL.md`
Expected: still present.

- [ ] **Step 4: Verify frontmatter (name/description) unchanged.**

Run: `git diff skills/validate-project-setup/SKILL.md | grep -E "^[-+](name:|description:)" | grep -vE "^[-+][-+]" | wc -l`
Expected: `0`

- [ ] **Step 5: Commit**

```bash
git add skills/validate-project-setup/SKILL.md
git commit -m "docs(validate-project-setup): add OKF-frontmatter check to docs/design row"
```

---

### Task 8: Cross-reference sweep + final conformance check

**Files:**
- Audit (read-only, then fix any hits): all `skills/**/*.md`

**Interfaces:**
- Consumes: everything from Tasks 1–7.

- [ ] **Step 1: Find any skill that quotes the OLD design-doc header shape** (`**Slug:**` / `**Status:**` in the context of a design doc) and would now be stale.

Run: `grep -rn '\*\*Slug:\*\*\|\*\*Status:\*\*' skills/ | grep -v design-experiment/references`
Expected: review each hit. If a skill shows the old prose-header form *as the design-doc shape*, update it to mention the OKF frontmatter form. (Many hits may be unrelated — judge each.)

- [ ] **Step 2: Confirm all four templates + the index template parse and carry the right `type`.**

Run:
```bash
for f in dataset experiment feature model; do
  awk '/^---$/{c++; next} c==1' "skills/design-experiment/references/$f-design-template.md" \
    | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); print('$f', d['type'], 'resource' in d)"
done
awk '/^---$/{c++; next} c==1' skills/design-experiment/references/index-template.md \
  | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); print('index', d['type'])"
```
Expected: four lines `<entity> <Kind> Design False` (resource absent) + `index Index`.

- [ ] **Step 3: Confirm the explicit OKF declaration is present in all three required places.**

Run:
```bash
echo "index-template:"; grep -c "Open Knowledge Format" skills/design-experiment/references/index-template.md
echo "SKILL.md:"; grep -c "Open Knowledge Format" skills/design-experiment/SKILL.md
echo "templates with OKF comment:"; grep -rl "Open Knowledge Format" skills/design-experiment/references/*-design-template.md | wc -l
```
Expected: index-template ≥ 1, SKILL.md ≥ 1, templates = 4.

- [ ] **Step 4: Confirm no template still has a "Worked example" heading.**

Run: `grep -rl "Worked example" skills/design-experiment/references/ || echo "none — good"`
Expected: `none — good`.

- [ ] **Step 5: Commit any fixes from Step 1** (if none, skip).

```bash
git add -A skills/
git commit -m "docs(skills): align cross-references to OKF design-doc header shape"
```

---

## Self-Review

**1. Spec coverage:**
- Frontmatter contract on 4 templates → Tasks 1–4. ✓
- `resource` always omitted + rationale comment → every template task (Step 2/3) + verified Step 5 + Task 8 Step 2. ✓
- `type` per entity + `status` per-type enum → Tasks 1–4 (Released only on dataset). ✓
- Body heading "Worked example"→`## Examples`, no `# Schema`, no invented `## Citations` → Tasks 1–4 Step 4 + Task 8 Step 4. ✓
- `index.md` bundle + its `type: Index` frontmatter → Task 6 (template) + Task 5 Step 3 (upkeep). ✓
- Explicit OKF declaration in 3 places → index-template (Task 6), SKILL.md (Task 5 Step 2), each template comment (Tasks 1–4) → verified Task 8 Step 3. ✓
- SKILL.md documents contract + index upkeep → Task 5. ✓
- `validate-project-setup` row + "absent is normal" preserved → Task 7. ✓
- SKILL.md name/description byte-identical → Task 5 Step 4, Task 7 Step 4. ✓
- No validator script, no `log.md` → not in any task (correctly absent). ✓
- Plugin ships templates/instructions, not a project's docs/design/ → reflected: no task creates a real `docs/design/` tree; Task 6 creates a *reference template*, not `docs/design/index.md`. ✓

**2. Placeholder scan:** The `<one-line title>` / `<slug>` / `<structure>` tokens are template *content* (the literal placeholders a user fills), not plan placeholders — intended. Worked-example tasks (2–4 Step 3) say "read the file first, fill values to match" rather than hardcoding values I haven't seen; that's deliberate (I haven't read those three files' exact example values), and each gives the exact `type` + enum to use. No "TODO/TBD/handle appropriately".

**3. Type consistency:** `type` values consistent across all tasks (`Dataset Design`/`Experiment Design`/`Feature Design`/`Model Design`, `Index`). `status` enum per-type consistent (Released only on dataset). OKF spec URL identical everywhere. The `references/index-template.md` path is named identically in Task 5 Step 3 and Task 6.
