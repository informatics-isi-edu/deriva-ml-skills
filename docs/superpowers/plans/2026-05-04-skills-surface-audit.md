# Skills surface audit — 2026-05-04

Final-pass audit of deriva-ml-skills (27 tier-2 skills + their
references) using the `/grill-with-docs` skill in caveman mode.
Parallel structure to the deriva-ml-mcp surface audit
(`../../deriva-ml-mcp/docs/superpowers/plans/2026-05-04-mcp-surface-audit.md`).

Four lenses applied, same shape as the MCP audit but reshaped for skills:

1. **ML developer perspective** — curator / catalog evolver / model dev
2. **Direct-invocation vs auto-fire vs reference-load** — does each
   skill earn its discovery surface?
3. **Maintainability** — per-skill size, cross-reference graph,
   drift detection
4. **Pull-up to always-on (or pull-down to references)** — placement
   audit, parallel to the MCP audit's "pull-down to deriva-ml" lens

## Inventory baseline

- **27 skills total**
- **7 auto-fire** (881 lines): `deriva-ml-context` (154), `dataset-lifecycle` (129), `execution-lifecycle` (107), `experiment-lifecycle` (139), `create-feature` (174), `maintain-experiment-notes` (114), `generate-descriptions` (64)
- **20 slash-only** (3977 lines): user-invocable surfaces
- **References:** 8263 lines across 14 skills (loaded only when skill body points at them)
- **Cross-reference graph:** 67 intra-tier `/deriva-ml:` refs + 39 tier-1 `/deriva:` refs
- **Round 6 tool surfacing:** 5 skills mention the new tools; 8 still document old manual patterns (overlap; those are the discovery-surface targets Round 6c hit)

---

## Decisions (rolling)

### L1 (ML developer)

#### Q1.1 — curator coverage: complete

Mapped curator workflow against skill coverage. Every step (load
→ asset table → tag → feature → values → curate → version →
document) is owned by a fitting skill. The only "gaps" are
either tier-1 territory (correct per ADR-0001) or template-repo
concerns out of skill scope.

`work-with-assets` skill size question (79 lines, slash-only)
deferred to L2.

#### Q1.2 — catalog-evolver coverage: adequate

Most of this persona's workflow is tier-1 territory (per ADR-0001).
The deriva-ml-specific evolution surfaces (element-type registration,
dataset versioning, project bootstrap, project-shape validation) are
all well-covered by existing skills.

| Gap | Disposition |
|---|---|
| No "what breaks if I drop X?" skill | **Defer.** Waits on Round B (deriva-ml `find_*_referencing` methods). Don't ship a skill before the underlying tools exist. |
| `catalog-operations-workflow` slash-only at 72 lines | Flag for L2 review (auto-fire candidate?). |
| No "what configs reference this version?" inverse query | Defer. Ergonomic but not load-bearing. |

#### Q1.3 — model-developer coverage: dense

~22 of the 27 skills serve this persona directly. Coverage map
walked end-to-end (bootstrap → setup → author → configure → run
→ track → compare → trace → troubleshoot → utilities).

| Gap | Disposition |
|---|---|
| No "is this sweep done?" skill | **Defer.** Waits on Round C (multirun-status summary). When it lands, add a section to `experiment-lifecycle` Phase 7 or a small `monitor-sweep` skill. |
| `compare-model-runs` Phase 1 (50-line metric-pattern detection) feels heavy | Flag for L4 (placement: skill body vs reference?). |
| `configure-experiment` vs `write-hydra-config` potential duplication | Flag for L4 (audit cross-skill content overlap). |
| No tier-2 "reproducibility" skill | Adequate — covered across `execution-lifecycle` + tier-1 + deriva-ml docs. |

### L2 (invocation discipline)

#### Q2.1 — auto-fire skills earn their slot

7 of 7 auto-fire skills justify the always-on cost. The one
asymmetry (`create-feature` auto-fires while sibling
create-shaped skills `new-model` and `setup-derivaml-project`
are slash-only) is honest, not a bug — feature creation is
many-times-per-project; model/project creation is once. Keep.

Re-examine if future audits show the LLM not actually
invoking `create-feature` correctly when auto-fired.

#### Q2.2 — `catalog-operations-workflow`: trigger-phrase auto-fire

**Flip to trigger-phrase auto-fire.** Currently slash-only at
72 lines. The skill is discipline-shaped (provenance discipline
for raw catalog mutation). Auto-firing on every conversation
overweights; staying slash-only leaves the discipline silent at
exactly the temptation-moment (raw `insert_records` /
`update_record` / `delete_record` calls).

Implementation: remove `disable-model-invocation: true`;
sharpen description to fire on `insert_records` /
`update_record` / `delete_record` / `raw catalog mutation` /
`bypass the lifecycle`. Will execute as a small commit at end
of audit.

#### Q2.3 — `work-with-assets`: keep slash-only at 79 lines

Status quo. Inside-execution asset case is already covered by
auto-fire `execution-lifecycle`. Outside-execution case is rare
and bounded. Differs from Q2.2's flip because the
*temptation-to-violate* dynamic is different — raw inserts to
`Dataset_Element` are a discipline violation; uploading an
asset outside an execution context is a legitimate operational
case.

#### Q2.4 — `compare-model-runs` Phase 1: keep in skill body

Detection logic (Pattern A vs B) IS the first phase of the
workflow. Skill is slash-only at 230 lines; 50 lines for
detection is proportional. References carry per-pattern depth.

### L3 (maintainability)

#### Q3.1 — cross-reference graph: zero broken refs but no drift detector

22 unique `/deriva-ml:` targets + 11 unique `/deriva:` targets.
Zero broken refs at audit time. But: no automated CI test exists.
Round 5 caught its renames manually; next rename round may not.

**Disposition: add a CI drift test.** Three checks (expanded
in Q3.3):

1. `/deriva-ml:<name>` refs → `skills/<name>/` exists
2. `/deriva:<name>` refs → tier-1 `skills/<name>/` exists
   (warn-only if tier-1 repo unavailable)
3. `deriva_ml_<name>` mentions → registered in deriva-ml-mcp
   tool registry (warn-only if mcp repo unavailable)

Will execute as a small commit in the wrap-up phase.

#### Q3.2 — file size profile

| Bucket | Lines / count / avg | Verdict |
|---|---|---|
| Auto-fire | 881 / 7 / 126 | Healthy. Round 4's slim landed. |
| Slash-only | 3977 / 20 / 199 | Top-4 cluster (`model-development-workflow` 346, `ml-data-engineering` 289, `debug-bag-contents` 284, `run-notebook` 264) checked. |
| References | 8263 / 14 / 590 | Heaviest set is `dataset-lifecycle/references/` at 1799 lines (5 files). Healthy distribution. |

Spot-checked top 2 slash-only:

- `model-development-workflow` 346 — genuine end-to-end arc;
  trimming would lose context. Standing.
- `ml-data-engineering` 289 — Step 4 framework-specific code
  examples (~70 lines: image classification, tabular,
  TensorFlow, multi-label) are reference-shaped. Could move to
  `references/training-pipelines.md` for ~70-line slim. **Defer**
  — slash-only doesn't pay always-on cost, low priority.

#### Q3.3 — reference quality + drift in both directions

- **22 unique `/deriva-ml:` targets, 0 broken** ✅
- **11 unique `/deriva:` targets, 0 broken** ✅
- **50 unique `deriva_ml_*` tool-name mentions vs 49 registered tools, 0 stale** ✅
- **49 registered MCP tools, 0 unmentioned in skill docs** ✅

Coverage complete in both directions.

**Note on tool count:** the MCP audit (`2026-05-04-mcp-surface-audit.md`)
said 48 tools; actual count is **49**. Will correct in the wrap-up.

### L4 (placement: pull-up to always-on / pull-down to references)

#### Q4.1 — `configure-experiment` vs `write-hydra-config`: keep both

Different questions, different shapes:

- `configure-experiment` (254 lines, slash-only, auto-fire-disabled) —
  config-group taxonomy + project structure ("what groups exist, how
  do they compose").
- `write-hydra-config` (258 lines, slash-only, auto-fire-disabled) —
  exact Python API patterns per config group ("what does the code
  look like").

Cross-link is correct (`configure-experiment` points at
`write-hydra-config` for API depth). No content overlap to
collapse. Standing.

#### Q4.2 — pull-up candidates to `deriva-ml-context`: none

`deriva-ml-context` (154 lines, always-on) carries the precedence
principle, five abstractions, and steering frame. Spot-checked
candidate content across slash-only skills: nothing is
universally-needed enough to justify always-on cost.

The 19-skill stateless-model boilerplate (flagged in the MCP audit
Q2.2) is already in `deriva-ml-context` — restating it in skill
bodies is the trim direction, not a pull-up. Deferred there;
deferred here.

**Standing: always-on stays minimal.**

#### Q4.3 — pull-down to references: standing on Q3.2

Q3.2 already flagged `ml-data-engineering` Step 4 (~70 lines
framework-specific code) as reference-shaped. Slash-only skills
don't pay always-on cost; the trim is low-priority. No new
pull-down candidates surfaced in L4.

**Standing on Q3.2 deferral.**

---

## Synthesis & disposition

### Audit findings — quick-win commits applied this round

- **QW-S1** — flip `catalog-operations-workflow` from slash-only to
  trigger-phrase auto-fire (Q2.2). Remove
  `disable-model-invocation: true`; sharpen description to fire on
  raw `insert_records` / `update_record` / `delete_record` /
  bypass-the-lifecycle phrasings.
- **QW-S2** — add CI drift detector (Q3.1, expanded scope per Q3.3):
  three checks for `/deriva-ml:`, `/deriva:`, and `deriva_ml_*`
  references vs. ground truth.
- **QW-S3** — correct tool count in MCP audit doc from 48 → 49
  (Q3.3 finding).

### Forward-looking pull-down candidates

L1 surfaced these as gaps but with the same disposition as the MCP
audit: each waits on a deriva-ml method first.

| Gap | Waits on |
|---|---|
| "What breaks if I drop X?" skill | Round B (`find_*_referencing` methods) |
| "Is this sweep done?" skill / section | Round C (multirun-status summary) |

These do not block the audit; the corresponding deriva-ml work is
already queued as spawn-task chips from the MCP audit.

### Deferred / watch

| Item | Disposition |
|---|---|
| `ml-data-engineering` Step 4 framework examples (~70 lines) | Defer — slash-only doesn't pay always-on cost |
| 19-skill stateless-model boilerplate (~19 lines aggregate) | Defer — small per-skill cost, already covered in `deriva-ml-context` |
| `compare-model-runs` Phase 1 (50 lines) | Standing — detection IS the first phase of the workflow |
| `work-with-assets` slash-only at 79 lines | Standing — outside-execution case is rare/bounded |

### Standing decisions confirmed

- 7 of 7 auto-fire skills earn their always-on slot (Q2.1).
- `create-feature` auto-fires asymmetrically vs sibling create-shaped
  skills (`new-model`, `setup-derivaml-project`); honest, not a bug
  — re-examine only if usage shows mis-fires.
- `configure-experiment` and `write-hydra-config` are complementary,
  not duplicative — keep both.
- Tool docstrings do NOT reference skills (per MCP audit standing
  decision); this audit confirms the symmetry — skill bodies DO
  reference tools, references go one direction only.

### Counts after this audit

- **Skills:** 27 (no change; QW-S1 changes invocation mode but
  doesn't add/remove a skill)
- **Auto-fire:** 7 → 8 after QW-S1 (`catalog-operations-workflow`
  flips)
- **Slash-only:** 20 → 19 after QW-S1
- **Cross-references:** 67 intra-tier + 39 cross-tier, 0 broken
- **MCP-tool mentions:** 50 unique vs 49 registered, 0 stale, 0
  unmentioned

### Quality bar achieved

- Zero broken cross-references in either direction.
- Zero stale `deriva_ml_*` tool-name mentions.
- Every registered MCP tool has at least one skill-doc mention.
- Auto-fire surface stays lean (≤8 of 27 after QW-S1).
- Reference-load size profile healthy (max bundle 1799 lines /
  `dataset-lifecycle/references/`).

The deriva-ml-skills surface is in a defensible state. The
forward-looking gaps are paired with already-queued deriva-ml
work; no audit-blocking issues remain.
