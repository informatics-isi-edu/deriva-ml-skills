# Round 6 refinement — addendum to 2026-05-02 plan

This addendum records the refinement interview for Round 6 of the
[2026-05-02 tier-2 audit cleanup plan](2026-05-02-tier-2-audit-cleanup-plan.md).
Round 6 was reshaped twice during execution:

**First reshape (mid-grilling, architectural):** The original framing
("add three tools and three resources to deriva-ml-mcp") was
challenged by a side-question ("should this go in deriva-ml-mcp, or
even deriva-ml?"). The resulting reframing split Round 6 into a
**prerequisite phase** (deriva-ml methods, designed and shipped via
separate spawned grill-with-docs tasks) and a **wrapper phase** (the
original deriva-ml-mcp work, scoped down to thin wrappers +
resources + tier-2 skill updates, blocked on the prerequisite phase).

**Second reshape (post-`lookup_lineage`, scope reduction):** After
`lookup_lineage` shipped (deriva-ml v1.32.0), a use-case re-examination
of the remaining two tools surfaced that `rank_executions` had a much
weaker motivation than `lookup_lineage`. The 3-step manual pattern it
would replace (`list_executions(sort=True, limit=N)` →
`list_feature_values(execution_rids=[...])` → Python sort) is only 2
round-trips and ~5-10 lines of caller code, well within what the LLM
handles cleanly via the existing `compare-model-runs` skill body. By
contrast, `lookup_lineage` was replacing 5-15 round-trips through a
recursive parent-chain walk, a real ergonomic burden. The audit had
grouped the three tools together, but on closer examination only two
genuinely earn their cost. **`rank_executions` was removed from
Round 6 scope.** See the "Scope reduction" section below for the full
rationale.

Six grilling questions resolved before the first reframing; one
high-leverage architectural question after; one scope-reduction
decision after `lookup_lineage` shipped.

## Audit findings revisited

The parent plan named three missing MCP tools that close real
workflow gaps identified in the audit:

- `deriva_ml_get_lineage(rid, depth=2)` — provenance traversal in
  one call. **Shipped as `lookup_lineage` in deriva-ml v1.32.0.**
- `deriva_ml_rank_executions(workflow_rid, by_feature, top_n=10,
  order="desc")` — server-side aggregation for the top-N pattern
  that `compare-model-runs` walks through manually. **Removed from
  scope after re-examination — see "Scope reduction" below.**
- `deriva_ml_validate_dataset_spec(specs=[{rid, version}])` —
  round-trips against the catalog to verify each (RID, version)
  pair refers to an existing dataset version. **Pending implementation
  via spawned task.**

Plus three corresponding read-only resources (URI-addressable
forms that wrap the tool logic).

The grilling started by walking through `get_lineage`'s design —
input RID type (Q4-A: auto-detect), `depth` parameter semantics
(Q4-B: unbounded by default with mandatory cycle avoidance) — when
the user surfaced the architectural side-question that reshaped
the round.

## Scope reduction: `rank_executions` removed

After `lookup_lineage` shipped (deriva-ml v1.32.0, commits
`301d0ac` → `2ef7c3a`, plus PR #72 for documentation), a
use-case re-examination of the remaining two tools surfaced that
`rank_executions` had a much weaker motivation than the audit
implied. The decision was to remove it from Round 6 scope.

**The motivation comparison:**

| Question | `lookup_lineage` motivation | `rank_executions` motivation |
|---|---|---|
| What does the manual version cost? | 5-15 round-trips, complex mental walk through parent chain, easy to get wrong | 2 round-trips + 5-10 lines of Python aggregation |
| Is the manual version error-prone? | Yes — tree walk, type-detection, recursion | No — straightforward groupby + sort |
| Is the operation domain-specific? | Yes — lineage walks DerivaML's graph structure | Mostly — but the aggregation is generic pandas/Python |
| Does the LLM stumble on this regularly? | Yes — every "what produced this?" was a many-step recipe | Less so — the LLM writes the inline aggregation easily |
| Is there a clear "wrong" alternative? | Yes — manual `lookup_execution` + parent traversal misses things | Not really — the existing 3-step pattern works |

**The use-case examination:** The `compare-model-runs` skill names
five user-facing questions. They cluster into three shapes:

- **Top-N from a workflow** ("which of my last N runs got the best
  F1?", "performance regression check") — the only shape that's
  genuinely a *rank* operation.
- **Show-me-everything** ("show me the recent training results") —
  not a rank; just a list. Already served by the existing
  `list_executions(workflow_rid=..., sort=True, limit=N)` +
  `list_feature_values(execution_rids=[...])` pair.
- **Hand-picked comparison** ("compare accuracy across these
  executions") — caller already has the RIDs; just needs the values,
  not a rank. Also already served.

Only the top-N shape is genuinely a rank question, and that shape is
served by the existing 3-step pattern in well-documented form. The
LLM follows it cleanly via the `compare-model-runs` skill body.

**The cost-benefit:** adding `rank_executions` would have created a
new public method to maintain across the deriva-ml + deriva-ml-mcp
+ tier-2-skill chain, in exchange for saving ~5 lines of caller
code. The audit had identified a gap that's largely a documentation
success story, not a real ergonomic burden.

**Skill-side consequence:** the tier-2 `compare-model-runs` skill
stays as-is. There is no slim opportunity for Phase 2A in Round 6b;
the skill's existing 3-step walkthrough remains the canonical
pattern. (If a future audit identifies real LLM stumbling on the
top-N pattern, `rank_executions` can be revisited then; the design
work would not be expensive.)

**Round 6 final scope:**

| Tool | Status |
|---|---|
| `lookup_lineage` | ✅ Shipped in deriva-ml v1.32.0; docs in PR #72 |
| `rank_executions` | ❌ Removed from scope (see above) |
| `validate_dataset_spec` | ⏳ Pending — spawned task to design + implement |

Round 6b's deriva-ml-mcp wrapper work also shrinks: instead of
three new MCP tools + three resources, it ships two tools
(`deriva_ml_get_lineage`, `deriva_ml_validate_dataset_spec`) and
two resources (`deriva://catalog/{h}/{c}/ml/lineage/{rid}`,
`deriva://catalog/{h}/{c}/ml/dataset/{rid}/spec`). The
`deriva://catalog/{h}/{c}/ml/executions?status={status}` resource
that was originally paired with `rank_executions` is also dropped
from scope — its motivation was to filter the execution list for
"show me what's failed," but that filter is already supported by
the existing `deriva_ml_list_executions(status="Failed")` parameter.

## The architectural reframing (the load-bearing decision)

**The side question:** "Is this a function that should go into MCP,
or even deriva-ml? Consider efficiency and architecture. Seems
that having this be available outside of skills might be good."

**The realization:** every existing `deriva_ml_*` MCP tool wraps a
deriva-ml Python method; none of them is the canonical
implementation of its operation. The MCP tool layer is a transport
veneer; the canonical surface for the five DerivaML abstractions
(Dataset, Workflow, Execution, Feature, Asset) is the deriva-ml
Python library, not the MCP server.

The three tools the parent plan named are all domain operations
that walk the deriva-ml graph:

- **Lineage** is the parent-execution chain that DerivaML records.
- **Ranking executions by feature value** is a Feature + Execution
  composite operation.
- **Validating dataset specs** is a question about the Dataset
  domain object's version graph.

If these methods only exist in deriva-ml-mcp, then:

1. **Reach is gated.** Python scripts, notebooks, the
   `deriva-ml-apps` server, and any non-MCP client can't use them
   without re-implementing the walk or — worse — calling MCP from
   Python (architectural inversion).

2. **Efficiency is wrong for the typical case.** The headline use
   case for `get_lineage` ("I'm debugging why this prediction looks
   off; let me trace its provenance") is interactive Python, not a
   chat conversation. Forcing every interactive session to round-
   trip through MCP serialization is needless cost.

3. **The inheritance-with-override rule from ADR-0001 has nothing
   to point at on the Python plane.** The rule says: if a deriva-ml
   surface exists for an operation, prefer it on all three planes
   (skills, MCP, Python API). For that rule to mean anything for
   these three operations, the operation has to exist in the
   Python API.

**The decision:** the canonical implementation of all three
operations lives in the deriva-ml Python library. The
deriva-ml-mcp tools and resources become thin wrappers that call
into deriva-ml. Tier-2 skills mention both surfaces (Python method
for scripts/notebooks; MCP tool for chat conversations).

This is consistent with how every existing `deriva_ml_*` MCP tool
already works — the tools wrap library methods. The parent plan's
framing was an oversight; it placed the new tools at the MCP layer
because that's where the audit identified the gap, but the
*correct* place for the underlying operation is the library.

## Resolved decisions (before the reframing)

| # | Question | Resolution |
|---|---|---|
| 1 | Scope: all 6 in one round, or staged? | All 6 in one round. The parent plan's framing is sound; resources mirror tools per the established convention (all 11 existing resources mirror existing tools). |
| 2 | Commit shape: per-tool, per-layer, or single mega-commit? | Per-tool commits — each tool is a separate design (response shape, traversal, error contract); reverting one without the others should be possible. |
| 3 | Tier-2 skill updates: scope? | Update only `compare-model-runs` (heavy slim opportunity in Phase 2A) and `write-hydra-config` (validation section). Skip `model-development-workflow` (already short pointer); defer cross-cutting "lineage skill" idea — the audit didn't find a place where users currently walk through manual lineage. |
| 4-A | `get_lineage` input RID type | Auto-detect (single `rid` parameter). Forcing the caller to type `rid_type=` defeats half the ergonomic win; matches existing tool-design philosophy. |
| 4-B | `get_lineage` `depth` semantics | Unbounded walk by default (lineage is infrequent and deliberate; not a hot path); optional `depth` cap; mandatory cycle avoidance with explicit reporting (`cycle_detected`, `walked_complete`, `executions_visited` in response). |
| 4-C | `get_lineage` response shape | (Resolved before reframing — design was tree-with-summaries; carries forward into the spawned task as a settled decision.) |

## Resolved decisions (after the reframing)

| # | Question | Resolution |
|---|---|---|
| α | Where does the canonical implementation live? | **deriva-ml Python library**, not deriva-ml-mcp. The MCP wrappers are secondary deliverables. The reframing applies symmetrically to all three tools (`get_lineage`, `rank_executions`, `validate_dataset_spec`) — each is a deriva-ml domain operation, not an MCP transport operation. |
| β | How to execute the deriva-ml work? | **Three spawned `/grill-with-docs` tasks**, one per method. Each is substantive enough to deserve focused grilling against the deriva-ml codebase; each can be picked up independently when the user has time; they don't block each other. This session's role flips from "design and implement Round 6" to "carve Round 6 into the right shape and stage it for execution." |
| γ | What happens to the deriva-ml-mcp wrapper work? | Deferred to a **follow-up wrapper round** (call it Round 6b) that runs after all three deriva-ml methods land. The wrapper round is much smaller per the original framing — thin `@ctx.tool` registrations + the three resources + tier-2 skill updates. With the heavy implementation done in deriva-ml, the wrapper round becomes ~1-2 hr instead of 2-4 hr. |

## Spawned tasks

Three tasks queued via `mcp__ccd_session__spawn_task`. Each carries:

- A "what the function does" plain-English explanation grounded in a concrete user scenario.
- A "decisions already settled" section listing the resolutions from this refinement (so the spawned grilling doesn't re-litigate them).
- A "what to grill" section listing the open design questions specific to that function — placement in the codebase, signature, return type, implementation strategy, edge cases, naming, test strategy.
- A "deliverable" section: implement + test + bump deriva-ml minor + push.
- A "coordination with deriva-ml-skills Round 6" section pointing at the wrapper-round work that comes next.

The three tasks:

1. **`get_lineage`** — ✅ shipped as `lookup_lineage` in deriva-ml v1.32.0 (commits `301d0ac` → `2ef7c3a`). Documentation landed in PR #72 (commit `4fab32a`). Auto-detect RID type; unbounded walk with cycle avoidance; data-flow parents only (per ADR-0001 in deriva-ml). Most-grilled of the three; the headline tool.
2. **`rank_executions`** — ❌ removed from scope (see "Scope reduction" above). The 3-step manual pattern in `compare-model-runs` Phase 2A is well-served by existing tools; the convenience win didn't earn the maintenance cost across three repos.
3. **`validate_dataset_spec`** — ⏳ pending. Bulk pre-flight validation of `(RID, version)` pairs from Hydra-zen configs. Replaces per-RID `get_entities` loops in `write-hydra-config`. Spawned task to design + implement.

## Operating principles confirmed

- **Architectural fit beats convenient placement.** The parent plan placed the new tools at the MCP layer because that's where the audit identified the gap (the LLM walks around the missing surface every time). The grilling found the right placement is one layer deeper — at the library that owns the data model. The audit's finding was correct (the gap exists); the fix's location was off by one.

- **The inheritance-with-override rule (ADR-0001) is operational, not just documentation.** When a refinement reveals that a planned MCP-only addition would leave the Python plane unable to honor the rule, that's a signal to push the implementation down a layer. The rule did real work in this round — it's why the reframing happened at all.

- **Spawning separate tasks for substantive design work is honest about cost.** Each method is a real design exercise (signature, return shape, edge cases, tests). Trying to design all three in this session would have produced rushed designs; spawning them as separate `/grill-with-docs` tasks lets each get the attention it warrants.

- **Round 6 isn't done when this session ends.** Only the *design staging* is done. The actual code lands in the spawned tasks; the deriva-ml-mcp wrapper work waits for those to land, then runs as Round 6b.

## Pickup notes

When this round ships fully:

- `lookup_lineage` is done in deriva-ml (v1.32.0); docs in PR #72 (merged).
- `validate_dataset_spec` lands via its spawned task (next).
- A follow-up Round 6b runs in deriva-ml-skills + deriva-ml-mcp:
  - Add two thin `deriva_ml_*` MCP tool wrappers in deriva-ml-mcp (`deriva_ml_get_lineage`, `deriva_ml_validate_dataset_spec`).
  - Add two corresponding resources (`deriva://catalog/{h}/{c}/ml/lineage/{rid}`, `deriva://catalog/{h}/{c}/ml/dataset/{rid}/spec`).
  - Bump deriva-ml-mcp (likely v3.2.1 → v3.3.0 since adding new tools/resources).
  - Slim tier-2 `write-hydra-config` validation section to use the new validate-spec tool. (`compare-model-runs` Phase 2A stays as-is per the scope reduction.)
  - Update the session-handoff to mark Round 6 ✅ Done.

The cross-repo asks raised in Round 2 (`add_instructions`, `exclude_paths` in deriva-mcp-core) remain in flight; neither has landed. Round 6b doesn't depend on either.

## Estimated effort (revised)

- **This session (refinement + task spawning):** ~30 min.
- **Three spawned `/grill-with-docs` tasks:** ~2-4 hr each (refinement + implementation + tests + version bump). Total ~6-12 hr across the three, parallelizable.
- **Round 6b wrapper round (after all three land):** ~1-2 hr. Smaller than the parent plan's 2-4 hr estimate because the heavy implementation work moved upstream.

**Total revised effort: ~7-14 hr (vs. parent plan's 2-4 hr).** The increase reflects the architectural correction — building three operations correctly across two layers takes more total work than building them sloppily at one layer, but the result is better placed and reaches more clients.
