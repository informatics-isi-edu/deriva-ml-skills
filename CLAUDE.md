# CLAUDE.md

Guidance for Claude Code when working in deriva-ml-skills. `AGENTS.md` mirrors
this file for Codex — keep the two in sync. Shared workspace
conventions (`uv`, `bump-version`, CWD discipline, docstrings) live in
[`../CLAUDE.md`](../CLAUDE.md).

## Project Overview

The `deriva-ml` Claude Code plugin: skills for the **DerivaML** domain layer —
datasets, workflows, executions, features, assets, experiments, model development.
Skills are Markdown with optional Python scripts; there is no build step.

- **Depends on the `deriva` plugin** ([`deriva-skills`](https://github.com/informatics-isi-edu/deriva-skills)),
  declared in `.claude-plugin/plugin.json` → `dependencies`. Skills reference its
  skills as `/deriva:<name>` without hedging.
- **Assumes a reachable `deriva-mcp-core` server** with the
  [`deriva-ml-mcp-plugin`](https://github.com/informatics-isi-edu/deriva-ml-mcp-plugin)
  loaded; `deriva_ml_*` tool mentions must match tools/prompts registered there.

## Layout

```
.claude-plugin/plugin.json   # manifest: name, version, dependencies
skills/<name>/SKILL.md       # auto-discovered; directory name = /deriva-ml:<name>
skills/<name>/references/    # optional depth docs
skills/<name>/scripts/       # optional helpers
hooks/                       # tacit-knowledge capture hooks (ship in the release)
evals/                       # eval cases, excluded from releases
docs/adr/, docs/superpowers/ # decisions, specs, plans
```

`evals/optimization/` is inherited from the pre-May-2026 layout and exercises
deleted skill names — update or retire it before trusting its results.

## Skill shapes

Every skill is one of two shapes; decide which before writing one.

- **Guide-shaped** — auto-fires and steers proactively (lifecycle, discipline,
  always-relevant guards). Needs a rich trigger `description`. Many are also
  slash-typeable (e.g. `dataset-lifecycle`, `compare-model-runs`). Background-only
  guides set `user-invocable: false` (e.g. `capture-tacit-knowledge`,
  `generate-descriptions`). `deriva-ml-context` is the always-on plugin context
  that carries the precedence principle.
- **Tool-shaped** — runs only when the user types `/deriva-ml:<name>`
  (verification, troubleshooting, environment setup, one-shot ops). Set
  `disable-model-invocation: true` and give a useful standalone response.

The four lifecycle skills (`experiment-lifecycle`, `dataset-lifecycle`,
`create-feature`, `model-development-workflow`) share one **Specify → Build →
Validate** arc and handoff grammar
(`docs/superpowers/specs/2026-06-22-unifying-lifecycle-framework.md`);
`design-experiment` owns Specify for all four.

User-facing docs (README, help) must keep the two shapes in separate sections so
users don't try to invoke a background guide as a command.

### Frontmatter

Follows the [Agent Skills spec](https://agentskills.io/specification) plus
Claude Code's [`when_to_use`](https://code.claude.com/docs/en/skills) field.

- **`description`** — ≤1024 chars (spec limit), third person: what the skill
  does, then `Use when…`. Key use case first. Must stand alone, since
  non-Claude-Code agents see only this field.
- **`when_to_use`** (guide-shaped only) — trigger phrases and `Not for … (use X)`
  routing. Claude Code appends it to `description` and truncates the pair at
  **1,536 chars**, so keep the combined length under that.
- **Tool-shaped skills** (`disable-model-invocation: true`) — description only, one
  or two sentences; it shows in the `/` menu but never reaches the model, so
  trigger lists there are dead weight.
- **References stay flat** — `references/<name>.md`, linked directly from
  `SKILL.md`, no subfolders or index/hub files (spec: one level deep). A long
  reference gets a table of contents and greppable `## ` sections instead of
  being split into a bundle (see `deriva-ml-context/references/ml-schema.md`).

## Cross-plugin and cross-repo rules

- **Precedence principle:** DerivaML abstractions override raw catalog primitives.
  `deriva-ml-context` owns the statement of this rule — don't restate it elsewhere.
- **References into deriva-skills** use `/deriva:<skill-name>` with a
  `(deriva-skills)` annotation; no tier-1/tier-2 framing.
- **The plugins release independently.** A `deriva-skills` change that affects
  this repo needs a coordinated release here by hand.
- **`deriva-ml-context` ↔ `deriva_ml_concepts` prompt are deliberately duplicated.**
  `_CONCEPTS_GUIDE` in `../deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/prompts.py`
  serves non-Claude-Code MCP clients the same conceptual floor (what DerivaML is,
  the five abstractions, the provenance principle, vocab extension via
  `add_term(schema="deriva-ml")`); the skill adds Claude-Code-specific routing on
  top. When the abstractions change, update both — each file's header points at
  the other.

## Releasing

`uv run bump-version patch|minor|major` from a clean tree; the tag triggers the
release workflow. Then **bump the `deriva-plugins` meta-marketplace by hand** or
`autoUpdate` users won't get the release. Full procedure, the `hooks/` packaging
requirement, and the tag-push gotcha: **[`docs/release.md`](docs/release.md)**.

## Gotchas

- **`description` decides triggering.** A vague one causes false or missed
  auto-invocation; say when *not* to fire, too.
- **After any skill edit, run `uv run --no-project python scripts/check_drift.py`**
  (what CI runs; stdlib-only, so no env sync). It checks `/deriva-ml:`, `/deriva:`
  and `deriva_ml_*` references against this repo, `../deriva-skills` and
  `../deriva-ml-mcp-plugin`.
- **Renaming or removing a skill** changes its `/deriva-ml:` command — grep every
  `SKILL.md` and `references/*.md` (and the `deriva-skills` repo) for the old name.
- **Never drop a `SKILL.md` into `skills/` for scratch work** — anything there loads
  as a skill.
- **Scripts must survive a minimal `PATH`** (the Desktop app may not source shell
  profiles): find `uv` via `shutil.which()`, then `~/.local/bin/`, `~/.cargo/bin/`,
  `/opt/homebrew/bin/`.

## Issues

GitHub issues at `informatics-isi-edu/deriva-ml-skills`, via the `gh` CLI.
Decisions are recorded in `docs/adr/`.
