# Tacit-Knowledge Retrieval-Index System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full tacit-knowledge retrieval-index design (D0–D13) — supersession edges, the anchor taxonomy, a derived retrieval index with an O(tail) un-indexed-tail read, a zero-touch silent rebuild, a repo-local topic controlled-vocabulary, a domain-background bundle, and `.gitattributes` merge drivers — as skill instructions, a bundled seed script, and conforming canonical example artifacts in the model template.

**Architecture:** The `deriva-ml-skills` plugin ships *instructions the LLM follows* (SKILL.md + references) plus *one bundled Python script* (`seed_tk_topics.py`) that scaffolds the tacit-knowledge artifacts into a consumer repo at project setup. The runtime behaviors — appending entries with supersession edges, classifying against the topic CV, rebuilding the derived index on a throttle, reading only the un-indexed tail — are *LLM procedures documented in SKILL.md and a new `references/index-and-retrieval.md`*, not compiled code (the corpus is permanently small; the "index builder" is the LLM re-reading the Log during a capture side-effect, exactly as `check_versions.py`-style scripts stay scripts but the reasoning stays in prose). The canonical *example* artifacts (a conforming Log, an `index.md`, a `topics.md`, a `docs/domain/` bundle, `.gitattributes`) live in `deriva-ml-model-template`, which every new project copies from.

**Tech Stack:** Markdown + YAML frontmatter (OKF), Python 3 (seed script, matching the `check_versions.py` `_find_uv()` minimal-PATH pattern), `uv` for running/testing, `.gitattributes` merge drivers (`merge=union`, `merge=ours`).

## Global Constraints

- **Two repos, two commit streams.** Skill machinery → `/Users/carl/GitHub/DerivaML/deriva-ml-skills`. Canonical example artifacts → `/Users/carl/GitHub/DerivaML/deriva-ml-model-template`. Never mix a skills edit and a template edit in one commit. `cd` into the target repo in every Bash call (CWD is not persistent — workspace CLAUDE.md rule).
- **Current work branch (skills repo):** `docs/tacit-knowledge-design` (already checked out; the spec + report were committed here as `b19a0ec`). Continue on this branch; do not return to `main`.
- **`uv` for everything** — `uv run pytest`, `uv run ruff check`, `uv run ruff format`, `uv run python`. Never invoke `pytest`/`ruff`/`python` directly.
- **Google-style docstrings** on every function/class in the seed script, with `Args:`/`Returns:`/`Raises:`/`Example:`.
- **No backwards-compat shims, no over-engineering** — build only what the task needs.
- **Skill descriptions are load-bearing** — the `description:` frontmatter controls auto-invocation; edit it only where a task explicitly says to, and preserve the existing under-firing-avoidance voice.
- **Scripts must handle a minimal PATH** — the seed script uses the `_find_uv()` pattern from `skills/troubleshoot-execution/scripts/check_versions.py` (try `shutil.which`, then `~/.local/bin`, `~/.cargo/bin`, `/opt/homebrew/bin`). Never assume `uv` is on PATH.
- **Exact field names from the spec (do not rename):** entry supersession = `Supersedes: tk-NNN` (forward edge) + `> Superseded by [tk-NNN](#tk-NNN)` (appended tombstone). Index frontmatter = `type: Index`, `generated_from`, `generated_at`, `generator`, `covers_through: {id, offset}`. Index rows = `{ anchor, concept keywords, tk-NNN, superseded-by }` + a `candidate-terms` list. Topic CV file = `docs/tacit-knowledge/topics.md` (`type` per OKF controlled-term list). Index file = `docs/tacit-knowledge/index.md`. Domain bundle = `docs/domain/` (+ `index.md`, `type: Concept` docs). Log stays at project-root `tacit-knowledge.md` (`type: Log`).
- **Anchor taxonomy (D13) families:** A = catalog artifacts (instance RID / class `*_Type` term or named feature / abstraction / schema entity); B = process (anchor = the owning skill name); C = socio-technical (social/team facts with the Family-C privacy constraint; domain concepts anchored to a `docs/domain/` subject).
- **The seed script is NOT user-invocable-in-the-loop** — it runs once at project setup, analogous to the loader templates. No new `/deriva-ml:` command is created by this plan (zero-touch, D7).

---

## File Structure

**Skills repo (`deriva-ml-skills`):**

| File | Create/Modify | Responsibility |
|---|---|---|
| `skills/capture-tacit-knowledge/references/entry-format.md` | Modify | Add `Supersedes:`/tombstone convention (D2); extend the title-handle rule to the full D13 anchor taxonomy. |
| `skills/capture-tacit-knowledge/references/index-and-retrieval.md` | Create | New reference: index format (D4), `covers_through` tail read + generalization walk (D5), silent throttled rebuild + normalizer (D7/D12), topic-CV classification + discovery (D11). The mechanics the SKILL.md body points at. |
| `skills/capture-tacit-knowledge/references/anchor-taxonomy.md` | Create | New reference: the D13 three-family taxonomy in full, with the Family-C privacy constraint. Referenced from entry-format.md and SKILL.md. |
| `skills/capture-tacit-knowledge/SKILL.md` | Modify | Wire supersession into Mode-A/write guidance; add the retrieval step (index + tail read, superseded-excluded); add the silent-rebuild + classify side-effects; point at the two new references + the domain bundle. |
| `skills/capture-tacit-knowledge/scripts/seed_tk_topics.py` | Create | Bundled setup script: scaffolds `tacit-knowledge.md` (OKF Log), `docs/tacit-knowledge/{topics.md,index.md}`, `docs/domain/index.md`, and `.gitattributes` merge drivers into a consumer repo; emits the fixed-baseline two-axis topic CV + invokes an LLM-augment hook; writes for human review. |
| `skills/capture-tacit-knowledge/scripts/test_seed_tk_topics.py` | Create | Tests for the seed script's pure logic (baseline CV contents, path safety, idempotence, `.gitattributes` content). |
| `skills/setup-derivaml-project/SKILL.md` (or `setup-ml-catalog`) | Modify | Add a step invoking `seed_tk_topics.py` during project setup. (Task 8 confirms which skill owns setup.) |
| `skills/validate-project-setup/SKILL.md` | Modify | Add rows validating the four tacit-knowledge artifacts + `.gitattributes` exist and conform. |

**Model-template repo (`deriva-ml-model-template`) — canonical example artifacts:**

| File | Create/Modify | Responsibility |
|---|---|---|
| `tacit-knowledge.md` | Modify | Add the OKF `type: Log` frontmatter it currently lacks; keep existing body. |
| `docs/tacit-knowledge/index.md` | Create | Canonical example derived index (`type: Index`, `covers_through`, flat rows, candidate-terms). |
| `docs/tacit-knowledge/topics.md` | Create | Canonical example topic CV (the fixed baseline the seed script ships). |
| `docs/domain/index.md` | Create | Canonical example domain `Concept` bundle root. |
| `.gitattributes` | Create | The three merge drivers. |

**Cross-repo sync (deferred to Task 10, flagged not built):** the `deriva-ml-mcp-plugin` `_CONCEPTS_GUIDE` mirror is NOT touched — this plan adds no core-abstraction change, so the skill↔prompt sync discipline is not triggered. Task 10 only *verifies* that.

---

## Task 1: Supersession convention in `entry-format.md` (D2)

**Files:**
- Modify: `skills/capture-tacit-knowledge/references/entry-format.md`

**Interfaces:**
- Produces: the `Supersedes: tk-NNN` header field + `> Superseded by [tk-NNN](#tk-NNN)` tombstone convention, referenced by SKILL.md (Task 4) and index-and-retrieval.md (Task 3).

- [ ] **Step 1: Add the `Supersedes:` field to the entry-header section.**

In `entry-format.md`, after the `**Supported by:**` subsection (ends ~line 138, before "### Walking the chain"), insert a new subsection:

```markdown
### `**Supersedes:**` — optional forward edge that overrides a prior entry

When a new decision **invalidates** an earlier one (not merely builds on it — that's
`Supported by:`), the new entry declares a forward edge and the old entry gets an
appended tombstone. This is how currency is expressed without ever rewriting history.

Two coordinated edits, both additive:

1. **On the new (superseding) entry**, add a header field:

   ```markdown
   **Supersedes:** [tk-018](#tk-018) (QC/diagnostic separation reversed — pools merged)
   ```

   Same link form as `Supported by:` — a markdown link to the superseded entry's
   anchor, plus a short parenthetical naming *what changed*. List multiple
   comma-separated if one decision retires several.

2. **On the old (superseded) entry**, append a tombstone as the last line of its body
   (never edit the entry's existing prose — append only):

   ```markdown
   > Superseded by [tk-047](#tk-047)
   ```

   The `>` blockquote makes it visually distinct; the link points *forward* to the
   entry that replaced it. The old entry's original text stays byte-for-byte intact —
   the tombstone is the only addition.

**Direction is the mirror of `Supported by:`.** `Supported by:` points backward to
antecedents; `Supersedes:` points forward to what a decision *replaces*. Together with
the tombstone's forward link, an entry knows both what it overrode and (if later
overridden) what overrode it.

**Currency lives in these edges, never in a separate "current list."** "Is this still
right?" is answered by reading the edges: an entry with a tombstone is superseded; an
entry without one is current. There is no authoritative live list to keep in sync.

**Retrieval excludes superseded entries by default — structurally, not by reading the
tombstone text.** See `references/index-and-retrieval.md` → "Supersession is structural
at retrieval": a superseded `tk-NNN` is dropped from candidate results before the LLM
ever quotes it, so stale knowledge is never served as current. The tombstone is the
human-readable breadcrumb; the *structural* exclusion (the index's `superseded-by`
column, or the on-the-fly edge scan when there's no index) is what actually protects
retrieval. A tombstone alone, relied on as a text marker, is not sufficient — under
similarity retrieval a stale entry is served 15–40% of the time when both versions
match (report §3.6). Never delete a superseded entry; never serve it as if current.
```

- [ ] **Step 2: Add `Supersedes:` to the entry-header template block.**

In the "## Entry header" section (~line 38–44), the template block currently ends with `**Supported by:**`. Add the optional field below it:

```markdown
<a id="tk-[branch-]NNN"></a>
### tk-[branch-]NNN — <short descriptive title> ([<anchor handle>](<citation URL>))
**When:** <ISO 8601 timestamp with timezone>
**By:** <display name> (<identity URI>)
**Supported by:** [tk-…](#tk-…) (parenthetical), [tk-…](#tk-…) (parenthetical)
**Supersedes:** [tk-…](#tk-…) (what changed) — *only when this entry overrides a prior one*
```

- [ ] **Step 3: Verify no contradiction with the append-only rule.**

Grep the file for "append-only" and "never rewrite" and confirm the new tombstone text ("append only", "byte-for-byte intact") is consistent — the tombstone is an *append to the old entry's body*, which the file already permits for the file as a whole; make the local wording explicit that this one appended line is the sole exception to "an entry's text doesn't change once written."

Run: `grep -n "once written\|append-only\|byte-for-byte" skills/capture-tacit-knowledge/references/entry-format.md`
Expected: the tombstone subsection and any existing "doesn't change once written" wording coexist without contradiction (the tombstone is explicitly the append-only addition).

- [ ] **Step 4: Commit.**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
git add skills/capture-tacit-knowledge/references/entry-format.md && \
git commit -m "$(cat <<'EOF'
feat(capture-tacit-knowledge): add Supersedes/tombstone convention (D2)

New knowledge overrides old via an additive forward edge (Supersedes: tk-NNN)
plus an appended tombstone on the old entry — never a rewrite. Retrieval
excludes superseded entries structurally (index-and-retrieval.md), not by
text marker.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Anchor taxonomy reference + title-rule extension (D13)

**Files:**
- Create: `skills/capture-tacit-knowledge/references/anchor-taxonomy.md`
- Modify: `skills/capture-tacit-knowledge/references/entry-format.md`

**Interfaces:**
- Consumes: nothing.
- Produces: `references/anchor-taxonomy.md` (the three-family scheme), referenced by entry-format.md's title-handle rule and by SKILL.md (Task 4) and index-and-retrieval.md (Task 3, generalization walk).

- [ ] **Step 1: Create `references/anchor-taxonomy.md`.**

```markdown
# Anchor Taxonomy — what a tacit-knowledge entry can be *about*

An entry's **anchor** names its referent — the thing the knowledge is about — and is
what retrieval matches on when a teammate later touches that thing. Tacit knowledge is
**not** limited to catalog objects. An anchor can be any of the following, in three
families. The anchor is what goes in the title parenthetical (entry-format.md) and in
the derived index's `anchor` column (index-and-retrieval.md). One entry may carry
several anchors (an instance *and* its type *and* the process that produced it).

## Family A — catalog artifacts (a spectrum of specificity)

1. **Instance** — a specific **RID** (`dataset 7KE`), rendered `ml.cite(rid)`,
   snapshot-pinned. What happened to *this one*.
2. **Class of object** — a **type/name**: a `Dataset_Type` / `Workflow_Type` /
   `Asset_Type` term, a named feature, a model class. A *reusable rule about a kind*
   ("patient-split datasets must avoid cross-split leakage"). Anchor = the type term
   (rendered via `ml.cite` on the term's RID when it has one).
3. **General object** — one of the **five abstractions** (`Dataset`, `Feature`,
   `Model`, `Workflow`, `Execution`) when nothing narrower fits.
4. **Schema entity** — a **table, column, or CV type** (knowledge about the
   *structure*, not the data — "the `Confidence` column is dual-purpose: GT vs
   prediction"). Formally a *class* anchor pointed at a schema entity.

## Family B — process / activity (the thing a *skill* covers)

5. **A process** — "creating a dataset," "training a model," "splitting a dataset,"
   "running a sweep" — knowledge about *how the work is done*, not about an object.
   **Anchor = the skill that owns the process** (`dataset-lifecycle`, `create-feature`,
   `execution-lifecycle`, …). The plugin's skill set is itself a controlled vocabulary
   of processes, so a process anchor is as stable and enumerable as a catalog CV term.
   Write the anchor as the bare skill name (no `ml.cite`; it is not a catalog RID).

## Family C — the socio-technical layer (no catalog handle at all)

6. **Social / team facts** — group dynamics, team structure, expertise, ownership, how
   decisions get made ("the pathologist owns the QC criteria"; "label disputes go to
   consensus"). Knowledge about the *collaboration around* the boundary object.

   > **Privacy constraint (Family C).** Social/team facts often name *individuals* and
   > are written to a **git-tracked, mergeable, team-shared** file — so unlike catalog
   > facts they carry a consent/dignity concern. **Rule:** record **role- and
   > process-level** facts ("QC criteria are owned by the pathology reviewer"; "label
   > disputes go to consensus"), not **evaluative or sensitive claims about a named
   > person** ("X doesn't understand the pipeline"; performance judgments). Prefer the
   > role to the name where the role carries the knowledge; a name is warranted only
   > when the person *is* the durable fact (e.g. a designated owner) and the statement
   > is neutral. When in doubt, capture the convention, not the person. This mirrors
   > the Log's "not a status board / not a snapshot of mutable state" discipline,
   > extended to people.

7. **Domain concepts** — target-domain understanding (staining variance, cohort skew,
   clinical conventions). This is the **domain-background content**; a domain-concept
   entry anchors to a subject in the **`docs/domain/`** bundle (a `type: Concept` doc).
   Per-term meaning that *does* have a catalog home (a vocab term's description) is
   linked by RID, not restated (the "link, don't replicate the catalog" rule).

## Why the non-instance anchors are often the more valuable knowledge

A rule about a *class*, a *process*, a *team fact*, or a *domain concept* applies to the
*next* thing a teammate does; an instance fact may not generalize. Reusable,
cross-time, cross-discipline knowledge is exactly what the system exists to preserve —
so when an entry could anchor at several levels, record the higher-level anchors too,
not only the instance RID.

## Every anchor is a stable, enumerable handle — never free text

- Family A handles are catalog CV terms / RIDs.
- Family B handles are skill names (the plugin's process vocabulary).
- Family C handles are `docs/domain/` subjects (domain) or short role/convention
  phrases (social) — the topic CV (`docs/tacit-knowledge/topics.md`) enumerates the
  recurring ones so they stay consistent.

This is what lets retrieval do a **generalization walk** (index-and-retrieval.md):
match the instance, then widen to its type, its abstraction, the owning process, and
the surrounding social/domain context, merging the hits.
```

- [ ] **Step 2: Extend the title-handle rule in `entry-format.md` to cite the taxonomy.**

In `entry-format.md`, the "Title includes the durable catalog handle" convention (~line 187–202) lists only catalog RID kinds. Replace the intro sentence and add the non-catalog cases. Find:

```markdown
- **Title includes the durable catalog handle in parentheses, written as a click-through markdown link** — the navigation anchor for what the entry refers to. Pick the RID a reader would use to find related artifacts, then render it via the deriva-ml citation API so the link is browser-openable and snapshot-pinned:
```

Replace with:

```markdown
- **Title includes the entry's anchor in parentheses** — the navigation handle for what the entry is *about*, drawn from the anchor taxonomy (see `references/anchor-taxonomy.md`). An anchor can be a catalog artifact (Family A), a process (Family B), or a socio-technical/domain subject (Family C) — not only a RID. When the anchor is a catalog artifact, render it as a click-through markdown link via the deriva-ml citation API so the link is browser-openable and snapshot-pinned:
```

- [ ] **Step 3: Add the non-catalog anchor cases after the catalog-RID list.**

Immediately after the existing bulleted RID-kind list (ends with the "Schema change → table RID" bullet, ~line 192), insert:

```markdown
   - Process knowledge (how the work is done) → **the owning skill name**, as bare
     text, no `ml.cite` (`### tk-047 — Convention — we always dry-run a sweep first (dataset-lifecycle)`)
   - Social/team fact → a short **role/convention phrase**, no RID
     (`### tk-048 — QC criteria owned by the pathology reviewer`) — observe the
     Family-C privacy constraint in `references/anchor-taxonomy.md`
   - Domain concept → the **`docs/domain/` subject**
     (`### tk-049 — Staining varies across the two sites (domain: staining-variance)`)

   For a catalog artifact the URL inside the markdown link comes from `ml.cite(rid)`
   (see below); for Family B/C anchors there is no citation URL — the bare handle is
   the anchor.
```

- [ ] **Step 4: Update the "entries that don't correspond to a single catalog artifact" note.**

The existing note (~line 202) says such entries can omit the parenthetical. Tighten it to point at Families B/C rather than implying "no anchor":

Find:
```markdown
   For entries that don't correspond to a single catalog artifact (conventions, recurring patterns, cross-cutting reasoning entries), the parenthetical handle can be omitted — the `tk-NNN` is sufficient identifier on its own.
```
Replace:
```markdown
   For entries that don't correspond to a single catalog artifact, prefer a Family B (process = skill name) or Family C (domain subject / role phrase) anchor from `references/anchor-taxonomy.md` — it makes the entry retrievable by the generalization walk. Only when *no* anchor from any family fits (a purely cross-cutting reasoning entry) may the parenthetical be omitted, with `tk-NNN` as the sole identifier.
```

- [ ] **Step 5: Verify cross-references resolve.**

Run: `grep -rn "anchor-taxonomy" skills/capture-tacit-knowledge/`
Expected: references from `entry-format.md` (added above) to `references/anchor-taxonomy.md`, and the file exists.

- [ ] **Step 6: Commit.**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
git add skills/capture-tacit-knowledge/references/anchor-taxonomy.md skills/capture-tacit-knowledge/references/entry-format.md && \
git commit -m "$(cat <<'EOF'
feat(capture-tacit-knowledge): add anchor taxonomy (D13) + extend title rule

Three-family anchor scheme (catalog artifact / process=skill / socio-technical)
with the Family-C privacy constraint. Entry titles may now anchor on any family,
not only a catalog RID.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Index + retrieval mechanics reference (D4, D5, D7, D11, D12)

**Files:**
- Create: `skills/capture-tacit-knowledge/references/index-and-retrieval.md`

**Interfaces:**
- Consumes: `references/entry-format.md` (Supersedes/tombstone, Task 1), `references/anchor-taxonomy.md` (Task 2).
- Produces: the index file format, the tail-read procedure, the rebuild procedure, and the classification procedure — all referenced by SKILL.md (Task 4). Defines the `covers_through: {id, offset}` frontmatter and the `{ anchor, concept keywords, tk-NNN, superseded-by }` row shape that the model-template example (Task 6) instantiates.

- [ ] **Step 1: Create `references/index-and-retrieval.md` with the index format section.**

```markdown
# Index and Retrieval Mechanics

This reference documents the *derived retrieval index* and how the LLM reads,
rebuilds, and classifies against it. It is the machinery behind SKILL.md's
retrieval and write steps. None of this is compiled code — the "index builder" is
the LLM re-reading the Log during a capture side-effect. The corpus is permanently
small (a few hundred entries), so the whole loop is a read-and-rewrite of small files.

## The derived index (`docs/tacit-knowledge/index.md`)

An OKF `type: Index` document — a **cache, not a record**. Delete it and retrieval
still works (it degrades to a supersession-aware Log scan); a stale index only slows
retrieval, never corrupts it. It is **rebuilt whole, never incrementally patched**.

### Frontmatter

```yaml
---
type: Index
title: Tacit Knowledge — retrieval index
description: Derived candidate index over tacit-knowledge.md. Cache, not record — rebuilt whole.
generated_from: tacit-knowledge.md
generated_at: <ISO 8601 timestamp of the rebuild>
generator: capture-tacit-knowledge rebuild
covers_through:
  id: tk-NNN        # the last tk-… id folded into this index (correctness boundary)
  offset: 12345     # byte offset of the END of that entry in the Log (fast-path)
---
```

`covers_through` is the boundary between what the index covers and the **un-indexed
tail** (entries appended since the last rebuild). It does double duty: retrieval seeks
to it to read only the tail (below), and the rebuild counts entries past it to decide
when to fire (D7). `generated_at` is a human-readable audit field, **not** the
retrieval boundary — the id/offset pair is.

### Rows — descriptive only

One flat row per entry (a table or list; the model-template example fixes the exact
Markdown shape). Each row carries:

- **`anchor`** — one or more handles from the anchor taxonomy
  (`references/anchor-taxonomy.md`): a catalog artifact (instance RID / `*_Type` term /
  abstraction / schema entity), a process (skill name), a social/team fact, or a domain
  subject. A single entry may list several.
- **`concept keywords`** — a flat list of topic-CV terms (`docs/tacit-knowledge/topics.md`)
  the entry was classified under. Not clustering structure — a flat column.
- **`tk-NNN`** — the entry id, the deref target.
- **`superseded-by`** — mirrors the entry's own `Supersedes:`/tombstone edge (D2). Empty
  for current entries; `tk-MMM` for a superseded one. The index does not *originate*
  currency — it copies what the entries already say.

The index also carries a **`candidate-terms` list** — topic-CV keywords the discovery
pass (below) proposes but a human has not yet confirmed. A *proposal queue*, not
authority: unconfirmed terms are not used to organize, and the list is regenerated each
rebuild like everything else. Rows are a **deterministic** function of the Log;
the candidate-terms list is **not** (it comes from the LLM discovery pass) — which is
fine, because candidate terms carry no authority.

**Rows are descriptive, never stateful.** The index is a phonebook: the LLM uses it to
find *candidates*, then opens and **quotes the actual entries**, never the index's
keyword summary.
```

- [ ] **Step 2: Add the retrieval section (D5 — tail read + generalization walk).**

Append to `index-and-retrieval.md`:

```markdown
## Retrieval at the moment of action (Mode A)

**Goal: context-window economy.** Load only what is required so as not to blow the
context store. The index bounds the token cost; the Log's front is never scanned.

Two-part read along the cold/warm boundary:

1. **Cold history (the bulk):** read the **index** → collect candidates by anchor and
   by keyword. Cheap regardless of Log size — the index stands in for the Log's front.

2. **Warm tail (the few un-indexed):** the entries appended since the last rebuild —
   the only ones the index doesn't cover. **Reading the tail does NOT require scanning
   the Log.** The Log is append-only, so the un-indexed entries are a **contiguous
   suffix at the end of the file**, after everything the index consumed:
   - **Seek to `covers_through.offset`, read to EOF** (`tail -c +OFFSET`, or an
     `open().seek(offset)`), then split into whole entries by their `<a id="tk-…">`
     markers. Cost is **O(tail size)**, not O(Log size).
   - **Correctness fallback:** if the entry at `covers_through.offset` does not start
     with `covers_through.id` (a merge interleaved lines, or the post-merge normalizer
     re-sorted entries so the tail is no longer a clean suffix — see "Merge and the
     normalizer" below), fall back to *"entries whose `tk-…` id is not in the index's
     covered-id set."* That costs one Log scan, but only in the rare post-rewrite case;
     the next rebuild restores the offset fast-path. **Correctness never depends on the
     offset; only speed does.**

3. **Apply the supersession filter, then open-and-quote the survivors.** Exclude any
   candidate that is superseded — for indexed candidates read the `superseded-by`
   column; for warm-tail candidates read the entry's tombstone/`Supersedes:` edge
   directly (the tail is un-indexed, so its supersession status isn't pre-computed).
   Surface only genuinely-relevant survivors; when unsure, **stay silent** — a false
   "you've done this before" is worse than none.

### The generalization walk (anchor matching)

Anchor match is **not** exact-RID — it widens across the anchor families and merges the
hits. For an action on dataset RID `7KE` (a `Patient_Split` dataset, created via the
`dataset-lifecycle` process):

1. **the instance** — entries anchored to `7KE` (what happened to *this* one);
2. **its type/class** — entries anchored to `Dataset_Type=Patient_Split` (reusable
   rules for that kind);
3. **the abstraction** — entries anchored to `Dataset` generally;
4. **the process** — entries anchored to the **skill in play** (`dataset-lifecycle`);
5. **the surrounding social/domain context** — team-fact and domain-concept entries
   whose keywords bear on the action.

The non-instance hits (type / abstraction / process / social / domain) are typically
the *higher-value* match. Precision still governs — surface a higher-level entry only
when it genuinely bears on the action.

## Supersession is structural at retrieval

A superseded entry is **excluded from candidate results by default** — dropped before
the LLM quotes anything. This is a structural exclusion (the `superseded-by` column, or
the on-the-fly edge scan when there's no index), **not** reliance on a reader noticing
the tombstone text. Relying on the text marker alone is measurably unsafe: under
similarity retrieval a stale entry is served 15–40% of the time when both versions
match. A consumer reaches a superseded entry only by explicitly walking history. Never
delete it; never serve it as current.

**Fallback without an index is still supersession-aware.** If the index is absent, the
fallback is *"scan the Log AND apply the supersession filter,"* not a plain grep — read
the entries, exclude any carrying a tombstone (or superseded by a `Supersedes:` edge),
then quote. A plain unfiltered grep would violate the exclusion rule.
```

- [ ] **Step 3: Add the rebuild section (D7 — silent throttled side-effect).**

Append to `index-and-retrieval.md`:

```markdown
## Rebuild — a silent side-effect of capture (no user action, ever)

The index maintains itself by riding along on the capture that already happens. There
is **no user-invocable reindex command** (zero-touch).

- After you append an entry, **silently check whether the un-indexed tail has reached
  the threshold**. The tail count is *entries past `covers_through`*: seek to
  `covers_through.offset`, read to EOF, count the `<a id="tk-…">` markers. (Correctness
  definition behind the fast path: *entries whose `tk-…` id is not in the index's
  covered-id set* — the set is `generated_from`'s entries plus `covers_through.id`.)
  IDs are branch-scoped (`tk-<branch>-NNN`), so you **cannot** subtract one id from
  another — it is a count, not id arithmetic.
- **Threshold `N` = 10.** A typical capture just appends; only every 10th un-indexed
  entry triggers a rebuild, so rebuilds are genuinely amortized. (Higher than the 3+
  commit-prompt bar on purpose.)
- If the count ≥ `N`, **rebuild the index whole in the same turn** — no prompt, no
  permission. Re-read the Log, re-emit every row, recompute `covers_through` to the last
  entry, run the discovery pass (below), and write `index.md`.
- **Visibility: silent but noted in one line** — e.g. "refreshed the tacit-knowledge
  index — 12 new entries folded in." Never a question or a blocker; an honest breadcrumb.
- **Do NOT auto-commit the rebuilt index.** It travels with the next normal commit (a
  derived file a reviewer sees alongside the entries that produced it), consistent with
  "commit only when asked."

## Merge and the normalizer (D12)

The tacit-knowledge files use `.gitattributes` merge drivers so collaborators merge
cleanly:

```
tacit-knowledge.md             merge=union
docs/tacit-knowledge/topics.md merge=union
docs/tacit-knowledge/index.md  merge=ours    # regenerated post-merge; never hand-merged
```

- **Log = union merge.** Both branches append at EOF; union concatenates both sides.
  Branch-scoped IDs guarantee the union is well-formed.
- **Index = `merge=ours` + regenerate.** A merged index is meaningless; the next
  capture-triggered rebuild reconciles it against the merged Log.
- **Topic CV = union merge.** Human-gated terms are real content, so it can't be
  regenerated; union keeps both branches' terms and the next discovery pass surfaces
  near-duplicates for human merge-into-synonym.

**Post-merge normalizer (part of the rebuild path).** `merge=union` operates on *lines*,
not entries — if both branches appended at the same final line, union can interleave the
lines of two multi-line entries. So the rebuild **re-parses the Log into whole entries
by their `<a id="tk-…">` boundaries, re-emits them well-formed and sorted by `**When:**`,
and fails loudly if an entry cannot be parsed.** Because the normalizer may re-sort
entries, the un-indexed tail is not a clean EOF suffix immediately after a merge — which
is exactly the case the retrieval offset-fallback (above) handles; the normalizer runs
inside the rebuild, which re-establishes `covers_through`, so the fast path is restored.
```

- [ ] **Step 4: Add the classification + discovery section (D11).**

Append to `index-and-retrieval.md`:

```markdown
## Classifying entries against the topic CV (D11)

Every entry is tagged with `concept keywords` drawn from a **repo-local topic CV**
(`docs/tacit-knowledge/topics.md`) — never free-tagged. The only tagger is the LLM, so
the human-tagger folksonomy pitfalls don't apply; the residual risk is **temporal
drift** (tagging `confidence-filtering` today, `qc-thresholding` in six months). The CV
is the fix.

**Reactive path (per entry).** When you classify an entry, run a synonym-aware lookup
against the topic CV (`lookup_term` / `rag_search` shape) and **reuse an existing term**
if one matches. Reuse is free (it's a syntactic boundary). If nothing matches and the
entry is clearly about a recurring theme, **propose** a new term into the index's
`candidate-terms` list — do not adopt it. Extending the CV is human-gated.

**Generative path (corpus-wide, every rebuild).** The rebuild already reads the whole
corpus, so it asks a second question: *given the current seed, what should change —
what term is missing, unused, or conflated?* It may **add** a term the project needed,
**retire** a seed term never used, **split** a conflated term, or fold a drifted
near-duplicate into a synonym. This is continuous refinement of the hypothesized seed,
not emergence-from-scale (N is permanently small). It runs every rebuild, no threshold.

- **Precision-biased — err toward silence.** Propose a term only when the theme is
  clearly recurrent; a noisy proposal queue is itself friction.
- **Human-gated, non-blocking.** Discovery *proposes* into the `candidate-terms` list;
  it never adopts. The human reviews on their own time; the system keeps working with
  un-promoted terms in the meantime. Never a mid-work prompt.
- **Chosen for retrieval value:** a discovered term's test is *"would someone search on
  this to find these entries?"* — findability, not descriptive accuracy.

**Desire-line signal (D10).** A term repeatedly proposed-but-unmatched, or a corpus-wide
theme that keeps surfacing, is a *desire line* — a signal the catalog schema/CV should
gain that term/column. The `candidate-terms` queue IS the promotion signal. Surfacing it
is in scope; **mutating the catalog is human-gated** and out of the tacit layer's hands
(route to `/deriva-ml:schema-evolution-impact` → the human decides).

Term authoring follows the `term-naming-strategy` discipline (`/deriva:manage-vocabulary`
→ `references/term-naming-strategy.md`).
```

- [ ] **Step 5: Verify internal consistency of field names.**

Run: `grep -n "covers_through\|superseded-by\|candidate-terms\|concept keywords\|generated_from" skills/capture-tacit-knowledge/references/index-and-retrieval.md`
Expected: every field name matches the Global Constraints spelling exactly (`covers_through`, `superseded-by`, `candidate-terms`, `concept keywords`, `generated_from`).

- [ ] **Step 6: Commit.**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
git add skills/capture-tacit-knowledge/references/index-and-retrieval.md && \
git commit -m "$(cat <<'EOF'
feat(capture-tacit-knowledge): add index + retrieval mechanics reference

The D4/D5/D7/D11/D12 machinery: derived type:Index with covers_through,
O(tail) un-indexed-tail read + generalization walk, silent throttled rebuild
(N=10) with post-merge normalizer, structural supersession exclusion, and
topic-CV classification + discovery. All LLM procedures, no compiled builder.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Wire the new behaviors into `SKILL.md`

**Files:**
- Modify: `skills/capture-tacit-knowledge/SKILL.md`

**Interfaces:**
- Consumes: all three references (Tasks 1–3).
- Produces: the user-facing skill body that fires the retrieval/write/rebuild behaviors and points at the references + the domain bundle.

- [ ] **Step 1: Add supersession to the "When to write" section.**

In `SKILL.md`, after the "When to write" paragraph (~line 33), add:

```markdown
**When an action overrides a prior decision, add a supersession edge.** If what you're
recording invalidates an earlier entry (not merely builds on it), declare
`**Supersedes:** [tk-NNN](#tk-NNN)` on the new entry and append `> Superseded by
[tk-MMM](#tk-MMM)` to the old one — never rewrite the old entry. See
`references/entry-format.md` → "`**Supersedes:**`". This is what keeps "is this still
right?" answerable: superseded entries are excluded from retrieval by default.
```

- [ ] **Step 2: Rewrite the Mode-A retrieval mechanics to use the index + tail read.**

In the "### Mode A: Guidance (before you act)" section (~line 37–43), after the existing "scan `tacit-knowledge.md`" paragraph, add a mechanics paragraph:

```markdown
**How to scan efficiently (don't read the whole Log).** Read the derived index
(`docs/tacit-knowledge/index.md`) for candidates by anchor and keyword, then read only
the un-indexed tail by seeking to the index's `covers_through` boundary — not a full
Log scan. Match anchors by a **generalization walk** (instance → type → abstraction →
process → social/domain), exclude superseded entries **structurally**, then quote the
survivors. Full procedure: `references/index-and-retrieval.md`. If the index is absent,
fall back to a supersession-aware Log scan (read entries, drop tombstoned ones, quote).
```

- [ ] **Step 3: Add the silent-rebuild + classify side-effects to "When to write".**

After the supersession paragraph from Step 1, add:

```markdown
**Two silent side-effects of appending an entry** (no user action, documented in
`references/index-and-retrieval.md`):
1. **Classify** the new entry against the topic CV (`docs/tacit-knowledge/topics.md`) —
   reuse an existing term via synonym-aware lookup; propose (don't adopt) a new one into
   the index's `candidate-terms` list if the theme is clearly recurrent and unmatched.
2. **Check the rebuild throttle** — if ≥ 10 entries have accumulated past the index's
   `covers_through`, rebuild `docs/tacit-knowledge/index.md` whole in the same turn and
   note it in one line ("refreshed the tacit-knowledge index — N new entries folded in").
   Never prompt; never auto-commit the rebuilt index.
```

- [ ] **Step 4: Add the anchor-taxonomy pointer where the title handle is introduced.**

The "For the entry format … see `references/entry-format.md`" line (~line 70) already points at entry-format. Add a sibling pointer right after it:

```markdown
An entry's **anchor** (what it's about — used for retrieval) can be a catalog artifact,
a process (a skill name), or a socio-technical/domain subject — not only a RID. See
[`references/anchor-taxonomy.md`](references/anchor-taxonomy.md) for the three families
and the Family-C privacy constraint on naming individuals.
```

- [ ] **Step 5: Add a domain-background pointer near the "What doesn't belong here" boundary.**

At the end of the "## What doesn't belong here" section (~line 96), add:

```markdown
**Durable domain background is a different artifact — put it in `docs/domain/`.** Facts
about the target domain that aren't tied to one dated decision (staining varies across
sites; sensitivity is valued over specificity in this field) are *semantic*, not
*episodic* — they belong in the domain-background bundle (`docs/domain/`, `type: Concept`
docs refined in place), not in a dated `tk-NNN` Log entry. A domain-concept Log entry
may *anchor* to a `docs/domain/` subject (Family C of the anchor taxonomy), but the
durable explanation lives in the Concept doc. Link the catalog term when one exists;
don't restate it.
```

- [ ] **Step 6: Verify all reference links resolve.**

Run: `grep -n "references/" skills/capture-tacit-knowledge/SKILL.md`
Expected: links to `entry-format.md`, `entry-examples.md`, `file-mechanics.md`, `anchor-taxonomy.md`, `index-and-retrieval.md` — and each target file exists:

Run: `ls skills/capture-tacit-knowledge/references/`
Expected: `anchor-taxonomy.md  entry-examples.md  entry-format.md  file-mechanics.md  index-and-retrieval.md`

- [ ] **Step 7: Commit.**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
git add skills/capture-tacit-knowledge/SKILL.md && \
git commit -m "$(cat <<'EOF'
feat(capture-tacit-knowledge): wire supersession, index retrieval, rebuild, classify

SKILL.md now fires the D2/D5/D7/D11/D13 behaviors: supersession edges on
override, index+tail retrieval with the generalization walk, silent classify
+ throttled rebuild side-effects, and pointers to the anchor-taxonomy and
domain-background bundle.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Seed script `seed_tk_topics.py` (fixed-baseline CV + scaffolding)

**Files:**
- Create: `skills/capture-tacit-knowledge/scripts/seed_tk_topics.py`
- Test: `skills/capture-tacit-knowledge/scripts/test_seed_tk_topics.py`

**Interfaces:**
- Consumes: nothing (standalone setup script).
- Produces: a CLI that scaffolds the four artifacts + `.gitattributes` into a target repo. Pure functions `fixed_baseline_topics() -> list[dict]`, `render_topics_md(topics) -> str`, `render_empty_index_md() -> str`, `render_log_frontmatter(project_name) -> str`, `render_gitattributes() -> str`, `render_domain_index_md() -> str`, and `is_gitignored(repo_root, relpath) -> bool` — all unit-tested. `main(argv)` orchestrates writes to a `--repo-root` with an `--overwrite` guard.

- [ ] **Step 1: Write failing tests for the pure render/logic functions.**

Create `skills/capture-tacit-knowledge/scripts/test_seed_tk_topics.py`:

```python
"""Tests for seed_tk_topics — pure render functions and path safety."""
import seed_tk_topics as s


def test_fixed_baseline_has_both_axis_kinds():
    topics = s.fixed_baseline_topics()
    kinds = {t["axis"] for t in topics}
    assert "entity-anchored" in kinds
    assert "entity-free" in kinds


def test_fixed_baseline_covers_five_abstractions():
    terms = {t["term"] for t in s.fixed_baseline_topics()}
    for abstraction in ("dataset", "feature", "model", "workflow", "execution"):
        assert any(abstraction in t for t in terms), abstraction


def test_fixed_baseline_covers_entity_free_axes():
    # process, domain, tooling, team — the entity-free axes (D11)
    terms = " ".join(t["term"] for t in s.fixed_baseline_topics())
    for axis_hint in ("process", "domain", "tooling", "team"):
        assert axis_hint in terms, axis_hint


def test_topics_md_is_okf_controlled_term_list():
    md = s.render_topics_md(s.fixed_baseline_topics())
    assert md.startswith("---")          # frontmatter
    assert "type:" in md
    assert "# " in md                    # a heading


def test_index_md_declares_derived_and_covers_through():
    md = s.render_empty_index_md()
    assert "type: Index" in md
    assert "generated_from: tacit-knowledge.md" in md
    assert "covers_through" in md


def test_log_frontmatter_is_okf_log():
    fm = s.render_log_frontmatter("MyProject")
    assert "type: Log" in fm
    assert "MyProject" in fm
    assert "resource:" not in fm          # intentionally omitted for a journal


def test_gitattributes_has_three_drivers():
    ga = s.render_gitattributes()
    assert "tacit-knowledge.md" in ga and "merge=union" in ga
    assert "docs/tacit-knowledge/topics.md" in ga
    assert "docs/tacit-knowledge/index.md" in ga and "merge=ours" in ga


def test_domain_index_is_concept_bundle_root():
    md = s.render_domain_index_md()
    assert "type: Concept" in md or "type: Index" in md  # bundle root is an Index over Concepts


def test_is_gitignored_detects_direct_match(tmp_path):
    (tmp_path / ".gitignore").write_text("tacit-knowledge.md\n")
    assert s.is_gitignored(str(tmp_path), "tacit-knowledge.md") is True


def test_is_gitignored_false_when_absent(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    assert s.is_gitignored(str(tmp_path), "tacit-knowledge.md") is False
```

- [ ] **Step 2: Run the tests to verify they fail (module doesn't exist yet).**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-skills/skills/capture-tacit-knowledge/scripts && uv run pytest test_seed_tk_topics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'seed_tk_topics'`.

- [ ] **Step 3: Implement `seed_tk_topics.py` — module docstring, imports, `_find_uv`.**

Create `skills/capture-tacit-knowledge/scripts/seed_tk_topics.py`:

```python
"""Scaffold the tacit-knowledge artifacts into a DerivaML project.

Run once at project setup (not user-invocable in the loop). Creates the
append-only OKF Log, the derived-index placeholder, the seed topic controlled
vocabulary, the domain-background bundle root, and the .gitattributes merge
drivers — then leaves the seed CV for human review.

The fixed baseline below is the deterministic floor every project gets. An LLM
augment step (see augment_topics, called by the invoking skill, not this script)
adds project-specific guesses; the combined set is human-reviewed before it
becomes the CV.

Example:
    $ uv run python seed_tk_topics.py --repo-root /path/to/project --project-name EyeAI
    Wrote tacit-knowledge.md, docs/tacit-knowledge/topics.md,
    docs/tacit-knowledge/index.md, docs/domain/index.md, .gitattributes.
    Review docs/tacit-knowledge/topics.md before committing.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


def _find_uv() -> str | None:
    """Locate the uv binary under a possibly-minimal PATH.

    Claude Code (especially the Desktop app) may not source shell profiles, so
    $PATH can be incomplete. Try shutil.which first, then well-known install
    locations.

    Returns:
        Absolute path to uv, or None if it cannot be found.

    Example:
        >>> _find_uv() is None or _find_uv().endswith("uv")
        True
    """
    found = shutil.which("uv")
    if found:
        return found
    for base in ("~/.local/bin", "~/.cargo/bin", "/opt/homebrew/bin", "/usr/local/bin"):
        candidate = Path(base).expanduser() / "uv"
        if candidate.exists():
            return str(candidate)
    return None
```

- [ ] **Step 4: Implement `fixed_baseline_topics()`.**

Append to `seed_tk_topics.py`:

```python
def fixed_baseline_topics() -> list[dict]:
    """Return the deterministic seed topic CV — the floor every project gets.

    Two axis kinds (D11): entity-anchored (the five DerivaML abstractions) and
    entity-free (process, domain, tooling, team — because not all tacit
    knowledge is about a catalog object).

    Returns:
        A list of {"term", "axis", "description"} dicts, authored to the
        term-naming-strategy discipline (one dimension, substitution test).

    Example:
        >>> terms = fixed_baseline_topics()
        >>> "dataset-construction" in {t["term"] for t in terms}
        True
    """
    entity_anchored = [
        ("dataset-construction", "how a dataset was assembled, split, or subsampled"),
        ("dataset-versioning", "why a dataset version was cut or pinned"),
        ("feature-design", "why a feature exists and how it is shaped"),
        ("model-configuration", "hyperparameter and architecture choices for a model"),
        ("workflow-typing", "why a workflow was classified as it was"),
        ("execution-provenance", "what an execution consumed, produced, or established"),
    ]
    entity_free = [
        ("process-convention", "a recurring 'whenever we do X we also do Y' pattern"),
        ("domain-background", "target-domain facts, confounds, and conventions"),
        ("tooling-gotcha", "a non-obvious behavior of the toolchain or platform"),
        ("team-ownership", "role/process facts about who owns or decides what"),
        ("dead-end", "an approach that was tried and abandoned, and why"),
    ]
    topics: list[dict] = []
    for term, desc in entity_anchored:
        topics.append({"term": term, "axis": "entity-anchored", "description": desc})
    for term, desc in entity_free:
        topics.append({"term": term, "axis": "entity-free", "description": desc})
    return topics
```

- [ ] **Step 5: Implement the render functions.**

Append to `seed_tk_topics.py`:

```python
def render_topics_md(topics: list[dict]) -> str:
    """Render the topic CV as an OKF controlled-term list.

    Args:
        topics: The term dicts from fixed_baseline_topics (+ any augmentation).

    Returns:
        Markdown with OKF frontmatter and one entry per term, grouped by axis.

    Example:
        >>> render_topics_md(fixed_baseline_topics()).startswith("---")
        True
    """
    lines = [
        "---",
        "type: Index",
        "title: Tacit Knowledge — topic controlled vocabulary",
        "description: >",
        "  Repo-local controlled vocabulary the LLM classifies tacit-knowledge",
        "  entries against. Human-gated: new terms are proposed into the index's",
        "  candidate-terms list and confirmed here. Cross-links catalog CV terms by RID.",
        "tags: [tacit-knowledge, vocabulary, deriva-ml]",
        "---",
        "",
        "# Tacit Knowledge — Topic Vocabulary",
        "",
        "Each entry in `tacit-knowledge.md` is classified under one or more of these",
        "terms. Reuse an existing term via synonym-aware lookup before proposing a new",
        "one; new terms are human-gated (see the index's `candidate-terms` list).",
        "",
    ]
    for axis in ("entity-anchored", "entity-free"):
        lines.append(f"## {axis}")
        lines.append("")
        for t in topics:
            if t["axis"] == axis:
                lines.append(f"- **{t['term']}** — {t['description']}")
        lines.append("")
    return "\n".join(lines)


def render_empty_index_md() -> str:
    """Render the derived-index placeholder (no entries indexed yet).

    Returns:
        Markdown OKF type:Index with covers_through pointing before the first entry.

    Example:
        >>> "type: Index" in render_empty_index_md()
        True
    """
    return "\n".join([
        "---",
        "type: Index",
        "title: Tacit Knowledge — retrieval index",
        "description: >",
        "  Derived candidate index over tacit-knowledge.md. Cache, not record —",
        "  rebuilt whole by the capture side-effect. Never hand-edit; never hand-merge.",
        "generated_from: tacit-knowledge.md",
        "generated_at: (not yet built)",
        "generator: capture-tacit-knowledge rebuild",
        "covers_through:",
        "  id: (none)",
        "  offset: 0",
        "tags: [tacit-knowledge, index, deriva-ml]",
        "---",
        "",
        "# Tacit Knowledge — Retrieval Index",
        "",
        "_No entries indexed yet. This file is rebuilt whole as a silent side-effect of",
        "capture once entries accumulate past the rebuild threshold (see",
        "`skills/capture-tacit-knowledge/references/index-and-retrieval.md`)._",
        "",
        "## Rows",
        "",
        "| anchor | concept keywords | tk-NNN | superseded-by |",
        "|---|---|---|---|",
        "",
        "## candidate-terms (proposed, awaiting human review)",
        "",
        "_none_",
        "",
    ])


def render_log_frontmatter(project_name: str) -> str:
    """Render the OKF Log frontmatter block for tacit-knowledge.md.

    Args:
        project_name: The human project name, interpolated into the title.

    Returns:
        The YAML frontmatter block plus the H1 and boundary-explaining header.

    Example:
        >>> "type: Log" in render_log_frontmatter("EyeAI")
        True
    """
    return "\n".join([
        "---",
        "type: Log",
        f"title: Tacit Knowledge — {project_name}",
        "description: >",
        "  The why behind this project's DerivaML decisions — rationale, dead ends,",
        "  and cross-discipline consequences that the catalog records but does not",
        "  explain. Append-only; each entry is a dated tk-… decision record.",
        "tags: [tacit-knowledge, provenance, deriva-ml]",
        "---",
        "",
        "# Tacit Knowledge",
        "",
        "This file records the *why* behind decisions about this project's models and",
        "data — intent and reasoning the catalog cannot store. The catalog is the source",
        "of truth for *what* exists (RIDs, configs, numbers, lineage); this file is the",
        "source of truth for *why*. Don't replicate catalog-stored facts here — link to",
        "them by RID. Append-only: never rewrite an entry (supersession is an additive",
        "edge, not an edit).",
        "",
    ])


def render_gitattributes() -> str:
    """Render the .gitattributes merge drivers for the tacit-knowledge files.

    Returns:
        Three merge-driver lines (union for Log + CV, ours for the derived index).

    Example:
        >>> "merge=union" in render_gitattributes()
        True
    """
    return "\n".join([
        "# Tacit-knowledge merge drivers (see capture-tacit-knowledge D12).",
        "# Log and topic CV union-merge (both branches append); the derived index is",
        "# regenerated post-merge, never hand-merged.",
        "tacit-knowledge.md             merge=union",
        "docs/tacit-knowledge/topics.md merge=union",
        "docs/tacit-knowledge/index.md  merge=ours",
        "",
    ])


def render_domain_index_md() -> str:
    """Render the docs/domain/ bundle root (an Index over Concept docs).

    Returns:
        Markdown OKF type:Index describing the domain-background bundle.

    Example:
        >>> "docs/domain" in render_domain_index_md() or "Concept" in render_domain_index_md()
        True
    """
    return "\n".join([
        "---",
        "type: Index",
        "title: Domain Background",
        "description: >",
        "  Semantic, refined-in-place background about the target domain — facts,",
        "  confounds, methodological conventions a cross-disciplinary newcomer needs.",
        "  One type:Concept doc per subject. Distinct from the episodic tacit-knowledge",
        "  Log and from docs/design/ up-front plans.",
        "tags: [domain, concept, deriva-ml]",
        "---",
        "",
        "# Domain Background",
        "",
        "One `type: Concept` doc per subject (e.g. `staining-variance.md`). Refined in",
        "place over time. Link catalog vocabulary-term descriptions by RID rather than",
        "restating them. A tacit-knowledge Log entry may *anchor* to a subject here",
        "(Family C of the anchor taxonomy).",
        "",
        "## Subjects",
        "",
        "_none yet_",
        "",
    ])
```

- [ ] **Step 6: Implement `is_gitignored` and `main`.**

Append to `seed_tk_topics.py`:

```python
def is_gitignored(repo_root: str, relpath: str) -> bool:
    """Check whether relpath would be ignored by the repo's .gitignore.

    Uses `git check-ignore` when git is available; falls back to a direct
    line-match against .gitignore otherwise. The Log must never be gitignored.

    Args:
        repo_root: Absolute path to the repository root.
        relpath: Path relative to repo_root to test.

    Returns:
        True if the path is ignored.

    Example:
        >>> is_gitignored("/nonexistent", "x")  # no .gitignore -> not ignored
        False
    """
    gitignore = Path(repo_root) / ".gitignore"
    if not gitignore.exists():
        return False
    target = relpath.strip().rstrip("/")
    for raw in gitignore.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.rstrip("/") == target or line == f"{target}":
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    """Scaffold the tacit-knowledge artifacts into --repo-root.

    Args:
        argv: CLI args (defaults to sys.argv[1:]).

    Returns:
        Process exit code (0 success, non-zero on refusal or error).

    Example:
        >>> main(["--repo-root", "/tmp/does-not-exist-xyz"])  # doctest: +SKIP
        2
    """
    parser = argparse.ArgumentParser(description="Seed tacit-knowledge artifacts.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--project-name", default="this project")
    parser.add_argument("--overwrite", action="store_true",
                        help="overwrite existing artifacts (default: skip, never clobber)")
    args = parser.parse_args(argv)

    root = Path(args.repo_root)
    if not root.is_dir():
        print(f"error: --repo-root {root} is not a directory", file=sys.stderr)
        return 2

    if is_gitignored(str(root), "tacit-knowledge.md"):
        print("error: tacit-knowledge.md is gitignored; fix .gitignore first "
              "(the Log must be tracked)", file=sys.stderr)
        return 2

    artifacts = {
        "tacit-knowledge.md": render_log_frontmatter(args.project_name),
        "docs/tacit-knowledge/topics.md": render_topics_md(fixed_baseline_topics()),
        "docs/tacit-knowledge/index.md": render_empty_index_md(),
        "docs/domain/index.md": render_domain_index_md(),
        ".gitattributes": render_gitattributes(),
    }
    written = []
    for rel, content in artifacts.items():
        dest = root / rel
        if dest.exists() and not args.overwrite:
            print(f"skip (exists): {rel}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        # .gitattributes may already exist with unrelated rules — append, don't clobber.
        if rel == ".gitattributes" and dest.exists() and "tacit-knowledge.md" not in dest.read_text():
            with dest.open("a") as fh:
                fh.write("\n" + content)
        else:
            dest.write_text(content)
        written.append(rel)

    if written:
        print("Wrote: " + ", ".join(written))
        print("Review docs/tacit-knowledge/topics.md before committing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Run the tests to verify they pass.**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-skills/skills/capture-tacit-knowledge/scripts && uv run pytest test_seed_tk_topics.py -v`
Expected: all tests PASS.

- [ ] **Step 8: Lint and format.**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && uv run ruff check skills/capture-tacit-knowledge/scripts/ && uv run ruff format skills/capture-tacit-knowledge/scripts/`
Expected: no lint errors; formatting applied.

- [ ] **Step 9: Smoke-test the CLI end-to-end against a temp repo.**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
TMP=$(mktemp -d) && \
uv run python skills/capture-tacit-knowledge/scripts/seed_tk_topics.py --repo-root "$TMP" --project-name SmokeTest && \
echo "--- tree ---" && find "$TMP" -type f | sort && \
echo "--- log frontmatter ---" && head -3 "$TMP/tacit-knowledge.md" && \
rm -rf "$TMP"
```
Expected: five artifacts written; `tacit-knowledge.md` opens with `---` / `type: Log`.

- [ ] **Step 10: Commit.**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
git add skills/capture-tacit-knowledge/scripts/seed_tk_topics.py skills/capture-tacit-knowledge/scripts/test_seed_tk_topics.py && \
git commit -m "$(cat <<'EOF'
feat(capture-tacit-knowledge): add seed_tk_topics.py setup script

Scaffolds the four tacit-knowledge artifacts + .gitattributes into a consumer
repo with the fixed-baseline two-axis topic CV (D11). Never clobbers existing
files; refuses if the Log is gitignored; appends to an existing .gitattributes.
Follows the check_versions.py minimal-PATH pattern.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Canonical example artifacts in the model template

**Files (model-template repo):**
- Modify: `tacit-knowledge.md`
- Create: `docs/tacit-knowledge/index.md`
- Create: `docs/tacit-knowledge/topics.md`
- Create: `docs/domain/index.md`
- Create: `.gitattributes`

**Interfaces:**
- Consumes: `seed_tk_topics.py` (Task 5) — the artifacts are generated by running it, then the Log gets its frontmatter reconciled with the existing body.
- Produces: the canonical example every new project copies from; the reference `file-mechanics.md` (Task 7) points at these.

- [ ] **Step 1: Generate the four new artifacts + `.gitattributes` by running the seed script.**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
uv run python skills/capture-tacit-knowledge/scripts/seed_tk_topics.py \
  --repo-root /Users/carl/GitHub/DerivaML/deriva-ml-model-template \
  --project-name "DerivaML Model Template"
```
Expected: `docs/tacit-knowledge/topics.md`, `docs/tacit-knowledge/index.md`, `docs/domain/index.md`, `.gitattributes` written; `tacit-knowledge.md` **skipped** (already exists — the script never clobbers).

- [ ] **Step 2: Add the OKF `type: Log` frontmatter to the existing `tacit-knowledge.md`.**

The template's `tacit-knowledge.md` currently starts with a bare `# Tacit Knowledge` H1 (no frontmatter). Prepend the OKF Log frontmatter block **above** the existing H1, keeping all existing body prose intact:

Read the current first line, then insert before it:
```markdown
---
type: Log
title: Tacit Knowledge — DerivaML Model Template
description: >
  The why behind this project's DerivaML decisions — rationale, dead ends, and
  cross-discipline consequences that the catalog records but does not explain.
  Append-only; each entry is a dated tk-… decision record.
tags: [tacit-knowledge, provenance, deriva-ml]
---

```
(Do not remove or reword the existing `# Tacit Knowledge` heading and boundary paragraph below it — only prepend the frontmatter.)

- [ ] **Step 3: Verify the template artifacts conform (OKF types present).**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-model-template && \
head -1 tacit-knowledge.md && \
grep -l "type: Log" tacit-knowledge.md && \
grep -l "type: Index" docs/tacit-knowledge/index.md docs/tacit-knowledge/topics.md docs/domain/index.md && \
cat .gitattributes
```
Expected: `tacit-knowledge.md` first line is `---`; all `type:` declarations present; `.gitattributes` shows the three drivers.

- [ ] **Step 4: Commit (model-template repo — separate commit stream).**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-model-template && \
git add tacit-knowledge.md docs/tacit-knowledge/ docs/domain/ .gitattributes && \
git commit -m "$(cat <<'EOF'
feat: add canonical tacit-knowledge artifacts (OKF Log/Index/Concept + merge drivers)

Scaffolds the tacit-knowledge retrieval-index system into the template every new
project copies from: OKF Log frontmatter on tacit-knowledge.md, the derived index,
the seed topic CV, the domain-background bundle root, and .gitattributes merge
drivers. Generated by capture-tacit-knowledge/scripts/seed_tk_topics.py.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Update `file-mechanics.md` for the new artifacts + `.gitattributes`

**Files:**
- Modify: `skills/capture-tacit-knowledge/references/file-mechanics.md`

**Interfaces:**
- Consumes: the seed script (Task 5) and the template example (Task 6).
- Produces: first-time-setup guidance that names the seed script and the four artifacts.

- [ ] **Step 1: Add a "companion artifacts" subsection after "First-time setup".**

After the numbered first-time-setup list (~line 24), insert:

```markdown
## Companion artifacts (created by the seed script)

The Log is not alone. Four companions and a merge-driver file complete the system,
all scaffolded by `scripts/seed_tk_topics.py` (run once at project setup, not
user-invocable in the loop):

| Artifact | Path | Type |
|---|---|---|
| The Log | `tacit-knowledge.md` (project root) | OKF `Log` — append-only |
| Derived retrieval index | `docs/tacit-knowledge/index.md` | OKF `Index` — cache, rebuilt whole |
| Topic CV | `docs/tacit-knowledge/topics.md` | OKF controlled-term list — human-gated |
| Domain-background bundle | `docs/domain/` (+ `index.md`) | OKF `Concept` docs — refined in place |
| Merge drivers | `.gitattributes` | `merge=union` (Log, CV) + `merge=ours` (index) |

Run it once:

```bash
uv run python \
  <deriva-ml-skills>/skills/capture-tacit-knowledge/scripts/seed_tk_topics.py \
  --repo-root . --project-name "<Project Name>"
```

It never clobbers existing files and refuses if `tacit-knowledge.md` is gitignored.
After running, **review `docs/tacit-knowledge/topics.md`** (the seed CV is a
hypothesis meant to be wrong at the edges) and commit. The canonical example of all
five artifacts lives in `deriva-ml-model-template`.

### The `.gitattributes` merge drivers matter

`merge=union` needs no extra git config (it's a built-in driver). It makes the Log and
topic CV merge cleanly when two teammates append in parallel. The index uses
`merge=ours` because it's a cache — the next capture-triggered rebuild reconciles it
against the merged Log. See `references/index-and-retrieval.md` → "Merge and the
normalizer" for why, and for the post-merge normalizer that repairs any line-level
interleaving `merge=union` can introduce.
```

- [ ] **Step 2: Update the first-time-setup list to reference the seed script.**

In the numbered list (~step 3), after "Create the file as an OKF Log document", add a note that the seed script does this plus the companions:

Find the list item that ends with "the model template's `tacit-knowledge.md` for the canonical header wording." and append:

```markdown

   In a fresh project, prefer running `scripts/seed_tk_topics.py` (see "Companion
   artifacts" below) — it creates the Log *and* the four companions in one step,
   instead of hand-creating just the Log.
```

- [ ] **Step 3: Verify the reference resolves and commit.**

Run: `grep -n "seed_tk_topics\|index-and-retrieval\|\.gitattributes" skills/capture-tacit-knowledge/references/file-mechanics.md`
Expected: references present.

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
git add skills/capture-tacit-knowledge/references/file-mechanics.md && \
git commit -m "$(cat <<'EOF'
docs(capture-tacit-knowledge): document companion artifacts + seed script in file-mechanics

Names the four companion artifacts, the .gitattributes merge drivers, and how to
run seed_tk_topics.py at project setup.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Wire the seed script into project setup + validation

**Files:**
- Modify: `skills/setup-derivaml-project/SKILL.md` **or** `skills/setup-ml-catalog/SKILL.md` (Step 1 determines which)
- Modify: `skills/validate-project-setup/SKILL.md`

**Interfaces:**
- Consumes: `seed_tk_topics.py` (Task 5), the four artifacts (Tasks 5/6).
- Produces: a setup step that runs the seed script and a validation step that checks the artifacts exist.

- [ ] **Step 1: Determine which skill owns project scaffolding.**

Run: `grep -rln "tacit-knowledge\|project setup\|scaffold\|first-time" skills/setup-derivaml-project/SKILL.md skills/setup-ml-catalog/SKILL.md skills/validate-project-setup/SKILL.md`
Then read whichever `setup-*` skill describes creating project-root files. Pick the one that already talks about creating `tacit-knowledge.md` or CLAUDE.md at setup. (Expected: `setup-derivaml-project` owns per-project scaffolding; `setup-ml-catalog` owns the catalog side. If `setup-derivaml-project` does not exist, use whichever setup skill the grep shows handling project-root files.)

- [ ] **Step 2: Add a seed-script step to the chosen setup skill.**

In the setup skill's scaffolding section, add a step:

```markdown
### Seed the tacit-knowledge system

Every DerivaML project accumulates *why*-knowledge in a tacit-knowledge system (the
append-only Log + a derived retrieval index + a topic CV + a domain-background bundle).
Scaffold all of it in one step:

```bash
uv run python \
  <deriva-ml-skills>/skills/capture-tacit-knowledge/scripts/seed_tk_topics.py \
  --repo-root . --project-name "<Project Name>"
```

Then **augment the seed topic CV with project-specific guesses**: read the repo, the
catalog's controlled vocabularies, and the project's domain, and propose 5–15
project-specific topic terms (authored to the `term-naming-strategy` discipline) into
`docs/tacit-knowledge/topics.md` under the matching axis heading. Present the combined
seed + augmentation for the user to review before committing — the CV is human-gated.
See `/deriva-ml:capture-tacit-knowledge` → `references/index-and-retrieval.md` for how
the CV is used.
```

- [ ] **Step 3: Add validation rows to `validate-project-setup`.**

In `skills/validate-project-setup/SKILL.md`, find the checklist/table of project-setup artifacts and add rows:

```markdown
| `tacit-knowledge.md` (root) | exists, tracked in git, opens with `type: Log` frontmatter | not gitignored |
| `docs/tacit-knowledge/topics.md` | exists, OKF controlled-term list, reviewed (not just the raw seed) | — |
| `docs/tacit-knowledge/index.md` | exists, `type: Index`, has `covers_through` | derived — do not hand-edit |
| `docs/domain/index.md` | exists, domain bundle root | — |
| `.gitattributes` | has `merge=union` for the Log + CV, `merge=ours` for the index | — |
```

- [ ] **Step 4: Verify and commit.**

Run: `grep -rn "seed_tk_topics\|tacit-knowledge/topics\|covers_through" skills/setup-*/SKILL.md skills/validate-project-setup/SKILL.md`
Expected: the setup step and validation rows present.

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
git add skills/setup-*/SKILL.md skills/validate-project-setup/SKILL.md && \
git commit -m "$(cat <<'EOF'
feat: wire tacit-knowledge seed script into project setup + validation

Setup runs seed_tk_topics.py and augments the topic CV with project-specific
terms (human-reviewed); validate-project-setup checks the four artifacts +
.gitattributes exist and conform.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Repo-wide cross-reference sweep + OKF conformance check

**Files:**
- Modify: any skill/reference that cross-references `capture-tacit-knowledge` with now-stale wording (found by the sweep).

**Interfaces:**
- Consumes: all prior tasks.
- Produces: a consistent cross-reference graph; no dangling links; no contradictory descriptions of retrieval.

- [ ] **Step 1: Sweep for cross-references to the tacit-knowledge system that may now be stale.**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
grep -rln "tacit-knowledge\|tacit knowledge" skills/ docs/ | grep -v "capture-tacit-knowledge/"
```
For each hit, read the surrounding context and confirm it doesn't describe the *old* retrieval model (plain grep of the whole Log, no index, no supersession). Update any that contradict the new mechanics to point at `references/index-and-retrieval.md` instead of restating.

- [ ] **Step 2: Verify no dangling reference links inside the skill.**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
for f in $(grep -rlo "references/[a-z-]*\.md" skills/capture-tacit-knowledge/); do :; done; \
grep -rho "references/[a-z-]*\.md" skills/capture-tacit-knowledge/ | sort -u | \
while read ref; do test -f "skills/capture-tacit-knowledge/$ref" && echo "OK  $ref" || echo "MISSING $ref"; done
```
Expected: every `references/*.md` link resolves to an existing file (`anchor-taxonomy.md`, `entry-examples.md`, `entry-format.md`, `file-mechanics.md`, `index-and-retrieval.md`). No `MISSING`.

- [ ] **Step 3: OKF conformance spot-check on the field names across all new files.**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
echo "=== index frontmatter fields ===" && \
grep -rn "covers_through\|generated_from\|superseded-by\|candidate-terms\|type: Index\|type: Log\|type: Concept" \
  skills/capture-tacit-knowledge/ && \
echo "=== template ===" && \
grep -rn "covers_through\|type: Index\|type: Log\|type: Concept" /Users/carl/GitHub/DerivaML/deriva-ml-model-template/docs /Users/carl/GitHub/DerivaML/deriva-ml-model-template/tacit-knowledge.md
```
Expected: field names spelled identically everywhere (matching Global Constraints); no `covers-through`/`superseded_by`/`candidate_terms` variants.

- [ ] **Step 4: Commit any sweep fixes.**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
git add -A skills/ docs/ && \
git commit -m "$(cat <<'EOF'
docs: cross-reference sweep + OKF conformance for tacit-knowledge system

Updated stale cross-references to point at the new index-and-retrieval mechanics;
verified every references/*.md link resolves and OKF field names are consistent.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```
(If the sweep found nothing to change, skip the commit and note "no stale references found.")

---

## Task 10: Verify the cross-repo sync discipline is NOT triggered

**Files:**
- Read-only: `../deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/prompts.py`, `skills/deriva-ml-context/SKILL.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a confirmation (no edit) that this plan added no core-abstraction change requiring the `_CONCEPTS_GUIDE` ↔ `deriva-ml-context` mirror update.

- [ ] **Step 1: Confirm no change to the five core abstractions or the concepts guide.**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && \
git diff main...docs/tacit-knowledge-design --stat -- skills/deriva-ml-context/
```
Expected: **no output** (the `deriva-ml-context` skill was not touched). If it *was* touched, re-read the workspace CLAUDE.md "Cross-Repo Sync" section and mirror the change into `../deriva-ml-mcp-plugin/.../prompts.py::_CONCEPTS_GUIDE`. Otherwise, the sync discipline is not triggered — record that in the final report and do nothing.

- [ ] **Step 2: Final full-suite check (skills repo).**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && uv run pytest && uv run ruff check skills/capture-tacit-knowledge/scripts/`
Expected: seed-script tests pass; no lint errors. (There is no repo-wide test suite for Markdown skills; the seed script is the only code.)

- [ ] **Step 3: Summarize the branch state.**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git log --oneline main..docs/tacit-knowledge-design && echo "--- template ---" && cd /Users/carl/GitHub/DerivaML/deriva-ml-model-template && git log --oneline -5`
Expected: the skills-repo branch shows the spec/report commit plus Tasks 1–9; the template repo shows the Task-6 commit. No push yet — that's a separate user decision.

---

## Self-Review notes (author)

- **Spec coverage:** D0 (baseline skill) = existing SKILL.md, extended by Tasks 1/4. D1 (append-only Log) = existing + Task 6 frontmatter. D2 (supersession) = Task 1. D3 (repo-local, no server index) = documented in Task 3's retrieval section (no code needed). D4 (derived index) = Task 3 format + Task 5/6 example. D5 (tail read + walk) = Task 3. D6 (start flat) = Task 3 flat rows + Task 5 render. D7 (silent rebuild) = Task 3 + Task 4. D8 (domain bundle) = Task 5 `docs/domain/` + Task 4 pointer. D9/D10 (boundary object, desire lines) = Task 3 classification/desire-line section. D11 (topic CV) = Task 3 + Task 5 seed. D12 (mergeable) = Task 3 merge section + Task 5 `.gitattributes` + Task 6/7. D13 (anchor taxonomy) = Task 2. File layout = Tasks 5/6. Setup + validation = Task 8. Cross-repo sync = Task 10 (verify-only).
- **Threshold N** was left "likely higher than 3" in the spec; **fixed at 10** here (a decision the plan makes explicit, per the spec's invitation to tune).
- **Belt-and-suspenders git-hook rebuild** (spec open item) is **NOT built** — the spec marks it optional/not-required and the zero-touch capture side-effect suffices. Explicitly out of scope.
- **Discovery-quality eval** (spec open item) is **NOT built** — it's an eval concern, not a mechanism; out of scope for this pass.
- **Concept-clustering builder** (D6 future) is **NOT built** — flat index only, per spec.
- **The rename** ("tacit knowledge" → decision record) is **NOT done** — deferred, load-bearing name.
