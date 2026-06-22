#!/usr/bin/env python3
"""Report installed-vs-latest versions of the DerivaML components.

This is the one-shot "are my DerivaML components current?" check. The three
components update through independent paths (the plugin via Claude Code's
marketplace, the MCP server via its deployment, the Python library via uv), so
there is no built-in command that tells you whether all of them are in sync.

**In the wild this cannot assume the deriva-ml source tree.** It runs against a
*user's* project, so it follows a discovery chain before trusting anything,
failing loud at the first unmet precondition (with the fix to apply):

1. **git repo?** The project must be a git working tree (deriva-ml projects are
   git repos — provenance depends on the commit hash).
2. **uv project?** A ``pyproject.toml`` must be present (the deriva-ml
   convention is uv + pyproject, not ad-hoc venvs).
3. **venv?** A ``.venv/`` (or active ``$VIRTUAL_ENV``) must exist — that is the
   environment that actually runs the user's pipeline.
4. **bootstrap from the venv interpreter.** The installed ``deriva-ml`` version
   is read by running the *venv's own* Python (``<venv>/bin/python -c
   'import deriva_ml; ...'``), NOT ``uv pip show`` — so the check does not
   depend on ``uv`` being on PATH (PATH is often incomplete, e.g. in the
   Desktop app). Whether ``uv`` is available is *reported*, not *required*.

Then it compares the installed versions against the latest published versions
on GitHub for all three components — the skills plugin, the deriva-ml library,
and the deriva-ml-mcp plugin.

Design constraints (why it looks the way it does):

- **No deriva-ml import in THIS process.** A version check must work even when
  deriva-ml is the broken thing, so this script is pure stdlib + subprocess and
  only imports deriva-ml *inside the venv's interpreter*, never here.
- **No hardcoded "latest" versions.** The predecessor skill rotted because its
  examples baked in stale values. This script asks GitHub at runtime and
  degrades to "unknown" — never a wrong hardcoded answer — when ``gh`` or the
  network is unavailable. Crucially, the library and the MCP plugin publish git
  **tags** (no GitHub Releases), while the skills plugin publishes **Releases**;
  the script reads each from the right source.

Run it against the project whose venv has deriva-ml installed:

    uv run python skills/troubleshoot-execution/scripts/check_versions.py --project /path/to/your/ml/project

(``--project`` defaults to the current directory.) Exit code is 2 when a
precondition fails (not a repo / no pyproject / no venv), 1 when a component is
behind, and 0 when everything determinable is current. Being unable to reach
GitHub for the "latest" columns is not a failure on its own.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# (owner/repo) and where "latest" lives for each component. The library and the
# MCP plugin ship git TAGS (bump-version / setuptools_scm; no GitHub Releases),
# so their latest is the highest tag. The skills plugin's tag-triggered workflow
# publishes GitHub RELEASES, so its latest is the highest release.
_LIBRARY_REPO = "informatics-isi-edu/deriva-ml"
_SKILLS_REPO = "informatics-isi-edu/deriva-ml-skills"
_MCP_REPO = "informatics-isi-edu/deriva-ml-mcp-plugin"

# Where Claude Code caches the installed skills plugin from the deriva-plugins
# marketplace; the version lives in the cached plugin.json.
_PLUGIN_CACHE_GLOB = ".claude/plugins/cache/deriva-plugins/deriva-ml/*/plugin.json"

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _parse_semver(text: str) -> tuple[int, int, int] | None:
    """Extract the first ``MAJOR.MINOR.PATCH`` triple from ``text``.

    Tolerates a leading ``v`` and surrounding noise (``v1.8.10``,
    ``deriva-ml 1.51.7``). Returns ``None`` when no triple is present.

    Example:
        >>> _parse_semver("v1.8.10")
        (1, 8, 10)
    """
    m = _VERSION_RE.search(text or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _run(cmd: list[str], cwd: Path | None = None) -> str | None:
    """Run ``cmd`` and return stripped stdout, or ``None`` on any failure.

    Never raises: a missing executable, non-zero exit, or timeout all yield
    ``None`` so callers can degrade. ``cmd[0]`` may be an absolute path (e.g. a
    venv interpreter) or a bare name resolved on PATH.
    """
    exe = cmd[0] if os.path.isabs(cmd[0]) else shutil.which(cmd[0])
    if exe is None:
        return None
    try:
        out = subprocess.run(
            [exe, *cmd[1:]],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return out.stdout.strip()


# ---------------------------------------------------------------------------
# Discovery chain (gates 1-3) + bootstrap (gate 4)
# ---------------------------------------------------------------------------


class PreconditionError(Exception):
    """A discovery gate failed; carries the user-facing fix instruction."""


def _require_git_repo(project: Path) -> None:
    """Gate 1: the project must be a git working tree."""
    out = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=project)
    if out != "true":
        raise PreconditionError(
            f"{project} is not inside a git repository. DerivaML projects are git "
            "repos (provenance records the commit hash). cd into your project, or "
            "pass --project /path/to/your/ml/project."
        )


def _require_uv_project(project: Path) -> None:
    """Gate 2: the repo must follow the deriva-ml uv convention (pyproject.toml)."""
    if not (project / "pyproject.toml").is_file():
        raise PreconditionError(
            f"No pyproject.toml in {project} — this does not look like a uv-managed "
            "DerivaML project. DerivaML projects use uv + pyproject.toml, not ad-hoc "
            "venvs or pip installs."
        )


def _find_venv(project: Path) -> Path:
    """Gate 3: locate the project venv (returns the venv root).

    Honors an active ``$VIRTUAL_ENV`` if it lives under the project; otherwise
    looks for the conventional ``.venv/``. Raises with a "run uv sync" fix when
    no venv exists.
    """
    # The project's own .venv wins. Only fall back to an active $VIRTUAL_ENV
    # if it actually lives under the project — otherwise an ambient activated
    # env (e.g. the one `uv run` activated to launch THIS script) would leak in
    # and we'd report the wrong project's deriva-ml.
    candidate = project / ".venv"
    if candidate.is_dir():
        return candidate
    active = os.environ.get("VIRTUAL_ENV")
    if active:
        ap = Path(active).resolve()
        try:
            ap.relative_to(project)  # raises if not under project
        except ValueError:
            ap = None  # ambient env from elsewhere — ignore it
        if ap is not None and ap.is_dir():
            return ap
    raise PreconditionError(
        f"No virtualenv found in {project} (looked for .venv/ and $VIRTUAL_ENV). "
        "Create and populate it first: `uv sync` in the project."
    )


def _venv_python(venv: Path) -> Path | None:
    """Return the venv's python interpreter path, or ``None`` if absent."""
    for rel in ("bin/python", "bin/python3", "Scripts/python.exe"):
        p = venv / rel
        if p.exists():
            return p
    return None


def _installed_library(venv: Path) -> tuple[str | None, str | None]:
    """Installed ``deriva-ml`` version, read via the VENV's own interpreter.

    Runs ``<venv>/bin/python -c 'import importlib.metadata ...'`` so the check
    does not depend on ``uv`` being on PATH — the venv interpreter is the
    source of truth for what the pipeline actually runs.
    """
    py = _venv_python(venv)
    if py is None:
        return None, f"venv at {venv} has no python interpreter"
    ver = _run(
        [
            str(py),
            "-c",
            "import importlib.metadata as m; print(m.version('deriva-ml'))",
        ]
    )
    if ver:
        return ver.strip(), None
    return None, f"deriva-ml is not installed in {venv} — run `uv sync` in the project"


def _uv_available() -> tuple[bool, str | None]:
    """Report whether ``uv`` is on PATH (reported, not required)."""
    if shutil.which("uv") is None:
        return False, "uv not on PATH (the check still works via the venv interpreter)"
    out = _run(["uv", "--version"])
    return True, (out or "uv (version unknown)")


def _installed_plugin() -> tuple[str | None, str | None]:
    """Installed skills-plugin version from the Claude Code cache."""
    matches = sorted(Path.home().glob(_PLUGIN_CACHE_GLOB))
    if not matches:
        return None, "plugin cache not found (~/.claude/plugins/cache/deriva-plugins/deriva-ml/)"
    best_ver: tuple[int, int, int] | None = None
    best_str: str | None = None
    for pj in matches:
        try:
            data = json.loads(pj.read_text())
        except (OSError, ValueError):
            continue
        parsed = _parse_semver(data.get("version") or "")
        if parsed and (best_ver is None or parsed > best_ver):
            best_ver, best_str = parsed, data.get("version")
    if best_str is None:
        return None, "plugin.json present but no parseable version field"
    return best_str, None


# ---------------------------------------------------------------------------
# Latest published versions (live, never hardcoded)
# ---------------------------------------------------------------------------


def _highest_semver(tags: list[str]) -> str | None:
    """Pick the maximum tag by parsed semver (ignoring non-semver tags)."""
    best_ver: tuple[int, int, int] | None = None
    best_tag: str | None = None
    for tag in tags:
        parsed = _parse_semver(tag)
        if parsed and (best_ver is None or parsed > best_ver):
            best_ver, best_tag = parsed, tag.strip()
    return best_tag


def _latest_version(repo: str, *, source: str) -> tuple[str | None, str | None]:
    """Highest-**semver** version for ``repo`` via ``gh``.

    ``source`` is ``"tags"`` (library, MCP plugin — they push git tags, no
    GitHub Releases) or ``"releases"`` (skills plugin — its workflow publishes
    Releases). Deliberately does NOT use ``gh release view`` (GitHub's "latest"
    pointer is by publish date / the latest flag, not by version — an
    out-of-order patch would be reported as newest). Returns ``(tag, None)`` or
    ``(None, reason)`` when undeterminable.
    """
    if shutil.which("gh") is None:
        return None, "gh CLI not installed — cannot determine latest version"
    if source == "tags":
        out = _run(["gh", "api", f"repos/{repo}/tags", "--paginate", "-q", ".[].name"])
        what = "tags"
    else:
        out = _run(["gh", "release", "list", "--repo", repo, "--limit", "200", "--json", "tagName", "-q", ".[].tagName"])
        what = "releases"
    if not out:
        return None, f"could not list {what} for {repo} (offline or unauthenticated?)"
    best = _highest_semver(out.splitlines())
    if best is None:
        return None, f"no semver {what} found for {repo}"
    return best, None


def _compare(installed: str | None, latest: str | None) -> str:
    """One-word status comparing installed vs latest semver."""
    pi, pl = _parse_semver(installed or ""), _parse_semver(latest or "")
    if pi is None or pl is None:
        return "unknown"
    return "current" if pi >= pl else "behind"


def _row(name: str, installed: str | None, latest: str | None, note: str | None) -> dict:
    return {
        "component": name,
        "installed": installed or "unknown",
        "latest": latest or "unknown",
        "status": _compare(installed, latest),
        "note": note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DerivaML component versions against the latest published versions.")
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Path to the DerivaML project (git repo with pyproject.toml + .venv). Default: cwd.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a table.")
    args = parser.parse_args()
    project = args.project.resolve()

    # Discovery chain: fail loud at the first unmet precondition.
    try:
        _require_git_repo(project)
        _require_uv_project(project)
        venv = _find_venv(project)
    except PreconditionError as e:
        if args.json:
            print(json.dumps({"error": str(e), "project": str(project)}, indent=2))
        else:
            print(f"Precondition failed: {e}", file=sys.stderr)
        return 2

    # Bootstrap from the venv: installed deriva-ml, and whether uv is available.
    lib_installed, lib_note = _installed_library(venv)
    uv_ok, uv_detail = _uv_available()
    plug_installed, plug_note = _installed_plugin()

    # Latest published versions (right source per component).
    lib_latest, lib_lnote = _latest_version(_LIBRARY_REPO, source="tags")
    skills_latest, skills_lnote = _latest_version(_SKILLS_REPO, source="releases")
    mcp_latest, mcp_lnote = _latest_version(_MCP_REPO, source="tags")

    rows = [
        _row("deriva-ml (library)", lib_installed, lib_latest, lib_note or lib_lnote),
        _row("deriva-ml-skills (plugin)", plug_installed, skills_latest, plug_note or skills_lnote),
        # The MCP server's RUNNING version is only knowable live (server_status);
        # offline we can still surface the latest published plugin version.
        _row("deriva-ml-mcp (plugin)", None, mcp_latest, mcp_lnote or "running version: server_status(hostname=...) — not determinable offline"),
    ]

    if args.json:
        print(json.dumps({"project": str(project), "venv": str(venv), "uv_available": uv_ok, "components": rows}, indent=2))
    else:
        print(f"Project: {project}")
        print(f"Venv:    {venv}")
        print(f"uv:      {'available — ' + uv_detail if uv_ok else uv_detail}\n")
        name_w = max(len(r["component"]) for r in rows)
        inst_w = max(len(r["installed"]) for r in rows)
        late_w = max(len(r["latest"]) for r in rows)
        print(f"{'COMPONENT':<{name_w}}  {'INSTALLED':<{inst_w}}  {'LATEST':<{late_w}}  STATUS")
        for r in rows:
            print(f"{r['component']:<{name_w}}  {r['installed']:<{inst_w}}  {r['latest']:<{late_w}}  {r['status']}")
        notes = [r for r in rows if r["note"]]
        if notes:
            print("\nNotes:")
            for r in notes:
                print(f"  - {r['component']}: {r['note']}")
        if any(r["status"] == "behind" for r in rows):
            print("\nAt least one component is behind. Update guidance: see the")
            print("'Versioning and updates' section of the troubleshoot-execution skill.")

    return 1 if any(r["status"] == "behind" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
