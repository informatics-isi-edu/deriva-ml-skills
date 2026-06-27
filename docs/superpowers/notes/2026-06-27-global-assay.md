# Global Skill Assay — 2026-06-27 (Claude + codex)

A whole-plugin audit of all 31 skills across structure, accuracy/currency,
triggers, context management, OKF-conversion, and persona workflow coverage —
run from **two independent perspectives** (a Claude skill-creator-rubric fan-out
+ an independent `/codex` read against the live deriva-ml / deriva-ml-mcp-plugin
sources). This note is the triaged synthesis; it is **assessment only** (no code
changed). Pin: deriva-ml-skills **v1.12.0**; sources read at the same commit.

**How to read the severity + confidence:** P1/P2/P3 = severity. **[BOTH]** =
flagged independently by codex *and* the Claude pass (high confidence); **[1]** =
single-source. Findings marked **✓verified** were checked against library source
by the controller, not taken on a model's word.

## Headline

The plugin is in good shape structurally — no broken `/deriva:` or `/deriva-ml:`
cross-skill references to *other plugins*, the v1.12.0 OKF/ingest work is sound,
and the data-curator and model-developer persona paths are ~80–85% complete. The
findings cluster into: **a few real accuracy defects** (two P1, both cross-model
agreed and source-verified), **a clear domain-scientist coverage hole**, a
**recurring trigger-flag class bug**, and a **set of progressive-disclosure /
OKF-conversion opportunities** that are maintainability, not correctness.

---

## Group A — Accuracy / currency defects (fix first; correctness)

| # | Severity | Conf | Finding | Fix |
|---|---|---|---|---|
| A1 | **P1** | **[BOTH] ✓verified** | `execution-lifecycle/SKILL.md:125` says you can "omit [`commit_output_assets()`] entirely and let the context manager's auto-stop drive the commit on exit." **Wrong.** `__exit__` (execution.py:2350-2357) calls `execution_stop()` → **Running→Stopped only**; it never uploads. Omitting `commit_output_assets()` strands the execution in `Stopped` with staged-but-unuploaded outputs — a provenance violation `audit_provenance()` would flag. | Delete the "or omit it entirely…" parenthetical; replace with an explicit "always required — the `with` block stops the run, it does NOT upload." |
| A2 | **P1** | **[BOTH] ✓verified** | `create-feature/SKILL.md:~132` tells users to test feature-value writes "via MCP tools directly." `deriva_ml_add_feature_values` was **removed in v0.5.0** (feature.py:7). There is no MCP write tool for feature values. | Reword: feature-value writes (even test writes) go through the Python template / `exe.add_features(...)` inside an execution. |
| A3 | P2 | **[BOTH]** | `setup-ml-catalog/SKILL.md` says `initialize_ml_schema` seeds **four** vocabularies and the verify step omits `Asset_Role`. Source seeds **five** (Asset_Type, Asset_Role, Dataset_Type, Workflow_Type, Execution_Status; create_schema.py:849) + `Feature_Name` exists as a 6th vocab table populated at runtime. | Correct the count + add `Asset_Role` to the verify list. (Note: deriva-ml-context was already fixed to "six vocab tables / 3 extensible + 3 managed" in v1.12.0 — align setup-ml-catalog to that framing.) |
| A4 | P2 | [1-codex] | `troubleshoot-execution/SKILL.md:76` implies upload requires the execution still `Running`, contradicting its own line 68 + source (`Stopped → Pending_Upload → Uploaded`). | Fix the line to the real transition; reconcile with line 68. |
| A5 | ~~P2~~ | [1-codex] | ~~`generate-scripts/SKILL.md:130` says the workflow goes to `ml.create_execution`, not `ExecutionConfiguration`.~~ | **FALSE POSITIVE (verified 2026-06-27):** generate-scripts:131 *already* states `workflow=` goes to `ml.create_execution(...)`, not `ExecutionConfiguration` — correct as written. Dropped. |
| A6 | ~~P2~~ | [1-claude] | ~~`using-deriva-mcp` uses `deriva_ml_list_assets(execution_rid=...)`.~~ | **FALSE POSITIVE (verified 2026-06-27):** no such call exists (grep clean). Dropped. |
| A7 | P2 (defer) | [1-claude] | `execution-lifecycle/references/concepts.md:123` crash-recovery does `update_status(Pending_Upload)` then `commit_output_assets()`. This is the **`Running → Pending_Upload` crash path** (no `__exit__` ran), distinct from the clean `Stopped → Pending_Upload` that `commit_output_assets` drives itself — so the manual step may be load-bearing here. | **Deferred from the Cluster-A PR** — needs a library check of whether `commit_output_assets` can advance from `Running`. Not a confirmed defect. |
| A8 | P3 (defer) | [1-claude] | `api-naming-conventions` says `list_*` returns complete lists "with no filtering"; MCP `deriva_ml_list_*` are paginated/filterable (`limit`/`after_rid`). | Deferred — P3 nuance, batch with a later wave. |

> **A1 and A2 are the load-bearing ones** — both correctness, both cross-model
> agreed, both source-verified. They directly mislead a user into a broken
> provenance state / a nonexistent tool. Fix these regardless of what else gets
> done.

### Cluster A resolution (2026-06-27, branch `fix/cluster-a-accuracy`)

Source-verified each finding before touching it (the session's "don't propagate
a model's claim unchecked" discipline). Outcome:

- **A1 — FIXED.** `execution-lifecycle/SKILL.md:125` parenthetical deleted; replaced with "always required — the `with` block only stops the run, it does NOT upload." Now consistent with the skill's own `references/concepts.md:126` ("the context manager only sets status to `Stopped`/`Failed`, never commits").
- **A2 — FIXED (worse than first noted).** The MCP feature surface is read-only (`list_features`, `get_feature`, `list_feature_values`, `find_features_referencing`, `create_feature`, `delete_feature`); `feature.py:7` documents the v0.5.0 removal and `prompts.py:185` confirms writes go through `exe.add_features(...)`, "not through the MCP wire." So the "MCP tools directly" table row was **dead guidance**, not a wording nit. Rewrote the rule in `create-feature/SKILL.md` ("Writing values: always through an execution") and corrected three stale `deriva_ml_add_feature_values` references in `create-feature/evals/evals.json`.
- **A3 — FIXED (three sites).** `create_schema.py:852` seeds **five** vocabularies. Corrected `setup-ml-catalog/SKILL.md`: the verify loop (added `Asset_Role`; was 4, now 5), the `initialize_ml_schema` table row (added `Execution_Status` + a `Feature_Name`-is-runtime note), and the manage-vocabulary cross-ref ("four built-in" → "built-in").
- **A4 — FIXED.** `troubleshoot-execution/SKILL.md:76` "still in `Running`" corrected — `commit_output_assets()` runs on a `Stopped` execution and drives `Stopped → Pending_Upload → Uploaded`. (Caught and corrected my own first-draft error here: I'd written "aborted outputs were discarded," but `execution.py:2401-2407` shows `abort()` *preserves* staged rows for `resume_execution`/`gc_executions`.)
- **A5, A6 — DROPPED as false positives** (see rows above).
- **A7, A8 — DEFERRED** (A7 needs a library check; A8 is a P3 nuance).

**A2/A3 sweep found wider staleness of the same class** (the cutover to a read-only MCP execution/asset/feature surface in v0.5.0 left fossil write-tool names in several places):

- **`deriva-ml-context/SKILL.md:76`** said the `deriva-ml` schema has "four built-ins" — corrected to **six built-in vocabulary tables**, matching the rest of this skill's post-v1.12.0 framing and its own `references/concepts/` bundle. (Same defect as A3, in a second skill.)
- **Stale fictional MCP *write* sequences in three eval files** — `execution-lifecycle/evals/evals.json` (evals 1, 2, 4 named `deriva_ml_create_execution` / `_start_execution` / `_commit_execution` / `_abort_execution` / `_update_execution` / `_add_feature_values`; eval 3 named `download_execution_dataset`) and `work-with-assets/evals/evals.json` (eval 1). **None of those tools exist** — `prompts.py:1336` states "There is NO `deriva_ml_update_execution` tool. As of v0.5.0 [execution writes are out of MCP scope]"; the MCP execution/asset surfaces are read-only (`tools/execution/read.py`, read-only asset tools). Rewrote each `expected_output` to the real Python-authored lifecycle (`with ml.create_execution(...) as exe:` → `exe.asset_file_path` / `exe.add_features` → `exe.commit_output_assets()` after the block; `ml.resume_execution`/`exe.abort()` for recovery) with the MCP read tools (`deriva_ml_get_execution`, `deriva_ml_list_feature_values`) as the observation surface. Evals are gitignored from releases, so this is suite hygiene, not user-facing — but leaving known-false content while editing neighbors would be worse.

> **Residual eval-suite staleness not chased here:** other evals across the suite
> may carry pre-cutover tool names. A dedicated eval-suite refresh (the
> `evals/optimization/` legacy suite the repo CLAUDE.md already flags) is its own
> wave — out of scope for this accuracy PR.

## Group B — Persona workflow gaps (coverage)

| # | Severity | Conf | Finding |
|---|---|---|---|
| B1 | **P1** | **[BOTH]** | **Domain-scientist path is ~25% covered.** No read-only "explore results / inspect lineage / browse feature values / navigate Chaise" workflow for a non-coding user. Closest pieces: `help` (orientation only), `compare-model-runs` (developer-framed), `create-feature` Phase 7 (buried). Both perspectives independently called this the biggest blank spot. |
| B2 | **P1** | [1-claude] | Feature-value *browsing* is trapped inside `create-feature` (titled "Creating… Features"); its triggers won't match "show me the labels / what annotations exist." |
| B3 | P1 | [1-claude] | Lineage inspection for non-coders has no home — `deriva_ml_get_lineage` lives in `compare-model-runs` framed as developer comparison; "where did this prediction come from?" routes nowhere. |
| B4 | P2 | **[BOTH]** | **Data-curator quality validation has a rubric but no recipe.** `dataset-lifecycle` Phase 5 names the four checks (balance, leakage, bag parity, counts) but ships no MCP sequence or script template. (codex: `characterize_dataset`/`compare_datasets`/`validate_split` are roadmap-not-implemented.) |
| B5 | P2 | [1-claude] | Hyperparameter sweep / multirun setup is scattered across 3 skills (execution-lifecycle, configure-experiment, experiment-lifecycle) with no canonical end-to-end recipe. |
| B6 | P2 | [1-claude] | `model-development-workflow` Phase 8 (iterate) overlaps `experiment-lifecycle` Phase 1 with no concrete "switch now" trigger — a developer can loop in cycle-zero indefinitely. |
| B7 | P3 | [1-claude] | `browse-erd` requires the external `deriva-ml-apps` server and offers no fallback for users who can't install it. |

> The domain-scientist hole (B1–B3) is the single largest *new-content*
> opportunity: likely one new read-only skill (e.g. `explore-results` /
> `browse-catalog-results`) covering RID lookup (`deriva_ml_describe_rid`),
> `rag_search` discovery, `get_lineage`, feature-value browsing, and Chaise
> `cite_url` navigation — plus widening `create-feature`'s triggers / a
> `browse-feature-values` alias.

## Group C — Trigger-flag bugs (recurring class)

| # | Severity | Conf | Finding |
|---|---|---|---|
| C1 | P2 | **[BOTH]** | **Guide-shaped skills marked `disable-model-invocation: true` that should auto-fire** — `new-model`, `setup-ml-catalog`, `validate-project-setup`, `create-web-app`, `help`. codex + Claude both flag `new-model` especially (breaks the natural "add a model / first training code" path). This is the same flag-class bug the June-25 audit fixed for other skills — it recurred / was missed on these. |
| C2 | P3 | **[BOTH]** | `deriva-ml-context` triggers on bare nouns (`dataset`, `workflow`, `model`, `asset`) — fine *because* it's intentionally always-on, but the description should say "always-on context" rather than read like noun-triggers. |
| C3 | P3 | [1-codex] | `create-feature` triggers on generic `classification` — can over-fire on model-classification discussion that isn't feature authoring. |
| C4 | P3 | [1-claude] | `user-invocable: false` may be a **no-op** Claude Code frontmatter field (the real field is `disable-model-invocation`). Skills relying on it (`generate-descriptions`, `capture-tacit-knowledge`) may surface as slash commands unintentionally. **Verify against Claude Code frontmatter docs before acting** — if true, this is a quiet class bug across several skills. |

> C1 must be checked case-by-case: some of these (`setup-ml-catalog`,
> `validate-project-setup`) were *deliberately* `disable-model-invocation: true`
> per the original skill-shape rubric (one-shot/verification = tool-shaped). The
> audit's claim they "should auto-fire" is a judgment call — `new-model` is the
> most defensible flip; the others need the per-skill shape decision re-made,
> not a blanket change. **Do not blanket-flip.**

### Cluster C resolution (2026-06-27, branch `fix/cluster-c-triggers`)

Verified the three frontmatter states against the Claude Code docs first
(`code.claude.com/docs/en/skills.md`, "Control who invokes a skill"): **(default)** =
Claude auto-fires + user `/cmd`; **`disable-model-invocation: true`** = `/cmd` only,
no auto-fire; **`user-invocable: false`** = auto-fire only, hidden from `/` menu.
So a C1 "flip" = *remove* `disable-model-invocation: true` (keeps the slash command,
adds auto-firing) — non-destructive.

- **C1 — `new-model` FLIPPED to auto+slash.** It's genuinely guide-shaped (a
  multi-step authoring workflow, the Build phase of the model lifecycle). Removed
  `disable-model-invocation: true` and pushed the description so it fires on "write
  training code / add a training pipeline / start the model file" even when the user
  doesn't say "model," with do-NOT boundaries vs `execution-lifecycle` / `design-experiment`.
- **C1 — the other four KEPT slash-only** after per-skill shape review: `setup-ml-catalog`
  (consequential one-shot bootstrap; `create_ml_schema` can DROP w/ CASCADE — deliberate
  invocation wanted), `validate-project-setup` (verification = tool-shaped per rubric),
  `create-web-app` (opt-in, needs the external `deriva-ml-apps` server), `help`
  (auto-firing would be redundant with the always-on `deriva-ml-context`). The audit's
  "should auto-fire" was a judgment call; on inspection only `new-model` warranted it.
- **C2 — `deriva-ml-context` description reworded** from a bare-noun trigger list to an
  explicit "always-on plugin context … background framing for the whole session, not a
  selective per-task trigger." (Behavior unchanged — it's still `disable-model-invocation:
  false`; this just stops the description from *reading* like selective noun-triggers.)
- **C3 — `create-feature` trigger tightened.** Bare `'classification'` → `'classification
  categories'` / `'classification labels'`, plus a do-NOT boundary so generic
  model-classification talk ("this is a classification model", "classification accuracy")
  doesn't over-fire the feature-authoring skill.
- **C4 — DROPPED as a false positive.** `user-invocable: false` IS a recognized Claude Code
  field with exactly the intended semantics (Claude-invoke-only, hidden from `/` menu).
  `generate-descriptions` and `capture-tacit-knowledge` are correctly flagged; no silent bug.

## Group D — Context management / progressive disclosure (maintainability)

Always-on (or auto-firing) skills that are heavy:

| Skill | Lines | Always-on? | Extractable |
|---|---|---|---|
| `troubleshoot-execution` | 497 | auto-fires on failure | Salvage section (~162L, lines 234-395) → `references/salvage-guide.md` **[BOTH]** |
| `deriva-ml-context` | 344 | ALWAYS loaded | entity-resolution workflow (~48L) + the `find_*`/`list_*` dup → trim/point **[BOTH]** |
| `capture-tacit-knowledge` | 301 | standing trigger | entry-format mechanics (lines ~72-212) → `references/entry-format.md` **[BOTH]** |
| `compare-model-runs` | 358 | auto-fires at eval | Pattern B/C inline code → existing references (Pattern A is the common path) **[1-claude]** |

> The June-25 compaction wave already pulled depth out of 10 skills; these four
> are the residual / always-on ones it touched conservatively or didn't reach.
> `troubleshoot-execution` at 497 (the rubric's 500 ceiling) is the most urgent.

## Group E — OKF-conversion candidates (maintainability)

The v1.12.0 schema bundle established the OKF pattern in
`deriva-ml-context/references/concepts/`. Other structured-knowledge references
that would benefit (both perspectives converged on the same top candidates):

| Reference | Lines | Suggested `type:` | Conf |
|---|---|---|---|
| `execution-lifecycle/references/concepts.md` | 687 | decompose into per-concept OKF docs (`type: StateMachine` / `Concept`) — status machine, nested execs, dry-run, schema-pinning, offline mode | **[BOTH]** (top candidate) |
| `write-hydra-config/references/config-reference.md` | 1271 | `type: ConfigReference` | **[BOTH]** |
| `dataset-lifecycle/references/concepts.md` (Dataset_Type axes) | 854 | `type: Concept` per axis | **[BOTH]** |
| `create-feature/references/concepts.md` + `feature-selectors.md` | 597 / 179 | `type: Concept` | **[BOTH]** |
| `design-experiment/references/*-template.md` | — | `type: Template` | [1-codex] |
| `generate-scripts/references/script-patterns.md` | 229 | `type: Pattern` per pattern | [1-claude] |

> Decomposing `execution-lifecycle/references/concepts.md` also *fixes* a linkage
> problem: `troubleshoot-execution` currently points at named sections of it
> across skill dirs (a fragile cross-skill section reference); per-file OKF docs
> make those pointers precise.

## Group F — Overlap / duplication (maintainability)

| Finding | Conf | Owner / fix |
|---|---|---|
| `restructure-guide.md` exists in BOTH `ml-data-engineering/references/` and `work-with-assets/references/` | [1-codex] | `ml-data-engineering` owns it; `work-with-assets` links. **Re-verify both files exist / aren't already deduped.** |
| Execution status state machine duplicated: `troubleshoot-execution` table + `execution-lifecycle/references/concepts.md` | **[BOTH]** | execution-lifecycle owns; troubleshoot compresses to 3-line + pointer (ties to D + E). |
| `find_*`/`list_*` taxonomy: `deriva-ml-context` (lines 204-215) + `api-naming-conventions` | [1-claude] | api-naming-conventions owns; deriva-ml-context → 2-line pointer. |
| `configure-experiment` + `write-hydra-config` both carry the Config-Groups table | [1-claude] | write-hydra-config owns; configure-experiment links. |
| MCP resource/primer rules in both `deriva-ml-context` + `using-deriva-mcp` | [1-codex] | using-deriva-mcp owns the cold-start; context keeps a pointer. |

## Group G — A new tool with zero coverage

| # | Severity | Conf | Finding |
|---|---|---|---|
| G1 | P2 | [1-codex] | `deriva_ml_describe_rid` (tools/resolve.py) — resolves any bare RID to its entity, a very common need — is **mentioned in zero skills**. Natural homes: `troubleshoot-execution`, `using-deriva-mcp`, and the proposed domain-scientist skill (B1). **Verify the tool name against the MCP source before adding.** |

---

## Recommended fix-plan (by risk; your go/no-go per cluster)

1. **Group A accuracy (especially A1 + A2)** — small, high-value, mostly verified. One PR. *Re-verify the single-source ones (A4-A7, A6/A7) against source before fixing — this session's pattern: don't propagate a model's "stale" claim without checking.*
2. **Group C1 trigger flags** — case-by-case, NOT a blanket flip. `new-model` is the clear win; re-decide the shape of `setup-ml-catalog`/`validate-project-setup` deliberately. Verify C4 (`user-invocable` no-op) against Claude Code docs first.
3. **Group B domain-scientist coverage (B1-B3)** — the biggest *value* opportunity; a new read-only `explore-results` skill + widen create-feature triggers. This is net-new design → its own brainstorm→spec→plan, not a quick fix.
4. **Group B4 dataset-QA recipe + B5 sweep recipe** — content additions to existing skills (a `validate_dataset.py` template; a sweep section). Medium.
5. **Groups D + E + F (disclosure / OKF / dedup)** — maintainability; batch like the June-25 compaction wave. Lowest urgency, highest churn.

## Method note

codex: 1 read, high-effort, ~2.3M tokens, read-only, against live sources.
Claude: 3 parallel sonnet agents (structure / accuracy+triggers / personas).
Controller verified A1, A2, A3, B4-roadmap, G-feature-removal against source.
Cross-model agreement (the **[BOTH]** marks) is the strongest signal; single-source
findings carry a **re-verify before fixing** flag where they assert a source fact.
Builds on `2026-06-25-global-skill-audit.md` (defects + compaction, shipped v1.11.3/.4).
