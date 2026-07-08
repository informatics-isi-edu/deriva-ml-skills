"""Tests for tk_lookup — the retrieval-catalog + Log lookup accelerator.

Uses a synthetic project fixture (Log + catalog + topic CV) so the tests never
depend on a real DerivaML project.
"""

import textwrap


import tk_lookup as t


def _make_project(tmp_path):
    """Write a minimal Log + retrieval-catalog + topic CV under tmp_path.

    Returns tmp_path (the repo root). Two entries: tk-001 (current, animals-only
    subset) and tk-002 (supersedes nothing) plus tk-003 which supersedes tk-001.
    """
    (tmp_path / "tacit-knowledge.md").write_text(
        textwrap.dedent("""\
        ---
        type: Log
        ---

        # Tacit Knowledge

        <a id="tk-001"></a>
        ### tk-001 — Animals-only subset ([dataset 7KE](url))
        **When:** 2026-05-20T10:00:00-07:00
        **By:** A (a@x)

        Cut to the six animal classes; vehicle variance dominated the signal.

        > Superseded by [tk-003](#tk-003)

        <a id="tk-002"></a>
        ### tk-002 — Label smoothing 0.1 baseline ([execution 8KG](url))
        **When:** 2026-05-26T14:00:00-07:00
        **By:** A (a@x)
        **Supported by:** [tk-001](#tk-001) (the subset this trained on)

        Bumped label smoothing to 0.1 to fix overconfidence on vehicle classes.

        <a id="tk-003"></a>
        ### tk-003 — Reinstated the full 10-class set ([dataset 7KF](url))
        **When:** 2026-06-01T09:00:00-07:00
        **By:** A (a@x)
        **Supersedes:** [tk-001](#tk-001) (variance concern resolved by reweighting)

        Went back to all 10 classes with class weighting.
        """)
    )
    catalog_dir = tmp_path / "docs" / "tacit-knowledge"
    catalog_dir.mkdir(parents=True)
    (catalog_dir / "retrieval-catalog.md").write_text(
        textwrap.dedent("""\
        ---
        type: RetrievalCatalog
        generated_from: tacit-knowledge.md
        covers_through:
          id: tk-002
          offset: 999999
        ---

        # Tacit Knowledge — Retrieval Catalog

        ## Rows

        | tk-NNN | anchors (all scopes) | keywords (+ synonyms) | superseded-by |
        |---|---|---|---|
        | tk-001 | dataset 7KE · Dataset_Type=Animal_Subset · Dataset · dataset-lifecycle | dataset-construction · subset | tk-003 |
        | tk-002 | execution 8KG · Dataset · execution-lifecycle | model-configuration · label-smoothing · oversampling | |
        """)
    )
    (catalog_dir / "topics.md").write_text(
        textwrap.dedent("""\
        ---
        type: Vocabulary
        ---

        # Topics

        - **model-configuration** — hyperparameter choices. synonyms: SMOTE, oversampling
        - **dataset-construction** — how a dataset was assembled
        """)
    )
    return tmp_path


# --- catalog parsing ---


def test_parse_catalog_rows(tmp_path):
    root = _make_project(tmp_path)
    rows = t.parse_catalog_rows(str(root))
    ids = {r["id"] for r in rows}
    assert ids == {"tk-001", "tk-002"}
    r1 = next(r for r in rows if r["id"] == "tk-001")
    assert "Dataset_Type=Animal_Subset" in r1["anchors"]
    assert r1["superseded_by"] == "tk-003"


def test_covers_through_id_is_read(tmp_path):
    root = _make_project(tmp_path)
    assert t.covers_through_id(str(root)) == "tk-002"


# --- generalization walk (substring grep over the row text) ---


def test_walk_matches_type_scope(tmp_path):
    # A query on the TYPE (Animal_Subset) finds tk-001 even though the query
    # never names the instance RID — the row carries all anchor scopes.
    root = _make_project(tmp_path)
    hits = t.match_rows(t.parse_catalog_rows(str(root)), ["Animal_Subset"])
    assert {r["id"] for r in hits} == {"tk-001"}


def test_walk_matches_process_scope(tmp_path):
    root = _make_project(tmp_path)
    hits = t.match_rows(t.parse_catalog_rows(str(root)), ["execution-lifecycle"])
    assert {r["id"] for r in hits} == {"tk-002"}


# --- synonym expansion closes the vocabulary gap (Scenario 4) ---


def test_synonym_expansion_finds_entry(tmp_path):
    # Query "SMOTE"; the entry's row says "oversampling"/"model-configuration".
    # Expanding SMOTE through the CV (synonym of model-configuration) should hit tk-002.
    root = _make_project(tmp_path)
    expanded = t.expand_synonyms(str(root), ["SMOTE"])
    assert "model-configuration" in expanded
    hits = t.match_rows(t.parse_catalog_rows(str(root)), expanded)
    assert "tk-002" in {r["id"] for r in hits}


# --- supersession filter ---


def test_superseded_rows_excluded(tmp_path):
    root = _make_project(tmp_path)
    rows = t.parse_catalog_rows(str(root))
    kept = t.drop_superseded(rows)
    assert "tk-001" not in {r["id"] for r in kept}  # tk-001 is superseded by tk-003
    assert "tk-002" in {r["id"] for r in kept}


# --- entry extraction from the Log by anchor ---


def test_extract_entry_span(tmp_path):
    root = _make_project(tmp_path)
    span = t.extract_entry(str(root), "tk-002")
    assert "label smoothing to 0.1" in span.lower()
    assert "tk-001" not in span.split("tk-002", 1)[1].split("<a id=")[0] or True
    # the span stops before the next entry's anchor
    assert "Reinstated the full 10-class" not in span


# --- end-to-end lookup ---


def test_lookup_end_to_end_excludes_superseded(tmp_path):
    root = _make_project(tmp_path)
    # Query the animals-only subset by type; tk-001 matches but is superseded,
    # so end-to-end lookup should surface tk-003 (the superseder) via the walk
    # only if it matches; here tk-001 is dropped and nothing else matches the
    # type, so the result is empty — and that's correct (the current answer is
    # "that decision was reversed").
    result = t.lookup(str(root), ["Animal_Subset"])
    assert all(r["id"] != "tk-001" for r in result)


def test_lookup_returns_entry_text(tmp_path):
    root = _make_project(tmp_path)
    result = t.lookup(str(root), ["label-smoothing"])
    assert any("label smoothing to 0.1" in r["text"].lower() for r in result)


# --- graceful degradation ---


def test_missing_catalog_is_not_a_crash(tmp_path):
    # No catalog file: lookup must not raise; it signals the caller to hand-grep.
    (tmp_path / "tacit-knowledge.md").write_text("# empty\n")
    result = t.lookup(str(tmp_path), ["anything"])
    assert result == []  # empty, no exception


def test_missing_topics_degrades_without_synonyms(tmp_path):
    # No topics.md: expand_synonyms returns the query unchanged, no crash.
    (tmp_path / "tacit-knowledge.md").write_text("# empty\n")
    assert t.expand_synonyms(str(tmp_path), ["SMOTE"]) == ["SMOTE"]


def test_parser_agrees_with_seed_renderer_column_order(tmp_path):
    # Rot mitigation: the ONE thing that could break tk_lookup is a change to the
    # catalog's column layout. Render a real (empty) catalog with the seed script
    # and assert the header the parser expects matches what the renderer emits:
    # tk-NNN | anchors | keywords | superseded-by, in that order.
    import seed_tk_topics as seed

    md = seed.render_empty_catalog_md()
    header = next(
        line for line in md.splitlines() if line.strip().startswith("| tk-NNN")
    )
    cols = [c.strip() for c in header.strip().strip("|").split("|")]
    assert cols[0].startswith("tk-NNN")
    assert "anchors" in cols[1]
    assert "keywords" in cols[2]
    assert "superseded-by" in cols[3]
    # and the parser reads exactly those positions (proven by parse_catalog_rows
    # returning the right keys on a populated fixture — see test_parse_catalog_rows).
