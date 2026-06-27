# D/E/F Maintainability Wave Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose 4 oversized reference files into OKF bundles, collapse 5 cross-skill duplications to one owner + pointer, and trim 3 heavy skills — with zero change to what any skill does.

**Architecture:** One dependency-ordered branch (`chore/def-maintainability-wave`), executed E (OKF decomposition) → F (dedup) → D (compaction). E runs first because its canonical docs (`status-machine.md`, `rules-and-validation.md`) are what F points at and D relies on. Every change is a content move + pointer update, an OKF restructure, or a dedup — never a rewrite.

**Tech Stack:** Markdown + YAML frontmatter (OKF — [SPEC](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)). No code, no build step. "Tests" are verification commands: section-inventory diffs, relative-link resolution, line-count targets, and a repo-wide dangling-pointer grep.

## Global Constraints

- **OKF bundle convention** (from the v1.12.0 schema bundle at `deriva-ml-context/references/concepts/`): directory `references/concepts/` with a reserved `index.md` (`type: Index`) + per-concept docs. Frontmatter = `type:` (required) + `title` + `description`; `resource:` omitted (reference concepts, not external-artifact pointers).
- **Links between sibling OKF docs are relative** (`[Status machine](status-machine.md)`), never bundle-absolute.
- **Cross-skill references are inline-code skill names** (`/deriva-ml:execution-lifecycle`), never `[](…)` links.
- **Granularity:** cluster H2 sections into 4-6 coherent OKF docs per bundle — NOT one-file-per-H2.
- **No frontmatter / trigger-description changes** — this wave is body + reference only. If a task would touch a SKILL.md `description:` line, stop; that's out of scope.
- **No content loss:** every move is cut-paste of whole sections. Each decomposition task ends by confirming the union of new-doc H2s equals the original's H2 inventory (minus the dropped `## Table of Contents`).
- **CWD discipline:** chain `cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && <cmd>` in every Bash call; the Bash cwd is not persistent.
- The branch already exists with the design spec committed. Do NOT create release tags.

---

## Phase E — OKF decomposition (Tasks 1-4)

Each task: create the bundle dir, split the monolith into clustered OKF docs, write the index, delete the monolith, update the OWNING skill's own pointers. Cross-SKILL pointers (from other skills) are fixed in Phase F/the final sweep so each E task stays self-contained.

### Task 1: Decompose `execution-lifecycle/references/concepts.md` → OKF bundle

**Files:**
- Create: `skills/execution-lifecycle/references/concepts/index.md` + `status-machine.md`, `structure.md`, `authoring.md`, `validation.md`, `data-flow.md`
- Delete: `skills/execution-lifecycle/references/concepts.md`
- Modify: `skills/execution-lifecycle/SKILL.md` (pointers to `references/concepts.md` → bundle)

**Interfaces:**
- Produces: `skills/execution-lifecycle/references/concepts/status-machine.md` — the canonical execution status machine (Task 9 / F-status-dedup points here); `validation.md` carries "Schema Pinning for Long Runs" + "Offline Mode" (Task 12 cross-skill pointers resolve here).

- [ ] **Step 1: Record the source inventory**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "^## " skills/execution-lifecycle/references/concepts.md | grep -v "Table of Contents" > /tmp/exec-concepts-before.txt
cat /tmp/exec-concepts-before.txt
```
Expected: the 18 content H2s (Executions in the Catalog … Offline Mode).

- [ ] **Step 2: Create the bundle docs by moving H2 clusters**

Create the directory and 5 docs. Move (cut-paste) each current H2 section verbatim into its target doc per the spec's cluster table:
- `status-machine.md` (`type: StateMachine`): Execution Statuses, Re-Running an Aborted Execution, + the status table.
- `structure.md` (`type: Concept`): Executions in the Catalog, Execution RIDs, Execution Structure, Nested Executions.
- `authoring.md` (`type: Concept`): Creating and Managing Executions, ExecutionConfiguration, The Execution Context Manager, Execution Working Directory, Execution Metadata Auto-Generation, Dry Run Mode.
- `validation.md` (`type: Concept`): Pre-Flight Validation, Schema Pinning for Long Runs, Offline Mode.
- `data-flow.md` (`type: Concept`): Execution Data Flow, Automatic Source Code Detection, Workflows and Workflow Types.

Each doc starts with frontmatter, e.g. `status-machine.md`:
```markdown
---
type: StateMachine
title: Execution status machine
description: The execution status lifecycle (Created → Running → Stopped → Pending_Upload → Uploaded, plus terminal Failed/Aborted) and how transitions are driven.
---

# Execution status machine

<moved sections here>
```
Convert any intra-file anchor links (`[…](#schema-pinning-for-long-runs)`) to relative sibling links (`[…](validation.md)`).

- [ ] **Step 3: Write the bundle index**

Create `index.md`:
```markdown
---
type: Index
title: Execution lifecycle concepts
description: OKF bundle for the DerivaML execution lifecycle — status machine, structure/nesting, authoring, validation, and data flow.
---

# Execution lifecycle concepts

- [Status machine](status-machine.md) — the status lifecycle + re-running aborted runs.
- [Structure](structure.md) — executions in the catalog, RIDs, nesting.
- [Authoring](authoring.md) — ExecutionConfiguration, the context manager, working dir, dry run.
- [Validation](validation.md) — pre-flight checks, schema pinning, offline mode.
- [Data flow](data-flow.md) — inputs/outputs, source-code detection, workflows.
```

- [ ] **Step 4: Delete the monolith and update the owning skill's pointers**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git rm skills/execution-lifecycle/references/concepts.md
grep -n "references/concepts" skills/execution-lifecycle/SKILL.md
```
Update each hit in `execution-lifecycle/SKILL.md` to point at the bundle (`references/concepts/` for the whole bundle, or the specific doc when it referenced a named section).

- [ ] **Step 5: Verify inventory preserved + links resolve**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -h "^## \|^# " skills/execution-lifecycle/references/concepts/*.md | grep -v "Table of Contents" | sort > /tmp/exec-concepts-after.txt
# Confirm no content H2 dropped (allowing the new H1 titles):
comm -23 <(sed 's/^## //' /tmp/exec-concepts-before.txt | sort) <(sed 's/^#* //' /tmp/exec-concepts-after.txt | sort)
# Verify every relative sibling link resolves:
for f in skills/execution-lifecycle/references/concepts/*.md; do
  grep -oE "\]\(([a-z-]+\.md)\)" "$f" | sed -E 's/\]\(|\)//g' | while read t; do
    [ -f "skills/execution-lifecycle/references/concepts/$t" ] || echo "DANGLING: $f -> $t"; done; done
```
Expected: `comm` prints nothing (every source H2 landed somewhere); no `DANGLING` lines.

- [ ] **Step 6: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/execution-lifecycle/
git commit -m "refactor(execution-lifecycle): decompose concepts.md into OKF bundle (E)"
```

### Task 2: Decompose `write-hydra-config/references/config-reference.md` → OKF bundle

**Files:**
- Create: `skills/write-hydra-config/references/config-reference/index.md` + `base-and-connection.md`, `data-configs.md`, `model-and-experiments.md`, `multiruns-and-notebooks.md`, `rules-and-validation.md`
- Delete: `skills/write-hydra-config/references/config-reference.md`
- Modify: `skills/write-hydra-config/SKILL.md` (6 named-section pointers at lines 24, 42, 58, 62, 120, 130, 159)

**Interfaces:**
- Produces: `rules-and-validation.md` — carries "Per-Group Key Rules", "Description Mechanisms", "Config Class Parameter Reference", "MCP Reference Resources", "Bootstrap Configs from a Catalog", "Validating Configs Against the Catalog", AND the Config-Groups material (Task 11 / F-config-groups points here).

- [ ] **Step 1: Record source inventory**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "^## " skills/write-hydra-config/references/config-reference.md | grep -v "Table of Contents" > /tmp/hydra-before.txt
cat /tmp/hydra-before.txt
```
Note: there are TWO `## Architecture` headings and the H2s map by config-file family.

- [ ] **Step 2: Create the bundle docs by moving H2 clusters**

Create `config-reference/` and move sections per the spec:
- `base-and-connection.md` (`type: ConfigReference`): `__init__.py`, Base Config (`base.py`), Deriva Connection (`deriva.py`).
- `data-configs.md`: Datasets (`datasets.py`), Assets (`assets.py`), Workflow (`workflow.py`), both Architecture blocks, Outputs.
- `model-and-experiments.md`: Model Config (`model.py`), Experiments (`experiments.py`).
- `multiruns-and-notebooks.md`: Multiruns (`multiruns.py`), Notebook Configs.
- `rules-and-validation.md`: Per-Group Key Rules, Description Mechanisms and Good Descriptions, Config Class Parameter Reference, MCP Reference Resources, Bootstrap Configs from a Catalog, Validating Configs Against the Catalog.

Frontmatter example (`rules-and-validation.md`):
```markdown
---
type: ConfigReference
title: Config rules, parameter reference, bootstrap & validation
description: Per-group key rules, the description mechanisms, the full config-class parameter tables, MCP starter resources, and how to bootstrap/validate configs against a catalog.
---
```

- [ ] **Step 3: Write `config-reference/index.md`** (`type: Index`) listing the 5 docs with one-line descriptions (same shape as Task 1 Step 3).

- [ ] **Step 4: Delete monolith + update the 6 owning-skill pointers**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git rm skills/write-hydra-config/references/config-reference.md
grep -n "config-reference" skills/write-hydra-config/SKILL.md
```
Rewrite each `references/config-reference.md → "<Section>"` pointer to the specific bundle doc that now holds that section, e.g.:
- line 42 `→ "Per-Group Key Rules"` ⇒ `references/config-reference/rules-and-validation.md`
- line 58 `→ "Description Mechanisms…"` ⇒ `rules-and-validation.md`
- line 62 `→ "Config Class Parameter Reference"` ⇒ `rules-and-validation.md`
- line 120 `→ "MCP Reference Resources"` ⇒ `rules-and-validation.md`
- line 130 `→ "Bootstrap Configs from a Catalog"` ⇒ `rules-and-validation.md`
- line 159 `→ "Validating Configs Against the Catalog"` ⇒ `rules-and-validation.md`
- line 24 (the generic "Annotated examples…" pointer) ⇒ `references/config-reference/` (the bundle).

- [ ] **Step 5: Verify** (same two checks as Task 1 Step 5, paths swapped to `write-hydra-config/references/config-reference/`). Expected: no dropped H2, no DANGLING.

- [ ] **Step 6: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/write-hydra-config/
git commit -m "refactor(write-hydra-config): decompose config-reference.md into OKF bundle (E)"
```

### Task 3: Decompose `dataset-lifecycle/references/concepts.md` → OKF bundle

**Files:**
- Create: `skills/dataset-lifecycle/references/concepts/index.md` + `dataset-types.md`, `structure-and-splits.md`, `versioning.md`, `navigation.md`, `lifecycle-ops.md`
- Delete: `skills/dataset-lifecycle/references/concepts.md`
- Modify: `skills/dataset-lifecycle/SKILL.md` (own pointers, if any — grep to confirm)

**Interfaces:**
- Consumes: nothing. Produces: a self-contained bundle. No other skill currently points at this file (verified — grep returned no external referrers), so only dataset-lifecycle's own pointers need updating.

- [ ] **Step 1: Record inventory**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "^## " skills/dataset-lifecycle/references/concepts.md | grep -v "Table of Contents" > /tmp/ds-before.txt && cat /tmp/ds-before.txt
```

- [ ] **Step 2: Move H2 clusters** into the 5 docs:
- `dataset-types.md` (`type: Concept`): What is a Dataset?, Dataset Types, Dataset Element Types.
- `structure-and-splits.md`: Dataset Structure (Standalone/Nested/Splits), Splitting Datasets, Subsampling Datasets.
- `versioning.md`: Dataset Versioning (ADR-0003), Identifying a Dataset: RID + Version.
- `navigation.md`: Discovering Existing Datasets, Exploring and Navigating Datasets, Using Datasets, Downloading Datasets as Bags.
- `lifecycle-ops.md`: Deleting Datasets, Operations Summary, Characterization & validation (roadmap).

- [ ] **Step 3: Write `concepts/index.md`** (`type: Index`).

- [ ] **Step 4: Delete monolith + update own pointers**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git rm skills/dataset-lifecycle/references/concepts.md
grep -n "references/concepts" skills/dataset-lifecycle/SKILL.md
```
Update each hit to the bundle / specific doc.

- [ ] **Step 5: Verify** (Task 1 Step 5 checks, paths swapped). Expected: no dropped H2, no DANGLING.

- [ ] **Step 6: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/dataset-lifecycle/
git commit -m "refactor(dataset-lifecycle): decompose concepts.md into OKF bundle (E)"
```

### Task 4: Decompose `create-feature/references/concepts.md` + fold in `feature-selectors.md` → OKF bundle

**Files:**
- Create: `skills/create-feature/references/concepts/index.md` + `feature-vs-column.md`, `design.md`, `selectors.md`, `usage.md`
- Delete: `skills/create-feature/references/concepts.md`, `skills/create-feature/references/feature-selectors.md`
- Modify: `skills/create-feature/SKILL.md` (lines 34, 91, 188, 220, 222); `skills/ml-data-engineering/references/restructure-guide.md:10` (anchor link to feature-selectors — see note); `skills/create-feature/evals/evals.json:55` (mentions `feature-selectors.md`)

**Interfaces:**
- Consumes: nothing. Produces: `selectors.md` (absorbs the old `feature-selectors.md` whole).

- [ ] **Step 1: Record inventory of BOTH source files**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "^## " skills/create-feature/references/concepts.md | grep -v "Table of Contents" > /tmp/feat-before.txt
echo "--- feature-selectors.md ---" >> /tmp/feat-before.txt
grep -n "^## \|^# " skills/create-feature/references/feature-selectors.md >> /tmp/feat-before.txt
cat /tmp/feat-before.txt
```

- [ ] **Step 2: Move H2 clusters** into 4 docs:
- `feature-vs-column.md` (`type: Concept`): What is a Feature?, When to Use a Feature vs a Column.
- `design.md`: Feature Types, Designing a Feature, Feature Naming, Metadata Columns, Feature Column Optionality and Valid Values, Multivalued Features.
- `selectors.md`: the "Feature Selection" H2 from concepts.md + the ENTIRE contents of `feature-selectors.md` (merge; dedupe the overlapping selector list, keep the richer version).
- `usage.md`: Discovering Existing Features, Feature Records (Python API), Features in Datasets, Exploring and Navigating Features, Feature Value Table Naming, Operations Summary.

- [ ] **Step 3: Write `concepts/index.md`** (`type: Index`, 4 entries).

- [ ] **Step 4: Delete both monoliths + update pointers**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git rm skills/create-feature/references/concepts.md skills/create-feature/references/feature-selectors.md
```
Update in `create-feature/SKILL.md`:
- line 34 `concepts.md under "When to Use a Feature vs a Column"` ⇒ `references/concepts/feature-vs-column.md`
- line 91 `concepts.md under "Designing a Feature"` ⇒ `references/concepts/design.md`
- line 188 `references/feature-selectors.md` ⇒ `references/concepts/selectors.md`
- line 220 `references/concepts.md — Feature types…` ⇒ `references/concepts/` (bundle)
- line 222 `references/feature-selectors.md — Complete guide…` ⇒ `references/concepts/selectors.md`

Update `create-feature/evals/evals.json:55` text "reference feature-selectors.md" ⇒ "reference references/concepts/selectors.md".
Update `ml-data-engineering/references/restructure-guide.md:10` — this is an intra-doc anchor `[Per-Feature Selectors](#per-feature-selectors)`, NOT a reference to the deleted file. Confirm with the grep below; if it's a self-anchor, leave it.
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
sed -n '8,12p' skills/ml-data-engineering/references/restructure-guide.md
```

- [ ] **Step 5: Verify** (Task 1 Step 5 checks, paths swapped to `create-feature/references/concepts/`). Confirm both source files' H2s landed. Expected: no dropped H2, no DANGLING.

- [ ] **Step 6: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/create-feature/ skills/ml-data-engineering/
git commit -m "refactor(create-feature): decompose concepts.md + fold in feature-selectors into OKF bundle (E)"
```

---

## Phase F — Dedup (Tasks 5-9)

### Task 5: Collapse the `restructure-guide.md` near-duplicate

**Files:**
- Modify: `skills/ml-data-engineering/references/restructure-guide.md` (absorb work-with-assets's unique sections if missing)
- Delete: `skills/work-with-assets/references/restructure-guide.md`
- Modify: `skills/work-with-assets/SKILL.md:160` (pointer → ml-data-engineering's guide)

**Interfaces:**
- Consumes: nothing. Produces: one canonical `ml-data-engineering/references/restructure-guide.md`.

- [ ] **Step 1: Diff the two files' section inventories to find work-with-assets-unique content**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
comm -13 \
  <(grep "^## " skills/ml-data-engineering/references/restructure-guide.md | sort) \
  <(grep "^## " skills/work-with-assets/references/restructure-guide.md | sort)
```
Expected: the H2s present ONLY in work-with-assets's copy (the audit cited "Upload Tuning", "ML Framework Patterns" — confirm here).

- [ ] **Step 2: Merge unique sections into the canonical guide**

For each H2 the `comm` lists as work-with-assets-only, cut-paste that section into `ml-data-engineering/references/restructure-guide.md` at a sensible position (Upload Tuning near the end; ML Framework Patterns after Directory Layout). If a same-named section already exists in the canonical guide with equivalent content, keep the canonical one (no duplicate).

- [ ] **Step 3: Delete work-with-assets's copy + repoint its skill**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git rm skills/work-with-assets/references/restructure-guide.md
```
Rewrite `work-with-assets/SKILL.md:160` from a self-reference to:
```markdown
- Restructuring assets for ML training (`targets`/`target_transform`, per-feature selectors, file transformers, ML framework patterns) is owned by `/deriva-ml:ml-data-engineering` — see its `references/restructure-guide.md`.
```

- [ ] **Step 4: Verify no remaining self-reference + canonical guide intact**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
test ! -f skills/work-with-assets/references/restructure-guide.md && echo "deleted OK"
grep -rn "work-with-assets/references/restructure-guide" skills/ || echo "no dangling refs"
grep -c "^## " skills/ml-data-engineering/references/restructure-guide.md
```
Expected: "deleted OK", "no dangling refs", and the canonical guide's H2 count ≥ its original (gained the merged sections).

- [ ] **Step 5: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/ml-data-engineering/ skills/work-with-assets/
git commit -m "refactor(assets): collapse duplicate restructure-guide to ml-data-engineering (F)"
```

### Task 6: Dedup find/list taxonomy (deriva-ml-context → api-naming-conventions)

**Files:**
- Modify: `skills/deriva-ml-context/SKILL.md` (lines ~204-215, the `## Python API method naming: find_* vs list_*` section)
- Verify: `skills/api-naming-conventions/SKILL.md` owns the full taxonomy

- [ ] **Step 1: Confirm api-naming-conventions carries the full taxonomy**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "find_\|list_\|find vs list\|scope" skills/api-naming-conventions/SKILL.md | head
```
Expected: the find/list distinction with examples is present (it owns this). If it is THIN (missing the deriva-ml-context detail), first move the richer examples there, THEN trim context. Note what you find.

- [ ] **Step 2: Replace the deriva-ml-context section with a 2-line pointer**

Read `deriva-ml-context/SKILL.md` lines 204-216, then replace the section body (keep the `## Python API method naming: find_* vs list_*` H2) with:
```markdown
## Python API method naming: `find_*` vs `list_*`

`find_*` searches the catalog for entities of a kind (its argument is a *filter*); `list_*` enumerates entities scoped to a specific parent (its first argument *is* the scope). The full taxonomy with examples lives in `/deriva-ml:api-naming-conventions` *(auto-loaded)* — consult it when choosing a method.
```

- [ ] **Step 3: Verify owner has the detail trimmed from context**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "ml.find_features\|ml.find_datasets\|ml.find_executions" skills/api-naming-conventions/SKILL.md
```
Expected: the example list now lives in api-naming-conventions (moved there in Step 1 if it wasn't already).

- [ ] **Step 4: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/deriva-ml-context/ skills/api-naming-conventions/
git commit -m "refactor(deriva-ml-context): point find/list taxonomy at api-naming-conventions (F)"
```

### Task 7: Dedup Config-Groups table (configure-experiment → write-hydra-config)

**Files:**
- Modify: `skills/configure-experiment/SKILL.md` (the Config-Groups table → pointer)
- Verify: `write-hydra-config` owns it (now in `references/config-reference/rules-and-validation.md` from Task 2)

- [ ] **Step 1: Locate the Config-Groups material in configure-experiment**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "Config.Group\|config_group\|base\b.*deriva\b.*datasets\|group.*table" skills/configure-experiment/SKILL.md | head
```
Read the surrounding table to see exactly what duplicates write-hydra-config's per-group material.

- [ ] **Step 2: Replace the duplicated table with a pointer**

Keep configure-experiment's own narrative (it owns the Phase-2 config seam), but where it reproduces the per-group key/structure table, replace that table with:
```markdown
The per-config-group key rules and structure (which keys each of `base` / `deriva` / `datasets` / `assets` / `model` / `experiments` / `multiruns` carries) are owned by `/deriva-ml:write-hydra-config` — see `references/config-reference/rules-and-validation.md`.
```
Only replace the duplicated TABLE; leave configure-experiment's routing/seam prose intact.

- [ ] **Step 3: Verify**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "rules-and-validation\|write-hydra-config" skills/configure-experiment/SKILL.md
```
Expected: the pointer is present; the duplicated table is gone.

- [ ] **Step 4: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/configure-experiment/
git commit -m "refactor(configure-experiment): point config-groups table at write-hydra-config (F)"
```

### Task 8: Dedup MCP primer/resource rules (deriva-ml-context → using-deriva-mcp)

**Files:**
- Modify: `skills/deriva-ml-context/SKILL.md` (MCP primer/resource procedure → short pointer; KEEP the precedence frame)
- Verify: `using-deriva-mcp` owns the cold-start procedure

- [ ] **Step 1: Find the overlapping MCP-procedure content in deriva-ml-context**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "primer\|cold.start\|deriva_ml_primer\|resource.*first\|fetch.*resource" skills/deriva-ml-context/SKILL.md
grep -n "primer\|cold.start\|deriva_ml_primer" skills/using-deriva-mcp/SKILL.md | head
```
Identify the lines in deriva-ml-context that restate the cold-start *procedure* (vs the precedence *principle*, which stays).

- [ ] **Step 2: Trim the procedure to a pointer**

In `deriva-ml-context/SKILL.md`, keep the "fetch the resource before reaching for tools" *principle* (lines ~65-82 — that's the load-bearing steering frame), but where it restates the primer/cold-start *procedure*, replace with:
```markdown
The MCP cold-start procedure (call `deriva_ml_primer`, then fetch guides on demand) is owned by `/deriva-ml:using-deriva-mcp` *(auto-loaded before the first MCP call)*.
```
Do NOT remove the read-side resource-first guidance — that's the steering principle this skill exists to carry.

- [ ] **Step 3: Verify the principle survived + procedure points out**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "fetch the resource\|resource first\|Read-side" skills/deriva-ml-context/SKILL.md
grep -n "using-deriva-mcp" skills/deriva-ml-context/SKILL.md
```
Expected: the resource-first principle is still present; a using-deriva-mcp pointer exists.

- [ ] **Step 4: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/deriva-ml-context/
git commit -m "refactor(deriva-ml-context): point MCP cold-start at using-deriva-mcp, keep precedence frame (F)"
```

### Task 9: Dedup execution status machine (troubleshoot-execution → execution-lifecycle status-machine.md)

**Files:**
- Modify: `skills/troubleshoot-execution/SKILL.md` (the status *transition* prose points at the canonical doc; KEEP the salvage-decision table)

**Interfaces:**
- Consumes: `execution-lifecycle/references/concepts/status-machine.md` (Task 1).

- [ ] **Step 1: Distinguish the two tables in troubleshoot-execution**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
sed -n '248,260p' skills/troubleshoot-execution/SKILL.md
```
The table at ~252-257 is a **salvage-decision** table (status | salvageable? | meaning | what to run) — troubleshooting-specific, KEEP IT. Only the generic *transition descriptions* elsewhere duplicate the canonical machine.

- [ ] **Step 2: Add a canonical-doc pointer above the salvage table**

Insert, just before the salvage-decision table, a one-liner:
```markdown
For the canonical status machine (every transition and what drives it), see `/deriva-ml:execution-lifecycle`'s `references/concepts/status-machine.md`. The table below is the troubleshooting view: which states are salvageable and what to run.
```
Then, if any prose elsewhere in the file *re-explains* the full Created→…→Uploaded transition sequence (not the salvage view), compress it to a sentence + the same pointer.

- [ ] **Step 3: Verify the salvage table is intact and the pointer resolves**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "status-machine.md\|Salvage" skills/troubleshoot-execution/SKILL.md
test -f skills/execution-lifecycle/references/concepts/status-machine.md && echo "canonical doc exists"
```
Expected: pointer present, salvage section heading present, canonical doc exists.

- [ ] **Step 4: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/troubleshoot-execution/
git commit -m "refactor(troubleshoot-execution): point status transitions at canonical status-machine (F)"
```

---

## Phase D — Compaction (Tasks 10-12)

### Task 10: Extract troubleshoot-execution salvage section → reference

**Files:**
- Create: `skills/troubleshoot-execution/references/salvage-guide.md`
- Modify: `skills/troubleshoot-execution/SKILL.md` (move the deep salvage workflow body; keep routing + decision table + pointer)

- [ ] **Step 1: Identify the salvage section boundaries**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "^## Salvage\|^## \|^### Branch" skills/troubleshoot-execution/SKILL.md | sed -n '/Salvage/,$p'
wc -l skills/troubleshoot-execution/SKILL.md
```
The "Salvage a Failed Execution" section (~line 234 onward) holds the deep recovery branches (B/C, pending_summary, recovery-execution code). The symptom-routing table + the salvage-decision table (Task 9) stay in SKILL.md.

- [ ] **Step 2: Move the deep workflow to the reference**

Create `references/salvage-guide.md` (plain reference, no OKF needed — it's a single workflow doc, consistent with the skill's other `references/`):
```markdown
# Salvaging a failed or stranded execution

<moved: the deep recovery branches, recovery-execution code, pending_summary inspection, the Branch B/C walkthrough>
```
Leave in SKILL.md: the symptom→section routing table, the salvage-decision table (status | salvageable? | what to run), and a pointer:
```markdown
For the full salvage walkthrough — recovery-execution code, the Branch B/C decision, `pending_summary()` inspection — see `references/salvage-guide.md`.
```

- [ ] **Step 3: Verify line target + pointer**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
wc -l skills/troubleshoot-execution/SKILL.md
grep -n "salvage-guide.md" skills/troubleshoot-execution/SKILL.md
test -f skills/troubleshoot-execution/references/salvage-guide.md && echo "reference created"
```
Expected: SKILL.md now < ~340L; pointer present; reference exists.

- [ ] **Step 4: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/troubleshoot-execution/
git commit -m "refactor(troubleshoot-execution): extract salvage workflow to reference (D)"
```

### Task 11: Extract capture-tacit-knowledge entry-format → reference

**Files:**
- Create: `skills/capture-tacit-knowledge/references/entry-format.md`
- Modify: `skills/capture-tacit-knowledge/SKILL.md` (move entry-format mechanics ~lines 72-212; keep the trigger discipline + pointer)

- [ ] **Step 1: Find the entry-format mechanics boundaries**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "^## \|^### " skills/capture-tacit-knowledge/SKILL.md
wc -l skills/capture-tacit-knowledge/SKILL.md
```
Identify the sections that are *format mechanics* (entry template, field-by-field rules, examples) vs the *trigger discipline* (the WRITE/GUIDANCE/FORENSIC firing rules — the load-bearing always-on part that stays).

- [ ] **Step 2: Move the mechanics to the reference**

Create `references/entry-format.md` with the entry template, the per-field guidance, and the worked examples. Keep in SKILL.md: the three-trigger discipline, the do-NOT-fire boundary, and a pointer:
```markdown
For the entry format — the template, field-by-field guidance, and worked examples — see `references/entry-format.md`.
```

- [ ] **Step 3: Verify**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
wc -l skills/capture-tacit-knowledge/SKILL.md
grep -n "entry-format.md" skills/capture-tacit-knowledge/SKILL.md
grep -n "WRITE\|GUIDANCE\|FORENSIC\|do NOT fire\|Do NOT" skills/capture-tacit-knowledge/SKILL.md
```
Expected: SKILL.md < ~200L; pointer present; the three triggers + do-NOT boundary still inline.

- [ ] **Step 4: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/capture-tacit-knowledge/
git commit -m "refactor(capture-tacit-knowledge): extract entry-format mechanics to reference (D)"
```

### Task 12: Extract deriva-ml-context entity-resolution detail + compare-model-runs Pattern B/C

**Files:**
- Create: `skills/deriva-ml-context/references/entity-resolution.md`
- Modify: `skills/deriva-ml-context/SKILL.md` (keep compact steps + why-one-liner; move expanded rationale + read-through caveat; strengthen `/deriva:semantic-awareness` pointer)
- Modify: `skills/compare-model-runs/SKILL.md` (move Pattern B/C inline code to its existing references; keep Pattern A)

- [ ] **Step 1: Trim deriva-ml-context entity-resolution (lines 260-313)**

Read lines 260-313. Keep inline: the 6 numbered steps (compact form) + the one-line "why it matters" + the "Related always-on skills" pointer block (it cites `/deriva:semantic-awareness`). Move to `references/entity-resolution.md`: the expanded "Why this workflow matters" rationale, the detailed read-through-index caveat (the `deriva_ml_list_*`/`reindex_rows` warming detail at lines ~274-281), and the structured-vs-fuzzy examples. Strengthen the semantic-awareness pointer to name it the owner of the find-before-create discipline.

Add the pointer in SKILL.md:
```markdown
The expanded rationale, the read-through-index caveat, and the structured-vs-fuzzy examples are in `references/entity-resolution.md`. The underlying find-before-create discipline is owned by `/deriva:semantic-awareness` *(deriva-skills, auto-loaded)*.
```

- [ ] **Step 2: Move compare-model-runs Pattern B/C to references**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "^## \|Pattern A\|Pattern B\|Pattern C" skills/compare-model-runs/SKILL.md
ls skills/compare-model-runs/references/
```
Move the Pattern B and Pattern C inline code blocks into the existing matching reference file (identify it from the `ls` + grep). Keep Pattern A inline (the common path) + a pointer to the reference for B/C.

- [ ] **Step 3: Verify both**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
wc -l skills/deriva-ml-context/SKILL.md skills/compare-model-runs/SKILL.md
test -f skills/deriva-ml-context/references/entity-resolution.md && echo "entity-resolution ref created"
grep -n "semantic-awareness\|entity-resolution.md" skills/deriva-ml-context/SKILL.md
grep -n "Pattern A" skills/compare-model-runs/SKILL.md
```
Expected: deriva-ml-context < ~280L, compare-model-runs < ~280L; entity-resolution ref exists; Pattern A still inline; pointers present.

- [ ] **Step 4: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A skills/deriva-ml-context/ skills/compare-model-runs/
git commit -m "refactor: extract deriva-ml-context entity-resolution detail + compare-model-runs Pattern B/C (D)"
```

---

## Task 13: Repo-wide cross-reference sweep + conformance

**Files:** none created; a verification + fix-up pass across all skills.

- [ ] **Step 1: Hunt for dangling pointers to moved/deleted files**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
echo "=== refs to now-deleted monoliths (should be ZERO) ==="
grep -rn "references/concepts\.md\|config-reference\.md\|feature-selectors\.md\|work-with-assets/references/restructure-guide" skills/ | grep -v "references/concepts/" | grep -v "config-reference/"
echo "=== every relative .md link inside the new bundles resolves ==="
for d in skills/execution-lifecycle/references/concepts skills/write-hydra-config/references/config-reference skills/dataset-lifecycle/references/concepts skills/create-feature/references/concepts; do
  for f in "$d"/*.md; do
    grep -oE "\]\(([a-z0-9-]+\.md)\)" "$f" | sed -E 's/\]\(|\)//g' | while read t; do
      [ -f "$d/$t" ] || echo "DANGLING: $f -> $t"; done; done; done
```
Expected: both sections print nothing.

- [ ] **Step 2: OKF frontmatter conformance — every bundle doc has `type:`**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
for d in skills/*/references/concepts skills/*/references/config-reference; do
  [ -d "$d" ] || continue
  for f in "$d"/*.md; do
    head -1 "$f" | grep -q "^---$" && grep -q "^type:" "$f" || echo "MISSING FRONTMATTER/type: $f"; done; done
```
Expected: nothing printed.

- [ ] **Step 3: Final line-count report (the D targets)**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
for s in troubleshoot-execution capture-tacit-knowledge compare-model-runs deriva-ml-context; do
  printf "%-28s %s\n" "$s" "$(wc -l < skills/$s/SKILL.md)"; done
```
Expected: troubleshoot < ~340, capture < ~200, compare < ~280, context < ~280.

- [ ] **Step 4: Update the assay note with the D/E/F resolution**

Append a "Cluster D/E/F resolution (branch `chore/def-maintainability-wave`)" block to `docs/superpowers/notes/2026-06-27-global-assay.md` summarizing: 4 bundles created (doc counts), feature-selectors folded, 5 dedups + the restructure-guide collapse, 4 skills trimmed (before→after line counts), G1 confirmed deferred to Cluster B.

- [ ] **Step 5: Commit**
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add -A
git commit -m "docs(assay): record D/E/F resolution + cross-reference sweep (D/E/F)"
```

---

## Self-Review notes

- **Spec coverage:** E (Tasks 1-4) covers all 4 OKF files + feature-selectors fold; F (Tasks 5-9) covers all 5 dedups incl. the restructure-guide collapse; D (Tasks 10-12) covers all 4 heavy skills (troubleshoot, capture-tacit, compare-model-runs, deriva-ml-context-via-Task-12). G1 explicitly deferred. ✓
- **Ordering:** Task 1 (status-machine) precedes Task 9 (points at it); Task 2 (rules-and-validation) precedes Task 7 (points at it). ✓
- **No content loss:** every decomposition task has a before/after H2-inventory `comm` check; every move is cut-paste. ✓
- **No frontmatter changes:** Global Constraints forbid touching `description:` lines; the dedup/compaction tasks touch bodies + `## ` sections only. ✓
