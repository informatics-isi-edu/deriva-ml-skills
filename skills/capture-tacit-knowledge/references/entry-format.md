# Entry Format — Template, Field Guidance, and Conventions

## File header — OKF Log frontmatter

`tacit-knowledge.md` is an **OKF Log document**: an append-only journal, which is
exactly the shape the [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
reserves for a `log`. The file opens with a single YAML frontmatter block, then the
`# Tacit Knowledge` H1, then the `tk-…` entries as the body:

```markdown
---
type: Log
title: Tacit Knowledge — <project name>
description: >
  The why behind this project's DerivaML decisions — rationale, dead ends, and
  cross-discipline consequences that the catalog records but does not explain.
  Append-only; each entry is a dated tk-… decision record.
tags: [tacit-knowledge, provenance, deriva-ml]
---

# Tacit Knowledge

<the boundary-explaining header paragraph, then the tk-… entries>
```

Frontmatter rules: `type: Log` is required (it's what makes the file a conformant
OKF Log). `title`/`description`/`tags` are recommended. **`resource` is intentionally
omitted** — the journal is the knowledge itself, not a pointer to an external
artifact (the same reason the design-doc templates omit it). The frontmatter is
written **once at file creation** and not touched per entry — entries are appended
to the body below the H1, exactly as before. This is a file-level wrapper; it does
not change the per-entry format documented in the rest of this file.

**`tags` here is document-level OKF metadata, not the per-entry classification.**
The `tags` line describes the *whole file* (`[tacit-knowledge, provenance, deriva-ml]`),
is written once, and is **not read by retrieval** — the LLM never keys on it to find or
match entries. Don't confuse it with an entry's **`concept keywords`**: those are the
per-entry classification drawn from the repo-local topic CV
(`docs/tacit-knowledge/topics.md`, LLM-managed, human-gated), and they live as a column
in the *derived retrieval catalog* (`docs/tacit-knowledge/retrieval-catalog.md`), **not** in the entry or its
frontmatter. The Log entry itself carries no keyword field — classification is derived,
so it stays out of the append-only record. See
`references/index-and-retrieval.md` → "Classifying entries against the topic CV" for the
mechanism, and `references/anchor-taxonomy.md` for the `anchor` (the primary retrieval
key — *what the entry is about*, distinct again from both `tags` and `concept keywords`).
For the whole picture in one place — the directory layout, every file's OKF `type`, and
how `type`/`tags`/`concept keywords`/`anchor` relate — see
`references/file-mechanics.md` → "OKF layout at a glance."

## Entry header

Every entry starts with an HTML anchor line and a four-line header. The anchor gives the entry a stable, link-target identifier; the header places it in time, names its author, and names its antecedents. Together they let future entries reference *this* entry with a click-through markdown link, let a future reader walk back through the chain of supporting decisions, and align the file's attribution with the catalog's `RMB` (Row-Modified-By) column so the same human is named the same way in both systems.

```markdown
<a id="tk-[branch-]NNN"></a>
### tk-[branch-]NNN — <short descriptive title> ([<entity-kind RID>](<citation URL>))
**When:** <ISO 8601 timestamp with timezone>
**By:** <display name> (<identity URI>)
**Supported by:** [tk-…](#tk-…) (parenthetical), [tk-…](#tk-…) (parenthetical)
**Supersedes:** [tk-…](#tk-…) (what changed) — *only when this entry overrides a prior one*
```

The identifier is `tk-NNN` on the trunk branch and `tk-<branch>-NNN` on any other
branch — see "entry identifier" below for the rule and the merge-collision
rationale. The anchor id and the title must use the **same** identifier so
`[tk-…](#tk-…)` links resolve.

The `<a id="tk-NNN"></a>` line is what makes `[tk-NNN](#tk-NNN)` references elsewhere in the file (and in `**Supported by:**`) click-through in any markdown viewer that follows the HTML anchor (GitHub, IDE preview, mdbook, browser-rendered Markdown). The explicit anchor is stable even if the title text gets edited later — the link target doesn't depend on slugged heading text.

The parenthetical RID in the title is itself a markdown link to a deriva-ml **citation URL** (see "Title includes the durable catalog handle" below) — clicking it opens the snapshot-pinned record for that catalog entity. Every RID reference in an entry, anywhere, is rendered the same way.

### `tk-[branch-]NNN` — entry identifier (branch-scoped to avoid merge collisions)

Every entry gets a unique identifier. The form depends on where you're authoring it:

- **On `main`** (or whatever the trunk branch is): `tk-NNN`, where `NNN` is a
  three-digit zero-padded integer (`tk-001`, `tk-002`, …). The next number is *one
  more than the highest existing trunk `tk-NNN` in the file*.
- **On any other branch** (a feature/work branch whose `tacit-knowledge.md` edits
  will later merge into trunk): `tk-<branch>-NNN`, where `<branch>` is a short slug
  of the current git branch and `NNN` is sequential *within that branch's entries*
  (`tk-ingest-001`, `tk-ingest-002`, …). Derive `<branch>` from `git rev-parse
  --abbrev-ref HEAD`: lowercase, drop any `feat/`/`fix/`/`chore/`/`docs/` prefix,
  replace non-alphanumerics with `-`, and trim to ~12 chars (e.g.
  `feat/ingest-spec-routing` → `ingest-spec`). Keep it stable for the life of the
  branch.

**Why branch-scope the number.** `tacit-knowledge.md` is append-only and lives in
the repo, so two branches editing it in parallel both reach for the next sequential
`tk-NNN` — and on merge they either collide on the same number/anchor or silently
duplicate it. Scoping the number to the branch (`tk-ingest-001` vs `tk-explore-001`)
makes concurrent-branch entries **collision-free by construction**: distinct anchors,
no renumbering, a clean three-way merge. Trunk entries keep the bare `tk-NNN` so the
common single-line-of-work case is unchanged and existing entries stay valid.

The identifier is stable because the file is append-only: nothing is ever
renumbered, and `tk-042` / `tk-ingest-001` always refers to the same decision. This
stability is what makes the **Supported by** chain possible — `Supported by:` and
in-body links use the full identifier exactly as authored (`[tk-ingest-001](#tk-ingest-001)`),
so cross-branch references keep resolving after the merge.

`tk-[branch-]NNN` is *the entry's* identifier — distinct from the catalog RID in the
title. The title's RID identifies the *catalog artifact* the entry is about; the
`tk-` id identifies *the decision record itself*. Both coexist because they serve
different lookup needs: `tk-019` lets entries point at other entries; `8KG` lets
entries point at catalog artifacts.

Three digits gives 999 entries per branch (and per trunk) before extending to four —
ample headroom. At `tk-999` the next is `tk-1000`; the column just gets a bit wider.

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
   the tombstone is the only addition. This is the **one narrow exception** to "an
   entry's text doesn't change once written": the entry's existing prose is never
   edited, but exactly one line may be appended after it, and only ever this line.

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

### Walking the chain

Together, `tk-NNN` + `Supported by:` give every entry a place in a directed acyclic graph: nodes are entries, edges run from each entry to the ones it was built on. Tracing back from any entry yields a tree of support. The shape mirrors `deriva_ml_get_lineage` on a catalog artifact (which walks producing-execution back to root datasets) — this is the same idea applied to decisions.

Practical uses of the chain:
- "Why did we make this decision?" — walk `Supported by:` back to find the original constraint.
- "What did we abandon?" — find dead-end entries that no later entry lists as `Supported by:`.
- "What's the root cause of this project's current state?" — find entries no other entry supports.

## What an entry contains

Each entry is a short markdown block describing one decision or run, anchored on the RID of the entity it's about. Entries answer questions like *why* a dataset / feature / split / config was chosen, *what* the goal of a run was, *how* the project arrived at the current configuration, and *where* a non-obvious decision came from.

**Every RID mentioned in an entry is rendered as a click-through markdown link** — this is the plugin-wide rule (`deriva-ml-context` → "Always render a RID as a click-through link"), not specific to this file; entries are just one place it applies. Use `ml.cite(rid)` for the URL: `[execution 8KG](https://localhost/id/96/8KG@2P-XYZW)`. In an entry it applies in the title parenthetical, in body prose ("compared against the 8KG baseline"), and in the `**Supported by:**` parentheticals — anywhere a RID appears.

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
- **Title starts with the entry identifier** — `tk-NNN` on trunk, `tk-<branch>-NNN` on a work branch (see "entry identifier" above). The next number is one more than the highest existing identifier *in the same scope* (trunk numbers count trunk entries; a branch's numbers count that branch's entries).
- **No dates in titles.** Time information lives in the `**When:**` header field, not the title; embedding a date in the title duplicates that field and rots if the entry is later edited.
- **No author names in titles.** Attribution lives in the `**By:**` header field. Embedding a name in the title (`### tk-042 — Carl's animal subset`) duplicates the field and forces a title edit if attribution changes (e.g., adding a second decider).
- **Title includes the entry's anchor in parentheses** — the navigation handle for what the entry is *about*, drawn from the anchor taxonomy (see `references/anchor-taxonomy.md`). An anchor can be a catalog artifact (Family A), a process (Family B), or a socio-technical/domain subject (Family C) — not only a RID. When the anchor is a catalog artifact, render it as a click-through markdown link via the deriva-ml citation API so the link is browser-openable and snapshot-pinned:
   - Model run → **execution RID** (`### tk-042 — ... ([execution 8KG](https://localhost/id/96/8KG@2P-XYZW))`)
   - Feature creation → **feature RID** (`### tk-043 — ... ([feature 9PQ4](https://localhost/id/96/9PQ4@2P-XYZW))`)
   - Vocabulary addition (terms only) → **vocabulary RID** (`### tk-044 — ... ([vocabulary 9PR0](https://localhost/id/96/9PR0@2P-XYZW))`)
   - Dataset creation or split → **dataset RID with version** (`### tk-045 — ... ([dataset 7KE v0.4.0](https://localhost/id/96/7KE@2P-XYZW))`)
   - Schema change → **table RID** (`### tk-046 — ... ([table 5-AB12](https://localhost/id/96/5-AB12@2P-XYZW))`)
   - Process knowledge (how the work is done) → **the owning skill name**, as bare
     text, no `ml.cite` (`### tk-047 — Convention — we always dry-run a sweep first (dataset-lifecycle)`)
   - Social/team fact → a short **role/convention phrase**, no RID
     (`### tk-048 — QC criteria owned by the pathology reviewer`) — observe the
     Family-C privacy constraint in `references/anchor-taxonomy.md`
   - Domain concept → the **`docs/domain/` subject**
     (`### tk-049 — Staining varies across the two sites (domain: staining-variance)`)

   For a catalog artifact the URL inside the markdown link comes from `ml.cite(rid)` —
   the deriva-ml citation API; for Family B/C anchors there is no citation URL, since
   the bare handle is the anchor. The persona writing the entry already has a
   `ml = DerivaML(...)` instance in scope (the same one being used for the action this
   entry records); call `ml.cite("8KG")` and it returns
   `https://{host}/id/{catalog}/8KG@{snapshot_time}` — a **permanent citation URL**
   that pins the catalog snapshot at write-time so the link still resolves to the same
   record years later, even after subsequent catalog writes. Default behavior is the
   permanent (snapshot-pinned) URL; `ml.cite(rid, current=True)` returns the
   current-state URL without a snapshot suffix, but the snapshot-pinned form is what
   you want for tacit-knowledge entries.

   The link is markdown — `[execution 8KG](url-from-cite)` — not bare text. This is the **durable** way to reference catalog entities from a markdown-rendered document: a reader in any viewer (GitHub, IDE preview, mdbook, browser-rendered Markdown) can click through and land on the catalog record.

   This is distinct from `deriva://catalog/{host}/{cat}/deriva-ml/...` **resource URIs**: those are for *queryable* resource references (MCP tools, programmatic fetches against a live catalog). Citation URLs from `ml.cite(rid)` are for *click-through navigation by a human reader*. Both have their place; this section's title-handle convention uses the citation URL because the audience is a future reader, not a tool.

   Describing the *kinds* of supporting artifacts ("three terms were created"; "model weights, training log, prediction CSV are linked to the execution") is fine and helpful. Reference RIDs sparingly, but **always name at least one representative supporting RID** a cross-domain reader can click through to ("the 8KG run that established the 20% baseline"). Every RID mentioned anywhere in the entry — title parenthetical, body prose, `**Supported by:**` parentheticals — is rendered as `[label](ml.cite(rid))`, never as bare text. Don't enumerate every supporting RID — they go stale, and the catalog already has them linked to the title's handle.

   For entries that don't correspond to a single catalog artifact, prefer a Family B (process = skill name) or Family C (domain subject / role phrase) anchor from `references/anchor-taxonomy.md` — it makes the entry retrievable by the generalization walk. Only when *no* anchor from any family fits (a purely cross-cutting reasoning entry) may the parenthetical be omitted, with `tk-NNN` as the sole identifier.
- **Length is set by content.** Long enough to answer the six entry parts; short enough to scan in one pass (~5–15 lines in practice).
- Past tense — these are settled records, not plans.

**Content principles:**

- **Dead ends are valid standalone entries.** When alternatives were weighed and the chosen path didn't pan out, write the dead-end entry on its own — no successor decision required. Dead ends are the highest-leverage tacit knowledge on a multidisciplinary team: the ML designer doesn't know that "we tried using FFPE stain type as a model input and it didn't work because staining variance dominated the signal" was a year of unproductive work the previous lab burned through. Title it after the dead-end action itself (`### tk-026 — Tried stain_type as model input; abandoned ([execution 3-XYZ](url-from-ml.cite))`).
- **Recurring patterns are also valid.** Entries of the form *"whenever we do X in this project, we also do Y because Z"* are tacit knowledge about the project's conventions — not directives. They're statements about *what this project's pattern is*, written for a future reader who's about to do X and would benefit from knowing the pattern exists. Example: `### tk-031 — Convention — releasing a dataset bumps src/configs/datasets.py` (rationale: experiment configs pin by version, so a release that isn't reflected in the config is unreachable from runners). The reader chooses whether to follow the pattern; the entry explains why the pattern exists. Convention entries usually have no catalog-RID handle in the parenthetical — the `tk-NNN` is sufficient identifier.
- **Reference RIDs and include quantitative evidence** (counts, sizes) when known — but as evidence for the reasoning, not as a replacement for it. See "What doesn't belong here — catalog data vs. tacit" below.

## What doesn't belong here — catalog data vs. tacit

An entry records *why*, not *what*. The catalog is the source of record for facts; an entry points at facts but doesn't replicate them, because anything the catalog can go stale on will silently rot what you wrote. Concretely, **don't write**:

- **Vocabulary term lists.** "The `Workflow_Type` vocab has terms X, Y, Z" goes stale the next time a term is added. Link to `deriva://catalog/{host}/{cat}/deriva-ml/vocabularies/deriva-ml/Workflow_Type` and let the reader fetch.
- **Dataset RID / type / description tables.** "13 datasets: 96E (Complete, Labeled, …), 96R (Split, …), …" is catalog data. Link to `deriva://catalog/{host}/{cat}/deriva-ml/datasets` instead. (A *short* table mapping the user-facing config name to a stable RID is fine when those names are themselves project decisions — the catalog doesn't store the mapping from `cifar10_small_labeled_split` to `CRR`. That's tacit.)
- **Schema field types or column lists.** Catalog data; fetch `deriva://catalog/{h}/{c}/schema` or the table resource.
- **Workflow URLs / checksums / version strings.** Catalog data; live in `Workflow` rows.
- **Asset MD5s, file sizes, lengths.** Catalog data.
- **Execution status, start/stop times, lineage edges.** Catalog data; fetch `deriva://catalog/{h}/{c}/deriva-ml/execution/{rid}` or `…/ml/lineage/{rid}`.
- **PR numbers, commit SHAs, issue IDs.** Git/forge coordinates are *archaeology*, not behaviour — they tell a reader *where the change landed*, not *what the change actually does*. The thing future readers need is the durable behavioural claim; the PR number is incidental and rots when the repo is mirrored, renumbered, or migrated. Name the behaviour. If git traceability genuinely adds value, the catalog's `Workflow.URL` column already pins the commit SHA — link to that, not to a PR.

  **Wrong** (cites a transient PR coordinate as the thing being said):

  > "PR #46 makes auto-composed Execution descriptions only fire for `+experiment=` overrides; bare `model_config=` runs default to 'Simple model run'."

  **Right** (the durable behaviour is the subject; the PR number is gone):

  > "Auto-composed `Execution.description` strings only fire when a Hydra experiment preset is in use (`+experiment=...`). Bare `model_config=` / `datasets=` overrides without an experiment preset fall back to the literal string 'Simple model run'. Workaround: define a one-line experiment preset for the variation you want a meaningful description for; don't try to pass `description=` directly, which Hydra's grammar rejects for free-form strings."

  The shape to learn: PR numbers describe the *change*; tacit entries describe the *behaviour the change left in place*. Always write the behaviour.

**Do write**: why the dataset was created, why the workflow's type was chosen, why a hyperparameter was selected, what alternatives were rejected and why, what would invalidate this decision, what a future reader needs to know to evaluate whether the decision still holds.

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
