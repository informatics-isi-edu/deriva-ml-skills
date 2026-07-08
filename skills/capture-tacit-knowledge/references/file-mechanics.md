# File Mechanics for `tacit-knowledge.md`

The file lives in the **project root** alongside `CLAUDE.md`, `pyproject.toml`,
and other project-level files. It must be tracked in git — it's part of the
project's permanent record.

## First-time setup

If the file does not exist yet:

1. Verify `tacit-knowledge.md` is not in `.gitignore` (search for the
   filename and for any glob that would match it — e.g. `*.md`, `outputs/`,
   `.cache/`).
2. Never place the file in a directory that is gitignored. Project root is
   the only correct location.
3. Create the file as an **OKF Log document**: a YAML frontmatter block
   (`type: Log`, `title`, `description`; `resource` omitted) at the very top,
   then the `# Tacit Knowledge` H1, then the boundary-explaining header
   paragraph that distinguishes *tacit knowledge* from *catalog facts* so a
   reader hitting the file knows what belongs in it. See
   `references/entry-format.md` → "File header — OKF Log frontmatter" for the
   exact block, and the model template's `tacit-knowledge.md` for the canonical
   header wording.

   In a fresh project, prefer running `scripts/seed_tk_topics.py` (see "Companion
   artifacts" below) — it creates the Log *and* the four companions in one step,
   instead of hand-creating just the Log.
4. `git add tacit-knowledge.md` immediately so it does not get lost.

## Companion artifacts (created by the seed script)

The Log is not alone. Four companions and a merge-driver file complete the system,
all scaffolded by `scripts/seed_tk_topics.py` (run once at project setup, not
user-invocable in the loop):

| Artifact | Path | Type |
|---|---|---|
| The Log | `tacit-knowledge.md` (project root) | `Log` — append-only |
| Derived retrieval catalog | `docs/tacit-knowledge/retrieval-catalog.md` | `RetrievalCatalog` — cache, rebuilt whole |
| Topic CV | `docs/tacit-knowledge/topics.md` | `Vocabulary` (controlled-term list) — human-gated |
| Domain-background bundle | `docs/domain/` (+ `index.md`) | `index.md` (no frontmatter) over `Concept` docs — refined in place |
| Merge drivers | `.gitattributes` | `merge=union` (Log, CV, and catalog) |

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

## OKF layout at a glance

The whole system in one place — the directory tree, and the OKF `type` of every file.

```
<project root>/
├── tacit-knowledge.md              type: Log              — the append-only journal of *why*
├── .gitattributes                  (git config)           — merge=union for the three files below
└── docs/
    ├── tacit-knowledge/
    │   ├── retrieval-catalog.md    type: RetrievalCatalog — derived lookup over the Log (cache, rebuilt whole)
    │   └── topics.md               type: Vocabulary       — the topic CV (controlled-term list)
    └── domain/
        ├── index.md                (OKF index.md — NO frontmatter) — lists the Concept docs below
        ├── staining-variance.md    type: Concept          — one subject per file
        └── cohort-skew.md          type: Concept          — …refined in place over time
```

**Two OKF levels — don't conflate them.**

- The **OKF file format** binds every OKF document: YAML frontmatter with a non-empty
  `type` + a free-form Markdown body (tables allowed). Custom `type` values are
  conformant; extra frontmatter keys are allowed and preserved.
- The **`index.md` convention** is a *special reserved filename*: the **one** OKF document
  that carries **no frontmatter**, whose body is `# heading` sections of
  `* [title](url) - description` bullets enumerating **its own directory's files**, for
  human browsing.

So: `tacit-knowledge.md`, `retrieval-catalog.md`, `topics.md`, and each `Concept` doc are
normal OKF **documents** (frontmatter + `type`). Only `docs/domain/index.md` is the
frontmatter-free `index.md` convention — because it, and only it, enumerates its
directory's files.

**Why the catalog is `retrieval-catalog.md`, not `index.md`.** It catalogs the **Log's
entries**, not its directory — that is a lookup structure, not a directory browse-list, so
it is a normal OKF document (`type: RetrievalCatalog`, frontmatter kept) and does **not**
take the reserved `index.md` name. The `docs/domain/index.md` correctly *does* take the
name and *correctly carries no frontmatter*: it lists the sibling `Concept` docs, exactly
what OKF `index.md` means.

**The document `type` values here** (all conformant custom types — OKF `type` is
open/extensible; consumers tolerate unknown types):

| `type` | What it is | In this system |
|---|---|---|
| `Log` | append-only journal; dated entries | `tacit-knowledge.md` — the source of *why*; never reorganized |
| `RetrievalCatalog` | a derived, whole-rebuilt lookup over Log entries — one greppable row per entry (descriptive only, never stateful) | `docs/tacit-knowledge/retrieval-catalog.md` — the retrieval accelerator; a cache, not a record |
| `Vocabulary` | a controlled-term list the entries are classified against | `docs/tacit-knowledge/topics.md` — the topic CV; human-gated |
| `Concept` | a semantic doc about one subject, refined in place | each `docs/domain/<subject>.md` |
| *(none — `index.md`)* | the frontmatter-free directory browse-list | `docs/domain/index.md` — NOT a `type`; the OKF index convention |

There is no `ConceptBundle` type — a "bundle" is just a directory of `Concept` docs with a
frontmatter-free `index.md` listing them.

## Concepts, files, tags, and type — the relationships, concisely

Four terms get confused; here is each, once:

- **A Concept is a file.** In the `docs/domain/` bundle, one `type: Concept` markdown
  file = one subject (staining variance, cohort skew). The bundle is just the directory
  of those files, with a frontmatter-free `index.md` at its root that lists them.
- **`type`** is the OKF *kind* of a document (`Log` / `RetrievalCatalog` / `Vocabulary` /
  `Concept`) — it says what the file is and how it behaves (append-only journal vs.
  regenerable retrieval cache vs. controlled-term list vs. refined-in-place subject doc).
  One value per file, in its frontmatter. (The `index.md` is the exception — it carries
  **no** `type` and no frontmatter; it is a convention, not a document type.)
- **`tags`** is OKF *document-level* descriptive metadata — free keywords describing the
  *whole file*. Its job is to let a human (or coarse search) tell sibling files apart
  within a directory (which Concept doc is about site-effects vs. cohort-effects). It is
  **not read by retrieval**; the LLM never matches on it.
- **`concept keywords`** (note: *not* the same as a `type: Concept` doc, despite the
  word) are the **per-entry classification** of a Log entry, drawn from the topic CV
  (`topics.md`) and stored as a column in the *derived retrieval catalog* — **not** in the entry and
  **not** in `tags`. This is the LLM-managed, human-gated classification.
- **`anchor`** is the **primary retrieval key** — *what a Log entry is about* (a RID, a
  type, a process/skill, or a `docs/domain/` subject). Retrieval walks anchors, not tags.

The one-line mental model: **`type` = what kind of file; `tags` = how a human tells
sibling files apart; `concept keywords` = how a Log entry is classified (in the catalog);
`anchor` = what a Log entry points at (how the LLM retrieves it).** A `type: Concept`
*file* and an entry's `concept keywords` are unrelated despite sharing the word "concept."

### The `.gitattributes` merge drivers matter

`merge=union` needs no extra git config (it's a built-in driver), and all three
tacit-knowledge files use it. It makes the Log and topic CV merge cleanly when two
teammates append in parallel. The index also unions — a union'd index is a
meaningless cache (rows from both branches interleaved with no guaranteed
structure), but that's harmless: the next capture-triggered rebuild discards it
whole and reconciles a fresh index against the merged Log. (`merge=ours` was
considered and rejected for the index: it is not a git built-in — it requires
`git config merge.ours.driver true` registered per-clone, which nothing sets up, so
an unconfigured clone would hit a real merge conflict instead.) See
`references/index-and-retrieval.md` → "Merge and the normalizer" for why, and for
the post-merge normalizer that repairs any line-level interleaving `merge=union`
can introduce.

## Relationship to other project files

| File | Role |
|---|---|
| `tacit-knowledge.md` | *Why* — intent and reasoning behind decisions |
| `experiments.md` (if present) | *What* — what each experiment configuration does (parameters, inputs, outputs) |
| `CLAUDE.md` | Project-level instructions for Claude |
| Hydra configs (`src/configs/...`) | Define experiment parameters |

Reference `tacit-knowledge.md` from `CLAUDE.md` so new sessions pick up
the context.
