# CLAUDE.md

This file provides guidance to Claude Code when working with the deriva-ml-skills codebase.

## Project Overview

Claude Code plugin providing 31 skills for the **DerivaML** domain layer (datasets, workflows, executions, features, assets, experiments, model development). Skills are organized as Markdown documents with optional Python scripts — no package build step required.

The plugin assumes the [`deriva-skills`](https://github.com/informatics-isi-edu/deriva-skills) plugin is also loaded — the README's install procedure brings in both — and assumes a `deriva-mcp-core` server with the [`deriva-ml-mcp-plugin`](https://github.com/informatics-isi-edu/deriva-ml-mcp-plugin) plugin loaded is reachable. Cross-references to `/deriva:<skill>` are written as if those skills are present; `deriva_ml_*` MCP tools assume the server is up. (The plugin-level `dependencies` field that would enforce the deriva-skills assumption at install time is a planned follow-up.) See [`deriva-skills/docs/superpowers/plans/2026-04-27-skills-restructure.md`](https://github.com/informatics-isi-edu/deriva-skills/blob/main/docs/superpowers/plans/2026-04-27-skills-restructure.md) for the rationale behind the two-plugin split.

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

Versioning and updates are documented in `skills/troubleshoot-execution/SKILL.md` ("Versioning and updates" section). The three DerivaML components — deriva-ml, deriva-ml-mcp-plugin, the deriva-ml plugin — each have their own update path. A one-shot installed-vs-latest check is the bundled **script** `skills/troubleshoot-execution/scripts/check_versions.py` (run via `uv run python …`), NOT a skill. The distinction is deliberate: the previous `check-deriva-ml-versions` *skill* was deleted because its bash examples hardcoded references that rotted (a deleted script in the deriva plugin). The replacement script avoids that failure mode by querying live and reading the right source per component: highest git **tag** for the library AND the `deriva-ml-mcp-plugin` (both ship tags via `bump-version`/`setuptools_scm`, NOT GitHub Releases — releases there are absent/stale), highest GitHub **release** for the `deriva-ml-skills` plugin (its workflow publishes releases). It runs a discovery chain first — git repo → `pyproject.toml` (uv convention) → `.venv/` — failing loud (exit 2) with the fix at the first unmet gate, and reads the installed `deriva-ml` via the **venv's own interpreter** (not `uv pip show`, so it works when `uv` isn't on PATH; `uv` availability is reported, not required). It degrades to `unknown` (never a wrong hardcoded value) when `gh`/network are absent. The MCP server's *running* version is only knowable live via `server_status`, so the script shows the latest published plugin version and points at that tool for the running one. **Gotcha learned building it:** an ambient activated `$VIRTUAL_ENV` (e.g. the one `uv run` activates to launch the script itself) will leak in unless the project's own `.venv/` takes precedence — the script enforces project-`.venv`-first and only honors `$VIRTUAL_ENV` when it lives under `--project`. The deriva-skills equivalent is `skills/troubleshoot-deriva-errors/SKILL.md` for the foundation (deriva-py, deriva-mcp-core, deriva plugin); check the foundation first since the DerivaML stack depends on it.

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
├── skills/                   # 31 skills, each in its own directory; auto-discovered by Claude Code from `skills/*/SKILL.md`
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

### Skill Organization

The 31 skills divide into two shapes by invocation model. The split matters when editing skills and when adding new ones — guide-shaped skills can assume background loading and should produce coordinated behavioral guidance; tool-shaped skills can assume the user explicitly typed `/deriva-ml:<name>` and should produce a useful standalone response.

**User commands (`/deriva-ml:<name>`)** — `user-invocable: true` or unset; the user types the command or asks a question that maps to it:

- Lifecycle (also auto-fires): `dataset-lifecycle`, `execution-lifecycle`, `experiment-lifecycle`
- Datasets: `debug-bag-contents`
- Features: `create-feature` (also auto-fires), `compare-model-runs` (also auto-fires — at the post-run evaluation moment)
- Assets: `work-with-assets` (also auto-fires — per-asset file I/O), `manage-deriva-storage` (also auto-fires — see below)
- Experiments / configs: `design-experiment` (also auto-fires — the design-first phase, owns experiment-design/ + dataset-design/), `configure-experiment` (also auto-fires — the lifecycle Phase 2 config seam), `write-hydra-config` (also auto-fires — when editing config files / wiring RIDs)
- Models: `new-model`, `model-development-workflow`
- Notebooks: `setup-notebook-environment`, `run-notebook`
- Project setup: `setup-derivaml-project`, `setup-ml-catalog`, `validate-project-setup`
- Apps + visualization: `create-web-app`, `browse-erd`, `use-annotation-builders`
- Help / orientation: `help`
- Troubleshooting: `troubleshoot-execution` (also auto-fires — on execution failures AND proactive DerivaML version checks; covers DerivaML versioning via the bundled `check_versions.py`), `schema-evolution-impact` (impact analysis before changing/deleting catalog entities)

**Auto-invoked guides (no slash command typed by user)** — `user-invocable: false` or `disable-model-invocation` unset; should NOT be surfaced in user-facing skill lists as if they were commands. These "look over the shoulder" of the ML developer to inject the right framing before mistakes:

- `deriva-ml-context` — always-on plugin context (the precedence principle, the five abstractions, the steering frame)
- `dataset-lifecycle`, `execution-lifecycle`, `experiment-lifecycle` — auto-fire on broad lifecycle phrasings (dual-mode: also slash-typeable)
- `model-development-workflow` — auto-fires when starting a project or onboarding
- `capture-tacit-knowledge` — auto-fires after significant decisions
- `using-deriva-mcp` — auto-fires before the first deriva MCP call (cold-start: call the `deriva_ml_primer` tool, then fetch guides on demand)
- `api-naming-conventions` — auto-fires when writing DerivaML Python code
- `ml-data-engineering` — auto-fires when designing data egress for ML pipelines
- `manage-deriva-storage` — auto-fires on local-storage / cache questions (dual-mode: also slash-typeable). Read-shaped asks ("what datasets are cached", "disk usage") surface it without the user knowing the command; destructive cleanup ops stay behind their own confirm discipline.
- `design-experiment` — auto-fires before configuring an experiment or building a dataset (dual-mode: also slash-typeable). Owns the design-first phase: the standardized design doc that precedes config/construction.
- `generate-scripts` — auto-fires when generating Python scripts for catalog operations
- `generate-descriptions` — auto-fires when creating any DerivaML entity without a description
- `configure-experiment` — auto-fires at the experiment-lifecycle Phase 2 config seam (dual-mode: also slash-typeable). The lifecycle routes here; making it auto-fire closes the "router points at a door you can't open" gap.
- `write-hydra-config` — auto-fires when editing config files or wiring RIDs into `configs/` (dual-mode). The mechanics behind the dataset/execution-lifecycle "add the RID to configs" offers.
- `work-with-assets` — auto-fires on per-asset file I/O — download/upload/inspect (dual-mode). The single-asset half of the asset offer; execution-lifecycle owns the bulk-output offer.
- `compare-model-runs` — auto-fires at the post-run evaluation moment — "which run was best", "is this a regression" (dual-mode). experiment-lifecycle Phase 6 routes here.

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
   - Creates `deriva-ml-skills-{VERSION}.tar.gz` (the tar invocation packages `.claude-plugin/`, `skills/`, and `hooks/`; everything else — `.git`, `.github`, `evals/`, `docs/`, `tests/`, `pyproject.toml`, `uv.lock` — is excluded by virtue of not being passed). **`hooks/` must stay in the tar** — it carries the tacit-knowledge capture hooks declared in `hooks/hooks.json`: a `SessionStart` hook (executable `hooks/session-start`) that injects the FULL capture discipline once at session start, plus a `UserPromptSubmit` hook (executable `hooks/user-prompt-submit`) that re-injects a SHORT binding directive on every user turn so the trigger isn't demoted as context grows. The two are a pair — SessionStart front-loads the full contract (including the do-NOT-fire boundary) so the per-turn line can stay terse without over-firing. Drop `hooks/` from the tar and the discipline silently ships nowhere. Both scripts are tracked executable (`100755`); tar preserves the mode so they stay runnable after install.
   - Publishes GitHub Release with auto-generated notes
4. **Manual step — bump the meta-marketplace.** See "Bumping the meta-marketplace" below. Without this step, users on `autoUpdate: true` will stay pinned to the previous version.

After step 4 lands, users with `autoUpdate: true` pick up the new version on next Claude Code restart. First-time install uses `/plugin install deriva-ml` after `/plugin marketplace add informatics-isi-edu/deriva-plugins`.

**Never create git tags manually** — always use `bump-version` from deriva-ml or the `bump_version` MCP tool.

### Bumping the meta-marketplace

The [`deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins) meta-marketplace must be updated **by hand** after every `bump-version` here. The update has two pieces:

1. The **version pin** in `marketplace.json` — controls what `autoUpdate` users get on next install.
2. A **`deriva-ml--v{version}` tag** on the meta-marketplace repo — what Claude Code's `dependencies:` resolver scans. (No external plugin currently depends on `deriva-ml`, but the tag is created consistently to match the convention.)

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

# Tag the commit so dependency resolution finds it.
# The naming convention `{plugin-name}--v{version}` is required by Claude Code.
git tag deriva-ml--v1.3.2

# Push commit + tag together
git push --follow-tags
```

Sanity-check the diff before pushing — `jq` rewrites the whole file, so the diff should be exactly one line changed.

**Failure modes:**

- Skip the version-pin bump → `autoUpdate` users stay on the old version. No error.
- Skip the prefixed tag → any plugin declaring `dependencies: [{name: "deriva-ml", ...}]` fails to install with `no-matching-tag`. (Currently no such plugin exists, but creating the tag preserves the invariant.)

**This plugin's own `dependencies:` field declares `deriva@^1.2.0`.** That means `deriva-ml` will not install unless a `deriva--v*` tag matching `^1.2.0` exists on the meta-marketplace. **The corresponding tag for the deriva plugin is the load-bearing one** — it must exist on the meta-marketplace before any user tries to install `deriva-ml`. See `deriva-skills/CLAUDE.md` for the deriva-side bump procedure.

This step is currently manual. A future improvement (deferred for now) is a GitHub Actions workflow on this repo that fires on `v*.*.*` tag push and opens a PR against `deriva-plugins` with both updates. Until that lands, treat the manual step as part of the release.

## Cross-plugin coordination

The plugin assumes `deriva-skills` is loaded — the README's install procedure brings in both, and skill-internal cross-references to `/deriva:<skill>` are written without "if you have it installed" hedging. (This is a documentation assumption, not yet enforced at install time; the `dependencies` field in `plugin.json` that would auto-install `deriva-skills` is a planned follow-up.) Three coordination points apply:

- **Steering principle (load-bearing):** when this plugin is loaded, the DerivaML abstractions (Dataset, Workflow, Execution, Feature, Asset_Type vocabularies) take precedence over the raw catalog primitives that `deriva-skills` documents. Use the `/deriva-ml:` skills and the deriva-ml Python API for these concepts — not the raw `insert_records` / `update_record` / `get_record` core tools. The `deriva-ml-context` always-on skill carries this principle plugin-wide; per-skill steering callouts in select `deriva-skills` skills (`troubleshoot-deriva-errors`, `manage-vocabulary`) reinforce it for users who arrive in those skills directly.
- **Cross-references to `deriva-skills` skills:** when a skill here needs a generic catalog operation (auth troubleshooting, schema introspection, generic vocab CRUD, custom domain table creation), use `/deriva:<skill-name>` references with `(deriva-skills)` as the disambiguating annotation — no `tier-1`/`tier-2` framing.
- **Versioning:** the `check-deriva-versions` and `check-deriva-ml-versions` skills were both deleted (`deriva-skills` commit `b407acf`; this repo May 2026 restructure). Versioning content now lives in `troubleshoot-deriva-errors` (deriva-skills) and `troubleshoot-execution` (this repo) as "Versioning and updates" sections. The deriva-skills foundation comes first; check it before the DerivaML stack since the latter depends on it.
- **Release coordination:** the two plugins are independently versioned and released. A `deriva-skills` release does NOT automatically bump this plugin; coordinate manually when a `deriva-skills` change has implications here.

### Distribution: the `deriva-plugins` marketplace

The supported install path is the [`informatics-isi-edu/deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins) marketplace. Users `/plugin marketplace add` it once, then `/plugin install deriva` and `/plugin install deriva-ml`. The marketplace lists both plugins side-by-side; installing this one does not yet pull in `deriva-skills` automatically (planned follow-up via `dependencies`).

Practical implications for this repo:

- This repo carries only `.claude-plugin/plugin.json` — the per-plugin manifest Claude Code reads after install. There is no `marketplace.json` here; the marketplace lives in the `deriva-plugins` repo.
- `bump-version` only rewrites `plugin.json` (and the `[tool.bumpversion] current_version`); the `pyproject.toml` block lists no marketplace entry. It does **not** touch the meta-marketplace's pin — see "Bumping the meta-marketplace" under Release Process for the manual follow-up.
- The skill list is **auto-discovered** by Claude Code from `skills/*/SKILL.md` in the cloned repo — no enumeration is needed in either `plugin.json` or the meta-marketplace's `marketplace.json`. Add a skill by creating `skills/<name>/SKILL.md`; it loads on the next plugin update.

## Cross-Repo Sync: `deriva-ml-context` skill ↔ `deriva_ml_concepts` prompt

The `skills/deriva-ml-context/SKILL.md` file in this repo and the
`_CONCEPTS_GUIDE` constant in
`../deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/prompts.py` (rendered as the
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
  prompt over the MCP wire from `deriva-ml-mcp-plugin`.

This skill is RICHER than the prompt — it adds tool-selection
guidance, cross-references to other skills (`/deriva-ml:dataset-lifecycle`,
`/deriva:troubleshoot-deriva-errors`, etc.), the worked "when to reach
back to the raw catalog surface" table, and other Claude-Code-specific
value-add. The prompt is the conceptual FLOOR; this skill is floor +
Claude-Code value-add.

**When updating the abstractions** (rare — they're fundamental),
update BOTH:

1. `skills/deriva-ml-context/SKILL.md` (this repo)
2. `_CONCEPTS_GUIDE` in `../deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/prompts.py`

Both files carry an inline comment block at their top pointing at the
other side. The matching cross-repo note lives in
`../deriva-ml-mcp-plugin/CLAUDE.md` under the same section heading so the
constraint is visible from either repo.

### v3.x update: deriva-ml-mcp-plugin prompts went from 4 to 2

The deriva-ml-mcp-plugin originally shipped four MCP prompts; v3.x
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
- **Cross-references matter** — when renaming or removing a skill, grep for its name across all other skills' `SKILL.md` and `references/*.md` files. Pay special attention to cross-references into `deriva-skills` — those land at `/deriva:<skill>` and assume the deriva-skills plugin is loaded (per the assumption stated in Cross-plugin coordination above).
- **No `deriva-skills` carry-over** — this repo was carved out of `deriva-skills` via a no-history-preserved import (per the migration plan). The two repos' contents are fundamentally separate; do not attempt to merge them back together.
- **`[tool.bumpversion]` config required** — `bump-version` wraps `bump-my-version` which needs `[tool.bumpversion]` in `pyproject.toml` with `tag = true` and `commit = true`. Without it, no tag or commit is created.
- **Never use `bump-my-version` directly** — always use `uv run bump-version patch|minor|major` which is the DerivaML CLI wrapper. Using `bump-my-version bump` directly bypasses project-specific logic.

## Agent skills

### Issue tracker

Issues are tracked on GitHub at `informatics-isi-edu/deriva-ml-skills` via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five canonical triage role labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
