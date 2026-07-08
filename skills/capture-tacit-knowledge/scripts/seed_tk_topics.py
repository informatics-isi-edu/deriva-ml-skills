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
    docs/tacit-knowledge/retrieval-catalog.md, docs/domain/index.md, .gitattributes.
    Review docs/tacit-knowledge/topics.md before committing.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _yaml_quote(value: str) -> str:
    """Quote a string for safe use as a YAML scalar value.

    Plain (unquoted) YAML scalars break or change meaning when the value
    contains YAML-significant characters — a colon-space (``: ``) starts a
    mapping, a leading ``#`` is a comment, and leading/trailing whitespace is
    stripped. Project names routinely carry subtitles (``EyeAI: pilot``), so any
    value interpolated into frontmatter must be quoted.

    Wraps the value in double quotes and escapes embedded backslashes and double
    quotes, which is sufficient for the flow double-quoted YAML scalar style.

    Args:
        value: The raw string to embed as a YAML scalar.

    Returns:
        A double-quoted, escaped YAML scalar safe to place after ``key:``.

    Example:
        >>> _yaml_quote("EyeAI: pilot")
        '"EyeAI: pilot"'
        >>> _yaml_quote('a "b" c')
        '"a \\\\"b\\\\" c"'
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def fixed_baseline_topics() -> list[dict]:
    """Return the deterministic seed topic CV — the floor every project gets.

    Two axis kinds (D11): entity-anchored (the five DerivaML abstractions) and
    entity-free (process, domain, tooling, team — because not all tacit
    knowledge is about a catalog object).

    High-value terms carry a `synonyms` list so the synonym-expansion retrieval
    path (tk_lookup.expand_synonyms) is live from the first commit rather than
    dormant until a human hand-adds synonyms. Terms with no natural synonym set
    carry an empty list (no `synonyms:` clause is emitted for them).

    Returns:
        A list of {"term", "axis", "description", "synonyms"} dicts, authored to
        the term-naming-strategy discipline (one dimension, substitution test).
        `synonyms` is a (possibly empty) list of alternate query words.

    Example:
        >>> terms = fixed_baseline_topics()
        >>> "dataset-construction" in {t["term"] for t in terms}
        True
        >>> mc = next(t for t in terms if t["term"] == "model-configuration")
        >>> "hyperparameter" in mc["synonyms"]
        True
    """
    entity_anchored = [
        (
            "dataset-construction",
            "how a dataset was assembled, split, or subsampled",
            ["dataset", "dataset-assembly", "subsample", "split"],
        ),
        ("dataset-versioning", "why a dataset version was cut or pinned", []),
        (
            "feature-design",
            "why a feature exists and how it is shaped",
            ["feature", "feature-engineering"],
        ),
        (
            "model-configuration",
            "hyperparameter and architecture choices for a model",
            ["hyperparameter", "hyperparameters", "architecture", "config"],
        ),
        ("workflow-typing", "why a workflow was classified as it was", []),
        (
            "execution-provenance",
            "what an execution consumed, produced, or established",
            ["provenance", "lineage", "execution"],
        ),
    ]
    entity_free = [
        (
            "process-convention",
            "a recurring 'whenever we do X we also do Y' pattern",
            [],
        ),
        ("domain-background", "target-domain facts, confounds, and conventions", []),
        (
            "tooling-gotcha",
            "a non-obvious behavior of the toolchain or platform",
            ["gotcha", "bug", "workaround"],
        ),
        ("team-ownership", "role/process facts about who owns or decides what", []),
        (
            "dead-end",
            "an approach that was tried and abandoned, and why",
            ["tried", "abandoned", "negative-result"],
        ),
    ]
    topics: list[dict] = []
    for term, desc, syns in entity_anchored:
        topics.append(
            {
                "term": term,
                "axis": "entity-anchored",
                "description": desc,
                "synonyms": syns,
            }
        )
    for term, desc, syns in entity_free:
        topics.append(
            {
                "term": term,
                "axis": "entity-free",
                "description": desc,
                "synonyms": syns,
            }
        )
    return topics


def render_topics_md(topics: list[dict]) -> str:
    """Render the topic CV as an OKF controlled-term list.

    Each term becomes one bullet: ``- **term** — description``. When the term
    carries a non-empty `synonyms` list, a ``synonyms: a, b, c`` clause is
    appended to the SAME line, in the exact form tk_lookup.expand_synonyms
    parses (single line, comma-separated) — so synonym expansion is live on a
    freshly-seeded project. Terms with no synonyms emit no clause.

    Args:
        topics: The term dicts from fixed_baseline_topics (+ any augmentation);
            each may carry an optional `synonyms` list.

    Returns:
        Markdown with OKF frontmatter and one entry per term, grouped by axis;
        terms with synonyms carry a trailing ``synonyms:`` clause on their line.

    Example:
        >>> md = render_topics_md(fixed_baseline_topics())
        >>> md.startswith("---")
        True
        >>> "synonyms:" in md
        True
    """
    lines = [
        "---",
        "type: Vocabulary",
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
                bullet = f"- **{t['term']}** — {t['description']}"
                syns = t.get("synonyms") or []
                if syns:
                    # Keep the clause on ONE line so expand_synonyms's per-line
                    # parser (term regex + `synonyms:` search) round-trips it.
                    bullet += f". synonyms: {', '.join(syns)}"
                lines.append(bullet)
        lines.append("")
    return "\n".join(lines)


def render_empty_catalog_md() -> str:
    """Render the retrieval-catalog placeholder (no entries indexed yet).

    A conformant OKF *document* of a custom `type: RetrievalCatalog` — YAML
    frontmatter (required) + a Markdown table body (OKF favors tables). It is
    NOT the reserved `index.md` browse-convention; it is a machine lookup
    structure over the Log's entries, consumed by `tk_lookup.py` (or a hand-grep
    fallback), never loaded whole. Lean by design: only the columns retrieval
    actually greps on.

    Returns:
        Markdown OKF type:RetrievalCatalog with covers_through before the first entry.

    Example:
        >>> "type: RetrievalCatalog" in render_empty_catalog_md()
        True
    """
    return "\n".join(
        [
            "---",
            "type: RetrievalCatalog",
            "title: Tacit Knowledge — retrieval catalog",
            "description: >",
            "  Derived lookup over tacit-knowledge.md — one greppable row per entry.",
            "  Cache, not record: rebuilt whole by the capture side-effect; every row",
            "  mirrors the Log and originates no authority. Queried by tk_lookup.py",
            "  (hand-grep is the fallback); never loaded whole. Not an OKF index.md.",
            "generated_from: tacit-knowledge.md",
            "generated_at: (not yet built)",
            "generator: capture-tacit-knowledge rebuild",
            "covers_through:",
            "  id: (none)",
            "  offset: 0",
            "tags: [tacit-knowledge, retrieval-catalog, deriva-ml]",
            "---",
            "",
            "# Tacit Knowledge — Retrieval Catalog",
            "",
            "_No entries indexed yet. Rebuilt whole as a silent side-effect of capture once",
            "entries accumulate past the threshold. Queried by `tk_lookup.py`; hand-grep is",
            "the fallback. See `skills/capture-tacit-knowledge/references/index-and-retrieval.md`._",
            "",
            "## Rows",
            "",
            "**One entry per line, greppable.** Each row carries the entry's `tk-NNN`, **all",
            "anchor scopes** it applies at (instance RID *and* type *and* abstraction *and*",
            "process/skill — so the generalization walk's widened greps all hit), and its",
            "**keywords including topic-CV synonyms** (so a query using a synonym still",
            "matches). `superseded-by` mirrors the entry's tombstone edge (D2). Cost of",
            "finding candidates is O(matches), not O(entries).",
            "",
            "| tk-NNN | anchors (all scopes) | keywords (+ synonyms) | superseded-by |",
            "|---|---|---|---|",
            "",
            "_Example populated row (illustrative):_",
            "`[tk-042](../../tacit-knowledge.md#tk-042)` | execution 8KG · Dataset_Type=Animal_Subset"
            " · Dataset · execution-lifecycle | model-configuration · label-smoothing ·"
            " regularization | ",
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
            f"title: {_yaml_quote(f'Tacit Knowledge — {project_name}')}",
            "description: >",
            "  The why behind this project's DerivaML decisions — rationale, dead ends,",
            "  and cross-discipline consequences that the catalog records but does not",
            "  explain. Append-only; each entry is a dated tk-… decision record.",
            "tags: [tacit-knowledge, provenance, deriva-ml]",
            "---",
            "",
            "# Tacit Knowledge",
            "",
            "**Tacit knowledge** is knowledge gained through experience and practice —",
            "context-dependent, and hard to codify or transfer through documentation",
            "(Polanyi). Its fully embodied core (intuition, pattern-recognition earned by",
            "doing) cannot be written down; what *can* be captured is the **externalizable",
            "shell** around it — the decisions made, the alternatives weighed and rejected,",
            "and the *why* a future teammate would otherwise have to reconstruct or",
            "re-learn the hard way. This file captures that shell and points at the rest.",
            "",
            "It records the *why* behind decisions about this project's models and data —",
            "intent and reasoning the catalog cannot store. The catalog is the source of",
            "truth for *what* exists (RIDs, configs, numbers, lineage); this file is the",
            "source of truth for *why*. Don't replicate catalog-stored facts here — link to",
            "them by RID. Append-only: never rewrite an entry (supersession is an additive",
            "edge, not an edit).",
            "",
        ]
    )


def _gitattributes_driver_lines() -> list[str]:
    """Return the three tacit-knowledge merge-driver lines (no comments).

    The single source of truth for which drivers a project needs. ``main()``
    uses it to detect which lines a pre-existing ``.gitattributes`` is missing
    (appending only the shortfall), and ``render_gitattributes`` embeds it in
    the full commented block. All three are ``merge=union`` — a git built-in
    needing no per-clone config.

    Returns:
        The three ``<path> merge=union`` lines, exactly as they appear on disk.

    Example:
        >>> len(_gitattributes_driver_lines())
        3
    """
    return [
        "tacit-knowledge.md                        merge=union",
        "docs/tacit-knowledge/topics.md            merge=union",
        "docs/tacit-knowledge/retrieval-catalog.md merge=union",
    ]


def render_gitattributes() -> str:
    """Render the .gitattributes merge drivers for the tacit-knowledge files.

    Returns:
        A commented header plus the three merge-driver lines, all `merge=union`
        (Log, topic CV, and the derived index — the index is a cache, so a
        union'd merge is harmless and discarded whole by the next
        capture-triggered rebuild).

    Example:
        >>> "merge=union" in render_gitattributes()
        True
    """
    return "\n".join(
        [
            "# Tacit-knowledge merge drivers (see capture-tacit-knowledge D12).",
            "# All three union-merge. Log and topic CV union because both branches",
            "# append; the derived index unions too — it's a cache, so a union'd",
            "# merge is harmless and gets discarded whole by the next",
            "# capture-triggered rebuild. merge=union needs no extra git config",
            "# (it's a built-in driver); merge=ours would need per-clone config",
            "# nothing here registers.",
            *_gitattributes_driver_lines(),
            "",
        ]
    )


def render_domain_index_md() -> str:
    """Render docs/domain/index.md — a conformant OKF `index.md`.

    This is the one true OKF index in the layout: it enumerates its directory's
    Concept docs. Per the OKF spec, an `index.md` is the sole document type that
    carries **NO frontmatter**; its body is `# heading` sections of
    `* [title](url) - description` bullets linking the directory's files. (The
    `Concept` docs it lists DO carry frontmatter; the index itself does not.)

    Returns:
        Markdown OKF index.md — no frontmatter, a bullet-list body.

    Example:
        >>> render_domain_index_md().startswith("# Domain Background")
        True
        >>> render_domain_index_md().startswith("---")   # no frontmatter
        False
    """
    return "\n".join(
        [
            "# Domain Background",
            "",
            "Semantic, refined-in-place background about the target domain — facts,",
            "confounds, and methodological conventions a cross-disciplinary newcomer needs.",
            "One `type: Concept` doc per subject (e.g. `staining-variance.md`), refined in",
            "place over time. Distinct from the episodic tacit-knowledge Log and from",
            "`docs/design/` up-front plans. Link catalog vocabulary-term descriptions by RID",
            "rather than restating them. A tacit-knowledge Log entry may *anchor* to a subject",
            "here (Family C of the anchor taxonomy).",
            "",
            "This file is the bundle's OKF `index.md`: it lists the Concept docs below, each",
            "as `* [title](file.md) - description`, with the description taken from the",
            "Concept doc's own frontmatter. It carries no frontmatter of its own. Give each",
            "Concept doc a discriminating `tags:` line (e.g. `[domain, site-effect, imaging]`",
            "vs. `[domain, cohort, sampling-bias]`) so a human can tell siblings apart —",
            "descriptive only; the LLM reaches a Concept doc via its Family-C anchor, not tags.",
            "",
            "## Subjects",
            "",
            "_none yet — add one bullet per Concept doc, e.g._",
            "_`* [Staining variance](staining-variance.md) - stain differences across sites`_",
            "",
        ]
    )


def is_gitignored(repo_root: str, relpath: str) -> bool:
    """Check whether relpath would be ignored by git.

    Prefers ``git check-ignore``, which evaluates the *actual* ignore rules git
    applies — glob patterns (``*.md``), directory patterns (``docs/``), nested
    ``.gitignore`` files, and the global/core excludes file — so a Log excluded
    by a glob is correctly refused. When git is unavailable or ``repo_root`` is
    not a git work tree, falls back to a conservative exact-line match against a
    top-level ``.gitignore`` (which cannot see glob/directory rules); the caller
    is still protected against the common literal-path case.

    Args:
        repo_root: Absolute path to the repository root.
        relpath: Path relative to repo_root to test.

    Returns:
        True if the path is ignored (by git, or by a literal .gitignore line in
        the fallback path).

    Example:
        >>> is_gitignored("/nonexistent", "x")  # not a dir / no rules -> False
        False
    """
    git = shutil.which("git")
    if git is not None:
        try:
            result = subprocess.run(  # noqa: S603 - fixed argv, no shell
                [git, "check-ignore", "-q", "--", relpath],
                cwd=repo_root,
                capture_output=True,
            )
        except OSError:
            result = None
        # exit 0 = ignored, 1 = not ignored, 128 = not a git repo / other error.
        if result is not None and result.returncode in (0, 1):
            return result.returncode == 0
        # returncode 128 (or the OSError above) falls through to the line-match.

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

    artifacts = {
        "tacit-knowledge.md": render_log_frontmatter(args.project_name),
        "docs/tacit-knowledge/topics.md": render_topics_md(fixed_baseline_topics()),
        "docs/tacit-knowledge/retrieval-catalog.md": render_empty_catalog_md(),
        "docs/domain/index.md": render_domain_index_md(),
    }

    # Every generated artifact must be trackable, not just the Log — an index or
    # CV excluded by a `docs/` or `*.md` glob would be written and silently
    # ignored. Refuse if git would ignore any of them.
    for rel in artifacts:
        if is_gitignored(str(root), rel):
            print(
                f"error: {rel} is gitignored; fix .gitignore first "
                "(the tacit-knowledge artifacts must be tracked)",
                file=sys.stderr,
            )
            return 2

    written = []

    # .gitattributes is handled first and separately: a pre-existing file must
    # get whichever tacit-knowledge merge-driver lines it is MISSING appended,
    # even without --overwrite. It must NOT go through the generic skip-if-exists
    # guard below (which would short-circuit the append), and a substring check
    # on one line would wrongly treat a partially-configured file as complete.
    gitattributes_content = render_gitattributes()
    ga_dest = root / ".gitattributes"
    if ga_dest.exists():
        existing = ga_dest.read_text()
        missing = [
            line for line in _gitattributes_driver_lines() if line not in existing
        ]
        if missing:
            with ga_dest.open("a") as fh:
                fh.write("\n" + "\n".join(missing) + "\n")
            print(f"append (merge drivers): .gitattributes ({len(missing)} missing)")
            written.append(".gitattributes")
        else:
            print("skip (already has drivers): .gitattributes")
    else:
        ga_dest.parent.mkdir(parents=True, exist_ok=True)
        ga_dest.write_text(gitattributes_content)
        written.append(".gitattributes")

    for rel, content in artifacts.items():
        dest = root / rel
        if dest.exists() and not args.overwrite:
            print(f"skip (exists): {rel}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        written.append(rel)

    if written:
        print("Wrote: " + ", ".join(written))
        print("Review docs/tacit-knowledge/topics.md before committing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
