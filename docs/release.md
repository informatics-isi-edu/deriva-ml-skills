# Release runbook — deriva-ml-skills

Referenced from [`CLAUDE.md`](../CLAUDE.md) → "Releasing". Shared `bump-version`
rules live in the workspace-level `../CLAUDE.md`.

## Steps

1. Commit changes on `main` (working tree must be clean).
2. Run `uv run bump-version patch|minor|major`. This bumps `plugin.json` and
   `[tool.bumpversion] current_version`, commits, tags, and pushes. Never create
   release tags by hand.
3. The `v*.*.*` tag triggers `.github/workflows/release.yml`, which:
   - warns if `plugin.json`'s version doesn't match the tag;
   - builds `deriva-ml-skills-{VERSION}.tar.gz` from `.claude-plugin/`, `skills/`
     and `hooks/` only;
   - drafts the GitHub Release with auto-generated notes.
4. **Manual: bump the meta-marketplace** (below). Without it, users on
   `autoUpdate: true` stay on the previous version.

After step 4, `autoUpdate` users pick up the new version on their next Claude Code
restart.

### `hooks/` must stay in the tarball

`hooks/hooks.json` declares the tacit-knowledge capture hooks: a `SessionStart`
hook (`hooks/session-start`) that injects the full capture discipline once, and a
`UserPromptSubmit` hook (`hooks/user-prompt-submit`) that re-injects a short
directive every turn so the trigger isn't demoted as context grows. They are a
pair — the session-start contract carries the do-NOT-fire boundary that lets the
per-turn line stay terse. Drop `hooks/` from the tar and the discipline silently
ships nowhere. Both scripts are tracked executable (`100755`); tar preserves the
mode.

## Bumping the meta-marketplace

The [`deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins)
meta-marketplace is updated **by hand** after every release. Two pieces:

1. The **version pin** in `.claude-plugin/marketplace.json` — what `autoUpdate`
   users get.
2. A **`deriva-ml--v{version}` tag** — what Claude Code's `dependencies:` resolver
   scans. No plugin currently depends on `deriva-ml`, but the tag is created to
   keep the convention.

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

# Tag naming `{plugin-name}--v{version}` is required by Claude Code.
git tag deriva-ml--v1.3.2

# Push the commit, then the tag EXPLICITLY by name.
git push
git push origin deriva-ml--v1.3.2
```

Sanity-check the diff before pushing — `jq` rewrites the whole file, so exactly one
line should change.

**Push the tag by name.** `git tag deriva-ml--v1.3.2` makes a *lightweight* tag,
and `git push --follow-tags` only pushes *annotated* tags — it would push the
commit and silently skip the tag. If you prefer `--follow-tags`, create an
annotated tag instead (`git tag -a deriva-ml--v1.3.2 -m "deriva-ml 1.3.2"`).

**Failure modes:**

- Skip the version-pin bump → `autoUpdate` users stay on the old version. No error.
- Skip the prefixed tag → any plugin declaring
  `dependencies: [{name: "deriva-ml", ...}]` fails with `no-matching-tag`.

**This plugin depends on `deriva@^1.2.0`** (`plugin.json` → `dependencies`), so
`deriva-ml` won't install unless a matching `deriva--v*` tag exists on the
meta-marketplace. That deriva-side tag is the load-bearing one — see
`deriva-skills/CLAUDE.md` for its bump procedure.

Automating this (an Actions workflow that opens a PR against `deriva-plugins` on
tag push) is deferred; until then the manual step is part of every release.
