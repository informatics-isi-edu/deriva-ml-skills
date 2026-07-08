---
name: capture-tacit-knowledge
description: "ALWAYS use this when a DerivaML experiment decision is being made, acted on, or asked about — and treat it as a STANDING trigger across the whole session, not a one-time check. The failure mode to beat is under-firing: the user almost never says 'record this' or 'why' — they just take an action or propose one, and the moment slips by. So fire on the ACTION, not on any keyword. Three triggers: (1) WRITE — fire right after YOU or the user just did something a future teammate would need the rationale for: ran/committed an execution, created/split/subsampled a dataset, created a feature or vocabulary, changed schema, chose or changed hyperparameters or a config, picked one approach over another, or resolved a bug with a non-obvious fix. Concrete tells: 'that fixed it…', 'ok that worked, moving on', 'let's use X instead of Y', 'bump … to …', 'going to split/train/register …'. Fire even when the choice felt obvious or routine. (2) GUIDANCE — fire BEFORE you execute or recommend a proposed action (add a feature, change a config, split a dataset, train a model, pick a preset); consult tacit-knowledge.md first because prior project experience may bear on whether it'll work. (3) FORENSIC — fire when asked 'why was X chosen', 'have we tried Y', 'what did we learn from Z', or indirect variants ('is this config still right?', 'should we still be using this?', 'why is it pinned to …?'), or when orienting to the project; consult before answering and say so if the file is silent. Do NOT fire for routine lookups, generic how-does-deriva-work questions, or pure tooling chores (reformatting, running tests, version bumps) that carry no experiment rationale."
user-invocable: false
---

# Capture and Consult Tacit Knowledge

`tacit-knowledge.md` (project root) is the project's accumulating record of **tacit knowledge** — the *why* behind its models and data that the catalog cannot store. Tacit knowledge (experience-earned, context-dependent, hard to codify) can't be fully written down; what this file captures is its **externalizable shell** — the decisions made, the alternatives rejected, and the reasoning a future teammate would otherwise re-learn the hard way. The catalog is the source of truth for *what* exists (RIDs, configs, numbers, lineage); this file is the source of truth for *why*. The division is load-bearing and runs through everything below: **anything the catalog can go stale on, the catalog should answer — this file links to it, never replicates it.** Entries connect (a follow-up run references prior runs by RID), so the file reads top-to-bottom as the history of how the project's understanding evolved.

It is also the **cross-domain bridge** on multidisciplinary teams: the ML designer writes entries the domain expert needs to *understand* (and vice versa) — decisions and rationale in language the other side can read, not directives for them to act on. What the reader does with that understanding is their call, in their own time.

Its complement is the catalog's **semantic-awareness layer** (`/deriva:semantic-awareness` — controlled vocabularies, descriptions, RIDs, synonyms, `rag_search`). Semantic awareness answers *what exists and what is it called*; this file answers *why does it exist*. They keep each other sharp: stable catalog names/RIDs are what let `tk-042` still resolve years later, and an entry recording *"we rejected the vehicles-only subset because variance dominated the signal"* is what stops a future `rag_search` from re-creating it. When a name doesn't resolve, fix it in the catalog (better description, synonym, rename) — don't paper over it with an entry; when an entry is just restating a catalog fact, link the catalog instead.

## What this file is not

Every entry is a **past-tense, settled record**. If something might change tomorrow, it belongs in the system responsible for that state — this file accumulates, it doesn't track. Concretely, it is **not**:

- **A TODO list.** "Analyst should run roc_analysis next" is a directive aimed at a person at a time — it belongs in a handoff, issue tracker, or task tool. Record what *was* decided, not what *should* be done.
- **A process spec.** Skills, READMEs, and runbooks own step-by-step procedures. The one exception is a **recurring-pattern entry** — *"whenever we do X in this project we also do Y because Z"* is observational ("the pattern is…"), not imperative ("you should…").
- **A status board.** "In progress: run X" is transient — catalog `Execution_Status` carries it. Entries don't change once written; a later entry can reference the settled *outcome*.
- **A snapshot of mutable catalog state.** A claim true at audit time but false after the next normal write is not durable — a count, distinctness, or shape claim about a table other personas write to ("1500 rows, no duplicates") silently rots and misleads a future reader who quotes it. Before writing any numerical/distinctness claim, ask whether the next normal write keeps it true; if not, record the **scoped** claim that *will* stay true ("the loader-execution rows form a clean GT layer") or the **convention** that explains the shape ("this feature table is dual-purpose; filter by `Confidence IS NULL` for GT-only"). The convention doesn't age; the raw count does.

The full catalog-data-vs-tacit boundary (which specific facts live in the catalog, and the PR-number-vs-behaviour rule) is in [`references/entry-format.md`](references/entry-format.md) → "What doesn't belong here."

## When to write

If you have just made or recorded a decision the file would document, append an entry. Append silently — don't ask permission, don't announce. The bar is **intent**, not "alternatives were weighed": first runs, baselines, and pipeline-validation runs all qualify even when the choice felt obvious. Skip routine read-only operations (querying, listing, browsing schemas) — they leave no entry.

**When an action overrides a prior decision, add a supersession edge.** If what you're
recording invalidates an earlier entry (not merely builds on it), declare
`**Supersedes:** [tk-NNN](#tk-NNN)` on the new entry and append `> Superseded by
[tk-MMM](#tk-MMM)` to the old one — never rewrite the old entry. See
`references/entry-format.md` → "`**Supersedes:**`". This is what keeps "is this still
right?" answerable: superseded entries are excluded from retrieval by default.

**Two silent side-effects of appending an entry** (no user action, documented in
`references/index-and-retrieval.md`):
1. **Classify** the new entry against the topic CV (`docs/tacit-knowledge/topics.md`) —
   reuse an existing term via synonym-aware lookup; propose (don't adopt) a new one into
   the index's `candidate-terms` list if the theme is clearly recurrent and unmatched.
2. **Check the rebuild throttle** — if ≥ 10 entries have accumulated past the index's
   `covers_through`, rebuild `docs/tacit-knowledge/index.md` whole in the same turn and
   note it in one line ("refreshed the tacit-knowledge index — N new entries folded in").
   Never prompt; never auto-commit the rebuilt index.

## When to read — two distinct modes

### Mode A: Guidance (before you act)

**Before acting on a user request that touches the catalog** — creating a feature, adding a vocab term, changing schema, training with new parameters, splitting a dataset, picking an MCP entry-point — **scan `tacit-knowledge.md` for entries about the same entity or the same kind of change**. The user will not phrase this as a "why" question; they'll just propose the action. The skill must fire on the *action*, not on a question keyword.

The bar is low: if the file mentions the entity (by RID) or the change-type ("we tried label smoothing 0.1 on training runs"), surface what it says *before* doing the action. Don't paraphrase — **quote the relevant entry** and let the user decide whether to proceed, adjust, or abandon. The cost of a wasted file-read is seconds; the cost of repeating a documented dead end is hours-to-weeks.

When prior experience contradicts the proposed action, hand the decision back with concrete options rather than blocking — the user may know the original constraints no longer hold.

**How to scan efficiently (don't read the whole Log).** Read the derived index
(`docs/tacit-knowledge/index.md`) for candidates by anchor and keyword, then read only
the un-indexed tail by seeking to the index's `covers_through` boundary — not a full
Log scan. Match anchors by a **generalization walk** (instance → type → abstraction →
process → social/domain), exclude superseded entries **structurally**, then quote the
survivors. Full procedure: `references/index-and-retrieval.md`. If the index is absent,
fall back to a supersession-aware Log scan (read entries, drop tombstoned ones, quote).

### Mode B: Forensic (when asked why)

If the user is asking a question the file would answer — *why* did we choose X, *was there a reason* for Y, *have we tried* Z, *what did we learn* from a prior run, *where does the rationale for this configuration live*, or *catch me up on this project* (new collaborator orientation) — consult `tacit-knowledge.md` *before* answering from configs, current catalog state, or general reasoning.

**Pair it with the design doc when the question is about a specific experiment, dataset, feature, or model.** `tacit-knowledge.md` holds what was *learned*; the matching `docs/design/<entity>/<slug>.md` holds the up-front *plan* — the goal/hypothesis, requirements, and what counted as success. A forensic question like "*why is this model built this way?*", "*what was this experiment testing?*", or "*is this still the right approach?*" is usually answered best by reading **both**: the design (intent + success criteria) and the journal (what happened, what changed). Check the design doc for the entity in question first when the question is about its purpose or whether it's still on-target; fall back to / combine with the journal for the during-and-after story. If neither has it, the honesty rule below applies.

### Honesty rule (both modes)

**If the file is silent on the question, say so explicitly. Do not invent a rationale to fill the gap.** (This is the provenance-honesty application of the plugin-wide rule — `deriva-ml-context` → "Never guess — ground truth is observable"; here the observable source is the journal itself.) Frame any reconstruction from current state as exactly that — a reconstruction, not a recalled decision — so the user can choose whether to treat it as authoritative or look further. When the file does have an entry, cite it (entity RID + entry title) so the user can verify and follow back-references.

## Provenance markers

Every claim in an entry should be readable as one of three things: *what was directly stated*, *what the agent inferred from evidence*, or *what was observed without articulated reasoning*. Default (unmarked) prose is "stated" — the user said this, or the entry's author wrote it directly. Use the explicit markers below for everything else.

| Marker | When to use |
|---|---|
| (none) | The user or author directly stated this. The default reading of unmarked prose. |
| **`[inferred from action]`** | The agent inferred this *fact* from the user's observable actions during the session (e.g., they opened a feature table, then moved on without curating). The action is the evidence. |
| **`[inferred from pattern]`** | The agent inferred this *reason* from prior knowledge, prior entries in this file, or general domain pattern-matching — not from anything the current user actually did or said. The riskiest class; reader-beware. |
| **`[observed]`** | The action happened; no rationale was articulated and none was inferred. The honest "we just did it" record. |

**The `[inferred from pattern]` marker is the riskiest and most fabrication-prone class.** It marks the agent's best guess based on domain knowledge or pattern-matching, not on evidence from this session. A future reader should treat these claims with the same skepticism they'd apply to an LLM's free-form rationalization. Prefer to omit the claim entirely if the pattern-inference is weak; prefer to ask the user to confirm if the claim is load-bearing (see "When to inquire" below).

`[observed]` is not failure. The collective tacit often *doesn't* have a verbalizable explanation. "The author created DAP without articulating a comparison" is a valid, complete record — better than a fabricated rationale. Don't be embarrassed by `[observed]`; it's how honest entries about tacit work look.

For the entry format — the template, field-by-field guidance, and worked examples — see [`references/entry-format.md`](references/entry-format.md).

An entry's **anchor** (what it's about — used for retrieval) can be a catalog artifact,
a process (a skill name), or a socio-technical/domain subject — not only a RID. See
[`references/anchor-taxonomy.md`](references/anchor-taxonomy.md) for the three families
and the Family-C privacy constraint on naming individuals.

## Domain background is a different artifact

**Durable domain background goes in `docs/domain/`, not here.** Facts
about the target domain that aren't tied to one dated decision (staining varies across
sites; sensitivity is valued over specificity in this field) are *semantic*, not
*episodic* — they belong in the domain-background bundle (`docs/domain/`, `type: Concept`
docs refined in place), not in a dated `tk-NNN` Log entry. A domain-concept Log entry
may *anchor* to a `docs/domain/` subject (Family C of the anchor taxonomy), but the
durable explanation lives in the Concept doc. Link the catalog term when one exists;
don't restate it.

## Examples

Five worked *write* examples — a model run with cross-domain implications, a non-run event (feature/vocab creation), a dead end, snapshot-vs-convention, and confirmatory inquiry — live in [`references/entry-examples.md`](references/entry-examples.md). Read the one that matches the entry you're about to write. The canonical **Mode-A "consult before acting"** illustration stays inline:

**User**: "Add a 'blurry' term to the Image_Annotation vocabulary so we can mark unusable slides."

**Response** *(before adding, the skill consults `tacit-knowledge.md` and finds a QC entry)*:

> Before adding, I checked `tacit-knowledge.md` and found:
>
> > ### tk-018 — QC status feature added to Image table ([feature 9PQ4](https://localhost/id/96/9PQ4@2P-XYZW))
> > Kept QC concerns separate from diagnostic concerns rather than extending Image_Annotation with a "blurry" diagnosis term: the two review workflows have different reviewers, criteria, and consumers, so collapsing them would entangle the queues.
>
> Adding `blurry` to `Image_Annotation` would reverse the decision in [**tk-018**](#tk-018). Two options: (a) add the term to the existing `Image_QC_Status` [vocabulary 9PR0](https://localhost/id/96/9PR0@2P-XYZW) (backing [feature 9PQ4](https://localhost/id/96/9PQ4@2P-XYZW)), which preserves the separation, or (b) revisit the original rationale if the constraints have changed. Which do you want?

The moves that matter here — fire on the *action* not a "why" keyword, *quote* the entry rather than paraphrase, and *hand the decision back* with options rather than block — are the Mode-A rules above, applied end-to-end.

## Commit prompting

After 3+ entries in a session — or at a natural pause — suggest committing `tacit-knowledge.md` on its own with a message like "Record tacit knowledge entries." Don't bundle with unrelated changes; don't prompt after every entry.

## File mechanics

`tacit-knowledge.md` lives in the project root and must be tracked in git. See `references/file-mechanics.md` for the gitignore check and first-time-setup details.
