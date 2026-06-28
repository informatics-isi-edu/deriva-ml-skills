---
name: capture-tacit-knowledge
description: "ALWAYS use this when a DerivaML experiment decision is being made, acted on, or asked about — and treat it as a STANDING trigger across the whole session, not a one-time check. The failure mode to beat is under-firing: the user almost never says 'record this' or 'why' — they just take an action or propose one, and the moment slips by. So fire on the ACTION, not on any keyword. Three triggers: (1) WRITE — fire right after YOU or the user just did something a future teammate would need the rationale for: ran/committed an execution, created/split/subsampled a dataset, created a feature or vocabulary, changed schema, chose or changed hyperparameters or a config, picked one approach over another, or resolved a bug with a non-obvious fix. Concrete tells: 'that fixed it…', 'ok that worked, moving on', 'let's use X instead of Y', 'bump … to …', 'going to split/train/register …'. Fire even when the choice felt obvious or routine. (2) GUIDANCE — fire BEFORE you execute or recommend a proposed action (add a feature, change a config, split a dataset, train a model, pick a preset); consult tacit-knowledge.md first because prior project experience may bear on whether it'll work. (3) FORENSIC — fire when asked 'why was X chosen', 'have we tried Y', 'what did we learn from Z', or indirect variants ('is this config still right?', 'should we still be using this?', 'why is it pinned to …?'), or when orienting to the project; consult before answering and say so if the file is silent. Do NOT fire for routine lookups, generic how-does-deriva-work questions, or pure tooling chores (reformatting, running tests, version bumps) that carry no experiment rationale."
user-invocable: false
---

# Capture and Consult Tacit Knowledge

`tacit-knowledge.md` (project root) is the project's accumulating record of **tacit knowledge** about its models and data — the intent and reasoning that the catalog cannot store. The catalog is the source of truth for *what* exists (RIDs, configs, numbers, lineage). This file is the source of truth for *why*. Entries connect: a follow-up run often references prior runs by RID, so the file reads top-to-bottom as the project's history of how its understanding evolved.

**Don't ask this file for catalog-stored facts.** If the question is *what* — what datasets exist, what vocabulary terms are defined, what assets a workflow produced, which version of a dataset is current — fetch the catalog directly (`deriva://catalog/{host}/{cat}/deriva-ml/...` resources first; tools next). If the question is *why* — why this dataset was created, why this hyperparameter was chosen, why a previous approach was abandoned — read this file. Entries reference catalog entities by RID rendered as a `ml.cite(rid)` markdown link (click-through, snapshot-pinned), not by inlining their contents.

This file is also the **cross-domain bridge** on multidisciplinary teams. The ML designer writes entries the domain expert needs to *understand* (and vice versa) — not directives for the other discipline to act on. Each entry captures decisions and their rationale in language the other side can read; what the reader chooses to do with that understanding is their decision, in their own time. Neither side writes only for themselves. The entry conventions below name this responsibility explicitly.

## Relationship to catalog semantic awareness

This file and the catalog's **semantic-awareness layer** (controlled vocabularies, table/column descriptions, RIDs, synonyms, and the `rag_search` index over them — see `/deriva:semantic-awareness`) are complementary halves of the same problem. Semantic awareness answers *what exists and what is it called*; tacit knowledge answers *why does it exist*. Each makes the other usable: the catalog's stable canonical names and RIDs are what let `tk-042` still resolve to a real entity five years from now, and a tacit entry recording *"we considered and rejected the vehicles-only subset because variance dominated the signal"* is what stops a future `rag_search` for `"vehicle subset"` from triggering a duplicate creation. When you find yourself reaching for a name that semantic awareness should have resolved, fix it in the catalog (better description, add a synonym, rename a term) — don't paper over it with a tacit entry. When you find yourself drafting a tacit entry that's really just restating a catalog fact, link the catalog instead. The two layers stay sharp by keeping their jobs distinct.

## What this file is not

- **Not a TODO list.** Don't write "Analyst should run roc_analysis next" or "we need to release dataset X." Those are workflow directives aimed at a specific person at a specific time; they belong in handoff sections, issue trackers, or a task tool — not here. This file records what *was* decided, not what *should* be done.
- **Not a process or workflow specification.** Don't write step-by-step procedures for a future contributor to follow. Skills, README files, and runbooks own that material. The exception is **recurring-pattern entries** — see Conventions: *"whenever we do X, we also do Y because Z"* is tacit knowledge about a project convention, not a directive. The form is observational ("the pattern in this project is..."), not imperative ("you should...").
- **Not a status board.** Don't write "in progress: training run X." Catalog `Execution_Status` carries that, and it changes; this file's entries don't change once written. If the run finishes, the next entry could reference the *settled outcome*, not a transient state.
- **Not a snapshot of mutable catalog state.** A claim that's true *at audit time* but becomes false the next time the catalog is normally written is not a durable entry — even if the audit itself was correct. The most common shape is a count, a distinctness claim, or a shape claim about a table other personas will write to ("1500 rows, no duplicates, no need for the `newest` selector"). On the next normal write, the claim silently rots and a future reader who quotes it in good faith is misled. If the audit produced a useful finding, record either the **scoped** version of the claim (the partition or filter that *will* remain true — "the loader-execution rows form a clean GT layer") or the **convention** that explains why the snapshot was that shape ("this feature table is dual-purpose; filter by execution or by `Confidence IS NULL` for GT-only"). The convention is what doesn't age; the raw count is what does.
- **Not a replacement for the catalog.** See "What doesn't belong here" below — RIDs, versions, vocab contents, schema shape, lineage edges all live in the catalog. This file links to them, doesn't replicate them.

The unifying rule: **entries are past-tense, settled records.** If something might change tomorrow, it doesn't belong here — it belongs in the system that's actually responsible for that state. This file accumulates; it doesn't track.

The companion rule for audits: **before writing a numerical or distinctness claim, ask whether the next normal catalog write will keep it true.** If the table will be written to by another persona's routine work (predictions into a shared GT+predictions feature, new members into a dataset, new terms into a vocab), scope the claim or capture the convention instead of the snapshot.

## When to write

If you have just made or recorded a decision the file would document, append an entry. Append silently — don't ask permission, don't announce. The bar is **intent**, not "alternatives were weighed": first runs, baselines, and pipeline-validation runs all qualify even when the choice felt obvious. Skip routine read-only operations (querying, listing, browsing schemas) — they leave no entry.

## When to read — two distinct modes

### Mode A: Guidance (before you act)

**Before acting on a user request that touches the catalog** — creating a feature, adding a vocab term, changing schema, training with new parameters, splitting a dataset, picking an MCP entry-point — **scan `tacit-knowledge.md` for entries about the same entity or the same kind of change**. The user will not phrase this as a "why" question; they'll just propose the action. The skill must fire on the *action*, not on a question keyword.

The bar is low: if the file mentions the entity (by RID) or the change-type ("we tried label smoothing 0.1 on training runs"), surface what it says *before* doing the action. Don't paraphrase — **quote the relevant entry** and let the user decide whether to proceed, adjust, or abandon. The cost of a wasted file-read is seconds; the cost of repeating a documented dead end is hours-to-weeks.

When prior experience contradicts the proposed action, hand the decision back with concrete options rather than blocking — the user may know the original constraints no longer hold.

### Mode B: Forensic (when asked why)

If the user is asking a question the file would answer — *why* did we choose X, *was there a reason* for Y, *have we tried* Z, *what did we learn* from a prior run, *where does the rationale for this configuration live*, or *catch me up on this project* (new collaborator orientation) — consult `tacit-knowledge.md` *before* answering from configs, current catalog state, or general reasoning.

**Pair it with the design doc when the question is about a specific experiment, dataset, feature, or model.** `tacit-knowledge.md` holds what was *learned*; the matching `docs/design/<entity>/<slug>.md` holds the up-front *plan* — the goal/hypothesis, requirements, and what counted as success. A forensic question like "*why is this model built this way?*", "*what was this experiment testing?*", or "*is this still the right approach?*" is usually answered best by reading **both**: the design (intent + success criteria) and the journal (what happened, what changed). Check the design doc for the entity in question first when the question is about its purpose or whether it's still on-target; fall back to / combine with the journal for the during-and-after story. If neither has it, the honesty rule below applies.

### Honesty rule (both modes)

**If the file is silent on the question, say so explicitly. Do not invent a rationale to fill the gap.** Frame any reconstruction from current state as exactly that — a reconstruction, not a recalled decision — so the user can choose whether to treat it as authoritative or look further. When the file does have an entry, cite it (entity RID + entry title) so the user can verify and follow back-references.

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

## What doesn't belong here

This file records *why*, not *what*. The catalog is the source of record for facts; this file points at facts but doesn't replicate them. Concretely, **don't write**:

- **Vocabulary term lists.** "The `Workflow_Type` vocab has terms X, Y, Z" goes stale the next time a term is added. Link to `deriva://catalog/{host}/{cat}/deriva-ml/vocabularies/deriva-ml/Workflow_Type` and let the reader fetch.
- **Dataset RID / type / description tables.** "13 datasets: 96E (Complete, Labeled, …), 96R (Split, …), …" is catalog data. Link to `deriva://catalog/{host}/{cat}/deriva-ml/datasets` instead. (A *short* table mapping the user-facing config name to a stable RID is fine when those names are themselves project decisions — the catalog doesn't store the mapping from `cifar10_small_labeled_split` to `CRR`. That's tacit.)
- **Schema field types or column lists.** Catalog data; fetch `deriva://catalog/{h}/{c}/schema` or the table resource.
- **Workflow URLs / checksums / version strings.** Catalog data; live in `Workflow` rows.
- **Asset MD5s, file sizes, lengths.** Catalog data.
- **Execution status, start/stop times, lineage edges.** Catalog data; fetch `deriva://catalog/{h}/{c}/deriva-ml/execution/{rid}` or `…/ml/lineage/{rid}`.
- **PR numbers, commit SHAs, issue IDs.** Git/forge coordinates are *archaeology*, not behaviour — they tell a reader *where the change landed*, not *what the change actually does*. The thing future readers need is the durable behavioural claim ("auto-composed Execution descriptions only fire when a Hydra experiment preset is in use"); the PR number is incidental and rots when the repo is mirrored, renumbered, or migrated. Name the behaviour. If git traceability genuinely adds value, the catalog's `Workflow.URL` column already pins the commit SHA — link to that, not to a PR.

  **Wrong** (cites a transient PR coordinate as the thing being said):

  > "PR #46 makes auto-composed Execution descriptions only fire for `+experiment=` overrides; bare `model_config=` runs default to 'Simple model run'."

  **Right** (the durable behaviour is the subject; the PR number is gone):

  > "Auto-composed `Execution.description` strings only fire when a Hydra experiment preset is in use (`+experiment=...`). Bare `model_config=` / `datasets=` overrides without an experiment preset fall back to the literal string 'Simple model run'. Workaround: define a one-line experiment preset for the variation you want a meaningful description for; don't try to pass `description=` directly, which Hydra's grammar rejects for free-form strings."

  The shape to learn: PR numbers describe the *change*; tacit entries describe the *behaviour the change left in place*. Always write the behaviour.

**Do write**: why the dataset was created, why the workflow's type was chosen, why a hyperparameter was selected, what alternatives were rejected and why, what would invalidate this decision, what a future reader needs to know to evaluate whether the decision still holds. Reference catalog entities by their RID rendered as a `ml.cite(rid)` markdown link rather than inlining their fields.

The rule of thumb: **if the catalog could go stale and break what you wrote, the catalog should answer the question, not this file.**

## Examples

Five worked examples — covering a model run with cross-domain implications, a
non-run event (feature/vocab creation), a dead end, snapshot-vs-convention, and
confirmatory inquiry — live in
[`references/entry-examples.md`](references/entry-examples.md). Read the one
that matches the entry you're about to write; the rules above are the contract,
those examples are the rules applied end-to-end. The canonical Mode-A
"consult before acting" illustration stays inline directly below.

## Worked example — Mode A firing on a proposed action

**User**: "Add a 'blurry' term to the Image_Annotation vocabulary so we can mark unusable slides."

**Response** *(before adding, the skill consults `tacit-knowledge.md` and finds the QC entry above)*:

> Before adding, I checked `tacit-knowledge.md` and found:
>
> > ### tk-018 — QC status feature added to Image table ([feature 9PQ4](https://localhost/id/96/9PQ4@2P-XYZW))
> > Kept QC concerns separate from diagnostic concerns rather than extending Image_Annotation with a "blurry" diagnosis term: the two review workflows have different reviewers, criteria, and consumers, so collapsing them would entangle the queues.
>
> Adding `blurry` to `Image_Annotation` would reverse the decision in [**tk-018**](#tk-018). Two options: (a) add the term to the existing `Image_QC_Status` [vocabulary 9PR0](https://localhost/id/96/9PR0@2P-XYZW) (backing [feature 9PQ4](https://localhost/id/96/9PQ4@2P-XYZW)), which preserves the separation, or (b) revisit the original rationale if the constraints have changed (e.g., the two review pools have merged, or you're explicitly opting into a single combined queue). Which do you want?

Three things this example demonstrates:
1. **Consult before act** — the skill fires on the proposed action, not on a "why" question.
2. **Quote, don't paraphrase** — the user can see the original entry and judge its weight themselves.
3. **Hand decision back with concrete options** — don't block, don't auto-proceed; the user may know the original constraints no longer hold.

## Commit prompting

After 3+ entries in a session — or at a natural pause — suggest committing `tacit-knowledge.md` on its own with a message like "Record tacit knowledge entries." Don't bundle with unrelated changes; don't prompt after every entry.

## File mechanics

`tacit-knowledge.md` lives in the project root and must be tracked in git. See `references/file-mechanics.md` for the gitignore check and first-time-setup details.
