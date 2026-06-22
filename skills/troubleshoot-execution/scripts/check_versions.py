#!/usr/bin/env python3
"""Report installed-vs-latest versions of the DerivaML components.

This is the one-shot "are my DerivaML components current?" check. The three
components update through independent paths (the plugin via Claude Code's
marketplace, the MCP server via its deployment, the Python library via uv), so
there is no built-in command that tells you whether all of them are in sync —
this script fills that gap by reading each installed version locally and
comparing it against the latest published release.

Design constraints (why it looks the way it does):

- **No deriva-ml import.** A version check has to work even when deriva-ml is
  broken or mismatched, so this script is pure stdlib + subprocess. Importing
  deriva-ml would defeat the purpose.
- **No hardcoded "latest" versions.** The predecessor skill rotted because its
  examples baked in stale values / referenced a deleted script. This script
  asks GitHub for the latest release at runtime (via the ``gh`` CLI) and
  degrades to "unknown" — never a wrong hardcoded answer — when ``gh`` or the
  network is unavailable.
- **Every probe degrades gracefully.** A missing tool, an absent plugin-cache
  path, or no project venv yields ``unknown`` with a one-line reason rather
  than a traceback. A partial answer is still useful.

Run it (from anywhere; pass --project to point at the venv that has deriva-ml):

    uv run python skills/troubleshoot-execution/scripts/check_versions.py
    uv run python .../check_versions.py --project /path/to/your/ml/project

Exit code is 0 when every component that could be determined is current, 1 when
at least one is behind, and 0 (with notes) when latest versions couldn't be
fetched — being unable to reach GitHub is not itself a failure.
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

# (owner/repo) for the two components published as GitHub releases.
_LIBRARY_REPO = "informatics-isi-edu/deriva-ml"
_PLUGIN_REPO = "informatics-isi-edu/deriva-ml-skills"

# Where Claude Code caches the installed plugin from the deriva-plugins
# marketplace. The version lives in the cached plugin.json. The glob accounts
# for the version-stamped subdirectory Claude Code creates.
_PLUGIN_CACHE_GLOB = "plugins/cache/deriva-plugins/deriva-ml/*/plugin.json"

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _parse_semver(text: str) -> tuple[int, int, int] | None:
    """Extract the first ``MAJOR.MINOR.PATCH`` triple from ``text``.

    Tolerates a leading ``v`` and surrounding noise (e.g. ``v1.8.10``,
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
    ``None`` so callers can degrade to "unknown".
    """
    exe = shutil.which(cmd[0])
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

    ``source`` selects where "latest" lives, which differs per component:

    - ``"tags"`` — the library (``deriva-ml``) ships via ``bump-version`` /
      ``setuptools_scm``, which pushes git **tags** but publishes no GitHub
      Releases (releases there stop at an old version). The truth is the
      highest tag.
    - ``"releases"`` — the plugin repos publish GitHub **Releases** from their
      tag-triggered workflow; the highest release tag is the truth.

    Deliberately does NOT use ``gh release view`` (GitHub's "latest" pointer is
    sorted by publish date / the latest flag, not by version — an out-of-order
    patch would be reported as newest). We list everything and take the max by
    parsed semver, which is what "are you up to date?" actually means.

    Returns ``(tag, None)`` or ``(None, reason)`` when undeterminable.
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


def _installed_library(project: Path) -> tuple[str | None, str | None]:
    """Installed ``deriva-ml`` version, preferring the project venv.

    Tries ``uv pip show`` in the project dir first (the venv that actually runs
    the user's pipeline), then falls back to ``python -c 'importlib.metadata'``.
    """
    out = _run(["uv", "pip", "show", "deriva-ml"], cwd=project)
    if out:
        for line in out.splitlines():
            if line.lower().startswith("version:"):
                return line.split(":", 1)[1].strip(), None
    # Fallback: importlib.metadata in whatever interpreter is on PATH.
    meta = _run(
        [
            "python",
            "-c",
            "import importlib.metadata as m; print(m.version('deriva-ml'))",
        ],
        cwd=project,
    )
    if meta:
        return meta.strip(), None
    return None, "deriva-ml not found in project venv (run from the project, or pass --project)"


def _installed_plugin() -> tuple[str | None, str | None]:
    """Installed ``deriva-ml`` plugin version from the Claude Code cache."""
    matches = sorted(Path.home().glob(f".claude/{_PLUGIN_CACHE_GLOB}"))
    if not matches:
        return None, "plugin cache not found (~/.claude/plugins/cache/deriva-plugins/deriva-ml/)"
    # If several version-stamped dirs exist, the newest semver wins.
    best_ver: tuple[int, int, int] | None = None
    best_str: str | None = None
    for pj in matches:
        try:
            data = json.loads(pj.read_text())
        except (OSError, ValueError):
            continue
        ver = data.get("version")
        parsed = _parse_semver(ver or "")
        if parsed and (best_ver is None or parsed > best_ver):
            best_ver, best_str = parsed, ver
    if best_str is None:
        return None, "plugin.json present but no parseable version field"
    return best_str, None


def _compare(installed: str | None, latest: str | None) -> str:
    """One-word status comparing installed vs latest semver."""
    pi, pl = _parse_semver(installed or ""), _parse_semver(latest or "")
    if pi is None or pl is None:
        return "unknown"
    if pi >= pl:
        return "current"
    return "behind"


def _row(name: str, installed: str | None, latest: str | None, note: str | None) -> dict:
    return {
        "component": name,
        "installed": installed or "unknown",
        "latest": latest or "unknown",
        "status": _compare(installed, latest),
        "note": note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DerivaML component versions against the latest releases.")
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Path to the project whose venv has deriva-ml installed (default: cwd).",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a table.")
    args = parser.parse_args()

    rows: list[dict] = []

    # 1. deriva-ml Python library — installed in the project venv vs the
    # highest git TAG (the library publishes tags, not GitHub Releases).
    lib_installed, lib_note = _installed_library(args.project)
    lib_latest, lib_latest_note = _latest_version(_LIBRARY_REPO, source="tags")
    rows.append(_row("deriva-ml (library)", lib_installed, lib_latest, lib_note or lib_latest_note))

    # 2. deriva-ml Claude Code plugin — local cache vs the highest GitHub
    # RELEASE (the plugin repo's workflow publishes releases on tag push).
    plug_installed, plug_note = _installed_plugin()
    plug_latest, plug_latest_note = _latest_version(_PLUGIN_REPO, source="releases")
    rows.append(_row("deriva-ml (plugin)", plug_installed, plug_latest, plug_note or plug_latest_note))

    # 3. deriva-ml-mcp server — informational only. The running version comes
    # from the MCP `server_status` tool (needs a live host + the MCP wire),
    # which this offline script can't call. Surface it as a pointer, not a probe.
    rows.append(
        _row(
            "deriva-ml-mcp (server)",
            None,
            None,
            "check live via the server_status(hostname=...) MCP tool — not determinable offline",
        )
    )

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
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

    # Exit 1 only when something is definitively behind; "unknown" is not a
    # failure (being offline shouldn't break a script meant to run anywhere).
    return 1 if any(r["status"] == "behind" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
