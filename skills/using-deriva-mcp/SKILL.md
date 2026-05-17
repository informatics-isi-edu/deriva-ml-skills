---
name: using-deriva-mcp
description: "ALWAYS load before the first deriva MCP call in any conversation — read the deriva_ml_getting_started and deriva_ml_concepts orientation resources from the deriva MCP server before reaching for tools, and the relevant deriva-mcp-core guide prompt (query_guide / entity_guide / annotation_guide / catalog_guide) before first use of each generic catalog tool group. The deriva-ml-context skill teaches the resource-vs-tool rule itself; this skill enforces the cold-start discipline of reading the upstream MCP server's own orientation material so that pagination, (hostname, catalog_id) conventions, error envelopes, and resource URI patterns are correctly understood before tools fire. Triggers on: any first-time use of mcp__deriva__ tools or resources in a conversation, 'list datasets', 'show datasets', 'browse catalog', 'verify catalog', 'check schema', 'inspect catalog', 'check feature values', any catalog inspection request. Do NOT trigger for shell-only workflows (load-cifar10 CLI, deriva-ml Python API only, deriva-ml-run) that bypass the MCP surface entirely."
disable-model-invocation: false
---

# Reading the deriva MCP Server's Orientation Material First

You are about to make a call against a Deriva catalog via the deriva MCP server (`mcp__deriva__*` tools or `deriva://...` resources, or under whatever name the connecting MCP server is registered). **Before the first such call in a conversation, read the upstream MCP server's own orientation material.** This skill exists because the MCP server's `initialize` instruction asks every client to do this, but Claude Code does not automatically inject those orientation prompts into your context — you have to fetch them yourself.

This skill is the trigger; the upstream prompts/resources are the rules. The conceptual frame for resource-vs-tool routing lives in the always-on `/deriva-ml:deriva-ml-context` skill — this skill makes sure you've actually read the server's own cold-start material before relying on that frame.

## The two-minute cold-start

**Step 1 — Read the DerivaML domain orientation.** Two resources, exposed by the deriva-ml-mcp plugin:

```
ReadMcpResourceTool(server="<server-name>", uri="deriva://deriva-ml/concepts")
ReadMcpResourceTool(server="<server-name>", uri="deriva://deriva-ml/getting-started")
```

Replace `<server-name>` with whatever the user's MCP server is registered as — commonly `deriva`, sometimes `dev-localhost`, sometimes something project-specific. If `ListMcpResourcesTool({server: "<name>"})` returns successfully, that's the right name.

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

- `deriva://deriva-ml/concepts` — same content as the `deriva_ml_concepts` MCP prompt; resource form for resource-walking clients
- `deriva://deriva-ml/getting-started` — same content as the `deriva_ml_getting_started` MCP prompt; resource form for resource-walking clients
- `/mcp__<server-name>__query_guide` — ERMrest query guide (path expressions, joins, aliases, pagination)
- `/mcp__<server-name>__entity_guide` — entity CRUD conventions, preflight count rule, display rules
- `/mcp__<server-name>__annotation_guide` — Chaise display annotation operations
- `/mcp__<server-name>__catalog_guide` — catalog-level operations (create, clone, schema introspection)
- `ListMcpResourcesTool({server: "<name>"})` — confirm the server name and see what resources are available
