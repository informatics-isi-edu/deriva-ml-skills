# DerivaML Startup Primer — Design

**Date:** 2026-06-02
**Status:** Approved (ready for implementation plan)
**Repos touched:** `deriva-ml-mcp-plugin` (server-side primer), `deriva-ml-skills` (skill rewrites)
**Explicitly NOT touched:** `deriva-mcp-core` (maintained separately; no edits permitted)

---

## Problem

The DerivaML startup "system" — the orientation an agent gets before its
first catalog interaction — is currently spread across two Claude Code
skills and a hand-rolled, eager-load procedure:

- `deriva-ml-context` (always-on) carries the conceptual frame (five
  abstractions, the inheritance-with-override rule, resource-first reads).
- `using-deriva-mcp` (cold-start) tells the agent to manually read two
  orientation resources (`deriva://deriva-ml/concepts`,
  `deriva://deriva-ml/getting-started`) **and** read each of the four
  generic `deriva-mcp-core` guide prompts (`query_guide`, `entity_guide`,
  `annotation_guide`, `catalog_guide`) **up front, before first use**.

That up-front, read-everything pattern is exactly the eager-load model
[ADR-0002 (deriva-mcp-core)](../../../deriva-mcp-core/docs/ADR-0002-system-prompt-extensions.md)
moves away from. ADR-0002 prescribes, for non-chatbot MCP clients like
Claude Code, a single bootstrap entry point (`system_primer`) that loads a
small mandatory core eagerly and advertises everything else as a one-line
**manifest** fetched **on demand** — its `ManifestStrategy`, matched to the
high-capability model tier (Opus/Sonnet) that Claude Code runs on.

The deriva-mcp-ui chatbot already does the eager variant: on the first turn
it assembles a system prompt from inline mandatory rules + the four guide
prompts (`_GUIDE_PROMPT_NAMES` in `chat.py`, fetched via `_fetch_guides`) +
a full schema dump (`_prime_schema`) + ERMrest syntax pulled from RAG
(`_prime_ermrest_syntax`). That is ADR-0002's `BudgetedStrategy`, chosen
because the chatbot targets Haiku/local models that cannot reliably chain
"fetch guide X before doing Y."

We want the Claude Code startup to be **consistent with the chatbot's
intent** (one bootstrap, same guide source-of-truth) while using the
**manifest/on-demand** stance appropriate to its model tier — and to
implement it **entirely inside `deriva-ml-mcp-plugin`**, since
`deriva-mcp-core` cannot be modified.

## Goals

1. A single bootstrap entry point (`deriva_ml_primer`) that returns the
   DerivaML mandatory core plus a manifest of available guides.
2. The startup system stays **two-tier** with a sharpened boundary:
   - **Always-on (`deriva-ml-context`):** the conceptual mandatory core —
     content whose absence causes *silent* failure (the inheritance rule,
     the five abstractions, resource-first reads).
   - **Cold-start (`using-deriva-mcp`):** the procedural bootstrap —
     collapses to "call the primer first; fetch a guide on demand."
3. No `deriva-mcp-core` changes. The primer composes only the plugin's own
   guide bodies and *names* core's four guides in the manifest.
4. The primer is exposed on all three MCP surfaces the plugin's existing
   guides use — tool, prompt, resource — so the deriva-mcp-ui chatbot can
   consume it the same way it consumes the existing guides.

## Non-goals

- Implementing ADR-0002's general `system_prompt_extension` API,
  `deriva://prompt-extensions` manifest resource, `BudgetedStrategy`, or
  the server `instructions` directive. Those live in `deriva-mcp-core`,
  which is out of bounds. We build a plugin-scoped, ML-specific primer that
  follows the ADR's *shape* without its core framework.
- Bundling a schema dump or RAG-primed ERMrest syntax into the primer.
  Those are UI-strategy concerns (the chatbot's `_prime_schema` /
  `_prime_ermrest_syntax` live in `chat.py`, not the server). In Claude
  Code the agent fetches schema via resources on demand; baking a 20k-char
  schema into every primer would recreate the bloat ADR-0002 fights.
- A fallback path for servers that lack the primer. Per decision, the
  rewritten `using-deriva-mcp` skill **requires** the primer.

## Consistency with deriva-mcp-ui (explicit mapping)

| deriva-mcp-ui (`chat.py`) | `deriva_ml_primer` | Consistent? |
|---|---|---|
| Hardcodes 4 guide names in `_GUIDE_PROMPT_NAMES`, fetches all up front (`_fetch_guides`) | Hardcodes the same 4 names in a manifest, fetched **on demand** | Same source-of-truth; opposite eager/lazy stance (by model tier) |
| Inlines mandatory rules in `system_prompt()` | Inlines `_CONCEPTS_GUIDE` + `_GETTING_STARTED_GUIDE` as mandatory core | Consistent in spirit |
| Primes full schema (`_prime_schema`) | Does not (resources on demand) | Divergent by design (UI-strategy concern) |
| Primes ERMrest syntax from RAG (`_prime_ermrest_syntax`) | Does not | Divergent by design (UI-strategy concern) |

The eager/lazy divergence is **not** an inconsistency: it is ADR-0002's two
strategies applied to two model tiers. Chatbot = `BudgetedStrategy`
(Haiku/local); Claude Code primer = `ManifestStrategy` (Opus/Sonnet). The
primer-as-resource (below) is what lets the chatbot also consume the primer
content, converging the two surfaces rather than letting them drift.

## Design

All code changes are under
`deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/`.

### A. `prompts.py` — manifest, render, primer, get_guide

**1. `_GUIDE_MANIFEST` (manifest-as-data).** A small structured list, the
structural seed of ADR-0002's `deriva://prompt-extensions`:

```python
# (name, source, summary). source in {"deriva-ml", "core"}.
# SYNC: the "core" rows mirror prompt names registered in
# deriva-mcp-core/src/deriva_mcp_core/tools/prompts.py. If a core guide is
# renamed there, update here. (We cannot enumerate core prompts at runtime
# without reaching into core internals; the names are stable public API.)
_GUIDE_MANIFEST = [
    ("query_guide",      "core", "ERMrest query/path syntax, pagination, results"),
    ("entity_guide",     "core", "entity CRUD, preflight count rule, display rules"),
    ("annotation_guide", "core", "Chaise annotation patterns, contexts, templates"),
    ("catalog_guide",    "core", "catalog create/clone/alias, snaptime, history"),
]
```

Future plugin-owned guides get `"deriva-ml"` rows; that is the only edit
needed to advertise them.

**2. `_render_primer() -> str`.** Pure string composition, no catalog
access. Three blocks (ADR-0002 §5 primer body shape):

- **Block 1 — mandatory core (full bodies):** `_CONCEPTS_GUIDE` then
  `_GETTING_STARTED_GUIDE` (the existing constants).
- **Block 2 — manifest (one line per guide):** rendered from
  `_GUIDE_MANIFEST`, grouped by source. `deriva-ml` rows: "fetch via
  `get_guide(name)` or `/<server>:<name>`." `core` rows: "fetch via
  `/<server>:<name>` when you first use that tool group."
- **Block 3 — closing directive:** fetch an unfamiliar tool's guide once
  then proceed; do not re-fetch loaded guides; prefer
  `deriva://...deriva-ml/...` resources for read-side questions.

**3. `deriva_ml_primer` — tool + prompt.** Both call `_render_primer()`.

- Tool: `@ctx.tool(mutates=False)`, signature
  `async def deriva_ml_primer(hostname: str = "", catalog_id: str = "") -> str`.
  `hostname`/`catalog_id` are optional and advisory (content is static; no
  `applies_to` filtering since the plugin is single-domain). Self-directing
  docstring: "Call this FIRST when working with DerivaML ... Call once per
  session; the content does not change."
- Prompt: `@ctx.prompt("deriva_ml_primer", description=...)`, zero-arg,
  surfaces as `/<server>:deriva_ml_primer`.

**4. `get_guide(name)` — tool.** `@ctx.tool(mutates=False)`. Behavior:

- `name` is a plugin-owned guide (`deriva_ml_concepts`,
  `deriva_ml_getting_started`) -> return its body directly. (The primer's
  own name is not a valid `get_guide` target — it is the bootstrap, not a
  guide; requesting it returns the unknown-name error.)
- `name` is a `core` manifest entry -> return a redirect string: "Fetch
  this guide via the `/<server>:<name>` slash-command prompt; it is
  registered in deriva-mcp-core and not retrievable through this plugin."
- otherwise -> structured `{"error": "..."}` listing valid guide names
  (consistent with the plugin's error-envelope convention).

### B. `resources/ml.py` — primer resource

**5. `deriva://deriva-ml/primer` resource.** `@ctx.resource(...)` returning
`_render_primer()`. Mirrors the existing `deriva://deriva-ml/concepts` and
`deriva://deriva-ml/getting-started` resource registrations. This is the
surface the deriva-mcp-ui chatbot consumes.

### C. `deriva-ml-skills/skills/` — skill rewrites

**6. `using-deriva-mcp/SKILL.md` rewrite.** Replace the manual
"read 2 resources + read 4 guides up front" procedure with: call
`deriva_ml_primer` first (one call); when the manifest points you at a
guide for a tool group you are about to use, fetch it then (via `get_guide`
for plugin guides, or the `/<server>:<name>` slash command for core
guides), once. Keep the resource-templates-first stance and the MCP /
local-Python boundary section. The skill **requires** the primer (no
fallback). Update the description frontmatter to trigger on the same
cold-start situations but route to the primer.

**7. `deriva-ml-context/SKILL.md` light touch.** Update the
"Cold-start orientation" subsection (~lines 71-75) to point at the primer
rather than describe the old read-the-guides procedure. The conceptual core
(abstractions, inheritance rule, resource table, find/list naming) is
unchanged — it remains the always-on mandatory core.

## Error handling

- `_render_primer()` is pure string composition; cannot fail at runtime
  (same robustness as the existing concepts/getting-started prompts).
- `get_guide` unknown name -> structured error listing valid names.
- Primer `hostname`/`catalog_id` are advisory and unused in rendering;
  empty or wrong values are harmless.

## Testing

In `deriva-ml-mcp-plugin/tests/`:

- `deriva_ml_primer` (tool, prompt, resource) all return identical text.
- Primer text contains both guide bodies and all four core guide names.
- `get_guide` returns a body for a plugin guide, a redirect for a core
  name, and an error for an unknown name.
- Manifest-drift guard: assert the four `core` names in `_GUIDE_MANIFEST`
  match the prompt names `deriva-mcp-core` registers. If importing core's
  prompt registry in tests is feasible, assert programmatically; otherwise
  document a manual sync point and assert the static list shape.

## Accepted limitations

- **No server `instructions` nudge.** ADR-0002 §5 wanted core's FastMCP
  `instructions` field to signal "call system_primer first." We cannot set
  it (core is out of bounds). Auto-invoke pressure comes from the tool's
  self-directing docstring + the `using-deriva-mcp` skill. Sufficient for
  Claude Code (the skill is the trigger); degrades gracefully for other
  clients (the tool docstring carries the hint).
- **Manifest hardcodes core guide names.** No runtime enumeration of core
  prompts is possible without reaching into core internals. Mitigated by
  the sync comment and the drift-guard test. Names are stable public API.
- **`get_guide` redirects for core guides.** It can only return
  plugin-owned bodies; for core names it points at the slash command. This
  is the only plugin-side behavior possible and is honest about the
  boundary.

## Cross-repo sync note

The primer inlines `_CONCEPTS_GUIDE` + `_GETTING_STARTED_GUIDE`, which are
already under the existing skill <-> prompt sync discipline (see
`deriva-ml-skills/CLAUDE.md`, "Cross-Repo Sync"). The primer adds no new
conceptual content, so it introduces no new sync obligation beyond the
`_GUIDE_MANIFEST` core-name sync described above.
