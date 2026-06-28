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
