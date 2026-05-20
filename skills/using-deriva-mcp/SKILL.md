---
name: using-deriva-mcp
description: "ALWAYS load before the first deriva MCP call in any conversation — read the deriva_ml_getting_started and deriva_ml_concepts orientation resources from the deriva MCP server before reaching for tools, and the relevant deriva-mcp-core guide prompt (query_guide / entity_guide / annotation_guide / catalog_guide) before first use of each generic catalog tool group. The deriva-ml-context skill teaches the resource-vs-tool rule itself; this skill enforces the cold-start discipline of reading the upstream MCP server's own orientation material so that pagination, (hostname, catalog_id) conventions, error envelopes, and resource URI patterns are correctly understood before tools fire. Triggers on: any first-time use of mcp__deriva__ tools or resources in a conversation, 'list datasets', 'show datasets', 'browse catalog', 'verify catalog', 'check schema', 'inspect catalog', 'check feature values', any catalog inspection request. ALSO triggers on read-shaped catalog questions that don't look like 'browse' on their face: 'what X are in the catalog', 'what X are available', 'show me the X', 'list the X', 'what's in catalog N', 'how many X are there', 'which workflows / features / vocabularies / datasets / executions / assets exist' — these are exactly the questions a resource URI is the right answer to, and the failure mode this skill exists to catch is reflexively reaching for a list-style tool (deriva_ml_list_datasets, deriva_ml_list_executions, list_vocabulary_terms, etc.) before checking the resource templates table. Do NOT trigger for shell-only workflows (load-cifar10 CLI, deriva-ml Python API only, deriva-ml-run) that bypass the MCP surface entirely."
disable-model-invocation: false
---

# Reading the deriva MCP Server's Orientation Material First

You are about to make a call against a Deriva catalog via the deriva MCP server (`mcp__deriva__*` tools or `deriva://...` resources, or under whatever name the connecting MCP server is registered). **Before the first such call in a conversation, read the upstream MCP server's own orientation material.** This skill exists because the MCP server's `initialize` instruction asks every client to do this, but Claude Code does not automatically inject those orientation prompts into your context — you have to fetch them yourself.

This skill is the trigger; the upstream prompts/resources are the rules. The conceptual frame for resource-vs-tool routing lives in the always-on `/deriva-ml:deriva-ml-context` skill — this skill makes sure you've actually read the server's own cold-start material before relying on that frame.

> **Stop before calling a list-style tool: check the resource templates table first.**
> Almost every read-shaped question against a catalog ("what datasets are in 46?", "what workflow types are available?", "what features exist on Image?") has a matching `deriva://catalog/{hostname}/{catalog_id}/ml/...` resource URI. The resource is **cached, page-free, returns a leaner payload, and produces no audit-log entries** — strictly preferable for read-only questions. The resource templates table in the Reference section at the end of this skill enumerates the ~15 templates the deriva-ml MCP plugin registers. If you find yourself reaching for `deriva_ml_list_datasets`, `deriva_ml_list_executions`, `deriva_ml_list_features`, `list_vocabulary_terms`, etc., pause and confirm there isn't a resource that would answer the same question. Reach for a tool only when the resource shape genuinely doesn't fit (e.g. you need a filter the resource doesn't expose, or pagination beyond what the resource page returns).

## The two-minute cold-start

**Step 1 — Read the DerivaML domain orientation.** Two resources, exposed by the deriva-ml-mcp plugin:

```
ReadMcpResourceTool(server="<server-name>", uri="deriva://deriva-ml/concepts")
ReadMcpResourceTool(server="<server-name>", uri="deriva://deriva-ml/getting-started")
```

Replace `<server-name>` with whatever the user's MCP server is registered as — commonly `deriva`, sometimes `dev-localhost`, sometimes something project-specific. If `ListMcpResourcesTool({server: "<name>"})` returns successfully, that's the right name.

> **`ListMcpResourcesTool` only enumerates concrete URIs, not templates.**
> Claude Code's `ListMcpResourcesTool` calls MCP's `resources/list` endpoint, which by protocol returns only resources with concrete URIs (no `{param}` placeholders). The deriva MCP server registers ~15 resource templates whose URIs *do* have placeholders (`deriva://catalog/{hostname}/{catalog_id}/ml/datasets`, etc.) — those are served via the separate `resources/templates/list` endpoint, which Claude Code does **not** surface. If `ListMcpResourcesTool` returns only 2–3 entries (the static orientation resources), that is the gap — **don't conclude that nothing else is available.** The full template inventory is in the "Reference" section at the end of this skill and inside the `deriva://deriva-ml/getting-started` resource. Read either to know what URIs you can `ReadMcpResourceTool` against.

- `deriva://deriva-ml/concepts` — the five core abstractions (Dataset, Workflow, Execution, Feature, Asset), the provenance principle, the vocabulary-extension pattern. Read **first** if you don't already have a DerivaML mental model.
- `deriva://deriva-ml/getting-started` — the `(hostname, catalog_id)` rule (mandatory on every call), the pagination contract (preflight → page → advance), the resource-vs-tool decision, error envelope conventions, the discovery-via-resources orientation.

Both are the same text the MCP server exposes as the `deriva_ml_concepts` and `deriva_ml_getting_started` **prompts** — the resource form was added explicitly so resource-walking clients (like the agent here) discover them without going through the prompt subsystem. Either path delivers the same canonical content.

**Step 2 — Read the relevant tier-1 catalog guide before first use.** The generic catalog operations (in `deriva-mcp-core`, distinct from the deriva-ml plugin above) ship four guide prompts. These have **no resource equivalent**; they must be invoked as slash commands. Read whichever applies to the tool group you're about to use:

| If your first call uses... | Read this slash command first |
|----|----|
| `query_attribute`, `query_aggregate`, `count_table` | `/mcp__<server-name>__query_guide` |
| `get_entities`, `insert_entities`, `update_entities`, `delete_entities` | `/mcp__<server-name>__entity_guide` |
| `get_table_annotations`, `get_column_annotations`, `set_*_display`, `set_visible_columns`, `add_visible_column`, etc. | `/mcp__<server-name>__annotation_guide` |
| `create_catalog`, `clone_catalog`, `delete_catalog`, `get_catalog_info`, `get_schema` | `/mcp__<server-name>__catalog_guide` |

You can invoke the slash command by typing `/` and selecting from the menu Claude Code surfaces, or by writing it directly into the conversation. **You only need to read each guide once per conversation** — they describe stable conventions, not per-call context.

## When this skill applies, and when it doesn't

**Applies** to any conversation that involves reading or mutating a Deriva catalog via the MCP surface — even if the user didn't explicitly say "use MCP":

- "Verify what's in catalog 8" — MCP-surface operation.
- "Check whether dataset RID 1-ABCD has the right members" — MCP-surface operation.
- "Build a model" where you reach for catalog state on the way — MCP-surface operation.
- "Show me the schema for `myproject:Image`" — MCP-surface operation.

**Does not apply** to:

- Shell-only invocations (`load-cifar10` CLI, `deriva-ml-run`, custom scripts that use the `deriva-ml` Python API directly). Those bypass the MCP server entirely and have their own orientation in the relevant skill (`/deriva-ml:setup-ml-catalog`, `/deriva-ml:execution-lifecycle`).
- Repeat MCP calls in the same conversation. Once you've read the orientation material, you've read it — don't re-fetch.
- Read-only catalog *resource* fetches against URIs you already understand (e.g., re-reading `deriva://catalog/<h>/<c>/ml/datasets` after you've done it once). The resource shape is established; no re-orientation needed.

## What you should NOT do

- **Skip the orientation and hit a tool directly.** This is the failure mode this skill exists to prevent. Without `deriva_ml_getting_started`'s pagination contract, you will mis-paginate. Without `query_guide`, you will pass `schema` + `table` + `filter` to `query_attribute` instead of a `path` expression. Without `deriva_ml_concepts`, you will treat Datasets / Workflows / Executions as raw tables and mutate them with `insert_entities` (bypassing the lifecycle machinery — see the inheritance-with-override rule in `/deriva-ml:deriva-ml-context`).
- **Treat slash-command guide prompts as required for every call.** Read each one once per conversation. They are stable references, not per-call setup.
- **Confuse the slash-command guides (tier-1, no resource equivalent) with the deriva-ml prompts (tier-2, also exposed as resources).** The tier-1 guides have prompt-only delivery; the tier-2 ones have a resource fallback because clients sometimes don't surface prompts.
- **Re-read the orientation when nothing changes.** If you've read `getting-started` and `concepts` once this conversation, you've covered the cold-start. Don't refetch.

## When the upstream material disagrees with a skill

The upstream MCP server's prompts and resources are the **canonical source of truth** for how to use the server. Skills in this plugin (including `/deriva-ml:deriva-ml-context`) summarize and reinforce the conventions, but if a skill and the upstream material conflict, **the upstream material wins** — the server is the deployment that actually runs the calls. Report the discrepancy back so the skill can be updated (or so a server-side change can be reflected in skills), but don't override the server based on a stale skill.

## Relationship to other skills

- **`/deriva-ml:deriva-ml-context`** *(always-loaded sibling)* — the canonical statement of the resource-vs-tool rule, the five abstractions, the inheritance-with-override rule, and the entity resolution workflow. This skill makes sure the upstream-server orientation is read; that skill makes sure the conceptual frame is loaded. Both should be active before the first MCP call.
- **`/deriva:deriva-context`** *(always-loaded, deriva-skills plugin)* — the plugin-wide context for the generic Deriva catalog surface (the seven design pillars, stateless-model framing). Independent of this skill, but worth having loaded for any catalog work.
- **`/deriva-ml:troubleshoot-execution`** *(this plugin)* — if you hit `dependency-version-unsatisfied`, `no-matching-tag`, or other version-mismatch errors after reading the orientation material, the versioning section there carries the diagnosis steps.

## Reference

### Orientation resources (concrete URIs, enumerated by `ListMcpResourcesTool`)

- `deriva://deriva-ml/concepts` — same content as the `deriva_ml_concepts` MCP prompt; resource form for resource-walking clients
- `deriva://deriva-ml/getting-started` — same content as the `deriva_ml_getting_started` MCP prompt; resource form for resource-walking clients
- `deriva://server/status` — server health / version info

### Catalog-scoped resource templates (NOT enumerated by `ListMcpResourcesTool` — read directly with `ReadMcpResourceTool`)

Substitute concrete values into the `{...}` placeholders before reading.
The `{hostname}` is the deriva server (e.g. `localhost`, `dev.eye-ai.org`),
`{catalog_id}` is the numeric catalog id (or alias / `id@snaptime`).
For an authoritative description of each resource's payload shape, see
the matching docstring in `deriva-ml-mcp/src/deriva_ml_mcp/resources/ml.py`.

**Datasets**

| URI | Returns |
|---|---|
| `deriva://catalog/{hostname}/{catalog_id}/ml/datasets` | all datasets (paginated) |
| `deriva://catalog/{hostname}/{catalog_id}/ml/dataset/{dataset_rid}` | single dataset summary + version history |
| `deriva://catalog/{hostname}/{catalog_id}/ml/dataset/{dataset_rid}/spec` | dataset specification (element types, etc.) |
| `deriva://catalog/{hostname}/{catalog_id}/ml/dataset/{dataset_rid}/bag-preview` | bag-download preview without materializing |
| `deriva://catalog/{hostname}/{catalog_id}/ml/dataset/{dataset_rid}/members` | dataset members (paginated) |

**Workflows & Executions**

| URI | Returns |
|---|---|
| `deriva://catalog/{hostname}/{catalog_id}/ml/workflows` | all workflows (paginated) |
| `deriva://catalog/{hostname}/{catalog_id}/ml/workflow/{workflow_rid}` | single workflow (source URL, checksum, type) |
| `deriva://catalog/{hostname}/{catalog_id}/ml/executions` | all executions (paginated) |
| `deriva://catalog/{hostname}/{catalog_id}/ml/execution/{execution_rid}` | execution detail (inputs, outputs, durations, experiment) |
| `deriva://catalog/{hostname}/{catalog_id}/ml/lineage/{rid}` | full provenance walk from any Dataset / Execution / Asset RID |

**Features, Assets, Vocabularies**

| URI | Returns |
|---|---|
| `deriva://catalog/{hostname}/{catalog_id}/ml/features/{table_name}` | features defined on `{table_name}` |
| `deriva://catalog/{hostname}/{catalog_id}/ml/asset/{asset_rid}` | single asset metadata + download URL |
| `deriva://catalog/{hostname}/{catalog_id}/ml/assets/{schema}` | all assets in a schema |
| `deriva://catalog/{hostname}/{catalog_id}/ml/assets/{schema}/{asset_table}` | assets in one specific asset table |
| `deriva://catalog/{hostname}/{catalog_id}/ml/vocabularies/{schema}` | all vocabulary tables in a schema |
| `deriva://catalog/{hostname}/{catalog_id}/ml/vocabularies/{schema}/{vocab_name}` | all terms in one vocabulary |

These templates are the read-side of the resource-vs-tool decision documented in `/deriva-ml:deriva-ml-context` — when a question is "what is the current state of X," prefer the resource over the equivalent list / get tool. Resources are cached, page-free, and produce no audit-log entries.

### deriva-mcp-core slash-command guides (read once per conversation, before first use of each tool group)

- `/mcp__<server-name>__query_guide` — ERMrest query guide (path expressions, joins, aliases, pagination)
- `/mcp__<server-name>__entity_guide` — entity CRUD conventions, preflight count rule, display rules
- `/mcp__<server-name>__annotation_guide` — Chaise display annotation operations
- `/mcp__<server-name>__catalog_guide` — catalog-level operations (create, clone, schema introspection)

### Discovery helpers

- `ListMcpResourcesTool({server: "<name>"})` — confirm the server name and list **concrete** resources. **Does not list templates** — see the warning in the cold-start section above.
