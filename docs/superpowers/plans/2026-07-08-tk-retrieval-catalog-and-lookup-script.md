# TK Retrieval: Typed Catalog + Optional Lookup Script

**Status:** planned, not started. Consolidates decisions from the 2026-07-07/08
retrieval-index design conversation.

## Decisions being implemented (both from the user, 2026-07-08)

1. **The retrieval index is a *typed machine catalog* — a conformant OKF *file*,
   but NOT the reserved `index.md` browse-convention.** Two OKF levels, kept distinct:
   - **OKF file format** (binds every OKF document): YAML frontmatter with a non-empty
     `type` + a free-form Markdown body. Custom `type` values are conformant; arbitrary
     extra frontmatter keys are allowed and preserved; the body MAY be a table (the spec
     lists tables among favored structures). → **The catalog conforms to this fully.**
   - **The `index.md` convention** (a special reserved filename): frontmatter-*free*,
     body = bullet lists linking to a directory's files, for human *browsing*. `index.md`
     is the *only* OKF document that omits frontmatter. → **The catalog is NOT this** —
     it's a machine lookup over one Log's entries, not a directory browse-list.

   So: keep the YAML frontmatter (`type: RetrievalCatalog` + `covers_through` etc. —
   required + allowed custom keys); keep the table body (conformant); just don't take the
   `index.md` filename or the frontmatter-free bullet shape. The catalog is a first-class
   OKF document of a custom type — fully spec-conformant as a *file* — that simply isn't
   the directory `index.md`.
2. **Bundle an *optional* lookup script `tk_lookup.py`** that does retrieval
   deterministically, with **graceful degradation to hand-grep** if the script is
   absent/broken. Same "optional accelerator, correctness floor underneath"
   architecture as the index-vs-Log relationship itself.

## Why this is the resolution (context for a fresh reader)

The retrieval index churned over several turns: renamed, richer-typed, given
"full OKF-index parity" (`version`/`owners`/`relationships`/`aliases`/browse
sections), then grep-optimized to de-cost that richness. The parity work was built
against a **wrong model of what an OKF `index.md` is** — the real spec says an OKF
index is a *frontmatter-free bullet list of `[title](url) - description` links to a
directory's documents*. Our artifact is none of those things. Decision 1 stops the
mismatch by declaring it a machine catalog, not an index. Decision 2 moves the
increasingly-intricate retrieval *procedure* (generalization walk, supersession
filter, warm-tail merge, synonym expansion) out of LLM-executed prose and into
optional code, because when a procedure gets this precise, code runs it identically
where prose invites drift.

**Scenario validation** (done in-conversation, 2026-07-08) confirmed the grep-based
mechanism works on 5/6 retrieval scenarios; the one weakness (Scenario 4: a query
using different *words* than the entry — "oversample" vs the entry's "SMOTE") is why
synonym-rich keywords + the script's CV-synonym expansion are load-bearing.

## Target row schema (the refined lean catalog)

Keep ONLY the fields the retrieval scenarios proved necessary:

```
| tk-NNN | anchors (all scopes) | keywords (CV terms + synonyms) | superseded-by |
```

- **`tk-NNN`** — the id / deref key (grep the Log's `<a id="tk-NNN">`). MAY be a
  click-through link `[tk-NNN](../../tacit-knowledge.md#tk-NNN)` for human navigation,
  but the raw `tk-NNN` string MUST appear literally for grep.
- **`anchors`** — ALL applicable anchor scopes as literal text: instance RID **and**
  type/`*_Type` **and** abstraction **and** process/skill. (Scenario 3: the
  generalization walk greps each widened scope; the type-grep only hits if the type
  string is in the row.)
- **`keywords`** — topic-CV terms the entry classifies under, **including their CV
  synonyms** as literal text. (Scenario 4: closes the substring/vocabulary gap.)
- **`superseded-by`** — mirrors the entry's tombstone edge (D2). Empty if current.

**DROP** (parity cargo added for the wrong OKF-index goal): `version`, `owners`,
the `relationships` column (the DAG lives authoritatively in the entries; traverse it
by reading the entry, not the catalog — Scenario 2), the separate `aliases` column
(fold synonyms into `keywords`), and the browse sections (`## Summary`,
`## Start here`, `## Inventory by anchor family`).

**KEEP the frontmatter** — `type: RetrievalCatalog` (required by the OKF file format),
plus `covers_through` (id+offset for the warm tail), `generated_from`, `generated_at`,
`generator`, `title`, `description`, `tags` (all allowed: OKF lets producers add
arbitrary keys, consumers preserve them). The frontmatter-free rule applies ONLY to the
reserved `index.md`; this file is a normal OKF document, so it MUST carry frontmatter
with a `type` — keeping it is *required for conformance*, not a leftover. Rename
`type: RetrievalIndex` → `type: RetrievalCatalog`, and the FILE `retrieval-index.md` →
`retrieval-catalog.md` (stops implying it's the directory `index.md`). Note:
`docs/domain/index.md` is the one true OKF `index.md` — but it is **currently
non-conformant and must be fixed** (see the co-discovered bug below).

## Co-discovered bug: `docs/domain/index.md` wrongly carries frontmatter

The same OKF-file-vs-index.md distinction, applied to the *other* file, surfaces a real
defect. OKF: **`index.md` files contain NO frontmatter** — they are the sole exception to
the frontmatter rule; body = bullet-list sections linking the directory's documents. But
our `docs/domain/index.md` currently carries `type: ConceptBundle` + title/description/
tags frontmatter (added during the "richer types" turn). That makes it **non-conformant
as an OKF index**. The `ConceptBundle` type was invented against a wrong model of what an
`index.md` is — OKF index files don't carry a `type` at all.

**Fix (add to the task list):** make `docs/domain/index.md` a real OKF `index.md` —
strip ALL frontmatter; the body is `# heading` sections with `* [subject](subject.md) -
description` bullets enumerating the Concept docs (empty-state: a placeholder line, since
the seed ships no subjects yet). Drop the `ConceptBundle` type entirely. This is the
symmetric correction to renaming the retrieval index: *that* file wrongly claimed to be
an index-ish thing while being a document; *this* file is a real index but wrongly wears
document frontmatter. Both wrong in opposite directions; both fixed here.

## The lookup script (`scripts/tk_lookup.py`)

**Contract: PRIMARY retrieval path, with a hand-grep fallback floor.** `tk_lookup.py`
is the intended way retrieval runs — the LLM calls it first. Hand-grep remains the
documented fallback for when the script is genuinely unavailable (not installed, wrong
env), so correctness never *hard*-depends on it, but the script is primary, not merely
optional. Rationale (user, 2026-07-08): the retrieval procedure is only going to get
*more* sophisticated — synonym/keyword expansion through an evolving topic CV, and
eventual **semantic** lookup — and those belong in tested code, not in an LLM-executed
prose procedure that drifts. Concentrating the logic in one script also *reduces* the
skill's prose surface. The "no compiled code" idea was never a real constraint: the
plugin already ships `seed_tk_topics.py` and `check_versions.py`; the earlier
script-deletion was one script with rotted hardcoded refs, not a blanket ban.

**What it does (deterministically):**
- Input: one or more query terms (an anchor RID/type, a keyword, a skill name).
- Expand each query term through the topic CV (`topics.md`) synonyms → widened term set.
- Grep the catalog rows for any widened term → candidate `tk-NNN` set (the
  generalization walk, done in code).
- Add the warm tail: read entries past `covers_through.offset` → EOF, match them too.
- Apply the supersession filter (drop rows whose `superseded-by` is set; drop tail
  entries carrying a tombstone).
- Extract each surviving entry from the Log by its `<a id="tk-NNN">` span.
- Output: the surviving entries (or just their ids + one-line titles with `--ids-only`).

**Design constraints (mirror `check_versions.py` / `seed_tk_topics.py`):**
- Pure Python stdlib; `_find_uv`-style minimal-PATH robustness NOT needed (no
  subprocess) but DO use the same defensive file-reading (missing files → graceful
  message, exit code, never a stack trace).
- Google-style docstrings; runnable `Example:`.
- Unit tests in `scripts/test_tk_lookup.py` against a synthetic Log+catalog fixture.
- **Rot mitigation** (the reason a prior script-skill was deleted): the script reads
  the row format and anchor convention from the *files themselves*, hardcoding only the
  stable conventions (`<a id="tk-…">`, `covers_through`, the pipe-table shape). A row
  schema change is the one thing that could rot it — so the script and the seed
  renderer share the column contract, and a test asserts they agree.

## Task list

1. **Revert the parity cruft** in `seed_tk_topics.py::render_empty_index_md` back to
   the lean schema (drop version/owners/relationships/aliases/browse-sections); keep
   `covers_through` + machine frontmatter; retype `RetrievalIndex`→`RetrievalCatalog`.
   Update the tests that assert the parity anatomy.
2. **Rename** `retrieval-index.md` → `retrieval-catalog.md` across seed script,
   `.gitattributes` driver, all references, SKILL.md, validate rows, template (git mv).
3. **Update `index-and-retrieval.md`**: the catalog is a typed machine artifact (not an
   OKF index); the lean row schema; anchors-all-scopes + synonym-rich keywords as the
   two scenario-driven requirements; grep-not-load unchanged; add the "optional lookup
   script" section describing `tk_lookup.py` + the hand-grep fallback.
4. **Write `scripts/tk_lookup.py`** + `scripts/test_tk_lookup.py` (TDD).
5. **Wire it in**: SKILL.md retrieval step offers "run `tk_lookup.py` if present, else
   hand-grep"; `file-mechanics.md` OKF-layout map updated (catalog is not an OKF index;
   `docs/domain/index.md` is the one true OKF index).
6. **Record the two decisions in the design spec** (`2026-07-06-…-design.md`): add a
   short decision note (the catalog-is-not-an-OKF-index call + the optional-script call
   + the "no compiled code" tension and why we accepted a script anyway). This is the
   tacit-knowledge-discipline capture, in the spec's decision log (this repo has no
   project `tacit-knowledge.md` of its own).
7. **Fix `docs/domain/index.md` to be a conformant OKF `index.md`** — strip all
   frontmatter (no `type`, no title/description/tags), body = `# heading` +
   `* [subject](subject.md) - description` bullets; drop the `ConceptBundle` type from the
   seed renderer, the OKF-layout map, validate rows, and the template. Update the "five
   types" framing (there are now four document types — Log, RetrievalCatalog, Vocabulary,
   Concept — plus the frontmatter-free `index.md` convention, which is not a `type`).
8. **Regenerate the template** `retrieval-catalog.md` + the fixed `docs/domain/index.md`
   (index-only; do NOT `--overwrite` the hand-authored Log — the known foot-gun).
9. **Conformance sweep + tests green + ruff clean** across both repos.

## Explicitly NOT doing (rejected this round)

- **Idea 2 (split entries into per-type subdirs)** — reverses D1 (one append-only Log).
  Not doing; D1 stands.
- **Reshaping the catalog into an OKF `index.md` bullet list** — user chose "keep it a
  typed catalog." Not doing.
- Concept-clustering, aliases-as-separate-column, the browse sections — all dropped.

## Open risk to watch

The `--overwrite` foot-gun (regenerating the derived catalog also clobbers the
hand-authored Log + domain root). Out of scope to fix here, but Task 7 must avoid it,
and it's worth a future `--only <artifact>` flag on the seed script.
