# CLAUDE.md

This file provides guidance to Claude Code when working with the deriva-ml-skills codebase.

## Project Overview

Claude Code plugin providing 23 tier-2 skills for the **DerivaML** domain layer (datasets, workflows, executions, features, assets, experiments, model development). Skills are organized as Markdown documents with optional Python scripts — no package build step required.

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

# Install from marketplace (requires the tier-1 plugin first)
/plugin marketplace add informatics-isi-edu/deriva-skills
/plugin install deriva
/plugin marketplace add informatics-isi-edu/deriva-ml-skills
/plugin install deriva-ml

# Run version checker (the script lives in the tier-1 sibling for now;
# Phase 4 of the migration plan splits it into a tier-2 copy here.)
python3 ../deriva-skills/skills/check-deriva-versions/scripts/check_versions.py --component deriva-ml --json
```

**Release mechanics:** `bump-version` triggers GitHub Actions, which
bumps version in `plugin.json` + `marketplace.json`, commits back to
main, and creates the release archive. `bump_version("patch")` via the
MCP tool is also supported.

## Architecture

```
├── .claude-plugin/
│   ├── plugin.json           # Plugin metadata (name, version, description)
│   └── marketplace.json      # Marketplace registration (lists all 23 tier-2 skills)
├── skills/                   # 23 tier-2 skills, each in its own directory
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

The 24 tier-2 skills cover the DerivaML domain layer.

**User-invocable (`/deriva-ml:<name>`):** dataset-lifecycle, debug-bag-contents, execution-lifecycle, troubleshoot-execution, create-feature, work-with-assets, manage-storage, configure-experiment, write-hydra-config, new-model, model-development-workflow, setup-notebook-environment, run-notebook, route-run-workflows, route-project-setup, check-deriva-ml-versions, help.

**Always-on (auto-invoked, no `/command`):** deriva-ml-context (plugin context skill, load-bearing), maintain-experiment-notes, catalog-operations-workflow, api-naming-conventions, ml-data-engineering, generate-scripts.

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

There is also an `evals/optimization/` directory containing a cross-skill eval suite (per-skill evals + a `run_all.py` runner) that was inherited from the pre-restructure layout. It exercises the legacy skill names (some of which were renamed during the migration); update or retire it as part of the v1.4 sweep (Phase 4).

## Release Process

1. Commit changes
2. Run `bump-version patch|minor|major` (creates tag and pushes automatically)
3. GitHub Actions automatically:
   - Bumps version in `plugin.json` and `marketplace.json`
   - Commits version bump back to main
   - Creates `deriva-ml-skills-{VERSION}.tar.gz` (excludes `.git`, `.github`, `evals/`, `docs/superpowers`)
   - Publishes GitHub Release with auto-generated notes
4. Users with `autoUpdate: true` get the new version on next Claude Code restart. First-time install uses `/plugin install deriva-ml`.

**Never create git tags manually** — always use `bump-version` from deriva-ml or the `bump_version` MCP tool.

## Cross-plugin coordination

The companion `deriva-skills` plugin (tier-1) is a documented dependency:

- **Steering principle (load-bearing):** when the deriva-ml plugin is loaded, the DerivaML abstractions (Dataset, Workflow, Execution, Feature, Asset_Type vocabularies) take precedence over the raw catalog primitives that `deriva-skills` documents. Use the `/deriva-ml:` skills and the deriva-ml Python API for these concepts — not the raw `insert_records` / `update_record` / `get_record` core tools. The `deriva-ml-context` always-on skill carries this principle plugin-wide; per-skill steering callouts in select tier-1 skills (`troubleshoot-deriva-errors`, `manage-vocabulary`) reinforce it for users who arrive in those skills directly.
- **Cross-references TO tier-1 skills:** when a tier-2 skill needs a generic catalog operation (auth troubleshooting, schema introspection, generic vocab CRUD, custom domain table creation), use `/deriva:<skill-name>` references with explicit `(tier-1; deriva-skills)` annotation so users know they need the companion plugin installed.
- **Shared script (legacy):** `check-deriva-versions/scripts/check_versions.py` lives in the tier-1 repo today and knows about the entire ecosystem (deriva-py + deriva-mcp-core + deriva-ml + deriva-ml-mcp + both plugins). Phase 4 of the restructure (the v1.4 MCP surface sweep) will split it; until then, the `--component` flag is the boundary, and the tier-2 `check-deriva-ml-versions` skill points at the tier-1 sibling's script.
- **Release coordination:** the two plugins are independently versioned and released. A tier-1 release does NOT automatically bump tier-2; coordinate manually when a tier-1 change has tier-2 implications.

## Gotchas

- **Description field is critical** — the `description` in SKILL.md frontmatter controls when Claude auto-invokes the skill. Poorly written descriptions cause false triggers or missed triggers.
- **No build step** — skills are pure Markdown + optional scripts. Changes take effect immediately when loaded locally.
- **Release requires tag** — the workflow only triggers on `v*.*.*` tags pushed to origin. Commits alone won't create a release.
- **marketplace.json must list all skills** — if you add or remove a skill, update the skills array in `.claude-plugin/marketplace.json`.
- **Eval workspace dirs are not skills** — `evals/<skill>/iteration-*/` directories contain eval outputs and must NOT be listed in marketplace.json.
- **Scripts must handle minimal PATH** — Claude Code (especially inside the Desktop app) may not source shell profiles, so `$PATH` can be incomplete. Use `_find_uv()` pattern: try `shutil.which()` first, then check well-known locations (`~/.local/bin/`, `~/.cargo/bin/`, `/opt/homebrew/bin/`). Never assume `uv` or other tools are on PATH.
- **Skill names must be unique** — the directory name under `skills/` is the skill identifier. Renaming a directory changes the `/deriva-ml:` command.
- **Cross-references matter** — when renaming or removing a skill, grep for its name across all other skills' `SKILL.md` and `references/*.md` files. Pay special attention to cross-references into `deriva-skills` — those land at `/deriva:<skill>` and depend on the user having the tier-1 plugin installed (which they should, but the reference text should make the dependency explicit).
- **No tier-1 carry-over** — this repo was carved out of `deriva-skills` via a no-history-preserved import (per the migration plan). The tier-1 surface is fundamentally separate; do not attempt to merge the two repos back together.
- **`[tool.bumpversion]` config required** — `bump-version` wraps `bump-my-version` which needs `[tool.bumpversion]` in `pyproject.toml` with `tag = true` and `commit = true`. Without it, no tag or commit is created.
- **Never use `bump-my-version` directly** — always use `uv run bump-version patch|minor|major` which is the DerivaML CLI wrapper. Using `bump-my-version bump` directly bypasses project-specific logic.
