# Round 3 refinement — addendum to 2026-05-02 plan

This addendum records the refinement interview for Round 3 of the
[2026-05-02 tier-2 audit cleanup plan](2026-05-02-tier-2-audit-cleanup-plan.md).
The interview reshaped Round 3 from "add a precedence map table +
data-centric philosophy subsection" to a tighter
"inheritance-with-override rule + targeted cleanup + targeted
cross-reference audit + cross-repo sync to deriva-ml-mcp."

Nine design questions resolved, walking down each branch of the
design tree with a recommended answer per question.

The interview was conducted via the
[`grill-with-docs`](../../.claude/skills/grill-with-docs/SKILL.md)
skill — a relentless one-question-at-a-time walk down the design
tree, with each question carrying a recommended answer for the user
to approve, modify, or reject. Two artifacts emerged alongside this
addendum: ADR-0001 (the precedence-rule decision) and the
recommendation that the user file a CONTEXT.md when the first term
is resolved (deferred — no project-wide glossary terms came up
during this round).

## Audit findings revisited

Round 3 was originally framed as the highest-value LLM-routing
change of the whole audit:

- Add an explicit precedence map table to `deriva-ml-context`
  enumerating, for each of the five DerivaML abstractions, the
  canonical tier-2 tool, the tier-1 tool to avoid, and the reason.
- Add a "DerivaML extends the data-centric philosophy" subsection
  naming the connection to tier-1's seven design pillars.
- Audit each tier-2 skill body for places where it currently says
  "see also `/deriva:<skill>`" and reframe as directional
  precedence.
- Cross-reference tier-1 `semantic-awareness` from `new-model`,
  `create-feature`, and `dataset-lifecycle`.

The refinement found that the precedence-map framing was wrong on
two counts. **First**, a row-per-case table duplicates routing
information the `deriva_ml_*` tool prefix already carries
mechanically; the per-abstraction lifecycle skills carry the
operation-to-tool detail at the right level. **Second**, the user
clarified that the precedence isn't about the five abstractions
specifically — it's about *anywhere a deriva-ml surface exists*
(skill, MCP tool/prompt/resource, or Python API). That's a sharper
rule than "the five abstractions win" and it applies symmetrically
on all three planes (skills, MCP, Python).

The user also flagged that the existing skill body carries
unnecessary legacy scaffolding from the `deriva-mcp` →
`deriva-mcp-core` cutover. Since the audience has no MCP veterans,
no legacy descriptions are needed.

These findings reshaped Round 3:

- Precedence map → **inheritance-with-override rule** (ADR-0001).
- Data-centric philosophy subsection → **one-paragraph "What
  DerivaML adds on top"** naming the data-design ↔ process-design
  orthogonality.
- Cross-reference audit → **full pass on all 33 cross-references**
  with bucket-1/2/3 categorization and targeted edits.
- Find-before-you-create extension → keep as planned (three skills:
  `new-model`, `create-feature`, `dataset-lifecycle`).
- Plus four cleanup items in `deriva-ml-context` itself.
- Plus a cross-repo sync commit to `deriva-ml-mcp`'s
  `_CONCEPTS_GUIDE`.

## Resolved decisions

| # | Question | Resolution |
|---|---|---|
| 1 | Shape of the precedence map: side-by-side table, restructured table, two complementary tables, or a different shape? | **Inheritance-with-override rule, no table.** Recorded as ADR-0001. |
| 2 | What to do with three pieces of legacy-MCP scaffolding in `deriva-ml-context` (Stateless model section, "extender tools were not ported" sentence, 28-line SYNC NOTE)? | **2a:** Stateless framing → one sentence. **2b:** Cut the legacy-extender sentence; lead with positive `add_term(schema="deriva-ml")` framing. **2c:** Trim SYNC NOTE to ~5 lines pointing at CLAUDE.md. |
| 3 | What to do with the "DerivaML stack" enumeration that mentions `deriva-mcp-core` and FastMCP architecture? | **Rewrite to user-facing surfaces only** — drop "loaded by deriva-mcp-core" plumbing detail; describe what a user encounters (Python library, MCP tool prefix, Claude Code plugin). |
| 4 | What happens to the existing inverse table at lines 145-156 ("When to reach back to the raw catalog surface")? | **Trim aggressively.** 8 rows → 3. Keep only display customization (both plugins have surfaces) and version checks (foundation vs DerivaML split). Rename section: routing-where-both-plugins-have-a-surface, not "reach back." |
| 5 | Scope of the per-skill audit pass across the 33 `/deriva:` cross-references? | **Full pass.** Categorize every cross-reference into bucket-1 (pure inheritance, no change), bucket-2 (inheritance with extension, make partition explicit), bucket-3 (mis-framed override, reframe or remove). |
| 6 | Should the "DerivaML extends the data-centric philosophy" framing land as a checklist (matching tier-1's seven-question shape), a one-paragraph framing, or be skipped entirely? | **One-paragraph framing.** Names the data-design ↔ process-design orthogonality and the three reproducibility additions (Datasets pin inputs; Workflows pin code; Executions link them). No checklist — that would compete with the lifecycle skills. |
| 7 | Find-before-you-create cross-reference scope: three skills (as planned), four (add `work-with-assets`), or skip and let inheritance carry it? | **Three skills as planned** — `new-model`, `create-feature`, `dataset-lifecycle`. Tier-1 `semantic-awareness` auto-fires plugin-wide but the entity-agnostic phrasing means LLMs may not extend the discipline to ML entities (Datasets, Workflows, Features) without an explicit prod. |
| 8 | Commit shape — one per group, A+B combined, or one mega-commit? | **Four commits, A+B combined.** (1) deriva-ml-context cleanup + rule, (2) tier-2 cross-reference audit, (3) semantic-awareness cross-references, (4) handoff update. |
| 9a | Does the cross-repo sync constraint extend to `_CONCEPTS_GUIDE` in deriva-ml-mcp? | **Yes — update both repos in Round 3.** Inheritance rule is conceptual core; one-side-only landing creates exactly the drift the sync convention prevents. Adds one commit to deriva-ml-mcp + a patch version bump. |
| 9b | Audit-pass output: preview the 33-row categorization table for approval, or trust-and-review at commit time? | **Single-stop preview.** Categorization is the only judgment step; once bucketed, edits are mechanical. Surface the table for approval; then edit mechanically. |
| 9c | Should there be a separate grep pass for tier-2 skill bodies that *restate* the steering principle in their own words (as opposed to merely cross-referencing tier-1)? | **Yes — add to the audit-pass commit.** A 1-minute grep prevents the failure mode of a tier-2 skill saying "use deriva-ml-X, NOT deriva-Y" while the new rule says "use deriva-ml-X if it exists; otherwise deriva-Y." |

## Operating principles confirmed (unchanged from prior rounds)

- **Each round ships as N independent commits, content-first
  ordering.** Multi-commit rounds (vs single mega-commits) so each
  step leaves the repo in a coherent state and can be reverted
  independently. Content-first means create the new content before
  deleting what it replaces, so cross-references never point at
  vanished content.

- **Guide-shaped skills auto-fire; tool-shaped skills are
  on-demand.** The deriva-ml-context skill is guide-shaped (always-on
  via `disable-model-invocation: false`); its content is what gets
  loaded into context on every conversation, so weight management
  matters.

- **CLAUDE.md is maintainer-only; user-critical content stays in
  README and skill bodies.** The SYNC NOTE in the skill body is the
  one exception — it's an in-file maintainer reminder; the canonical
  sync constraint lives in CLAUDE.md.

## Operating principle reinforced

The inheritance-with-override rule (ADR-0001) is itself an operating
principle — but a stronger one than the prior rounds' principles
because it now governs **how the LLM routes** between tier-1 and
tier-2 surfaces on every operation.

> The deriva-ml plugin extends the deriva plugin. Everything that
> applies in a Deriva catalog applies in a deriva-ml catalog by
> default. **Override:** if a deriva-ml surface exists for an
> operation, prefer it over the equivalent deriva surface. This
> applies on all three planes:
> - **Skills:** prefer `/deriva-ml:<skill>` over `/deriva:<skill>`
>   when both exist.
> - **MCP:** prefer `deriva_ml_*` MCP tools, prompts, and resources
>   over the equivalent `deriva-mcp-core` tool / prompt / resource.
> - **Python API:** prefer `deriva-ml` objects and methods over the
>   equivalent `deriva-py` calls.

The five abstractions (Dataset, Workflow, Execution, Feature,
Asset) are where the override mostly lands — but the rule is
mechanical, surface-driven, not concept-driven. The override
boundary is "is there a deriva-ml `<thing>` for this?"

## Execution shape

Four commits in deriva-ml-skills + one commit in deriva-ml-mcp.

### Commit 1 (deriva-ml-skills)

`deriva-ml-context: replace steering principle with inheritance rule + cleanup`

- Trim SYNC NOTE 28 → ~5 lines, point at CLAUDE.md.
- Cut "Stateless model" section to one sentence.
- Cut "extender tools not ported" sentence; lead with positive `add_term(schema="deriva-ml")` framing.
- Rewrite "DerivaML stack" enumeration to user-facing surfaces only.
- Replace existing "Steering principle" prose with the
  inheritance-with-override rule across all three planes.
- Add the "What DerivaML adds on top" paragraph (data-design ↔
  process-design orthogonality).
- Trim inverse table 8 → 3 rows; rename to a routing-notes section
  that names the genuine ambiguities only.

### Commit 2 (deriva-ml-skills)

`tier-2 audit: reframe cross-references under inheritance rule`

- Categorize all 33 `/deriva:` cross-references into buckets 1/2/3.
- Edit bucket-2 cases (likely: `/deriva:generate-descriptions`,
  `/deriva:customize-display`) to make the inheritance-with-extension
  partition explicit.
- Edit bucket-3 cases (mis-framed overrides) to remove or reframe.
- Grep for tier-2 skill bodies that restate the steering principle
  in their own words; reframe to defer to the rule rather than
  restate.
- Show the categorization table to the user for approval BEFORE
  making edits (single-stop preview).

### Commit 3 (deriva-ml-skills)

`new-model, create-feature, dataset-lifecycle: cross-reference tier-1 semantic-awareness`

- Add a brief cross-reference paragraph to each of the three skills,
  pointing at `/deriva:semantic-awareness` and naming the
  EAV-vs-wide-table dual-extreme framing rather than re-deriving it.

### Commit 4 (deriva-ml-skills)

`docs: round 3 handoff update`

- Mark Round 3 done in
  `2026-05-02-tier-2-audit-cleanup-session-handoff.md`.
- Record the three preceding commits' hashes.
- Note the corresponding deriva-ml-mcp commit hash + version bump.
- Carry rounds 4-6 forward as the next pickup point.

### Commit 5 (deriva-ml-mcp, separate repo)

`prompts: align _CONCEPTS_GUIDE with deriva-ml-skills inheritance rule`

- Update `_CONCEPTS_GUIDE` in
  `src/deriva_ml_mcp/prompts.py` to mirror the inheritance-rule
  framing in the skill.
- Bump version (patch — content-only update to a prompt; no API
  change).
- Cross-repo CLAUDE.md update if needed.

## Estimated effort

- Commit 1: ~30-45 min (the substantive content rewrite).
- Commit 2: ~15 min categorization preview + ~30 min edits = ~45 min.
- Commit 3: ~30 min (3 skills × ~10 min each).
- Commit 4: ~15 min (handoff doc update).
- Commit 5 (deriva-ml-mcp): ~15-20 min (small content edit + bump).

**Total:** ~2.5 hours. Slightly over the original Round 3 estimate
(~1 hr), reflecting the scope expansions (full audit pass instead of
selective; cross-repo sync; cleanup of pre-existing legacy
scaffolding).

## Dependencies and ordering

- Round 1 (cleanup) and Round 2 (MCP prompt restructure) are done.
- No upstream dependencies remain.
- Within Round 3: commit 1 must ship before commit 2 (so the
  audit references the new rule); commit 5 (deriva-ml-mcp) should
  ship after commit 1 (so the mirror is well-defined); commit 4 is
  last.

## Pickup notes

When this round ships:

- Update the parent session-handoff document
  (`2026-05-02-tier-2-audit-cleanup-session-handoff.md`) to mark
  Round 3 ✅ Done; record the four commits' hashes; record the
  cross-repo deriva-ml-mcp commit and version bump.
- Round 4 (always-on weight reduction, ~1234 → <500 lines) becomes
  the natural next round.
- Note for Round 4: with the inheritance rule landing,
  `deriva-ml-context` is now smaller AND more load-bearing — Round
  4's slimming pass should preserve the rule as the highest-priority
  always-on content.
