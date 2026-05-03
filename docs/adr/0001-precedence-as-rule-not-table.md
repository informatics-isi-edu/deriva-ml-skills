# 0001 — Precedence as inheritance-with-override rule, not a routing table

Date: 2026-05-03
Status: Accepted

## Context

The 2026-05-02 tier-2 audit cleanup plan, Round 3, called for an
explicit "precedence map" in `skills/deriva-ml-context/SKILL.md` —
a table enumerating, for each of the five DerivaML abstractions
(Dataset, Workflow, Execution, Feature, Asset), the canonical tier-2
tool, the tier-1 tool to avoid, and the reason. Framed as the
highest-value LLM-routing change of the whole audit.

During the Round 3 refinement interview the framing was challenged
twice. First: can the same routing pressure be achieved with a
sharper general rule rather than a row-per-case table? Second: is
the precedence really about the five abstractions specifically, or
about *anywhere a deriva-ml surface exists*?

## Decision

Use a **inheritance-with-override rule** that applies symmetrically
across all three planes (skills, MCP, Python API), not a table:

> The deriva-ml plugin extends the deriva plugin. Everything that
> applies in a Deriva catalog applies in a deriva-ml catalog by
> default. **Override:** if a deriva-ml surface exists for an
> operation, prefer it over the equivalent deriva surface. This
> applies on all three planes:
>
> - **Skills:** prefer `/deriva-ml:<skill>` over `/deriva:<skill>`
>   when both exist.
> - **MCP:** prefer `deriva_ml_*` MCP tools, prompts, and resources
>   over the equivalent `deriva-mcp-core` tool / prompt / resource.
> - **Python API:** prefer `deriva-ml` objects and methods
>   (`DerivaML`, `Dataset`, `Workflow`, `Execution`, `Feature`, the
>   `with ml.create_execution(config) as exe:` context manager,
>   `exe.asset_file_path()`, etc.) over the equivalent `deriva-py`
>   calls (`ErmrestCatalog`, `PathBuilder`, raw entity resource
>   access).

The override boundary is "is there a deriva-ml `<thing>` for this?"
— mechanical, surface-driven, not concept-driven. The five
abstractions are the place the override mostly lands, but the rule
doesn't enumerate them; it tells the LLM where to look. The Python
plane matters as much as the MCP and skills planes — when a user is
writing notebook or script code, the same precedence applies; the
override surface is the deriva-ml package, the inherited default is
deriva-py.

This replaces the existing "Steering principle" prose in
`deriva-ml-context` (lines 64-76 as of the round). The 5-bullet
"what raw tools bypass" list (business logic, FK validation,
provenance, version, RAG, audit) is retained as the *why* — kept as
prose because it's a single conceptual unit, not five independent
rows.

The existing inverse table at the bottom of the skill ("When to
reach back to the raw catalog surface") is significantly trimmed or
removed — under inheritance-as-default, "going back" to the deriva
plugin is just "doing the normal thing" and doesn't need an
explicit list. The plugin-pointer block can carry whatever residual
routing the LLM still needs.

If specific hybrid-mistake patterns surface during the cross-skill
audit pass (or in future use), they may be added as a small
"Common traps" subsection — but as flagged exceptions, not as a
comprehensive routing table.

## Consequences

**Positive:**

- Single rule the LLM holds in working memory; mechanical to apply.
- Survives new tools/skills/prompts/resources cleanly — when a new
  deriva-ml surface lands, the rule picks it up automatically
  without an edit.
- Eliminates the awkward "reach back to the raw catalog surface"
  inverse table — under inheritance, tier-1 is the default; "going
  back" is just "doing the normal thing."
- Builds the "DerivaML extends the data-centric philosophy"
  framing into the rule itself. The seven design pillars from
  tier-1 apply unchanged in a deriva-ml catalog because the rule
  says they do.
- The `deriva_ml_*` tool prefix already announces "this is the
  override surface" mechanically; the rule names the principle
  behind the prefix without re-stating it row-by-row.

**Negative / accepted trade-off:**

- The rule does not enumerate which specific `deriva_ml_*` tool
  maps to which operation (e.g., that "add a row to a dataset" is
  `deriva_ml_add_dataset_members`, not `deriva_ml_create_dataset`).
  This is acceptable because the per-abstraction lifecycle skills
  (`/deriva-ml:dataset-lifecycle`, `/deriva-ml:execution-lifecycle`,
  `/deriva-ml:create-feature`, `/deriva-ml:work-with-assets`) carry
  the operation-to-tool mapping at the right level of detail.
- The rule does not flag specific hybrid mistakes (e.g., direct
  writes to the underlying `Dataset_Element` association table via
  `insert_entities`). These can be added as a "Common traps"
  subsection if and when they prove to be a real failure mode.

## Audit-pass framing implication

The tier-2 cross-skill audit pass — originally framed as "reframe
parallel-options as directional precedence" — becomes "reframe
parallel-options as inheritance + override." For each of the ~33
existing `/deriva:<skill>` cross-references in tier-2 skill bodies,
the question is:

- **Inheritance:** there's no deriva-ml override for this; tier-1
  is the canonical home; the cross-reference is honest pointer to
  the tier-1 skill (no reframing needed).
- **Override:** there IS a deriva-ml way for this; the cross-reference
  should make the override explicit ("for ML entities use
  `/deriva-ml:foo`; for non-ML entities the deriva default
  `/deriva:bar` applies").

Most of the 33 cross-references are expected to fall in the
inheritance bucket and need no change — they're already pointing at
the right place; the rule just makes the relationship explicit.

## Alternatives considered

**(β) Routing table with tier-2 tool / tier-1 anti-tool / reason
columns.** Concrete and enumerable; LLM reads exact tool names
without a separate lookup. Rejected because the `deriva_ml_*`
prefix already carries the routing signal at the tool name level,
and the table would be expensive to maintain (every renamed or
added tool is a row edit) for a benefit the prefix already delivers.

**(γ) Rule plus a minimal "canonical tier-2 tool per abstraction"
table (no anti-tool column).** Rejected because the per-abstraction
lifecycle skills already are the canonical home for "the tier-2
tool for X operation"; a one-line-per-abstraction summary in
`deriva-ml-context` would either duplicate those skill bodies or be
too compressed to be useful.

**Earlier framing: precedence is about the five abstractions
specifically.** This was the version the audit and the original
plan used. Rejected during refinement: the override is not
concept-bounded (the five abstractions) but surface-bounded
(anywhere a deriva-ml `<thing>` exists). The two collapse to
roughly the same set in practice today, but the surface-bounded
framing is mechanical, future-proof, and matches how the LLM should
actually decide ("look for a deriva-ml `<thing>`; if found, use it").
