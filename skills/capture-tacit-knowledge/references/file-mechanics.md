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
3. Create the file with the standard header (see the model template's
   `tacit-knowledge.md` for the canonical wording; the header explains the
   *tacit knowledge* vs *catalog facts* boundary so a reader hitting the
   file knows what belongs in it).
4. `git add tacit-knowledge.md` immediately so it does not get lost.

## Relationship to other project files

| File | Role |
|---|---|
| `tacit-knowledge.md` | *Why* — intent and reasoning behind decisions |
| `experiments.md` (if present) | *What* — what each experiment configuration does (parameters, inputs, outputs) |
| `CLAUDE.md` | Project-level instructions for Claude |
| Hydra configs (`src/configs/...`) | Define experiment parameters |

Reference `tacit-knowledge.md` from `CLAUDE.md` so new sessions pick up
the context.
