# D/E/F Maintainability Wave — Design

**Date:** 2026-06-27
**Source:** Clusters D, E, F of [`docs/superpowers/notes/2026-06-27-global-assay.md`](../notes/2026-06-27-global-assay.md)
**Shape:** one dependency-ordered PR (the June-25 compaction wave is the precedent)
**Scope:** maintainability only — no user-facing behavior change, no accuracy fixes (those shipped in Clusters A/C, PRs #97/#98).

## Goal

Reduce duplication, decompose oversized reference files into addressable OKF
bundles, and trim heavy always-on / auto-firing skills — without changing what
any skill *does*. Every change is a content move + pointer, an OKF restructure,
or a dedup. No trigger changes, no API guidance changes.

## Why one PR, dependency-ordered

The three clusters interact: decomposing `execution-lifecycle/references/concepts.md`
(E) produces the canonical **status-machine** doc that the status-dedup (F) points
at, which in turn lets `troubleshoot-execution` shed its duplicate transition table
(D). Splitting these into separate PRs would force D and F to wait on E. One PR,
executed E → F → D, keeps the dependency chain coherent.

## Conventions (inherited from the v1.12.0 schema bundle)

- An OKF bundle is a directory `references/concepts/` with a reserved
  `index.md` (`type: Index`) plus per-concept docs.
- Frontmatter: `type:` (required) + `title` + `description`. `resource:` omitted
  (these are reference concepts, not pointers to external artifacts).
- Links between sibling docs are **relative** (`[Status machine](status-machine.md)`),
  matching `deriva-ml-context/references/concepts/`.
- Cross-skill references stay inline-code skill names (`/deriva-ml:execution-lifecycle`),
  never `[]()` links — per the established repo convention.
- **Granularity decision:** cluster related H2 sections into **4–6 coherent OKF
  docs per bundle**, NOT one-file-per-H2. These concept files are narrative prose
  with heavy cross-referencing (15–20 short H2s each); one-file-per-H2 would yield
  60–70 fragments that read as pieces of a narrative, not standalone concepts. The
  schema bundle used one-file-per-table because tables are atomic, independently
  *queried* entities — a different shape. Each clustered doc must be a real
  standalone concept with a meaningful `type:`.

## Phase 1 — E: OKF decomposition (do FIRST; unblocks D + F)

Each oversized concept file becomes a `references/concepts/` bundle. The original
`concepts.md` is **deleted** and replaced by the bundle; the owning SKILL.md's
pointer is updated to the bundle `index.md` (and to specific docs where it
currently points at a named section).

### 1a. `execution-lifecycle/references/concepts.md` (687L) → 5 docs

| OKF doc | `type:` | Folds in these current H2s |
|---|---|---|
| `status-machine.md` | StateMachine | Execution Statuses, Re-Running an Aborted Execution, the status table. **Canonical status machine — F-status-dedup points here.** |
| `structure.md` | Concept | Executions in the Catalog, Execution RIDs, Execution Structure, Nested Executions |
| `authoring.md` | Concept | Creating and Managing Executions, ExecutionConfiguration, The Execution Context Manager, Execution Working Directory, Execution Metadata Auto-Generation, Dry Run Mode |
| `validation.md` | Concept | Pre-Flight Validation, Schema Pinning for Long Runs, Offline Mode |
| `data-flow.md` | Concept | Execution Data Flow, Automatic Source Code Detection, Workflows and Workflow Types |

### 1b. `write-hydra-config/references/config-reference.md` (1271L) → 5 docs

Grouped by config-file family (the file is already organized this way).

| OKF doc | `type:` | Folds in |
|---|---|---|
| `base-and-connection.md` | ConfigReference | `__init__.py`, Base Config (`base.py`), Deriva Connection (`deriva.py`) |
| `data-configs.md` | ConfigReference | Datasets (`datasets.py`), Assets (`assets.py`), Workflow (`workflow.py`) + the two Architecture/Outputs blocks |
| `model-and-experiments.md` | ConfigReference | Model Config (`model.py`), Experiments (`experiments.py`) |
| `multiruns-and-notebooks.md` | ConfigReference | Multiruns (`multiruns.py`), Notebook Configs |
| `rules-and-validation.md` | ConfigReference | Per-Group Key Rules, Description Mechanisms, Config Class Parameter Reference, MCP Reference Resources, Bootstrap Configs from a Catalog, Validating Configs Against the Catalog. **Carries the Config-Groups material — F-config-groups-dedup points here.** |

### 1c. `dataset-lifecycle/references/concepts.md` (854L) → 5 docs

| OKF doc | `type:` | Folds in |
|---|---|---|
| `dataset-types.md` | Concept | What is a Dataset?, Dataset Types (the 3-axis framing), Dataset Element Types |
| `structure-and-splits.md` | Concept | Dataset Structure (Standalone/Nested/Splits), Splitting Datasets, Subsampling Datasets |
| `versioning.md` | Concept | Dataset Versioning (ADR-0003), Identifying a Dataset: RID + Version |
| `navigation.md` | Concept | Discovering Existing Datasets, Exploring and Navigating Datasets, Using Datasets, Downloading Datasets as Bags |
| `lifecycle-ops.md` | Concept | Deleting Datasets, Operations Summary, Characterization & validation (roadmap) |

### 1d. `create-feature/references/concepts.md` (597L) + `feature-selectors.md` (179L) → 4 docs

`feature-selectors.md` is folded into the `selectors.md` doc and deleted.

| OKF doc | `type:` | Folds in |
|---|---|---|
| `feature-vs-column.md` | Concept | What is a Feature?, When to Use a Feature vs a Column |
| `design.md` | Concept | Feature Types, Designing a Feature, Feature Naming, Metadata Columns, Feature Column Optionality and Valid Values, Multivalued Features |
| `selectors.md` | Concept | Feature Selection + the whole of `feature-selectors.md` |
| `usage.md` | Concept | Discovering Existing Features, Feature Records (Python API), Features in Datasets, Exploring and Navigating Features, Feature Value Table Naming, Operations Summary |

**Each bundle gets an `index.md`** (`type: Index`) listing its docs with one-line
descriptions, matching the schema-bundle index.

## Phase 2 — F: dedup (uses E's canonical docs)

| Duplication | Verified state | Resolution |
|---|---|---|
| Status state-machine | troubleshoot-execution status table (lines 252-257) + execution-lifecycle concepts | execution-lifecycle's new `status-machine.md` is canonical. troubleshoot-execution KEEPS its **salvage-decision** table (troubleshooting-specific: "salvageable? / what to run") but its transition *descriptions* point at the canonical doc. |
| `restructure-guide.md` ×2 | **Near-duplicate confirmed** — same title + H2 structure; ml-data-engineering 498L, work-with-assets 217L (a trimmed copy + a couple unique sections). Neither cross-references the other. | `ml-data-engineering` owns restructuring (its description scopes it). Merge work-with-assets's unique bits (Upload Tuning, ML Framework Patterns if absent upstream) INTO the canonical guide, then replace work-with-assets's copy with a pointer to `/deriva-ml:ml-data-engineering`'s guide. |
| find/list taxonomy | deriva-ml-context:204-210 (full `find_*` vs `list_*` taxonomy) + api-naming-conventions | api-naming-conventions owns. deriva-ml-context → 2-line summary + pointer. |
| Config-Groups table | configure-experiment SKILL + write-hydra-config | write-hydra-config owns (now in `rules-and-validation.md`). configure-experiment → pointer. |
| MCP primer/resource rules | deriva-ml-context + using-deriva-mcp | using-deriva-mcp owns the cold-start. deriva-ml-context keeps a short pointer (the precedence frame stays; the *procedure* points out). |

## Phase 3 — D: compaction (uses E + F results)

| Skill (current L) | Action | Target |
|---|---|---|
| `troubleshoot-execution` (497) | Move the Salvage section (lines ~234-395, ~162L) → `references/salvage-guide.md`; SKILL keeps the symptom-routing + salvage-decision tables + a pointer. F-status-dedup further trims the transition prose. | < ~330L |
| `capture-tacit-knowledge` (301) | Move the entry-format mechanics (~lines 72-212) → `references/entry-format.md`; SKILL keeps the trigger discipline + a pointer. | < ~200L |
| `compare-model-runs` (358) | Move Pattern B/C inline code → its existing references (Pattern A is the common path, stays inline). | < ~280L |
| `deriva-ml-context` (344) | Two D actions beyond F: (a) the **entity-resolution workflow** (lines 260-313, ~54L) — keep the compact numbered steps + the one-line "why it matters" inline (it's load-bearing always-on behavior), but move the expanded rationale + the read-through-index caveat detail to `references/entity-resolution.md`, and strengthen the pointer to `/deriva:semantic-awareness` *(deriva-skills)* as the owner of the underlying find-before-create discipline (it already cites it). (b) F handles find/list → pointer and MCP-primer → pointer. | < ~280L |

## Out of scope

- **G1** (`deriva_ml_describe_rid` zero coverage) — routed to Cluster B
  (domain-scientist skill); not folded here.
- **The other E candidates** the assay listed as single-source
  (`design-experiment` templates already got OKF frontmatter in #94;
  `generate-scripts/script-patterns.md` [1-claude]) — deferred; this wave does
  the 4 `[BOTH]`-flagged files only.
- Any accuracy / trigger change — those are Clusters A/C, already shipped.

## Risks & mitigations

- **Broken cross-references** — decomposing concept files moves anchor targets.
  *Mitigation:* a repo-wide grep sweep for every `concepts.md` / `feature-selectors.md`
  reference (and named-section links into them) is a required final task; update
  each pointer to the new bundle doc.
- **Content loss during merge/move** — *Mitigation:* moves are cut-paste of whole
  sections, not rewrites; a conformance task diffs section inventories before/after
  to confirm nothing dropped.
- **OKF link rot inside bundles** — *Mitigation:* the schema-bundle conformance
  pattern (verify every relative sibling link resolves) is re-run per bundle.
- **Large diff** — accepted; the wave is coherent and each phase is independently
  reviewable in the plan's task breakdown.

## Success criteria

1. The 4 oversized reference files are replaced by OKF bundles (4–6 typed docs each
   + index), original monoliths deleted.
2. `feature-selectors.md` folded into the feature bundle and deleted.
3. The 5 F-duplications each have one owner + a pointer from the other side; the
   `restructure-guide.md` near-dup is collapsed to one canonical file.
4. The 4 D skills are trimmed (depth moved to references), each SKILL.md leaner with
   working pointers.
5. Repo-wide cross-reference sweep passes — no dangling pointers to moved/renamed/
   deleted files or sections.
6. No SKILL.md frontmatter or trigger description changed (this wave is body/reference
   only).
