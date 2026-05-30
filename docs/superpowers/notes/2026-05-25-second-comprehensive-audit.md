# deriva-ml-skills — second comprehensive audit
**Date:** 2026-05-25
**Scope:** all 29 skills under `skills/`, against deriva-ml v1.39.0 + deriva-ml-mcp v0.5.0+ (current upstream HEAD).
**Predecessor:** [2026-05-23 follow-up note](2026-05-23-skills-followups-from-mcp-audit.md) + the 5-PR remediation sequence (PRs #36 / #38 / #35 / #39 / #40 / #41 / #42).

## Executive summary

The plugin is in **substantially better shape than the May 18 audit found it**. All 12 removed MCP tools and 8 removed/superseded Python methods are clean across every skill `.md` file. The stateless-MCP rule, MCP/local-Python boundary, RID opacity, and Asset_Role auto-tag contract are upheld consistently. The registry source-of-truth shows zero semantic drift since May 18 — same 43 tools + 2 prompts, same Python API surface (one new optional parameter, file-path drift from upstream reorganization).

**But:** the audit found one **critical P0 regression** and a handful of P1/P2 issues that aggregate into ~30 skill files needing edits.

The critical P0: **PR-2a's script templates were never merged into main.** PR #37 (the branch `pr-2a-script-templates`) is still OPEN on GitHub. All eight bundled templates that PR-2b through PR-5 routed users to (`basic_execution.py`, `nested_execution.py`, `salvage_execution.py`, `crash_recovery.py`, `populate_feature_values.py`, `warm_cache.py`, `upload_asset.py`, `download_asset.py`) **do not exist on disk on main**. Every "copy this template" pointer added by PR-2b is a dead link. This is load-bearing — it sits at the center of the execution-authoring story that the entire post-v0.5.0 architecture depends on.

This audit also surfaces three categories of smaller issues: dead cross-references, over-broad descriptions (8 skills), and consolidation opportunities (2-3 skill pairs).

---

## P0 — Immediate correctness fixes

### P0.1 — Merge PR #37 (the bundled script templates from PR-2a)

**The problem.** PR-2a's commit `d3dec28` adds 8 template files across 5 skills' `scripts/` directories. The PR was opened (#37), the user said "merged," internal task tracking marked it complete, and PR-2b through PR-5 then routed prose to those templates. But PR #37 was never actually squash-merged into main — it shows `state: OPEN` on GitHub.

**Impact.** ~25 broken file references across these skills:

| Template | Referenced from |
|---|---|
| `skills/execution-lifecycle/scripts/basic_execution.py` | `execution-lifecycle/SKILL.md:60,64`, `troubleshoot-execution/SKILL.md:58`, `troubleshoot-execution/references/execution-lifecycle.md:107`, `dataset-lifecycle/references/workflow.md:44`, `generate-descriptions/SKILL.md:17`, `manage-storage/SKILL.md:269` |
| `skills/execution-lifecycle/scripts/nested_execution.py` | `execution-lifecycle/SKILL.md:65`, `troubleshoot-execution/references/execution-lifecycle.md:377` |
| `skills/execution-lifecycle/scripts/salvage_execution.py` | `execution-lifecycle/SKILL.md:66`, `troubleshoot-execution/SKILL.md:69,308`, `troubleshoot-execution/references/execution-lifecycle.md:368,456`, `manage-storage/SKILL.md:184` |
| `skills/execution-lifecycle/scripts/crash_recovery.py` | `execution-lifecycle/SKILL.md:67`, `troubleshoot-execution/SKILL.md:147,151,156`, `troubleshoot-execution/references/execution-lifecycle.md:457`, `run-notebook/references/workflow.md:262` |
| `skills/create-feature/scripts/populate_feature_values.py` | `execution-lifecycle/SKILL.md:71`, `create-feature/SKILL.md:126,139`, `deriva-ml-context/SKILL.md:75` |
| `skills/manage-storage/scripts/warm_cache.py` | `execution-lifecycle/SKILL.md:43,72`, `manage-storage/SKILL.md:21,214,267,286`, `using-deriva-mcp/SKILL.md:67`, `dataset-lifecycle/references/concepts.md:307`, `deriva-ml-context/SKILL.md:72` |
| `skills/work-with-assets/scripts/upload_asset.py` | `execution-lifecycle/SKILL.md:43,73` |
| `skills/work-with-assets/scripts/download_asset.py` | `execution-lifecycle/SKILL.md:43,73`, `work-with-assets/references/workflow.md` (downstream refs) |

**Fix:** merge PR #37. Verify the templates land on main. After merge, every existing prose pointer resolves correctly — no follow-up edit needed.

**Why this was missed:** PRs #2b, #3, #4, #5 reviewed cleanly because the *routing prose* was correct in isolation; the dead-link condition is only visible when you `ls` the scripts directories. The earlier regex sweep checked for stale tool names, not for broken file pointers. This audit's parallel consistency-check agent caught it.

### P0.2 — Fix 3 dead `run-experiment` cross-references

`run-experiment` is referenced as a skill in 3 places but does not exist:
- `configure-experiment/SKILL.md:254`
- `new-model/SKILL.md:208, 215`
- `configure-experiment/references/workflow.md:166`

The right target is probably `execution-lifecycle` (for the run mechanics) or `experiment-lifecycle` (for the broader arc). Each occurrence needs review on which is more appropriate; the wrong choice would route users away from the right answer.

---

## P1 — Stale-but-works fixes

### P1.1 — Trim over-broad descriptions

Eight skills have descriptions exceeding ~250 words. Per the skill-creator guidance, metadata is "always in context (~100 words)"; excess dilutes the trigger signal and crowds out the load-bearing parts.

| Skill | Current length | Notes |
|---|---|---|
| `experiment-lifecycle` | ~400 words | Longest in the plugin. Trigger phrase list is doing nothing the body doesn't already do better. |
| `dataset-lifecycle` | ~350 words | "Covers" + "Triggers on" + "Do NOT use for" all redundant with body. |
| `troubleshoot-execution` | ~400 words | Symptom-table-like contents in the description. Most of this can move to body. |
| `using-deriva-mcp` | ~400 words | The detailed trigger phrase list ("what X are in the catalog," etc.) belongs in body. |
| `execution-lifecycle` | ~250 words | Earns most of its length; mild trim. |
| `setup-ml-catalog` | ~250 words | Marketing-language trigger expansion. |
| `create-feature` | ~250 words | Multi-paragraph. |
| `setup-notebook-environment` | ~200 words | 20+ trigger phrases. |

**Recommended target:** 150-200 words per skill, prioritizing the clearest 2-3 trigger contexts and one sentence about what the skill does. Examples that worked well in the audit: `compare-model-runs` and `maintain-experiment-notes` (~300 words but earn it because they teach distinct modes that the body alone wouldn't surface).

### P1.2 — `browse-erd` stateless-MCP framing

`browse-erd/SKILL.md` carries connection-state framing inconsistent with the rest of the plugin:

- Line 3 (description): *"...for the currently connected Deriva catalog. Requires an active catalog connection."*
- Line 9: *"...the connected catalog."*
- Line 21: *"Read `deriva://catalog/connections` to verify you're connected."* (This resource is referenced nowhere else in the plugin.)

This contradicts the stateless rule documented in `using-deriva-mcp`, `deriva-ml-context`, and `api-naming-conventions`. Fix: rephrase to take `hostname=` and `catalog_id=` explicitly like every other skill.

### P1.3 — Asset_Type filter prose inconsistency in `compare-model-runs`

The code in `compare-model-runs/references/jsonl-asset-pattern.md:71` correctly uses `in` membership (`"Metrics_File" in (f.get("asset_types") or [])`), but the surrounding prose at line 56 says *"Filter for `asset_type == "Metrics_File"`"* and `SKILL.md:176` says *"Look for entries where `asset_type == "Metrics_File"`."*

Prose contradicts code, and code is correct. The contradiction is what PR-4's Asset_Role contract section in `work-with-assets` exists to prevent. Fix: align prose with the membership pattern.

### P1.4 — Vocab steering silence in `dataset-lifecycle` and `work-with-assets`

These skills tell users to extend built-in vocabularies via `add_term`, which is correct — those vocab tables already exist. But none of them point users at `deriva_ml_create_vocabulary` when they need a brand-new vocabulary table. The steering is documented in `deriva-ml-context`, `create-feature`, `api-naming-conventions`, `troubleshoot-execution` — it should also fire here.

**Specific silences:**
- `dataset-lifecycle/references/concepts.md:115-121`
- `dataset-lifecycle/references/workflow.md:296`
- `dataset-lifecycle/references/curated-subsets.md:39`
- `work-with-assets/SKILL.md:64`
- `work-with-assets/references/concepts.md:118-121`
- `work-with-assets/references/workflow.md:127`

Each spot needs a one-liner: *"If the vocab table doesn't exist yet, create it with `deriva_ml_create_vocabulary(...)` (ML-aware: applies project curie prefix, refreshes navbar). See `deriva-ml-context` for the steering rationale."*

### P1.5 — Resource-first reads silence in `write-hydra-config`

`write-hydra-config` reaches for `deriva_ml_list_datasets` / `deriva_ml_list_workflows` at lines 206, 234, 295, 335, 346, 468 without offering the resource-form alternative each time. Only line 238 mentions it. The rest of the lifecycle skills (`dataset-lifecycle`, `execution-lifecycle`, `experiment-lifecycle`, `work-with-assets`, `configure-experiment`, `compare-model-runs`, `manage-storage`) all uniformly lead with the resource form and fall back to the tool for paginated/filtered cases. Fix: add the resource-form callout to each of those `write-hydra-config` sites.

### P1.6 — Registry needs a small delta patch

The source-truth registry at `docs/superpowers/notes/2026-05-18-source-truth-registry.md` has minor drift since May 18:

- New parameter `validate: bool = True` on `deriva_ml_add_dataset_members` (mutate.py:246-255)
- File-path drift from upstream's `tools/` subpackage reorganization (cosmetic; all paths still resolve to real files at slightly different line numbers)
- New public surface on `DerivaML`: `workspace` property, `create_table()`, `define_association()`
- New `Execution.from_registry()` classmethod
- `Asset` and `Workflow` value-object classes never enumerated in §B

No semantic drift, no tool additions/removals, no exception class changes, both DO-NOT-REFERENCE lists still pass. A 30-minute delta patch closes the gap.

---

## P2 — Capability uplift / consolidation

### P2.1 — Consolidation candidates

**(a) `catalog-operations-workflow` + `generate-scripts`.** Both teach "committed scripts vs interactive MCP," both ship template patterns, both fire on overlapping triggers. The substantive content overlap is high. Pick one name (probably `generate-scripts` — broader trigger set) and consolidate.

**(b) `model-development-workflow` + `experiment-lifecycle`.** Both teach the dry-run → small-data → full-data progression as their core content. `model-development-workflow`'s Phase 1-5 is a superset of `experiment-lifecycle`'s seven-phase arc. Either merge or sharply re-scope one of them — `model-development-workflow` could narrow to "onboarding to an existing project," and `experiment-lifecycle` could own the per-cycle discipline.

### P2.2 — Push positive-capability content out of `troubleshoot-execution`

`troubleshoot-execution` is 527 lines (the longest SKILL.md). The "Trace an artifact's provenance" section + worked example (~50 lines) is a positive ML-workflow capability, not a troubleshooting topic. It teaches `deriva_ml_get_lineage` — a tool a user reaches for to answer "where did this prediction come from," not to fix an error. Move it to `compare-model-runs` (which already does provenance-style queries) or split out a small `trace-provenance` skill.

### P2.3 — Move salvage/recovery into the existing references file

`troubleshoot-execution`'s "Salvage a Failed Execution" section is ~100 lines of standalone content already referenced from `troubleshoot-execution/references/execution-lifecycle.md`. The body could carry only the symptom-table entry plus a pointer; the recovery steps move into the reference file. Brings SKILL.md back under 400 lines without losing anything.

### P2.4 — De-duplicate "wire RIDs into configs/*.py" content

The "proactively offer to update `src/configs/assets.py`" content appears in three skills:
- `work-with-assets/SKILL.md` (per-asset scope)
- `execution-lifecycle/SKILL.md` (bulk-output scope, with explicit scope boundary)
- `write-hydra-config/SKILL.md` (config-author scope)

The scope boundaries are documented, but readers see the same shape three times. Consolidation: make `write-hydra-config` the authority on the `AssetSpecConfig` shape and how to add entries; have `work-with-assets` and `execution-lifecycle` name only the trigger (when to offer) and link out.

### P2.5 — Cold-start banner — pick a policy and apply it uniformly

Currently three skills carry the cold-start orientation banner (`dataset-lifecycle`, `execution-lifecycle`, `experiment-lifecycle`); the other catalog-touching skills don't. This is arbitrary — `create-feature`, `work-with-assets`, `troubleshoot-execution`, `compare-model-runs`, `configure-experiment`, `ml-data-engineering`, `model-development-workflow`, `manage-storage` are all first-touch-likely too.

Two options:
- Add the banner to all 11 catalog-touching skills (consistent but more visual noise)
- Remove from the 3 that have it and let `using-deriva-mcp` carry the discipline alone (relies on `using-deriva-mcp` actually firing first; it has `disable-model-invocation: false` and should)

The latter is the more elegant choice. Either way, pick one.

### P2.6 — Trim `write-hydra-config` SKILL.md body

529 lines, second-longest. Has a reference file (`config-reference.md`, 18KB) but the SKILL.md body still carries per-config-group "Key Rules" detail that belongs in the reference. Push down; aim for under 400 lines.

### P2.7 — Trim `troubleshoot-execution` SKILL.md body

527 lines (longest). Combination of P2.2 + P2.3 above plus general tightening would land it under 400.

---

## What's already solid

- **All 12 removed MCP tools: zero references in any skill `.md`** (regex sweep, 57 files audited).
- **All 8 removed/superseded Python methods: zero references** including the `cache_dataset(asset_rid=)` parameter hallucination check.
- **Stateless MCP rule:** upheld in 28 of 29 skills (only `browse-erd` violates).
- **MCP/local-Python boundary:** clean — no skill suggests an MCP tool downloads bytes to the caller's filesystem.
- **RID opacity:** zero violations.
- **Asset_Role auto-tag contract:** correctly documented in `work-with-assets`; one minor prose-vs-code inconsistency in `compare-model-runs` (P1.3 above).
- **`deriva_ml_create_vocabulary` steering:** correctly documented in 6 places.
- **Resource-first reads:** documented in 7 of 8 catalog-touching skills (`write-hydra-config` is the gap).
- **Source-truth registry:** zero semantic drift since May 18.

---

## Recommended next steps

In strict priority order:

1. **Merge PR #37** to land the bundled script templates. (Fixes P0.1, ~25 dead links.) Zero new code needed — branch already exists.
2. **Fix the 3 `run-experiment` dead refs** (P0.2). 10-minute change.
3. **Trim the 8 over-broad descriptions** (P1.1). 90 minutes; do as a single PR.
4. **Fix `browse-erd` stateless framing + `compare-model-runs` filter prose** (P1.2 + P1.3). 15 minutes; same PR.
5. **Add vocab steering to `dataset-lifecycle` + `work-with-assets`** (P1.4). 20 minutes; same PR as #3 or its own.
6. **Add resource-form callouts to `write-hydra-config`** (P1.5). 20 minutes.
7. **Patch the registry** (P1.6). 30 minutes; a documentation chore, no skill edits.
8. **Decide on consolidations** (P2.1) — requires a design call, not just an edit. Worth a separate conversation.
9. **Push positive-capability content out of `troubleshoot-execution`** (P2.2 + P2.3). 1-2 hours of restructure.
10. **De-dup the wire-RIDs content** (P2.4). 1 hour.
11. **Pick a cold-start banner policy** (P2.5).
12. **Trim `write-hydra-config` body** (P2.6).

#1-2 are correctness fixes and should land immediately. #3-7 are quality-of-life improvements that compound into a measurably leaner plugin. #8-12 are design / capability work that benefit from a planning conversation first.
