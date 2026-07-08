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


def test_match_rows_short_needle_requires_word_boundary():
    # A short (<3 char) needle like "ml" must not match as a bare substring
    # inside an unrelated token ("yaml-config") — that floods results. It
    # must still match as a standalone word or inside a hyphenated token
    # boundary like "ml-pipeline".
    rows_no_match = [{"id": "a", "raw": "row about yaml-config only"}]
    assert t.match_rows(rows_no_match, ["ml"]) == []

    rows_hyphen = [{"id": "b", "raw": "uses the ml-pipeline tool"}]
    assert {r["id"] for r in t.match_rows(rows_hyphen, ["ml"])} == {"b"}

    rows_standalone = [{"id": "c", "raw": "trained via ml this quarter"}]
    assert {r["id"] for r in t.match_rows(rows_standalone, ["ml"])} == {"c"}


def test_match_rows_escapes_regex_metacharacters_in_needle():
    # Needles containing regex metacharacters (anchors like "Dataset_Type=X"
    # or keyword separators like "·") must be treated literally, not as
    # regex syntax, for both the short- and long-needle paths.
    rows = [{"id": "a", "raw": "anchors: Dataset_Type=X · other"}]
    assert {r["id"] for r in t.match_rows(rows, ["Dataset_Type=X"])} == {"a"}
    assert {r["id"] for r in t.match_rows(rows, ["·"])} == {"a"}


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


def test_drop_superseded_treats_none_placeholder_as_current():
    # The seed template's illustrative row used to render the literal "(none)"
    # for an empty superseded-by cell; "(none)".strip() is truthy, so the old
    # implementation wrongly dropped current entries. A cell only means
    # "superseded" when it actually names a tk-... id (bare or link-wrapped).
    rows = [
        {"id": "a", "superseded_by": "(none)"},
        {"id": "b", "superseded_by": ""},
        {"id": "c", "superseded_by": "tk-9"},
        {"id": "d", "superseded_by": "[tk-9](#tk-9)"},
    ]
    kept = {r["id"] for r in t.drop_superseded(rows)}
    assert kept == {"a", "b"}


# --- entry extraction from the Log by anchor ---


def test_extract_entry_span(tmp_path):
    root = _make_project(tmp_path)
    span = t.extract_entry(str(root), "tk-002")
    assert "label smoothing to 0.1" in span.lower()
    # the span starts at tk-002, not earlier: it must not bleed backward into
    # tk-001's body text (tk-002 legitimately links to tk-001 via a
    # "Supported by" reference, so we assert on tk-001's unique BODY text,
    # not on the substring "tk-001" itself).
    assert "vehicle variance dominated" not in span
    # the span stops before the next entry's anchor
    assert "Reinstated the full 10-class" not in span


# --- tombstone detection ---


def test_entry_is_superseded_is_case_insensitive():
    # A hand-edited tombstone with lowercase "superseded by" must still be
    # recognized (the canonical form capitalizes "Superseded").
    assert t._entry_is_superseded("> superseded by [tk-9](#tk-9)") is True


# --- end-to-end lookup ---


def test_lookup_end_to_end_excludes_superseded(tmp_path):
    root = _make_project(tmp_path)
    # Negative control: query the animals-only subset by type; tk-001 matches
    # but is superseded, so end-to-end lookup should surface tk-003 (the
    # superseder) via the walk only if it matches; here tk-001 is dropped and
    # nothing else matches the type, so the result is empty — and that's
    # correct (the current answer is "that decision was reversed").
    result_superseded = t.lookup(str(root), ["Animal_Subset"])
    assert result_superseded == []
    assert all(r["id"] != "tk-001" for r in result_superseded)

    # Positive control (same test, so a broken matcher can't hide behind an
    # empty result on both queries): a query that SHOULD match a current
    # entry must be non-empty and contain tk-002. Without this, an
    # accidentally-broken matcher that matches nothing would make the
    # negative-control assertion above pass vacuously.
    result_current = t.lookup(str(root), ["label-smoothing"])
    assert result_current != []
    assert any(r["id"] == "tk-002" for r in result_current)


def test_lookup_returns_entry_text(tmp_path):
    root = _make_project(tmp_path)
    result = t.lookup(str(root), ["label-smoothing"])
    assert any("label smoothing to 0.1" in r["text"].lower() for r in result)


def test_lookup_warm_tail_excludes_catalog_superseded_without_tombstone(tmp_path):
    # A warm-tail entry (past covers_through) can be superseded per the
    # catalog's superseded-by column even though its Log span carries no
    # tombstone yet (e.g. the catalog was rebuilt after a later entry
    # superseded it, but the tombstone edit to the earlier span is still
    # pending/manual). lookup() must still exclude it — checking the
    # tombstone alone is not enough.
    root = _make_project(tmp_path)
    log = root / "tacit-knowledge.md"
    text = log.read_text()
    # Add tk-004: a warm-tail entry (after covers_through: tk-002) with a
    # unique keyword and NO tombstone in its span.
    text += textwrap.dedent("""
        <a id="tk-004"></a>
        ### tk-004 — Switched augmentation pipeline ([execution 9ZZ](url))
        **When:** 2026-06-05T09:00:00-07:00
        **By:** A (a@x)

        Tried a new augmentation-pipeline-widget approach for preprocessing.
        """)
    log.write_text(text)
    # The catalog says tk-004 is superseded by tk-009 (no such entry needs to
    # exist for this test — only the catalog-consultation behavior matters).
    catalog = root / "docs" / "tacit-knowledge" / "retrieval-catalog.md"
    catalog_text = catalog.read_text()
    catalog_text += (
        "| tk-004 | execution 9ZZ | augmentation-pipeline-widget | tk-009 |\n"
    )
    catalog.write_text(catalog_text)

    result = t.lookup(str(root), ["augmentation-pipeline-widget"])
    assert all(r["id"] != "tk-004" for r in result)


def test_lookup_catalog_hit_excluded_by_tombstone_when_column_stale(tmp_path):
    # Post-supersession, pre-rebuild: the catalog row's superseded-by cell is
    # still empty (the catalog hasn't been rebuilt yet — the 10-entry throttle
    # hasn't fired), but the Log span for that same entry already carries a
    # `> Superseded by ...` tombstone (tombstones are written at capture time,
    # independent of the catalog rebuild cadence). A catalog HIT (not a
    # warm-tail entry) must still be excluded — the Log tombstone is the
    # authoritative backstop over the whole result set, regardless of which
    # path (catalog vs. warm tail) surfaced the id.
    root = _make_project(tmp_path)

    # tk-002 is a normal catalog entry (covered by covers_through) with no
    # tombstone. Add one directly to its Log span to simulate a supersession
    # that hasn't been reflected in the catalog's superseded-by column yet.
    log = root / "tacit-knowledge.md"
    text = log.read_text()
    text = text.replace(
        "Bumped label smoothing to 0.1 to fix overconfidence on vehicle classes.\n",
        "Bumped label smoothing to 0.1 to fix overconfidence on vehicle classes.\n"
        "\n> Superseded by [tk-999](#tk-999)\n",
    )
    log.write_text(text)

    # Catalog row for tk-002 is untouched: superseded-by cell is still empty.
    catalog = root / "docs" / "tacit-knowledge" / "retrieval-catalog.md"
    assert "| tk-002 |" in catalog.read_text()
    rows = t.parse_catalog_rows(str(root))
    r2 = next(r for r in rows if r["id"] == "tk-002")
    assert r2["superseded_by"] == ""  # stale: catalog doesn't know yet

    # tk-002 would otherwise be a catalog HIT for "label-smoothing" (see
    # test_lookup_returns_entry_text) — but the Log tombstone must exclude it.
    result = t.lookup(str(root), ["label-smoothing"])
    assert all(r["id"] != "tk-002" for r in result)


def test_lookup_warm_tail_matching_is_word_boundary_bounded(tmp_path):
    # The warm-tail path must use the same bounded-match rule as match_rows
    # (_needle_matches), not a raw substring test. A short query term ("ml")
    # must not match a tail entry purely because its span contains an
    # unrelated token that happens to embed it ("yaml-config"). It SHOULD
    # match a tail entry via a term that legitimately word-boundary-matches
    # ("pipeline").
    root = _make_project(tmp_path)
    log = root / "tacit-knowledge.md"
    text = log.read_text()
    # tk-004: a warm-tail entry (past covers_through: tk-002), NOT in the
    # catalog. Its span contains "yaml-config" (should NOT match "ml") and
    # "pipeline" (should match on its own term as a word-boundary control).
    text += textwrap.dedent("""
        <a id="tk-004"></a>
        ### tk-004 — Switched to a yaml-config pipeline ([execution 9ZZ](url))
        **When:** 2026-06-05T09:00:00-07:00
        **By:** A (a@x)

        Moved preprocessing to a yaml-config driven pipeline.
        """)
    log.write_text(text)

    # "ml" must NOT match tk-004 via the incidental substring inside
    # "yaml-config" — that's the bug: raw `"ml" in hay` would match here.
    result_ml = t.lookup(str(root), ["ml"])
    assert all(r["id"] != "tk-004" for r in result_ml)

    # A real word-boundary match on the same tail entry must still work.
    result_pipeline = t.lookup(str(root), ["pipeline"])
    assert any(r["id"] == "tk-004" for r in result_pipeline)


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
