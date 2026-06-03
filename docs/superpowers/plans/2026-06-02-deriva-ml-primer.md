# DerivaML Startup Primer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single `deriva_ml_primer` bootstrap (tool + prompt + resource) plus a `get_guide` tool to `deriva-ml-mcp-plugin`, and rewrite the two startup skills in `deriva-ml-skills` to route through it — an ADR-0002 manifest-strategy startup, entirely plugin-side (no `deriva-mcp-core` changes).

**Architecture:** The primer composes the plugin's existing `_CONCEPTS_GUIDE` + `_GETTING_STARTED_GUIDE` bodies (mandatory core) plus a one-line manifest rendered from a structured `_GUIDE_MANIFEST` list that names `deriva-mcp-core`'s four tier-1 guides. The primer is exposed on the same three MCP surfaces the existing guides use (tool, prompt, resource). `get_guide(name)` returns plugin-owned guide bodies directly and redirects core guide names to their slash-command. The always-on `deriva-ml-context` skill keeps the conceptual mandatory core; the cold-start `using-deriva-mcp` skill collapses to "call the primer first."

**Tech Stack:** Python 3.11+, FastMCP via `deriva-mcp-core`'s `PluginContext`, pytest, `uv` for all commands, Markdown skills.

**Repos / working directories:**
- `deriva-ml-mcp-plugin` at `/Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin` (Tasks 1-5)
- `deriva-ml-skills` at `/Users/carl/GitHub/DerivaML/deriva-ml-skills` (Tasks 6-7)

**Conventions (both repos):** Run everything via `uv run`. ASCII-only in
Python code, docstrings, and built-in prompt strings (no en-dashes, smart
quotes, bullet chars). Google-style docstrings with `Args:`/`Returns:`/
`Example:`. No backwards-compat shims. Always `cd` into the target repo in
the same Bash call (cwd is not persistent).

**Spec:** `deriva-ml-skills/docs/superpowers/specs/2026-06-02-deriva-ml-primer-design.md`

---

## Phase 1 — Plugin (`deriva-ml-mcp-plugin`), Tasks 1-5

> All Phase 1 tasks edit
> `/Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/`
> and `tests/`. Start by creating a branch:
>
> ```bash
> cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && git checkout -b primer-startup
> ```

---

### Task 1: `_GUIDE_MANIFEST` structured list

**Files:**
- Modify: `src/deriva_ml_mcp_plugin/prompts.py` (add near the other module-level constants, before the `register` function)
- Test: `tests/test_prompts.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_prompts.py`:

```python
def test_guide_manifest_shape():
    """_GUIDE_MANIFEST is a list of (name, source, summary) triples."""
    manifest = prompts._GUIDE_MANIFEST
    assert isinstance(manifest, list)
    assert len(manifest) >= 4
    for entry in manifest:
        name, source, summary = entry  # exactly three fields
        assert isinstance(name, str) and name
        assert source in {"deriva-ml", "core"}
        assert isinstance(summary, str) and summary


def test_guide_manifest_names_core_tier1_guides():
    """The four deriva-mcp-core tier-1 guides are named with source 'core'."""
    core_names = {n for (n, src, _) in prompts._GUIDE_MANIFEST if src == "core"}
    assert core_names == {
        "query_guide",
        "entity_guide",
        "annotation_guide",
        "catalog_guide",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_prompts.py::test_guide_manifest_shape tests/test_prompts.py::test_guide_manifest_names_core_tier1_guides -v`
Expected: FAIL with `AttributeError: module 'deriva_ml_mcp_plugin.prompts' has no attribute '_GUIDE_MANIFEST'`

- [ ] **Step 3: Add the constant**

In `src/deriva_ml_mcp_plugin/prompts.py`, after the `_GETTING_STARTED_GUIDE` constant and before `def register(`, add:

```python
# Manifest of guides advertised by the primer (manifest-as-data). Each entry
# is (name, source, summary). source is "deriva-ml" for guides owned by this
# plugin (fetchable via get_guide) or "core" for deriva-mcp-core tier-1 guides
# (fetchable only via the /<server>:<name> slash-command prompt).
#
# SYNC: the "core" rows mirror prompt names registered in
# deriva-mcp-core/src/deriva_mcp_core/tools/prompts.py. If a core guide is
# renamed there, update the matching row here. We cannot enumerate core
# prompts at runtime without reaching into core internals; the names are
# stable public API. The drift-guard test lives in test_prompts.py.
_GUIDE_MANIFEST: list[tuple[str, str, str]] = [
    ("query_guide", "core", "ERMrest query and path syntax, pagination, result interpretation"),
    ("entity_guide", "core", "entity CRUD, preflight count rule, display rules"),
    ("annotation_guide", "core", "Chaise annotation patterns, context names, templates"),
    ("catalog_guide", "core", "catalog create/clone/alias, snaptime format, history"),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_prompts.py::test_guide_manifest_shape tests/test_prompts.py::test_guide_manifest_names_core_tier1_guides -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && git add src/deriva_ml_mcp_plugin/prompts.py tests/test_prompts.py && git commit -m "feat(prompts): add _GUIDE_MANIFEST structured guide list"
```

---

### Task 2: `_render_primer()` composition function

**Files:**
- Modify: `src/deriva_ml_mcp_plugin/prompts.py` (add after `_GUIDE_MANIFEST`, before `register`)
- Test: `tests/test_prompts.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_prompts.py`:

```python
def test_render_primer_contains_both_guide_bodies():
    """The primer inlines the concepts and getting-started guide bodies."""
    body = prompts._render_primer()
    # A distinctive phrase from each guide must be present verbatim.
    assert "DERIVA-ML GETTING STARTED" in body
    assert "five core abstractions" in body or "Dataset" in body


def test_render_primer_lists_all_guide_names():
    """Every guide name from the manifest appears in the primer text."""
    body = prompts._render_primer()
    for name, _, _ in prompts._GUIDE_MANIFEST:
        assert name in body, f"{name} missing from primer"


def test_render_primer_is_ascii():
    """The primer body must be plain ASCII (workspace convention)."""
    prompts._render_primer().encode("ascii")  # raises UnicodeEncodeError on failure


def test_render_primer_has_three_blocks():
    """The primer has a mandatory-core header, a manifest header, and a closing directive."""
    body = prompts._render_primer()
    assert "DERIVA-ML AGENT GUIDELINES" in body  # block 1 header
    assert "ON-DEMAND GUIDES" in body            # block 2 header
    assert "get_guide" in body                   # block 3 references on-demand fetch
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_prompts.py -k render_primer -v`
Expected: FAIL with `AttributeError: ... has no attribute '_render_primer'`

- [ ] **Step 3: Add the render function**

In `src/deriva_ml_mcp_plugin/prompts.py`, after `_GUIDE_MANIFEST` and before `def register(`, add:

```python
def _render_primer() -> str:
    """Render the DerivaML startup primer body.

    Composes three blocks: (1) the mandatory-core guide bodies
    (concepts + getting-started), (2) a one-line manifest of on-demand
    guides grouped by source, and (3) a closing directive on when to
    fetch a guide and to prefer resources for read-side questions.

    The body is phrased neutrally ("DERIVA-ML AGENT GUIDELINES") rather
    than "you MUST", so it reads correctly whether it lands in a system
    prompt or arrives as tool/prompt output in an agent conversation.

    Returns:
        The full primer text as a single plain-ASCII string.

    Example:
        >>> text = _render_primer()
        >>> "DERIVA-ML AGENT GUIDELINES" in text
        True
    """
    ml_guides = [(n, s) for (n, src, s) in _GUIDE_MANIFEST if src == "deriva-ml"]
    core_guides = [(n, s) for (n, src, s) in _GUIDE_MANIFEST if src == "core"]

    parts: list[str] = []

    # Block 1 -- mandatory core (full bodies).
    parts.append("=== DERIVA-ML AGENT GUIDELINES ===\n")
    parts.append(_CONCEPTS_GUIDE)
    parts.append(_GETTING_STARTED_GUIDE)

    # Block 2 -- manifest of on-demand guides.
    parts.append("=== ON-DEMAND GUIDES ===")
    if ml_guides:  # empty today; activates when _GUIDE_MANIFEST gains "deriva-ml" rows
        parts.append(
            "DerivaML domain guides (this plugin) -- fetch with "
            "get_guide(name) when you first need them:"
        )
        for name, summary in ml_guides:
            parts.append(f"  - {name}: {summary}")
    parts.append(
        "Generic catalog guides (deriva-mcp-core) -- fetch the matching "
        "/<server>:<name> prompt when you first use that tool group:"
    )
    for name, summary in core_guides:
        parts.append(f"  - {name}: {summary}")

    # Block 3 -- closing directive. NOTE: the get_guide reference lives here
    # (not only in the ml_guides block) so the on-demand fetch mechanism is
    # always named, even while the ml_guides list is empty.
    parts.append(
        "When you reach an unfamiliar tool covered by a guide above, fetch "
        "that guide once (get_guide(name) for the domain guides above, or "
        "the matching /<server>:<name> prompt for the core guides) and "
        "proceed; do not re-fetch a guide already loaded this conversation. "
        "For read-side questions about existing entities (show X, what is in "
        "Y, what did Z produce), prefer the "
        "deriva://catalog/<host>/<cat>/deriva-ml/... resources over the "
        "equivalent list/get tools -- they are cached, page-free, and emit "
        "no audit entries."
    )

    return "\n\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_prompts.py -k render_primer -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && git add src/deriva_ml_mcp_plugin/prompts.py tests/test_prompts.py && git commit -m "feat(prompts): add _render_primer three-block composition"
```

---

### Task 3: `deriva_ml_primer` tool + prompt registration

**Files:**
- Modify: `src/deriva_ml_mcp_plugin/prompts.py` (inside `register`)
- Test: `tests/test_prompts.py`

Note: `_CapturingMCP` keys tools by `fn.__name__` and prompts by the
explicit `name` argument. The tool function is named `deriva_ml_primer`;
the prompt function is named `deriva_ml_primer_prompt` (to avoid a Python
name collision in the module) but registered under the prompt name
`"deriva_ml_primer"`. Both delegate to `_render_primer()`.

- [ ] **Step 1: Update the existing prompt-count test, then add new assertions**

In `tests/test_prompts.py`, change `_EXPECTED_PROMPT_NAMES` and the count test:

```python
_EXPECTED_PROMPT_NAMES = frozenset(
    {
        "deriva_ml_concepts",
        "deriva_ml_getting_started",
        "deriva_ml_primer",
    }
)
```

Change `test_two_prompts_registered` to:

```python
def test_three_prompts_registered(ctx, capturing_mcp):
    """Exactly three prompts land in the capturing MCP after register."""
    prompts.register(ctx)
    assert len(capturing_mcp.prompts) == 3
```

(Delete the old `test_two_prompts_registered`.)

Add new tests:

```python
def test_primer_prompt_returns_primer_body(ctx, capturing_mcp):
    """The deriva_ml_primer prompt returns the rendered primer."""
    prompts.register(ctx)
    fn = capturing_mcp.prompts["deriva_ml_primer"]
    assert fn() == prompts._render_primer()


def test_primer_tool_registered_read_only(ctx, capturing_mcp):
    """deriva_ml_primer is registered as a read-only tool."""
    prompts.register(ctx)
    assert "deriva_ml_primer" in capturing_mcp.tools
    assert capturing_mcp.tool_kwargs["deriva_ml_primer"]["mutates"] is False


def test_primer_tool_returns_primer_body(ctx, capturing_mcp):
    """The deriva_ml_primer tool returns the rendered primer regardless of args."""
    prompts.register(ctx)
    fn = capturing_mcp.tools["deriva_ml_primer"]
    assert fn() == prompts._render_primer()
    assert fn(hostname="h", catalog_id="1") == prompts._render_primer()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_prompts.py -k "primer or three_prompts" -v`
Expected: FAIL — `KeyError: 'deriva_ml_primer'` and the count test expecting 3 but finding 2.

- [ ] **Step 3: Register the tool and prompt**

In `src/deriva_ml_mcp_plugin/prompts.py`, inside `def register(ctx)`, after the existing `deriva_ml_getting_started` prompt registration, add:

```python
    @ctx.tool(mutates=False)
    def deriva_ml_primer(hostname: str = "", catalog_id: str = "") -> str:
        """Load DerivaML agent guidelines and the manifest of available guides.

        Call this FIRST when working with DerivaML in a catalog, before any
        ``deriva_ml_*`` tool or ``deriva://...deriva-ml/...`` resource. Returns
        the conceptual frame, the operating contract (hostname/catalog rule,
        pagination, error envelope), and a one-line manifest of on-demand
        guides. Call once per session; the content does not change.

        Args:
            hostname: Optional Deriva server hostname. Advisory only -- the
                primer content is static and does not vary by catalog.
            catalog_id: Optional catalog id. Advisory only, as above.

        Returns:
            The primer text (plain ASCII).

        Example:
            >>> deriva_ml_primer()  # doctest: +SKIP
            '=== DERIVA-ML AGENT GUIDELINES ===\\n...'
        """
        return _render_primer()

    @ctx.prompt(
        "deriva_ml_primer",
        description=(
            "DerivaML startup primer: agent guidelines (concepts + operating "
            "contract) plus a manifest of on-demand guides. Invoke first when "
            "working with DerivaML; the equivalent deriva_ml_primer tool is "
            "auto-callable by agents that do not surface prompts as commands."
        ),
    )
    def deriva_ml_primer_prompt() -> str:
        return _render_primer()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_prompts.py -v`
Expected: PASS (all tests in the file, including the updated ASCII and non-empty checks which now also cover the primer prompt)

- [ ] **Step 5: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && git add src/deriva_ml_mcp_plugin/prompts.py tests/test_prompts.py && git commit -m "feat(prompts): register deriva_ml_primer tool + prompt"
```

---

### Task 4: `get_guide(name)` tool

**Files:**
- Modify: `src/deriva_ml_mcp_plugin/prompts.py` (add a `_PLUGIN_GUIDE_BODIES` map and register the tool inside `register`)
- Test: `tests/test_prompts.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_prompts.py`:

```python
def test_get_guide_returns_plugin_guide_body(ctx, capturing_mcp):
    """get_guide returns the full body for a plugin-owned guide."""
    prompts.register(ctx)
    get_guide = capturing_mcp.tools["get_guide"]
    assert get_guide(name="deriva_ml_concepts") == prompts._CONCEPTS_GUIDE
    assert get_guide(name="deriva_ml_getting_started") == prompts._GETTING_STARTED_GUIDE


def test_get_guide_redirects_core_guide(ctx, capturing_mcp):
    """get_guide returns a slash-command redirect for a core guide name."""
    prompts.register(ctx)
    get_guide = capturing_mcp.tools["get_guide"]
    result = get_guide(name="query_guide")
    assert "query_guide" in result
    assert "/<server>:" in result or "slash-command" in result


def test_get_guide_unknown_name_errors(ctx, capturing_mcp):
    """get_guide returns a structured error for an unknown name."""
    import json as _json

    prompts.register(ctx)
    get_guide = capturing_mcp.tools["get_guide"]
    result = get_guide(name="does_not_exist")
    payload = _json.loads(result)
    assert "error" in payload
    # The error lists the valid names so the agent can recover.
    assert "deriva_ml_concepts" in payload["error"]


def test_get_guide_registered_read_only(ctx, capturing_mcp):
    """get_guide is a read-only tool."""
    prompts.register(ctx)
    assert capturing_mcp.tool_kwargs["get_guide"]["mutates"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_prompts.py -k get_guide -v`
Expected: FAIL — `KeyError: 'get_guide'`

- [ ] **Step 3: Add the guide-body map and register the tool**

In `src/deriva_ml_mcp_plugin/prompts.py`, add a module-level map after
`_GUIDE_MANIFEST`:

```python
# Bodies of guides this plugin owns and can return directly via get_guide.
# Core guides are intentionally absent -- their bodies live in
# deriva-mcp-core and are reachable only via their slash-command prompts.
_PLUGIN_GUIDE_BODIES: dict[str, str] = {
    "deriva_ml_concepts": _CONCEPTS_GUIDE,
    "deriva_ml_getting_started": _GETTING_STARTED_GUIDE,
}
```

Then, inside `def register(ctx)` after the primer registration, add:

```python
    @ctx.tool(mutates=False)
    def get_guide(name: str) -> str:
        """Fetch a DerivaML or generic-catalog guide by name.

        For a guide this plugin owns, returns its full body. For a
        deriva-mcp-core tier-1 guide, returns a short redirect pointing at
        the ``/<server>:<name>`` slash-command prompt (core guide bodies are
        not retrievable through this plugin). For an unknown name, returns a
        structured error listing valid names.

        Args:
            name: The guide name, as advertised in the primer manifest.

        Returns:
            The guide body, a redirect string, or a JSON ``{"error": ...}``
            payload for an unknown name.

        Example:
            >>> get_guide("deriva_ml_concepts")  # doctest: +SKIP
            '...the five core abstractions...'
        """
        import json

        if name in _PLUGIN_GUIDE_BODIES:
            return _PLUGIN_GUIDE_BODIES[name]

        core_names = {n for (n, src, _) in _GUIDE_MANIFEST if src == "core"}
        if name in core_names:
            return (
                f"Guide '{name}' is registered in deriva-mcp-core and is not "
                f"retrievable through this plugin. Fetch it via the "
                f"/<server>:{name} slash-command prompt."
            )

        valid = sorted(_PLUGIN_GUIDE_BODIES) + sorted(core_names)
        return json.dumps(
            {"error": f"Unknown guide '{name}'. Valid guides: {', '.join(valid)}."}
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_prompts.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && git add src/deriva_ml_mcp_plugin/prompts.py tests/test_prompts.py && git commit -m "feat(prompts): add get_guide tool (plugin bodies + core redirect)"
```

---

### Task 5: `deriva://deriva-ml/primer` resource

**Files:**
- Modify: `src/deriva_ml_mcp_plugin/resources/ml.py` (add inside `register`, next to the concepts/getting-started resources; extend the late import)
- Test: `tests/test_resources.py`

- [ ] **Step 1: Write the failing test**

The suite uses `asyncio_mode = "auto"` (see `pyproject.toml`), so tests are
plain `async def` with no `@pytest.mark.asyncio` decorator, and resources
are reached via the `capturing_mcp` fixture's `.resources[URI]` dict (the
same pattern as the existing `test_static_resources_return_prompt_constants`
and `test_ml_datasets_success`). Add to `tests/test_resources.py`:

```python
_PRIMER_URI = "deriva://deriva-ml/primer"


async def test_primer_resource_registered(resource_ctx, capturing_mcp):
    """The primer resource is registered under its static URI."""
    assert _PRIMER_URI in capturing_mcp.resources


async def test_primer_resource_matches_render(resource_ctx, capturing_mcp):
    """The primer resource returns the same text as prompts._render_primer()."""
    from deriva_ml_mcp_plugin import prompts

    result = await capturing_mcp.resources[_PRIMER_URI]()
    assert result == prompts._render_primer()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_resources.py -k primer -v`
Expected: FAIL — `KeyError` / assertion that `_PRIMER_URI` is not registered.

- [ ] **Step 3: Register the resource**

In `src/deriva_ml_mcp_plugin/resources/ml.py`, extend the late import at the
top of `register` to also import the render function:

```python
    from deriva_ml_mcp_plugin.prompts import (
        _CONCEPTS_GUIDE,
        _GETTING_STARTED_GUIDE,
        _render_primer,
    )
```

Then, immediately after the `deriva_ml_concepts_resource` registration, add:

```python
    @ctx.resource("deriva://deriva-ml/primer")
    async def deriva_ml_primer_resource() -> str:
        """DerivaML startup primer: agent guidelines plus the on-demand guide manifest.

        Same content as the ``deriva_ml_primer`` MCP prompt and tool --
        exposed here as a resource so clients that consume the primer as
        resource content (e.g. the deriva-mcp-ui chatbot's first-turn
        assembly) get the identical text. Composes the concepts and
        getting-started guide bodies plus a one-line manifest of the
        generic-catalog tier-1 guides.
        """
        return _render_primer()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_resources.py -k primer -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full plugin unit suite + lint**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest -m "not integration" -q && uv run ruff check src tests && uv run ruff format --check src tests
```
Expected: all pass; ruff reports no issues. If `ruff format --check` reports
files needing formatting, run `uv run ruff format src tests` and re-run.

- [ ] **Step 6: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && git add src/deriva_ml_mcp_plugin/resources/ml.py tests/test_resources.py && git commit -m "feat(resources): expose deriva://deriva-ml/primer resource"
```

---

## Phase 2 — Skills (`deriva-ml-skills`), Tasks 6-7

> Phase 2 edits Markdown skills in
> `/Users/carl/GitHub/DerivaML/deriva-ml-skills/skills/`. These depend on
> the primer existing (Phase 1). Work continues on the existing
> `primer-startup-skill` branch already checked out in this repo (the spec
> was committed there). No tests run; verification is by re-reading the
> edited files and a cross-reference grep.

---

### Task 6: Rewrite `using-deriva-mcp/SKILL.md` to route through the primer

**Files:**
- Modify: `skills/using-deriva-mcp/SKILL.md`

- [ ] **Step 1: Replace the frontmatter description**

Replace the `description:` value (lines 3, the long string) with one that
triggers on the same cold-start situations but routes to the primer. New
frontmatter block (keep `name` and `disable-model-invocation: false`):

```yaml
---
name: using-deriva-mcp
description: "ALWAYS load before the first deriva MCP call in any conversation. Call the deriva_ml_primer tool first -- it returns the DerivaML agent guidelines (concepts + operating contract: (hostname, catalog_id) rule, pagination, error envelope) plus a one-line manifest of on-demand guides. Then fetch an individual guide only when you first reach the tool group it covers: get_guide(name) for deriva-ml guides, or the /<server>:<name> slash-command prompt for the generic-catalog tier-1 guides (query_guide / entity_guide / annotation_guide / catalog_guide). Triggers on: first-time use of mcp__deriva__ tools/resources, any catalog inspection request ('list / show / browse / verify / inspect catalog', 'check schema', 'check feature values'), AND read-shaped questions that don't look like 'browse' on their face ('what X are in catalog N', 'what X are available', 'how many X', 'which workflows / features / vocabularies / datasets / executions / assets exist'). Do NOT trigger for shell-only workflows (load-cifar10 CLI, deriva-ml Python API only, deriva-ml-run) that bypass MCP entirely."
disable-model-invocation: false
---
```

- [ ] **Step 2: Replace the body's cold-start procedure**

Replace the body from the `# Reading the deriva MCP Server's Orientation
Material First` heading through the end of the `## The two-minute
cold-start` section (the part that tells the agent to read two resources
and then read each tier-1 guide up front) with the primer-first procedure
below. Keep the later sections (`## When this skill applies, and when it
doesn't`, `## The MCP / local-Python boundary`, `## What you should NOT
do`, `## When the upstream material disagrees with a skill`, `##
Relationship to other skills`, `## Reference`) but make the two edits noted
in Step 3.

New opening through cold-start:

```markdown
# Bootstrapping the deriva MCP Server: call the primer first

You are about to make a call against a Deriva catalog via the deriva MCP
server (`mcp__deriva__*` tools or `deriva://...` resources, or under
whatever name the connecting MCP server is registered). **Before the first
such call in a conversation, call the `deriva_ml_primer` tool.** One call
returns the DerivaML agent guidelines and a manifest of the guides
available for deeper tool groups. This skill is the trigger; the primer is
the bootstrap.

> **Stop before calling a list-style tool: check the resource templates table first.**
> Almost every read-shaped question against a catalog ("what datasets are in 46?", "what workflow types are available?", "what features exist on Image?") has a matching `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/...` resource URI. The resource is **cached, page-free, returns a leaner payload, and produces no audit-log entries** -- strictly preferable for read-only questions. The resource templates table in the Reference section at the end of this skill enumerates the templates the deriva-ml MCP plugin registers. If you find yourself reaching for `deriva_ml_list_datasets`, `deriva_ml_list_executions`, `deriva_ml_list_features`, `list_vocabulary_terms`, etc., pause and confirm there isn't a resource that would answer the same question.

## The one-call cold-start

**Step 1 -- call the primer.** It is exposed three ways; use whichever your
client surfaces:

- As a **tool**: `deriva_ml_primer()` (agents that auto-call tools should
  call it on the first turn -- the docstring is self-directing).
- As a **prompt / slash command**: `/<server>:deriva_ml_primer` for manual
  invocation.
- As a **resource**: `ReadMcpResourceTool(server="<name>", uri="deriva://deriva-ml/primer")`.

All three return identical text: the concepts frame, the getting-started
operating contract (the `(hostname, catalog_id)` rule, the pagination
preflight->page->advance contract, the error envelope), and a one-line
manifest of on-demand guides.

Replace `<server>` / `<name>` with whatever the user's MCP server is
registered as -- commonly `deriva`, sometimes `dev-localhost`, sometimes
project-specific. If `ListMcpResourcesTool({server: "<name>"})` returns
successfully, that's the right name.

**Step 2 -- fetch a guide on demand, only when you reach its tool group.**
The primer's manifest names the available guides but does not inline their
bodies. Fetch a guide the first time you are about to use the tools it
covers, and not before:

| If your first call uses... | Fetch this guide |
|----|----|
| `query_attribute`, `query_aggregate`, `count_table` | `/<server>:query_guide` |
| `get_entities`, `insert_entities`, `update_entities`, `delete_entities` | `/<server>:entity_guide` |
| `get_table_annotations`, `set_*_display`, `set_visible_columns`, etc. | `/<server>:annotation_guide` |
| `create_catalog`, `clone_catalog`, `get_schema`, `get_catalog_info` | `/<server>:catalog_guide` |

For guides this plugin owns (none beyond the primer today, but future
deriva-ml guides will appear in the manifest with the `deriva-ml` source),
use `get_guide(name)` instead of the slash command. **Fetch each guide once
per conversation** -- they are stable references, not per-call context.
```

- [ ] **Step 3: Update two cross-references in the retained sections**

In the retained `## What you should NOT do` section, replace the bullet
that starts "**Skip the orientation and hit a tool directly.**" with:

```markdown
- **Skip the primer and hit a tool directly.** This is the failure mode this skill exists to prevent. Without the primer's getting-started contract, you will mis-paginate. Without `query_guide`, you will pass `schema` + `table` + `filter` to `query_attribute` instead of a `path` expression. Without the concepts frame, you will treat Datasets / Workflows / Executions as raw tables and mutate them with `insert_entities` (bypassing the lifecycle machinery -- see the inheritance-with-override rule in `/deriva-ml:deriva-ml-context`).
```

In the retained `## Reference` section, replace the
`### Orientation resources` list's first two bullets (concepts /
getting-started) with a single primer bullet plus the unchanged
server/status bullet:

```markdown
### Orientation surface (the primer)

- `deriva_ml_primer` -- tool, prompt (`/<server>:deriva_ml_primer`), and resource (`deriva://deriva-ml/primer`); all three return the same primer text (agent guidelines + on-demand guide manifest). This supersedes reading `deriva://deriva-ml/concepts` and `deriva://deriva-ml/getting-started` separately -- the primer inlines both.
- `deriva://deriva-ml/concepts`, `deriva://deriva-ml/getting-started` -- still available individually if you want one without the other, but the primer is the preferred single entry point.
- `deriva://server/status` -- server health / version info
```

- [ ] **Step 4: Verify the edit reads correctly and has no dangling references**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -n "two-minute cold-start\|Read the DerivaML domain orientation" skills/using-deriva-mcp/SKILL.md
```
Expected: no matches (the old eager-read procedure is gone).

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -n "deriva_ml_primer\|get_guide\|one-call cold-start" skills/using-deriva-mcp/SKILL.md
```
Expected: matches present (the new primer-first procedure is in place).

- [ ] **Step 5: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/using-deriva-mcp/SKILL.md && git commit -m "skill(using-deriva-mcp): route cold-start through deriva_ml_primer"
```

---

### Task 7: Update `deriva-ml-context` cold-start subsection

**Files:**
- Modify: `skills/deriva-ml-context/SKILL.md` (the `### Cold-start orientation` subsection, ~lines 71-75)

- [ ] **Step 1: Replace the cold-start subsection**

Replace the subsection that currently reads "### Cold-start orientation:
load `using-deriva-mcp` before the first MCP call" and its two paragraphs
with:

```markdown
### Cold-start orientation: call the primer before the first MCP call

The deriva MCP server ships its orientation material as a single primer:
`deriva_ml_primer` (a tool, a `/<server>:deriva_ml_primer` prompt, and a
`deriva://deriva-ml/primer` resource -- all returning the same text). It
inlines the concepts frame and the getting-started operating contract (the
pagination contract, error-envelope conventions, the `(hostname,
catalog_id)` rule) and advertises a manifest of on-demand guides for the
generic-catalog tool groups. Claude Code does not auto-inject this -- the
agent calls the primer (or the `using-deriva-mcp` skill prompts it to).

This skill (`deriva-ml-context`) teaches the resource-vs-tool *rule*; the
`/deriva-ml:using-deriva-mcp` skill makes sure you have called the primer
the rule is grounded in. Both should be active before the first MCP call.
Skip `using-deriva-mcp` only when the entire interaction stays on the
shell/Python side (`load-cifar10`, `deriva-ml-run`, direct `deriva-ml`
library calls in a script) and never crosses the MCP boundary.
```

- [ ] **Step 2: Verify the edit**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -n "deriva_ml_primer\|four guide prompts" skills/deriva-ml-context/SKILL.md
```
Expected: `deriva_ml_primer` present; the old "four guide prompts
(`query_guide`, `entity_guide`, ...)" phrasing in the cold-start subsection
is gone (the manifest now lives in the primer, not described here).

- [ ] **Step 3: Cross-reference sweep for stale primer-related wording**

Run:
```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && grep -rn "read the server's own orientation\|read.*concepts.*getting-started\|two-minute cold-start" skills/ | grep -v using-deriva-mcp
```
Expected: no matches (no other skill still describes the old eager-read
procedure). If any appear, update them to reference the primer in the same
spirit, then re-run.

- [ ] **Step 4: Commit**

```bash
cd /Users/carl/GitHub/DerivaML/deriva-ml-skills && git add skills/deriva-ml-context/SKILL.md && git commit -m "skill(deriva-ml-context): point cold-start subsection at the primer"
```

---

## Final verification

- [ ] **Plugin suite green:**
  `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest -m "not integration" -q && uv run ruff check src tests`
  Expected: all pass, no lint errors.

- [ ] **Plugin smoke test of the three surfaces (one body):** confirm the
  primer tool, prompt, and resource all return identical text. This is
  already covered by `test_primer_prompt_returns_primer_body`,
  `test_primer_tool_returns_primer_body`, and
  `test_primer_resource_matches_render` -- re-run them together:
  `cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp-plugin && uv run pytest tests/test_prompts.py tests/test_resources.py -k primer -v`
  Expected: all pass.

- [ ] **Skills read clean:** open both edited SKILL.md files and confirm
  the primer-first flow reads coherently and no section still instructs the
  agent to eagerly read all four guides up front.

- [ ] **Cross-repo note:** the spec and plan live in `deriva-ml-skills`, but
  the bulk of the change is in `deriva-ml-mcp-plugin`. When opening PRs,
  open two: one per repo, cross-linking each other. The plugin PR must merge
  (or at least be reviewable) first, since the skills assume the primer
  exists.

- [ ] **Out of scope, do NOT do here:** no `deriva-mcp-core` edits; no
  server `instructions` field change; no `bump-version` (release is a
  separate, later step once both PRs land).
```
