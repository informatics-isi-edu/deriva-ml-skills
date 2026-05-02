# Plan: tier-2 cleanup and improvement (2026-05-02)

## Background and audit context

This plan addresses findings from a two-part audit of the DerivaML ML-domain
surface, conducted in early May 2026:

1. **Tier-2 skills audit** — full collection-level evaluation of
   `deriva-ml-skills` (the Claude Code plugin shipping 29 tier-2 skills),
   following the same designer / LLM / new-user / experienced-user lens that
   was applied to tier-1 (`deriva-skills`) earlier the same week.

2. **MCP surface audit** — review of `deriva-ml-mcp` prompts, resources, and
   tools to identify gaps and misalignments with the tier-2 skill set.

Both audits were grounded in two things that happened immediately before:

- **Tier-1 had just been substantially restructured.** The `deriva-skills`
  plugin had its always-on context weight reduced by 58% (344 → 144 lines),
  the redundant `route-catalog-schema` router skill was deleted, the
  `check-deriva-versions` skill was deleted (versioning folded into
  `troubleshoot-deriva-errors`), and two new skills were added (`load-data`
  for the data-loading gap, and `getting-started` for the new-user
  onboarding gap). The find-before-you-create discipline was also extended
  with column-shape duplicate detection and the EAV-vs-wide-table dual-extreme
  framing.

- **The user explicitly raised the precedence principle** mid-audit:
  "deriva-ml provides higher-level convenience routines for many operations.
  If there is a better deriva-ml way to do something, that should take
  preference over the underlying deriva-mcp tool. Deriva-ml has additional
  concepts that build on deriva core concepts. These have priority — for
  example, datasets operations over raw table operations." This principle
  is documented in `deriva-ml-context` but inconsistently surfaced in
  per-skill bodies; making it explicit and consistent is a cross-cutting
  goal of this plan.

## Audit findings, summarized

### Tier-2 skills (29 active)

| Layer | Skills | Lines (always-on) |
|---|---|---|
| Always-on (auto-trigger) | `deriva-ml-context`, `maintain-experiment-notes`, `catalog-operations-workflow`, `api-naming-conventions`, `generate-descriptions`, `generate-scripts`, `ml-data-engineering` | ~1,234 |
| Routers (same shape as deleted tier-1 `route-catalog-schema`) | `route-project-setup`, `route-run-workflows` | 35 + 39 |
| Workflow / lifecycle | `dataset-lifecycle` (436), `execution-lifecycle` (188), `model-development-workflow` (314) | — |
| Specific tasks (15 skills) | `create-feature` (405) and 14 others | — |
| Operational / meta | `check-deriva-ml-versions`, `help` | — |

**High-priority findings:**

- 🔴 Always-on weight ~1,234 lines vs tier-1's 144 (~9× heavier). Every
  conversation pays this regardless of whether ML work is happening.
- 🔴 Two router skills — same problems as the deleted tier-1 router
  (duplicate the LLM's own routing job, return meta-instructions to user).
- 🔴 11 stale references to deleted tier-1 skills (`route-catalog-schema`,
  `check-deriva-versions`) across SKILL.md files, README, CLAUDE.md.
- 🔴 Zero references to the new tier-1 skills (`load-data`, `getting-started`).
  Tier-2 doesn't know they exist.
- 🔴 Three skills with questionable tier placement: `coding-guidelines`
  (generic Python project setup), `use-annotation-builders` (Chaise display
  annotations — pure tier-1 territory), `create-web-app` (mixed: app server
  is tier-2, visualization patterns are more generic).

**Medium-priority findings:**

- ⚠️ Two skills approaching the 500-line skill-creator soft limit:
  `dataset-lifecycle` (436), `create-feature` (405).
- ⚠️ `api-naming-conventions` (200 lines, always-on) is reference-shaped
  content loading on every conversation.
- ⚠️ `generate-scripts` (208 lines, always-on) is also reference-shaped.
- ⚠️ `ml-data-engineering` (291 lines, always-on) is the heaviest auto-fire
  skill; should be on-demand.
- ⚠️ `generate-descriptions` (169 lines, always-on) — same shape as the
  tier-1 version that was slimmed to 45 + 98-line reference; same
  opportunity here.

### MCP prompts (4 prompts; comprehensive but asymmetric)

| Prompt | Coverage |
|---|---|
| `deriva_ml_concepts` | Conceptual frame: Datasets, Workflows, Executions, Features, Assets — mirrors `deriva-ml-context` skill |
| `deriva_ml_getting_started` | Cold-start orientation: (hostname, catalog_id) rule, pagination contract, error envelope, the five ML domains |
| `deriva_ml_execution_lifecycle` | State machine (Created/Running/Stopped/Pending_Upload/Uploaded/Failed/Aborted), the five lifecycle tools, pitfalls |
| `deriva_ml_workflow_dedup` | `deriva_ml_create_workflow` is idempotent on (URL, checksum); don't preflight |

**Findings:**

- ✅ Existing prompts are high-quality; none need rewriting.
- 🔴 Asymmetry — Executions get a lifecycle prompt; Datasets, Features, Assets
  don't. The tier-2 `dataset-lifecycle` skill is 436 lines (the largest task
  skill) for a reason; non-Claude-Code clients (Cursor, raw FastMCP, SDK
  agents) have no equivalent prompt-side coverage.

### MCP resources (11 resources; coverage good but no lineage)

URIs registered: `ml/datasets`, `ml/dataset/{rid}`, `ml/dataset/{rid}/members`,
`ml/workflows`, `ml/workflow/{rid}`, `ml/executions`, `ml/execution/{rid}`,
`ml/features/{table_name}`, `ml/asset-tables`, `ml/asset/{rid}`, `ml/registries`.

**Findings:**

- ✅ Major ML entities covered at collection + per-entity-detail granularity.
- ⚠️ No `ml/lineage/{rid}` resource for cross-cutting "what produced this?"
  reads — currently requires multi-call traversal.
- ⚠️ No execution-by-status filter (`ml/executions?status=Failed`).
- ⚠️ No `ml/dataset/{rid}/spec` (the canonical Hydra-zen pin would be a
  useful URI-addressable form).

### MCP tools (~50; comprehensive but missing three convenience tools)

Every CRUD verb on every ML entity. Lifecycle tools. Dataset operations
(split, denormalize, cache, bag, member management). Workflow dedup. Asset
CRUD with `lookup_asset`. Maintenance tools.

**Findings:**

- ✅ Surface is comprehensive and well-named (`deriva_ml_*` prefix is a clean
  discriminator from tier-1 tools — embodies the precedence principle
  mechanically).
- ⚠️ No `deriva_ml_get_lineage` — provenance traversal is the headline
  DerivaML feature; making it one call is the obvious ergonomic win.
- ⚠️ No `deriva_ml_rank_executions` — `compare-model-runs` (224 lines) walks
  through "rank executions by metric X" with manual `list_feature_values` +
  client-side aggregation.
- ⚠️ No `deriva_ml_validate_dataset_spec` — `write-hydra-config` mentions
  "validate that config RIDs and versions match the catalog" but has no
  server-side helper.

### Cross-cutting principle (the steering reminder)

DerivaML's higher-level conveniences take precedence over raw catalog
primitives. The `deriva_ml_*` tool prefix and the lifecycle abstractions
(Dataset, Workflow, Execution, Feature, Asset) embody this mechanically.
The `deriva-ml-context` skill carries it as documentation. But many tier-2
skill bodies treat tier-1 cross-references as parallel options ("see also
`/deriva:create-table`") rather than directional precedence ("if you're
working with Datasets, use `/deriva-ml:dataset-lifecycle`; only fall back
to `/deriva:create-table` for project-specific domain tables that DerivaML
doesn't abstract over"). Making the precedence map explicit and consistent
is the highest-value LLM-routing change of the entire audit.

## Guiding principles for the plan

1. **Cleanup before content.** Mechanical fixes (stale refs, redundant
   routers, missing cross-refs) ship first because they have zero risk,
   immediate value, and they prepare the ground for the content additions.
2. **High-value content before polish.** Within the content rounds, the
   missing lifecycle prompts (which close a real surface asymmetry) come
   before slimming and reorganization.
3. **Precedence framing is one round on its own.** It touches multiple files
   and is the highest-value LLM-routing change, but it's also conceptually
   focused and small in line count — bundling it with other work would
   dilute it.
4. **Each round is independently shippable.** A round can be paused or
   skipped; nothing later strictly depends on something earlier (except
   where noted).
5. **Round size targeted at 30 min – 2 hours.** Rounds shorter than that
   don't earn the commit overhead; rounds longer than that risk losing
   context mid-flight.

## The six rounds

### Round 1 — Tier-2 mechanical cleanup

**Scope:** pure debt repayment. No new content; no design questions.

**Items:**

- Delete `route-project-setup` and `route-run-workflows` (the two router
  skills that mirror the deleted tier-1 `route-catalog-schema` — same
  problems, same justification).
- Fix all 11 stale references to deleted tier-1 skills
  (`route-catalog-schema`, `check-deriva-versions`) — replace with the
  right pointers.
- Add cross-references to the new tier-1 skills (`load-data`,
  `getting-started`) where they're relevant — `dataset-lifecycle`,
  `work-with-assets`, `create-feature` for `load-data`; `help`,
  `model-development-workflow` for `getting-started`.
- Apply tier-1's user-commands-vs-auto-invoked-behaviors README/CLAUDE.md
  framing to tier-2 (the recent tier-1 commit `7ca1fad` is the model).
- Update the marketplace count, README skill table, CLAUDE.md skill counts
  and lists.
- Delete any orphan empty directories left from prior reorganizations.

**Effort:** 30-45 min
**Risk:** very low — pure cleanup
**Dependencies:** none
**Outcome:** tier-2 skill catalog drops from 29 to 27, all cross-references
current, no broken pointers anywhere, README clearly distinguishes user
commands from auto-invoked behaviors.

### Round 2 — MCP prompt-surface symmetry

**Scope:** add the three missing lifecycle prompts on the MCP side. Closes
the asymmetry where executions and workflow-dedup get prompts but datasets,
features, and assets don't.

**Items:**

- Add `_DATASET_LIFECYCLE_GUIDE` prompt — covers creation → element types →
  adding members → splits (random + stratified, dry-run) → versions → bags
  (materialize, common timeouts) → denormalize (include/exclude tables) →
  caching. Source material is the tier-2 `dataset-lifecycle` skill body.
- Add `_FEATURE_LIFECYCLE_GUIDE` prompt — covers features as
  multivalued-by-design, the value-selector pattern (`select_newest`,
  `select_by_workflow`, custom selectors), `cache_features`,
  `add_feature_values` dispatch, the catalog-query vs bag-download paths
  for filtering by feature values.
- Add `_ASSET_LIFECYCLE_GUIDE` prompt — covers asset tables as the bridge
  to Hatrac, the standard column shape, the `Asset_Type` vocab pattern,
  `lookup_asset` vs `list_assets`, the upload-side via `deriva-upload-cli`
  (with a pointer to the spec).
- Cross-link the prompts (each lifecycle prompt mentions the others where
  relevant; `_GETTING_STARTED_GUIDE` should reference all four lifecycle
  prompts).
- Update `deriva-ml-mcp/CLAUDE.md`'s cross-repo-sync section to note the
  three new prompt ↔ skill mirrors.
- Bump `deriva-ml-mcp` version (this is the first non-mechanical change to
  the MCP package).

**Effort:** 1-2 hours; substantive content writing
**Risk:** low — prompts are text additions; no behavior change
**Dependencies:** Round 1 should ship first so the tier-2 skills the prompts
mirror are in clean state
**Outcome:** the MCP prompt surface is symmetric; non-Claude-Code clients
(Cursor, raw FastMCP, SDK agents) get lifecycle orientation for every
major ML entity.

### Round 3 — Precedence map + ML-extension philosophy

**Scope:** the highest-value LLM-routing change in the whole audit. Single
focused round so it doesn't get diluted.

**Items:**

- Add an explicit precedence map to `deriva-ml-context` SKILL.md body — a
  table of "when both tier-1 and tier-2 could do something, tier-2 wins
  because…" with concrete examples (Dataset operations over raw row
  inserts; Execution lifecycle over generic queries; Feature CRUD over
  ad-hoc tables; Asset operations over raw asset-table CRUD). Phrased as
  routing guidance the LLM follows, not as architectural commentary.
- Add a "DerivaML extends the data-centric philosophy" subsection to
  `deriva-ml-context` — names the connection between tier-1's seven pillars
  (data is the artifact, evolution over time, etc.) and tier-2's additions
  (reproducibility through Datasets pinning snapshots; provenance through
  Executions linking everything; reusability through Workflows being
  deduped). Short — one paragraph per addition, not a re-derivation of
  the philosophy.
- Audit each tier-2 skill body for places where it currently says "see also
  `/deriva:<skill>`" and reframe as directional precedence ("if you're
  working with Datasets, use `/deriva-ml:dataset-lifecycle`; only fall back
  to `/deriva:create-table` for project-specific domain tables that
  DerivaML doesn't abstract over").
- Find-before-you-create extension: cross-reference tier-1
  `semantic-awareness` from the relevant tier-2 skills (`new-model`,
  `create-feature`, `dataset-lifecycle`) so the LLM applies the discipline
  to ML entities too. Include a pointer to tier-1's recent EAV-vs-wide-table
  dual-extreme framing rather than re-deriving it.

**Effort:** 30-45 min for the additions; 30 min for the audit pass across
tier-2 skills
**Risk:** low — text additions and reframing
**Dependencies:** Round 1 should ship first (so the cross-reference audit
isn't fighting stale references)
**Outcome:** the precedence principle is explicit and consistent; the LLM
has a clear routing prior; the connection to tier-1's data-centric framing
is named so users (and the LLM) understand tier-2 isn't "more skills" but
"the same principles applied to the ML domain."

### Round 4 — Tier-2 always-on weight reduction

**Scope:** apply the slimming patterns from tier-1's recent work to the
tier-2 always-on layer. The biggest single improvement in tier-1 was
dropping always-on weight from 344 to 144 lines (−58%). Tier-2 is at ~1,234
lines and the same patterns apply.

**Items:**

- Slim `api-naming-conventions` (200 → ~30) — change from auto-fire to
  slash-only OR move the body to a reference. The content is
  reference-shaped (LLM consults it when picking a method name), not
  behavioral (always-relevant prior).
- Slim `generate-descriptions` (169 → ~50) — apply the tier-1 pattern:
  keep the trigger logic + quality criteria + workflow in the body; move
  per-entity templates (Dataset, Workflow, Execution, Feature, Asset,
  Experiment, multirun) to `references/templates.md`.
- Slim `generate-scripts` (208 → ~60) — move script templates and the
  script-vs-MCP-call decision tree to a reference; keep the trigger logic
  and the always-relevant guardrail in the body.
- Slim `ml-data-engineering` (291 → ~80) — keep the discipline guard
  ("when getting data OUT into ML pipelines, use the right value selector
  for training, denormalize before joining, etc."); move the worked
  patterns (PyTorch, ImageFolder, DICOM conversion) to a reference.
- Slim `dataset-lifecycle` (436 → ~250) — already has 4 references and 2
  scripts; another pass should move more depth. Specifically, the
  curated-subsets workflow and the dataset-types section are candidates
  for further reference movement.
- Slim `create-feature` (405 → ~250) — same pattern; the value-selector
  and feature-discovery sections are candidates.
- Slim `maintain-experiment-notes` (118, but the description itself is
  heavy) — consider whether the description's 25-line "every operation
  that should trigger" list can move into the body, with a more focused
  trigger description.

**Target:** drop tier-2 always-on weight from ~1,234 to under 500 lines.

**Effort:** 1-2 hours
**Risk:** low to medium — slimming a heavy skill always carries some risk
of losing useful content; mitigated by moving to references rather than
deleting
**Dependencies:** Round 3 should ship first so the precedence framing is in
`deriva-ml-context` before the slimming pass touches related skills
**Outcome:** every tier-2 conversation pays substantially less context; the
depth is preserved in references that load on demand.

### Round 5 — Tier placement decisions

**Scope:** decide where three borderline skills belong. This is the only
round with real design discussion.

**Items:**

- **`coding-guidelines` (154 lines, currently tier-2):** generic Python
  project setup (uv, pyproject.toml, Git workflow, Google docstrings, ruff,
  type hints). No DerivaML-specific content. Three options: (a) move to
  tier-1 since it applies to any Deriva project; (b) keep in tier-2 if
  "DerivaML projects use these specific conventions"; (c) split into a
  generic tier-1 piece and a DerivaML-specific tier-2 piece.
- **`use-annotation-builders` (175 lines, currently tier-2):** Chaise
  display annotations via type-safe Python builder classes. This is pure
  tier-1 territory (Chaise display annotations are core Deriva, not ML).
  Recommend move to tier-1; tier-1's `customize-display` could absorb it
  as a reference, or it could be its own tier-1 skill.
- **`create-web-app` (161 lines, currently tier-2):** custom web apps for
  DerivaML data — registering apps in the app server, building
  visualizations. The "app server" piece is DerivaML-specific (the
  deriva-ml ecosystem ships an app server for hosting custom apps). The
  "visualization patterns" piece is more generic but oriented toward
  DerivaML's data shapes. Recommend keep in tier-2 but rename or
  scope-narrow if needed.

**Effort:** discussion + 1 hour edits per move
**Risk:** medium — moving skills between plugins requires marketplace/README
updates in two repos; cross-references in both directions need to be
correct after the move
**Dependencies:** none, but Round 1 (cleanup) and Round 3 (precedence
framing) should be done so the tier-1/tier-2 boundaries are clearly
understood
**Outcome:** every skill is in the right plugin; the tier-1 vs tier-2
distinction is consistent and defensible.

### Round 6 — MCP tool and resource additions

**Scope:** add the missing tools and resources identified in the MCP audit.
This round touches `deriva-ml-mcp` source code (not just docs/skills), so
it's the heaviest round and warrants its own placement.

**Items:**

**Tools:**

- `deriva_ml_get_lineage(rid, depth=2)` — returns
  `{execution, workflow, datasets[], inputs[], parent_executions[]}` for
  any artifact (asset RID, feature value RID, dataset RID). Eliminates the
  multi-call traversal pattern that's currently the only way to answer
  "what produced this?"
- `deriva_ml_rank_executions(workflow_rid, by_feature, top_n=10, order="desc")`
  — server-side aggregation for the top-N-by-metric pattern that tier-2
  `compare-model-runs` walks through manually. Saves the LLM from writing
  client-side aggregation code on every comparison.
- `deriva_ml_validate_dataset_spec(specs=[{rid, version}])` — round-trips
  against the catalog to verify each (RID, version) pair refers to an
  existing dataset version. Lets `write-hydra-config` validate without
  going through the Python API.

**Resources:**

- `deriva://catalog/{h}/{c}/ml/lineage/{rid}` — read-only resource form of
  the new `get_lineage` tool. URI-addressable means configs and citations
  can reference it directly.
- `deriva://catalog/{h}/{c}/ml/executions?status={status}` — filtered
  execution list for the "show me what's failed" pattern.
- `deriva://catalog/{h}/{c}/ml/dataset/{rid}/spec` — exposes
  `get_dataset_spec` as a URI; useful for Hydra-zen configs to reference
  by URI rather than computed call.

**Effort:** 2-4 hours
**Risk:** medium — touches MCP source code with new tool implementations;
needs tests; needs version bump
**Dependencies:** Round 2 should ship first so the MCP prompts can mention
the new tools at registration time (the prompts that introduce the new
tools should already exist when the tools land)
**Outcome:** the MCP surface closes three real workflow gaps; the LLM has
direct tools for provenance traversal, execution ranking, and config
validation rather than walking around them.

## Cross-cutting items (woven through the rounds, not their own round)

A few items don't justify their own rounds but should be done as part of
others:

- **Round 1 also:** rebuild the README's user-commands vs
  auto-invoked-behaviors framing (apply the same fix from tier-1's recent
  commit `7ca1fad`) — the tier-2 README and CLAUDE.md should clearly
  separate the two shapes the way tier-1's now does.
- **Round 3 also:** if the EAV / wide-table dual-extreme framing from the
  most recent tier-1 work isn't yet visible to tier-2 (it isn't — tier-1's
  `semantic-awareness` is the home), make sure tier-2's relevant skills
  (`dataset-lifecycle`, `create-feature`, `new-model`) reference it rather
  than re-deriving the same guidance.
- **Round 4 also:** when slimming each skill, check that the description
  is still appropriately pushy (lead with "ALWAYS use this skill when…")
  and that trigger phrases haven't drifted from what the skill actually
  covers.
- **Round 6 also:** every new MCP tool needs a corresponding skill update
  (or at minimum a mention in the relevant tier-2 skill body) so users
  discover the new capability.

## Plan summary table

| Round | Scope | Effort | Risk | Depends on | Headline outcome |
|---|---|---|---|---|---|
| 1 | Tier-2 mechanical cleanup | 30-45 min | very low | — | Stale refs gone, routers gone, new tier-1 refs added |
| 2 | MCP lifecycle prompts | 1-2 hr | low | (1 first) | MCP prompt symmetry restored |
| 3 | Precedence map + ML philosophy framing | 1 hr | low | 1, 2 | LLM routing prior is consistent and explicit |
| 4 | Tier-2 always-on weight reduction | 1-2 hr | low-med | 3 | ~1234 → <500 lines always-on |
| 5 | Tier placement decisions | 2-3 hr | medium | 1, 3 | Every skill in the right plugin |
| 6 | MCP tools and resources | 2-4 hr | medium | 2 | get_lineage, rank_executions, validate_dataset_spec land |

**Total estimated effort:** 8-13 hours across 6 rounds.

**Total quantitative impact:**

- Tier-2 skill count: 29 → 27 (router deletions) → possibly 24-26 (after
  tier placement decisions in Round 5)
- Tier-2 always-on weight: ~1,234 → target <500 (−60%)
- MCP prompts: 4 → 7 (75% growth on the lifecycle surface)
- MCP tools: ~50 → ~53 (3 new closing real workflow gaps)
- MCP resources: 11 → ~13-14
- Stale tier-1 references: 11 → 0
- Cross-references to new tier-1 skills (`load-data`, `getting-started`):
  0 → present in 5+ tier-2 skills

## Recommendation on which round to do first

**Round 1.** Pure cleanup, zero risk, immediate value, prepares the ground
for everything else. It's also the smallest commitment (30-45 min), so it's
the easiest place to start without committing to the whole arc.

After Round 1 ships, the natural next call is **Round 2** (MCP prompts)
because it's the highest-value content addition and doesn't require
touching skills again. Rounds 3-6 can then be sequenced based on what's
most pressing.
