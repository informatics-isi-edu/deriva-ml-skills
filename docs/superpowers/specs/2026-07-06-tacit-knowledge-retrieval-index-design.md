 A # Tacit-Knowledge Retrieval, Supersession & Index — Implementation Spec

**Date:** 2026-07-06
**Status:** Design settled; not yet implemented (no skill changes made).
**Skill affected:** `capture-tacit-knowledge` (+ its `references/entry-format.md`).
**Companion report (the *why* / theory / literature):**
[`../../reports/2026-07-06-tacit-knowledge-approach.md`](../../reports/2026-07-06-tacit-knowledge-approach.md).
This spec carries the **mechanics**; the report carries the goals, theory, and validation.
Decision IDs (D1–D13) are shared between the two documents.
**Lineage:** this whole system is the *interactional layer* from Li & Kesselman (2026),
"Reproducibility Beyond Artifacts" (19-month EyeAI deployment; Table 1 = the field
evidence — report §3.9), built as a **SCALE-conformant instance** of the vision in
Kesselman & Schuler (2026), "Building AI-Ready Scientific Data Ecosystems" (report §3.10).

## Overview

**Goal.** Let an interdisciplinary DerivaML team — and its future members, who may never
meet the original authors — reuse the *why* behind past work instead of re-deriving it or
losing it. When any team member is about to clean a dataset, train a model, or evaluate a
result, the system should notice that similar work was done before and guide them — warning
of a known dead end, or offering a reusable rule — so that hard-won rationale, dead ends,
conventions, and domain context survive handoffs, team transitions, and time. This is the
knowledge the catalog cannot store (it records *what* exists, not *why*), and it is what
makes reproducibility a matter of *understanding*, not just re-execution.

This spec designs the **tacit-knowledge layer** that meets that goal: an always-on,
LLM-mediated system that records the *why* behind a team's decisions and surfaces the
relevant prior knowledge to whoever acts next. (The full motivation, theory, and literature
grounding are in the companion report; this spec carries the mechanics.)

**How it works, in one paragraph.** Tacit knowledge is represented in the **Open Knowledge
Format (OKF)** — Markdown + YAML frontmatter — and accumulates as an append-only journal
(`tacit-knowledge.md`, an OKF `Log`; one dated entry per decision). Each entry is anchored
to what it is *about* — a catalog artifact, a *type* of artifact, a process, a team fact,
or a domain concept — so it can be found later. To keep retrieval affordable as the journal
grows, the tacit knowledge is **periodically restructured** into a related set of concepts
characterized by an **evolving set of concept tags** (a repo-local controlled vocabulary
that is refined over time so the LLM's own classification does not drift), and an **OKF
index** is generated over it to direct the LLM to the appropriate entries — the mechanism
by which the system achieves **progressive disclosure** (load only the few relevant entries,
never the whole journal). When a teammate takes an action, the system **retrieves and
quotes** the entries that bear on it; after the action, it **captures** a new entry. The
index and vocabulary **maintain and refine themselves** as a silent by-product of that
capture — no user upkeep.

**Retrieval is candidate-then-verify — so false positives are cheap and expected.** The
index does not need to be precise. Its job is to hand the LLM a small *candidate set*; the
LLM then opens and examines those entries in detail to judge which genuinely bear on the
action, and quotes only those. A false positive in the candidate set costs one extra entry
read, not a wrong answer — so the index is tuned for **recall over precision** (better to
include a marginal candidate than miss a relevant one), and the *precision* judgment lives
in the LLM's second-stage inspection, not the index. This two-stage shape is why the derived
index can stay small and approximate.

**The design in five moving parts** (each elaborated in the decisions below):
1. **The Log** — the append-only journal of *why* (D1), with structural supersession so
   stale knowledge is never served as current (D2).
2. **The derived index** — a regenerable *cache* (never a source of truth) that accelerates
   retrieval and bounds its token cost (D3–D6), rebuilt silently as a side-effect of
   capture (D7).
3. **The topic vocabulary** — a controlled term set the LLM classifies against, seeded up
   front and refined continuously (D11), organized by an **anchor taxonomy** of what an
   entry can be about (D13).
4. **The catalog connection** — the Deriva catalog as an evolving *boundary object* that
   grounds cross-discipline translation (D9) and *co-evolves* under tacit-knowledge pressure
   (D10); domain background lives in its own surface (D8).
5. **Collaboration mechanics** — the files are designed to merge cleanly across branches
   (D12).

**The one constraint that governs every decision** is stated next.

## Guiding constraint (governs every decision)

**No new upkeep task is put in front of the user.** Capture auto-fires on the action,
retrieval auto-fires on the action, the index and vocabulary self-maintain. No skill to
invoke, no prompt to answer mid-work, no tagging chore. Any decision that would add a
*routine* user task is wrong by this constraint. (Report §1.)

**What "the action" means (the trigger).** The loop fires on the same events the existing
`capture-tacit-knowledge` skill already triggers on — a DerivaML decision or operation a
future teammate would need the rationale for: running/committing an execution,
creating/splitting a dataset, creating a feature or vocabulary, changing schema, choosing a
config or hyperparameters, resolving a non-obvious bug (see that skill's description and the
SessionStart/UserPromptSubmit hooks). Retrieval fires *before* such an action; capture fires
*after* it. There is no new event model to build — the trigger is the skill's existing
firing surface; this spec adds *what happens* when it fires, not *when*.

**Scope of "zero-touch" (honest boundary).** The *operational loop* — capture, retrieval,
classification, index maintenance — is genuinely zero-touch: it happens as a by-product of
normal work. What is **not** zero-touch, and is not meant to be, is **governance of the
shared vocabulary**: confirming a proposed topic term (D11), approving a schema/CV
evolution (D10), and reviewing the initial seed (D11) are **human-gated** by design. These
are deliberate, occasional review acts, not routine upkeep — and they are gated precisely
because they change a shared artifact all future entries depend on (the same reason D10's
*transform* step is human-gated). So: the day-to-day loop asks nothing of the user; the
rare vocabulary-governance decisions ask for a yes/no on the user's own time. The
constraint forbids the former, not the latter.

## The loop, as mechanics

The retrieve-then-capture loop of the Overview, stated as the concrete operations and the
decisions that specify each:

- **Foreground (moment of action):** single append to the Log (D1). Zero index work. If
  the action overrides a prior decision, add the supersession edge + tombstone (D2).
- **Retrieval (before acting):** index for candidates + read only the un-indexed tail
  (seek to the index's `covers_through` boundary, don't scan the Log) → open & quote the
  matching entries (D5). Uses the derived index (D4/D6) but never depends on it for
  correctness. Surface only genuinely-relevant entries; when unsure, stay silent.
- **Background (silent, throttled side-effect of capture):** once the un-indexed tail
  reaches *N* entries, the *next* capture rebuilds the index whole — silent but noted in
  one line, no user action (D7). Structure can evolve flat → clustered over time without
  touching entries (D6).
- **Classification:** every entry is tagged against a repo-local topic CV via
  find-before-create (D11).

**The loop is zero-touch:** the user only states actions and makes decisions; capture,
retrieval, classification, and index maintenance are automatic consequences. (Occasional
*vocabulary-governance* review — confirming a proposed term, approving a schema/CV
evolution — is human-gated by design; see the guiding constraint's "Scope of zero-touch.")

## Decision map

- **D0** — this builds on the **existing** `capture-tacit-knowledge` skill; the entry
  format, provenance markers, `Supported by:` DAG, and consult Mode A/B are the baseline
  D1–D13 extend (not replace). The skill files are the source of record.
- **D1–D7** — core storage/retrieval mechanics.
- **D8** — domain background as a separate `type: Concept` surface.
- **D9** — the catalog is the (evolving) boundary object; controlled vocab grounds
  cross-discipline translation; the human refines the bridge at low cost.
- **D10** — the tacit log is the *desire-line* signal steering catalog schema/CV
  evolution (the return path; human-gated).
- **D11** — tk-entries are classified against a **repo-local topic CV** (not LLM
  free-tags); the sole tagger is the LLM and its drift is *temporal*; the CV is the
  noise control and the D6 index seed. Terms enter two ways: *reactive* (per-entry
  no-match) and *generative* — a corpus-wide keyword-discovery step in the rebuild that
  proposes organizing keywords mined from the accumulated entries (human-gated).
- **D12** — the tacit-knowledge files must be **trivially mergeable** (collaboration
  requirement): Log + CV union-merge via `.gitattributes`; the derived index regenerates
  post-merge (it's a cache); domain docs merge per-file. Builds on the branch-scoped
  `tk-<branch>-NNN` IDs already in entry-format.md.
- **D13** — the **anchor taxonomy**: an entry can be about a catalog artifact (instance
  RID / class / abstraction / schema entity), a **process** (anchor = the owning skill),
  a **social/team** fact, or a **domain concept** (the D8 surface). Retrieval does a
  *generalization walk*; the non-instance anchors carry the more reusable knowledge.
  Unifies D8 + D11 + the RID/type anchoring as one scheme.

D9 + D10 are the "catalog connection" (the boundary object *grounds* translation and
*evolves* under tacit-knowledge pressure); D9/D10/D11 all apply one recurring discipline
— **controlled vocab + find-before-create + human-gated extension** — at three layers.

> **Reading order note.** Decisions are numbered in the order they were made, not strict
> dependency order. Two concepts are referenced by earlier decisions before their own
> section: the **anchor taxonomy (D13)** — an entry is *about* a catalog artifact, a
> process (= a skill), a social/team fact, or a domain concept — is used by D4/D5/D6/D8/D11;
> and **mergeability (D12)** builds on D1/D4. Skim D13's three families first if the
> "Family A/B/C" and "anchor" references in D4–D11 are unfamiliar. The **file layout** and
> the two **guaranteed properties** (self-organizing; structured for discovery) are stated
> as synthesis *after* the decisions, since both assemble mechanisms from several.

## D0 — This BUILDS ON the existing `capture-tacit-knowledge` skill (baseline)

A `capture-tacit-knowledge` skill already exists and ships today; D1–D13 **extend** it,
they do not replace it. The skill and its references are the **source of record** for
everything below; the summaries here exist so this spec is self-complete, but the skill
files govern. The load-bearing conventions the spec's mechanics assume:

- **The Log is already an OKF `Log`** — `tacit-knowledge.md` at the project root, with
  `type: Log` frontmatter, a `# Tacit Knowledge` H1, and a boundary-explaining header
  paragraph, written once at file creation. (Source: `references/entry-format.md` → "File
  header"; `references/file-mechanics.md` for root placement + gitignore check + first-time
  setup. D1's "append-only OKF Log" and the File-layout root placement are *this*, not new.)
- **The entry already has a defined shape** — an `<a id="tk-[branch-]NNN">` anchor + a
  four-line header (`### tk-… — <title> ([RID](ml.cite url)) / **When:** / **By:** /
  **Supported by:**`), then a body answering **six parts**: (1) what was run/decided, (2)
  hypothesis / use case, (3) reasoning (spell out one cross-discipline term-of-art), (4)
  immediate observations *when applicable*, (5) consequences for collaborators *stated as
  facts*, (6) weighed alternatives *when genuinely considered — never fabricated*. (Source:
  `references/entry-format.md` → "What an entry contains"; worked shapes in
  `references/entry-examples.md`.)
- **Provenance markers already exist** — unmarked = stated; `[inferred from action]`,
  `[inferred from pattern]` (the riskiest), `[observed]`. The honesty rule ("if the file is
  silent, say so; do not invent a rationale") is established. The spec's D5 "surface only
  genuinely-relevant; when unsure, stay silent" is the *retrieval-side* twin of this
  *write-side* honesty rule.
- **The `Supported by:` DAG already exists** — backward-pointing antecedent links. **D2's
  `Supersedes:` is the new *forward* counterpart** the spec adds to this same family.
- **The two consult modes already exist** — **Mode A** (consult *before acting* on a
  proposed action; fire on the action, not a keyword; quote don't paraphrase; hand the
  decision back with options) and **Mode B** (forensic, "why was X chosen"). **The spec's
  retrieval loop (D5, "Retrieval before acting") is Mode A, mechanized** — the index +
  generalization walk (D13) is *how* Mode A finds what to quote. Mode B is the same
  retrieval invoked by a question instead of an action.
- **The "what doesn't belong" discipline already exists** — no catalog facts, PR/commit
  numbers, or mutable-state snapshots that rot; link the catalog, don't replicate it. This
  bounds what an *anchor* (D13) points at and what the *index* records: the tacit layer
  holds *why*, the catalog holds *what*.
- **The trigger already exists** — the skill's auto-fire description + the
  `SessionStart`/`UserPromptSubmit` hooks (`hooks/hooks.json`) are "the action" the guiding
  constraint refers to. The spec adds no new event model.

**What the spec's decisions actually change in the existing skill** (the deltas, not a
rewrite):
- `references/entry-format.md` gains the **`Supersedes:` field + tombstone** convention
  (D2) and the extended **title-handle rule** allowing a type/process/social/domain anchor,
  not only a RID (D13).
- `SKILL.md` Mode-A retrieval step gains **index-for-candidates + supersession-aware
  quote** (D5/D2), and "When to write" gains the **classify-against-topic-CV** step and the
  **silent throttled rebuild** side-effect (D11/D7).
- New companion artifacts appear (`docs/tacit-knowledge/index.md`, `topics.md`, the seed
  script, `.gitattributes`) — none of which change how a human reads or writes the Log.

Everything in D1–D13 is compatible with the existing entry shape: the additions are a
forward supersession edge, a broader anchor, a derived index, and a topic vocabulary —
layered *around* the entry, not inside it.

## D1 — Storage stays an append-only OKF `Log`, NOT a per-fact concept bundle

`tacit-knowledge.md` remains one append-only `type: Log` (project root, git-tracked;
today the workspace's own file is ~2000 lines, so scale is a live concern).

Rejected the per-fact / per-topic concept bundle because splitting by topic:
- destroys **chronology-as-structure** (the file reads top-to-bottom as the project's
  history; one experiment's story would scatter across files);
- rots the **`Supported by:` DAG** — in-document `#tk-NNN` anchor links (resolve in every
  viewer, offline, instantly) become cross-file links that break on rename;
- invites **edit-in-place**, destroying append-only integrity.

If ever partitioned for scale, partition by **time** (active file + archived eras in the
same Log format), never by topic — time-split keeps each era's story intact and crosses
files only at rare era boundaries.

## D2 — Supersession is an ADDITIVE, STRUCTURAL edge (new knowledge overrides old)

New knowledge can invalidate old, handled without mutating history:

- The **new** entry declares a forward edge: `Supersedes: tk-NNN`.
- The **old** entry gets an **appended tombstone** (never rewritten):
  `> Superseded by [tk-NNN](#tk-NNN)`.
- Forward counterpart to the existing backward-only `Supported by:` field; mirrors how
  the catalog versions rows without deleting them.

**Currency lives in the entries** (as these edges), never in a separate authoritative
"live list." "Is this still right?" is a *derived read*.

**CRITICAL — supersession must be STRUCTURAL at retrieval, not a text marker.** A
tombstone quote line + tail-grep is measurably unsafe alone: keeping both stale and
current versions serves the superseded fact **15–40 % of the time** under similarity
retrieval, and text markers are easily ignored (report §3.6, Yadav 2026). Therefore: the
supersession edge is a **queryable, structural relation the retrieval step and the
derived index both honor** — the superseded `tk-NNN` is **excluded from Moment-2
candidate results by default** (a consumer sees the superseding entry; reaches the old
one only by explicitly walking history). Event-sourcing "tombstone-in-projection":
**append-only in storage, superseded-excluded in the served view.** *Never delete, but
never serve a superseded entry as if current.*

**Second motivation (platform doctrine): the "scientific fact guardrail" vs. model
collapse.** The vision document (Kesselman & Schuler 2026, §7.3) requires that agentic
reasoning be "anchored in verifiable knowledge rather than probabilistic inference," and
names the risk: **model collapse** — unverified AI outputs compounding when fed back into
downstream reasoning/training. A superseded entry served *as current* is exactly such an
unverified input. So structural exclusion (not a mere text marker) is what the fact
guardrail requires here — a stronger reason than the retrieval-accuracy one above.

## D3 — Retrieval is REPO-LOCAL (no server index for tacit knowledge)

The catalog's `rag_search` indexes the *catalog's* semantic layer (table/column
descriptions, vocabularies, synonyms — server-side, catalog-scoped). Tacit knowledge is
different: it records the repo's model-builders' actions, lives in **git**, travels with
the code, is readable offline. Repo-author knowledge **cannot** be pushed into a catalog
index. Retrieval substrate = **files in the working tree** (grep/read). This makes the
token-cost, findability, and supersession concerns load-bearing (no server index papers
over them) → motivates D4.

## D4 — A DERIVED, whole-rebuilt OKF `type: Index` as a retrieval accelerator

An OKF `type: Index` may carry per-member **descriptive** metadata (title, description,
tags/keywords, type, relationships) but **not** *stateful* semantics ("this is the
current one"). So:

- Index rows are **descriptive only**: `{ anchor, concept keywords, tk-NNN,
  superseded-by }`.
- **The `anchor` holds a handle from the D13 anchor taxonomy** — a catalog artifact
  (instance RID, class/`*_Type` term, abstraction, or schema entity), a **process** (a
  skill name), a **social/team** fact, or a **domain concept** (a `docs/domain/` subject).
  The index row records whichever apply; a single entry may carry several (an instance *and*
  its type *and* the process that produced it). This is the field D8's domain background and
  D11's entity-free axes both feed.
- `superseded-by` **mirrors** the entry's own edge (D2) — the index does not *originate*
  currency (no stateful authority smuggled into the Index type).
- The index also carries a **candidate-terms list** — CV keywords the rebuild's
  discovery step (D11) proposes but a human has not yet confirmed. This is a *proposal
  queue*, not authority: unconfirmed terms are not used to organize, and the list is
  regenerated each rebuild like everything else in the index. Still a descriptive index
  member (it lists proposed keywords), so it stays OKF-conformant.
- Frontmatter declares it **derived**: `generated_from`, `generated_at`, `generator`,
  and **`covers_through`** — the boundary between what the index covers and the un-indexed
  tail. `covers_through` is a **pair**: the **last `tk-…` id indexed** (`covers_through.id`,
  the correctness boundary that survives merges) and the **byte offset of the end of that
  entry** in the Log (`covers_through.offset`, the fast-path that lets D5 seek straight to
  the tail). `generated_at` is retained as a human-readable timestamp and rebuild-audit
  field, but it is **not** the retrieval boundary — the id/offset pair is (D5). Keeping a
  precise structural boundary rather than a wall-clock time is what lets retrieval read
  *only* the un-indexed suffix instead of scanning the Log to find "newer" entries.
- It is **100 % regenerable, rebuilt whole, never incrementally patched** → a **cache,
  not a record**; a stale index is just "the Log has entries past `covers_through`"
  (entries whose id is not in the covered set — the tail D5 reads and D7 counts).
- **Retrieval dereferences through it to the immutable entry** — the LLM uses the index
  to find *candidates*, then opens and **quotes the actual entries**, never the index's
  keyword summary. The index is a phonebook, not the conversation.
- **Candidate-then-verify → tune for recall, not precision.** Because retrieval is
  two-stage — the index hands over a *candidate set*, and the LLM then reads those entries
  in detail to judge which genuinely apply (D5) — **false positives in the index are cheap
  and expected.** A spurious candidate costs one extra entry read, not a wrong answer, so
  the index (and the anchor/keyword match, D5/D13) is biased toward **recall over
  precision**: better to include a marginal candidate than miss a relevant one. The
  precision judgment lives in the LLM's second-stage inspection, not in the index. This is
  what lets the index stay small and approximate. *(Distinct from the point-of-need
  surfacing rule, §3.7: the LLM is generous when gathering **candidates**, but conservative
  about what it ultimately **surfaces** to the user.)*

**Correctness property: the index can only accelerate, never gate.** Delete it and
retrieval degrades to scanning the whole Log — slower, but no less correct. **One
subtlety:** the fallback is *"scan the Log **and apply the supersession filter**,"* not a
plain grep. Supersession lives in the entries themselves (D2: the `Supersedes:` edge and
tombstone), so the fallback reader must still honor it — read the entries, exclude any
carrying a tombstone (or superseded by a `Supersedes:` edge), then quote. The index makes
that filter *fast* (the `superseded-by` column is pre-computed); without the index the
same filter is computed on the fly from the entries. Either way the superseded-exclusion
of D2 holds — a plain unfiltered grep would violate it, so the fallback is *not* a plain
grep. A builder bug costs *speed*, never *correctness*. Entries remain the only authority.

## D5 — Retrieval at Moment 2: index for candidates + read only the un-indexed tail

**Primary goal: context-window economy** — "load only what is required so as not to blow
the LLM's context store" (the Claude-Code-skills sense of *progressive disclosure*: load
on demand). The index bounds the token cost of retrieval; because there is no server-side
index (D3), the entire context-economy burden falls on the repo-local layout — which is
*why* the index is load-bearing, not optional.

Two-part read along the cold/warm boundary:
- **Cold history (the bulk):** read the **index** → candidates by anchor and by keyword.
  The index is small (one flat row per entry), so this is cheap regardless of Log size —
  the front of the Log is **never scanned**; the index stands in for it.
- **Warm tail (the few un-indexed):** the entries appended to the Log *since the last
  rebuild* — the only entries the index doesn't yet cover. **The key: reading the tail
  does NOT require scanning the Log.** The Log is append-only (D1), so the un-indexed
  entries are physically **contiguous at the end of the file**, after everything the index
  already consumed. The index records where it stopped, so retrieval reads *only* from there
  to EOF:
  - **The index frontmatter carries a `covers_through` marker** — the **last `tk-…` id it
    indexed** (the correctness boundary) plus the **byte offset of end-of-that-entry** (the
    performance fast-path).
  - **Reading the tail = seek to `covers_through.offset`, read to EOF** (`tail -c +OFFSET`
    / an `open().seek()`), then split into whole entries by their `<a id="tk-…">` markers.
    Cost is **O(tail size)**, not O(Log size) — a 3-entry tail is 3 entries read whether
    the Log has 50 lines or 50,000.
  - **The id is the correctness fallback.** If the offset ever disagrees with the file
    (the pure-append assumption was violated — a `merge=union` interleaved lines, or the
    post-merge normalizer re-sorted entries by `**When:**` so the un-indexed ones are no
    longer a clean EOF suffix, D12), the reader falls back to *"entries whose `tk-…` id is
    not in the index's covered-id set."* That fallback *does* cost one Log scan, but the
    window is narrow: the normalizer runs **inside the D7 rebuild**, which regenerates the
    index and re-establishes `covers_through` against the freshly-sorted file — so the
    offset is stale only after a merge that did *not* cross the rebuild threshold (tail
    still < N). The next rebuild restores the fast-path. **Correctness never depends on the
    offset; only speed does** — and a mismatch is cheaply detected (the entry at
    `covers_through.offset` doesn't start with `covers_through.id`).
  - This is the same boundary D7 uses to decide *when* to rebuild ("count of entries past
    `covers_through` ≥ N"), so the marker does double duty: it bounds the read here and
    triggers the rebuild there. One marker, two uses.
- Then **apply the supersession filter and open-and-quote the surviving matching
  entries.** Exclude any candidate carrying a tombstone / superseded by a `Supersedes:`
  edge (D2) — for indexed candidates this is the `superseded-by` column; for warm-tail
  candidates it is read from the entry (the tail is un-indexed, so its supersession status
  isn't pre-computed). Surface only genuinely-relevant survivors; when unsure, stay silent
  (report §3.7 — a false "you've done this before" is worse than none; keep the push
  ignorable).

**Anchor match is a *generalization walk* over the D13 taxonomy, not exact-RID.** When the
user acts, retrieval matches candidates at widening scopes across the anchor families and
merges them. For an action on dataset RID `7KE` (a `Patient_Split` dataset, being created
via the `dataset-lifecycle` process):
1. **the instance** — entries anchored to RID `7KE` (what happened to *this* one);
2. **its type/class** — entries anchored to `Dataset_Type=Patient_Split` — *reusable rules*
   for every dataset of that kind ("patient-split datasets must avoid cross-split leakage");
3. **the abstraction** — entries anchored to `Dataset` generally;
4. **the process** — entries anchored to the **skill in play** (`dataset-lifecycle`) —
   how-the-work-is-done knowledge (Family B);
5. **the surrounding social/domain context** — team-fact and domain-concept entries
   (Families C) whose keywords bear on the action.
The non-instance hits (type / abstraction / process / social / domain) are typically the
*higher-value* match — a rule about a *kind*, a *process*, or the *team/domain* applies to
what the user is about to do, whereas an instance fact may not generalize. The walk needs
no new machinery: Family A uses the catalog's own typing (D9's boundary object), Family B
uses the skill vocabulary, Families C match by handle + keyword. (Precision still governs —
surface a higher-level entry only when it genuinely bears on the action; §3.7.)

The `covers_through` boundary is both the freshness handling and the staleness signal:
the tail past it is what D5 reads directly, and its *size* is the staleness signal (long
tail → rebuild is due, D7). Index = pure upside: fresh, it accelerates; stale, it degrades
gracefully to the supersession-aware Log scan (D4) — slower, never wrong.

## D6 — Index richness: START FLAT (clustering is a future, migration-free evolution)

- v1 index is **flat**: one row per entry with `anchor` (RID *or* type handle — D13),
  `concept keywords` (a flat column, *not* clustering structure), `tk-NNN`,
  `superseded-by`.
- Rationale: the **highest-value retrieval path is anchor lookup** — a flat key-value
  match (RID or type) that clustering doesn't improve. Clustering helps only the rarer
  browse-by-theme query
  and introduces non-determinism (an entry can sit under several themes; two rebuilds may
  cluster differently) in a cache that should be boring.
- Because the index is regenerable, **clustering can be added later as a layer over the
  same flat rows — no entry touched, no data migrated.** Flat-now costs nothing later.
- **D11 supplies the seed + normalization** these guardrails wanted, by construction:
  the topic CV is seeded with a hypothesized vocabulary and refined continuously (D11), so
  the rebuild groups by CV term instead of inferring clusters from noisy free-tags. If
  clustering is ever added, it groups the (small, human-reviewed) CV terms into a hierarchy
  — a judgment a human can make directly, not a statistical saturation check (there is no
  large-N regime here; see D11). Flat is sufficient for v1.

## D7 — Rebuild is a SILENT side-effect of capture; no user action, ever

The zero-touch constraint rules out a user-invocable reindex skill. The index maintains
itself by riding along on the capture that already happens:

- After `capture-tacit-knowledge` appends an entry (already zero-effort — auto-fires on
  the action), the skill **silently checks whether the un-indexed tail has reached the
  threshold**. The tail is a **count of Log entries past `covers_through`** (D4), not ID
  arithmetic: because IDs are branch-scoped (`tk-<branch>-NNN`, D12), you cannot subtract
  one `tk-…` from another. The fast path uses the *same* boundary D5 reads with — seek to
  `covers_through.offset`, read to EOF, count the entries there; the count *is* the number
  of un-indexed entries. The correctness definition behind it is *"number of entries in the
  Log whose `tk-…` id is not in the index's covered-id set ≥ N"* (the set is
  `generated_from` plus `covers_through.id`); after a merge that set simply gains the other
  branch's ids, and the offset fast-path is rebuilt on the next pass. If the count ≥ N it
  **rebuilds the index whole in the same turn** — no prompt, no permission.
- **Throttled to every *N* entries**, so a typical capture just appends; only every *N*th
  pays the rebuild. Amortized bookkeeping, not per-entry coupling.
- **The rebuild is also where corpus-wide keyword discovery runs (D11).** Since the
  rebuild already reads the whole corpus, it additionally proposes **refinements to the
  hypothesized seed vocabulary** — add/retire/split/merge terms based on what actually
  accreted — precision-biased, batched into the index's human-gated candidate-terms list
  (never blocking). No threshold (N is permanently small; see D11); discovery free-rides
  on a read that happens anyway.
- **Safe to be lazy:** D5's tail-grep means a stale index is never *wrong*, only slower.
  The rebuild needs to happen *eventually, before the tail gets slow* — which "every *N*"
  satisfies.
- **Visibility: silent but noted in one line** ("refreshed the tacit-knowledge index —
  12 new entries folded in"). Never a question or blocker; an honest breadcrumb about
  cost + a debugging aid. Mirrors capture (append is silent-but-visible).
- **Rejected: auto-commit.** Committing the regenerated index unasked cuts against
  "commit only when asked"; it travels with the next normal commit (a derived file a
  reviewer sees alongside the entries that produced it).
- **Optional belt-and-suspenders (not required, not user-facing):** a git hook or
  scheduled run *may* also rebuild — ambient, never the primary path. The capture
  side-effect alone guarantees zero-touch maintenance.

## D8 — Domain background is a separate `type: Concept` surface, not Log entries

Domain understanding is a *different knowledge type* from decision rationale — **semantic**
(slowly-refined, not tied to one dated decision) vs. **episodic** (dated, RID-anchored,
supersedable). Forcing semantic domain knowledge into the dated `tk-NNN` Log fights its
nature (report §3.4, TK-R4). *(Domain concepts are Family C of the D13 anchor taxonomy —
this bundle is where entries anchored to a domain concept live.)*

- **Decision rationale** stays in the episodic append-only Log (`type: Log`) — unchanged.
- **Domain background** goes in **`type: Concept`** OKF docs — one doc per subject, each
  *refined in place* over time (semantic), with its own index membership.
- **What goes in it — the durable background a cross-disciplinary newcomer needs to make
  sense of the project** (the know-*that* shell the Log's episodic entries assume but never
  state). One `Concept` doc per subject, across:
  - **Domain facts / confounds** — e.g. "staining varies across the two clinical sites and
    confounds any cross-site model"; "the fundus cohort under-represents Latino patients."
  - **Field methodological conventions** — e.g. "in this domain sensitivity is valued over
    specificity — a missed case is worse than a false alarm."
  - **Data-provenance context** — e.g. "these images come from a screening program, so
    they are pre-filtered in ways that bias sampling."
  - **Cross-cutting project stances** — e.g. "we favor interpretability over raw accuracy
    here because the model feeds a clinical decision."
  This is exactly the tacit knowledge that is **not about a catalog object** (cf. D11's
  entity-free axes) — which is why it cannot just be catalog metadata.
- **One retrieval loop over both.** The derived index (D4) spans both artifact types;
  Moment-2 retrieval consults both and weaves domain + decision guidance together. The
  consumer never needs to know which file a fact came from.
- **Honesty boundary:** Concept docs capture the *externalizable* domain shell and
  **point at** the tacit remainder (who practices this, what to observe), not pretend to
  contain it. **D9 makes the pointer concrete:** point at the catalog term (boundary
  object) + the human who practices it, and translate through the term's
  synonyms/description.
- **Overlap with the catalog (D9):** a controlled-vocab term's *description* IS domain
  background, authored once and shared — so a Concept doc should **link the catalog term,
  not restate it** (the same "link, don't replicate the catalog" rule the Log follows).
  The domain bundle is for *cross-cutting* understanding spanning terms with no single
  catalog home; per-term meaning lives in the vocab description, reached by RID.
- **Location (decided): its own `docs/domain/` bundle.** Every deriva-ml-skills repo
  already has a `docs/` directory (holding `docs/design/`, `docs/adr/`, …), so the domain
  bundle lives at **`docs/domain/`** — a `type: Concept` bundle with its own `index.md`.
  It gets *its own* directory rather than folding into `docs/tacit-knowledge/` (the Log's
  companions) precisely to keep the D8 distinction visible in the tree: **semantic,
  refined-in-place domain understanding is a different artifact from the episodic,
  append-only Log**. It is also distinct from `docs/design/` (which holds up-front
  *design* docs, not domain background).

## D9 — The catalog IS the boundary object; controlled vocab grounds translation; the human refines the bridge

Grounds two hand-wavy parts of the design in infrastructure that **already exists** (so
this is an extension of a pattern the codebase already commits to). Theory in report
§3.2 / §4-layer-3.

- **(a) The catalog is a boundary object** (Star & Griesemer's *repository* type; the
  shared-syntax layer Carlile's translate-step requires). `capture-tacit-knowledge`
  (SKILL.md line 17) already calls the catalog's semantic layer and the tacit file
  "complementary halves of the same problem" — D9 names that shared layer a boundary
  object.
- **(b) Controlled-vocab synonyms + descriptions GROUND the translation.** The
  `ml/vocabularies/{schema}/{vocab_name}` resource returns per-term `(name, rid,
  description, synonyms, CURIE, URI)` (`deriva-ml-context` SKILL.md line 196). **Synonyms
  bridge the words** (pathologist "blurry slide" ↔ ML engineer "low-confidence input");
  **descriptions bridge the meaning** (a citable source, not a hallucination). Rule: *the
  broker translates by resolving the reader's vocabulary against the catalog's controlled
  terms, and cites the term RID.* Carlile's "translate" with a citable ground.
- **(c) Human-in-the-loop = low-cost bridge refinement.** When translation is thin/
  uncertain (no synonym, stale description, genuine divergence), the broker **surfaces the
  gap to the human in the practice**; the fix **feeds back into the catalog** (add a
  synonym, sharpen a description) or a tacit entry. This is Answer Garden's
  escalate-and-fold-back applied to translation, and it is **already a rule for the
  sibling find-before-create case** (`semantic-awareness` SKILL.md line 25;
  `capture-tacit-knowledge` line 17). Keeps Carlile's *transform* step in human hands, at
  low cost.

Tooling: `deriva:semantic-awareness`, the `ml/vocabularies/...` resource, `add_synonym`,
`generate-descriptions`.

## D10 — The boundary object EVOLVES; the tacit log is the desire-line signal that steers it

The catalog is not static (Deriva is data-centric-evolution by design). The boundary
object **itself evolves** (schema + CV), and the **accumulated tacit knowledge steers
that evolution** — the *return path* (tacit-log → catalog), not just catalog → tacit-log.
Theory in report §4-layer-3 (desire lines; folksonomy→ontology).

- Recurring patterns in the log are **desire lines** — worn paths saying *the schema
  should gain that column, or the CV that term/synonym.* Bottom-up usage *feeds* the
  formal structure.
- **Relocates durable self-organization to the layer that can bear it:** don't ask the
  small single-team *tk-index* to self-organize into deep themes — have it **emit desire
  lines a human promotes into the catalog**, which is broad (many disciplines/projects)
  and can carry durable structure. The log stays a chronological journal.
- **Aggregate generalization of an existing rule:** `capture-tacit-knowledge` (line 17)
  + `semantic-awareness` (line 25) already say "when a name doesn't resolve, fix it in
  the catalog — don't paper over it with a tacit entry" (the *one-off* fix). D10: the
  *same* unmet distinction hit **repeatedly** is a **schema/CV-evolution signal**.
- **Already tooled:** desire-line → `/deriva-ml:schema-evolution-impact` (blast-radius
  analysis *before* the change) → `/deriva:evolve-schema` or
  `add_term`/`add_synonym`/`add_column` (the change).
- **HUMAN-GATED (Carlile transform).** Evolving the schema/CV changes the shared syntax
  everyone depends on (competing interests) — the hardest T, located in human
  negotiation. **The system SURFACES the desire line and recommends; a human decides and
  evolves.** The broker proposes ("hit this distinction 5× — consider a `Confidence_Tier`
  term / a `confidence` column"); it does **not** mutate the schema.

## D11 — tk-entries are classified against a repo-local topic CV, not free-tagged

*This is the longest decision; it has five parts, marked by the bold run-in headings
below: (1) the **motivation** (single-tagger temporal drift); (2) **term authoring** (reuse
`manage-vocabulary`); (3) the **seed** (rich hypothesized vocabulary, small N); (4) **where
the CV lives**; and (5) the **two term-supply paths** (reactive per-entry + generative
corpus-wide discovery).*

**The correction that motivates this: the only tagger is the LLM.** It writes every entry
and assigns every tag — so the human-tagger folksonomy pitfalls (personal vocab, typos,
inter-person drift) **do not apply**; a single consistent tagger avoids them. The residual
risk is **temporal drift**: with no memory of its own prior vocabulary, it tags
`confidence-filtering` today and `qc-thresholding` six months later. *That* is the noise
to design against. (Report §4 — the classification layer.)

**The fix (same discipline as D9/D10, one level in):** classify against a **tk-topic CV**
via find-before-create. When the LLM classifies an entry it runs a synonym-aware
`lookup_term`/`rag_search` against the CV *first* and reuses the matching term; it
proposes a *new* term only on no-match, and (D10 human-gating) the new-term proposal is
surfaced for a human to confirm before it enters the CV. Guy & Tonkin's "soft
intervention: suggest at entry time," done structurally. **The CV is the noise control**
and the cross-session memory the single tagger lacks.

**How a term's text is authored — reuse `manage-vocabulary`, don't reinvent.** The lookup
path above says *when* a term is created (no-match) and *who* approves it (human); the
following specifies *how the candidate term string is formed*, which the temporal-drift
argument makes load-bearing — an undisciplined term-*author* reintroduces exactly the
drift the term-*lookup* is meant to prevent. A tk-topic term is a controlled-vocabulary
term like any other, so **term authoring delegates to the existing Deriva term-naming
discipline** — `/deriva:manage-vocabulary` → `references/term-naming-strategy.md`
*(deriva-skills)* — rather than defining a parallel one. Concretely, when the LLM must
propose a new term it applies that discipline's rules:
- **One conceptual dimension per term** (orthogonal tagging) — a tk-topic term names *one*
  subject axis (`confidence-filtering`, `class-imbalance`, `stain-variance`), never a
  compound (`vehicle-confidence-filtering-for-training`).
- **Run the substitution test before creating** — list the candidate beside the closest
  existing tk-topic terms and ask "would I swap this for any of those?"; if yes, the right
  action is a **synonym on the existing term**, not a new term. This is the same
  near-duplicate guard `term-naming-strategy.md` prescribes, and it is what keeps the
  single LLM tagger from minting `qc-thresholding` when `confidence-filtering` already
  exists.
- **Naming conventions + a description** per `/deriva:entity-naming` and the
  "Term Descriptions" section — the description is what makes the term resolvable by a
  future synonym-aware lookup (and, via D9, what a cross-discipline reader translates
  through).

**Seed the CV richly with a hypothesized vocabulary — because N is permanently small.**
A single project's tacit-knowledge log is at most a few hundred entries; it will *never*
reach the web-scale N at which folksonomy structure statistically emerges from many
independent taggers. So the design does **not** start minimal and wait for structure to
appear — there is no "warm" phase to wait for. Instead it starts with a **good
hypothesized vocabulary generated up front**, and refines it continuously (below).

The LLM can author a genuinely useful starting vocabulary *before any entries exist*,
because it knows the domain — this is the LLM's prior knowledge of *what teams argue
about* substituting for the corpus statistics small-N cannot supply.

**The seed spans the D13 anchor taxonomy, because not all tacit knowledge is about a
catalog object.** Some entries *are* about a Dataset / Execution / Feature (Family A); many
are not — a process convention ("we dry-run before every sweep" — Family B), a domain fact
("staining differs across the two sites" — Family C), a tooling gotcha ("Colab OOMs above
batch 64 here"), a team decision ("the pathologist owns the QC criteria" — Family C). A
RID-centric seed would mis-serve all of the latter. So the seed spans:
- **Entity-anchored axes** — the **five DerivaML abstractions** (Dataset, Workflow,
  Execution, Feature, Asset), for entries that *are* about a catalog object. Known and
  fixed.
- **Entity-free topic axes** — recurring subjects that don't anchor to a RID, across at
  least: **decision/method** (`data-selection`, `split-strategy`, `hyperparameter-choice`,
  `feature-choice`, `dead-end`, `evaluation-metric`), **domain** (domain-specific confounds
  and cohort facts), **process/convention** (`convention`, review/QA practices),
  **tooling/environment** (`environment-gotcha`, resource limits), and **team/collaboration**
  (ownership, dispute-resolution). These carry the tacit knowledge that has no catalog home
  — and that overlaps D8 (domain background) and the honesty boundary of D9.

The seed is produced at project setup by a **bundled script** (see implementation
surfaces): a **fixed baseline** of both axis kinds — deterministic and reviewable, the
same floor every project gets — plus an **LLM per-project augmentation** that guesses
project-specific topic terms from the repo/catalog/domain context. Both are authored to
the `term-naming-strategy` discipline, and the combined set is human-reviewed before it
becomes the CV. The guess is *meant* to be wrong at the edges — continuous refinement
(below) corrects it.

**Small N is a feature, not just a limit:** because the whole term set stays small enough
for a human to read in one sitting, the human-gated review of the seed and of proposed
changes (below) is always tractable — you cannot hand-review 10,000 folksonomy tags, but
you *can* review ~30 tk-topic terms.

**Where the tk-topic CV lives (decided): repo-local, cross-linked to catalog CV.** A
small git-tracked controlled-term list at **`docs/tacit-knowledge/topics.md`** (see File
layout — repo-local and git-resident, which is what the D3-independence rationale below
requires; `docs/` is where the repo already keeps such artifacts). The LLM tags against it
**offline**; new terms are human-gated; it **seeds from and cross-links to catalog CV
terms** where they correspond but needs **no live catalog connection to classify.**
Rationale: preserves **D3** (offline, git-resident, catalog-independent) and the
tk-layer's self-sufficiency, while still getting the noise control. **Rejected:** putting
the tk-topic CV *in* the catalog (a vocabulary table) — more unified with D9/D10 but
couples classification to a live catalog connection and erodes the tk-log's git-resident
independence. The catalog CV is a **seed source + cross-reference target**, not a hard
dependency.

**Two ways a term enters the CV — reactive (per-entry) and generative (corpus-wide).**
The lookup path above is *reactive*: it proposes a term only when a *single* entry fails
to match. That is myopic — it cannot see that several entries are *collectively* about one
theme when each got a slightly different ad-hoc description. The complement is a
**generative, corpus-wide keyword-discovery step**: the LLM analyzes the *accumulated*
entries and proposes a set of **keywords that would improve concept discovery** — the
terms a future reader (or the retrieval step of D5) would actually search on to find the
relevant entries. Because N is permanently small (above), this is **not** emergence-from-
scale — it is **continuous refinement of the hypothesized seed against what actually
accretes**, which is how grounded-theory coding works in a small study anyway: you code
against a starting frame and adjust it, you do not wait for structure to appear from
nothing (Glaser & Strauss 1967). Discovery's job is to correct the seed's inevitable
mistakes at the edges: **add** a term the project turned out to need that the seed missed,
**retire** a seed term the project never used, **split** a seed term that conflated two
things, or fold a drifted near-duplicate into a synonym.

- **When it runs — every rebuild, no threshold.** The derived-index rebuild already reads
  the whole corpus; discovery is a second question asked during that same read ("given the
  current seed, what should change — what's missing, unused, or conflated?"), so it costs
  little extra. There is **no cold-start gate**, because there is no warm phase to wait
  for: refinement is useful from the first rebuild, when it is mostly pruning/adjusting the
  guess, and stays useful as entries accrete. (Halpin 2007's cold-start finding is why we
  *seed a hypothesis* rather than wait for emergence — not a threshold we honor.)
- **Chosen for retrieval value, not just description.** A discovered keyword's test is
  *"would someone search on this to find these entries?"* — findability, not merely
  descriptive accuracy. Terms are authored to the same `term-naming-strategy` discipline
  (one dimension, substitution test, description) as the per-entry path.
- **Precision-biased — err toward silence.** Discovery proposes a term only when the theme
  is *clearly recurrent*; a noisy proposal queue is itself friction (the same precision
  precondition report §3.7 places on point-of-need retrieval). Better to miss a weak theme
  than to flood the human gate.
- **Human-gated, non-blocking (preserves the guiding constraint).** Discovery *proposes*;
  it never adopts. Proposals are **queued into the derived index's candidate-terms list**
  (derived, regenerable → no authority) for the human to review on their own time; the
  system keeps working with the un-promoted terms in the meantime (an unconfirmed term
  simply isn't used to organize yet). Never a mid-work prompt — same escalate-and-review
  discipline as D10's schema desire lines.

*Relationship to the deferred concept-clustering (D6):* discovery proposes *flat CV terms*
(v1-compatible — no hierarchy needed) and is the generative slice of what the deferred
concept-clustering builder eventually does; clustering later adds the *hierarchy* over
these terms. Discovery does not require the clustered index.

**Composition:**
- **Feeds the index (D4/D6)** — the tk-topic CV *is* D6's seed scaffold and normalization
  pass; the rebuild groups by CV term, and the rebuild *also* proposes new keywords from
  the corpus (above). TK-R2's guardrails are satisfied by construction, and TK-R2's
  "self-organize over time" becomes genuinely *generative* — the term set grows from the
  corpus, not only from hand-seeding + per-entry misses.
- **Feeds D10** — a tk-topic term repeatedly *proposed-but-unmatched*, or a corpus-wide
  theme discovery surfaces, is a desire line; the human-gated candidate-terms queue IS the
  D10 promotion signal, made concrete.
- **Still human-gated** — the LLM reuses existing terms freely (syntactic boundary,
  safe); *extending* the tk-topic CV — whether from a per-entry miss or a corpus-wide
  discovery — is surfaced for human confirmation (it changes the vocabulary all future
  entries are organized by).

Tooling: `lookup_term`/`rag_search`, `add_term`/`add_synonym` (for the repo-local vocab's
catalog cross-links); term-authoring discipline from `/deriva:manage-vocabulary` →
`references/term-naming-strategy.md` and `/deriva:entity-naming` *(deriva-skills)*.

## D12 — Tacit knowledge must be trivially MERGEABLE (collaboration requirement)

**Requirement:** the system exists *to support collaboration*, so two teammates working
on parallel branches must be able to accumulate tacit knowledge independently and have it
**merge cleanly** — a merge conflict in the tacit-knowledge files is a failure of the
design, not a normal event a human should resolve by hand. Mergeability is a first-class
requirement, not an afterthought.

Two ingredients are already in place from earlier decisions:
- **Branch-scoped identifiers** (`tk-<branch>-NNN`, entry-format.md) make concurrent-branch
  entries **collision-free by construction** — distinct anchors, no renumbering. This
  solves *semantic* collision (two entries claiming the same ID).
- **Append-only + chronology-as-structure (D1)** makes new entries additive lines at the
  end of one file — the friendliest git shape (the rejected per-topic bundle would have
  been *worse* to merge).

But those leave three *textual* merge hazards, each with a decided strategy — and the
strategy maps onto the derived-vs-record distinction the design already draws:

| Artifact | Merge strategy | Rationale |
|---|---|---|
| **Log** `tacit-knowledge.md` | **union merge** (`.gitattributes` `merge=union`) | Both branches append entries at EOF (a textual conflict even though IDs don't collide); union concatenates both sides' lines automatically. Branch-scoped IDs guarantee the union is well-formed. Tombstone edits (D2) are rare mid-file edits; union keeps both tombstones harmlessly. |
| **Derived index** `docs/tacit-knowledge/index.md` | **regenerate post-merge — never hand-merge** | It is a *cache, not a record* (D4). A merged index is meaningless; a *rebuilt* one is correct given the merged Log. Mark it so conflicts don't surface — e.g. `merge=ours` + a post-merge rebuild, or exclude it from merge concern entirely and let the next capture-triggered rebuild (D7) reconcile it. **Determinism, precisely:** the *index rows* (anchor / keywords / tk-NNN / superseded-by) are a deterministic function of the merged Log — same Log in, same rows out. The *candidate-terms list* is **not** deterministic (it comes from the LLM discovery pass, D11), but that does not affect merge correctness: candidate terms carry no authority (they are proposals a human reviews), so a different candidate list after a re-merge is not a conflict, just a different set of suggestions. Because the index can only accelerate, never gate (D4), a transiently-stale post-merge index is *safe*. |
| **tk-topic CV** `docs/tacit-knowledge/topics.md` | **union merge** | *Semi-derived*: human-gated terms are real content, so it can't just be regenerated. Union keeps both branches' terms; the next rebuild's discovery pass (D11) surfaces any near-duplicates the union introduced for human merge-into-synonym — the drift-cleanup path already exists. |
| **Domain bundle** `docs/domain/` | **ordinary per-doc merge** | Separate `Concept` docs, one per subject; two people rarely edit the *same* doc, so standard file merge suffices. (If a single hot doc becomes a conflict point, split it — the bundle shape makes that cheap.) |

**Why this composes cleanly:** every strategy above is *already implied* by a prior
decision — union for the Log follows from append-only (D1); regenerate for the index
follows from cache-not-record (D4/D7); union+discovery-cleanup for the CV follows from
semi-derived + the drift pass (D11). D12 just *names the git mechanics* that were latent.

**Two honest caveats about `merge=union`:**
- **Chronological interleaving (cosmetic).** Git concatenates both hunks and does not sort
  by `**When:**`, so two branches' appended entries can end up out of strict time order.
  This is cosmetic — the `**When:**` timestamps still give the true order and the
  `Supported by:`/`Supersedes:` DAG is order-independent.
- **Possible malformed entry (not merely cosmetic) — this is why a post-merge normalizer
  is more than optional.** `merge=union` operates on *lines*, not entries: if both branches
  append starting at the same final line of the file, union can interleave the *lines* of
  two multi-line entries (e.g. splitting a fenced code block or an entry header), producing
  syntactically broken Markdown. In practice appends land at distinct EOF regions so clean
  concatenation is the norm, but the design must not *rely* on it. **Mitigation:** a
  **post-merge normalizer** (part of the D7 rebuild path) that re-parses the Log into whole
  entries by their `<a id="tk-…">` boundaries, re-emits them well-formed and sorted by
  `**When:**`, and fails loudly if an entry cannot be parsed. This handles both caveats at
  once. It is a **recommended** post-merge step, not merely a nicety — union guarantees a
  well-formed *union of lines*, and the normalizer is what restores a well-formed *union of
  entries*.

Tooling: `.gitattributes` merge drivers (`merge=union`, `merge=ours`); the D7 rebuild as
the post-merge reconciler for the index.

## D13 — The anchor taxonomy: what a tacit-knowledge entry can be *about*

An entry's **anchor** names its referent — the thing the knowledge is about, used to
retrieve it when a teammate later touches that thing. Tacit knowledge is *not* limited to
catalog objects; the anchor can be any of the following, in three families. This taxonomy
**unifies three earlier decisions** — D8's domain background, D11's entity-free axes, and
the RID/type anchoring — as facets of one scheme.

**Family A — catalog artifacts (a spectrum of specificity, all catalog-grounded):**
1. **Instance** — a specific **RID** (`dataset 7KE`). `ml.cite(rid)`, snapshot-pinned.
2. **Class of object** — a **type/name**: a `Dataset_Type` / `Workflow_Type` / `Asset_Type`
   term, a named feature, a model class. A reusable rule about a kind
   ("patient-split datasets must avoid cross-split leakage").
3. **General object** — one of the **five abstractions** (`Dataset`, `Feature`, `Model`,
   `CV`, …) when nothing narrower fits.
4. **Schema entity** — a **table, column, or CV type** in the catalog (knowledge about the
   *structure*, not the data — "the `Confidence` column is dual-purpose: GT vs prediction").
   Formally a *class* anchor pointed at a schema entity.

**Family B — process / activity (the thing a *skill* covers):**
5. **A process** — "creating a dataset," "training a model," "splitting a dataset,"
   "running a sweep" — knowledge about *how the work is done*, not about an object.
   **Anchor = the skill that owns the process** (`dataset-lifecycle`, `create-feature`,
   `execution-lifecycle`, …). The plugin's **skill set is itself a controlled vocabulary of
   processes**, so a process anchor is as stable and enumerable as a catalog CV term. This
   is what D11's entity-free "process/method" seed axis was reaching for.

**Family C — the socio-technical layer (no catalog handle at all):**
6. **Social / team facts** — group dynamics, team structure, expertise, ownership, how
   decisions get made ("the pathologist owns the QC criteria"; "label disputes go to
   consensus"; "the RSE is the only one who understands the pipeline"). Knowledge about the
   *collaboration around* the boundary object, not the object.
   > **Privacy constraint (Family C).** Social/team facts often name *individuals* and are
   > written to a **git-tracked, mergeable, team-shared** file — so unlike catalog facts
   > they carry a consent/dignity concern. Rule: record **role- and process-level** facts
   > ("QC criteria are owned by the pathology reviewer"; "label disputes go to consensus"),
   > not **evaluative or sensitive claims about a named person** ("X doesn't understand the
   > pipeline"; performance judgments). Prefer the role to the name where the role carries
   > the knowledge; a name is warranted only when the person *is* the durable fact (e.g. a
   > designated owner) and the statement is neutral. When in doubt, capture the convention,
   > not the person. This mirrors the Log's existing "not a status board / not a snapshot of
   > mutable state" discipline, extended to people. (Access control on the file itself is
   > out of scope — it inherits the repo's git permissions.)
7. **Domain concepts** — target-domain understanding (staining variance, cohort skew,
   clinical conventions). This **is the D8 domain-background content**, seen as an anchor
   kind: a domain-concept entry anchors to a subject in the `docs/domain/` bundle.

**Why the higher, non-instance anchors are often the more valuable knowledge.** A rule
about a *class*, a *process*, a *team fact*, or a *domain concept* applies to the next
thing a teammate does, whereas an instance fact may not generalize. Reusable, cross-time,
cross-discipline knowledge is exactly what the system exists to preserve.

**How it composes — no new machinery, and it validates prior decisions:**
- **Anchor field (D4)** holds a handle from *any* family; one entry may carry several (an
  instance *and* its type *and* the process that produced it).
- **Retrieval (D5)** does the **generalization walk**: an action on RID `7KE` surfaces
  instance (7KE) → type (`Patient_Split`) → abstraction (`Dataset`) hits **and** the
  process anchor of the action (e.g. the `dataset-lifecycle` skill in play). Non-catalog
  anchors (Families B/C) are matched by their handle (skill name, domain subject) plus CV
  keywords.
- **Grounded in existing vocabularies (D9):** Family A handles are catalog CV terms / RIDs;
  Family B handles are skill names (the plugin's process vocabulary); so every anchor is a
  stable, enumerable, citable handle — no free text.
- **Family C validates D3 + D8.** Social and domain knowledge have **no catalog handle**,
  which is precisely why the tacit layer is **repo-local and catalog-independent (D3)** and
  why domain background is a **separate `Concept` surface (D8)**. The anchor taxonomy
  confirms those were the right calls: a catalog-only design could not hold Families B/C.
- **Entry-format (implementation)** — the title-handle rule in `entry-format.md` currently
  assumes a RID via `ml.cite(rid)`; it must allow a handle from any family: `*_Type` term
  or abstraction (A), a skill name (B), or a `docs/domain/` subject (C).

---

## File layout (decided)

The decisions above place four artifacts. Every deriva-ml-skills repo already has a
`docs/` directory (holding `docs/design/`, `docs/adr/`, …), so all *derived and companion*
artifacts live under `docs/`; only the Log itself stays at the project root, where D1, the
SessionStart hook, and the cross-repo references require it.

| Artifact | Path | Why here |
|---|---|---|
| **The Log** | `tacit-knowledge.md` (**project root**) | D1 chronology + the SessionStart/UserPromptSubmit hooks + the plugin/MCP-prompt mirror all reference it at the root; load-bearing, do not move. |
| **Derived retrieval index** (D4) | `docs/tacit-knowledge/index.md` | Derived, human-readable companion to the Log; grouped with the CV. |
| **tk-topic CV** (D11) | `docs/tacit-knowledge/topics.md` | Small OKF controlled-term list; the Log's classification companion. |
| **Domain-background bundle** (D8) | `docs/domain/` (+ `index.md`) | A *distinct* artifact — semantic, refined-in-place — kept in its own dir so the D8 episodic-vs-semantic boundary is visible in the tree. |

(Filenames `index.md` / `topics.md` are the recommended defaults; the directory placements
are the decided part.)

## Two properties the decisions guarantee (and how)

The decisions above serve two load-bearing properties. Because the mechanisms for each are
distributed across several decisions, they are assembled here as a closing synthesis.

### The tacit knowledge is SELF-ORGANIZING

Its organizing structure is not hand-maintained; it is *re-derived from usage and refined
continuously*, through four cooperating mechanisms:

- **A rich hypothesized seed** (D11) — the organizing vocabulary starts non-empty, spanning
  entity-anchored (the five abstractions) and entity-free (process, domain, tooling, team)
  axes, generated by the seed script. Structure exists from entry one.
- **Continuous refinement** (D11) — each index rebuild re-derives the organization against
  the accreting corpus (add / retire / split / merge terms), so the structure tracks what
  is actually there.
- **Generative keyword discovery** (D11/D7) — the rebuild mines the corpus for organizing
  keywords the seed missed. This is the "structure emerges from usage" half, made concrete.
- **The catalog-evolution return path** (D10) — recurring themes surface as *desire lines*
  that promote into the catalog's own schema/CV evolution; durable structure migrates to
  the layer that can bear it.

**Precise meaning (not an overclaim):** "self-organizing" here means *re-derived-from-usage
on each rebuild*, **not** autonomous ontology discovery. Because N is permanently small
(D11), there is no folksonomy-scale emergence to wait for — it is *seed-then-refine* — and
every structural change is **human-gated** (a human confirms new/promoted terms, D10/D11).
This is *supervised* self-organization by design: the tractability of human review is
exactly what small N buys.

### The tacit knowledge is STRUCTURED for LLM discovery and use

Discovering the relevant prior entries at the moment of action, and using them, is the
*default behavior* — built into the structure at three levels:

- **Entries are anchored for lookup** — each carries a stable `tk-NNN` id, an **anchor**
  from the D13 taxonomy (a catalog artifact at any specificity, a **process** = a skill, a
  **social/team** fact, or a **domain concept** — not only a RID), and **CV keywords**
  (D4/entry-format). Retrieval is a **generalization walk**: an action surfaces entries
  about *this* instance, its *type/process*, the *abstraction*, and the surrounding
  *social/domain* context (D5/D13) — the non-instance hits are often the most valuable.
- **A derived index accelerates candidate-finding** (D4/D5) — the LLM reads the compact
  index to find *candidates* under bounded token cost, then **opens and quotes the actual
  entries** (it dereferences the index to the real entry, never quotes the index summary).
  Superseded entries are structurally excluded so only current knowledge surfaces (D2).
- **Retrieval auto-fires and is grounded** — at Moment 2 the loop fires on the *action*
  (not a keyword), quotes what it finds, and — across disciplines — translates it through
  the catalog boundary object (D9). The consumer does nothing to trigger discovery.

**Open — discovery *quality* is not yet closed-loop.** Discovery-for-*use* (Moment-2
retrieval) is fully specified. Discovery-for-*organization* (the corpus keyword pass)
relies on "precision-biased, err toward silence" + the human gate for quality, but the spec
has no *evaluation* that the discovered keywords actually **improved findability** — no
metric closing the loop from "we added these terms" back to "retrieval got better." That is
an eval concern rather than a mechanism, and is listed under *What is NOT yet decided*.

## OKF conformance summary

- `tacit-knowledge.md` → `type: Log` (unchanged; append-only). ✔ conformant.
- Supersession edges + tombstones → ordinary append-only Log content. ✔ conformant.
- Retrieval index → `type: Index` carrying **descriptive** rows only, self-declaring as
  **derived**; currency **mirrored** from entries, never originated. ✔ conformant
  (avoids the stateful-index-type overload).
- tk-topic CV → repo-local OKF controlled-term list (its own small doc), cross-linking
  catalog vocab terms by RID. ✔ conformant.

## What is NOT yet decided / out of scope

**Scope note — this is a design doc; v1 should be smaller than the full decision set.**
The full D1–D13 design describes the *target* system. A skeptical reading is right that
for a permanently-small log (a few hundred entries) the complete machinery — OKF index +
topic CV + seed script + LLM augmentation + candidate-term queue + merge drivers + domain
bundle + catalog desire-line loop — is more than a first cut needs. **A minimal v1 is:**
the append-only Log with the `Supersedes:`/tombstone convention and a supersession-aware
read (D1, D2), retrieval by scanning + the anchor convention (D5, D13), and the
`.gitattributes` merge drivers (D12). The **derived index (D3–D7)** earns its place only
once retrieval cost is *measured* to hurt (the Log is small at first; a full scan is fine
early). The **topic-CV governance, generative discovery, catalog co-evolution, and domain
bundle (D8–D11)** are the *organizing/evolution* layer — genuinely valuable but a later
phase, not day-one retrieval mechanics. The decisions are written as the coherent whole so
the later phases fit without rework; they are **not** a mandate to build all of it at once.
Implementation should stage them and let measured pain, not the spec's completeness, pull
each phase in.

- Exact **index row schema / table format** (location is decided —
  `docs/tacit-knowledge/index.md`; see File layout).
- The **fixed-baseline seed contents** the seed script ships (location
  `docs/tacit-knowledge/topics.md` and the two-axis structure — entity-anchored +
  entity-free — are decided; D11).
- Exact **threshold *N*** for the silent rebuild (mirror the "3+" commit-prompt shape, or
  tune — likely higher than 3 so rebuilds are genuinely amortized).
- Whether to ship the **optional git-hook / scheduled** belt-and-suspenders rebuild.
- **Discovery-quality evaluation (open).** The design *specifies* how keywords are
  discovered (D11) and biases for precision, but has **no closed-loop metric** confirming
  discovered keywords actually improved findability — nothing measures "did adding this
  term make the right entries easier to retrieve?" An eval concern (retrieval hit-rate on a
  held-out set of action→relevant-entry pairs before/after a rebuild), not a mechanism;
  needed to make "structured for discovery" *demonstrably* true rather than *designed* true.
- **Time-partitioning / archival** of the Log — deferred; only if the active file
  outgrows tail-grep + index. Not v1.
- **Concept-clustering** builder logic — explicitly a future evolution (D6/D11).
- The **rename** ("tacit knowledge" → decision/rationale record) — deferred; the name is
  load-bearing across the plugin, the MCP prompt mirror, and the session hooks (report
  §3.4).

## Implementation surfaces (when this proceeds)

1. **`skills/capture-tacit-knowledge/references/entry-format.md`** — add the
   `Supersedes:` field + tombstone convention (forward counterpart to `Supported by:`);
   specify that supersession is honored *structurally* at retrieval, not as a text marker
   (D2); and extend the **title-handle rule** to allow any anchor from the **D13 taxonomy**
   — a catalog artifact (`ml.cite(rid)` / `*_Type` term / abstraction / schema entity), a
   **process** (a skill name), a **social/team** fact, or a **domain concept** (a
   `docs/domain/` subject) — not only a RID.
2. **`skills/capture-tacit-knowledge/SKILL.md`** —
   (a) Mode A retrieval step → "read the index for candidates + read only the un-indexed
   tail by seeking to `covers_through.offset` (id fallback if the offset is stale),
   exclude superseded, then quote the entries; surface only genuinely-relevant ones, else
   stay silent" (D5, D2).
   (b) "When to write" gains the **silent throttled rebuild** side-effect (D7) and the
   **classify-against-the-topic-CV** step (D11). The index-builder + CV-lookup logic lives
   here or in a bundled script the skill calls — **not** a user-invocable skill.
3. **Define the derived index file** (`docs/tacit-knowledge/index.md`): `generated_from` /
   `generated_at` / `generator` / **`covers_through` (`{id, offset}` — the un-indexed-tail
   boundary D5 seeks to and D7 counts past)** frontmatter + flat rows `{ anchor, concept
   keywords, tk-NNN, superseded-by }` (the `anchor` per the D13 taxonomy) + a
   **candidate-terms list** (the human-gated keyword-discovery proposals) (D4/D5/D6/D7/D11/D13).
4. **Define the repo-local tk-topic CV file** (`docs/tacit-knowledge/topics.md`): an OKF
   controlled-term list — terms across **two axis kinds** (entity-anchored: the five
   DerivaML abstractions; entity-free: decision/method, domain, process, tooling, team —
   because not all TK is about a catalog object), optional catalog cross-links by RID, and
   human-gated extension (D11).
5. **Bundled seed script** (`skills/capture-tacit-knowledge/scripts/seed_tk_topics.py` or
   similar) — generates the initial tk-topic CV at project setup:
   - emits a **fixed baseline** of both axis kinds (deterministic, reviewable — the floor
     every project gets);
   - invokes the **LLM to augment** with project-specific topic guesses from
     repo/catalog/domain context;
   - authors every term to the `term-naming-strategy` discipline
     (`/deriva:manage-vocabulary` → `references/term-naming-strategy.md`,
     `/deriva:entity-naming` *(deriva-skills)*);
   - writes the combined set for **human review** before it becomes the CV.
   A script (not a skill) for the same reason `check_versions.py` is a script — it runs
   deterministically and its logic shouldn't rot in prose. The **fixed-baseline contents**
   are the one open item. NB: not user-invocable-in-the-loop — it runs once at setup,
   analogous to the loader templates.
6. **`.gitattributes` merge drivers (D12)** — ship/append entries so the tacit-knowledge
   files merge cleanly for collaborators:
   ```
   tacit-knowledge.md            merge=union
   docs/tacit-knowledge/topics.md merge=union
   docs/tacit-knowledge/index.md  merge=ours   # regenerated post-merge; never hand-merged
   ```
   The seed script (or project setup) writes these; the D7 rebuild is the post-merge
   reconciler for the index. Optional: a post-merge entry normalizer (sort by `**When:**`)
   if strict Log order matters.
7. **(Optional, later)** domain-background `Concept` bundle at **`docs/domain/`** (D8);
   desire-line surfacing into `schema-evolution-impact` (D10); concept-clustering builder
   (D6).
8. **Cross-reference sweep + OKF conformance check** on the new index + CV shapes.

Note: there is **no** new user-invocable skill. Earlier drafts proposed
`reindex-tacit-knowledge`; the zero-touch constraint (D7) replaced it with the silent
capture side-effect.
