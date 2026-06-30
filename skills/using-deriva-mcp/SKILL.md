---
name: using-deriva-mcp
description: "ALWAYS load before the first deriva MCP call in any conversation — it carries the cold-start procedure (call the deriva_ml_primer tool, then fetch individual guides on demand; full step-by-step in the skill body). Triggers on: first-time use of mcp__deriva__ tools/resources, any catalog inspection request ('list / show / browse / verify / inspect catalog', 'check schema', 'check feature values'), AND read-shaped questions that don't look like 'browse' on their face ('what X are in catalog N', 'what X are available', 'how many X', 'which workflows / features / vocabularies / datasets / executions / assets exist'). Do NOT trigger for shell-only workflows (load-cifar10 CLI, deriva-ml Python API only, deriva-ml-run) that bypass MCP entirely."
disable-model-invocation: false
---

# Bootstrapping the deriva MCP Server: call the primer first

You are about to make a call against a Deriva catalog via the deriva MCP
server (`mcp__deriva__*` tools or `deriva://...` resources, or under
whatever name the connecting MCP server is registered). **Before the first
such call in a conversation, call the `deriva_ml_primer` tool.** One call
returns the DerivaML agent guidelines and a manifest of the guides
available for deeper tool groups. This skill is the trigger; the primer is
the bootstrap.

> **Stop before calling a list-style tool: check the resource templates table first.**
> Almost every read-shaped question against a catalog ("what datasets are in 46?", "what workflow types are available?", "what features exist on Image?") has a matching `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/...` resource URI. The resource is **cached, page-free, returns a leaner payload, and produces no audit-log entries** — strictly preferable for read-only questions. The resource templates table in the Reference section at the end of this skill enumerates the templates the deriva-ml MCP plugin registers. If you find yourself reaching for `deriva_ml_list_datasets`, `deriva_ml_list_executions`, `deriva_ml_list_features`, `list_vocabulary_terms`, etc., pause and confirm there isn't a resource that would answer the same question.

## The one-call cold-start

**Step 1 — call the primer.** It is exposed three ways; use whichever your
client surfaces:

- As a **tool**: `deriva_ml_primer()` (agents that auto-call tools should
  call it on the first turn — the docstring is self-directing).
- As a **prompt / slash command**: `/<server>:deriva_ml_primer` for manual
  invocation.
- As a **resource**: `ReadMcpResourceTool(server="<name>", uri="deriva://deriva-ml/primer")`.

All three return identical text: a compact operating contract (the five
abstractions, the `(hostname, catalog_id)` rule, the query-strategy
ladder summary, the pagination preflight→page→advance contract, the
error envelope, the local-Python mutation boundary) plus a one-line
manifest of on-demand guides. The primer is deliberately small (~1K
tokens); the full conceptual and operational guides are fetched on
demand (Step 2), not inlined.

Replace `<server>` / `<name>` with whatever the user's MCP server is
registered as — commonly `deriva`, sometimes `dev-localhost`, sometimes
project-specific. If `ListMcpResourcesTool({server: "<name>"})` returns
successfully, that's the right name.

**Step 1.5 — confirm the server is authenticated to the target catalog.**
Before the first *catalog* operation against a host/catalog (especially a fresh
session, a host you haven't touched, or after 401-looking failures), call
`deriva_ml_check_authentication(hostname, catalog_id)`. It returns
`{"authenticated": bool, "identity": {...}|null}` — the **MCP server's** session
for *that* catalog (the server holds the per-request credential, not your local
machine). `authenticated: false` → tell the user they're not logged in before you
fan out catalog reads/writes; a connection/DNS/TLS failure returns `{"error": ...}`
instead (a different problem — that's `/deriva:troubleshoot-deriva-errors`). This
confirms *authentication*, not *authorization* — see
`/deriva-ml:deriva-ml-context` → "Confirm authentication before the first catalog
operation" for the canonical rule (and the parallel `ml.is_authenticated()` check
on the Python side).

**Step 2 — fetch a guide on demand, only when you reach its tool group.**
The primer's manifest names the available guides but does not inline their
bodies. Fetch a guide the first time you are about to use the tools it
covers, and not before:

| If your first call uses... | Fetch this guide |
|----|----|
| `query_attribute`, `query_aggregate`, `count_table` | `/<server>:query_guide` |
| `get_entities`, `insert_entities`, `update_entities`, `delete_entities` | `/<server>:entity_guide` |
| `get_table_annotations`, `set_*_display`, `set_visible_columns`, etc. | `/<server>:annotation_guide` |
| `create_catalog`, `clone_catalog`, `get_schema`, `get_catalog_info` | `/<server>:catalog_guide` |

For guides this plugin owns, use `deriva_ml_get_guide(name)` instead of the slash
command. `deriva_ml_get_guide` serves `deriva_ml_concepts` and
`deriva_ml_getting_started` directly — the primer does NOT inline them
(it carries only the compact contract), so fetch whichever you need:
`deriva_ml_getting_started` before sustained tool use (pagination
details, the full query-strategy ladder + anti-patterns, curation
patterns), `deriva_ml_concepts` for the deeper conceptual frame. Both
appear in the primer's manifest with the `deriva-ml` source. **Fetch
each guide once per conversation** — they are stable references, not
per-call context.

> The four generic-catalog guides above (`query_guide` / `entity_guide` /
> `annotation_guide` / `catalog_guide`) belong to the `deriva-mcp-core`
> server, and the foundation `deriva-skills` plugin carries the same cold-start
> discipline for them in `/deriva:using-deriva-mcp-core`. This skill is the
> DerivaML entry point that builds on it: it adds the `deriva_ml_primer`
> bootstrap and the `deriva://...deriva-ml/...` resource-first reads on top of
> the generic guide-before-tool-group routing. When both plugins are loaded,
> start here — you do not need to invoke the foundation skill separately.

## When this skill applies, and when it doesn't

**Applies** to any conversation that involves reading or mutating a Deriva catalog via the MCP surface — even if the user didn't explicitly say "use MCP":

- "Verify what's in catalog 8" — MCP-surface operation.
- "Check whether dataset RID 1-ABCD has the right members" — MCP-surface operation.
- "Build a model" where you reach for catalog state on the way — MCP-surface operation.
- "Show me the schema for `myproject:Image`" — MCP-surface operation.

**Does not apply** to:

- Shell-only invocations (`load-cifar10` CLI, `deriva-ml-run`, custom scripts that use the `deriva-ml` Python API directly). Those bypass the MCP server entirely and have their own orientation in the relevant skill (`/deriva-ml:setup-ml-catalog`, `/deriva-ml:execution-lifecycle`).
- Repeat MCP calls in the same conversation. Once you've read the orientation material, you've read it — don't re-fetch.
- Read-only catalog *resource* fetches against URIs you already understand (e.g., re-reading `deriva://catalog/<h>/<c>/deriva-ml/datasets` after you've done it once). The resource shape is established; no re-orientation needed.

## The MCP / local-Python boundary

The deriva-ml MCP surface is **observation + catalog-state mutation**, not execution authorship. Two whole classes of operation belong in user-local Python, not on the wire:

1. **Execution lifecycle.** Creating an Execution, opening its context manager, staging feature values, and committing output assets all require the user's git checkout (for workflow URL + commit hash), the local filesystem (for staged output files), and a per-process SQLite manifest (for feature-value staging). An MCP server can't participate in any of that. The pattern is `with ml.create_execution(config) as exe:` in a committed script, run via `deriva-ml-run`. The MCP surface still exposes read-only execution tools (`deriva_ml_list_executions`, `deriva_ml_get_execution`, `deriva_ml_get_lineage`, `deriva_ml_find_executions_consuming`, `deriva_ml_multirun_status`, `deriva_ml_list_execution_children`, `deriva_ml_list_execution_parents`, `deriva_ml_find_workflow_executions`) and the matching `deriva://catalog/{h}/{c}/deriva-ml/execution/...` resources for post-run observation — those stay on the wire. See `/deriva-ml:execution-lifecycle` for the script-template pattern.

2. **Bag materialization.** Downloading a dataset bag writes bytes to the caller's local cache directory. The MCP server has no shared filesystem with the caller, so any "warm the cache" MCP call would produce inaccessible bytes on the server's disk. The pattern is `ml.cache_dataset(spec)` in a committed script — see the `skills/manage-deriva-storage/scripts/warm_cache.py` template. The MCP surface keeps the **preview** path (`deriva://catalog/{h}/{c}/deriva-ml/dataset/{rid}/bag-preview` resource and `deriva_ml_bag_info` tool) because both return bounded inline rows the wire is good for. The denormalized-bag tool (`deriva_ml_denormalize_dataset`) stays too — its output is bounded inline rows; the cache_dataset it uses internally is an implementation detail the caller never sees.

The rule of thumb: if an operation needs **bytes on the caller's machine** or **the caller's git commit hash**, it's local Python.

## What you should NOT do

- **Skip the primer and hit a tool directly.** This is the failure mode this skill exists to prevent. Without the primer's getting-started contract, you will mis-paginate. Without `query_guide`, you will pass `schema` + `table` + `filter` to `query_attribute` instead of a `path` expression. Without the concepts frame, you will treat Datasets / Workflows / Executions as raw tables and mutate them with `insert_entities` (bypassing the lifecycle machinery — see the inheritance-with-override rule in `/deriva-ml:deriva-ml-context`).
- **Treat slash-command guide prompts as required for every call.** Read each one once per conversation. They are stable references, not per-call setup.
- **Confuse the generic-catalog slash-command guides with the primer.** The four `deriva-mcp-core` guides (`query_guide` / `entity_guide` / `annotation_guide` / `catalog_guide`) have prompt-only delivery — fetch them via `/<server>:<name>`. The primer is delivered three ways (tool / prompt / resource) and inlines the deriva-ml orientation; don't treat the core guides as if they had a resource form.
- **Re-read the orientation when nothing changes.** If you've called the primer once this conversation, you've covered the cold-start. Don't refetch.

## When the upstream material disagrees with a skill

The upstream MCP server's prompts and resources are the **canonical source of truth** for how to use the server. Skills in this plugin (including `/deriva-ml:deriva-ml-context`) summarize and reinforce the conventions, but if a skill and the upstream material conflict, **the upstream material wins** — the server is the deployment that actually runs the calls. Report the discrepancy back so the skill can be updated (or so a server-side change can be reflected in skills), but don't override the server based on a stale skill.

## Relationship to other skills

- **`/deriva-ml:deriva-ml-context`** *(always-loaded sibling)* — the canonical statement of the resource-vs-tool rule, the five abstractions, the inheritance-with-override rule, and the entity resolution workflow. This skill makes sure the upstream-server orientation is read; that skill makes sure the conceptual frame is loaded. Both should be active before the first MCP call.
- **`/deriva:deriva-context`** *(always-loaded, deriva-skills plugin)* — the plugin-wide context for the generic Deriva catalog surface (the seven design pillars, stateless-model framing). Independent of this skill, but worth having loaded for any catalog work.
- **`/deriva-ml:troubleshoot-execution`** *(this plugin)* — if you hit `dependency-version-unsatisfied`, `no-matching-tag`, or other version-mismatch errors after reading the orientation material, the versioning section there carries the diagnosis steps.

## Reference

### Orientation surface (the primer)

- `deriva_ml_primer` — tool, prompt (`/<server>:deriva_ml_primer`), and resource (`deriva://deriva-ml/primer`); all three return the same primer text (agent guidelines + on-demand guide manifest). Start here instead of reading `deriva://deriva-ml/concepts` and `deriva://deriva-ml/getting-started` blind — the primer's manifest names them so you fetch the one you need on demand (it does NOT inline them; it carries only the compact contract).
- `deriva://deriva-ml/concepts`, `deriva://deriva-ml/getting-started` — still available individually if you want one without the other, but the primer is the preferred single entry point.
- `deriva://server/status` — server health / version info

### Catalog-scoped resource templates (NOT enumerated by `ListMcpResourcesTool` — read directly with `ReadMcpResourceTool`)

Substitute concrete values into the `{...}` placeholders before reading.
The `{hostname}` is the deriva server (e.g. `localhost`, `dev.eye-ai.org`),
`{catalog_id}` is the numeric catalog id (or alias / `id@snaptime`).
For an authoritative description of each resource's payload shape, see
the matching docstring in `deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/resources/ml.py`.

**Datasets**

| URI | Returns |
|---|---|
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/datasets` | all datasets (paginated) |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/dataset/{dataset_rid}` | single dataset summary + version history |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/dataset/{dataset_rid}/spec` | dataset specification (element types, etc.) |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/dataset/{dataset_rid}/bag-preview` | bag-download preview without materializing |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/dataset/{dataset_rid}/members` | dataset members (paginated) |

**Workflows & Executions**

| URI | Returns |
|---|---|
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/workflows` | all workflows (paginated) |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/workflow/{workflow_rid}` | single workflow (source URL, checksum, type) |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/executions` | all executions (paginated) |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/execution/{execution_rid}` | execution detail (inputs, outputs, durations, experiment) |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/lineage/{rid}` | full provenance walk from any Dataset / Execution / Asset RID |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/lineage-forward/{rid}` | forward lineage: executions that CONSUMED this Dataset / asset as input |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/workflow/{workflow_rid}/multirun-status` | status counts across one workflow's executions ("is the sweep done?") |

**Features, Assets, Vocabularies**

| URI | Returns |
|---|---|
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/features/{table_name}` | features defined on `{table_name}` |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/asset/{asset_rid}` | single asset metadata + download URL |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/assets/{schema}` | all assets in a schema |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/assets/{schema}/{asset_table}` | assets in one specific asset table |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/vocabularies/{schema}` | all vocabulary tables in a schema |
| `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/vocabularies/{schema}/{vocab_name}` | all terms in one vocabulary |

These templates are the read-side of the resource-vs-tool decision documented in `/deriva-ml:deriva-ml-context` — when a question is "what is the current state of X," prefer the resource over the equivalent list / get tool. Resources are cached, page-free, and produce no audit-log entries.

### deriva-mcp-core slash-command guides (read once per conversation, before first use of each tool group)

Written here as `/<server>:<name>` for brevity; Claude Code surfaces MCP
prompts under the fully-qualified form `/mcp__<server-name>__<name>` (e.g.
`/mcp__deriva__query_guide`) — both denote the same prompt.

- `/<server>:query_guide` — ERMrest query guide (path expressions, joins, aliases, pagination)
- `/<server>:entity_guide` — entity CRUD conventions, preflight count rule, display rules
- `/<server>:annotation_guide` — Chaise display annotation operations
- `/<server>:catalog_guide` — catalog-level operations (create, clone, schema introspection)

### Discovery helpers

- `ListMcpResourcesTool({server: "<name>"})` — confirm the server name and list **concrete** resources. **Does not list templates** — the catalog-scoped resource templates above (the `deriva://catalog/.../deriva-ml/...` table) are served via `resources/templates/list`, which Claude Code does not surface; read them directly with `ReadMcpResourceTool`. If `ListMcpResourcesTool` returns only the 2-3 static orientation entries, that is this gap, not an empty catalog.
