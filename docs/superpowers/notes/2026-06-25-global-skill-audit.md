# Global Skill Audit — 2026-06-25

A whole-set evaluation of all 31 skills against the skill-creator quality rubric
(consistency, currency, compactness via progressive disclosure). Run as a
parallel fan-out (4 auditors over slices) + cross-cutting checks. This note is
the triaged result, to be executed as a follow-up after PR #88 merges (branch
off the updated `main`).

## Headline

The skill set is in good shape. Cross-cutting structure is sound: **no broken
`/deriva-ml:` cross-references, the Specify→Build→Validate arc vocabulary is
coherent (6 surfaces), all design-doc paths correctly migrated to
`docs/design/<entity>/`, no hardcoded stale skill counts.** The findings are a
handful of localized defects + a large set of optional compaction
opportunities.

## Verified FALSE alarms (do not re-chase)

Checked against live deriva-ml / deriva-ml-mcp-plugin source:

- `work-with-assets` execution status `Stopped → Pending_Upload → Uploaded` — **current** (enums.py:69, canonical 7-state lifecycle). Not stale.
- `deriva_ml_create_vocabulary` (api-naming, create-feature) — **real MCP tool** (deriva-ml-mcp-plugin tools/vocabulary.py). Not stale.
- `select_newest` / `select_latest` (ml-data-engineering) — **both real** (`select_latest` is an alias for `select_newest`, feature.py:20). Using both is a *style* inconsistency, not a bug.

## Group A — Real defects to fix (small, high-value)

| # | Skill | Severity | Issue | Fix |
|---|---|---|---|---|
| A1 | `create-web-app` | **High** | `list_apps()` / `start_app()` shown under a "Via MCP Tools" heading — they are **HTTP REST endpoints** of the app server, not MCP tools. A reader will try to call them as tools and fail. | Reword the heading/section: these are REST API calls (`/api/registry`), not MCP tools. |
| A2 | `using-deriva-mcp` | Medium | Internal contradiction: line ~122 says the primer "inlines both" the concepts + getting-started guides; lines ~31-37 and ~58-59 say it carries only a compact contract + a manifest, NOT inlined. | Pick one (the manifest/not-inlined version is correct per the primer's ~1K-token design) and fix the contradicting line. |
| A3 | `setup-notebook-environment` | Medium | (a) "use the MCP tool:" followed by a *CLI* command (`uv run deriva-ml-install-kernel`) — there is no such MCP tool. (b) Description trigger `'install deriva-ml-mcp'` has no matching body content. | (a) Reword: it's a CLI command, not an MCP tool. (b) Drop the dead trigger or add the content. |
| A4 | `generate-scripts` | Medium | Decision-matrix row marks "modify vocabulary terms" as requiring a committed script + execution — contradicts the `add_term` interactive-MCP pattern (vocab terms don't need provenance executions). | Recategorize the vocab-modification row: interactive `add_term`, not a committed script. |
| A5 | `help` | Low | Description says `deriva-mcp` — the **archived** legacy server name. | → `deriva-mcp-core` / `deriva-ml-mcp`. |
| A6 | `ml-data-engineering` | Low | Uses both `select_newest` (lines 145, 263) and `select_latest` (line 235) — both valid, but inconsistent within one file. | Standardize on `select_newest` (the canonical name; `select_latest` is the alias). |
| A7 | `dataset-lifecycle` | Low | Announces the arc's Validate step but has **no explicit `## Phase: Validate` heading** — buried in the Phase 5 (Version) callout. Its siblings (`create-feature` Phase 6, `experiment-lifecycle` Phase 6) have explicit Validate phases. | Add an explicit Validate phase heading, or reframe so the arc claim matches the structure. |
| A8 | `browse-erd` | Low | Dangling `references/erd-design-guide.md` — exists but never referenced from the body. | Reference it from the body, or remove it if obsolete. |
| A9 | `validate-project-setup` | Trivial | Redundant frontmatter: both `user-invocable: true` and `disable-model-invocation: true` set (the disable flag wins). | Drop the redundant `user-invocable: true`. |

## Group B — Compaction opportunities (progressive disclosure)

Principle (skill-creator): SKILL.md ideally <500 lines; reference-grade depth
(long worked examples, exhaustive option tables, deep API recipes, error
catalogs) belongs in `references/` with a one-line pointer left behind — losing
NO effectiveness. Ranked by lines saved.

**Skills with NO `references/` dir (create one) — biggest structural wins:**

| Skill | Lines | Extractable | Candidates |
|---|---|---|---|
| `manage-deriva-storage` | 490 | ~300 → ~190 | cache-warming (Phase 3, ~110), cleanup recipes (Phase 2, ~100), inspection (Phase 1, ~90). Also: the `rag_search` preamble at line 11 is vestigial (queries the catalog, not the local cache) — review/drop. |
| `setup-ml-catalog` | 330 | ~100 → ~230 | clone_via_bag deep-dive (Branch 2 Steps 2-6, ~75), failure-modes catalog (~30) |
| `debug-bag-contents` | 304 | ~90 → ~215 | Step 5 scenario catalog (~60) + Step 8 fix recipes (~32) → `references/scenarios.md`. Keep the Quick Diagnostic Checklist inline. |
| `model-development-workflow` | 407 | ~65 → ~340 | Phase 3 dev-dataset recipe (~65, dup of dataset-lifecycle) → `references/dev-dataset-recipe.md` |
| `deriva-ml-context` | 326 | ~65 (careful) | `carry structure` worked examples (~30) + `find_*`/`list_*` convention (~35). NOTE: always-on skill — entity-resolution workflow + start-here orientation must stay inline (load-bearing). Extract conservatively. |

**Skills WITH `references/` underusing it:**

| Skill | Lines | Extractable | Candidates |
|---|---|---|---|
| `write-hydra-config` | 610 | ~370 → ~240 | Largest file. Deep per-config recipes / option tables → its existing references. (Also re-verify the `validate_config_file` note flagged by auditor A.) |
| `capture-tacit-knowledge` | 458 | ~145 → ~315 | The 5 worked examples (lines ~267-431) → `references/entry-examples.md`; keep the single Mode-A canonical illustration inline. **Always-on skill — the behavioral rules must stay; only the examples move.** |
| `run-notebook` | 381 | ~140 → ~241 | Hydra override gotcha (~50), host/catalog recipe (~35), ROC worked example (~55) → its existing `references/workflow.md` |
| `create-feature` | 331 | ~65 → ~266 | Bulk-CSV worked example (lines ~157-245, ~89→trim to pointer) → `references/workflow.md` |
| `compare-model-runs` | 443 | ~60 | Phase 2C Python that duplicates `references/prediction-csv-pattern.md`; de-dup inline-vs-reference |

## Cross-cutting style note (not a defect)

The shorthand `feature-design` / `dataset-design` / `model-design` (entity-noun)
is used in some skills alongside the full `docs/design/<entity>/<slug>.md` path.
Intentional in `design-experiment`'s trigger list, but mixing the two forms in
one skill body can read as if the shorthand is a filename. Optional: standardize
to "a `<entity>` design doc (`docs/design/<entity>/<slug>.md`)" on first use per
skill. Low priority.

## Execution plan

After PR #88 merges, branch off `main`. Suggested structure:
1. **Defects PR** — all of Group A (small, one coherent PR, fast review).
2. **Compaction** — per-skill or small batches; each extraction reviewed for
   "pointer left behind, no effectiveness lost." The no-references/ skills first
   (biggest structural win), always-on skills (capture-tacit-knowledge,
   deriva-ml-context) last and most conservatively.

Compaction is token-budget / maintainability, not correctness — sequence it
behind the defects so the high-value correctness fixes land first.
