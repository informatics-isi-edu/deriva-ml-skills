#!/usr/bin/env python3
"""Run skill description optimization for all DerivaML skills.

Requires the skill-creator plugin to be installed in Claude Code.
The script discovers paths dynamically rather than using hardcoded locations.
"""

import json
import os
import sys
from pathlib import Path


def _find_skill_creator() -> Path | None:
    """Find the skill-creator plugin in the Claude Code plugin cache."""
    cache_dir = Path.home() / ".claude" / "plugins" / "cache" / "claude-plugins-official" / "skill-creator"
    if not cache_dir.exists():
        return None
    # Find the most recent version directory
    version_dirs = [d for d in cache_dir.iterdir() if d.is_dir() and (d / "skills" / "skill-creator").is_dir()]
    if not version_dirs:
        return None
    # Sort by modification time, most recent first
    version_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return version_dirs[0] / "skills" / "skill-creator"


def _find_skills_dir() -> Path | None:
    """Find the deriva-skills repository root.

    Tries walking up from this script's location first, then checks
    common development directory patterns.
    """
    # This script lives inside the skills repo: skills/optimization/run_all.py
    script_dir = Path(__file__).resolve().parent
    # Walk up to find repo root
    for parent in [script_dir, *script_dir.parents]:
        if (parent / ".claude-plugin" / "plugin.json").exists():
            return parent / "skills"
        if parent == parent.parent:
            break

    return None


SKILL_CREATOR = _find_skill_creator()
if SKILL_CREATOR is None:
    print("ERROR: skill-creator plugin not found in Claude Code plugin cache.", file=sys.stderr)
    print("  Install it with: /plugin install skill-creator", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(SKILL_CREATOR))
os.chdir(SKILL_CREATOR)

from scripts.run_loop import run_loop
from scripts.utils import parse_skill_md

SKILLS_DIR = _find_skills_dir()
if SKILLS_DIR is None:
    print("ERROR: Could not find deriva-skills repository.", file=sys.stderr)
    print("  Run this script from within the deriva-skills repo.", file=sys.stderr)
    sys.exit(1)

OPT_DIR = SKILLS_DIR / "optimization"
RESULTS_DIR = OPT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Map skill names to paths
SKILL_MAP = {}
for skill_md in SKILLS_DIR.rglob("SKILL.md"):
    skill_dir = skill_md.parent
    name, description, content = parse_skill_md(skill_dir)
    if name:
        SKILL_MAP[name] = str(skill_dir)

MODEL = "claude-opus-4-6"
MAX_ITERATIONS = 3

def run_one(name: str):
    eval_file = OPT_DIR / f"{name}-evals.json"
    skill_path = SKILL_MAP.get(name)
    result_file = RESULTS_DIR / f"{name}-result.json"

    if not eval_file.exists():
        print(f"SKIP {name}: no eval file")
        return
    if not skill_path:
        print(f"SKIP {name}: skill not found")
        return
    if result_file.exists():
        print(f"SKIP {name}: already optimized")
        return

    print(f"\n{'='*60}")
    print(f"OPTIMIZING: {name}")
    print(f"  Skill: {skill_path}")
    print(f"  Evals: {eval_file}")
    print(f"{'='*60}\n")

    with open(eval_file) as f:
        eval_set = json.load(f)

    try:
        result = run_loop(
            eval_set=eval_set,
            skill_path=Path(skill_path),
            description_override=None,
            num_workers=3,
            timeout=30,
            max_iterations=MAX_ITERATIONS,
            runs_per_query=3,
            trigger_threshold=0.5,
            holdout=0.4,
            model=MODEL,
            verbose=True,
            log_dir=RESULTS_DIR / name,
        )

        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"\nRESULT for {name}:")
        if isinstance(result, dict):
            best = result.get("best_description", "N/A")
            print(f"  Best description: {best[:100]}...")
        print(f"  Saved to: {result_file}")

    except Exception as e:
        print(f"ERROR optimizing {name}: {e}")
        with open(result_file, "w") as f:
            json.dump({"error": str(e), "skill": name}, f, indent=2)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", help="Optimize a single skill by name")
    parser.add_argument("--list", action="store_true", help="List all skills")
    args = parser.parse_args()

    if args.list:
        for name in sorted(SKILL_MAP.keys()):
            eval_exists = (OPT_DIR / f"{name}-evals.json").exists()
            result_exists = (RESULTS_DIR / f"{name}-result.json").exists()
            status = "done" if result_exists else ("ready" if eval_exists else "no-evals")
            print(f"  [{status}] {name}")
        sys.exit(0)

    if args.skill:
        run_one(args.skill)
    else:
        # Run all skills that have eval sets
        names = sorted(n for n in SKILL_MAP if (OPT_DIR / f"{n}-evals.json").exists())
        print(f"Optimizing {len(names)} skills...")
        for name in names:
            run_one(name)
        print(f"\nDone! Results in {RESULTS_DIR}")
