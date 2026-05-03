# Round 2 refinement — addendum to 2026-05-02 plan

This addendum records the refinement interview for Round 2 of the
[2026-05-02 tier-2 audit cleanup plan](2026-05-02-tier-2-audit-cleanup-plan.md).
The interview substantially reshaped Round 2 from its original framing
("add three lifecycle prompts to close the asymmetry") to a much
smaller, architecturally cleaner change ("delete two mis-shaped or
redundant prompts; redistribute content to its proper homes; widen
RAG coverage to top-level files").

Twelve design questions resolved, walking down each branch of the
design tree with a recommended answer per question.

## Audit findings revisited (2026-05-02)

Round 2's original framing came from the MCP-side audit:

- 4 prompts (`deriva_ml_concepts`, `deriva_ml_getting_started`,
  `deriva_ml_execution_lifecycle`, `deriva_ml_workflow_dedup`) —
  asymmetric, since executions get a lifecycle prompt but datasets,
  features, and assets don't.
- 11 catalog-state resources (datasets/workflows/executions/features/
  assets, listed and per-RID).
- ~50 tools.
- 4 RAG indexing hooks (per-user dataset/workflow/execution rows;
  bulk vocabulary; plus a `deriva-ml/docs/` GitHub source via
  `_GITHUB_DOCS_PATH_PREFIX = "docs/"`).

Original Round 2 plan: add three lifecycle prompts (dataset, feature,
asset) mirroring `_EXECUTION_LIFECYCLE_GUIDE`'s pattern. Estimated
1-2 hours, low risk.

The refinement found that this framing was wrong on two counts.

**First**, the four existing "prompts" aren't really MCP prompts.
The MCP spec and FastMCP guidance describe prompts as
**user-controlled, parameterized message templates** ("do not
over-engineer prompts — the host model is far better at orchestrating
tool sequences than your prompt template will ever be"). The four
existing prompts in deriva-ml-mcp are static reference documents
registered as prompts — a holdover that overloads the prompt
mechanism for a job it wasn't designed for. The cross-repo CLAUDE.md
note explicitly says they exist to mirror the always-on
`deriva-ml-context` skill for non-Claude-Code clients; that's
documentation delivery, not parameterized templating.

**Second**, the "lifecycle prompts asymmetry" gap doesn't actually
exist. The deriva-ml repo's `docs/user-guide/{datasets,features,
executions}.md` files (498, 505, 510 lines respectively) already
cover the per-domain lifecycle depth content at multiple times the
density of an `_EXECUTION_LIFECYCLE_GUIDE`-style prompt — and they're
already RAG-indexed via `_GITHUB_DOCS_PATH_PREFIX = "docs/"`. Adding
three new prompts duplicates content the LLM can already RAG-search
for.

These two findings reshaped Round 2 from "add three prompts" to
"delete the redundant/mis-shaped prompts; redistribute their content
to the proper homes."

## Architectural target (where each kind of content belongs)

The refinement established a four-surface map for what content goes
where:

| Surface | Right for | Access pattern |
|---|---|---|
| **Tool docstring** | Per-tool LLM-trap warnings; per-tool parameter docs | LLM sees automatically when considering the call |
| **MCP resource** (existing catalog-state pattern) | Live data: datasets, executions, etc. URI-addressable | LLM reads on demand by URI |
| **README + RAG** | Per-domain depth / reference content | LLM reads README via web; RAG-searches for hits |
| **Server `instructions=` field** (FastMCP) | Cross-cutting cold-start orientation; the operating contract | Delivered to every client at session init |

The four existing "prompts" map to those surfaces:

| Existing prompt | Right home | Notes |
|---|---|---|
| `_WORKFLOW_DEDUP_GUIDE` | Tool docstring on `deriva_ml_create_workflow` (and a complementary note on `deriva_ml_find_workflow_by_url`) | Per-tool LLM-trap warning belongs *on the trap*, not in a separate document |
| `_EXECUTION_LIFECYCLE_GUIDE` | Per-tool pitfalls onto the 4-5 lifecycle tools' docstrings; cross-cutting depth already in `user-guide/executions.md` (RAG-indexed) | Redundant with existing RAG-indexed docs |
| `_CONCEPTS_GUIDE` | Server `instructions=` field (right home; requires deriva-mcp-core API addition that doesn't exist yet) | Cold-start orientation; no clean alternative without the core API |
| `_GETTING_STARTED_GUIDE` | Server `instructions=` field (same) | Cold-start operating contract; no clean alternative without the core API |

## Cross-repo asks raised in parallel (option y)

Two API additions to deriva-mcp-core would unblock the architectural
end state:

1. **`ctx.add_instructions(text)` plugin API** — lets plugins
   contribute to the server's `instructions=` field that FastMCP
   sends to clients at init. Without this, cold-start orientation
   has nowhere to land cleanly outside of prompts. With it,
   `_CONCEPTS_GUIDE` and `_GETTING_STARTED_GUIDE` can move there
   and the prompt mechanism can be freed for its actual purpose
   (parameterized templates, when we have any).

2. **`exclude_paths=[...]` parameter on the GitHub crawler** — lets
   RAG sources widen their `path_prefix` (e.g., to `""` for
   repo-root coverage) while excluding specific files (e.g.,
   `CLAUDE.md`, `.pytest_cache/README.md`). Without this, widening
   the prefix indexes some maintainer-only files alongside the
   intended ones. With it, the indexing is tight.

The user has raised these with the deriva-mcp-core maintainer in
parallel. Round 2 ships the small clean improvements that don't
depend on either API; follow-up rounds finish the migration when
the APIs land.

## Resolved decisions

| # | Question | Resolution |
|---|---|---|
| 1 | Prompt-shape: full mirror, operational essentials, or hybrid? | Re-grounded — these aren't really prompts |
| 2 | What becomes of the four existing prompts? | Mixed: keep 2 cold-start; delete 2 (one mis-shaped, one redundant) |
| 3 | Should we add resources for new lifecycle content? | No — wrong primitive; resources are for files/schemas/data, not docs |
| 4 | Three-surface split (docstrings / README / RAG) | Approved as architectural target |
| 5 | RAG indexing scope — tier-2 skills too? | No — skills stay out of RAG (option j: just the 3 top-level files) |
| 6 | What about RAG implementation details? | Deferred to question 10 |
| 7 | Which existing prompts to keep / delete? | Option (w): keep cold-start, delete redundant + mis-shaped |
| 8 | Use server `instructions=` field instead? | Architecturally correct; requires core API addition |
| 9 | Path forward given missing core API? | Option (w) ships now; option (y) raised in parallel |
| 10 | RAG indexing under no-exclusion constraint | Option (δ): widen prefix; accept mild noise; raise exclusion API in parallel |
| 11 | Commit sequencing | 4 commits, content-first ordering |
| 12 | Test impact of prompt deletions | Confirmed: tests assert "exactly four prompts"; updates ride along with each deletion commit |

## Round 2 final scope

**Delete two prompts** (with content redistributed to tool docstrings):

| Prompt | Content disposition |
|---|---|
| `_WORKFLOW_DEDUP_GUIDE` | Move to `deriva_ml_create_workflow` docstring; add complementary note on `deriva_ml_find_workflow_by_url` |
| `_EXECUTION_LIFECYCLE_GUIDE` | Per-tool pitfalls (state-machine acceptance sets, commit drains, `add_feature_values` dispatch) move onto `deriva_ml_start_execution`, `deriva_ml_commit_execution`, `deriva_ml_abort_execution`, `deriva_ml_add_feature_values` docstrings; cross-cutting depth is already in `user-guide/executions.md` (RAG-indexed) |

**Keep two prompts** (until `instructions=` API lands):

- `_CONCEPTS_GUIDE`
- `_GETTING_STARTED_GUIDE`

**Widen RAG indexing** to cover three top-level files:

| Repo | Change | Files newly indexed |
|---|---|---|
| `deriva-ml` | Change `_GITHUB_DOCS_PATH_PREFIX` from `"docs/"` to `""` | `README.md`, `CHANGELOG.md` (wanted); `CLAUDE.md` (mild noise) |
| `deriva-ml-mcp` | New `ctx.rag_github_source(...)` registration with `path_prefix=""` | `README.md` (wanted); `CLAUDE.md`, `docs/scratch/*.md` (mild noise) |

**Test updates** (each deletion commit includes the test update so
the repo stays in a coherent state):

- `tests/test_prompts.py` — currently asserts "exactly four prompts"
  and lists the four expected names; updates ride along with each
  deletion (commit 1 → assert 3 names; commit 2 → assert 2 names).
- `tests/test_plugin.py` — same pattern; the `_ML_PROMPT_NAMES`
  frozenset gets two members removed across the two commits.

## Final Round 2 execution plan: four commits

Round 2 ships as four focused commits, each independently revertable,
in this order. Same content-first discipline as Round 1.

### Commit 1 — Delete `_WORKFLOW_DEDUP_GUIDE`; move content to docstring

- Move the workflow-dedup content into `deriva_ml_create_workflow`'s
  docstring as a "Note: this tool is idempotent on (URL, checksum)"
  paragraph plus a worked correct vs anti-pattern example.
- Add a complementary one-paragraph note on
  `deriva_ml_find_workflow_by_url`'s docstring directing the LLM to
  use `create_workflow` instead unless the intent is read-only.
- Delete the `@ctx.prompt("deriva_ml_workflow_dedup", ...)`
  registration block from `prompts.py`.
- Delete the `_WORKFLOW_DEDUP_GUIDE` constant.
- Update `tests/test_prompts.py` and `tests/test_plugin.py` to
  assert 3 prompts and the 3 remaining names.

### Commit 2 — Delete `_EXECUTION_LIFECYCLE_GUIDE`; distribute pitfalls

- Distribute the per-tool warnings from the lifecycle prompt onto
  the relevant tool docstrings:
  - `deriva_ml_start_execution`: `_START_REJECT_STATES` reasoning
    (why Stopped/Failed/Pending_Upload/Uploaded/Aborted are rejected)
  - `deriva_ml_commit_execution`: `_COMMIT_ALLOWED_STATES` reasoning
    (why all five accepted states make sense; the
    Uploaded → Pending_Upload → Uploaded cycle for additive uploads)
  - `deriva_ml_abort_execution`: when to call vs let things drain
  - `deriva_ml_add_feature_values`: the hybrid dispatch behavior
    (per-record vs batch vs deferred-via-execution)
- Delete the `@ctx.prompt("deriva_ml_execution_lifecycle", ...)`
  registration block.
- Delete the `_EXECUTION_LIFECYCLE_GUIDE` constant.
- Update tests to assert 2 prompts (`_CONCEPTS_GUIDE`,
  `_GETTING_STARTED_GUIDE`).

### Commit 3 — Widen RAG indexing for top-level docs

- Change `_GITHUB_DOCS_PATH_PREFIX` from `"docs/"` to `""` in
  `resources/rag.py`. The existing source now indexes the deriva-ml
  repo's `README.md` and `CHANGELOG.md` alongside the `docs/`
  contents.
- Add a new `ctx.rag_github_source(...)` registration in
  `resources/rag.py` for `informatics-isi-edu/deriva-ml-mcp`,
  branch `main`, `path_prefix=""`, with a distinct source `name`
  (e.g., `"deriva-ml-mcp-docs"`) and `doc_type="ml-mcp-docs"` (to
  distinguish hits from the existing `"ml-docs"` source).
- No test impact expected.

### Commit 4 — Cross-repo sync notes; version bump; CHANGELOG

- Update the cross-repo sync section in `deriva-ml-mcp/CLAUDE.md`
  ("Cross-Repo Sync: `deriva_ml_concepts` prompt ↔
  `deriva-ml-context` skill"): note that two of the four prompts
  were deleted; the surviving two (`_CONCEPTS_GUIDE`,
  `_GETTING_STARTED_GUIDE`) still mirror the skill content; the
  long-term plan is to migrate them to server instructions when
  the deriva-mcp-core API lands.
- Update the matching cross-repo note in
  `deriva-ml-skills/CLAUDE.md` (mirrors the same section).
- Bump `deriva-ml-mcp` version per the project's `bump-version`
  process (this is a deletion of public surface — the four
  prompts go from 4 → 2 — so a minor or major bump per the
  project's semver discipline).
- Add a CHANGELOG entry describing the deletion (with a migration
  note: clients that listed `deriva_ml_workflow_dedup` or
  `deriva_ml_execution_lifecycle` should migrate to the
  corresponding tool docstrings or RAG-search the user-guide docs).

## Estimated effort

Original Round 2 estimate (from parent plan): 1-2 hours.

Refined estimate after the substantial reshape: **~90 min single
sitting**, all in `deriva-ml-mcp`. No cross-repo edits required
(the sync notes update touches `deriva-ml-skills` but that's a
single-line change). The earlier "Round 2 might require core API
changes" concern is parked under option y — the asks are raised
with the deriva-mcp-core maintainer in parallel; Round 2 doesn't
depend on them landing.

Per-commit estimate:

- Commit 1 (workflow-dedup): ~25 min (docstring authoring +
  test update)
- Commit 2 (execution-lifecycle): ~30 min (4 tool docstrings to
  update + test update)
- Commit 3 (RAG widening): ~15 min (one constant change + one
  new source registration)
- Commit 4 (sync + bump + CHANGELOG): ~20 min

## Dependencies and follow-up

Round 2 has no upstream dependencies — it can execute immediately.

After Round 2 ships, two follow-up items become possible when the
deriva-mcp-core APIs land:

- When `ctx.add_instructions(text)` lands: migrate `_CONCEPTS_GUIDE`
  and `_GETTING_STARTED_GUIDE` content into server instructions;
  delete the remaining two prompts. Round small (~30 min).
- When `exclude_paths=[...]` on the GitHub crawler lands: tighten
  the RAG source prefixes to drop the indexed maintainer files
  (`CLAUDE.md`) and scratch notes. Round small (~15 min).

Both follow-up rounds are content moves on top of the API
additions; the heavy work (deciding what content goes where) is
already done by Round 2's refinement.

## Quantitative impact

- MCP prompts: 4 → 2 (workflow-dedup + execution-lifecycle deleted;
  concepts + getting-started preserved until cross-repo API arrives)
- MCP tool docstrings: ~5 tools get expanded with content moved
  from prompts (richer per-tool guidance at the trap)
- RAG-indexed files: ~97 → ~104 (3 wanted top-level files plus
  ~4 noise files until exclusion API lands)
- Architectural correctness: partial — two of four mis-shaped
  prompts removed; the remaining two stay until the right home
  (server instructions) becomes available.

The "right" end state is documented but not reached in Round 2;
the cross-repo asks track the gap. Round 2 ships the work that's
clean today.
