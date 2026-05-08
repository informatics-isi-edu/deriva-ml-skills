# CLAUDE.md

This file provides guidance to Claude Code when working with the deriva-ml-skills codebase.

## Project Overview

Claude Code plugin providing 27 tier-2 skills for the **DerivaML** domain layer (datasets, workflows, executions, features, assets, experiments, model development). Skills are organized as Markdown documents with optional Python scripts — no package build step required.

This plugin is the **tier-2** surface — the DerivaML-specific surface. It depends on the **tier-1** [`deriva-skills`](https://github.com/informatics-isi-edu/deriva-skills) plugin (the core Deriva catalog ecosystem) and the [`deriva-ml-mcp`](https://github.com/informatics-isi-edu/deriva-ml-mcp) MCP plugin loaded by `deriva-mcp-core`. See `../deriva-skills/docs/superpowers/plans/2026-04-27-skills-restructure.md` for the rationale and migration history.

## Commands

See [`../CLAUDE.md`](../CLAUDE.md) for shared `uv` and `bump-version`
conventions. Repo-specific commands:

> **CWD:** every command below assumes you are in
> `/Users/carl/GitHub/DerivaML/deriva-ml-skills`. The Bash tool's cwd is **not**
> reliably persistent across turns — always chain `cd` into a single call,
> e.g. `cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && uv run pytest`.
> See the workspace-level `CLAUDE.md` ("CWD discipline") for the rule.

```bash
# Load locally for development (no install needed)
claude --plugin-dir /path/to/deriva-ml-skills

# Install from the unified marketplace (one marketplace, both plugins)
/plugin marketplace add informatics-isi-edu/deriva-plugins
/plugin install deriva
/plugin install deriva-ml

```

Versioning and updates are documented in `skills/troubleshoot-execution/SKILL.md` ("Versioning and updates" section). The three DerivaML components — deriva-ml, deriva-ml-mcp, the deriva-ml plugin — each have their own update path; there is no unified version-checker tool in the plugin (the previous `check-deriva-ml-versions` skill was deleted because its bash examples referenced a deleted tier-1 script, and `autoUpdate: true` for plugins / `server_status` for the server / `uv pip show` for the library all became reliable enough that wrapping them in a custom skill no longer earned its weight). The tier-1 equivalent is `skills/troubleshoot-deriva-errors/SKILL.md` for the foundation (deriva-py, deriva-mcp-core, deriva plugin); check the foundation first since the DerivaML stack depends on it.

**Release mechanics:** `bump-version` triggers GitHub Actions, which
bumps version in `plugin.json`, commits back to main, and creates the
release archive. `bump_version("patch")` via the MCP tool is also
supported. Note: the version field in the
[`deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins)
meta-marketplace's `marketplace.json` is **not** auto-bumped — see
"Cross-plugin coordination" below.

## Architecture

```
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest (name, version, description) — read by Claude Code after install
├── skills/                   # 27 tier-2 skills, each in its own directory; the marketplace lives in the deriva-plugins repo and lists each one by path
│   ├── {skill-name}/
│   │   ├── SKILL.md          # Frontmatter (YAML) + skill content (Markdown)
│   │   ├── scripts/          # Optional Python helper scripts
│   │   └── references/       # Optional extended documentation
│   └── ...
├── evals/                    # Eval test cases (gitignored from releases)
│   └── {skill-name}/
│       └── trigger-eval.json
└── .github/
    ├── workflows/release.yml # Tag-triggered release automation
    └── release-drafter.yml   # Release notes template
```

### Skill Organization (tier-2)

The 27 tier-2 skills divide into two shapes by invocation model. The split matters when editing skills and when adding new ones — guide-shaped skills can assume background loading and should produce coordinated behavioral guidance; tool-shaped skills can assume the user explicitly typed `/deriva-ml:<name>` and should produce a useful standalone response.

**User commands (`/deriva-ml:<name>`)** — `user-invocable: true` or unset; the user types the command or asks a question that maps to it:

- Lifecycle (also auto-fires): `dataset-lifecycle`, `execution-lifecycle`, `experiment-lifecycle`
- Datasets: `debug-bag-contents`
- Features: `create-feature`, `compare-model-runs`
- Assets: `work-with-assets`, `manage-storage`
- Experiments / configs: `configure-experiment`, `write-hydra-config`
- Models: `new-model`, `model-development-workflow`
- Notebooks: `setup-notebook-environment`, `run-notebook`
- Project setup: `setup-derivaml-project`, `validate-project-setup`
- Apps + visualization: `create-web-app`, `browse-erd`
- Help / orientation: `help`
- Troubleshooting: `troubleshoot-execution` (also covers DerivaML versioning)

**Auto-invoked guides (no slash command typed by user)** — `user-invocable: false` or `disable-model-invocation` unset; should NOT be surfaced in user-facing skill lists as if they were commands. These "look over the shoulder" of the ML developer to inject the right framing before mistakes:

- `deriva-ml-context` — always-on plugin context (the precedence principle, the five abstractions, the steering frame)
- `dataset-lifecycle`, `execution-lifecycle`, `experiment-lifecycle` — auto-fire on broad lifecycle phrasings (dual-mode: also slash-typeable)
- `model-development-workflow` — auto-fires when starting a project or onboarding
- `maintain-experiment-notes` — auto-fires after significant decisions
- `catalog-operations-workflow` — auto-fires before catalog mutations
- `api-naming-conventions` — auto-fires when writing DerivaML Python code
- `ml-data-engineering` — auto-fires when designing data egress for ML pipelines
- `generate-scripts` — auto-fires when generating Python scripts for catalog operations
- `generate-descriptions` — auto-fires when creating any DerivaML entity without a description

**Convention for adding a new skill:** decide which shape it is. Guide-shaped skills (workflow, lifecycle, discipline, always-relevant guard) get rich auto-fire descriptions and guide the user proactively. Tool-shaped skills (verification, troubleshooting, environment setup, one-shot operations) get `disable-model-invocation: true` and wait for the user to explicitly invoke them. Documentation surfaces (README, marketing copy, help blurbs) should keep the two layers in clearly-separated sections so users don't reach for an auto-invoked guide as if it were a command.

### Skill Anatomy (`SKILL.md`)

```yaml
---
name: skill-name
description: >
  Trigger description — Claude uses this to decide when to auto-invoke.
  Be specific about when to trigger and when NOT to trigger.
disable-model-invocation: true   # Optional: only invoke via /skill-name
user-invocable: false             # Optional: auto-invoked only, no /command
---

# Skill Content

Markdown instructions that Claude follows when the skill is active.
```

### Eval Structure

Skills with evals have files under `evals/<skill-name>/`. Workspace iteration outputs (`evals/<skill>/iteration-*/`) are gitignored from releases.

There is also an `evals/optimization/` directory containing a cross-skill eval suite (per-skill evals + a `run_all.py` runner) that was inherited from the pre-restructure layout. It exercises legacy skill names from before the routers were deleted (May 2026 restructure); update or retire it before relying on its results.

## Release Process

1. Commit changes
2. Run `bump-version patch|minor|major` (creates tag and pushes automatically)
3. GitHub Actions automatically:
   - Bumps version in `plugin.json` (the bump-my-version config in `pyproject.toml` runs as part of `bump-version`, before the tag push)
   - Commits version bump back to main
   - Creates `deriva-ml-skills-{VERSION}.tar.gz` (the tar invocation packages `.claude-plugin/` and `skills/`; everything else — `.git`, `.github`, `evals/`, `docs/`, `tests/`, `pyproject.toml`, `uv.lock` — is excluded by virtue of not being passed)
   - Publishes GitHub Release with auto-generated notes
4. **Manual step — bump the meta-marketplace.** See "Bumping the meta-marketplace" below. Without this step, users on `autoUpdate: true` will stay pinned to the previous version.

After step 4 lands, users with `autoUpdate: true` pick up the new version on next Claude Code restart. First-time install uses `/plugin install deriva-ml` after `/plugin marketplace add informatics-isi-edu/deriva-plugins`.

**Never create git tags manually** — always use `bump-version` from deriva-ml or the `bump_version` MCP tool.

### Bumping the meta-marketplace

The [`deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins) meta-marketplace pins each plugin to a specific version (`version` field per plugin entry in its `marketplace.json`). That pin is **not** updated by this repo's release workflow — `autoUpdate` users on the meta-marketplace will not see a new release until the pin is bumped. After every `bump-version` here:

```bash
# In a checkout of informatics-isi-edu/deriva-plugins:
cd /path/to/deriva-plugins
git pull

# Bump the deriva-ml entry (replace 1.3.2 with the new version)
jq '(.plugins[] | select(.name == "deriva-ml") | .version) = "1.3.2"' \
  .claude-plugin/marketplace.json > /tmp/m.json && \
  mv /tmp/m.json .claude-plugin/marketplace.json

git add .claude-plugin/marketplace.json
git commit -m "Bump deriva-ml to 1.3.2"
git push
```

Sanity-check the diff before pushing — `jq` rewrites the whole file, so the diff should be exactly one line changed.

This step is currently manual. A future improvement (deferred for now) is a GitHub Actions workflow on this repo that fires on `v*.*.*` tag push and opens a PR against `deriva-plugins` with the version bump. Until that lands, treat the manual step as part of the release.

## Cross-plugin coordination

The companion `deriva-skills` plugin (tier-1) is a documented dependency:

- **Steering principle (load-bearing):** when the deriva-ml plugin is loaded, the DerivaML abstractions (Dataset, Workflow, Execution, Feature, Asset_Type vocabularies) take precedence over the raw catalog primitives that `deriva-skills` documents. Use the `/deriva-ml:` skills and the deriva-ml Python API for these concepts — not the raw `insert_records` / `update_record` / `get_record` core tools. The `deriva-ml-context` always-on skill carries this principle plugin-wide; per-skill steering callouts in select tier-1 skills (`troubleshoot-deriva-errors`, `manage-vocabulary`) reinforce it for users who arrive in those skills directly.
- **Cross-references TO tier-1 skills:** when a tier-2 skill needs a generic catalog operation (auth troubleshooting, schema introspection, generic vocab CRUD, custom domain table creation), use `/deriva:<skill-name>` references with explicit `(tier-1; deriva-skills)` annotation so users know they need the companion plugin installed.
- **Versioning:** the `check-deriva-versions` and `check-deriva-ml-versions` skills were both deleted (tier-1 commit `b407acf`; tier-2 May 2026 restructure). Versioning content now lives in `troubleshoot-deriva-errors` (tier-1) and `troubleshoot-execution` (tier-2) as "Versioning and updates" sections. Foundation comes first; check tier-1 versions before tier-2.
- **Release coordination:** the two plugins are independently versioned and released. A tier-1 release does NOT automatically bump tier-2; coordinate manually when a tier-1 change has tier-2 implications.

### One marketplace: `deriva-plugins`

The only supported install path is the unified [`informatics-isi-edu/deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins) marketplace, which lists both `deriva` (the tier-1 companion) and `deriva-ml` (this plugin). The previous per-repo single-plugin marketplace (`informatics-isi-edu/deriva-ml-skills` with a `.claude-plugin/marketplace.json` at the repo root, `source: ./`) was removed in May 2026 — there's now exactly one place where the skill list and version pin live.

Practical implications:

- This repo no longer carries a `marketplace.json`. Only `.claude-plugin/plugin.json` lives here.
- `bump-version` only rewrites `plugin.json` (and the `[tool.bumpversion] current_version`); the `pyproject.toml` block lists no marketplace entry. It does **not** touch the meta-marketplace's pin — see "Bumping the meta-marketplace" under Release Process for the manual follow-up.
- The skill list is **auto-discovered** by Claude Code from `skills/*/SKILL.md` in the cloned repo — no enumeration is needed in either `plugin.json` or the meta-marketplace's `marketplace.json`. Add a skill by creating `skills/<name>/SKILL.md`; it loads on the next plugin update.

The companion `deriva-skills` plugin (tier-1) ships its plugin manifest the same way — `plugin.json` only — and is listed alongside this plugin in the same meta-marketplace.

## Cross-Repo Sync: `deriva-ml-context` skill ↔ `deriva_ml_concepts` prompt

The `skills/deriva-ml-context/SKILL.md` file in this repo and the
`_CONCEPTS_GUIDE` constant in
`../deriva-ml-mcp/src/deriva_ml_mcp/prompts.py` (rendered as the
`deriva_ml_concepts` MCP prompt) share their conceptual content
DELIBERATELY. Both must explain:

- What DerivaML is (one paragraph)
- The five core abstractions (Dataset, Workflow, Execution, Feature, Asset)
- The provenance principle (every artifact links to its producing Execution)
- The vocabulary-extension pattern (use core's `add_term` with `schema="deriva-ml"`)

The duplication is intentional. The two surfaces serve different LLM
clients with different invocation models:

- **Claude Code clients** with this plugin loaded get the conceptual
  frame pushed into context proactively via the always-on
  `deriva-ml-context` skill (the audit-named "load-bearing" path).
- **Non-Claude-Code clients** (Cursor, SDK-based agents, raw FastMCP
  clients, etc.) pull the same frame in via the `deriva_ml_concepts`
  prompt over the MCP wire from `deriva-ml-mcp`.

This skill is RICHER than the prompt — it adds tool-selection
guidance, cross-references to other skills (`/deriva-ml:dataset-lifecycle`,
`/deriva:troubleshoot-deriva-errors`, etc.), the worked "when to reach
back to the raw catalog surface" table, and other Claude-Code-specific
value-add. The prompt is the conceptual FLOOR; this skill is floor +
Claude-Code value-add.

**When updating the abstractions** (rare — they're fundamental),
update BOTH:

1. `skills/deriva-ml-context/SKILL.md` (this repo)
2. `_CONCEPTS_GUIDE` in `../deriva-ml-mcp/src/deriva_ml_mcp/prompts.py`

Both files carry an inline comment block at their top pointing at the
other side. The matching cross-repo note lives in
`../deriva-ml-mcp/CLAUDE.md` under the same section heading so the
constraint is visible from either repo.

### v3.x update: deriva-ml-mcp prompts went from 4 to 2

The deriva-ml-mcp plugin originally shipped four MCP prompts; v3.x
removed two of them when the [Round 2 audit cleanup](docs/superpowers/plans/2026-05-02-tier-2-audit-cleanup-plan-round-2-refinement.md)
identified them as architecturally mis-shaped per FastMCP guidance.
The conceptual frame (`_CONCEPTS_GUIDE` ↔ this skill) and the
operating contract (`_GETTING_STARTED_GUIDE`) survive as the two
remaining prompts; `deriva_ml_workflow_dedup` and
`deriva_ml_execution_lifecycle` were deleted with their content
redistributed to the relevant tool docstrings (per-tool warnings)
and the RAG-indexed `user-guide/executions.md` doc in the deriva-ml
repo (cross-cutting depth). The cross-repo sync discipline above
is unchanged; the skill ↔ prompt mirror is now skill ↔ prompt for
the two remaining content pairs.

## Gotchas

- **Description field is critical** — the `description` in SKILL.md frontmatter controls when Claude auto-invokes the skill. Poorly written descriptions cause false triggers or missed triggers.
- **No build step** — skills are pure Markdown + optional scripts. Changes take effect immediately when loaded locally.
- **Release requires tag** — the workflow only triggers on `v*.*.*` tags pushed to origin. Commits alone won't create a release.
- **Skills are auto-discovered, not enumerated** — Claude Code walks `skills/*/SKILL.md` in the cloned plugin repo at install time. Neither this repo's `plugin.json` nor the meta-marketplace's `marketplace.json` lists individual skills. Adding a new skill is just `mkdir skills/<name> && touch skills/<name>/SKILL.md` (with valid frontmatter); it'll appear on the next plugin update without touching any manifest.
- **Eval workspace dirs would auto-discover as skills if they had a SKILL.md** — `evals/<skill>/iteration-*/` directories live under `evals/`, not `skills/`, so auto-discovery won't pick them up. But don't accidentally drop a `SKILL.md` into `skills/` for a workspace artifact, or it will load.
- **Scripts must handle minimal PATH** — Claude Code (especially inside the Desktop app) may not source shell profiles, so `$PATH` can be incomplete. Use `_find_uv()` pattern: try `shutil.which()` first, then check well-known locations (`~/.local/bin/`, `~/.cargo/bin/`, `/opt/homebrew/bin/`). Never assume `uv` or other tools are on PATH.
- **Skill names must be unique** — the directory name under `skills/` is the skill identifier. Renaming a directory changes the `/deriva-ml:` command.
- **Cross-references matter** — when renaming or removing a skill, grep for its name across all other skills' `SKILL.md` and `references/*.md` files. Pay special attention to cross-references into `deriva-skills` — those land at `/deriva:<skill>` and depend on the user having the tier-1 plugin installed (which they should, but the reference text should make the dependency explicit).
- **No tier-1 carry-over** — this repo was carved out of `deriva-skills` via a no-history-preserved import (per the migration plan). The tier-1 surface is fundamentally separate; do not attempt to merge the two repos back together.
- **`[tool.bumpversion]` config required** — `bump-version` wraps `bump-my-version` which needs `[tool.bumpversion]` in `pyproject.toml` with `tag = true` and `commit = true`. Without it, no tag or commit is created.
- **Never use `bump-my-version` directly** — always use `uv run bump-version patch|minor|major` which is the DerivaML CLI wrapper. Using `bump-my-version bump` directly bypasses project-specific logic.

## Agent skills

### Issue tracker

Issues are tracked on GitHub at `informatics-isi-edu/deriva-ml-skills` via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five canonical triage role labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
