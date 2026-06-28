# explore-results Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new guide-shaped read-only `explore-results` skill that gives domain scientists a home for the four read journeys (describe a RID, trace lineage, browse feature values, open in Chaise), and wire the surrounding skills to route to it.

**Architecture:** One new `skills/explore-results/SKILL.md` (resource-first, < ~200L, no references/ bundle) + three small wiring edits (create-feature trigger split + pointer, compare-model-runs cross-link, deriva-ml-context start-here row). No executable code — "tests" are tool/resource reality greps against the MCP plugin, cross-reference resolution, and trigger sanity.

**Tech Stack:** Markdown + YAML frontmatter. Skills are auto-discovered from `skills/*/SKILL.md`.

## Global Constraints

- **Read-only:** explore-results names ONLY observation-side tools/resources; it states it does not mutate the catalog. No mutating tool (`create_*`, `add_*`, `commit_*`, `update_*`, `delete_*`, `release_*`) may appear in a journey.
- **Resource-first:** each journey leads with the `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/...` resource fetch and names a `deriva_ml_*` tool only where the resource doesn't answer the question — honoring the `deriva-ml-context` precedence rule. Exception: Journey 1 (unknown-type RID) must start with `deriva_ml_describe_rid` because the entity type isn't known yet.
- **Cross-skill references are inline-code skill names** (`/deriva-ml:compare-model-runs`), never `[](…)` links.
- **No content duplication:** the DEEP lineage mechanics (two-step workflow-URL/git-commit walk, reproduction, per-row feature-value provenance) already live in `compare-model-runs` → "Trace an artifact's provenance" (lines 253-313). explore-results gives the domain-scientist ENTRY to lineage and DELEGATES the deep walk there — it does not restate it.
- **Verified tool/resource set** (real as of this wave — grep `../deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/` to confirm): tools `deriva_ml_describe_rid`, `deriva_ml_get_lineage`, `deriva_ml_get_execution`, `deriva_ml_get_dataset`, `deriva_ml_list_features`, `deriva_ml_list_feature_values`, `deriva_ml_lookup_asset`; resources `ml/dataset/{rid}`, `ml/execution/{rid}`, `ml/lineage/{rid}`, `ml/features/{table}`, `ml/asset/{rid}` — each returns per-row `cite_url`.
- **CWD discipline:** chain `cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && <cmd>` in every Bash call.
- Branch `feat/explore-results-skill` already exists with the spec committed. No release tags.

---

### Task 1: Author `skills/explore-results/SKILL.md` (the new skill)

**Files:**
- Create: `skills/explore-results/SKILL.md`

**Interfaces:**
- Produces: a new `/deriva-ml:explore-results` skill that Tasks 2-4 cross-reference. Its triggers will OWN the read-side feature-value-browsing phrases (`show me the labels`, `browse features`, `what annotations exist`, `feature values`, `show feature values`, `feature preview`) that Task 2 removes from create-feature.

- [ ] **Step 1: Write the frontmatter + skill body**

Create `skills/explore-results/SKILL.md` with this exact content:

```markdown
---
name: explore-results
description: "Use when a user wants to READ or INSPECT existing results in a DerivaML catalog without writing code — the domain-scientist read path. Fire on: inspecting a specific RID / result / artifact ('what is RID X', 'describe this RID', 'what is this'), tracing where something came from ('where did this prediction come from', 'what produced this', 'what dataset version is behind this', 'trace this asset'), browsing labels/annotations on records ('show me the labels', 'what annotations exist', 'what are the consensus labels', 'browse the feature values', 'feature preview'), and opening a record in the browser ('see this in Chaise', 'open this record', 'give me a link to this'). This skill is READ-ONLY — it inspects, it never creates or modifies. Do NOT use for: authoring (creating features/datasets/executions, adding labels → /deriva-ml:create-feature, /deriva-ml:execution-lifecycle, /deriva-ml:dataset-lifecycle); comparing MULTIPLE runs or regression checks (→ /deriva-ml:compare-model-runs); the first-MCP-call cold-start orientation (→ /deriva-ml:using-deriva-mcp); generic 'what is DerivaML' framing (→ the always-on deriva-ml-context)."
---

# Explore Results in a DerivaML Catalog

The read-only companion for **domain scientists** — inspect a result, trace where
it came from, browse labels, open a record in the browser. Everything here is
observation: this skill never creates or modifies catalog state (for that, see
the authoring skills it points to).

> Every tool and resource below takes the catalog's `hostname=` and `catalog_id=`
> explicitly. **Read-side rule:** fetch the `deriva://…` resource *first* — one
> fetch returns the entity plus its bundled children — and reach for a
> `deriva_ml_*` tool only where the resource doesn't answer the question (see
> `/deriva-ml:deriva-ml-context` → "Read-side questions: fetch the resource first").

## Journey 1 — "What is this RID?"

A bare RID whose kind you don't yet know is the one case that starts with a
**tool**, not a resource (you can't pick the right `deriva://…/{entity}/{rid}`
until you know the entity type):

```
deriva_ml_describe_rid(hostname, catalog_id, rid="<rid>")
```

It resolves the RID to its entity kind + a summary. From there, fetch the matching
resource for detail — `ml/dataset/{rid}` (→ Journey 3 for its labels),
`ml/execution/{rid}` (→ Journey 2 for what it produced), `ml/asset/{rid}` — and
read the `cite_url` it returns (→ Journey 4).

## Journey 2 — "Where did this come from?"

Provenance for any artifact (a prediction, a trained-model asset, a dataset
version, a feature value). Lead with the bundled lineage resource:

```
ReadMcpResourceTool(server="<name>",
  uri="deriva://catalog/{hostname}/{catalog_id}/deriva-ml/lineage/{rid}")
```

It returns the provenance chain — which Execution produced the artifact, what it
consumed, recursively. For traversal the resource doesn't cover, or to see a
producing run's full inputs/outputs, use `deriva_ml_get_lineage(hostname,
catalog_id, rid=...)` and `deriva_ml_get_execution(hostname, catalog_id,
execution_rid=...)`.

This is the **domain-scientist entry** to lineage — "what produced this?", answered
simply, then the `cite_url` to see it. When the question is the **developer**
reproduction one — *"what git commit + dataset version produced this, so I can
reproduce it"* — that needs the two-step lineage-walk → workflow-record pattern,
which is owned by `/deriva-ml:compare-model-runs` → "Trace an artifact's
provenance". And when the question is **across runs** — "which run was best", "is
this a regression" — that's `/deriva-ml:compare-model-runs` too. Hand those off;
don't reinvent them here.

## Journey 3 — "Show me the labels / what annotations exist"

Browsing feature values (labels, annotations, scores) on a table's records — the
read side of features. (Authoring features and *adding* values is
`/deriva-ml:create-feature`; this is reading what's there.)

First see what features exist on the table:

```
ReadMcpResourceTool(server="<name>",
  uri="deriva://catalog/{hostname}/{catalog_id}/deriva-ml/features/{table}")
```

Then read the values, choosing a **selector** for the common domain-scientist asks:

```
deriva_ml_list_feature_values(hostname, catalog_id,
  target_table="<table>", feature_name="<feature>", selector="newest")
```

- `selector="newest"` — the latest label per record (most recent annotation).
- `selector="majority_vote"` — the consensus label when multiple annotators or
  runs labeled the same record.
- omit the selector to see *all* values (every annotator's row) for a record.

For how feature values get their producing-execution link, and the full selector
catalog, see `/deriva-ml:create-feature`.

## Journey 4 — "Let me see it in the browser"

Every read above returns a per-row **`cite_url`** — a stable link that opens the
record in **Chaise**, the catalog's web UI. Surface it so a non-coder can click
through to the record instead of reading JSON:

> "Here's the record in Chaise: `<cite_url>`"

To see the whole catalog's shape (tables and how they relate) rather than one
record, use `/deriva-ml:browse-erd`.

## What this skill does NOT do

- **Create or change anything** — features (`/deriva-ml:create-feature`), datasets
  (`/deriva-ml:dataset-lifecycle`), runs (`/deriva-ml:execution-lifecycle`), assets
  (`/deriva-ml:work-with-assets`).
- **Compare multiple runs / regressions** — `/deriva-ml:compare-model-runs`.
- **The deep reproduce-this-result lineage walk** (git commit + dataset version) —
  `/deriva-ml:compare-model-runs` → "Trace an artifact's provenance".
```

- [ ] **Step 2: Verify frontmatter is valid + read-only invariant holds**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
head -4 skills/explore-results/SKILL.md            # frontmatter present: name + description
grep -nE "create_|add_|commit_|update_|delete_|release_" skills/explore-results/SKILL.md \
  | grep -v "create-feature\|create or change\|Create or change" || echo "READ-ONLY OK — no mutating tools named"
```
Expected: frontmatter shows `name: explore-results` + a `description:`; the mutating-tool grep prints "READ-ONLY OK" (the only `create-` hits are the create-feature skill name / the "does NOT create" prose).

- [ ] **Step 3: Verify every named tool + resource is real**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
for t in describe_rid get_lineage get_execution list_features list_feature_values; do
  grep -rq "deriva_ml_$t" ../deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/ && echo "$t OK" || echo "$t MISSING"; done
for r in "lineage/{rid}" "features/{table}" "dataset/{rid}" "execution/{rid}" "asset/{rid}"; do
  grep -rq "$(echo $r | sed 's/{[^}]*}/.*/')" ../deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/ && echo "resource $r OK" || echo "resource $r CHECK"; done
```
Expected: all five tools `OK`. (Resource check is best-effort — the URI shapes are copied verbatim from deriva-ml-context's resource table, the canonical source; a `CHECK` there just means the grep pattern didn't match, not that the URI is wrong — confirm against `skills/deriva-ml-context/SKILL.md`'s URI table.)

- [ ] **Step 4: Verify selector values are real**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -rn "newest\|majority_vote" ../deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/tools/feature.py | head
```
Expected: both `newest` and `majority_vote` appear as recognized selector values in the `deriva_ml_list_feature_values` tool. If `majority_vote` is spelled differently in source (e.g. `majority`), correct the skill to match the source spelling.

- [ ] **Step 5: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add skills/explore-results/SKILL.md
git commit -m "feat(explore-results): new read-only domain-scientist skill (B1-B3)"
```

---

### Task 2: create-feature trigger split + browsing pointer

**Files:**
- Modify: `skills/create-feature/SKILL.md` (the `description:` frontmatter line 3, and a body pointer)

**Interfaces:**
- Consumes: the `/deriva-ml:explore-results` skill from Task 1 (its triggers now own the read-side feature phrases).

- [ ] **Step 1: Re-narrow the create-feature description (remove read-side triggers)**

The current description claims both authoring AND reading. Read line 3 of `skills/create-feature/SKILL.md`, then replace it with this (authoring-focused; read-side phrases removed and handed to explore-results):

```
description: "ALWAYS use this skill when CREATING features or ADDING labels/annotations/values to records in DerivaML — the authoring side. Covers: the feature-vs-column decision, discovering whether a feature already exists before creating one, single vs multi-column design, creating vocabularies and features, and adding feature values with provenance. Triggers on: 'create feature', 'add labels', 'add annotations', 'annotate images', 'set up classification categories', 'ground truth labels', 'record predictions', 'what features exist' (when deciding whether to create one). For READING/BROWSING existing feature values — 'show me the labels', 'what annotations exist', 'browse the feature values', 'the consensus label' — use /deriva-ml:explore-results instead. Do NOT trigger on generic model-classification discussion ('this is a classification model', 'classification accuracy') that isn't about authoring a feature."
```

- [ ] **Step 2: Add the browsing pointer in the body**

Find the Phase that covers querying/browsing feature values (the "Phase 5: Add Feature Values" area or the discovery section). Add, near the top of the value-reading content, a pointer:

```markdown
> **Reading existing values?** Browsing labels/annotations that are already in the
> catalog — "show me the labels", "what's the consensus", a feature preview — is
> the read path, owned by `/deriva-ml:explore-results`. This skill covers *creating*
> features and *adding* values; reach for explore-results to inspect what's there.
```

- [ ] **Step 3: Verify the split**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
echo "=== create-feature description should NO LONGER carry read-browse phrases ==="
grep -n "show feature values\|browse features\|feature preview\|explore annotations\|querying or exploring" skills/create-feature/SKILL.md | grep "^3:" && echo "STILL IN DESCRIPTION — re-narrow" || echo "read-side phrases removed from description"
echo "=== explore-results pointer present in body ==="
grep -n "deriva-ml:explore-results" skills/create-feature/SKILL.md
```
Expected: "read-side phrases removed from description"; the explore-results pointer appears (description hand-off + body pointer).

- [ ] **Step 4: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add skills/create-feature/SKILL.md
git commit -m "refactor(create-feature): hand read-side feature browsing to explore-results (B2)"
```

---

### Task 3: compare-model-runs cross-link

**Files:**
- Modify: `skills/compare-model-runs/SKILL.md` (a cross-link in the "Trace an artifact's provenance" section, ~line 253)

**Interfaces:**
- Consumes: `/deriva-ml:explore-results` from Task 1.

- [ ] **Step 1: Add the bidirectional cross-link**

compare-model-runs OWNS the deep artifact-trace mechanics (the two-step workflow-URL/git-commit walk). Add, at the top of the `## Trace an artifact's provenance` section (~line 253), a one-line routing note so a domain scientist who lands here for a *simple* "where did this come from" is pointed to the lighter skill, while keeping the deep pattern here:

```markdown
> **Simple "where did this come from?"** — a domain scientist who just wants to see
> what produced an artifact (not reproduce it) starts at `/deriva-ml:explore-results`
> (Journey 2). The section below is the **developer** depth: the two-step
> lineage-walk → workflow-record pattern that recovers the git URL + commit for
> reproduction.
```

- [ ] **Step 2: Verify the cross-link**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "deriva-ml:explore-results" skills/compare-model-runs/SKILL.md
sed -n '/## Trace an artifact/,+3p' skills/compare-model-runs/SKILL.md | head -5
```
Expected: the explore-results cross-link appears right under the "Trace an artifact's provenance" heading.

- [ ] **Step 3: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add skills/compare-model-runs/SKILL.md
git commit -m "docs(compare-model-runs): cross-link explore-results for simple artifact tracing (B3)"
```

---

### Task 4: deriva-ml-context start-here row

**Files:**
- Modify: `skills/deriva-ml-context/SKILL.md` (the "Which skill do I start with?" table, ~lines 53-61)

**Interfaces:**
- Consumes: `/deriva-ml:explore-results` from Task 1.

- [ ] **Step 1: Add the domain-scientist row to the start-here table**

The table currently ends with the `| Something broke / am I up to date | … troubleshoot-execution |` row. Add a new row just before it (so read-results sits with the working-with-results situations):

```markdown
| Want to read / inspect existing results without writing code | `/deriva-ml:explore-results` |
```

Place it after the `| About to plan any of the above | … |` row and before the `| Something broke … |` row.

- [ ] **Step 2: Verify the row + that this was a TABLE edit only (no description change)**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
grep -n "Want to read / inspect existing results" skills/deriva-ml-context/SKILL.md
echo "=== confirm deriva-ml-context description: line UNCHANGED (no trigger edit for this skill) ==="
git diff skills/deriva-ml-context/SKILL.md | grep "^[-+]description:" && echo "DESCRIPTION CHANGED — revert, table only" || echo "description unchanged OK"
```
Expected: the new row is present; "description unchanged OK".

- [ ] **Step 3: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add skills/deriva-ml-context/SKILL.md
git commit -m "docs(deriva-ml-context): add explore-results to the start-here table (B1)"
```

---

### Task 5: Final cross-reference sweep + assay-note update

**Files:** none created; verification + the assay-note resolution entry.

- [ ] **Step 1: Repo-wide cross-reference + read-only sweep**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
echo "=== explore-results' outbound cross-links all name real skills ==="
for s in compare-model-runs create-feature dataset-lifecycle execution-lifecycle work-with-assets browse-erd using-deriva-mcp deriva-ml-context; do
  test -f skills/$s/SKILL.md && echo "$s OK" || echo "$s MISSING"; done
echo "=== inbound: the 3 wiring skills point at explore-results ==="
grep -rln "deriva-ml:explore-results" skills/create-feature skills/compare-model-runs skills/deriva-ml-context
echo "=== no double-fire: 'show me the labels'-class phrases now in explore-results, not create-feature description ==="
grep -c "show me the labels\|browse the feature values\|consensus label" skills/explore-results/SKILL.md
echo "=== read-only invariant holds across the new skill ==="
grep -nE "deriva_ml_(create|add|commit|update|delete|release)" skills/explore-results/SKILL.md || echo "no mutating tools in explore-results OK"
```
Expected: all 8 cross-linked skills `OK`; all 3 wiring skills appear in the inbound grep; explore-results carries the read-browse phrases; no mutating tools.

- [ ] **Step 2: Update the global-assay note with the B1-B3 resolution**

Append a "Cluster B1-B3 resolution (branch `feat/explore-results-skill`)" block to `docs/superpowers/notes/2026-06-27-global-assay.md` summarizing: new explore-results skill (4 journeys, read-only, guide-shaped); the create-feature trigger split (read→explore-results); compare-model-runs bidirectional cross-link (kept the deep walk, added the domain-scientist routing); deriva-ml-context start-here row; G1 landed (`describe_rid` now referenced); B4-B7 still deferred.

- [ ] **Step 3: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills
git add docs/superpowers/notes/2026-06-27-global-assay.md
git commit -m "docs(assay): record Cluster B1-B3 resolution (explore-results)"
```

---

## Self-Review notes

- **Spec coverage:** Task 1 = the skill (4 journeys, read-only, guide-shaped, G1's `describe_rid`); Task 2 = B2 (browsing → explore-results + create-feature trigger split); Task 3 = B3 (lineage door + delegate deep walk to compare-model-runs, no duplication); Task 4 = B1 start-here row; Task 5 = sweep + note. All success criteria mapped. ✓
- **Refinement vs spec:** the plan sharpens B3 — compare-model-runs already OWNS the deep artifact-trace section (lines 253-313) and troubleshoot-execution:34 already routes there. So explore-results gives the *domain-scientist entry* and DELEGATES the deep walk (no duplication, per Global Constraints). The spec's "lineage has no home" is corrected to "the home is developer-framed"; the fix is a light entry + bidirectional cross-link.
- **Type/name consistency:** the skill name `explore-results` and command `/deriva-ml:explore-results` are used identically across all 5 tasks; the read-browse trigger phrases removed from create-feature (Task 2) are exactly the ones explore-results claims (Task 1). ✓
- **No placeholders:** every task shows the exact frontmatter/prose to write and the exact verification commands. ✓
