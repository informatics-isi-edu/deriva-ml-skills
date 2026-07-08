# Retrieval Catalog and Retrieval Mechanics

This reference documents the *derived retrieval catalog*
(`docs/tacit-knowledge/retrieval-catalog.md`) and how retrieval reads, rebuilds, and
classifies against it. It is the machinery behind SKILL.md's retrieval and write steps.
The corpus is permanently small (a few hundred entries), so the whole loop is a
read-and-rewrite of small files.

> **Terminology.** This doc says "the catalog" and "the index" interchangeably for the
> *same* file, `retrieval-catalog.md` — a derived lookup over the Log. It is a machine
> catalog, not the OKF `index.md` browse-convention (see "The retrieval catalog" below).
> **Primary path is the bundled `tk_lookup.py` script** (see "The lookup script"); the
> hand-grep procedure documented here is the fallback the LLM uses when the script is
> unavailable, and the reference spec the script implements.

**The one thing to get right about how this works.** Entries live in
`tacit-knowledge.md` and **never leave it** — they are never moved, copied, or split
into per-topic files. Progressive disclosure ("load only what's required") does **not**
come from scattering entries across files. It comes from a **derived index of
pointers**: the rebuild reads the Log and emits one small row per entry (anchor,
keywords, `tk-NNN`) that *points back at* the entry. At retrieval the LLM reads the
compact index to decide *which* entries are relevant, then opens `tacit-knowledge.md`
and reads **only those few entries** — not the whole Log. The index is a phonebook, not
the phone: it tells you which entries to open; the entries stay in one append-only book
that only grows. (Splitting entries by topic was explicitly rejected — design spec D1 —
because it would destroy chronology-as-structure, break the in-document `Supported by:`
links, and forfeit clean append-only merges. The only sanctioned split is by *time*
— archived eras in the same Log format — never by topic.)

## The retrieval catalog (`docs/tacit-knowledge/retrieval-catalog.md`)

A conformant OKF **document** of a custom `type: RetrievalCatalog` — YAML frontmatter
(required by the OKF file format) + a Markdown table body (OKF favors tables). It is
**not** the reserved `index.md` browse-convention: it is a machine *lookup* over the
Log's entries, not a directory browse-list, so it is a normal OKF document that keeps its
frontmatter and does not take the `index.md` name. (`docs/domain/index.md` is the one true
OKF `index.md` here — frontmatter-free, lists its directory. See
`references/file-mechanics.md` → "OKF layout at a glance".)

It is a **cache, not a record**: delete it and retrieval still works (it degrades to a
supersession-aware Log scan); a stale catalog only slows retrieval, never corrupts it. It
is **rebuilt whole, never incrementally patched**, and every row is a *descriptive
reflection* of the Log — it originates no authority (D4).

### Frontmatter

```yaml
---
type: RetrievalCatalog
title: Tacit Knowledge — retrieval catalog
description: Derived lookup over tacit-knowledge.md — one greppable row per entry. Cache, not record.
generated_from: tacit-knowledge.md
generated_at: <ISO 8601 timestamp of the rebuild>
generator: capture-tacit-knowledge rebuild
covers_through:
  id: tk-NNN        # the last tk-… id folded into the catalog (correctness boundary)
  offset: 12345     # byte offset of the END of that entry in the Log (fast-path)
tags: [tacit-knowledge, retrieval-catalog, deriva-ml]
---
```

`covers_through` is the boundary between what the catalog covers and the **un-indexed
tail** (entries appended since the last rebuild). It does double duty: retrieval seeks to
it to read only the tail (below), and the rebuild counts entries past it to decide when
to fire (D7). `generated_at` is a human-readable audit field, **not** the retrieval
boundary — the id/offset pair is.

### Rows — lean and greppable (the only body)

One row per entry, one line each. The catalog carries **only** the fields retrieval
actually greps on — the "full OKF-index" enrichment (version/owners/relationships/aliases
columns, browse sections) was reverted because it was built against a wrong model of an
OKF index and taxed the grep hot path for no retrieval gain.

| column | what it holds | derived from |
|---|---|---|
| **`tk-NNN`** | the entry id — the deref key (grep the Log's `<a id="tk-NNN">`). MAY be rendered as a click-through link `[tk-042](../../tacit-knowledge.md#tk-042)` for human navigation, but the raw `tk-NNN` string MUST appear literally so grep matches it. | the entry's `<a id>` anchor |
| **`anchors (all scopes)`** | **every** anchor scope the entry applies at — instance RID **and** its type/`*_Type` **and** the abstraction **and** the process/skill — as literal text. The generalization walk greps each widened scope, so a row that only carried the instance RID would be missed by the type-grep. | the entry's title handle + body (anchor taxonomy) |
| **`keywords (+ synonyms)`** | topic-CV terms the entry classifies under, **including their CV synonyms** as literal text — so a query using a synonym ("oversample") still hits an entry that used a different word ("SMOTE"). This is the substring/vocabulary-gap fix. | the classification pass + `topics.md` synonyms |
| **`superseded-by`** | `tk-MMM` if a later entry superseded this one, else empty — mirrors the entry's tombstone (D2); the catalog never *originates* currency. | the entry's tombstone edge |

Below the table, a **candidate-terms** list — topic-CV keywords the discovery pass (below)
proposes but a human has not confirmed. A *proposal queue*, not authority; regenerated
each rebuild.

**Determinism.** The rows are a deterministic function of the Log — same Log in, same rows
out. Only `candidate-terms` is non-deterministic (LLM discovery pass), which is fine
because candidate terms carry no authority.

**Greppability is the one hard rule.** Each entry is one line with its `tk-NNN`, anchors,
and keywords+synonyms as literal matchable text — that is what makes the row greppable and
keeps candidate-finding O(matches), not O(entries). Do not wrap a row across lines; do not
hide an anchor behind a link label grep can't see.

**Descriptive, never stateful.** The catalog is a phonebook: retrieval uses it to find
*candidates*, then opens and **quotes the actual entries** (via the `tk-NNN` → Grep/Read
extraction above), never the catalog's keyword summary.

## The lookup script (`tk_lookup.py`) — the primary retrieval path

Retrieval runs through the bundled **`scripts/tk_lookup.py`** first. It does the entire
procedure below deterministically — so the LLM does not hand-execute the multi-step grep
walk, and the logic has one tested home that can grow (synonym expansion today, semantic
lookup later) without the skill's prose drifting:

```bash
uv run python <deriva-ml-skills>/skills/capture-tacit-knowledge/scripts/tk_lookup.py \
  --repo-root . <anchor / keyword / skill terms>          # add --ids-only for just ids
```

It: (1) **expands** the query terms through the topic-CV synonyms (`topics.md`) — closing
the substring/vocabulary gap a raw grep can't; (2) **matches** catalog rows (the
generalization walk, over rows that carry all anchor scopes as literal text); (3) merges
the **warm tail** (entries past `covers_through`); (4) applies the **supersession filter**
(catalog `superseded-by` column + tail tombstones); (5) **extracts** each surviving
entry's span from the Log. It prints the entries to quote.

**It is the primary path, not a hard dependency.** Every missing file degrades gracefully
(returns empty / unexpanded, never raises); if the script is unavailable or prints
`(no matching … — fall back to hand-grep)`, the LLM runs the hand-grep procedure below,
which is *also* the reference spec the script implements. Correctness never hard-depends
on the script — same guarantee the catalog gives over the Log. (Bundling a script here is
consistent with the plugin's other scripts — `seed_tk_topics.py`, `check_versions.py`;
the retrieval procedure is code-shaped and only getting more so.)

## Retrieval at the moment of action (Mode A) — the hand-grep procedure (fallback + spec)

**Goal: context-window economy.** Load only what is required so as not to blow the
context store. The index bounds the token cost; the Log's front is never scanned.

**v1 scope note (D8).** The index's `generated_from` is `tacit-knowledge.md` only —
retrieval in v1 indexes and reads the **Log**, not the domain-background Concept docs
in `docs/domain/`. A domain doc is reached indirectly, via a Family-C anchor recorded
on a Log entry, not by direct index lookup. Weaving domain-background retrieval and
decision retrieval into a single dual-source loop (`generated_from` spanning both the
Log and `docs/domain/`) is a **deferred phase**, not part of this build.

Two-part read along the cold/warm boundary:

1. **Cold history (the bulk): *grep* the index — never load it whole.** The index is a
   file of rows, one per entry, so it grows with the corpus. Do **not** read the whole
   file to find candidates — that would reintroduce the O(N) cost the index exists to
   avoid, just one layer up. Instead **`Grep` the index for rows matching the current
   anchor(s) and keyword(s)** and read only the matching rows:

   ```
   Grep(pattern='Patient_Split|Dataset|dataset-lifecycle',
        path='docs/tacit-knowledge/retrieval-catalog.md',
        output_mode='content')
   → the handful of rows whose anchor/keywords match → their tk-NNN ids
   ```

   You read ~5 matching rows, not all 500. **This is what makes the index scalable:
   retrieval cost is O(matches), not O(entries) — a 5,000-row index costs the same to
   query as a 50-row one, because you never load it whole.** It also means the index's
   *rich* columns (relationships, aliases, per-family sections, navigation) are **free on
   the hot path** — they sit in rows you never read unless they match, so richness for
   humans/tools costs the retrieval loop nothing. Grep is substring, not semantic, so the
   **generalization walk** (below) is done by grepping for *each* widened term (the
   instance RID, then its type, then the abstraction, then the process/skill) — a handful
   of bounded greps, still never a full read.

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

### Extracting one entry by id — the concrete tool sequence

The index hands you a `tk-…` id; here is exactly how to pull *that one entry* out of
`tacit-knowledge.md` without reading the whole file. The id is the join key: the same
string is the index's `tk-NNN` column **and** the entry's `<a id="tk-NNN">` anchor line
in the Log. Every entry is a span from its own anchor to the next one:

```markdown
<a id="tk-042"></a>
### tk-042 — <title> ([execution 8KG](…))
**When:** …
**By:** …
<body…>
                          ← blank line
<a id="tk-043"></a>       ← the NEXT entry's anchor marks the end of tk-042
```

**Two-step extraction (the low-token path):**

1. **Locate the entry by its anchor** — `Grep` for the literal anchor string and get its
   line number:

   ```
   Grep(pattern='<a id="tk-042">', path='tacit-knowledge.md', output_mode='content', -n=true)
   → tk-042 begins at, say, line 812
   ```

2. **Read only that span** — `Read` a bounded window starting at that line. Entries run
   ~5–15 lines (entry-format.md), so a `limit` of ~30 comfortably captures one and stops
   well short of the next:

   ```
   Read(path='tacit-knowledge.md', offset=812, limit=30)
   → the tk-042 entry (stop quoting at the next `<a id="tk-…">` line you see in the window)
   ```

   Reading the window, not the file, is the whole point: you pulled one entry out of a
   several-hundred-entry Log at the cost of ~30 lines.

**Batch shortcut.** With several ids to fetch, one `Grep` over all their anchors returns
all the start lines at once (`Grep(pattern='<a id="tk-(042|118|231)">', …, -n=true)`), then
one `Read` per span. Don't loop a whole-file read per id.

**The un-indexed tail is the exception — no per-id grep needed.** Warm-tail entries
(step 2 above) are already a contiguous block from `covers_through.offset` to EOF, so you
read that block once and split it on `<a id="tk-…">` markers; you don't grep each tail id
individually.

**Why no compiled retriever.** There is no extraction *function* — the "retriever" is you
(the LLM) running `Grep` → `Read`. The `<a id="tk-NNN">` anchor makes each entry
addressable by a unique, stable string, which is what turns "find one entry in a big
Markdown file" into a cheap two-tool lookup instead of a full read. This is viable
precisely because the corpus is permanently small and the id is exact.

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
  entry, run the discovery pass (below), and write `retrieval-catalog.md`.
- **Visibility: silent but noted in one line** — e.g. "refreshed the tacit-knowledge
  index — 12 new entries folded in." Never a question or a blocker; an honest breadcrumb.
- **Do NOT auto-commit the rebuilt index.** It travels with the next normal commit (a
  derived file a reviewer sees alongside the entries that produced it), consistent with
  "commit only when asked."

## Merge and the normalizer (D12)

The tacit-knowledge files use `.gitattributes` merge drivers so collaborators merge
cleanly:

```
tacit-knowledge.md                        merge=union
docs/tacit-knowledge/topics.md            merge=union
docs/tacit-knowledge/retrieval-catalog.md merge=union   # regenerated post-merge; never hand-merged
```

- **Log = union merge.** Both branches append at EOF; union concatenates both sides.
  Branch-scoped IDs guarantee the union is well-formed.
- **Index = union merge + regenerate.** A union'd index is a meaningless cache — rows
  from both branches interleaved with no guaranteed structure — but that's harmless,
  not corrupting: the very next capture-triggered rebuild discards the merged file
  wholesale and re-derives it fresh from the merged Log. Using `merge=union` here
  (rather than `merge=ours`) matters because `merge=ours` is not a git built-in — it
  requires `git config merge.ours.driver true` registered per-clone, which nothing
  here sets up, so an unconfigured clone gets a real merge *conflict* on concurrent
  index edits instead of a clean merge. `merge=union` is a built-in driver and needs
  no such setup.
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

## How the knowledge reorganizes as entries accumulate

As the Log grows, the structure keeps up **without touching the entries** — this is what
"self-organizing" means here, and the boundary is strict:

- **The Log never reorganizes.** Entries are append-only and chronological; you never
  move, regroup, renumber, rewrite, or re-file an entry as more accumulate. Chronology
  *is* the structure — it preserves the `Supported by:`/`Supersedes:` DAG, keeps the file
  reading top-to-bottom as project history, and is what makes the file trivially
  mergeable. Reorganization happens **only in the derived layer** (the index and the
  topic CV), which is regenerable and carries no authority.
- **The topic CV is where organization actually evolves.** Each rebuild's discovery pass
  (above) is the reorganization: it re-derives which terms the corpus needs, so the
  vocabulary tracks what accreted rather than what the seed guessed. The index then
  re-groups entries under the current terms — wholesale, from scratch, every rebuild.

**Worked example — one rebuild, ~40 entries in.** The discovery pass reads the whole Log
and proposes (into `candidate-terms`, for the human to confirm):

- **Merge (drift):** entries tagged `confidence-filtering` and `qc-thresholding` are the
  same theme under two names that crept in months apart → fold into one term, the other
  becomes a synonym. *(This is the temporal-drift fix, made concrete.)*
- **Retire (unused):** the seed shipped `tooling-gotcha`, but no entry ever matched it →
  propose retiring it so the CV stays readable.
- **Add (emergent):** six entries across datasets and models all turn out to be about
  the same underlying concern — the model not generalizing across the two clinical sites
  — which no seed term names → propose a new `cross-site-generalization` term, because a
  future teammate *would* search on it to find those six entries (the findability test).

None of this rewrites an entry. The entries keep their original text and dated order; only
their `concept keywords` (a derived index column) get recomputed under the refreshed CV,
and the CV itself gains/loses/merges terms — all human-gated via the queue.

**What is NOT built yet — flat now, clustered later.** The index is intentionally
**flat**: a single keyword column, no theme hierarchy. Grouping the CV terms into a
theme tree (so retrieval could browse by theme, not just match by term) is a deliberate
future evolution — it can be layered over the same flat rows with **no entry touched and
no data migrated**, so nothing here blocks it, and at the small N this system lives at,
anchor + flat-keyword lookup is the high-value path. Do not hand-build a cluster
hierarchy in v1; if theme-browsing is ever needed, it groups the (small, human-reviewed)
CV terms, not the entries.
