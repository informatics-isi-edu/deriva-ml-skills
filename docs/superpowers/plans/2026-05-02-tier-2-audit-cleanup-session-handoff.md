# Session handoff — tier-2 audit cleanup (2026-05-02)

This is a session-state-and-interactions document. It captures the
full context of an in-progress multi-round refactor so the work can
be resumed in a future session without losing the design rationale,
the cross-repo asks raised in parallel, or the operating principles
that emerged during the refinement interviews.

## TL;DR

A two-part audit (tier-2 skills + MCP surface) of the DerivaML
domain layer produced a six-round cleanup plan. **All six rounds
are complete.** Final outcomes: tier-2 skill count 28→27 with
~56% always-on weight reduction; tier-1 gained `use-annotation-builders`
(v1.2.0); deriva-ml gained `lookup_lineage` (v1.32.0) and
`validate_dataset_specs`+`validate_execution_configuration` (v1.33.0);
deriva-ml-mcp gained 3 thin tool wrappers + 2 resources (v3.3.0).
A new PR-required workflow convention was added to deriva-ml/CLAUDE.md
during Round 6.

| Round | Status | Effort | Description |
|---|---|---|---|
| 1 | ✅ Done | ~75 min | Tier-2 mechanical cleanup (deleted 2 routers + 1 broken skill; added experiment-lifecycle and validate-project-setup skills; fixed 11 stale tier-1 references; brought lifecycle trio to uniform behavior) |
| 2 | ✅ Done | ~90 min | MCP prompt restructure (deleted 2 mis-shaped prompts + redistributed content to docstrings; widened RAG indexing to top-level docs; bumped deriva-ml-mcp v3.1.1 → v3.2.0) |
| 3 | ✅ Done | ~3 hr | Inheritance-with-override rule across all three planes (skills, MCP, Python) replaces the old "DerivaML abstractions take precedence" framing; ADR-0001 captures the rule-vs-table call; "What DerivaML adds on top" paragraph names the data-design ↔ process-design orthogonality; tier-2 cross-reference audit (33 refs, all bucket-1 inheritance, no edits needed); legacy-MCP scaffolding cleaned from 14 tier-2 skill files; 3 skills cross-reference tier-1 `semantic-awareness`; cross-repo sync to deriva-ml-mcp `_CONCEPTS_GUIDE` (bumped v3.2.0 → v3.2.1) |
| 4 | ✅ Done | ~2 hr | Tier-2 always-on weight reduction (1994 → 879 lines, -56%). Re-targeted from the parent plan's literal slimming list to the actual auto-fire skills. Three skills flipped to slash-only (`compare-model-runs`, `help`, `browse-erd`) for a 376-line one-shot drop; four heavy slims (`dataset-lifecycle` 434→129, `create-feature` 403→174, `execution-lifecycle` 185→107, `generate-descriptions` 169→64) move depth to references/; light-touch trim on three smaller skills (`deriva-ml-context`, `experiment-lifecycle`, `maintain-experiment-notes`); README "Auto-invoked guides" table corrected (was claiming 11 auto-fire skills; only 6 actually were). |
| 5 | ✅ Done | ~3 hr | Tier placement: `use-annotation-builders` moved to tier-1 (deriva-skills v1.1.1 → v1.2.0); `coding-guidelines` reframed (was misnamed — content is project-bootstrap-and-operations, not generic coding standards) and content distributed to a new tier-2 `setup-derivaml-project` skill (bootstrap moment), `setup-notebook-environment` (uv discipline), `model-development-workflow` (git workflow + version-bumping decision matrix + DerivaML extensibility), with redundant atoms deleted; `create-web-app` description sharpened to lead with the deriva-ml-apps server prerequisite; tier-2 README's Tier-1-vs-Tier-2 framing updated to ADR-0001's inheritance-with-override rule (carryover correction from Round 3) and to reflect the two tier-1 Chaise-annotation paths. Tier-2 skill count: 28 → 27. |
| 6 | ✅ Done | ~30 min refinement; `lookup_lineage` ~6 hr; `validate_*` ~5 hr; Round 6b ~2 hr | Reshaped twice during execution. **First** (mid-grilling): architectural reframing — the new operations belong in the deriva-ml Python library first (where every existing `deriva_ml_*` MCP tool already wraps a deriva-ml method), with thin MCP wrappers; ADR-0001's inheritance rule operationalized. **Second** (post-`lookup_lineage`): use-case re-examination dropped `rank_executions` — the 3-step manual pattern in `compare-model-runs` is well-served by existing tools and didn't earn its maintenance cost. Final shipped scope: deriva-ml gained `lookup_lineage` (v1.32.0; PR #72 docs+convention merged) and `validate_dataset_specs` + `validate_execution_configuration` (v1.33.0; PR #73 merged). deriva-ml-mcp v3.3.0 ships 3 thin MCP tool wrappers + 2 read-only resources (`ml/lineage/{rid}`, `ml/dataset/{rid}/spec`). Tier-2 `write-hydra-config` skill's validation section slimmed to use the new validate-spec tools instead of the per-RID `get_entities` walkthrough. PR-required workflow added to deriva-ml/CLAUDE.md (and tier-1 workspace CLAUDE.md). |

The full audit context and round structure are in three plan
documents in this directory; this handoff cross-references them and
captures session state not in those documents.

## Plan documents (canonical references)

These are the durable artifacts; resume by reading them in order.

| Document | Purpose |
|---|---|
| [`2026-05-02-tier-2-audit-cleanup-plan.md`](2026-05-02-tier-2-audit-cleanup-plan.md) | The original 6-round plan with the full audit context (tier-2 skills audit findings; MCP prompts/tools/resources audit findings; the precedence-principle steering reminder) |
| [`2026-05-02-tier-2-audit-cleanup-plan-round-1-refinement.md`](2026-05-02-tier-2-audit-cleanup-plan-round-1-refinement.md) | Round 1 refinement: 12 design questions resolved + 7-commit execution shape + the "guide-shaped vs tool-shaped" operating principle |
| [`2026-05-02-tier-2-audit-cleanup-plan-round-2-refinement.md`](2026-05-02-tier-2-audit-cleanup-plan-round-2-refinement.md) | Round 2 refinement: 12 design questions resolved + 4-commit execution shape; the "prompts shouldn't be static reference docs" reframing; the cross-repo asks raised in parallel |
| [`2026-05-02-tier-2-audit-cleanup-plan-round-3-refinement.md`](2026-05-02-tier-2-audit-cleanup-plan-round-3-refinement.md) | Round 3 refinement: 9 design questions resolved + 5-commit execution shape; reshapes Round 3 from "precedence map table" to "inheritance-with-override rule across all three planes" + ADR-0001 |
| [`2026-05-02-tier-2-audit-cleanup-plan-round-4-refinement.md`](2026-05-02-tier-2-audit-cleanup-plan-round-4-refinement.md) | Round 4 refinement: 6 design questions resolved + 5-commit execution shape; reshapes Round 4 from the parent plan's literal slimming list (which mixed auto-fire and slash-only skills) to "re-target on actual auto-fire weight; flip slash-only candidates; slim the keepers using tier-1's reference-pattern" |
| [`2026-05-02-tier-2-audit-cleanup-plan-round-5-refinement.md`](2026-05-02-tier-2-audit-cleanup-plan-round-5-refinement.md) | Round 5 refinement: 8 design questions resolved + 5-commit execution shape; reshapes Round 5 from "decide where 3 borderline skills belong" to the more substantive "use-annotation-builders moves to tier-1; coding-guidelines is misnamed and gets distributed across 3 skills (one new); create-web-app stays with a description reframe" |
| [`2026-05-02-tier-2-audit-cleanup-plan-round-6-refinement.md`](2026-05-02-tier-2-audit-cleanup-plan-round-6-refinement.md) | Round 6 refinement: two reshapes. **First:** architectural reframing — the new operations belong in the deriva-ml Python library first, with thin deriva-ml-mcp wrappers (ADR-0001's inheritance rule operationalized). **Second:** scope reduction — `rank_executions` removed after a use-case re-examination found its motivation much weaker than `lookup_lineage`'s; the existing `compare-model-runs` 3-step pattern serves the rank case adequately. Round 6 final scope is two methods (`lookup_lineage` ✅, `validate_dataset_spec` ⏳); the deriva-ml-mcp wrapper work becomes Round 6b after `validate_dataset_spec` lands. |
| [`../../adr/0001-precedence-as-rule-not-table.md`](../../adr/0001-precedence-as-rule-not-table.md) | ADR-0001: precedence as inheritance-with-override rule, not a routing table. Captures the rule-vs-table call and the surface-bounded (vs concept-bounded) framing of the override boundary. |

## Round 1 commits (deriva-ml-skills)

All on `main`, all pushed to origin:

| Hash | What |
|---|---|
| [`07f38a7`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/07f38a7) | Add "Versioning and updates" section to `troubleshoot-execution` |
| [`dc735a0`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/dc735a0) | Delete `check-deriva-ml-versions`; route to new section |
| [`bfce3e9`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/bfce3e9) | Fix 5 stale `route-catalog-schema` refs in skill content |
| [`bffd106`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/bffd106) | Delete the two routers; redistribute orphan triggers |
| [`7af79dd`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/7af79dd) | New skill: `experiment-lifecycle` (149 lines) |
| [`7630e83`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/7630e83) | New skill: `validate-project-setup` (143 lines) |
| [`78ee761`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/78ee761) | README/CLAUDE.md catch-up + execution-lifecycle auto-fire |

Net: skill count 29 → 28; the lifecycle trio (dataset, execution,
experiment) now uniformly auto-fires; all 11 stale tier-1 references
resolved; the operating principle established (guide-shaped skills
auto-fire; tool-shaped skills are on-demand).

## Round 2 commits (deriva-ml-mcp + one cross-repo doc commit)

| Hash | Repo | What |
|---|---|---|
| [`1fe2119`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/1fe2119) | deriva-ml-mcp | Delete `_WORKFLOW_DEDUP_GUIDE`; move content to `deriva_ml_create_workflow` docstring |
| [`1456f4f`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/1456f4f) | deriva-ml-mcp | Delete `_EXECUTION_LIFECYCLE_GUIDE`; distribute pitfalls to 4 lifecycle tools |
| [`a70b6e1`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/a70b6e1) | deriva-ml-mcp | Widen RAG indexing — repo-root prefix on deriva-ml; new source for deriva-ml-mcp |
| [`31246bf`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/31246bf) | deriva-ml-mcp | CLAUDE.md cross-repo sync notes update |
| [`655aac7`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/655aac7) | deriva-ml-mcp | Auto-generated bump-version commit (3.1.1 → **3.2.0**) |
| [`7df48e9`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/7df48e9) | deriva-ml-skills | Matching CLAUDE.md update |

Net: MCP prompts 4 → 2; ~5 tool docstrings expanded with the
redistributed warnings; RAG sources 1 → 2; released as **deriva-ml-mcp
v3.2.0** with the prompt removals as documented breaking changes.

## Round 3 commits (deriva-ml-skills + cross-repo deriva-ml-mcp)

| Hash | Repo | What |
|---|---|---|
| [`f7ca92f`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/f7ca92f) | deriva-ml-skills | `deriva-ml-context: replace steering principle with inheritance rule + cleanup` — also adds ADR-0001 + Round 3 refinement addendum |
| [`f3f1c93`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/f3f1c93) | deriva-ml-skills | `tier-2 audit: remove legacy-MCP scaffolding from three skills` (initial pass — narrow grep) |
| [`4457bf7`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/4457bf7) | deriva-ml-skills | `tier-2 audit: complete legacy-MCP cleanup across remaining 11 skills` (wider re-grep caught the boilerplate "the new MCP server is stateless" pattern that the first pass missed) |
| [`2c057ab`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/2c057ab) | deriva-ml-skills | `new-model, create-feature, dataset-lifecycle: cross-reference tier-1 semantic-awareness` |
| [`4bd77be`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/4bd77be) | deriva-ml-mcp | `refactor(prompts): align _CONCEPTS_GUIDE with deriva-ml-skills inheritance rule` |
| [`b2626cb`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/b2626cb) | deriva-ml-mcp | Auto-generated bump-version commit (3.2.0 → **3.2.1**) |

Net: deriva-ml-context shrank by 16 lines while gaining the
inheritance rule and the data-design ↔ process-design orthogonality
paragraph; legacy-MCP scaffolding removed from 14 tier-2 skill
files (no MCP veterans in the audience); 33 tier-1 cross-references
audited (all bucket-1 inheritance, no edits needed); 3 skills
gained explicit semantic-awareness pointers; cross-repo sync to
deriva-ml-mcp landed as v3.2.1; ADR-0001 records the rule-vs-table
design decision.

## Round 4 commits (deriva-ml-skills)

| Hash | What |
|---|---|
| [`a3a6cf1`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/a3a6cf1) | `tier-2: flip 3 skills to slash-only; correct README auto-fire list` (also lands the Round 4 refinement addendum) |
| [`845f330`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/845f330) | `dataset-lifecycle: slim auto-fire body; move depth to references` (434 → 129; new references/curated-subsets.md) |
| [`b18c563`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/b18c563) | `create-feature: slim auto-fire body; move depth to references` (403 → 174) |
| [`7fec0a8`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/7fec0a8) | `execution-lifecycle, generate-descriptions: slim auto-fire bodies` (185 → 107; 169 → 64; new references/templates.md for the latter) |
| (this commit) | `tier-2: opportunistic compression on light-touch trio + round 4 handoff` |

Net: tier-2 auto-fire weight 1994 → 879 lines (-56%, matching
tier-1's 58% reduction). The 7 keepers each fall under 200 lines.
Round 4 also incidentally completed the auto-fire-table correction
in the README (it was claiming 11 auto-fire skills; only 6
actually were).

## Round 5 commits (deriva-ml-skills + cross-repo deriva-skills)

| Hash | Repo | What |
|---|---|---|
| [`0cf14b3`](https://github.com/informatics-isi-edu/deriva-skills/commit/0cf14b3) | deriva-skills | `use-annotation-builders: new tier-1 skill (moved from deriva-ml-skills)` — adds the skill, marketplace entry, README row, and customize-display cross-reference |
| [`9ccf718`](https://github.com/informatics-isi-edu/deriva-skills/commit/9ccf718) | deriva-skills | `chore: add bump-my-version to dev deps so bump-version works` — environment fix needed before the version bump (bump-version CLI couldn't find the underlying tool) |
| [`d69425e`](https://github.com/informatics-isi-edu/deriva-skills/commit/d69425e) | deriva-skills | Auto-committed `uv.lock` update (from `uv sync` during the env fix) |
| [`c0f3649`](https://github.com/informatics-isi-edu/deriva-skills/commit/c0f3649) | deriva-skills | Auto-generated bump-version commit (1.1.1 → **1.2.0**) |
| [`5a07877`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/5a07877) | deriva-ml-skills | `coding-guidelines: distribute content across 3 skills; delete; add setup-derivaml-project` — the 13 atoms distributed atom-by-atom per the Round 5 refinement table |
| [`5e7226f`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/5e7226f) | deriva-ml-skills | `create-web-app: sharpen description to lead with deriva-ml-apps prerequisite` |
| [`51c3808`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/51c3808) | deriva-ml-skills | `README: update Tier-1 vs Tier-2 framing for post-Round-3 + post-Round-5 reality` (steering principle → inheritance-with-override; tier-1 Chaise-annotation paths spelled out) |
| (this commit) | deriva-ml-skills | `docs: round 5 handoff update` |

Net effect: tier-2 skill count 28 → 27 (deleted `coding-guidelines`
+ moved `use-annotation-builders` to tier-1 + added new
`setup-derivaml-project`). Tier-1 skill count: 11 → 12. Tier-1
released as **deriva-skills v1.2.0**. Both repos clean on `main`.

## Round 6 commits (deriva-ml + deriva-ml-mcp + deriva-ml-skills)

Round 6 is the only round that touched all three of the
implementation repos (deriva-ml, deriva-ml-mcp, deriva-ml-skills),
because the architectural reframing put canonical methods in
deriva-ml first with thin MCP wrappers in deriva-ml-mcp.

**deriva-ml side (the canonical implementations):**

| Hash | What |
|---|---|
| [`301d0ac`](https://github.com/informatics-isi-edu/deriva-ml/commit/301d0ac) | `docs(adr): adopt data-flow walk for lineage (ADR-0001)` |
| [`2190eb5`](https://github.com/informatics-isi-edu/deriva-ml/commit/2190eb5) | `docs(plans): refinement for lookup_lineage design` |
| [`1e82407`](https://github.com/informatics-isi-edu/deriva-ml/commit/1e82407) | `feat(execution): add lookup_lineage with data-flow walk` |
| [`2ef7c3a`](https://github.com/informatics-isi-edu/deriva-ml/commit/2ef7c3a) | `tests(execution): unit + integration tests for lookup_lineage` (released as **v1.32.0** after these four landed direct-to-main, BEFORE the PR rule existed) |
| [`4fab32a`](https://github.com/informatics-isi-edu/deriva-ml/commit/4fab32a) | PR #72 squash-merge: `docs(lineage): user-guide for lookup_lineage; PR convention in CLAUDE.md` (added the deriva-ml PR-required rule + retroactive user-facing docs for v1.32.0) |
| [`84fc140`](https://github.com/informatics-isi-edu/deriva-ml/commit/84fc140) | PR #73 squash-merge: `feat(dataset): add validate_dataset_specs and validate_execution_configuration` (released as **v1.33.0** via post-merge bump) |

**deriva-ml-mcp side (the thin wrappers + resources):**

| Hash | What |
|---|---|
| [`495be20`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/495be20) | `feat(execution): add deriva_ml_get_lineage tool + ml/lineage/{rid} resource` |
| [`b77f3b3`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/b77f3b3) | `feat(dataset): add validate_dataset_specs + validate_execution_configuration tools + dataset/{rid}/spec resource` |
| [`af04eb4`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/af04eb4) | `chore: raise deriva-ml pin to >=1.33.0 for new wrapper methods` |
| [`225c389`](https://github.com/informatics-isi-edu/deriva-ml-mcp/commit/225c389) | Auto-generated bump-version commit (3.2.1 → **v3.3.0**) |

**deriva-ml-skills side (the tier-2 skill update + handoff):**

| Hash | What |
|---|---|
| [`4b0160e`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/4b0160e) | `docs: round 6 refinement + reshape; spawn 3 deriva-ml tasks; queue Round 6b` (the architectural-reframing addendum) |
| [`4b6ab5f`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/4b6ab5f) | `docs: round 6 scope reduction — remove rank_executions` |
| [`f9149b3`](https://github.com/informatics-isi-edu/deriva-ml-skills/commit/f9149b3) | `write-hydra-config: slim validation section to use new validate_* MCP tools` |
| (this commit) | `docs: round 6 handoff close-out — Round 6 ✅ Done` |

**Net effect:** deriva-ml at **v1.33.0** with three new public methods on `DerivaML` (`lookup_lineage`, `validate_dataset_specs`, `validate_execution_configuration`) plus an ADR (ADR-0001) and the new PR-required workflow convention (CLAUDE.md). deriva-ml-mcp at **v3.3.0** with three new MCP tools and two new resources. deriva-ml-skills tier-2 `write-hydra-config` slimmed accordingly.

The architectural insight from this round — "anything walking the deriva-ml domain model belongs in deriva-ml first; deriva-ml-mcp wraps; deriva-ml-skills documents" — was load-bearing and should inform any future tool additions.

## Operating principles established during refinement

These emerged from the interview process and are now load-bearing
for future rounds. Treat them as project conventions when picking
up the work.

### 1. Guide-shaped skills auto-fire; tool-shaped skills are on-demand

Established during Round 1, question 11 (the user's "I want these
skills to always be looking over the shoulder of the ML developer
to guide them" steering).

- **Guide-shaped** skills auto-fire on broad phrasings: lifecycle
  trio (dataset, execution, experiment), discipline skills
  (maintain-experiment-notes, catalog-operations-workflow,
  model-development-workflow). They watch what the user is doing
  and inject framing before mistakes happen.
- **Tool-shaped** skills wait to be explicitly invoked: verification
  (validate-project-setup), troubleshooting (troubleshoot-execution,
  troubleshoot-deriva-errors), environment setup
  (setup-notebook-environment), one-shot operations.

The distinction shapes `disable-model-invocation` flag, description
voice ("ALWAYS use this skill when…" for guides; "Use when…" for
tools), README presentation (separate "user commands" vs
"auto-invoked guides" sections).

### 2. CLAUDE.md is maintainer-only; user-critical content stays in README

CLAUDE.md ships in the source repo but is not packaged into the
installable plugin. End users never see it. The implication: no
end-user-critical content goes in CLAUDE.md. Conventions, gotchas,
and release process belong in CLAUDE.md; what skills exist and how
to use them belongs in README and the skill descriptions/bodies
themselves.

### 3. Each round ships as N independent commits, content-first ordering

Multi-commit rounds (vs single mega-commits) so each step leaves
the repo in a coherent state and can be reverted independently.
Content-first means create the new content before deleting what it
replaces, so cross-references never point at vanished content.

### 4. The DerivaML precedence principle

(Documented in `deriva-ml-context` skill; load-bearing for Round 3.)

Whenever both tier-1 (deriva-skills) and tier-2 (deriva-ml-skills)
could do an operation, tier-2 wins because it preserves the
DerivaML abstractions and provenance:

- Dataset operations over raw row inserts
- Execution lifecycle over generic queries
- Feature CRUD over ad-hoc tables
- Asset operations over raw asset-table CRUD

Round 3's primary deliverable is making this precedence map
explicit in `deriva-ml-context` SKILL.md.

### 5. Architecturally correct surface for content ≠ where MCP "prompts" lives

Established during Round 2, question 1 (the user's "I thought
prompts were meant to be specific and parameterized with context").
The MCP/FastMCP spec describes prompts as user-controlled
parameterized templates. Static reference content has three correct
homes: tool docstrings (per-tool warnings), server `instructions=`
field (cross-cutting cold-start orientation), or RAG-indexed docs
(per-domain depth). Round 2 redistributed two of the four prompts
accordingly; the remaining two await a deriva-mcp-core API addition
(see "Cross-repo asks" below).

## Cross-repo asks raised in parallel

Both raised with the deriva-mcp-core maintainer outside this thread
(per Round 2's option y). Status: in flight, not yet landed.

### Ask 1: `ctx.add_instructions(text)` plugin API

Lets plugins contribute to the FastMCP `instructions=` field that
gets sent to clients at session init. Without it, cold-start
orientation has nowhere to land cleanly outside of prompts. With
it, the remaining two MCP prompts (`_CONCEPTS_GUIDE`,
`_GETTING_STARTED_GUIDE`) can move to the architecturally correct
home and the prompt mechanism gets freed for its intended use
(parameterized templates).

When this lands, follow-up round (~30 min): migrate the two
remaining prompts; delete the prompt mechanism's content side
entirely; the registration code stays available for any future
parameterized-template additions.

### Ask 2: `exclude_paths=[...]` parameter on the GitHub crawler

Lets RAG sources widen their `path_prefix` (e.g., to `""` for
repo-root coverage) while excluding specific files (`CLAUDE.md`,
`.pytest_cache/README.md`). Without it, widening the prefix
indexes some maintainer-only files alongside the intended ones.

When this lands, follow-up round (~15 min): tighten the RAG source
prefixes to drop the indexed maintainer files (currently mild
noise: deriva-ml/CLAUDE.md, deriva-ml-mcp/CLAUDE.md,
deriva-ml-mcp/docs/scratch/*.md).

## Round 3 (✅ Done)

Reshaped during refinement from "add a precedence map table" to
"replace the steering principle with an inheritance-with-override
rule." See [Round 3 refinement addendum](2026-05-02-tier-2-audit-cleanup-plan-round-3-refinement.md)
for the 9 design questions resolved and the 5-commit execution
shape, and [ADR-0001](../../adr/0001-precedence-as-rule-not-table.md)
for the rule-vs-table decision. Commit hashes are in the "Round 3
commits" section above.

## Round 4 (✅ Done)

Reshaped during refinement from "drop always-on weight from ~1,234
to <500 lines" (anchored on an out-of-date count that mixed
auto-fire and slash-only skills) to "re-target on actual auto-fire
weight; flip slash-only candidates; slim the keepers using tier-1's
reference-pattern." See [Round 4 refinement addendum](2026-05-02-tier-2-audit-cleanup-plan-round-4-refinement.md)
for the 6 design questions resolved and the 5-commit execution
shape. Commit hashes are in the "Round 4 commits" section above.

## Round 5 (✅ Done)

Reshaped during refinement from "decide where 3 borderline skills
belong" to a sharper set: `use-annotation-builders` moves to tier-1
(clear case, parent plan's recommendation validated); `coding-guidelines`
is misnamed — its content is mostly project-bootstrap-and-operations,
not generic Python — so it gets distributed across 3 skills (one new
`setup-derivaml-project` skill, plus content into
`setup-notebook-environment` and `model-development-workflow`) and
deleted; `create-web-app` stays in tier-2 with a small description
reframe. See [Round 5 refinement addendum](2026-05-02-tier-2-audit-cleanup-plan-round-5-refinement.md)
for the 8 design questions resolved and the per-atom distribution
table. Commit hashes are in the "Round 5 commits" section above.

## Round 6 (✅ Done)

Reshaped twice during execution. The architectural reframing (mid-grilling) put the canonical methods in deriva-ml first with thin MCP wrappers in deriva-ml-mcp; the scope reduction (post-`lookup_lineage`) dropped `rank_executions` after a use-case re-examination found its motivation much weaker than `lookup_lineage`'s. The final shipped scope: 2 deriva-ml methods (`lookup_lineage`, `validate_dataset_specs`+`validate_execution_configuration`), 3 MCP tool wrappers, 2 MCP resources, 1 tier-2 skill update, plus a new PR-required workflow convention added to deriva-ml/CLAUDE.md.

See [Round 6 refinement addendum](2026-05-02-tier-2-audit-cleanup-plan-round-6-refinement.md) for the full reshape rationale and scope-reduction analysis. Commit hashes are in the "Round 6 commits" section above.

**Round 6b** was the deriva-ml-mcp wrapper round, executed in this same session as commits 1-3 of the deriva-ml-mcp side. There is no separate Round 6b deliverable; the wrapper work is the back half of Round 6.

## To resume in a new session

The 2026-05-02 audit cleanup plan is **complete** — all six rounds done. There is no in-flight Round 6 work to resume; this section now serves as a starting point for future work.

1. **Read this handoff first** for the cross-rounds picture, then the per-round refinement addenda (rounds 1-6) for the design history of any specific round.
2. **Verify all four touched repos are clean** and on `main`:
   ```
   cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git status
   cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp && git status
   cd /Users/carl/GitHub/DerivaML/deriva-skills && git status
   cd /Users/carl/GitHub/DerivaML/deriva-ml && git status
   ```
3. **Check whether the cross-repo asks raised in Round 2 have landed** — if either API addition (`add_instructions` or `exclude_paths`) is now available in deriva-mcp-core, those become unblocked follow-up work (independent of any cleanup-plan rounds).
4. **For any new round of work** (a fresh audit, a feature addition, a refactor):
   - Run a refinement interview following the 6-12 question pattern established by Rounds 1-6: walk down the design tree one question at a time, recommended-answer-with-each-question, prefer codebase exploration over questions when discoverable.
   - Save the refinement as a new addendum following the `YYYY-MM-DD-<short-name>-refinement.md` convention.
   - Honor the operating principles in the section above (especially: PR-required for deriva-ml; canonical implementations in deriva-ml with thin wrappers in deriva-ml-mcp; ADR for hard-to-reverse decisions).

## Current state of touched repos (final, post-Round-6)

| Repo | Branch | Latest commit | Latest tag |
|---|---|---|---|
| deriva-ml-skills | main | (this commit closes out Round 6) | (skill plugin; tag-triggered release on bump-version) |
| deriva-ml-mcp | main | 225c389 (Round 6b: 3 wrappers + 2 resources + pin bump + minor) | **v3.3.0** |
| deriva-skills (tier-1) | main | c0f3649 (touched in Round 5) | **v1.2.0** |
| deriva-ml | main | 84fc140 (PR #73 squash; Round 6 second deriva-ml feature) | **v1.33.0** |
| deriva-mcp-core | (separate maintainer) | (untouched here) | (cross-repo asks raised separately, not yet landed) |

All four touched repos have clean working trees as of this handoff.
