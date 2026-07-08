"""Tests for seed_tk_topics — pure render functions and path safety."""

import shutil
import subprocess

import pytest

import seed_tk_topics as s


def _git_init(path):
    """Initialise a git repo at path so git check-ignore has a work tree.

    Skips the calling test if git is not installed. Configures a throwaway
    identity so the repo is usable without touching the caller's global config.
    """
    git = shutil.which("git")
    if git is None:  # pragma: no cover - environment without git
        pytest.skip("git not available")
    subprocess.run([git, "init", "-q", str(path)], check=True)
    subprocess.run(
        [git, "-C", str(path), "config", "user.email", "t@t.test"], check=True
    )
    subprocess.run([git, "-C", str(path), "config", "user.name", "t"], check=True)


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
    assert "type: Vocabulary" in md  # richer type: the topic CV self-identifies
    assert "# " in md  # a heading


def test_index_md_declares_derived_and_covers_through():
    md = s.render_empty_index_md()
    assert "type: RetrievalIndex" in md  # richer type: not the generic Index
    assert "generated_from: tacit-knowledge.md" in md
    assert "covers_through" in md


def test_index_md_tags_match_type_not_stale_index():
    # The tags must not still say the generic "index" (a rename leftover).
    md = s.render_empty_index_md()
    assert "retrieval-index" in md  # the corrected tag
    assert "tags: [tacit-knowledge, index" not in md  # the stale tag is gone


def test_index_md_has_full_okf_index_anatomy():
    # Full OKF-index parity: bundle metadata, inventory, relationships,
    # navigation, and search/discovery elements are all present as sections.
    md = s.render_empty_index_md()
    # bundle metadata
    assert "version:" in md
    assert "owners:" in md
    # navigation
    assert "## Summary" in md
    assert "## Start here" in md
    # inventory: categories by anchor family
    assert "## Inventory by anchor family" in md
    assert "Family A" in md and "Family B" in md and "Family C" in md
    # rows carry a click-through link, relationships, and aliases
    assert "tk-NNN (link)" in md
    assert "relationships" in md
    assert "aliases" in md
    # the illustrative row links into the Log by anchor
    assert "../../tacit-knowledge.md#tk-042" in md


def test_index_rows_are_descriptive_not_stateful():
    # D4 guardrail: the index mirrors the entries, it never originates authority.
    md = s.render_empty_index_md()
    assert "originates no authority" in md
    assert "mirrors the entry" in md or "mirrors the Log" in md


def test_log_frontmatter_is_okf_log():
    fm = s.render_log_frontmatter("MyProject")
    assert "type: Log" in fm
    assert "MyProject" in fm
    assert "resource:" not in fm  # intentionally omitted for a journal


def test_gitattributes_has_three_drivers():
    ga = s.render_gitattributes()
    assert "tacit-knowledge.md" in ga
    assert "docs/tacit-knowledge/topics.md" in ga
    assert "docs/tacit-knowledge/retrieval-index.md" in ga
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
    assert "type: ConceptBundle" in md  # richer type: bundle root over Concept docs


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


# --- codex P2 regression tests ---


def test_is_gitignored_detects_glob_rule(tmp_path):
    # A glob like *.md hides the Log; git check-ignore must catch it even
    # though no literal `tacit-knowledge.md` line exists (line-match would miss).
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text("*.md\n")
    assert s.is_gitignored(str(tmp_path), "tacit-knowledge.md") is True


def test_is_gitignored_detects_directory_rule(tmp_path):
    # A `docs/` directory rule hides the index/CV/domain artifacts.
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text("docs/\n")
    assert s.is_gitignored(str(tmp_path), "docs/tacit-knowledge/retrieval-index.md") is True


def test_is_gitignored_false_for_tracked_path(tmp_path):
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    assert s.is_gitignored(str(tmp_path), "tacit-knowledge.md") is False


def test_main_refuses_when_an_artifact_is_glob_ignored(tmp_path):
    # If docs/ is ignored, the index/CV/domain artifacts can't be tracked —
    # the scaffold must refuse (exit 2), not write files git will ignore.
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text("docs/\n")

    rc = s.main(["--repo-root", str(tmp_path), "--project-name", "X"])

    assert rc == 2
    # Nothing under docs/ should have been written.
    assert not (tmp_path / "docs").exists()


def test_main_appends_only_missing_driver_lines(tmp_path):
    # A .gitattributes that has the Log driver but is MISSING the two docs/
    # drivers must still get the missing lines appended (substring-on-one-line
    # would wrongly treat it as complete and skip). Use the exact Log driver
    # line the script emits so the "present" half matches.
    ga = tmp_path / ".gitattributes"
    ga.write_text("tacit-knowledge.md                      merge=union\n")

    rc = s.main(["--repo-root", str(tmp_path), "--project-name", "X"])

    assert rc == 0
    text = ga.read_text()
    assert "docs/tacit-knowledge/topics.md          merge=union" in text
    assert "docs/tacit-knowledge/retrieval-index.md merge=union" in text


def test_log_frontmatter_quotes_yaml_significant_title(tmp_path):
    # A project name with a colon-space would break plain-scalar YAML; the
    # title must be quoted so the frontmatter stays valid.
    fm = s.render_log_frontmatter("EyeAI: pilot")
    title_line = next(ln for ln in fm.splitlines() if ln.startswith("title:"))
    assert title_line == 'title: "Tacit Knowledge — EyeAI: pilot"'


def test_log_frontmatter_yaml_parses_with_significant_name():
    # If PyYAML is available, the emitted frontmatter must parse cleanly with
    # a YAML-significant project name. Skip if PyYAML isn't installed.
    yaml = pytest.importorskip("yaml")
    fm = s.render_log_frontmatter("EyeAI: pilot #1")
    block = fm.split("---")[1]  # the frontmatter between the first two `---`
    doc = yaml.safe_load(block)
    assert doc["type"] == "Log"
    assert doc["title"] == "Tacit Knowledge — EyeAI: pilot #1"
