"""Scaffold the tacit-knowledge artifacts into a DerivaML project.

Run once at project setup (not user-invocable in the loop). Creates the
append-only OKF Log, the derived-index placeholder, the seed topic controlled
vocabulary, the domain-background bundle root, and the .gitattributes merge
drivers — then leaves the seed CV for human review.

The fixed baseline below is the deterministic floor every project gets. An LLM
augment step (see augment_topics, called by the invoking skill, not this script)
adds project-specific guesses; the combined set is human-reviewed before it
becomes the CV.

Example:
    $ uv run python seed_tk_topics.py --repo-root /path/to/project --project-name EyeAI
    Wrote tacit-knowledge.md, docs/tacit-knowledge/topics.md,
    docs/tacit-knowledge/index.md, docs/domain/index.md, .gitattributes.
    Review docs/tacit-knowledge/topics.md before committing.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _find_uv() -> str | None:
    """Locate the uv binary under a possibly-minimal PATH.

    Claude Code (especially the Desktop app) may not source shell profiles, so
    $PATH can be incomplete. Try shutil.which first, then well-known install
    locations.

    Returns:
        Absolute path to uv, or None if it cannot be found.

    Example:
        >>> _find_uv() is None or _find_uv().endswith("uv")
        True
    """
    found = shutil.which("uv")
    if found:
        return found
    for base in ("~/.local/bin", "~/.cargo/bin", "/opt/homebrew/bin", "/usr/local/bin"):
        candidate = Path(base).expanduser() / "uv"
        if candidate.exists():
            return str(candidate)
    return None


def fixed_baseline_topics() -> list[dict]:
    """Return the deterministic seed topic CV — the floor every project gets.

    Two axis kinds (D11): entity-anchored (the five DerivaML abstractions) and
    entity-free (process, domain, tooling, team — because not all tacit
    knowledge is about a catalog object).

    Returns:
        A list of {"term", "axis", "description"} dicts, authored to the
        term-naming-strategy discipline (one dimension, substitution test).

    Example:
        >>> terms = fixed_baseline_topics()
        >>> "dataset-construction" in {t["term"] for t in terms}
        True
    """
    entity_anchored = [
        ("dataset-construction", "how a dataset was assembled, split, or subsampled"),
        ("dataset-versioning", "why a dataset version was cut or pinned"),
        ("feature-design", "why a feature exists and how it is shaped"),
        ("model-configuration", "hyperparameter and architecture choices for a model"),
        ("workflow-typing", "why a workflow was classified as it was"),
        (
            "execution-provenance",
            "what an execution consumed, produced, or established",
        ),
    ]
    entity_free = [
        ("process-convention", "a recurring 'whenever we do X we also do Y' pattern"),
        ("domain-background", "target-domain facts, confounds, and conventions"),
        ("tooling-gotcha", "a non-obvious behavior of the toolchain or platform"),
        ("team-ownership", "role/process facts about who owns or decides what"),
        ("dead-end", "an approach that was tried and abandoned, and why"),
    ]
    topics: list[dict] = []
    for term, desc in entity_anchored:
        topics.append({"term": term, "axis": "entity-anchored", "description": desc})
    for term, desc in entity_free:
        topics.append({"term": term, "axis": "entity-free", "description": desc})
    return topics


def render_topics_md(topics: list[dict]) -> str:
    """Render the topic CV as an OKF controlled-term list.

    Args:
        topics: The term dicts from fixed_baseline_topics (+ any augmentation).

    Returns:
        Markdown with OKF frontmatter and one entry per term, grouped by axis.

    Example:
        >>> render_topics_md(fixed_baseline_topics()).startswith("---")
        True
    """
    lines = [
        "---",
        "type: Index",
        "title: Tacit Knowledge — topic controlled vocabulary",
        "description: >",
        "  Repo-local controlled vocabulary the LLM classifies tacit-knowledge",
        "  entries against. Human-gated: new terms are proposed into the index's",
        "  candidate-terms list and confirmed here. Cross-links catalog CV terms by RID.",
        "tags: [tacit-knowledge, vocabulary, deriva-ml]",
        "---",
        "",
        "# Tacit Knowledge — Topic Vocabulary",
        "",
        "Each entry in `tacit-knowledge.md` is classified under one or more of these",
        "terms. Reuse an existing term via synonym-aware lookup before proposing a new",
        "one; new terms are human-gated (see the index's `candidate-terms` list).",
        "",
    ]
    for axis in ("entity-anchored", "entity-free"):
        lines.append(f"## {axis}")
        lines.append("")
        for t in topics:
            if t["axis"] == axis:
                lines.append(f"- **{t['term']}** — {t['description']}")
        lines.append("")
    return "\n".join(lines)


def render_empty_index_md() -> str:
    """Render the derived-index placeholder (no entries indexed yet).

    Returns:
        Markdown OKF type:Index with covers_through pointing before the first entry.

    Example:
        >>> "type: Index" in render_empty_index_md()
        True
    """
    return "\n".join(
        [
            "---",
            "type: Index",
            "title: Tacit Knowledge — retrieval index",
            "description: >",
            "  Derived candidate index over tacit-knowledge.md. Cache, not record —",
            "  rebuilt whole by the capture side-effect. Never hand-edit; never hand-merge.",
            "generated_from: tacit-knowledge.md",
            "generated_at: (not yet built)",
            "generator: capture-tacit-knowledge rebuild",
            "covers_through:",
            "  id: (none)",
            "  offset: 0",
            "tags: [tacit-knowledge, index, deriva-ml]",
            "---",
            "",
            "# Tacit Knowledge — Retrieval Index",
            "",
            "_No entries indexed yet. This file is rebuilt whole as a silent side-effect of",
            "capture once entries accumulate past the rebuild threshold (see",
            "`skills/capture-tacit-knowledge/references/index-and-retrieval.md`)._",
            "",
            "## Rows",
            "",
            "| anchor | concept keywords | tk-NNN | superseded-by |",
            "|---|---|---|---|",
            "",
            "## candidate-terms (proposed, awaiting human review)",
            "",
            "_none_",
            "",
        ]
    )


def render_log_frontmatter(project_name: str) -> str:
    """Render the OKF Log frontmatter block for tacit-knowledge.md.

    Args:
        project_name: The human project name, interpolated into the title.

    Returns:
        The YAML frontmatter block plus the H1 and boundary-explaining header.

    Example:
        >>> "type: Log" in render_log_frontmatter("EyeAI")
        True
    """
    return "\n".join(
        [
            "---",
            "type: Log",
            f"title: Tacit Knowledge — {project_name}",
            "description: >",
            "  The why behind this project's DerivaML decisions — rationale, dead ends,",
            "  and cross-discipline consequences that the catalog records but does not",
            "  explain. Append-only; each entry is a dated tk-… decision record.",
            "tags: [tacit-knowledge, provenance, deriva-ml]",
            "---",
            "",
            "# Tacit Knowledge",
            "",
            "This file records the *why* behind decisions about this project's models and",
            "data — intent and reasoning the catalog cannot store. The catalog is the source",
            "of truth for *what* exists (RIDs, configs, numbers, lineage); this file is the",
            "source of truth for *why*. Don't replicate catalog-stored facts here — link to",
            "them by RID. Append-only: never rewrite an entry (supersession is an additive",
            "edge, not an edit).",
            "",
        ]
    )


def render_gitattributes() -> str:
    """Render the .gitattributes merge drivers for the tacit-knowledge files.

    Returns:
        Three merge-driver lines (union for Log + CV, ours for the derived index).

    Example:
        >>> "merge=union" in render_gitattributes()
        True
    """
    return "\n".join(
        [
            "# Tacit-knowledge merge drivers (see capture-tacit-knowledge D12).",
            "# Log and topic CV union-merge (both branches append); the derived index is",
            "# regenerated post-merge, never hand-merged.",
            "tacit-knowledge.md             merge=union",
            "docs/tacit-knowledge/topics.md merge=union",
            "docs/tacit-knowledge/index.md  merge=ours",
            "",
        ]
    )


def render_domain_index_md() -> str:
    """Render the docs/domain/ bundle root (an Index over Concept docs).

    Returns:
        Markdown OKF type:Index describing the domain-background bundle.

    Example:
        >>> "docs/domain" in render_domain_index_md() or "Concept" in render_domain_index_md()
        True
    """
    return "\n".join(
        [
            "---",
            "type: Index",
            "title: Domain Background",
            "description: >",
            "  Semantic, refined-in-place background about the target domain — facts,",
            "  confounds, methodological conventions a cross-disciplinary newcomer needs.",
            "  One type:Concept doc per subject. Distinct from the episodic tacit-knowledge",
            "  Log and from docs/design/ up-front plans.",
            "tags: [domain, concept, deriva-ml]",
            "---",
            "",
            "# Domain Background",
            "",
            "One `type: Concept` doc per subject (e.g. `staining-variance.md`). Refined in",
            "place over time. Link catalog vocabulary-term descriptions by RID rather than",
            "restating them. A tacit-knowledge Log entry may *anchor* to a subject here",
            "(Family C of the anchor taxonomy).",
            "",
            "## Subjects",
            "",
            "_none yet_",
            "",
        ]
    )


def is_gitignored(repo_root: str, relpath: str) -> bool:
    """Check whether relpath would be ignored by the repo's .gitignore.

    Uses `git check-ignore` when git is available; falls back to a direct
    line-match against .gitignore otherwise. The Log must never be gitignored.

    Args:
        repo_root: Absolute path to the repository root.
        relpath: Path relative to repo_root to test.

    Returns:
        True if the path is ignored.

    Example:
        >>> is_gitignored("/nonexistent", "x")  # no .gitignore -> not ignored
        False
    """
    gitignore = Path(repo_root) / ".gitignore"
    if not gitignore.exists():
        return False
    target = relpath.strip().rstrip("/")
    for raw in gitignore.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.rstrip("/") == target or line == f"{target}":
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    """Scaffold the tacit-knowledge artifacts into --repo-root.

    Args:
        argv: CLI args (defaults to sys.argv[1:]).

    Returns:
        Process exit code (0 success, non-zero on refusal or error).

    Example:
        >>> main(["--repo-root", "/tmp/does-not-exist-xyz"])  # doctest: +SKIP
        2
    """
    parser = argparse.ArgumentParser(description="Seed tacit-knowledge artifacts.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--project-name", default="this project")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="overwrite existing artifacts (default: skip, never clobber)",
    )
    args = parser.parse_args(argv)

    root = Path(args.repo_root)
    if not root.is_dir():
        print(f"error: --repo-root {root} is not a directory", file=sys.stderr)
        return 2

    if is_gitignored(str(root), "tacit-knowledge.md"):
        print(
            "error: tacit-knowledge.md is gitignored; fix .gitignore first "
            "(the Log must be tracked)",
            file=sys.stderr,
        )
        return 2

    artifacts = {
        "tacit-knowledge.md": render_log_frontmatter(args.project_name),
        "docs/tacit-knowledge/topics.md": render_topics_md(fixed_baseline_topics()),
        "docs/tacit-knowledge/index.md": render_empty_index_md(),
        "docs/domain/index.md": render_domain_index_md(),
        ".gitattributes": render_gitattributes(),
    }
    written = []
    for rel, content in artifacts.items():
        dest = root / rel
        if dest.exists() and not args.overwrite:
            print(f"skip (exists): {rel}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        # .gitattributes may already exist with unrelated rules — append, don't clobber.
        if (
            rel == ".gitattributes"
            and dest.exists()
            and "tacit-knowledge.md" not in dest.read_text()
        ):
            with dest.open("a") as fh:
                fh.write("\n" + content)
        else:
            dest.write_text(content)
        written.append(rel)

    if written:
        print("Wrote: " + ", ".join(written))
        print("Review docs/tacit-knowledge/topics.md before committing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
