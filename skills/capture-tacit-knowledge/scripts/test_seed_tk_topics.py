"""Tests for seed_tk_topics — pure render functions and path safety."""

import seed_tk_topics as s


def test_fixed_baseline_has_both_axis_kinds():
    topics = s.fixed_baseline_topics()
    kinds = {t["axis"] for t in topics}
    assert "entity-anchored" in kinds
    assert "entity-free" in kinds


def test_fixed_baseline_covers_five_abstractions():
    terms = {t["term"] for t in s.fixed_baseline_topics()}
    for abstraction in ("dataset", "feature", "model", "workflow", "execution"):
        assert any(abstraction in t for t in terms), abstraction


def test_fixed_baseline_covers_entity_free_axes():
    # process, domain, tooling, team — the entity-free axes (D11)
    terms = " ".join(t["term"] for t in s.fixed_baseline_topics())
    for axis_hint in ("process", "domain", "tooling", "team"):
        assert axis_hint in terms, axis_hint


def test_topics_md_is_okf_controlled_term_list():
    md = s.render_topics_md(s.fixed_baseline_topics())
    assert md.startswith("---")  # frontmatter
    assert "type:" in md
    assert "# " in md  # a heading


def test_index_md_declares_derived_and_covers_through():
    md = s.render_empty_index_md()
    assert "type: Index" in md
    assert "generated_from: tacit-knowledge.md" in md
    assert "covers_through" in md


def test_log_frontmatter_is_okf_log():
    fm = s.render_log_frontmatter("MyProject")
    assert "type: Log" in fm
    assert "MyProject" in fm
    assert "resource:" not in fm  # intentionally omitted for a journal


def test_gitattributes_has_three_drivers():
    ga = s.render_gitattributes()
    assert "tacit-knowledge.md" in ga and "merge=union" in ga
    assert "docs/tacit-knowledge/topics.md" in ga
    assert "docs/tacit-knowledge/index.md" in ga and "merge=ours" in ga


def test_domain_index_is_concept_bundle_root():
    md = s.render_domain_index_md()
    assert (
        "type: Concept" in md or "type: Index" in md
    )  # bundle root is an Index over Concepts


def test_is_gitignored_detects_direct_match(tmp_path):
    (tmp_path / ".gitignore").write_text("tacit-knowledge.md\n")
    assert s.is_gitignored(str(tmp_path), "tacit-knowledge.md") is True


def test_is_gitignored_false_when_absent(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    assert s.is_gitignored(str(tmp_path), "tacit-knowledge.md") is False
