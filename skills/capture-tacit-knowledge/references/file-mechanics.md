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

## Relationship to other project files

| File | Role |
|---|---|
| `tacit-knowledge.md` | *Why* — intent and reasoning behind decisions |
| `experiments.md` (if present) | *What* — what each experiment configuration does (parameters, inputs, outputs) |
| `CLAUDE.md` | Project-level instructions for Claude |
| Hydra configs (`src/configs/...`) | Define experiment parameters |

Reference `tacit-knowledge.md` from `CLAUDE.md` so new sessions pick up
the context.
