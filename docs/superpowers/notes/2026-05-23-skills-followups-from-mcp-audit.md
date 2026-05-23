# Skills follow-ups from the 2026-05-23 deriva-ml-mcp audit

Cross-repo follow-up note. Origin: deep audit of `deriva-ml-mcp`
recorded at
[`../../../deriva-ml-mcp/docs/audit-2026-05-23.md`](../../../../deriva-ml-mcp/docs/audit-2026-05-23.md).
The audit surfaced eight skill-side gaps the MCP plugin cannot fix
on its own (this repo owns the skill text), plus one architectural
shift in the MCP plugin (`v4.0.0`) whose user-facing consequences
have to land here.

When picking this up: **always test against the latest `deriva-ml`**
(at write time, v1.38.0; bump with `uv lock --upgrade-package deriva-ml`
and resync before running any skill against a live catalog).
Several findings depend on tools/parameters that landed in recent
`deriva-ml` releases (write-through description setters in v1.38.0,
`workflow_type` filter and `execution_rids` filter in 1.36.x).

---

## The v4.0.0 architectural shift

`deriva-ml-mcp` v4.0.0 removed all execution-mutating tools from the
MCP surface:

- `deriva_ml_create_execution`
- `deriva_ml_start_execution`
- `deriva_ml_commit_execution`
- `deriva_ml_abort_execution`
- `deriva_ml_update_execution`
- `deriva_ml_add_feature_values`
- `deriva_ml_create_execution_dataset`
- `deriva_ml_add_nested_execution`

Reason: executions must originate in the caller's local Python
environment. The workflow code lives in the user's git checkout,
feature staging writes to a per-process SQLite manifest, asset
upload needs local bytes, and the `with Execution(...) as exe:`
context manager owns the lifecycle. An MCP server can't participate
in any of that. Full architectural rationale is in
[`deriva-ml-mcp/CLAUDE.md`](../../../../deriva-ml-mcp/CLAUDE.md)
under "Stateless / bounded-resource rule for MCP operations" and in
the audit doc.

The MCP plugin still exposes read-only execution tools
(`list_executions`, `get_execution`, `find_workflow_executions`,
`list_execution_children`, `list_execution_parents`, `get_lineage`)
and the three execution resources (`/ml/executions`,
`/ml/execution/{rid}`, `/ml/lineage/{rid}`). The skill-side work is
to teach the local-Python pattern for the mutation half.

### Skills that need updates for v4.0.0

| Skill | What needs to change |
|---|---|
| `execution-lifecycle` | Currently the canonical lifecycle reference — but any prose pointing at MCP tools for create/start/commit/abort/etc. is now wrong. Rewrite the lifecycle section around the `with ml.create_execution(...) as exe:` context manager in user-local Python. The MCP read tools remain the right path for post-run observation. |
| `troubleshoot-execution` | Any "fix it by calling `commit_execution`" suggestions are out. Salvage flows already correctly say "Python-only" for `pending_summary` — extend the same framing to the full lifecycle. |
| `experiment-lifecycle` | Same surgical sweep as `execution-lifecycle`. |
| `create-feature` | Feature DEFINITION (schema) still uses `deriva_ml_create_feature` (MCP). Writing feature VALUES now goes through `exe.add_features(records)` inside the local context manager — was `deriva_ml_add_feature_values`. Update the worked examples. |
| `compare-model-runs` | Read-side; should be unaffected. Spot-check the prose for any stale references. |
| `model-development-workflow` | Has the end-to-end pattern — likely contains both the workflow creation (still MCP) and the execution authorship (now local). The MCP/local boundary needs to be made visible. |
| `ml-data-engineering` | Same audit pass as `model-development-workflow`. |

### New skill that doesn't exist yet

The audit recommended a `work-with-executions` skill (mirroring
`work-with-assets` in `deriva-skills`) that GENERATES the local-Python
snippet a user runs to drive an execution. The existing
`execution-lifecycle` skill is the natural home for this content if
a new skill is too much overhead — either approach works as long as
the user (and the LLM driving them) learns the local-Python pattern
when they need to author an execution.

---

## Eight skill gaps surfaced by the audit (Lens B)

These pre-date v4.0.0 and remain open. Each is a single-skill fix
unless noted. Sorted by severity / leverage.

| # | Skill | Gap | Action |
|---|-------|-----|--------|
| 1 | `manage-storage` (line ~182) | Documents `deriva_ml_cache_dataset(asset_rid=...)` — **the parameter doesn't exist** (tool takes only `dataset_rid`). Earlier in the same skill (~line 37) correctly defers asset download to Python. | Delete the hallucinated example; reuse the line-37 Python pattern. Verify no other skill copied this hallucination. |
| 2 | `write-hydra-config` (centerpiece) | Documents `deriva_ml_validate_config_file` and `deriva_ml_bootstrap_config` as "planned." Both exist on MCP today. The skill's 5-tool composition recipe and the N-round-trip bootstrap walk are now obsolete fallbacks. | Promote both tools to the lead path; keep the composition recipe as a "for granular debugging" footnote. Drop the "no asset analog to `validate_dataset_specs` yet" claim at line ~430 — `validate_config_file` IS that analog. |
| 3 | `deriva-ml-context` (always-on) | Doesn't steer at `deriva_ml_create_vocabulary` (ML-aware: curie-prefix scoping + navbar refresh). Only `create-feature` knows it exists; every other vocab-touching skill points at the generic `create_vocabulary`. Wrong on deriva-ml catalogs. | Add a one-liner to `deriva-ml-context/SKILL.md`: "On a deriva-ml-loaded catalog, prefer `deriva_ml_create_vocabulary` over the generic `create_vocabulary`." Update `troubleshoot-execution`'s "Vocabulary term missing" section to follow that rule. |
| 4 | `troubleshoot-execution`, `experiment-lifecycle` | Don't surface the `workflow_type=` filter on `deriva_ml_list_executions`. Currently force the LLM to paginate + post-filter where one server-side filter does the job. | Add a `workflow_type=` example in each. The filter is the cross-workflow "show me every Training execution" answer. |
| 5 | All skills with "read the orientation first" prose | Reference MCP prompts (clients skip them) or inline summaries. The static cold-start resources `deriva://deriva-ml/getting-started` and `deriva://deriva-ml/concepts` are fetched by resource-walking clients; only `using-deriva-mcp` references them. | First-line "fetch this resource" pointer in `dataset-lifecycle`, `execution-lifecycle`, `experiment-lifecycle`, etc. The prompt name stays as the fallback channel. |
| 6 | `model-development-workflow`, `troubleshoot-execution` | Don't surface the `execution_rids=` filter on `deriva_ml_list_feature_values` — the one-round-trip pattern for "feature X across these N executions." `compare-model-runs` and `experiment-lifecycle` use it correctly. | Cross-reference `compare-model-runs`'s worked example from the other two skills' relevant sections. |
| 7 | `manage-storage`, `dataset-lifecycle`, `execution-lifecycle` | Route every "preview before download" through the `deriva_ml_bag_info` tool; don't reference the snapshot-form `deriva://catalog/{h}/{c}/ml/dataset/{rid}/bag-preview` resource. Only `debug-bag-contents` mentions it. | Add the resource as the lead "preview-the-current-version" path; keep the tool for the version-pinned / exclude-tables case. |
| 8 | `using-deriva-mcp` | This skill was the audit's good model — references new tools, new resources, the cold-start statics. As the v4.0.0 changes land, this skill should also pick up the "execution lifecycle = local Python" framing as a top-level concept. | Add an "execution lifecycle" section pointing at the deriva-ml repo's `user-guide/executions.md` doc. |

---

## Working notes when you pick this up

1. **Bump deriva-ml to current** before testing anything:
   ```bash
   cd /path/to/deriva-ml-mcp  # or wherever you test from
   uv lock --upgrade-package deriva-ml --upgrade-package deriva
   uv sync --extra dev --reinstall-package deriva-ml --reinstall-package deriva
   ```
   Several gaps depend on new parameters that landed in 1.36.x and
   later; testing against a stale `deriva-ml` will give false negatives.

2. **Rebuild the dockerized MCP server** if testing against
   dev-localhost — the rebuild script is at
   `deriva-ml-mcp/scripts/rebuild-deriva-docker-mcp.sh`. Pulls
   the latest `deriva-ml-mcp@main` (which is v4.0.0+) and the
   latest `deriva-ml@main`.

3. **The `manage-storage` cache_dataset hallucination (#1)** is the
   only outright correctness bug. The other seven are
   leverage/discoverability — skills work today, they just don't
   consume the full plugin surface optimally.

4. **Cross-repo sync rule.** When updating skills that contain
   conceptual content also present in `deriva-ml-mcp/src/deriva_ml_mcp/prompts.py`
   (`deriva-ml-context/SKILL.md` is the load-bearing one), check
   the plugin-side prompt for matching edits. The lockstep is
   documented at the top of `prompts.py` and in
   `deriva-ml-mcp/CLAUDE.md` "Cross-Repo Sync" section.

5. **The audit doc itself** lives at
   `deriva-ml-mcp/docs/audit-2026-05-23.md`. Read it for the
   rationale; this note is the action list extracted from it.
