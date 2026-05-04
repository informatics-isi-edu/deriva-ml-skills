#!/usr/bin/env python3
"""Cross-reference drift detector for deriva-ml-skills.

Three checks against the skills tree:

1. ``/deriva-ml:<name>`` references resolve to a sibling skill in this
   repo's ``skills/<name>/``. (HARD — fail on miss.)
2. ``/deriva:<name>`` references resolve to a tier-1 skill in
   ``../deriva-skills/skills/<name>/``. (SOFT — warn-only when the
   tier-1 repo is unavailable; HARD when it is.)
3. ``deriva_ml_<name>`` mentions correspond to a tool registered in
   ``../deriva-ml-mcp``'s tool registry. (SOFT — warn-only when the
   mcp repo is unavailable; HARD when it is.)

Usage::

    uv run python scripts/check_drift.py

Exit codes:
    0 — all checks passed (warnings allowed)
    1 — at least one HARD-mode check failed

The script is intentionally dependency-free (stdlib only) so CI does
not need to ``uv sync`` the dev/test groups to run it.

Example:
    $ uv run python scripts/check_drift.py
    OK: 22 /deriva-ml: refs, 11 /deriva: refs, 50 deriva_ml_* mentions
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
TIER1_REPO = REPO_ROOT.parent / "deriva-skills"
MCP_REPO = REPO_ROOT.parent / "deriva-ml-mcp"

# Match `/deriva-ml:<name>` and `/deriva:<name>`. The trailing
# negative-lookahead on `-` distinguishes `/deriva:foo` from
# `/deriva-ml:foo` so we don't double-count.
INTRA_RE = re.compile(r"/deriva-ml:([a-z][a-z0-9-]*)")
TIER1_RE = re.compile(r"/deriva:(?!ml:)([a-z][a-z0-9-]*)")
TOOL_RE = re.compile(r"\bderiva_ml_([a-z][a-z0-9_]*)")

# Python package / module names that share the `deriva_ml_*` prefix
# but are NOT tool names. Excluded so they don't trip the drift
# detector when documented in skill bodies.
TOOL_NAME_EXCLUDES = frozenset({
    "apps",   # `deriva_ml_apps` — companion app package
    "mcp",    # `deriva_ml_mcp` — the MCP server package itself
})


def collect_text() -> str:
    """Concatenate every SKILL.md and references/*.md under skills/."""
    parts: list[str] = []
    for path in SKILLS_DIR.rglob("*.md"):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def check_intra(text: str) -> tuple[set[str], list[str]]:
    """Check intra-tier `/deriva-ml:<name>` references resolve."""
    refs = set(INTRA_RE.findall(text))
    skills = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    missing = sorted(refs - skills)
    return refs, [f"/deriva-ml:{n} → no skills/{n}/" for n in missing]


def check_tier1(text: str) -> tuple[set[str], list[str], bool]:
    """Check tier-1 `/deriva:<name>` references; soft when repo absent."""
    refs = set(TIER1_RE.findall(text))
    tier1_skills_dir = TIER1_REPO / "skills"
    if not tier1_skills_dir.is_dir():
        return refs, [], False  # soft: tier-1 unavailable
    skills = {p.name for p in tier1_skills_dir.iterdir() if p.is_dir()}
    missing = sorted(refs - skills)
    return refs, [f"/deriva:{n} → no {tier1_skills_dir}/{n}/" for n in missing], True


def check_tools(text: str) -> tuple[set[str], list[str], bool]:
    """Check `deriva_ml_<name>` mentions match registered MCP tools."""
    mentions = set(TOOL_RE.findall(text)) - TOOL_NAME_EXCLUDES
    plugin_json = MCP_REPO / ".claude-plugin" / "plugin.json"
    # Tool registry lives in the source — search for @mcp.tool decorated
    # function names. Fall back to a static list file if present.
    src_dir = MCP_REPO / "src" / "deriva_ml_mcp"
    if not src_dir.is_dir():
        return mentions, [], False
    registered: set[str] = set()
    # Tools are registered with `@ctx.tool(...)` followed by an
    # `async def deriva_ml_<name>(...)` (or plain `def`). Match the
    # decorator + (async )? def form so we count exactly the
    # decorated entrypoints, not internal helpers named `deriva_ml_*`.
    decorator_re = re.compile(
        r"@ctx\.tool\b[^\n]*\n\s*(?:async\s+)?def\s+(deriva_ml_[a-z0-9_]+)"
    )
    for py in src_dir.rglob("*.py"):
        registered.update(decorator_re.findall(py.read_text(encoding="utf-8")))
    stale = sorted(f"deriva_ml_{m}" for m in mentions if f"deriva_ml_{m}" not in registered)
    return mentions, [f"{n} → not registered in deriva-ml-mcp" for n in stale], True


def main() -> int:
    text = collect_text()
    intra_refs, intra_errs = check_intra(text)
    tier1_refs, tier1_errs, tier1_hard = check_tier1(text)
    tool_mentions, tool_errs, tool_hard = check_tools(text)

    any_hard_fail = bool(intra_errs) or (tier1_hard and tier1_errs) or (tool_hard and tool_errs)

    if intra_errs:
        print("HARD: intra-tier `/deriva-ml:` reference drift")
        for line in intra_errs:
            print(f"  {line}")

    if tier1_errs:
        prefix = "HARD" if tier1_hard else "WARN"
        print(f"{prefix}: tier-1 `/deriva:` reference drift")
        for line in tier1_errs:
            print(f"  {line}")
    elif not tier1_hard:
        print(f"NOTE: tier-1 repo at {TIER1_REPO} not found — skipping `/deriva:` checks")

    if tool_errs:
        prefix = "HARD" if tool_hard else "WARN"
        print(f"{prefix}: `deriva_ml_*` mention drift")
        for line in tool_errs:
            print(f"  {line}")
    elif not tool_hard:
        print(f"NOTE: mcp repo at {MCP_REPO} not found — skipping tool checks")

    if not any_hard_fail:
        print(
            f"OK: {len(intra_refs)} /deriva-ml: refs, "
            f"{len(tier1_refs)} /deriva: refs, "
            f"{len(tool_mentions)} deriva_ml_* mentions"
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
