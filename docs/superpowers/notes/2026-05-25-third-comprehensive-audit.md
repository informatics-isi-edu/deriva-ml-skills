# deriva-ml-skills — third comprehensive audit
**Date:** 2026-05-25 (later same day as the second audit)
**Scope:** all 28 skills under `skills/` (1 fewer than the second audit — `catalog-operations-workflow` merged into `generate-scripts` via #47).
**Predecessor:** [2026-05-25 second comprehensive audit](2026-05-25-second-comprehensive-audit.md) plus the 11-PR remediation sequence that followed (PRs #42 / #43 / #44 / #45 / #46 / #47 / #48 / #49 / #50).
**Methodology:** Same four-agent shape as the second audit (registry refresh + regex sweep + substantive read + cross-skill consistency) so findings compare apples-to-apples.

## Executive summary

The plugin is **substantially cleaner than the second audit found it**. The headline P0 from that audit (missing bundled script templates) is fixed. All P1 items are fixed. Three of four P2 design questions are fixed; the fourth (vocab-creation steering in dataset-lifecycle + work-with-assets) was addressed in #45.

This audit found **zero P0 issues, one P1 surface-convention nit, and a handful of small P2 polish opportunities.** The most substantive finding is one missed-by-prior-audits item: `configure-experiment` carries ~100 lines of storage content that duplicates `manage-storage`, with placeholder-looking pseudo-code that probably should be a clean pointer.

### Agent verdicts at a glance

| Agent | Verdict |
|---|---|
| Registry refresh | **No drift.** 43 tools + 2 prompts match name-for-name, signature-for-signature, path-for-path. One trivial 1-line shift on `DerivaML.workspace` (842 vs 841 — within tolerance). Both DO-NOT-REFERENCE lists pass. No new exceptions. |
| Regex sweep | **Zero matches.** All 12 removed MCP tools clean. All 8 removed/superseded Python methods clean. The `execution.execute() as` indirection (pre-v0.5.0 pattern) is also clean — no skill uses it. |
| Substantive read | All 28 skills broadly clean. 4 small issues identified (1 stale, 3 polish). One false positive flagged below. |
| Cross-skill consistency | All 10 cross-cutting principles (8 from the second audit + 2 new ones introduced by recent PRs) upheld. 1 P1 surface-convention nit, 2 P2 silences. |

---

## Verified cross-cutting principles

The second audit established 8 principles; PRs #47 and #50 added 2 more. All 10 are upheld:

| # | Principle | Status |
|---|---|---|
| 1 | Stateless MCP rule (`hostname=` / `catalog_id=` everywhere) | ✅ Clean, with one P1 nit |
| 2 | deriva-ml inheritance-with-override (`deriva_ml_create_vocabulary` over generic) | ✅ Clean — load-bearing steering present in 6+ places |
| 3 | Bundled-template pattern (8 templates on disk; references resolve) | ✅ Clean — every routing prose pointer resolves |
| 4 | MCP / local-Python boundary | ✅ Clean |
| 5 | RID opacity | ✅ Clean (zero violations; principle lives in deriva-skills) |
| 6 | Resource-first reads | ✅ Clean — every list-tool use carries justification |
| 7 | Cold-start orientation (only in `using-deriva-mcp` + `deriva-ml-context`) | ✅ Clean — PR-49 contract holds; zero banners in lifecycle skills |
| 8 | Asset_Role auto-tag contract | ✅ Clean — canonical block + reinforcement; no equality filters except as anti-pattern |
| 9 | **Wire-RIDs centralization** (new from PR-50) | ✅ Mostly clean — minor residual mini-snippets noted below |
| 10 | **Cycle-zero vs cycle-N boundary** (new from PR-47) | ✅ Clean — explicit handoff prose both ways |

---

## P0 — none

No correctness regressions. No broken file pointers. No removed-tool references. No stale lifecycle terms.

## P1 — surface-convention nit

### P1.1 — `experiment-lifecycle` illustrative MCP shapes omit `hostname=`/`catalog_id=`

Two MCP call illustrations in `experiment-lifecycle/SKILL.md`:
- Line 96: `deriva_ml_list_feature_values(execution_rids=[...])`
- Line 99: `deriva_ml_list_executions(workflow_type="Training", sort=True)`

Both are prose-style shape fragments embedded inside descriptive paragraphs, not full examples that would expect every argument filled in. But every other skill in the plugin includes `hostname=` and `catalog_id=` even in illustrative fragments — this is a judgment call. Tightening these two would restore the surface-convention uniformity the rest of the plugin upholds.

5-minute fix; mostly a discipline-signal issue.

## P2 — polish opportunities

### P2.1 — `configure-experiment` storage section duplicates `manage-storage`

`configure-experiment/SKILL.md` lines 134-242 (~100 lines) is a full "Storage: Cache vs Working Directory" section that duplicates content owned by `manage-storage`. It also contains pseudo-code with commented-out tool calls (`# Python API or Bash: inspect ~/.deriva-ml/ (...)`) that read as placeholder or broken.

This **predates the entire PR-43→PR-50 remediation cycle** and was missed by both the May 18 and May 25 second audits — the audit pattern was looking for stale API references and didn't surface duplication this size.

**Fix:** strip the section, replace with a one-line pointer to `/deriva-ml:manage-storage`. ~30 minutes including cross-reference touch-up.

### P2.2 — small residual `DatasetSpecConfig(...)` snippets in `dataset-lifecycle`

PR-50's contract for `dataset-lifecycle` was "name only the trigger + scope + pointer; `write-hydra-config` owns the shape." Three sites still carry mini-illustrations of the shape (SKILL.md L93, L147, L201): `DatasetSpecConfig(rid="28EA", version="0.4.0")`-style fragments inside surrounding prose.

These are illustrative ("explicit released versions only — see `DatasetSpecConfig(rid=..., version=...)` form") rather than full field references, so they don't strictly violate PR-50. But they're a real seam — a future tightening could push them all into bare prose ("explicit released versions only, embeddable in experiment configs — see write-hydra-config for the full shape").

Not urgent; trade-off is between strict de-duplication and inline reading flow.

### P2.3 — `debug-bag-contents` Step 6 doesn't name the API

`debug-bag-contents` Step 6 says "Python API bag inspection" without naming the actual method. The method is `bag.validate()` per `dataset-lifecycle` line 188. Trivial — one-line fix to name the API.

### P2.4 — `model-development-workflow` Quick Reference table has malformed rows

The "Quick Reference: Which Skill for What" table at the end of `model-development-workflow/SKILL.md` has several rows missing the rightmost `| this plugin |` cell. Cosmetic; renders fine in most viewers but is uneven.

### P2.5 — `compare-model-runs` description length

After PR-48 absorbed the provenance-tracing content, `compare-model-runs`'s description grew to surface both "compare metrics" and "trace provenance" as triggers. The description works but is at the edge — an auto-trigger discrimination test on a context-free "where did this come from" question could fire this skill in cases where a different skill might be more appropriate.

Not a clear violation; worth watching but no immediate fix needed. Could be addressed by pushing the provenance triggers into the body and trimming the description head back to metric comparison.

### P2.6 — `api-naming-conventions` could surface RID opacity

The RID opacity rule lives in `deriva-skills/deriva-context` (workspace decision: principles that apply across both plugins live in the sibling). `api-naming-conventions` documents the `lookup_` / `find_` / `get_` semantics — a natural spot to add "...and RIDs passed to these methods are opaque tokens; compare for equality only, never parse or slice" if the team wants in-plugin coverage. Currently silent.

Not urgent; depends on a workspace-level call about which principles need plugin-local reinforcement.

---

## Corrections to the substantive-read agent's findings

I verified the agent's claims against current source before writing this report. One claim turned out to be a false positive:

**False positive — `new-model` Step 4 `make_config` vs `experiment_store`.** The agent flagged `new-model/SKILL.md` Step 4 as using `make_config()` while `write-hydra-config` "canonical" uses `experiment_store(name=..., deriva_ml=..., ...)`. **Both are documented in `write-hydra-config`** — `make_config(...)` is the canonical experiment shape (lines 36, 72, 97); `experiment_store(...)` at line 370 is the **bootstrap composition shortcut** for `defaults`-driven configs without `make_config`. `new-model` Step 4 uses the canonical form correctly. No drift.

---

## What's improved since the second audit

The remediation sequence (PRs #42–#50) closed the second audit's findings cleanly:

| Second audit P0/P1/P2 | Closed by | Status |
|---|---|---|
| P0.1 missing script templates (~25 dead links) | #43 | ✅ Fixed |
| P0.2 dead `run-experiment` cross-refs | #44 | ✅ Fixed |
| P1.1 over-broad descriptions (3 skills) | #45 | ✅ Fixed |
| P1.2 `browse-erd` stateless framing | #44 | ✅ Fixed |
| P1.3 `compare-model-runs` `==` vs `in` prose | #44 | ✅ Fixed |
| P1.4 vocab-creation steering silence | #45 | ✅ Fixed |
| P1.5 `write-hydra-config` resource-first silence | #45 | ✅ Fixed |
| P1.6 registry delta patch | #46 | ✅ Fixed |
| P2 catalog-operations consolidation | #47 | ✅ Fixed |
| P2 model-development vs experiment-lifecycle scoping | #47 | ✅ Fixed |
| P2 troubleshoot-execution restructure | #48 | ✅ Fixed (provenance moved to compare-model-runs) |
| P2 cold-start banner policy | #49 | ✅ Fixed (centralized in 2 places, 3 banners removed) |
| P2 wire-RIDs de-duplication | #50 | ✅ Fixed |

Plus #42 (maintain-experiment-notes rewrite — two read modes, cross-domain bridging — surfaced from a parallel skill-creator pass).

## What this audit found that prior audits missed

Only one substantive item — and it's pre-existing, not a regression:

- **P2.1 (configure-experiment storage duplication, ~100 lines).** Predates the PR-43→PR-50 cycle. The audit pattern in both prior passes was looking for stale API references and missed duplication of this size. The substantive-read agent caught it this time because its criteria explicitly flagged "skills doing too much" and "consolidation candidates."

Everything else this audit found is either polish-grade (P2.2-P2.6) or a 5-minute surface-convention nit (P1.1).

## Recommended next steps

If you want to do another sweep:

1. **P2.1** (configure-experiment storage strip) — biggest payoff. ~30 min. Materially improves both skills (configure-experiment by shedding dead weight; manage-storage by becoming the unambiguous home).
2. **P1.1** (experiment-lifecycle `hostname=`/`catalog_id=` in two illustrative fragments) — 5 min.
3. **P2.3, P2.4** (debug-bag-contents API name; model-development-workflow table fix) — 10 min total.

The remaining P2 items (P2.2 mini-snippets, P2.5 compare-model-runs description, P2.6 RID opacity surface) are real but optional design calls.

## Bottom line

The remediation worked. The plugin is in **measurably better shape** than the 2026-05-25 second audit found it: zero correctness issues, principle uniformity across 10 cross-cutting rules, source-truth registry exactly matches upstream. The findings this audit surfaced are smaller in aggregate than even a single P0 from the second audit.

If no further audit-driven work is planned, the plugin is in a steady-state place from which user-driven changes can land confidently.
