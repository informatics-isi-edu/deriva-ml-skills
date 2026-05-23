# Skill update assessment — 2026-05-18

A cross-repo audit of `deriva-ml-skills` (29 skills) against substantial
upstream changes that have landed in `deriva-ml` (v1.34..v1.38.0 +
unreleased) and `deriva-ml-mcp` (v0.5.0). Recommends a prioritized
update plan from three perspectives: **LLM trigger accuracy**,
**ML developer building reproducible models / evaluating models**, and
**maximizing LLM leverage** (use the new MCP surface fully, route the
right work to local Python).

**TL;DR.** The skills repo lags both upstream repos materially. The
**v0.5.0 MCP-tool removal** (9 execution + cache tools) is the
biggest gap — **15 skill files** still reference at least one removed
tool by name. The **v1.36 `restructure_assets` rename** is a
fully-broken example path in `ml-data-engineering`'s most-used
section. The **v1.34 dev-versioning model** and **v1.38 write-through
description setters** mostly landed but with stragglers. New
capability that would move the LLM/user forward — framework adapters
(`as_torch_dataset` / `as_tf_dataset`), `exe.metrics_file()`,
`feature_values(execution_rids=, materialize_limit=)`,
`workflow_type=` filter, schema pin/diff, offline mode, two cold-start
resources — is largely undocumented.

A single PR can land the P0/P1 fixes in ~one engineering session; the
P2 capability uplifts are a second session. The two prior triage
notes (`2026-05-23-skills-followups-from-mcp-audit.md` and its
addendum) covered ~half of this surface; this assessment adds the
deriva-ml-side breaking changes the MCP-only audit didn't see.

---

## Method

- **Lens A** (LLM trigger accuracy): does every skill's
  `description:` and body reference live tool / API names? A skill
  that names a removed tool either fails silently (the LLM hallucinates
  the call and gets `unknown tool`) or — worse — drives the user to a
  wrong workflow.
- **Lens B** (Reproducible model dev / evaluation): does the skill
  reflect the current canonical path for the user's task? Does it
  surface the cheap-and-correct option, not just the legacy one?
- **Lens C** (LLM leverage): is the right work offloaded to MCP
  (catalog reads, vocab CRUD, lifecycle observation) and the right
  work routed to local Python (execution staging, asset I/O,
  schema-cache pinning, framework adapters)? Skills that try to
  drive everything through MCP, or that don't surface new
  one-round-trip filters, leave value on the table.

Sources consulted:

- `deriva-ml/docs/user-guide/migration.md` (v1.34 + post-S2 release)
- `deriva-ml/CHANGELOG.md` (Unreleased; covers ~25 entries Phase 1
  through Phase 2 Subsystem 4 + recent fixes)
- `deriva-ml-mcp/docs/audit-2026-05-23.md` (Lens C stateless rule)
- `deriva-ml-mcp/docs/superpowers/notes/2026-05-23-cache-denormalize-deprecation-design.md`
- `deriva-ml-skills/docs/superpowers/notes/2026-05-23-skills-followups-from-mcp-audit.md`
  (the prior triage; this assessment supersedes parts of it that have
  not been actioned and adds the deriva-ml-side breaks it didn't see)

---

## Section 1 — P0: outright broken (the user / LLM hits an error)

### 1.1 Removed v0.5.0 MCP tools, still cited in 15 skill files

`deriva-ml-mcp` v0.5.0 retired all 9 execution-mutating and cache
tools. The principle: executions and cache materialization must
originate in the caller's local Python environment (workflow code is
in the user's git checkout; staging is per-process SQLite; asset
bytes are local). MCP can't participate. The wire surface is now
**41 tools + 3 prompts** (was 52+).

| Removed tool | Skills still referencing | Replacement pattern |
|---|---|---|
| `deriva_ml_create_execution` | 15 files | `with ml.create_execution(...) as exe:` (local Python) |
| `deriva_ml_start_execution` | 12 files | implicit in `__enter__` |
| `deriva_ml_commit_execution` | 12 files | `exe.upload_outputs()` after the `with` block |
| `deriva_ml_abort_execution` | 12 files | `exe.abort()` |
| `deriva_ml_update_execution` | 6 files | `exe.update_status(target, error=...)` |
| `deriva_ml_add_feature_values` | 10 files | `exe.add_features(records)` |
| `deriva_ml_create_execution_dataset` | 3 files | through `create_execution(datasets=[...])` |
| `deriva_ml_add_nested_execution` | 4 files | parent context wraps child `with ml.create_execution(...)` |
| `deriva_ml_cache_dataset` | 7 files | `ml.cache_dataset(spec)` (local Python) |

Read-side execution tools **stay** (`list_executions`, `get_execution`,
`find_workflow_executions`, `list_execution_children`,
`list_execution_parents`, `get_lineage`). The skill content needs the
**MCP read / local-Python write** split made explicit, not a global
sed of one tool to another.

**Recommendation:** A focused pass across these 15 files, organized
as **MCP for observation, local Python for authorship**. Each skill
should grow (or sharpen) a section that walks the
`with ml.create_execution(...) as exe:` context-manager pattern
verbatim — this is the new canonical lifecycle that skills should
generate as code the user runs locally. The audit note's recommended
`work-with-executions` skill is a viable home for the generator
content, but folding it into `execution-lifecycle` is also acceptable
(and lower disruption).

**Files most-affected** (by reference count + centrality):

1. `execution-lifecycle/SKILL.md` + `references/{concepts,workflow}.md`
2. `troubleshoot-execution/SKILL.md` + `references/execution-lifecycle.md`
3. `create-feature/SKILL.md` + `references/{concepts,workflow}.md`
4. `model-development-workflow/SKILL.md`
5. `manage-storage/SKILL.md`
6. `work-with-assets/SKILL.md` + `references/workflow.md`
7. `deriva-ml-context/SKILL.md` (always-on; the highest-leverage edit)

### 1.2 `restructure_assets` API rename (v1.36 D2)

`ml-data-engineering` is the central training-data-prep skill. Its
two `restructure_assets` worked examples and its
`references/restructure-guide.md` (a 150+ line guide) all use the
**removed** `group_by=` / `value_selector=` kwargs and the **removed**
dotted `"Feature.column"` syntax. Calling any of those examples
raises `TypeError`.

- `ml-data-engineering/SKILL.md` lines 41, 175, 212, 227, 228, 262
- `ml-data-engineering/references/restructure-guide.md` lines 38, 66,
  73, 80, 87, 93, 106, 113, 123, 130, 148

The new shape:

```python
# Was:
bag.restructure_assets(output_dir="./ml_data", group_by=["Diagnosis"],
                       value_selector=FeatureRecord.select_latest)
# Is:
bag.restructure_assets(output_dir="./ml_data",
                       targets={"Diagnosis": FeatureRecord.select_latest},
                       missing="unknown")  # or "error" / "skip"

# Dotted column → target_transform:
# Was: group_by=["Classification.Label"]
# Is:  targets=["Classification"], target_transform=lambda rec: rec.Label
```

**Recommendation:** P0. One PR rewrites the `ml-data-engineering`
skill body + reference doc, shows the new `targets={...}` /
`target_transform=...` / `missing=...` vocabulary, and removes the
dotted-syntax example entirely.

### 1.3 Hallucinated parameter in `manage-storage`

The prior audit note (B4) flagged this and it has not been actioned:

- `manage-storage/SKILL.md:182` documents
  `deriva_ml_cache_dataset(asset_rid=...)`. The tool only accepts
  `dataset_rid`. The user hits an `unknown argument` error.

Compounded by 1.1 (the tool is gone in v0.5.0 anyway), the whole
section needs a rewrite: bag-warming moves to local Python; per-asset
download is `Execution.download_asset(...)`.

### 1.4 `cache_features()` is now private

The `dataset-lifecycle` skill body (line 217), its
`references/curated-subsets.md` (lines 103, 110, 127), and its two
helper scripts (`scripts/subset_filters.py:41`,
`scripts/generate_subset_template.py:41, 136`) all call
`ml.cache_features(...)` directly. The method was renamed
`_cache_features` (private; v1.37 migration table). Public callers
should use:

```python
# Was:
ml.cache_features("Image", "Diagnosis")
# Is:
ml.feature_values("Image", "Diagnosis")   # online
# Or via MCP for inspection:
deriva_ml_list_feature_values(hostname, catalog_id, target_table="Image",
                              feature_name="Diagnosis",
                              execution_rids=[...],      # new kwarg
                              materialize_limit=10000)   # new kwarg
```

The scripts in particular are user-facing copy-paste templates;
shipping a script that calls a now-private API is the worst kind of
P0.

### 1.5 `upload_execution_outputs(...)` is legacy

Phase 1 introduced `exe.upload_outputs(...)` as the canonical name.
The old `exe.upload_execution_outputs(...)` is retained for backward
compat (see CHANGELOG Phase 1 §Removed table — only "still present;
superseded" for this one), but every example skill should use the
new name. Still cited:

- `manage-storage/SKILL.md` (2 refs)
- `new-model/references/runner-interface.md` (2)
- `dataset-lifecycle/references/workflow.md` (4)
- `catalog-operations-workflow/references/script-patterns.md` (5)
- `troubleshoot-execution/SKILL.md` (7) + `references/execution-lifecycle.md` (9)
- `run-notebook/{SKILL.md,references/workflow.md}` (2 + 2)
- `generate-scripts/SKILL.md` (1)
- `create-feature/references/workflow.md` (1)

**Recommendation:** P1 (works, but every skill body should standardize
on `upload_outputs`); ideally part of the v0.5.0 sweep so each file
gets one coordinated edit.

### 1.6 `increment_dataset_version` straggler

`debug-bag-contents/SKILL.md` still references `deriva_ml_increment_dataset_version`
(removed; replaced by `deriva_ml_release` per migration §1.34).
Single-line fix.

---

## Section 2 — P1: stale-but-works (user writes worse code than necessary)

### 2.1 `deriva_ml_create_vocabulary` is the right tool on deriva-ml catalogs

The prior audit (B2) flagged this; only `create-feature` knows the
ML-aware tool exists. Others (`api-naming-conventions/SKILL.md`,
`create-feature/references/{concepts,workflow}.md`) still point at
the generic `create_vocabulary` from `deriva-mcp-core`, which doesn't
apply curie-prefix scoping or trigger the navbar refresh on a
deriva-ml-loaded catalog.

**Recommendation:** Add a one-line steering note to
`deriva-ml-context/SKILL.md` (always-on, plugin-wide reach):

> On a deriva-ml-loaded catalog, prefer `deriva_ml_create_vocabulary`
> over the generic `create_vocabulary` — it applies the
> `deriva-ml`-scoped curie prefix and refreshes the navbar.

Then the in-skill steering becomes a sentence each, not a section.

### 2.2 The `write-hydra-config` "planned" claims

`write-hydra-config/SKILL.md` documents `deriva_ml_validate_config_file`
and `deriva_ml_bootstrap_config` as **planned** (lines 19, 377, 389,
~430). Both tools exist on MCP today. The skill's 5-tool composition
recipe — what the skill currently leads with — is the obsolete
fallback; the two tools are the canonical path now.

**Recommendation:** Promote both tools to the lead path; keep the
composition recipe as a "for granular debugging" footnote. Drop the
"no asset analog to `validate_dataset_specs` yet" claim near line 430
— `validate_config_file` IS that analog.

### 2.3 `as_torch_dataset` / `as_tf_dataset` are new but discoverable

Native framework adapters landed in deriva-ml (probably v1.36 / post-S2;
documented in `migration.md` "New recommended patterns"). They
replace ~35 lines of hand-rolled `torch.utils.data.Dataset` boilerplate.

Currently `ml-data-engineering/SKILL.md` (the natural home) walks
`restructure_assets` + `ImageFolder` for image classification only.
A user training on tabular features or a non-classification task
still has to hand-roll.

**Recommendation:** P1 because `restructure_assets` still works; the
adapters are an alternative, not a replacement. But the skill should
show both paths and steer:

- `as_torch_dataset` / `as_tf_dataset` when training in PyTorch /
  TF / Keras directly (most common).
- `restructure_assets` when the downstream trainer wants the
  ImageFolder class-folder layout (RetFound fine-tuning,
  third-party trainers).

Both use the same `targets=` / `target_transform=` / `missing=`
vocabulary (1.36 D2 alignment) — that's the natural way to introduce
the rename from §1.2 above.

### 2.4 `exe.metrics_file()` is the metric-log API

Previously users wrote training metrics to an `Execution_Metadata`
asset via `asset_file_path(MLAsset.execution_metadata, "metrics.jsonl",
asset_types=ExecMetadataType.execution_config.value)`. The asset type
lied about the file's purpose (it's metrics, not config).

The new `exe.metrics_file()` method uploads with
`asset_types=Metrics_File`. Used inside an execution context:

```python
with exe.metrics_file().open("a") as f:
    f.write(json.dumps({"epoch": 0, "val_loss": 0.23}) + "\n")
```

`execution-lifecycle/references/workflow.md:125` still mentions the
old pattern. `model-development-workflow/SKILL.md` is the natural
home to show the new one.

### 2.5 Crash recovery is now a legal transition

Old workaround was `exe.update_status(ExecutionStatus.Failed,
"Resumed after crash")` — a spurious Failed marker that polluted the
audit trail. The new path: `update_status(ExecutionStatus.Pending_Upload)`
is now a legal direct transition from Running.

Worth a callout in `troubleshoot-execution/SKILL.md` salvage section.

### 2.6 `ExecutionRecord` → `ExecutionSnapshot` rename

`execution-lifecycle/references/concepts.md` still references the old
class name (`ExecutionRecord` in two places where it now means the
local-cached snapshot type). Three-line fix.

---

## Section 3 — P2: missing capability (N round-trips when 1 would do)

### 3.1 `feature_values(execution_rids=, materialize_limit=)`

The migration guide highlights this as a 30-LOC fix that unlocks
single-round-trip cross-execution metric comparison
(`compare_metrics`-shaped queries). Two skills know about it
(`compare-model-runs`, `experiment-lifecycle`); two don't but should
(`model-development-workflow`, `troubleshoot-execution`).

```python
# Was: N+1 round trips
for exec_rid in exec_rids:
    rows = ml.feature_values("Image", "F1", execution=exec_rid)

# Is: 1 round trip
rows = ml.feature_values("Image", "F1",
                         execution_rids=exec_rids,
                         materialize_limit=10000)
```

Also wraps as `execution_rids=` on `deriva_ml_list_feature_values`
MCP tool.

### 3.2 `workflow_type=` filter on `deriva_ml_list_executions`

`troubleshoot-execution` and `experiment-lifecycle` paginate +
post-filter when a single server-side filter does the job. The
audit note flagged this; it remains open.

```python
# Was: paginate everything, filter client-side for "Training" runs
# Is: deriva_ml_list_executions(..., workflow_type="Training")
```

### 3.3 `find_*(sort=True)` for newest-first activity

`find_executions`, `find_datasets`, `find_workflows` all accept
`sort=True` (newest first by RCT) or a callable for custom sort.
Recommended for "show me what's new" queries in
`maintain-experiment-notes`, `compare-model-runs`,
`execution-lifecycle`. Currently no skill demonstrates this.

### 3.4 `deriva_ml_validate_config_file` / `deriva_ml_bootstrap_config`

Per §2.2, these shipped. The `write-hydra-config` skill should lead
with them. Beyond that skill, **every other** experiment/config skill
should reference them as the validation step at the end of a config
edit. Specifically:

- `configure-experiment` — should call `validate_config_file` after
  generating the user's config.
- `run-notebook` — should validate before running.
- `experiment-lifecycle` — should validate at the pre-flight step.

### 3.5 `bag-preview` resource

The new `deriva://catalog/{h}/{c}/ml/dataset/{rid}/bag-preview`
resource serves the "size before download" question without a tool
call (no roundtrip to the bag_info impl). Only `debug-bag-contents`
references it currently; `manage-storage`, `dataset-lifecycle`,
`execution-lifecycle` should too.

### 3.6 Cold-start resources

`deriva://deriva-ml/getting-started` and `deriva://deriva-ml/concepts`
are resource-walked by resource-aware clients (the agent here). Only
`using-deriva-mcp` references them. Every skill with "read the
orientation first" prose (`dataset-lifecycle`, `execution-lifecycle`,
`experiment-lifecycle`, `create-feature`) should point at the
resource form as the first-line "fetch this resource" pointer. The
prompt name stays as the fallback channel.

### 3.7 Schema pin / diff (`pin_schema`, `diff_schema`)

Phase 2 added a schema-pin + diff surface. Useful in two scenarios
that skills currently don't address:

- "I want to freeze my analysis against this catalog state for a
  paper / experiment series" → `ml.pin_schema(reason=...)`.
- "Something changed — what?" → `ml.diff_schema()` returns a
  `SchemaDiff` with `.render()` for human output and
  `.model_dump()` for JSON.

Probably a single new section in `troubleshoot-execution` and a
cross-reference from `execution-lifecycle`.

### 3.8 Offline mode

`ConnectionMode.offline` + `CatalogStub` make it possible to do a
read-only working session against a pre-cached schema with no
network. Useful on planes, in air-gapped review settings, or for
preventing accidental writes to a production catalog. No skill
mentions it.

### 3.9 `Asset_Role` contract + auto-tags

PR #220 + the deriva-ml CLAUDE.md refresh (#223) pinned the contract:
every execution-linked asset carries both `Asset_Role`
(`Input`/`Output`) and a directional `Asset_Type` tag
(`Input_File`/`Output_File`); deriva-ml assigns both, never the
caller. An LLM that filters `asset_types == ["Model_File"]` will see
zero results after upgrade because the directional tag is now also
present.

Worth a one-paragraph block in `deriva-ml-context` (always-on) and
a callout on the `deriva_ml_list_assets` / `deriva_ml_lookup_asset`
explanations in `work-with-assets` / `manage-storage`.

---

## Section 4 — Cross-skill consistency wins

### 4.1 The MCP-read / local-Python-write boundary

After the v0.5.0 cut, the skill text needs the boundary made
**explicit**. A canonical paragraph in `deriva-ml-context` would
read approximately:

> **MCP tools observe; local Python authors.** Reading executions,
> datasets, workflows, features, lineage — all MCP, all stateless,
> all addressable by hostname + catalog_id. Authoring executions
> (creating + staging features + uploading outputs), caching bags
> for offline use, and any operation that needs the user's local
> filesystem or git checkout — all local Python via the
> `DerivaML` Python API.

That paragraph in the always-on context skill is leverage:
every other skill can then route to "MCP" or "Python" without
re-justifying the boundary.

### 4.2 The `read-this-resource-first` pointer

§3.6 covered this. The norm should be: every domain skill that
serves a real first-touch (`dataset-lifecycle`, `execution-lifecycle`,
`experiment-lifecycle`, `create-feature`, `model-development-workflow`)
starts with:

> **First time touching DerivaML this session?** Read
> `deriva://deriva-ml/concepts` and `deriva://deriva-ml/getting-started`
> for the conceptual frame.

Repetition is fine; it's how LLMs learn to do the orientation read
without being told twice.

### 4.3 Consistent vocabulary for `targets=` / `target_transform=` /
`missing=`

§1.2 + §2.3 + §1.4 all touch the same vocabulary now shared by
`restructure_assets`, `as_torch_dataset`, `as_tf_dataset`. The
skill text should use these terms consistently across
`ml-data-engineering`, `dataset-lifecycle` (where features are
discussed in the context of split stratification), and
`compare-model-runs` (where labels are pulled for evaluation).

---

## Section 5 — Recommended PR plan

A staged set of PRs, in landing order:

### PR-1: P0 — restore correctness

- §1.2 `restructure_assets` rename in `ml-data-engineering` +
  reference doc
- §1.3 `manage-storage` hallucinated parameter (and full
  cache-section rewrite per §1.1)
- §1.4 `cache_features` rename in `dataset-lifecycle` SKILL +
  `references/curated-subsets.md` + both helper scripts
- §1.6 `increment_dataset_version` straggler in `debug-bag-contents`

Estimated effort: 3-4 hours. Net: zero broken example code.

### PR-2: P0 — v0.5.0 MCP-removal sweep

- §1.1 across 15 skill files. Per file:
  - Replace each removed-tool reference with the Python-API
    equivalent.
  - Add the `with ml.create_execution(...) as exe:` canonical
    pattern as the worked example.
  - Keep MCP read tools (`list_executions`, `get_execution`,
    `find_workflow_executions`, `get_lineage`) on the observation
    side.
- §1.5 standardize on `exe.upload_outputs(...)` (one coordinated edit
  per file).
- §4.1 the canonical "MCP-reads-local-Python-writes" paragraph in
  `deriva-ml-context`.

Estimated effort: 6-8 hours (15 files × careful edit). Net: the
plugin's central lifecycle pattern matches the upstream's central
lifecycle pattern.

### PR-3: P1 — stale-but-works fixes

- §2.1 `deriva_ml_create_vocabulary` steering in `deriva-ml-context`
  + remove the generic-tool references from `create-feature` /
  `api-naming-conventions`
- §2.2 `write-hydra-config` "planned" → "shipped" rewrite
- §2.4 `exe.metrics_file()` in `execution-lifecycle` +
  `model-development-workflow`
- §2.5 Crash-recovery legal transition callout in
  `troubleshoot-execution`
- §2.6 `ExecutionRecord` → `ExecutionSnapshot` in
  `execution-lifecycle/references/concepts.md`

Estimated effort: 2-3 hours.

### PR-4: P2 — capability uplift

- §2.3 `as_torch_dataset` / `as_tf_dataset` in `ml-data-engineering`
  alongside `restructure_assets`, with the new `targets=` /
  `target_transform=` / `missing=` vocabulary used consistently.
- §3.1 `feature_values(execution_rids=, materialize_limit=)` in
  `model-development-workflow` + `troubleshoot-execution`.
- §3.2 `workflow_type=` filter in `troubleshoot-execution` +
  `experiment-lifecycle`.
- §3.3 `find_*(sort=True)` examples in
  `maintain-experiment-notes` + `compare-model-runs`.
- §3.4 `validate_config_file` / `bootstrap_config` as the validation
  step in `configure-experiment` / `run-notebook` /
  `experiment-lifecycle`.
- §3.5 `bag-preview` resource in `manage-storage` / `dataset-lifecycle`
  / `execution-lifecycle`.
- §3.6 Cold-start resource pointers across the touch-first skills.
- §3.9 `Asset_Role` contract paragraph in `deriva-ml-context` +
  callout in `work-with-assets`.

Estimated effort: 4-5 hours. Net: each major workflow uses the
cheapest correct path.

### PR-5: P3 — new capability scaffolding (optional)

- §3.7 Schema pin / diff section in `troubleshoot-execution`.
- §3.8 Offline mode section in `using-deriva-mcp` or new section in
  `dataset-lifecycle`.

Estimated effort: 1-2 hours. Lowest priority because workflows still
work without these, but they're an LLM-leverage win when working
against catalogs that drift mid-session.

---

## Section 6 — What to NOT do

A few proposals worth explicitly rejecting:

- **Don't create a new `work-with-executions` skill.** The audit
  note offered it as a pattern (mirroring `work-with-assets` in
  deriva-skills). It's a viable option, but folding the new
  context-manager content into the existing `execution-lifecycle`
  skill is cheaper (one skill, one trigger description, no
  cross-reference burden) and avoids the "is it `execution-lifecycle`
  or `work-with-executions`?" routing confusion.
- **Don't bulk-add `as_torch_dataset` to every skill that touches
  features.** It belongs in `ml-data-engineering` (its natural
  home); the other skills should cross-reference, not duplicate.
- **Don't try to land all five PRs as one.** The sweep is too large
  to review honestly. Stage them; PR-1 + PR-2 are independent and
  can land in either order.

---

## Section 7 — Out-of-scope follow-ups

These are real but outside this assessment's scope:

- The deriva-ml-mcp v0.5.0 cut **changed the tool count** (was ~52,
  now 41). Any skill text that names a specific count is stale
  (audit-note addendum item #13). Search-and-replace; low value.
- `deriva_ml_split_dataset` was retired from MCP (replaced by the
  Python `split_dataset(ml, source_rid, execution, ...)`). Zero
  skill files reference the MCP tool name; the Python API references
  are correct.
- The `deriva-ml-mcp` plugin itself still has cleanup work pending
  (see its `docs/audit-2026-05-23.md` Tier 2 backlog: write-through
  description setters, Asset_Role prompt content, structured
  `DerivaMLRidsNotFound` envelopes). Those are plugin-side, not
  skill-side.
- The `evolve-schema` skill in `deriva-skills` and the catalog audit
  design doc (PR #11 in deriva-skills) are in the sibling plugin
  and are independently scheduled.

---

## Summary table

| Priority | What | Skills affected | Effort | Net |
|---|---|---|---|---|
| **P0** | Restore example correctness | `ml-data-engineering`, `manage-storage`, `dataset-lifecycle`, `debug-bag-contents` | 3-4h | Zero broken code |
| **P0** | v0.5.0 MCP-removal sweep | 15 files | 6-8h | Canonical lifecycle matches upstream |
| **P1** | Stale-but-works fixes | `deriva-ml-context`, `create-feature`, `write-hydra-config`, `execution-lifecycle`, `troubleshoot-execution`, `model-development-workflow` | 2-3h | Users write current-day code |
| **P2** | Capability uplift | 8 skills across `ml-data-engineering`, model + experiment, validate/preview/sort + filters | 4-5h | One round-trip where N+1 was the norm |
| **P3** | New-capability scaffolding (optional) | `troubleshoot-execution`, `using-deriva-mcp` | 1-2h | Schema-drift + offline-mode coverage |

Land PR-1 + PR-2 first. Everything else can wait without surfacing
errors to users.
