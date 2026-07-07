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
    assert "tacit-knowledge.md" in ga
    assert "docs/tacit-knowledge/topics.md" in ga
    assert "docs/tacit-knowledge/index.md" in ga
    # All three tacit-knowledge files use merge=union on their driver lines
    # (index included — it's a cache, so a union'd merge is harmless and
    # discarded by the next rebuild; merge=ours would need per-clone git
    # config nothing here registers).
    driver_lines = [
        line for line in ga.splitlines() if line and not line.strip().startswith("#")
    ]
    assert len(driver_lines) == 3
    assert all(line.strip().endswith("merge=union") for line in driver_lines)


def test_domain_index_is_concept_bundle_root():
    md = s.render_domain_index_md()
    assert "type: Index" in md  # bundle root is an Index over Concept docs


def test_is_gitignored_detects_direct_match(tmp_path):
    (tmp_path / ".gitignore").write_text("tacit-knowledge.md\n")
    assert s.is_gitignored(str(tmp_path), "tacit-knowledge.md") is True


def test_is_gitignored_false_when_absent(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    assert s.is_gitignored(str(tmp_path), "tacit-knowledge.md") is False


def test_main_appends_merge_drivers_to_existing_gitattributes(tmp_path):
    # A repo that already has a .gitattributes with unrelated rules should get
    # the tacit-knowledge merge drivers appended, even without --overwrite.
    ga = tmp_path / ".gitattributes"
    ga.write_text("*.pyc binary\n")

    rc = s.main(["--repo-root", str(tmp_path), "--project-name", "X"])

    assert rc == 0
    text = ga.read_text()
    assert "*.pyc binary" in text
    assert "merge=union" in text


def test_main_gitattributes_append_is_idempotent(tmp_path):
    ga = tmp_path / ".gitattributes"
    ga.write_text("*.pyc binary\n")

    s.main(["--repo-root", str(tmp_path), "--project-name", "X"])
    s.main(["--repo-root", str(tmp_path), "--project-name", "X"])

    text = ga.read_text()
    # The rendered driver block itself contains two merge=union lines by
    # design (Log + topic CV); assert the whole block appears once, not that
    # the substring count is 1.
    assert text.count("Tacit-knowledge merge drivers") == 1
