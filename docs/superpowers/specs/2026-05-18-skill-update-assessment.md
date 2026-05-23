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

**Update 2026-05-18 (verification pass).** Every finding below has
been ground-truthed against current source (deriva-ml + deriva-ml-mcp
HEAD) and re-grepped against the actual skill files. Specific
corrections logged in [§8 Verification log](#section-8--verification-log).
Two findings from the first agent pass were wrong and have been
struck (one false-alarm `increment_dataset_version` reference; one
mis-identified `ExecutionRecord` rename — the class **kept its name**
and was disambiguated by introducing a separate `ExecutionSnapshot`).
Five findings were under-counted and the assessment now reflects the
true per-file numbers (notably `manage-storage` has 6 `cache_dataset`
references, not the 1 the first pass found; `execution-lifecycle/
references/concepts.md` has 40 removed-tool references in a single
file).

**Refined PR-2 strategy (per user direction).** The replacement for
removed MCP execution-mutating tools is **not** "write Python inline
in the skill body" — it's **"use the skill's bundled `scripts/`
templates."** Reproducibility requires that the workflow URL +
checksum reference *committed code*, which means: skills should ship
committable script templates under `skills/<name>/scripts/`, and the
skill body should instruct the LLM to copy a template into
`src/scripts/<task>.py` in the user's project, edit the parameters,
commit, then run via `deriva-ml-run`. The proper-workflow + Execution
context manager rides along automatically because the template
encodes them. See [§4.4 The bundled-script-template pattern](#44-the-bundled-script-template-pattern--user-directed) for
details. **This changes the shape of PR-2 substantially** — it's now
"propagate `catalog-operations-workflow`'s script-template approach
to the skills that don't yet have one" rather than "rewrite skill
prose to teach context-manager Python from scratch."

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

All 9 tools were confirmed absent from
`deriva-ml-mcp/src/deriva_ml_mcp/` during verification. Per-file
mention counts (totals across .md files only):

| Removed tool | Total skill-file mentions | Replacement pattern |
|---|---:|---|
| `deriva_ml_create_execution` | **39** across 15 files | bundled script template using `with ml.create_execution(...) as exe:` (see §4.4) |
| `deriva_ml_start_execution` | **28** across 12 files | implicit in `__enter__` |
| `deriva_ml_commit_execution` | **35** across 12 files | `exe.upload_outputs()` after the `with` block |
| `deriva_ml_abort_execution` | **23** across 12 files | `exe.abort()` |
| `deriva_ml_update_execution` | **15** across 6 files | `exe.update_status(target, error=...)` |
| `deriva_ml_add_feature_values` | **19** across 10 files | `exe.add_features(records)` |
| `deriva_ml_create_execution_dataset` | **3** across 3 files | through `create_execution(datasets=[...])` |
| `deriva_ml_add_nested_execution` | **5** across 4 files | parent context wraps child `with ml.create_execution(...)` |
| `deriva_ml_cache_dataset` | **17** across 7 files | bundled script template using `ml.cache_dataset(spec)` (see §4.4) |

**Worst-affected files** (>10 stale mentions each):

- `execution-lifecycle/references/concepts.md` — **40 mentions** across 7 removed tools (9 `create_execution` + 8 `start_execution` + 8 `commit_execution` + 5 `abort_execution` + 3 `update_execution` + 1 `add_feature_values` + 1 `add_nested_execution` + 5 `cache_dataset`)
- `execution-lifecycle/references/workflow.md` — **29 mentions** across 8 tools
- `troubleshoot-execution/SKILL.md` — **15 mentions** across 4 tools
- `manage-storage/SKILL.md` — **9 mentions** total: 6× `deriva_ml_cache_dataset` at lines 21, 166, 174, 182, 201, 220, and 3× `deriva_ml_create_execution` at lines 23, 148, 203. The prior audit (B4) flagged only line 182; verification widens the scope substantially. Line 182 is the additional hallucination of `asset_rid=` (still wrong even were the tool present).

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

The method was renamed `_cache_features` (private) in v1.37
migration. Public callers should use `ml.feature_values(...)` (or
`deriva_ml_list_feature_values` MCP tool with the new
`execution_rids=` / `materialize_limit=` kwargs from §3.1).

Verified call sites (8 mentions across 4 files):

- `dataset-lifecycle/SKILL.md:217`
- `dataset-lifecycle/references/curated-subsets.md:103, 105, 110, 127`
- `dataset-lifecycle/scripts/generate_subset_template.py:41, 136`
  (user-facing copy-paste template — worst-class P0)
- `generate-scripts/SKILL.md:13, 24, 46, 152` (this skill GENERATES
  scripts — the templates it produces would themselves use the
  private API)
- `create-feature/SKILL.md:273` (single pointer reference)

```python
# Was:
ml.cache_features("Image", "Diagnosis")
# Is (Python):
ml.feature_values("Image", "Diagnosis")
# Or via MCP for inspection:
deriva_ml_list_feature_values(hostname, catalog_id, target_table="Image",
                              feature_name="Diagnosis",
                              execution_rids=[...],      # new kwarg
                              materialize_limit=10000)   # new kwarg
```

The two **scripts** (template files + the `generate-scripts` skill
that emits more like them) are user-facing copy-paste; shipping
templates that call a now-private API guarantees broken downstream
projects.

### 1.5 `upload_execution_outputs(...)` is legacy

Verification confirms **both methods still exist** on the `Execution`
class (`upload_execution_outputs` at execution.py:1468,
`upload_outputs` at execution.py:2307). Phase 1 introduced
`upload_outputs` as the canonical name; the legacy `upload_execution_outputs`
is retained for backward compat (CHANGELOG Phase 1 §Removed table:
"still present; superseded"). So this is **P1, not P0** — examples
still execute, they just use the old name.

Counts (re-verified):

- `troubleshoot-execution/SKILL.md` (7) + `references/execution-lifecycle.md` (9)
- `catalog-operations-workflow/references/script-patterns.md` (5)
- `dataset-lifecycle/references/workflow.md` (4)
- `new-model/references/runner-interface.md` (2)
- `manage-storage/SKILL.md` (2)
- `run-notebook/{SKILL.md,references/workflow.md}` (2 + 2)
- `generate-scripts/SKILL.md` (1)
- `create-feature/references/workflow.md` (1)

**Recommendation:** Land as part of the v0.5.0 sweep so each affected
file gets one coordinated edit (script templates, MCP-tool
replacements, and method-name standardization all in one pass).

### 1.6 ~~`increment_dataset_version` straggler~~ — VERIFICATION: FALSE ALARM

The first audit agent reported a straggler reference to
`deriva_ml_increment_dataset_version` in `debug-bag-contents/SKILL.md`.
Verification: the only mention is a single line of historical context
(line 278: `\`deriva_ml_release\` | Promote a dev period to a released
version (per ADR-0003 — replaces the old increment_dataset_version)`).
The skill correctly uses `deriva_ml_release` everywhere else and
documents the rename as historical context. No fix needed.

---

## Section 2 — P1: stale-but-works (user writes worse code than necessary)

### 2.1 `deriva_ml_create_vocabulary` is the right tool on deriva-ml catalogs

Verification refined this finding. `create-feature` already correctly
steers at `deriva_ml_create_vocabulary` (SKILL.md:82-87, workflow.md:32,
35, 183; the SKILL.md:306 entry in the tool-reference table is also
correct). The remaining stale references in
`create-feature/references/{concepts,workflow}.md` to
`ml.create_vocabulary(...)` are **Python API calls** (legitimate) and
not the generic MCP tool — false-positive from the first agent pass.

The **only** stale steering site is one row of one reference table:
`api-naming-conventions/SKILL.md:100`:

```
| `create_vocabulary` (MCP, core) | Create new vocabulary |
```

Replace with `deriva_ml_create_vocabulary` and note that it scopes
the curie prefix.

**Stronger fix that prevents future drift:** Add a one-line steering
note to `deriva-ml-context/SKILL.md` (always-on, plugin-wide reach):

> On a deriva-ml-loaded catalog, prefer `deriva_ml_create_vocabulary`
> over the generic `create_vocabulary` — it applies the
> `deriva-ml`-scoped curie prefix and refreshes the navbar.

Then the in-skill steering is implicit; future skills that touch
vocabulary creation inherit the discipline.

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

### 2.6 ~~`ExecutionRecord` → `ExecutionSnapshot` rename~~ — VERIFICATION: WRONG; SOFTENED TO P3 POLISH

The first audit agent claimed `ExecutionRecord` had been renamed
`ExecutionSnapshot` and that `execution-lifecycle/references/concepts.md`
was stale. **This is wrong.** What actually happened in the H3
disambiguation (per CHANGELOG):

- The original **catalog-backed** `ExecutionRecord` (live, mutable,
  ERMrest) **kept its name** — still exists at
  `deriva_ml/execution/execution_record.py:53`.
- A **separate** frozen value-object class (was internally
  `_ExecutionRecordV2`) was renamed to `ExecutionSnapshot`
  (SQLite-backed, frozen Pydantic model) and lives at
  `deriva_ml/execution/execution_snapshot.py:48`.
- The two coexist with different semantics. `ml.list_executions(...)`
  and `ml.find_incomplete_executions()` return `ExecutionSnapshot`;
  `asset.list_executions()` and similar return `ExecutionRecord`.

The skill's four references to `ExecutionRecord` in
`execution-lifecycle/references/concepts.md` (lines 73, 83, 298, 373)
are **all describing the live catalog-backed type** and remain
correct. The skill does **not** mention `ExecutionSnapshot`, which
is a missing-capability gap (P3 polish — worth a one-paragraph note
distinguishing the two classes, but no error today).

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

### 4.4 The bundled-script-template pattern — user-directed

**Provenance is the reason MCP execution-mutating tools were removed
in v0.5.0.** A real workflow record carries a URL + checksum that
identifies the code that ran. MCP-driven Python written in a model
turn is by definition uncommitted — there is no URL, the checksum
is meaningless, and the execution has provenance metadata that lies
about reproducibility.

The replacement pattern that **does** preserve provenance is:

1. **Skill bundles a runnable template** under
   `skills/<name>/scripts/<task>.py`. The template encodes the
   `with ml.create_execution(config, workflow=workflow, dry_run=...)
   as execution:` context manager, the right `ExecutionConfiguration`
   shape, the `execution.upload_outputs()` (post-`with`) call, and
   typed argparse parameters (`--hostname`, `--catalog-id`,
   `--workflow-type`, `--dry-run`, etc.).
2. **The skill body instructs the LLM** to:
   - Copy the template to `src/scripts/<task>.py` in the user's
     project.
   - Edit only the parameters the user names — vocab terms, asset
     RIDs, feature definitions, etc.
   - Commit the edited script. The workflow URL + checksum now
     resolve.
   - Run via `deriva-ml-run src/scripts/<task>.py --dry-run` first,
     then for real.
3. **MCP tools remain** for the observation half (reading the
   resulting execution / dataset / workflow records, listing
   children, walking lineage). MCP is the *observation surface*;
   committed scripts are the *authorship surface*.

**This pattern already exists** in `catalog-operations-workflow/
references/script-patterns.md` for a half-dozen common operations
(dataset creation, dataset splitting, feature creation +
population, ETL load). The PR-2 work is **not** "rewrite skill prose
to teach Python from scratch" — it's:

| For each skill in PR-2's 15-file scope | Action |
|---|---|
| **`execution-lifecycle`** | Bundle 3-4 templates (basic execution, nested execution, salvage, crash-recovery) under `skills/execution-lifecycle/scripts/`. Skill body becomes "use template X for task Y, edit these 3 params, commit + run." |
| **`troubleshoot-execution`** | Bundle a salvage-runner template. Skill body keeps its diagnostic Q&A but routes mutating recovery actions to the template. |
| **`create-feature`** | Bundle `populate_feature_values.py` (already exists informally in `references/workflow.md` — promote to `scripts/`). |
| **`work-with-assets`** | Bundle `upload_asset.py`, `download_asset.py` templates (pattern already exists in the `work-with-assets` skill in `deriva-skills`). |
| **`manage-storage`** | Bundle `warm_cache.py` (replaces the lost `deriva_ml_cache_dataset` MCP tool with a committed script). |
| **`model-development-workflow`** | Should reference templates from the other skills, not re-bundle. |
| **`dataset-lifecycle`** | Already has `scripts/`; extend with templates that match the v0.5.0-removed dataset-creation flow. |

**Net architecture**: ~10 new template files across ~6 skills + the
skill-body rewrites that route the LLM to them. Reproducible by
construction because the template *is* the workflow's source of truth.

**Cross-reference**: `generate-scripts/SKILL.md` already exists with
the meta-pattern ("here's how to generate well-formed deriva-ml
scripts"). The work in PR-2 is the inverse — instead of asking the
LLM to generate a fresh script each time, *ship* the canonical
template and have the LLM edit + commit + run it.

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

### PR-2: P0 — v0.5.0 MCP-removal sweep (template-based, per §4.4)

**Two sub-PRs** (PR-2a + PR-2b) so the template authoring lands
before the skill-body rewrites that route to them. Splitting also
keeps each PR honestly reviewable.

**PR-2a — Bundled templates (3-4 hours)**:

- Author `skills/execution-lifecycle/scripts/{basic_execution,
  nested_execution, salvage_execution, crash_recovery}.py` —
  4 canonical templates following the `catalog-operations-workflow/
  references/script-patterns.md` shape.
- Author `skills/create-feature/scripts/populate_feature_values.py` —
  promote the `references/workflow.md` example to a runnable file.
- Author `skills/manage-storage/scripts/warm_cache.py` — replaces
  the removed `deriva_ml_cache_dataset` MCP path.
- Author `skills/troubleshoot-execution/scripts/salvage_runner.py` —
  the salvage-flow template the skill currently inlines.
- Each script: typed argparse, `--dry-run` mandatory, full
  `with ml.create_execution(config, workflow=workflow,
  dry_run=args.dry_run) as execution:` shape, `execution.upload_outputs()`
  post-`with`, module docstring explaining the use case.

**PR-2b — Skill-body sweep (5-6 hours)**:

- §1.1 across 15 files. Per file: replace each removed-tool reference
  with "copy `<template-path>`, edit `<params>`, commit, run".
  Add a "Bundled templates" subsection at the top of each affected
  skill pointing at the PR-2a scripts.
- §1.5 standardize on `exe.upload_outputs(...)` in the same coordinated
  per-file edit.
- §4.1 the canonical "MCP-reads-templates-for-writes" paragraph in
  `deriva-ml-context/SKILL.md`.

Total PR-2 effort: 8-10 hours (slight increase over original estimate
to cover template authoring; pays back in lower drift cost forever
after — templates are unit-testable, skill prose isn't).

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

---

## Section 8 — Verification log

Every claim above was ground-truthed against current source after
the first agent pass. Recorded here so the next reader knows which
findings were re-confirmed and which were corrected.

### Verified true (no change)

| Finding | What was checked | How |
|---|---|---|
| §1.1 v0.5.0 9-tool removal | All 9 absent from `deriva-ml-mcp/src/deriva_ml_mcp/` | `grep "def deriva_ml_<tool>"` returns no hits for each |
| §1.1 stale-mention counts per skill | Re-grep'd, totals adjusted upward | Per-tool, per-file grep loop |
| §1.2 restructure_assets rename | `targets`, `target_transform`, `missing` are the current kwargs; `group_by` + `value_selector` removed | AST inspection of `src/deriva_ml/dataset/dataset_bag.py:1445` |
| §1.3 cache_dataset hallucination | `manage-storage:182` confirmed; tool now accepts only `dataset: DatasetSpec` | Read line 182; read `cache_dataset` signature at `core/mixins/dataset.py:552` |
| §1.4 cache_features privacy | Method is `_cache_features` (private) at `core/base.py:929`; public replacement is `feature_values` at `core/mixins/feature.py:378` | grep + read |
| §2.2 write-hydra-config "planned" | Both tools registered in deriva-ml-mcp; skill still labels them "planned" at 4 sites (lines 3, 19, 377, 389, 430). Internal inconsistency: line 488 actually uses `validate_config_file` | grep + read |
| §2.3 framework adapters | `as_torch_dataset` at `dataset_bag.py:1090`; `as_tf_dataset` at `dataset_bag.py:1264` | grep |
| §2.4 metrics_file | Method at `execution.py:1679` | grep |
| §3.1 feature_values kwargs | `(self, table, feature_name, selector, materialize_limit, execution_rids)` confirmed via AST | AST inspection |
| §3.2 workflow_type filter | `deriva_ml_list_executions(..., workflow_type, ...)` confirmed in tool source | Read tool definition |
| §3.3 find_*(sort=) | All three of `find_executions`, `find_datasets`, `find_workflows` accept `sort=` | AST inspection |
| §3.5 bag-preview resource | `@ctx.resource("deriva://catalog/{hostname}/{catalog_id}/ml/dataset/{dataset_rid}/bag-preview")` at `resources/ml.py:449` | grep |
| §3.6 cold-start resources | `deriva://deriva-ml/getting-started` at `resources/ml.py:344`; `deriva://deriva-ml/concepts` at `resources/ml.py:357` | grep |
| §3.7 schema pin/diff | All 4 methods exist in `core/base.py` (604, 657, 668, 684) | grep |
| §3.8 ConnectionMode + CatalogStub | `core/connection_mode.py:14`; `core/catalog_stub.py:27`; `DerivaMLReadOnlyError` exported | grep |
| §3.9 Asset_Role auto-tags | `core/enums.py:93, 179, 180` — `Asset_Role`, `Input_File`, `Output_File` all present | grep |
| "No-findings" claims | Confirmed no skill references any of: prefetch_dataset, add_page, user_list, globus_login, retrieve_rid, AssetRIDConfig, asset_types == filter | grep loop |

### Corrected from first agent pass

| Finding | Original claim | Verified reality | Resolution |
|---|---|---|---|
| §1.6 `increment_dataset_version` in `debug-bag-contents` | "Single-line fix" | Only one mention, and it's historical context next to the correct `deriva_ml_release` reference (line 278). The skill is correct. | Struck §1.6; noted as FALSE ALARM |
| §2.1 vocab steering — stale in multiple files | `create-feature/references/{concepts,workflow}.md` cited as stale | Those files contain `ml.create_vocabulary(...)` which is the **Python API** (legitimate), not the MCP tool. Only stale steering site is `api-naming-conventions/SKILL.md:100` (a row of a reference table) | Narrowed §2.1 to a single one-line fix |
| §2.6 `ExecutionRecord` → `ExecutionSnapshot` rename | "Three-line fix in concepts.md" | The two classes **coexist** with different semantics. `ExecutionRecord` (live, catalog-backed) kept its name; `ExecutionSnapshot` is a separate new class for the SQLite-backed frozen-value-object role. The four `ExecutionRecord` references in `execution-lifecycle/references/concepts.md` are all describing the live type and remain correct. | Struck §2.6's break-claim; downgraded to P3 polish opportunity to document the two classes' distinction |
| §1.4 cache_features scope | Two helper scripts + `dataset-lifecycle/SKILL.md` line | Actually 8 mentions across 4 files including `generate-scripts/SKILL.md` (which itself generates more scripts that would use the private API — compounding risk). Widened scope. | Expanded the §1.4 file list |
| §1.5 upload_execution_outputs status | Implied to be a clean rename | Both methods coexist on the `Execution` class; legacy is retained for back-compat. Examples still execute. | Re-graded from possibly-P0 to firmly-P1 |
| §1.1 per-file count for `manage-storage` | "1 cache_dataset reference (line 182)" | Actually 6 cache_dataset references (lines 21, 166, 174, 182, 201, 220) + 3 create_execution references (lines 23, 148, 203) | Restated; widened scope to "section rewrite", not "line fix" |

### Methodology

- **Source-level verification.** For every removed-tool claim, I ran
  `grep -rn "def $tool"` in `deriva-ml-mcp/src/`. For every renamed/
  new method, I either AST-inspected the function signature or
  grep'd the class definition.
- **Skill-level verification.** For every claim of staleness in a
  skill file, I either ran `grep -n` on that file or read the lines
  directly with the Read tool. No claim about a specific file:line
  in the doc is unconfirmed.
- **Cross-checked the agent's "no findings" assertions** by grep'ing
  each of: prefetch_dataset, add_page, user_list, globus_login,
  retrieve_rid, AssetRIDConfig, `asset_types ==` patterns,
  `ExecutionStatus.<lowercase>` patterns. All confirmed clean.

### What this verification did NOT do

- Did not run any skill end-to-end against a live catalog. The
  staleness analysis is static.
- Did not exhaustively cross-check every paragraph of every skill
  against every method in deriva-ml — only the changes named in the
  migration guide + CHANGELOG.
- Did not check whether the skill text describes correct behavior at
  every named API; only whether the named APIs exist + have the
  documented signature.

A future verification pass should add at least one end-to-end test
("instruct LLM to perform task X using only this skill; observe
where it gets stuck") — but that's better scoped as a `/skill-creator`
benchmark run after PR-2 lands.
