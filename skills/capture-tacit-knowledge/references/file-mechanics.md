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
| The Log | `tacit-knowledge.md` (project root) | OKF `Log` — append-only |
| Derived retrieval index | `docs/tacit-knowledge/index.md` | OKF `Index` — cache, rebuilt whole |
| Topic CV | `docs/tacit-knowledge/topics.md` | OKF `Index` (controlled-term list) — human-gated |
| Domain-background bundle | `docs/domain/` (+ `index.md`) | OKF `Concept` docs — refined in place |
| Merge drivers | `.gitattributes` | `merge=union` (Log, CV, and index) |

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
├── tacit-knowledge.md              type: Log      — the append-only journal of *why*
├── .gitattributes                  (git config)   — merge=union for the three files below
└── docs/
    ├── tacit-knowledge/
    │   ├── index.md                type: Index    — derived retrieval index (cache, rebuilt whole)
    │   └── topics.md               type: Index    — the topic CV (controlled-term list)
    └── domain/
        ├── index.md                type: Index    — bundle root: an Index *over* the Concept docs
        ├── staining-variance.md    type: Concept  — one subject per file
        └── cohort-skew.md          type: Concept  — …refined in place over time
```

**What each OKF `type` means here:**

| `type` | OKF role | In this system |
|---|---|---|
| `Log` | append-only journal; entries are dated records | `tacit-knowledge.md` — the source of *why*; never reorganized |
| `Index` | a catalog of members carrying *descriptive* metadata (never stateful) | three uses: the retrieval index (points at Log entries), the topic CV (catalogs the classification terms), and the domain bundle root (catalogs the Concept docs) |
| `Concept` | a semantic doc about one subject, refined in place | each `docs/domain/<subject>.md` |

`type: Index` is reused for three different jobs because they are all the same OKF
shape — a descriptive catalog of members — not because they are the same thing.

## Concepts, files, tags, and type — the relationships, concisely

Four terms get confused; here is each, once:

- **A Concept is a file.** In the `docs/domain/` bundle, one `type: Concept` markdown
  file = one subject (staining variance, cohort skew). The bundle is just the directory
  of those files, with an `index.md` (`type: Index`) at its root that lists them.
- **`type`** is the OKF *kind* of a file (`Log` / `Index` / `Concept`) — it says what
  shape the file is and how it behaves (append-only journal vs. regenerable catalog vs.
  refined-in-place subject doc). One value per file, in its frontmatter.
- **`tags`** is OKF *document-level* descriptive metadata — free keywords describing the
  *whole file*. Its job is to let a human (or coarse search) tell sibling files apart
  within a directory (which Concept doc is about site-effects vs. cohort-effects). It is
  **not read by retrieval**; the LLM never matches on it.
- **`concept keywords`** (note: *not* the same as a `type: Concept` doc, despite the
  word) are the **per-entry classification** of a Log entry, drawn from the topic CV
  (`topics.md`) and stored as a column in the *derived index* — **not** in the entry and
  **not** in `tags`. This is the LLM-managed, human-gated classification.
- **`anchor`** is the **primary retrieval key** — *what a Log entry is about* (a RID, a
  type, a process/skill, or a `docs/domain/` subject). Retrieval walks anchors, not tags.

The one-line mental model: **`type` = what kind of file; `tags` = how a human tells
sibling files apart; `concept keywords` = how a Log entry is classified (in the index);
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
