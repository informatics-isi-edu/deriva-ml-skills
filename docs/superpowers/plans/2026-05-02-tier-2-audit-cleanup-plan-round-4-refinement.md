# Round 4 refinement — addendum to 2026-05-02 plan

This addendum records the refinement interview for Round 4 of the
[2026-05-02 tier-2 audit cleanup plan](2026-05-02-tier-2-audit-cleanup-plan.md).
The interview reshaped Round 4 from "drop tier-2 always-on weight
from ~1,234 to under 500 lines" to "re-target on actual auto-fire
weight; flip the slash-only candidates; slim the keepers using
tier-1's reference-pattern."

Six design questions resolved.

## Audit findings revisited

The parent plan's framing ("drop always-on weight from ~1,234 to
<500") was anchored on an out-of-date count and included some skills
in its slimming list that don't actually pay always-on cost. A fresh
audit at Round 4 start showed:

- Today's actual auto-fire weight (skills without
  `disable-model-invocation: true`): **1,994 lines across 10 skills**.
- Four of the parent plan's named slimming targets
  (`api-naming-conventions`, `generate-scripts`,
  `ml-data-engineering`, `catalog-operations-workflow`) are already
  `disable-model-invocation: true` and pay zero always-on cost.
  Slimming them is a separate exercise (cleaner reference content
  is its own win) but not part of "drop always-on weight."
- The 10 actual auto-fire skills divide into three guide-shaped
  lifecycles (Dataset, Execution, Experiment), three discipline
  skills (`deriva-ml-context`, `generate-descriptions`,
  `maintain-experiment-notes`), one specific-task skill
  (`compare-model-runs`), and three orientation/operation skills
  (`help`, `browse-erd`, `create-feature`).

The user clarified the steering principle for what earns an
always-on slot:

> **Round 4 always-on rule:** A skill earns its always-on slot if
> it shapes the user's interaction with deriva-ml — looking over
> the shoulder of the ML developer, training them and supporting
> frictionless interaction. Always-on is for the disciplines and
> lifecycles that should be in context the LLM operates from, not
> for specific operations the user might do once.

This is a positive reframing of the Round 1 operating principle
("guide-shaped skills auto-fire; tool-shaped skills are on-demand").
Always-on isn't just permitted for guides — it's *required* for
them, because the role of the always-on layer is to **train** the
user and **support frictionless interaction**.

## Resolved decisions

| # | Question | Resolution |
|---|---|---|
| 1 | Stay with parent plan's literal target list, re-target on actual auto-fire weight, or hybrid? | **Re-target.** Drop the four already-slash-only skills from the slimming list. Add the auto-fire skills the plan didn't name. Apply tier-1's `references/` slim-pattern as the template. Flag-flip changes (changing `disable-model-invocation`) ARE in scope. |
| 2 | Categorization of the 10 auto-fire skills under the rule | **3 flip to slash-only:** `compare-model-runs` (specific task), `help` (canonical user-invocable), `browse-erd` (one specific operation). **7 keepers earn always-on slot:** `deriva-ml-context`, `dataset-lifecycle`, `execution-lifecycle`, `experiment-lifecycle`, `create-feature`, `generate-descriptions`, `maintain-experiment-notes`. **Target:** ~800 lines (not <500). |
| 3 | Slimming approach: case-by-case, mechanical template, or triage by current size? | **Triage by current size.** The four big skills (`dataset-lifecycle` 434, `create-feature` 403, `execution-lifecycle` 185, `generate-descriptions` 169) get full slim. The three smaller ones (`deriva-ml-context` 160, `experiment-lifecycle` 149, `maintain-experiment-notes` 118) get light-touch only. |
| 4 | Commit shape: 6 commits, 4 commits, or 5 commits? | **5 commits.** (1) flag flips, (2) `dataset-lifecycle` heavy slim, (3) `create-feature` heavy slim, (4) `execution-lifecycle` + `generate-descriptions` slims, (5) light-touch trio + handoff update. |
| 5 | Verification gate against over-slimming? | **Per-slim diff preview.** Show full new SKILL.md + new references file(s) before each heavy-slim commit lands; user spots anything that should have stayed in the body. Cheap check; over-slimming is the real risk. |
| 6 | Explicit "what stays in the body" rule per slim? | **Yes, codified.** Body contains: (1) trigger context, (2) discipline / always-relevant prior, (3) phase framing for lifecycle skills, (4) pointers into references. References get: per-entity templates, worked examples, decision matrices longer than ~5 rows, mechanics for commit-time operations, multi-step procedures with code. |

## Operating principles (carried forward from prior rounds)

- **Guide-shaped skills auto-fire; tool-shaped skills are
  on-demand.** Round 4 sharpens this with the positive framing
  above ("always-on is required for guides, not just permitted").
- **Each round ships as N independent commits, content-first
  ordering.**
- **The inheritance-with-override rule from ADR-0001** stays
  load-bearing: when slimming a skill, references that point at
  tier-1 surfaces remain inheritance-shaped, not override-shaped.

## Categorization table

| Skill | Lines today | Round 4 action | Lines after | Notes |
|---|---|---|---|---|
| `compare-model-runs` | 224 | Flip to slash-only | 0 (out of always-on) | Specific task — rank executions by metric. Not a discipline. User invokes it when they have runs to compare. |
| `help` | 91 | Flip to slash-only | 0 (out of always-on) | Canonical user-invocable — `/deriva-ml:help` for orientation. |
| `browse-erd` | 61 | Flip to slash-only | 0 (out of always-on) | One specific operation — launches an ERD viewer. |
| `deriva-ml-context` | 160 | Light touch | ~150 | Plugin context (post-Round-3); inheritance rule lives here. Already trimmed; only opportunistic compression. |
| `dataset-lifecycle` | 434 | Heavy slim | ~200 | Has 4 references and 2 scripts already. Move curated-subsets workflow, dataset-types depth, BDBag mechanics, denormalize details to references. |
| `execution-lifecycle` | 185 | Medium slim | ~100 | Move per-status state-machine details, upload-discipline depth to references. |
| `experiment-lifecycle` | 149 | Light touch | ~140 | New skill from Round 1; already at right size. Opportunistic only. |
| `create-feature` | 403 | Heavy slim | ~200 | Has 3 references already. Move value-selector mechanics, feature-discovery deep-dive, feature-type matrix to references. |
| `generate-descriptions` | 169 | Heavy slim | ~50 | Move per-entity templates (Dataset, Workflow, Execution, Feature, Asset, Experiment) to `references/templates.md`. Tier-1's identical pattern. |
| `maintain-experiment-notes` | 118 | Light touch | ~115 | Body is already lean; description is heavy but the description is part of routing logic and stays. |

**Net before:** 1,994 lines auto-fire weight.
**Net after:** ~955 lines auto-fire weight (376 from flag flips + 663 from slim of seven keepers, allowing some headroom in the heavy-slim estimates).
**Reduction:** ~52%, roughly matching tier-1's 58% reduction outcome.

## Execution shape

Five commits in deriva-ml-skills.

### Commit 1

`tier-2: flip 3 skills to slash-only (drop 376 lines from auto-fire weight)`

Mechanical: change `disable-model-invocation` to `true` in
`compare-model-runs`, `help`, `browse-erd` frontmatter. Update
the README skill-organization section if it splits the auto-fire
vs slash-only lists. Independent of any content slim — ships
first because lowest-risk, highest-leverage.

### Commit 2

`dataset-lifecycle: slim auto-fire body; move depth to references`

Heavy slim of the 434-line skill. Existing references directory
expands; new references file(s) carry the depth. Body keeps phase
framing + discipline guards + pointers. Show diff preview before
landing.

### Commit 3

`create-feature: slim auto-fire body; move depth to references`

Same pattern as commit 2 for the 403-line skill. Show diff
preview before landing.

### Commit 4

`execution-lifecycle, generate-descriptions: slim auto-fire bodies`

Bundles two smaller slims. `execution-lifecycle` 185 → ~100;
`generate-descriptions` 169 → ~50 (matches tier-1's identical
pattern). Show diff preview before landing.

### Commit 5

`tier-2: opportunistic compression on light-touch trio + round 4 handoff`

`deriva-ml-context`, `experiment-lifecycle`,
`maintain-experiment-notes` get any easy compression wins (no
forced restructuring). Update session-handoff.md to mark Round 4
✅ Done with commit hashes.

## Estimated effort

- Commit 1: ~5 min (mechanical flag flips).
- Commit 2: ~30-45 min (dataset-lifecycle slim + diff preview).
- Commit 3: ~30-45 min (create-feature slim + diff preview).
- Commit 4: ~25-35 min (two smaller slims + diff preview).
- Commit 5: ~15-20 min (light touch + handoff).

**Total:** ~2 hours, matching the parent plan's estimate.

## Pickup notes

When this round ships:

- Update the parent session-handoff document
  (`2026-05-02-tier-2-audit-cleanup-session-handoff.md`) to mark
  Round 4 ✅ Done; record the five commits' hashes.
- Round 5 (tier placement decisions for `coding-guidelines`,
  `use-annotation-builders`, `create-web-app`) becomes the natural
  next round.
- Note for Round 5: with Round 4 having sharpened the
  always-on-vs-slash-only distinction, the tier placement
  decisions in Round 5 inherit a clearer mental model — the
  question becomes "which plugin AND which invocation mode?" not
  just "which plugin?".
