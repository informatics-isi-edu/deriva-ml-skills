---
name: check-deriva-ml-versions
description: "Check if the DerivaML ecosystem (deriva-ml Python lib, deriva-ml-mcp plugin, deriva-ml-skills plugin) is up to date and offer to update outdated components. Use when the user asks about ML-side versions, updates, or whether their DerivaML environment is current. Triggers on: 'check ml versions', 'am I up to date deriva-ml', 'update deriva-ml', 'what version of deriva-ml', 'upgrade derivaml packages'."
disable-model-invocation: true
---

# Check and Update DerivaML Ecosystem

Check whether the user's DerivaML components are up to date, then offer to update each outdated component.

This skill covers the **tier-2** surface — the DerivaML-specific components that build on top of the core Deriva ecosystem. It assumes the tier-1 surface (`deriva-py`, `deriva-mcp-core`, `deriva` plugin) has already been checked via `/deriva:check-deriva-versions`. **Run that skill first**; if its components are outdated, update them before checking the ML layer (deriva-ml depends on deriva-py; deriva-ml-mcp depends on deriva-mcp-core).

**Important:** Skills (including this one) are a Claude Code feature. Claude Desktop does not have plugins or skills — it only has MCP servers. If running in Claude Desktop, you can only check the MCP server (deriva-ml-mcp) version.

## Components to Check

| Component | What | How to check | Who can update |
|-----------|------|-------------|----------------|
| **deriva-ml** | Python library in the project's `.venv` (DerivaML domain library) | Script (needs project venv) | Claude (automated) |
| **deriva-ml-skills** | The `deriva-ml` Claude Code plugin (this plugin) | Script (reads plugin cache) | Automated (cache refresh + restart) |
| **deriva-ml-mcp** | DerivaML MCP plugin loaded by deriva-mcp-core | `deriva://server/version` resource (look for `deriva-ml-mcp` plugin entry) | User (restart required) |

> **Note:** This skill invokes the shared `check_versions.py` script that lives in the **`deriva-skills`** plugin (the tier-1 sibling). The script knows about the entire ecosystem (tier-1 + tier-2 components) and the `--component` flag is the boundary. The script will be split between the two plugins during Phase 4 of the restructure (the v1.4 MCP surface sweep); until then, point at the tier-1 plugin's copy as shown in the commands below. Users who do NOT have the `deriva-skills` plugin installed must install it first (this skill assumes both plugins are present, since deriva-ml-skills declares deriva-skills as a documented dependency).

## Workflow

### Step 0: Run the tier-1 check first

If you have not already run `/deriva:check-deriva-versions` in this session, do so now. The DerivaML stack depends on the core Deriva stack — it makes no sense to update `deriva-ml` while `deriva-py` is stale.

If the user explicitly asks for ML-only checks, you may skip this — but mention the dependency.

### Step 1: Check deriva-ml version

The script must run in the **project's Python environment**. Follow this sequence:

1. **Check if CWD has a `pyproject.toml`** — if yes, run from here:
   ```bash
   uv run python3 ~/.claude/plugins/cache/deriva-plugins/deriva/skills/check-deriva-versions/scripts/check_versions.py --component deriva-ml --json
   ```
   (Path is the install location of the `deriva-skills` plugin's marketplace cache. Substitute the actual path if your Claude Code install uses a different cache root — read `~/.claude/plugins/known_marketplaces.json` for the `deriva-plugins` entry's `installLocation`.)

2. **If no `pyproject.toml` in CWD**, ask the user:
   > "I need to check the `deriva-ml` version in your project's virtual environment. What directory is your DerivaML project in?"

   Then `cd` to that directory and run with `uv run python3`.

3. **If the user has no local project** (MCP-only workflow), skip this component — they don't have a local `deriva-ml` install to check.

### Step 2: Check deriva-ml-skills plugin version

```bash
python3 ~/.claude/plugins/cache/deriva-plugins/deriva/skills/check-deriva-versions/scripts/check_versions.py --component skills --json
```

This reads the plugin cache and compares against the latest GitHub release tag.

> **Note:** The shared script's `--component skills` flag currently reports the `deriva-skills` (tier-1) plugin. A dedicated tier-2 script that reports on `deriva-ml-skills` specifically lands in Phase 4 of the restructure. Until then, manually inspect the `deriva-ml-skills` plugin version by reading `~/.claude/plugins/cache/deriva-ml-plugins/deriva-ml/.claude-plugin/plugin.json` and comparing against the latest tag at `informatics-isi-edu/deriva-ml-skills`.

**Skip this in Claude Desktop** — Desktop doesn't have plugins.

### Step 3: Check deriva-ml-mcp plugin version

Read the `deriva://server/version` resource. The response includes the running deriva-mcp-core framework version plus a list of loaded plugins; look for the `deriva-ml-mcp` entry.

If the resource read fails (MCP server not running), report as "UNKNOWN — MCP server not running". If the resource succeeds but no `deriva-ml-mcp` entry appears, report as "NOT LOADED — deriva-ml-mcp plugin not active in this server".

Compare the returned plugin version against the latest release tag for `informatics-isi-edu/deriva-mcp` (legacy repo name; the script knows this).

### Step 4: Present results

Show a summary table:

| Component | Status | Installed | Latest |
|-----------|--------|-----------|--------|
| deriva-ml | UP TO DATE | 1.25.1 | v1.25.1 |
| deriva-ml-skills | OUTDATED | 0.12.1 | v0.12.2 |
| deriva-ml-mcp | UP TO DATE | 1.4.0 | v1.4.0 |

If everything is up to date, say so and stop. Otherwise, proceed to Step 5.

### Step 5: Offer updates for outdated components

#### deriva-ml (automated)

```bash
uv run python3 ~/.claude/plugins/cache/deriva-plugins/deriva/skills/check-deriva-versions/scripts/check_versions.py --component deriva-ml --update
```

This runs `uv lock --upgrade-package deriva-ml && uv sync` and verifies the new version.

#### deriva-ml-skills (Claude Code only)

Run the update script, which refreshes the local marketplace cache:
```bash
python3 ~/.claude/plugins/cache/deriva-plugins/deriva/skills/check-deriva-versions/scripts/check_versions.py --component skills --update
```

The script checks whether `autoUpdate` is enabled in `~/.claude/settings.json` and adjusts its advice (same logic as the tier-1 sibling).

#### deriva-ml-mcp (user action — restart required)

The MCP server cannot be updated by Claude because restarting it breaks the MCP connection mid-session. Tell the user how to update based on their deployment:

- **Docker** (most common): `docker pull ghcr.io/informatics-isi-edu/deriva-mcp:latest && docker restart deriva-mcp` (the container ships both core and ml-mcp; updating the image updates both)
- **Native install**: `cd <project-dir> && uv lock --upgrade-package deriva-ml-mcp && uv sync`, then restart the server

### Step 6: Confirm

After updates, re-run the relevant checks to confirm everything is current.

## Status Values

- **UP TO DATE** — No action needed
- **OUTDATED** — Newer version available; offer to update
- **UPDATED** — Successfully updated (shown after `--update`)
- **UNKNOWN** — Could not determine status (not installed, server not running, network issue)
- **NOT LOADED** — Component is installed but the MCP plugin is not active in the running server
- **Dev version** — Installed from git HEAD, at or ahead of latest release. Normal for developers working on the library itself.

## Related Skills

- **`/deriva:check-deriva-versions`** *(tier-1)* — Run this first to verify the foundational Deriva ecosystem (deriva-py, deriva-mcp-core, deriva plugin) is current before checking the ML layer.
