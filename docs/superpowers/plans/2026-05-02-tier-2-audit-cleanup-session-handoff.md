# Session handoff — tier-2 audit cleanup (2026-05-02)

This is a session-state-and-interactions document. It captures the
full context of an in-progress multi-round refactor so the work can
be resumed in a future session without losing the design rationale,
the cross-repo asks raised in parallel, or the operating principles
that emerged during the refinement interviews.

## TL;DR

A two-part audit (tier-2 skills + MCP surface) of the DerivaML
domain layer produced a six-round cleanup plan. Rounds 1 and 2 are
complete; rounds 3–6 are designed but not yet executed.

| Round | Status | Effort | Description |
|---|---|---|---|
| 1 | ✅ Done | ~75 min | Tier-2 mechanical cleanup (deleted 2 routers + 1 broken skill; added experiment-lifecycle and validate-project-setup skills; fixed 11 stale tier-1 references; brought lifecycle trio to uniform behavior) |
| 2 | ✅ Done | ~90 min | MCP prompt restructure (deleted 2 mis-shaped prompts + redistributed content to docstrings; widened RAG indexing to top-level docs; bumped deriva-ml-mcp v3.1.1 → v3.2.0) |
| 3 | ⏳ Designed; not started | ~1 hr | Precedence map + ML-extension philosophy in `deriva-ml-context` |
| 4 | ⏳ Drafted | ~1-2 hr | Tier-2 always-on weight reduction (~1234 → <500 lines) |
| 5 | ⏳ Drafted | ~2-3 hr | Tier placement decisions (coding-guidelines / use-annotation-builders / create-web-app) |
| 6 | ⏳ Drafted | ~2-4 hr | MCP tool and resource additions (get_lineage, rank_executions, validate_dataset_spec) |

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

## Round 3 (designed; not refined or executed)

**Scope:** add the explicit precedence map to `deriva-ml-context`
SKILL.md; add the "DerivaML extends data-centricity with
reproducibility and provenance" framing; audit each tier-2 skill
body for places where it currently says "see also `/deriva:<skill>`"
and reframe as directional precedence; cross-reference tier-1
`semantic-awareness` from the relevant tier-2 skills (`new-model`,
`create-feature`, `dataset-lifecycle`) so the LLM applies the
discipline to ML entities too.

**Estimated effort:** ~30-45 min for the additions + ~30 min for
the audit pass.

**Dependencies:** Round 1 (cleanup) is done; Round 2 (the
deriva-ml-mcp surface clarification) is done. No upstream
dependencies remain.

**To start:** open the parent plan document and the Round 1
refinement addendum for context, then begin a new refinement
interview for Round 3 following the 12-question pattern from
Rounds 1-2.

## Round 4 (drafted; not refined or executed)

**Scope:** apply tier-1's slimming patterns to the tier-2 always-on
layer. Target: drop tier-2 always-on weight from ~1,234 to under
500 lines. Slim `api-naming-conventions`, `generate-descriptions`,
`generate-scripts`, `ml-data-engineering`, `dataset-lifecycle`,
`create-feature`. Same skill-creator-style patterns tier-1's recent
work used (the slimmed `semantic-awareness` 170 → 31 lines is the
canonical model).

**Estimated effort:** ~1-2 hr.

**Dependencies:** Round 3 should ship first so the precedence
framing in `deriva-ml-context` is in place before slimming related
skills.

## Round 5 (drafted; not refined or executed)

**Scope:** decide where three borderline skills belong.

- `coding-guidelines` (currently tier-2; generic Python project
  setup; arguably tier-1 or generic)
- `use-annotation-builders` (currently tier-2; pure Chaise display
  annotations; clearly tier-1)
- `create-web-app` (currently tier-2; mixed — app-server piece is
  tier-2, visualization patterns are more generic)

**Estimated effort:** ~2-3 hr (discussion + 1 hr edits per move).

**Dependencies:** Rounds 1, 3 should be done so the tier-1/tier-2
boundary is clearly understood.

## Round 6 (drafted; not refined or executed)

**Scope:** add three missing MCP tools and three resources that
close real workflow gaps identified in the audit.

- `deriva_ml_get_lineage(rid, depth=2)` — returns the full
  provenance chain for any artifact
- `deriva_ml_rank_executions(workflow_rid, by_feature, top_n)` —
  server-side aggregation for the comparison pattern
- `deriva_ml_validate_dataset_spec(specs=[...])` — round-trips
  against the catalog to verify (RID, version) pairs
- `deriva-ml://lineage/{rid}` resource form
- `deriva-ml://executions?status={status}` filtered execution list
- `deriva-ml://dataset/{rid}/spec` resource form of get_dataset_spec

**Estimated effort:** ~2-4 hr.

**Dependencies:** Round 2 is done; the deriva-ml-mcp surface is
in v3.2.0 baseline. Round 6 would bump again.

## To resume in a new session

1. **Read this handoff first**, then the three plan documents in
   the order listed at the top.
2. **Verify both repos are clean** and on `main`:
   ```
   cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git status
   cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp && git status
   ```
3. **Check whether the cross-repo asks have landed** — if either
   API addition (`add_instructions` or `exclude_paths`) is now
   available in deriva-mcp-core, the corresponding follow-up round
   becomes possible (and architecturally preferred to the current
   Round 3-6 sequencing).
4. **Pick the next round** — Round 3 is the natural next step
   (highest-value LLM-routing change; small effort).
5. **Run a refinement interview** following the 12-question pattern
   from Rounds 1-2: walk down the design tree one question at a
   time, recommended-answer-with-each-question, prefer codebase
   exploration over questions when discoverable.
6. **Save the refinement as an addendum** to this directory using
   the same naming convention:
   `2026-05-02-tier-2-audit-cleanup-plan-round-N-refinement.md`.
7. **Execute as the planned commits**, content-first ordering,
   each independently revertable. Update this handoff doc at the
   end of the round.

## Current state of touched repos

| Repo | Branch | Latest commit | Latest tag |
|---|---|---|---|
| deriva-ml-skills | main | 7df48e9 | (skill plugin; tag-triggered release on bump-version) |
| deriva-ml-mcp | main | 655aac7 | v3.2.0 |
| deriva-skills (tier-1) | main | (untouched in Rounds 1-2) | (last touched in earlier session work documented in plans for that repo) |
| deriva-mcp-core | (separate maintainer) | (untouched here) | (cross-repo asks raised separately) |

Both touched repos have clean working trees as of this handoff.
