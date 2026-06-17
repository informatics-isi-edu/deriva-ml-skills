---
name: capture-tacit-knowledge
description: "ALWAYS use this when a DerivaML experiment decision is being made, acted on, or asked about — and treat it as a STANDING trigger across the whole session, not a one-time check. The failure mode to beat is under-firing: the user almost never says 'record this' or 'why' — they just take an action or propose one, and the moment slips by. So fire on the ACTION, not on any keyword. Three triggers: (1) WRITE — fire right after YOU or the user just did something a future teammate would need the rationale for: ran/committed an execution, created/split/subsampled a dataset, created a feature or vocabulary, changed schema, chose or changed hyperparameters or a config, picked one approach over another, or resolved a bug with a non-obvious fix. Concrete tells: 'that fixed it…', 'ok that worked, moving on', 'let's use X instead of Y', 'bump … to …', 'going to split/train/register …'. Append a short dated entry to tacit-knowledge.md (project root) in the SAME response — fire even when the choice felt obvious or routine. (2) GUIDANCE — fire BEFORE you execute or recommend a proposed action (add a feature, change a config, split a dataset, train a model, pick a preset); consult tacit-knowledge.md first because prior project experience may bear on whether it'll work. (3) FORENSIC — fire when asked 'why was X chosen', 'have we tried Y', 'what did we learn from Z', or indirect variants ('is this config still right?', 'should we still be using this?', 'why is it pinned to …?'), or when orienting to the project; consult before answering and say so if the file is silent rather than inventing rationale. Do NOT fire for routine lookups, generic how-does-deriva-work questions, or pure tooling chores (reformatting, running tests, version bumps) that carry no experiment rationale."
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

## Entry header

Every entry starts with an HTML anchor line and a four-line header. The anchor gives the entry a stable, link-target identifier; the header places it in time, names its author, and names its antecedents. Together they let future entries reference *this* entry with a click-through markdown link, let a future reader walk back through the chain of supporting decisions, and align the file's attribution with the catalog's `RMB` (Row-Modified-By) column so the same human is named the same way in both systems.

```markdown
<a id="tk-NNN"></a>
### tk-NNN — <short descriptive title> ([<entity-kind RID>](<citation URL>))
**When:** <ISO 8601 timestamp with timezone>
**By:** <display name> (<identity URI>)
**Supported by:** [tk-NNN](#tk-NNN) (parenthetical), [tk-MMM](#tk-MMM) (parenthetical)
```

The `<a id="tk-NNN"></a>` line is what makes `[tk-NNN](#tk-NNN)` references elsewhere in the file (and in `**Supported by:**`) click-through in any markdown viewer that follows the HTML anchor (GitHub, IDE preview, mdbook, browser-rendered Markdown). The explicit anchor is stable even if the title text gets edited later — the link target doesn't depend on slugged heading text.

The parenthetical RID in the title is itself a markdown link to a deriva-ml **citation URL** (see "Title includes the durable catalog handle" below) — clicking it opens the snapshot-pinned record for that catalog entity. Every RID reference in an entry, anywhere, is rendered the same way.

### `tk-NNN` — entry identifier

Every entry gets a unique sequential identifier of the form `tk-NNN`, where `NNN` is a three-digit zero-padded integer (`tk-001`, `tk-002`, ..., `tk-042`, ...). The next entry's number is *one more than the highest existing `tk-NNN` in the file* — count from the file, not from the catalog.

The identifier is stable because the file is append-only: nothing is ever renumbered, and `tk-042` always refers to the same decision. This stability is what makes the **Supported by** chain possible.

`tk-NNN` is *the entry's* identifier — distinct from the catalog RID in the title. The title's RID identifies the *catalog artifact* the entry is about; `tk-NNN` identifies *the decision record itself*. Both coexist because they serve different lookup needs: `tk-019` lets entries point at other entries; `8KG` lets entries point at catalog artifacts.

Three digits gives 999 entries before extending to four — more than enough headroom for any project. If a project ever reaches `tk-999`, the next entry is `tk-1000` and the file just gets a bit wider in that column.

### `**When:**` — required ISO 8601 timestamp with timezone

Every entry has a `**When:**` line giving the timestamp the decision was made (not the entry was last edited — subsequent edits to fix a typo don't update this field).

Format: ISO 8601 with timezone, e.g. `2026-05-26T14:32:00-07:00`. The agent populates this from the system clock — no need to ask the user. Use full precision (date + time of day + timezone) because:

- Same-day decision chains (entries written minutes apart in one session) need ordering finer than dates.
- Timestamps align with catalog event times — useful when an entry references "execution 8KG that finished at 14:32" and was written "at 14:45" (entry written while the run was fresh, not days later as reconstruction).
- ISO 8601 sorts lexically as strings; no parsing required to order entries by time.

### `**By:**` — required decision attribution

Every entry has a `**By:**` line naming the human(s) the decision is attributable to. This field is **required** — not optional — because back-attribution is unreliable: once an entry exists without an author, no future reader can recover who made the call, and the file accumulates anonymous entries that can never be properly cited. Making it required at write-time prevents that drift.

**Source priority** for populating the field:

1. **Authenticated catalog identity (preferred).** If the agent has an active catalog session, use the same identity the catalog would record in the `RMB` (Row-Modified-By) column for a write from this session. Format: `<display name> (<Globus identity URI>)`, e.g. `Carl Kesselman (https://auth.globus.org/abc12345-67ef-8901-2345-67890abcdef0)`. This makes the file's author field byte-identical to what the catalog records, so a tooling pass can correlate entries with their corresponding `Workflow` / `Execution` / `Dataset_Version` rows by author.
2. **Git config fallback.** If no catalog session is active, fall back to `git config user.name` + `git config user.email`. Format: `Carl Kesselman (carl@isi.edu)`.
3. **Explicit `unknown`.** If neither is available, write `unknown` — and prompt the user to set git config or authenticate. Don't guess.

**Multiple deciders.** When a decision is jointly owned (e.g., a clinical curation choice between an ML developer and a pathologist), name both, comma-separated:

```markdown
**By:** Dr. Pathologist (https://auth.globus.org/...), Carl Kesselman (https://auth.globus.org/...)
```

**No author names in titles.** Don't write `### tk-042 — Carl's CIFAR animal subset`. The `**By:**` field is the canonical attribution; embedding the name in the title duplicates the field and forces edits to the title if attribution changes (e.g., a second decider is added later).

### `**Supported by:**` — optional list of antecedent entries

When this decision was built on prior decisions captured in earlier entries, name them. Format: `[tk-NNN](#tk-NNN) (short parenthetical phrase naming what's being relied on)`, comma-separated for multiple. Each reference is a **markdown link to the antecedent entry's anchor** (the `<a id="tk-NNN"></a>` line that precedes its header) — never bare text. Example:

```markdown
**Supported by:** [tk-019](#tk-019) (created the labeled split this filtered from), [tk-038](#tk-038) (Developer handoff named confusion-matrix work)
```

The same linking convention applies to **every** `tk-NNN` mentioned anywhere in an entry's body prose — not just the `**Supported by:**` line. If body prose says "compared against the 8KG baseline established in tk-007," write it as `compared against the 8KG baseline established in [tk-007](#tk-007)` so a reader can click through to the antecedent.

Three things to know about this field:

1. **Direction is backward only.** This field lists entries *this one was built on*, looking backward in time. The reverse direction ("what entries built on this one?") is recoverable by walking the graph — any entry that names `tk-019` in its `Supported by:` is a descendant of `tk-019`. There's no forward-pointing field.

2. **Provenance markers apply.** A `Supported by:` reference can be `[stated]` (the author told me), `[inferred from action]` (the agent saw them read the prior entry before writing), or `[inferred from pattern]` (the agent guessed based on topic adjacency). Mark each reference if its provenance differs from the default (stated).

3. **Optional, not required.** Not every entry has antecedents. The first few entries in a fresh project, conventions about external constraints, dead-end discoveries — these often have no prior entries to lean on. Write the entry without the `**Supported by:**` line in those cases.

### Walking the chain

Together, `tk-NNN` + `Supported by:` give every entry a place in a directed acyclic graph: nodes are entries, edges run from each entry to the ones it was built on. Tracing back from any entry yields a tree of support. The shape mirrors `deriva_ml_get_lineage` on a catalog artifact (which walks producing-execution back to root datasets) — this is the same idea applied to decisions.

Practical uses of the chain:
- "Why did we make this decision?" — walk `Supported by:` back to find the original constraint.
- "What did we abandon?" — find dead-end entries that no later entry lists as `Supported by:`.
- "What's the root cause of this project's current state?" — find entries no other entry supports.

## What an entry contains

Each entry is a short markdown block describing one decision or run, anchored on the RID of the entity it's about. Entries answer questions like *why* a dataset / feature / split / config was chosen, *what* the goal of a run was, *how* the project arrived at the current configuration, and *where* a non-obvious decision came from.

**Every RID mentioned in an entry is rendered as a click-through markdown link** using the deriva-ml citation API — `[execution 8KG](https://localhost/id/96/8KG@2P-XYZW)`, where the URL comes from `ml.cite("8KG")`. This applies in the title parenthetical, in body prose ("compared against the 8KG baseline"), in the `**Supported by:**` field's parentheticals — anywhere a RID appears. Bare-text RIDs don't navigate from a markdown viewer; citation links do, and they stay valid because they pin the catalog snapshot at write-time. See "Title includes the durable catalog handle" under Conventions for the full rule and the distinction from resource URIs.

**`ml.cite()` applies to every RID type, not just datasets.** Executions, assets, workflows, features, vocabularies, vocabulary terms, tables — every RID rendered in an entry is routed through `ml.cite(rid)`. The partial-adoption failure mode is to snapshot-pin Dataset RIDs (because the worked examples happen to use them) and hand-write bare-URL links for the others; the convention is uniform. A mixed entry referencing a dataset and the execution that consumed it looks like:

```markdown
Trained cifar10_quick on [dataset 7KE v0.4.0](https://localhost/id/96/7KE@2P-XYZW)
in [execution 8KG](https://localhost/id/96/8KG@2P-XYZW); both URLs come from
ml.cite("7KE") and ml.cite("8KG") respectively.
```

If you find yourself typing `https://.../id/<cat>/<rid>` by hand, you've left the convention — call `ml.cite(rid)` instead and paste the returned URL.

Every entry should answer:

1. **What was run or decided** — the action.
2. **Hypothesis or question** the entry was meant to answer. For non-run events (feature creation, schema change, vocabulary addition, dataset construction) this is the *use case the change exists to serve* — what does this enable, what was missing before — rather than a literal hypothesis.
3. **Reasoning** — what led to this configuration, in plain language. **Spell out one term-of-art per entry that a reader from the other discipline wouldn't know** — either inline ("label smoothing 0.1 — softens hard 0/1 targets to discourage overconfidence") or as a parenthetical. The entry's job is to be readable by the discipline you're *not* in. The catalog has the precise numbers.
4. **Immediate observations** *when applicable* — cheap-to-record facts that would be awkward to retrieve later (wall-clock time, headline metric the run printed, anomalies). For schema and feature changes there usually are no observations at write-time; skip part 4 rather than padding it.
5. **Consequences for downstream readers** *when applicable* — factual statements about what this decision means for someone in the *other* discipline, **stated as facts, not as directives**. Past or present tense, never imperative. If an ML run produced something a domain expert should know about, say so factually ("at this accuracy, roughly 8% of slides surface below 0.5 confidence — the queue size the QC team would see if this model were used for triage"). If a schema change affects how ML configs reference the data, say so factually ("after this change, `Subject.age` no longer exists; the equivalent column is `Subject.age_at_intake`"). Skip this part when the change is purely internal to one discipline. The reader decides what to *do* about the consequence; this section's job is to make sure they know.
6. **Weighed alternatives** *when alternatives were genuinely considered* — what else was on the table, and what ruled them out. This is the **comparative-judgment layer**: a future reader needs to see *what was compared*, not just *what was picked*. **Never fabricate this section.** If the reasoning trace doesn't show alternatives, write nothing here, or write `**Weighed alternatives:** *(none captured — choice was [observed] without an articulated comparison)*`. Use the provenance markers above; ask for confirmation when an `[inferred from pattern]` claim would be load-bearing (see "When to inquire").

**Conclusions are optional and can be deferred.** At write-time you usually have a hypothesis and reasoning, not a settled "what this means." Don't fabricate. Conclusions show up later in whichever entry the reasoning crystallizes in — sometimes the very next run, sometimes much later. A single prior run can spawn multiple follow-ups exploring different angles. Refer back by execution RID so a reader can navigate the chain in either direction.

## Conventions

These are the cross-cutting rules — how entries are titled, ordered, and grounded in the catalog. Entry shape (the six parts above) goes inside; these rules govern the boundaries.

**Structural:**

- **Heading level is `###`.** Each entry is a sibling under the file's top-level `# Tacit Knowledge` heading.
- **Append new entries at the bottom.** The file reads top-to-bottom as the project's history; chronology is the structure.
- **Title starts with `tk-NNN`**, the entry's unique identifier (see "Entry header" above). The next entry's number is one more than the highest existing `tk-NNN` in the file.
- **No dates in titles.** Time information lives in the `**When:**` header field, not the title; embedding a date in the title duplicates that field and rots if the entry is later edited.
- **No author names in titles.** Attribution lives in the `**By:**` header field. Embedding a name in the title (`### tk-042 — Carl's animal subset`) duplicates the field and forces a title edit if attribution changes (e.g., adding a second decider).
- **Title includes the durable catalog handle in parentheses, written as a click-through markdown link** — the navigation anchor for what the entry refers to. Pick the RID a reader would use to find related artifacts, then render it via the deriva-ml citation API so the link is browser-openable and snapshot-pinned:
   - Model run → **execution RID** (`### tk-042 — ... ([execution 8KG](https://localhost/id/96/8KG@2P-XYZW))`)
   - Feature creation → **feature RID** (`### tk-043 — ... ([feature 9PQ4](https://localhost/id/96/9PQ4@2P-XYZW))`)
   - Vocabulary addition (terms only) → **vocabulary RID** (`### tk-044 — ... ([vocabulary 9PR0](https://localhost/id/96/9PR0@2P-XYZW))`)
   - Dataset creation or split → **dataset RID with version** (`### tk-045 — ... ([dataset 7KE v0.4.0](https://localhost/id/96/7KE@2P-XYZW))`)
   - Schema change → **table RID** (`### tk-046 — ... ([table 5-AB12](https://localhost/id/96/5-AB12@2P-XYZW))`)

   The URL inside the markdown link comes from `ml.cite(rid)` — the deriva-ml citation API. The persona writing the entry already has a `ml = DerivaML(...)` instance in scope (the same one being used for the action this entry records); call `ml.cite("8KG")` and it returns `https://{host}/id/{catalog}/8KG@{snapshot_time}` — a **permanent citation URL** that pins the catalog snapshot at write-time so the link still resolves to the same record years later, even after subsequent catalog writes. Default behavior is the permanent (snapshot-pinned) URL; `ml.cite(rid, current=True)` returns the current-state URL without a snapshot suffix, but the snapshot-pinned form is what you want for tacit-knowledge entries.

   The link is markdown — `[execution 8KG](url-from-cite)` — not bare text. This is the **durable** way to reference catalog entities from a markdown-rendered document: a reader in any viewer (GitHub, IDE preview, mdbook, browser-rendered Markdown) can click through and land on the catalog record.

   This is distinct from `deriva://catalog/{host}/{cat}/deriva-ml/...` **resource URIs**: those are for *queryable* resource references (MCP tools, programmatic fetches against a live catalog). Citation URLs from `ml.cite(rid)` are for *click-through navigation by a human reader*. Both have their place; this section's title-handle convention uses the citation URL because the audience is a future reader, not a tool.

   Describing the *kinds* of supporting artifacts ("three terms were created"; "model weights, training log, prediction CSV are linked to the execution") is fine and helpful. Reference RIDs sparingly, but **always name at least one representative supporting RID** a cross-domain reader can click through to ("the 8KG run that established the 20% baseline"). Every RID mentioned anywhere in the entry — title parenthetical, body prose, `**Supported by:**` parentheticals — is rendered as `[label](ml.cite(rid))`, never as bare text. Don't enumerate every supporting RID — they go stale, and the catalog already has them linked to the title's handle.

   For entries that don't correspond to a single catalog artifact (conventions, recurring patterns, cross-cutting reasoning entries), the parenthetical handle can be omitted — the `tk-NNN` is sufficient identifier on its own.
- **Length is set by content.** Long enough to answer the six entry parts; short enough to scan in one pass (~5–15 lines in practice).
- Past tense — these are settled records, not plans.

**Content principles:**

- **Dead ends are valid standalone entries.** When alternatives were weighed and the chosen path didn't pan out, write the dead-end entry on its own — no successor decision required. Dead ends are the highest-leverage tacit knowledge on a multidisciplinary team: the ML designer doesn't know that "we tried using FFPE stain type as a model input and it didn't work because staining variance dominated the signal" was a year of unproductive work the previous lab burned through. Title it after the dead-end action itself (`### tk-026 — Tried stain_type as model input; abandoned ([execution 3-XYZ](url-from-ml.cite))`).
- **Recurring patterns are also valid.** Entries of the form *"whenever we do X in this project, we also do Y because Z"* are tacit knowledge about the project's conventions — not directives. They're statements about *what this project's pattern is*, written for a future reader who's about to do X and would benefit from knowing the pattern exists. Example: `### tk-031 — Convention — releasing a dataset bumps src/configs/datasets.py` (rationale: experiment configs pin by version, so a release that isn't reflected in the config is unreachable from runners). The reader chooses whether to follow the pattern; the entry explains why the pattern exists. Convention entries usually have no catalog-RID handle in the parenthetical — the `tk-NNN` is sufficient identifier.
- **Reference RIDs and include quantitative evidence** (counts, sizes) when known — but as evidence for the reasoning, not as a replacement for it. See "What doesn't belong here" below for what's catalog data vs. what's tacit.

## When to inquire

Inquiry is the agent's tool for sharpening an `[inferred from pattern]` claim — the riskiest provenance class — into a stated one, or for confirming that a guess shouldn't be written at all. Use it when the answer would materially improve a load-bearing claim, and observe these guardrails:

- **At most one question per entry.** If multiple ambiguities exist, pick the highest-leverage one and use provenance markers for the rest.
- **Confirmatory shape only — never interrogative.** The question must be answerable by yes / no / correction, not by open-ended self-attribution. The user often *can't* honestly answer "why did you do X?" — they just did it. Asking the open form invites confabulation, which is worse than `[observed]` honesty.
- **"I just did it" is a valid answer.** If the user can't articulate a reason, that maps to `[observed]` — it's a complete, honest record, not a failure.

**Inquiry shape:**

| ✅ Confirmatory | ❌ Interrogative |
|---|---|
| "I'm about to write that you chose CS0 over CSA because CS0 carries stratified labels. Is that the characterization, a different one, or no articulated reason?" | "Why did you choose CS0?" |
| "I'm inferring this split's rationale is variance-control. Confirm, correct, or 'just did it'?" | "What's the rationale for this split?" |
| "I see traces suggesting you considered the vehicles-only subset. Was that on the table, or was the choice between animals-only and 10-class from the start?" | "What alternatives did you consider?" |

**Response → marker mapping:**

| User response | Marker becomes |
|---|---|
| "Yes / correct" | (none — promote to stated) |
| "Different reason — actually [X]" | (none — record X as stated) |
| "No reason / I just did it / I don't remember" | `[observed]` for the fact; drop any inferred rationale |
| "I didn't consider that alternative" | Remove the inferred alternative entirely |

This pairwise confirmation matches the Law of Comparative Judgment: humans can reliably answer "is this the better characterization?" but unreliably answer "what is the absolute reason?" Confirmatory inquiry preserves *"I just did it"* as a valid answer.

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

### Example 1 — A model run with cross-domain implications

```markdown
<a id="tk-007"></a>
### tk-007 — First end-to-end CIFAR-10 run on localhost catalog 1407 ([execution 8KG](https://localhost/id/96/8KG@2P-XYZW))
**When:** 2026-04-12T15:22:00-07:00
**By:** Carl Kesselman (https://auth.globus.org/abc12345-67ef-8901-2345-67890abcdef0)
**Supported by:** [tk-003](#tk-003) (created the labeled split this run consumed)

Hypothesis: the cifar10_e2e schema, dataset [7KE](https://localhost/id/96/7KE@2P-XYZW),
and the deriva-ml-run pipeline wired together cleanly against a
freshly-seeded localhost catalog. Ran cifar10_quick (small image
classifier, fewest training passes, smallest network) because the
question was "does the plumbing work," not "does the model perform."
Picked the labeled split as input because it was the smallest dataset
with ground-truth labels on both partitions (80 train, 20 test), so a
real test number was reachable at this scale. Run finished in ~30s on
CPU; held-out accuracy 20% on 20 images vs a 10% guess-one-of-ten
baseline — a learning signal but within noise at this sample size.
Outputs linked to execution [8KG](https://localhost/id/96/8KG@2P-XYZW).

Implications for collaborators: this is a pipeline-validation run, not a
performance baseline — don't cite the 20% number as a model capability
claim. The next end-to-end run on the full dataset is where the
domain-meaningful accuracy comparison starts.
```

### Example 2 — A non-run event (no part-4 observations because nothing to observe at write-time)

```markdown
<a id="tk-018"></a>
### tk-018 — QC status feature added to Image table ([feature 9PQ4](https://localhost/id/96/9PQ4@2P-XYZW))
**When:** 2026-04-23T10:05:00-07:00
**By:** Dr. Pathologist (https://auth.globus.org/d4e8f200-9c2b-4a1d-bf3e-1234567890ab), Carl Kesselman (https://auth.globus.org/abc12345-67ef-8901-2345-67890abcdef0)

Created `QC_Status` on `Image`
([table 5-AB12](https://localhost/id/96/5-AB12@2P-XYZW), ~3,200 rows)
backed by a new `Image_QC_Status`
[vocabulary 9PR0](https://localhost/id/96/9PR0@2P-XYZW) in the
`histopath` schema — three terms (pass, blurry, tissue_fold) plus a
confidence_score column. Use case: blurry slides have been silently
degrading downstream model accuracy with no first-class way to mark
them. Kept QC concerns separate from diagnostic concerns rather than
extending Image_Annotation with a "blurry" diagnosis term: the two
review workflows have different reviewers, criteria, and consumers,
so collapsing them would entangle the queues. Values not populated
yet — annotator workflow is the next step.

Implications for collaborators: ML training configs that currently filter
on `Image_Annotation` should also start filtering on
`QC_Status != "blurry"` once values are populated, to avoid training on
images the pathologists have flagged unusable.
```

### Example 3 — A dead end (no successor decision)

```markdown
<a id="tk-026"></a>
### tk-026 — Tried stain_type as model input; abandoned ([execution 3-XYZ](https://localhost/id/96/3-XYZ@2P-XYZW))
**When:** 2026-05-04T09:18:00-07:00
**By:** Carl Kesselman (https://auth.globus.org/abc12345-67ef-8901-2345-67890abcdef0)
**Supported by:** [tk-007](#tk-007) (baseline 8KG run this is compared against), [tk-018](#tk-018) (QC_Status feature is the well-typed alternative to stain_type for model input)

Hypothesis: adding the stain_type categorical (H&E vs IHC vs Trichrome)
as a one-hot model input would let the network learn stain-specific
diagnostic patterns. Trained the cifar10_quick architecture with the
extra input channel on dataset [7KE v0.4.0](https://localhost/id/96/7KE@2P-XYZW);
held-out accuracy actually dropped 4 points vs the baseline run
([execution 8KG](https://localhost/id/96/8KG@2P-XYZW), recorded in
[tk-007](#tk-007)) that didn't use stain_type. Walking the model's
gradient attributions showed the network was using stain_type as a
shortcut to predict scanner site, not disease class — staining variance
(which is operator- and lab-specific) was dominating the signal we
wanted. Abandoned this input channel. Not revisiting unless we get a
multi-site dataset where stain protocols are matched across sites.

Implications for collaborators: the catalog still has the `stain_type`
column on Image — keep populating it (it's correct curation), just
don't pipe it into models without a multi-site dataset.
```

### Example 4 — Snapshot vs convention: recording the durable shape, not the audit-time count

A Curator auditing a freshly-bootstrapped catalog runs a direct query against the `Image_Classification` feature table and verifies: 1500 rows, 1500 distinct images, every image labeled exactly once. The temptation is to write that finding as a clean, quotable fact for downstream readers.

**Draft that ages out (don't write this):**

```markdown
<a id="tk-NNN"></a>
### tk-NNN — Image_Classification ground-truth audit clean ([feature 7AB](https://localhost/id/96/7AB@2P-XYZW))
... 1500 rows in Execution_Image_Image_Classification covering 1500
distinct images — no missing labels, no duplicate labels (no need for
the `newest` selector when reading this feature).
```

The audit is correct *at this instant*, but `Image_Classification` is the same table the Modeler's prediction-recording step writes into. The moment the next training execution runs, the table contains both ground-truth rows (written by the loader execution, `Confidence IS NULL`) and prediction rows (written by training executions, `Confidence` populated). The unfiltered count goes to 1800+, the same image carries multiple label rows, and a reader who quotes "no need for `newest` selector" in good faith gets the wrong result. The entry didn't lie when it was written; the catalog moved underneath it.

**Durable rewrite — capture the convention, not the snapshot:**

```markdown
<a id="tk-NNN"></a>
### tk-NNN — Convention — Image_Classification is dual-purpose (ground truth + predictions)
**When:** ...
**By:** ...

`Image_Classification` ([feature 7AB](https://localhost/id/96/7AB@2P-XYZW))
is written by two distinct kinds of execution and the rows are not
distinguishable by table membership alone: the loader execution writes
ground-truth rows with `Confidence IS NULL`; training executions write
prediction rows with `Confidence` populated. After any training run,
the same image will carry multiple rows in this feature.

Implications for collaborators: when reading this feature as ground
truth, filter by execution (the loader exec RID) or by `Confidence IS
NULL`. An unfiltered `ml.feature_values("Image", "Image_Classification")`
returns GT + every recorded prediction interleaved, which is rarely
what an analysis wants. The `newest` selector is also not a safe
substitute — "newest" is whichever execution last wrote, not "ground
truth."
```

If the audit-time snapshot still feels worth recording, scope it explicitly to the partition that *will* remain stable — e.g. "the loader-execution rows form a 1500-of-1500 clean GT layer; this scope doesn't grow with subsequent training runs." That framing makes the durability boundary visible to a future reader.

The shape to learn: **audits surface conventions.** When an audit finds a clean count or a clean shape, the count is the symptom; the convention that explains *why* the table has that shape (and what about it will or won't survive the next write) is the entry.

### Example 5 — Confirmatory inquiry promoting an `[inferred from pattern]` claim

User just created an animals-only subset of `cifar10_complete` and didn't articulate alternatives. The agent's reasoning trace shows the user opened the vehicle-class feature values mid-session before moving on. The agent is about to write the entry.

**Agent's draft** *(before inquiry)*:

```markdown
<a id="tk-042"></a>
### tk-042 — Created cifar10_animals_subset ([dataset DAP v0.2.0](https://localhost/id/96/DAP@2P-XYZW))
**When:** 2026-05-25T16:08:00-07:00
**By:** Carl Kesselman (https://auth.globus.org/abc12345-67ef-8901-2345-67890abcdef0)
**Supported by:** [tk-019](#tk-019) (created cifar10_labeled_split that this filters from), [tk-038](#tk-038) [inferred from pattern] (Developer handoff named confusion-matrix work)

300-image filter of cifar10_complete to {bird, cat, deer, dog, frog,
horse}, 50/class. Reserved for the Analyst's confusion-matrix work.

Weighed alternatives:
- Balanced 10-class subset — rejected: doesn't isolate the
  intra-animal confusion mode.
- [inferred from action] Vehicles-only subset was considered (author
  opened the vehicle feature values mid-session) and dropped without
  an articulated reason. [inferred from pattern] *possibly* because
  per-class visual variance within vehicles is higher than within
  animals in CIFAR-10; not confirmed by author.
```

The agent notices that the second alternative carries an `[inferred from pattern]` claim about *why* vehicles-only was rejected — load-bearing, because a future reader trying to understand the curation strategy would treat the variance-reasoning as a stated principle. Per "When to inquire," it asks (one question, confirmatory shape):

> "I'm about to write that you considered the vehicles-only subset and rejected it because per-class visual variance is higher in vehicles than in animals. Is that the reason, a different reason, or no articulated reason?"

**Three response paths:**

| User response | Agent's entry update |
|---|---|
| "Yes, that's right" | Promote `[inferred from pattern]` → unmarked. The variance reasoning is now stated. |
| "I rejected vehicles-only because the Analyst said the confusion mode they care about is cat-vs-dog, not truck-vs-car" | Drop the variance inference. Record the user's stated reason. |
| "I don't remember / I just clicked through and went with animals" | Keep `[inferred from action]` on the fact (the action trace shows it was considered). Drop the `[inferred from pattern]` reasoning entirely. Final entry's alternative reads: `[observed]` Vehicles-only subset was considered (author opened the feature table mid-session) and dropped without an articulated reason. |

The third response is *not failure* — it's the honest tacit-knowledge record. A future reader sees "this was on the table; no recorded reason" and can choose to re-open the comparison if relevant. The agent has resisted fabricating a plausible-sounding rationale to fill the gap.

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
