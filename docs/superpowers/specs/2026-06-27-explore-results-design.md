# explore-results Skill — Design (Cluster B1-B3)

**Date:** 2026-06-27
**Source:** Group B (findings B1, B2, B3) of [`docs/superpowers/notes/2026-06-27-global-assay.md`](../notes/2026-06-27-global-assay.md); also lands the long-deferred G1 (`deriva_ml_describe_rid` in zero skills).
**Scope:** one new guide-shaped skill + small cross-skill wiring edits. Read-only — the skill never mutates the catalog.

## Goal

Give the **domain scientist** — a user who reads ML results but does not write code — a home for the read-only journeys they actually ask about: *what is this RID, where did this come from, show me the labels, let me see it in the browser*. The 2026-06-27 assay found this persona ~25% covered (B1, cross-model agreed): lineage inspection had no non-coder door (B3, `get_lineage` framed for developers in compare-model-runs), and feature-value browsing was trapped behind create-feature's "Creating… Features" title (B2). This skill is the missing read surface.

## Non-goals

- **Not authoring.** Creating features, running executions, uploading assets, splitting datasets — those stay in their owning skills. explore-results points at them but never does them.
- **Not run-vs-run comparison.** `compare-model-runs` owns "which run was best / is this a regression." explore-results owns *tracing one artifact*; the two cross-link.
- **Not the MCP cold-start.** `using-deriva-mcp` owns the first-MCP-call primer procedure. explore-results assumes the MCP surface is reachable.
- **Not B4-B7.** Curator QA recipe (B4), sweep recipe (B5), cycle-zero→experiment trigger (B6), browse-erd fallback (B7) are deferred to separate efforts.

## Shape & invocation

- **New skill:** `skills/explore-results/SKILL.md`. Auto-discovered by Claude Code from `skills/*/SKILL.md`.
- **Guide-shaped:** default frontmatter (NO `disable-model-invocation`) → auto-invokes AND is typeable as `/deriva-ml:explore-results`. The whole point of B1 is that a non-coder's read questions currently "route nowhere"; slash-only would defeat that.
- **Read-only:** every tool/resource it names is observation-side. The skill explicitly states it does not mutate.
- **Target length:** < 200 lines (a focused read-workflow). No `references/` bundle initially (YAGNI — extract later if it grows).

## The four read journeys (skill body)

Each journey is **resource-first** — honoring the load-bearing `deriva-ml-context` rule ("fetch the `deriva://…` resource *before* reaching for `deriva_ml_*` tools" for read-side questions, because one resource fetch returns the bundled entity + children vs 2-7 tool round-trips). Each names a `deriva_ml_*` tool only where the resource doesn't answer the question, and ends by surfacing the entity's `cite_url` so the user can open it in Chaise.

1. **"What is this RID?"** (entry point for a bare RID of unknown type)
   - Lead: `deriva_ml_describe_rid(hostname, catalog_id, rid)` — the one journey that *must* start with a tool, because you don't yet know which `deriva://…/{entity}/{rid}` resource to fetch. It resolves the RID to its entity kind + summary.
   - Then route to the matching resource for detail (dataset → journey 3 context, execution → journey 2, etc.).
   - **Lands G1:** `deriva_ml_describe_rid` is referenced in zero skills today; this is its home.

2. **"Where did this come from?"** (provenance / lineage — the B3 domain-scientist door)
   - Lead: `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/lineage/{rid}` — the bundled provenance chain for any artifact (Dataset, Asset, Feature value, Execution).
   - Tool fallback: `deriva_ml_get_lineage` for traversal the resource doesn't cover; `deriva_ml_get_execution` to see a producing run's inputs/outputs.
   - Framed as the domain-scientist question ("what produced this prediction", "which dataset version trained this model"), explicitly distinct from compare-model-runs' developer comparison framing. Cross-link: "comparing multiple runs? → `/deriva-ml:compare-model-runs`."

3. **"Show me the labels / what annotations exist"** (feature-value browsing — the B2 content's new home)
   - Lead: `deriva://catalog/{h}/{c}/deriva-ml/features/{table}` to see what features are defined on a target table.
   - Then `deriva_ml_list_feature_values(hostname, catalog_id, target_table, feature_name, selector=…)` for the values — with selector guidance for the common domain-scientist asks: `selector="newest"` ("the latest label"), `selector="majority_vote"` ("the consensus label across annotators"). Reading only.
   - create-feature keeps *authoring*; it gains a pointer here for browsing. explore-results' triggers catch "show me the labels / what annotations exist."

4. **"Let me see it in the browser"** (Chaise navigation — the GUI half of B1)
   - Every journey above ends by surfacing the entity's `cite_url` (the `deriva://` resources already return per-row `cite_url`) → the user opens the record in Chaise in a browser.
   - Cross-reference `/deriva-ml:browse-erd` for "the whole catalog shape" (schema diagram). No new GUI tooling, no `deriva-ml-apps` dependency pulled in (keeps the B7 caveat out of scope).

## Cross-skill wiring

| Skill | Edit |
|---|---|
| `create-feature/SKILL.md` | Two edits. **(a) Body pointer:** feature-value *browsing/reading* is owned by `/deriva-ml:explore-results`; this skill keeps *creating* features and adding values. **(b) Trigger split (REQUIRED — resolves the over-fire):** create-feature's current `description:` claims the read side ("querying or exploring feature values", `'show feature values'`, `'what are the labels'`, `'explore annotations'`, `'browse features'`, `'feature preview'`). Those read-side triggers MOVE to explore-results. Re-narrow create-feature's description to authoring + the feature-vs-column decision + *discovering whether a feature already exists before creating one* (that discovery stays — it's part of authoring). Keep create-feature firing on "create feature / add labels / annotate / what features exist (before creating)"; hand "show me the values / browse the labels / what are the consensus labels" to explore-results. This is the one `description:` change in this wave, and it's deliberate — without it the two skills double-fire on every label-reading question. |
| `compare-model-runs/SKILL.md` | Add a cross-link: tracing where ONE artifact came from → `/deriva-ml:explore-results`; comparing MULTIPLE runs stays here. |
| `deriva-ml-context/SKILL.md` | Add one row to the "Which skill do I start with?" table: *"Want to read / inspect existing results without writing code" → `/deriva-ml:explore-results`.* (Table/body edit only — NOT a `description:`/trigger change for this skill.) |

**Note on `description:` changes:** exactly ONE trigger/`description:` edit happens in this wave — the create-feature read-side trigger split above (deliberate, to prevent double-firing). explore-results gets a new `description:` (it's a new skill). deriva-ml-context and compare-model-runs are body-only edits.

## Trigger discipline (over-fire mitigation)

The real risk is overlap with the always-on `deriva-ml-context` and the cold-start `using-deriva-mcp`, both of which already fire on read-shaped questions. Mitigation in the `description:`:

- **Fire on:** inspecting a *specific* result/artifact ("what is RID X", "where did this prediction come from", "what produced this", "trace this asset's provenance"), browsing labels/annotations on records ("show me the labels", "what annotations exist", "the consensus label"), and "open this in Chaise / see it in the browser."
- **Do NOT fire on** (name these explicitly): authoring anything (→ create-feature / execution-lifecycle / dataset-lifecycle); the generic first-MCP-call cold-start (→ using-deriva-mcp owns the primer); comparing multiple runs / regression checks (→ compare-model-runs); generic "what is DerivaML" orientation (→ deriva-ml-context, always-on).

## Verification (no executable code — this is a Markdown skill)

1. **Tool/resource reality:** every `deriva_ml_*` tool and `deriva://…` URI named in the skill exists — grep against `../deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/`. (Pre-verified set: `describe_rid`, `get_lineage`, `get_execution`, `list_feature_values`, `list_features`, plus the `dataset/execution/lineage/features` resource families and per-row `cite_url`.)
2. **Auto-discovery:** `skills/explore-results/SKILL.md` has valid frontmatter (`name`, `description`) so Claude Code loads it.
3. **Cross-references resolve:** the pointers added in create-feature / compare-model-runs / deriva-ml-context name real skills; explore-results' outbound cross-links (`/deriva-ml:compare-model-runs`, `/deriva-ml:browse-erd`, `/deriva-ml:create-feature`) are correct.
4. **Trigger sanity:** the description names the read questions AND the do-NOT boundaries (so it doesn't over-fire against deriva-ml-context / using-deriva-mcp / compare-model-runs).
5. **Read-only invariant:** no journey names a mutating tool; the skill states it does not modify the catalog.

## Success criteria

1. A new `skills/explore-results/` skill exists, guide-shaped, covering the 4 journeys, resource-first, < ~200L.
2. `deriva_ml_describe_rid` is referenced (lands G1).
3. Feature-value *browsing* has a domain-scientist home (B2); create-feature points here and keeps authoring.
4. Lineage inspection has a non-coder door (B3); compare-model-runs cross-links.
5. deriva-ml-context's start-here table has the domain-scientist row.
6. No over-fire: description carries explicit do-NOT boundaries vs the always-on / cold-start / comparison skills.
7. Every named tool/resource verified real; all cross-references resolve.
