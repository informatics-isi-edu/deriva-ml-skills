"""Retrieval accelerator for the tacit-knowledge system.

The PRIMARY retrieval path: given query terms (an anchor RID/type, a keyword, a
skill name), find the relevant tacit-knowledge entries deterministically —
the generalization walk, topic-CV synonym expansion, the supersession filter,
the warm-tail merge, and entry extraction from the Log — all in one place.

This is an *optional accelerator*: if it is unavailable (not installed, wrong
env) or a project's files are missing, the caller falls back to the documented
hand-grep procedure (see references/index-and-retrieval.md). Correctness never
hard-depends on this script; it is faster, deterministic, and does synonym
expansion the hand path can only approximate. The design intentionally lives in
code (not LLM-executed prose) because the retrieval procedure is only getting
more sophisticated (evolving keywords, semantic lookup) and code runs it
identically where prose drifts.

Files it reads (all relative to a project root):
    tacit-knowledge.md                       the append-only Log (type: Log)
    docs/tacit-knowledge/retrieval-catalog.md the derived catalog (type: RetrievalCatalog)
    docs/tacit-knowledge/topics.md            the topic CV (type: Vocabulary), for synonyms

Example:
    $ uv run python tk_lookup.py --repo-root . Animal_Subset label-smoothing
    tk-002 — Label smoothing 0.1 baseline
    <the entry text…>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_LOG = "tacit-knowledge.md"
_CATALOG = "docs/tacit-knowledge/retrieval-catalog.md"
_TOPICS = "docs/tacit-knowledge/topics.md"

_ANCHOR_RE = re.compile(r'<a id="(tk-[^"]+)">')


def _read(root: str, relpath: str) -> str | None:
    """Read a project file, returning None if it is absent.

    Graceful degradation: a missing file is a normal signal (fall back to
    hand-grep / skip synonyms), never an exception.

    Args:
        root: The project root directory.
        relpath: Path relative to root.

    Returns:
        The file text, or None if the file does not exist / cannot be read.

    Example:
        >>> _read("/nonexistent", "x.md") is None
        True
    """
    path = Path(root) / relpath
    try:
        return path.read_text()
    except OSError:
        return None


def covers_through_id(root: str) -> str | None:
    """Return the catalog's `covers_through.id`, or None if unavailable.

    Args:
        root: The project root directory.

    Returns:
        The last-indexed `tk-…` id, or None if the catalog / field is absent.

    Example:
        >>> covers_through_id("/nonexistent") is None
        True
    """
    text = _read(root, _CATALOG)
    if text is None:
        return None
    match = re.search(r"covers_through:\s*\n\s*id:\s*(\S+)", text)
    if not match:
        return None
    value = match.group(1)
    return None if value in ("(none)", "none") else value


def parse_catalog_rows(root: str) -> list[dict]:
    """Parse the retrieval-catalog's Rows table into row dicts.

    Reads the pipe-table under the `## Rows` heading. Each row yields
    {"id", "anchors", "keywords", "superseded_by", "raw"}. Header, separator,
    and non-`tk-` lines are skipped. Missing catalog → empty list (degrade).

    Args:
        root: The project root directory.

    Returns:
        A list of row dicts (empty if the catalog is absent or has no rows).

    Example:
        >>> parse_catalog_rows("/nonexistent")
        []
    """
    text = _read(root, _CATALOG)
    if text is None:
        return []
    rows: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        # A real row id is tk- followed by (optional branch +) digits. This skips
        # the header token `tk-NNN` and any illustrative/link-wrapped placeholder.
        first = cells[0].strip("`").strip() if cells else ""
        first = re.sub(r"^\[|\]\(.*$", "", first)  # unwrap [tk-042](...) → tk-042
        if not re.fullmatch(r"tk-(?:[a-z0-9-]+-)?\d+", first):
            continue  # header / separator / placeholder / non-row
        cells[0] = first
        # columns: tk-NNN | anchors | keywords | superseded-by
        row = {
            "id": cells[0],
            "anchors": cells[1] if len(cells) > 1 else "",
            "keywords": cells[2] if len(cells) > 2 else "",
            "superseded_by": cells[3] if len(cells) > 3 else "",
            "raw": stripped,
        }
        rows.append(row)
    return rows


def expand_synonyms(root: str, terms: list[str]) -> list[str]:
    """Expand query terms through the topic-CV synonyms.

    For each term, if the term appears as a CV term OR among a CV term's
    `synonyms:`, add that CV term (and its synonyms) to the result. This is the
    fix for the substring/vocabulary gap: a query using one word ("SMOTE")
    reaches an entry classified under another ("model-configuration"). Missing
    topics.md → the terms are returned unchanged (degrade, no synonyms).

    Args:
        root: The project root directory.
        terms: The raw query terms.

    Returns:
        The original terms plus any CV terms/synonyms they map to (deduped,
        order-stable).

    Example:
        >>> expand_synonyms("/nonexistent", ["SMOTE"])
        ['SMOTE']
    """
    text = _read(root, _TOPICS)
    result = list(terms)
    if text is None:
        return result
    # Parse CV lines of the form:  - **term** — desc. synonyms: a, b, c
    cv: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        m = re.match(r"\s*-\s+\*\*(?P<term>[^*]+)\*\*", line)
        if not m:
            continue
        term = m.group("term").strip()
        syn_match = re.search(r"synonyms?:\s*(.+)$", line, re.IGNORECASE)
        syns = (
            [s.strip() for s in re.split(r"[,;·]", syn_match.group(1)) if s.strip()]
            if syn_match
            else []
        )
        cv.append((term, syns))

    lowered = {x.lower() for x in terms}
    for term, syns in cv:
        family = [term, *syns]
        if any(f.lower() in lowered for f in family):
            for f in family:
                if f not in result:
                    result.append(f)
    return result


def _needle_matches(needle: str, hay: str) -> bool:
    """True if `needle` matches `hay`, word-bounded for short needles.

    An unbounded substring match lets a 1-2 char term ("ml", "cv") match
    inside unrelated tokens (e.g. "ml" inside "yaml-config"). Needles shorter
    than 3 chars require a word-boundary match instead (bounded by
    non-alphanumeric on each side, so hyphenated tokens like "ml-pipeline"
    still match); needles of length >= 3 keep the plain substring match. The
    needle is regex-escaped either way so metacharacter-bearing text (e.g.
    "Dataset_Type=X", "·") is matched literally.

    Args:
        needle: The lowercased query term.
        hay: The lowercased haystack text.

    Returns:
        True if the needle is considered a match against the haystack.

    Example:
        >>> _needle_matches("ml", "yaml-config")
        False
        >>> _needle_matches("ml", "ml-pipeline")
        True
    """
    escaped = re.escape(needle)
    if len(needle) < 3:
        return bool(re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", hay))
    return needle in hay


def match_rows(rows: list[dict], terms: list[str]) -> list[dict]:
    """Return rows whose text contains any query term (case-insensitive substring).

    This is the generalization walk in code: because each row carries ALL anchor
    scopes (instance, type, abstraction, process) plus keywords+synonyms as
    literal text, a substring match on a widened term (a type, a skill) hits the
    right rows without the query needing the exact instance handle. Short (<3
    char) needles are word-boundary matched to avoid flooding on incidental
    substrings (see _needle_matches).

    Args:
        rows: Catalog rows from parse_catalog_rows.
        terms: Query terms (already synonym-expanded, ideally).

    Returns:
        The matching rows, order preserved, deduped by id.

    Example:
        >>> match_rows([{"id": "tk-1", "raw": "Dataset"}], ["dataset"])
        [{'id': 'tk-1', 'raw': 'Dataset'}]
    """
    needles = [x.lower() for x in terms if x.strip()]
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        hay = row["raw"].lower()
        if any(_needle_matches(n, hay) for n in needles) and row["id"] not in seen:
            seen.add(row["id"])
            out.append(row)
    return out


def _names_superseder(cell: str) -> bool:
    """True if a `superseded_by` cell actually names a `tk-…` id.

    An empty cell or the seed template's `(none)` placeholder are both
    "not superseded"; only a cell that names a tk- id (bare, e.g. `tk-003`,
    or link-wrapped, e.g. `[tk-003](#tk-003)`) counts as a real superseder.

    Args:
        cell: The raw `superseded_by` table-cell text.

    Returns:
        True if the cell names a tk- id.

    Example:
        >>> _names_superseder("(none)")
        False
        >>> _names_superseder("[tk-9](#tk-9)")
        True
    """
    return bool(re.search(r"tk-", cell))


def drop_superseded(rows: list[dict]) -> list[dict]:
    """Drop rows whose `superseded_by` names a real tk- id (D2 exclusion).

    An empty cell or the `(none)` placeholder both mean "still current" and
    are kept; only a cell that actually names a `tk-…` id causes a drop.

    Args:
        rows: Catalog rows.

    Returns:
        Only the rows that are still current.

    Example:
        >>> drop_superseded([{"id": "a", "superseded_by": "tk-b"}])
        []
        >>> drop_superseded([{"id": "a", "superseded_by": "(none)"}])
        [{'id': 'a', 'superseded_by': '(none)'}]
    """
    return [r for r in rows if not _names_superseder(r.get("superseded_by", ""))]


def extract_entry(root: str, tk_id: str) -> str | None:
    """Extract one entry's Markdown span from the Log by its `<a id>` anchor.

    Reads from the entry's `<a id="tk_id">` marker to the next `<a id="tk-…">`
    marker (or EOF). Missing Log / id → None (degrade).

    Args:
        root: The project root directory.
        tk_id: The entry id, e.g. "tk-042".

    Returns:
        The entry span (including its anchor line), or None if not found.

    Example:
        >>> extract_entry("/nonexistent", "tk-001") is None
        True
    """
    text = _read(root, _LOG)
    if text is None:
        return None
    anchor = f'<a id="{tk_id}">'
    start = text.find(anchor)
    if start == -1:
        return None
    rest = text[start + len(anchor) :]
    nxt = _ANCHOR_RE.search(rest)
    end = start + len(anchor) + (nxt.start() if nxt else len(rest))
    return text[start:end].strip()


def _warm_tail_ids(root: str) -> list[str]:
    """Return the ids of Log entries not yet in the catalog (the warm tail).

    The tail is every `<a id>` after `covers_through.id`. Uses id membership (the
    correctness definition), not the byte offset, since the script re-reads the
    whole Log anyway (it is small). Missing Log → empty.

    Args:
        root: The project root directory.

    Returns:
        The tail entry ids, in Log order.

    Example:
        >>> _warm_tail_ids("/nonexistent")
        []
    """
    text = _read(root, _LOG)
    if text is None:
        return []
    all_ids = _ANCHOR_RE.findall(text)
    boundary = covers_through_id(root)
    if boundary is None or boundary not in all_ids:
        # No/unknown boundary: treat everything as tail-safe (match handles dedup).
        return all_ids
    return all_ids[all_ids.index(boundary) + 1 :]


def _entry_is_superseded(span: str) -> bool:
    """True if an entry span carries a tombstone (`> Superseded by …`).

    Case-insensitive so a lowercased hand-edited tombstone (e.g.
    ``> superseded by [tk-9](#tk-9)``) is still recognized.
    """
    return bool(re.search(r">\s*Superseded by\s+\[tk-", span, re.IGNORECASE))


def lookup(root: str, terms: list[str]) -> list[dict]:
    """Full retrieval: catalog match + warm tail + synonym expansion + filter.

    Steps:
      1. Expand the query terms through the topic CV synonyms.
      2. Match catalog rows (the generalization walk) → candidate ids.
      3. Add warm-tail entries (past covers_through) matching any term.
      4. Drop superseded candidates (catalog column + tail tombstone).
      5. Extract each surviving entry's text from the Log.

    Args:
        root: The project root directory.
        terms: Raw query terms.

    Returns:
        A list of {"id", "title", "text"} dicts for the surviving entries. Empty
        list on missing files or no match (the caller then hand-greps).

    Example:
        >>> lookup("/nonexistent", ["x"])
        []
    """
    expanded = expand_synonyms(root, terms)

    # 2. catalog matches, minus superseded
    catalog_rows = parse_catalog_rows(root)
    catalog_hits = drop_superseded(match_rows(catalog_rows, expanded))
    ids = [r["id"] for r in catalog_hits]

    # ids the catalog already knows are superseded (real tk- superseder, not
    # empty/"(none)") — consulted below so a warm-tail entry whose Log span
    # has no tombstone yet, but whose catalog row already names a superseder,
    # is still excluded.
    superseded_ids = {
        r["id"] for r in catalog_rows if _names_superseder(r.get("superseded_by", ""))
    }

    # 3. warm tail: entries past covers_through that match any term
    for tk_id in _warm_tail_ids(root):
        if tk_id in ids:
            continue
        if tk_id in superseded_ids:
            continue
        span = extract_entry(root, tk_id)
        if span is None:
            continue
        hay = span.lower()
        if any(x.lower() in hay for x in expanded if x.strip()):
            # 4b. tail supersession filter (read the tombstone directly)
            if not _entry_is_superseded(span):
                ids.append(tk_id)

    results: list[dict] = []
    for tk_id in ids:
        span = extract_entry(root, tk_id)
        if span is None:
            continue
        title = _title_of(span)
        results.append({"id": tk_id, "title": title, "text": span})
    return results


def _title_of(span: str) -> str:
    """Pull the short title from an entry span's `### tk-NNN — <title>` line."""
    m = re.search(r"^###\s+tk-\S+\s+—\s+(.+?)(?:\s+\(|$)", span, re.MULTILINE)
    return m.group(1).strip() if m else ""


def main(argv: list[str] | None = None) -> int:
    """CLI: look up tacit-knowledge entries by query terms.

    Args:
        argv: CLI args (defaults to sys.argv[1:]).

    Returns:
        0 on success (including "no matches" — that is a valid answer), 2 on a
        usage / missing-root error.

    Example:
        >>> main(["--repo-root", "/nonexistent", "x"])
        2
    """
    parser = argparse.ArgumentParser(description="Look up tacit-knowledge entries.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("terms", nargs="+", help="anchor / keyword / skill terms")
    parser.add_argument(
        "--ids-only", action="store_true", help="print just ids + titles"
    )
    args = parser.parse_args(argv)

    root = Path(args.repo_root)
    if not root.is_dir():
        print(f"error: --repo-root {root} is not a directory", file=sys.stderr)
        return 2

    results = lookup(str(root), args.terms)
    if not results:
        print("(no matching tacit-knowledge entries — fall back to hand-grep)")
        return 0
    for r in results:
        print(f"{r['id']} — {r['title']}")
        if not args.ids_only:
            print(r["text"])
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
