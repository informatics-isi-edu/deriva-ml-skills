# Design: OKF representation of the deriva-ml schema in `deriva-ml-context`

**Date:** 2026-06-27
**Status:** Draft (awaiting user review)
**Skills touched:** `deriva-ml-context` (new references bundle + a new body subsection), `create-feature` (fix a pre-existing stale table name surfaced by the audit).

## Problem

The plugin has no single, structural reference for the **fixed `deriva-ml`
catalog schema**. The 26 tables, their foreign keys, the FK graph, the
domain-schema-vs-`deriva-ml`-schema distinction, and the mapping of the five
abstractions to their backing tables are all *scattered operationally* across
skills (a table named in passing here, a status enum there) but never
consolidated. A duplication audit across all skills confirmed: no skill provides
this as a first-class reference. `browse-erd` gives a *live visual* of a specific
catalog, not a static always-available reference.

This change adds that reference as an **Open Knowledge Format (OKF)** bundle in
`deriva-ml-context`, teaches the two-schema distinction in the skill body, and
fixes a stale feature-table name the audit surfaced.

## Goal

1. A static, navigable OKF bundle documenting every fixed `deriva-ml` schema
   table, its FKs (as OKF links), and the FK graph — consumable by an agent or a
   human as schema context.
2. `deriva-ml-context` explicitly teaches **domain schema vs `deriva-ml`
   schema** and points at the bundle.
3. Avoid duplicating content owned by other skills — *point at* the asset-table
   shape (work-with-assets), the feature-table shape (create-feature), and the
   `Execution_Status` state machine (execution-lifecycle) rather than restate.
4. Fix the stale feature-table naming in `create-feature` so the bundle's
   feature pattern doc points at an accurate skill.

Source of truth: the deriva-ml library schema as of **v1.53.0**
(`deriva-ml/src/deriva_ml/schema/create_schema.py` + `core/mixins/feature.py`).
The bundle is pinned to that version.

## What this bundle owns vs points at (from the duplication audit)

**Newly owned** (no skill consolidates these today): the complete fixed-table
inventory; the FK graph as static text; the domain-vs-`deriva-ml`-schema model
as a concept; the five-abstractions → backing-tables mapping; the `File`,
`Directory_Dataset`, `Dataset_Execution`, and `Execution_Execution` tables
(absent or unnamed in every existing skill).

**Points at, does not restate:**

| Content | Owner the bundle links to |
|---|---|
| Asset-table shape (5 standard columns + `{Name}_Asset_Type` / `{Name}_Execution` associations) | `/deriva-ml:work-with-assets` (`references/concepts.md`) |
| Feature-table shape (column categories) | `/deriva-ml:create-feature` (`references/concepts.md`) |
| `Execution_Status` state machine (the transition diagram) | `/deriva-ml:execution-lifecycle` (`references/concepts.md`) |
| Live visual ERD for a specific catalog | `/deriva-ml:browse-erd` |

The bundle *names* `Execution_Status`'s values and the built-in asset tables (so
the inventory is complete) but defers the deep detail to the owner.

## Bundle structure

`skills/deriva-ml-context/references/concepts/` is an OKF bundle (the directory
tree is independent of domain — OKF groups by directory).

```
concepts/
  index.md                          # type: Index — bundle root (the entry point)
  table/                            # the 26 FIXED deriva-ml schema tables
    Dataset.md  Dataset_Version.md  Dataset_Type.md  Dataset_Dataset_Type.md
    Dataset_Dataset.md  Dataset_Execution.md  Dataset_File.md  Directory_Dataset.md
    Workflow.md  Workflow_Type.md  Workflow_Workflow_Type.md
    Execution.md  Execution_Execution.md  Execution_Status.md
    Execution_Metadata.md  Execution_Metadata_Asset_Type.md  Execution_Metadata_Execution.md
    Execution_Asset.md  Execution_Asset_Asset_Type.md  Execution_Asset_Execution.md
    File.md  File_Asset_Type.md  File_Execution.md
    Asset_Type.md  Asset_Role.md  Feature_Name.md
  pattern/                          # the RUNTIME-created shapes
    asset-table.md
    feature-table.md
```

### `index.md` (`type: Index`)

The single entry point and the OKF bundle root. Contains:
- The OKF declaration (a one-line "this is an OKF bundle following [spec-link]")
  and a pin to deriva-ml **v1.53.0** with a note to re-check when the library
  schema changes.
- The 26 tables listed **grouped by kind** (core / vocabulary / association /
  asset / satellite), each a relative link into `table/`.
- Links to the two `pattern/` docs.
- The **FK-graph-shape summary** (Execution→Workflow; Dataset.Version→Dataset_Version;
  Dataset_Version.Execution = output-dataset provenance; Dataset_Execution = input;
  the `*_Execution` asset associations carry `Asset_Role`; Dataset_Dataset /
  Execution_Execution self-nesting; etc.).
- The **five-abstractions → backing-tables mapping**.

Frontmatter: `type: Index`, `title`, `description`.

### `table/<Table>.md` (`type: Table`)

One per fixed table (26 total). Frontmatter: `type: Table`, `title` (the table
name), `kind` (a DerivaML extension key: `core` | `vocabulary` | `association` |
`asset` | `satellite`), `description`. Body:
- One-paragraph **purpose**.
- A **`## Foreign Keys`** section: every FK as a **relative sibling Markdown
  link** to the referenced table's doc (`[Workflow](Workflow.md)`) with the FK
  column name + the relationship named in the prose beside it (OKF links are
  untyped; prose conveys the edge). **Association tables name BOTH sides.**
  Tables with no outbound FK say so explicitly.
- **Notable columns** — only the structurally-significant ones (e.g.
  `Workflow.URL`/`Checksum`, `Execution.Status`, `Dataset_Version.Version`/`Snapshot`,
  `Directory_Dataset.Path`). Not an exhaustive column dump.
- **Vocabulary** docs (`kind: vocabulary`) additionally list their **seeded
  terms** (e.g. `Execution_Status`: Created, Running, Stopped, Pending_Upload,
  Uploaded, Failed, Aborted — and a link to execution-lifecycle for the state
  machine; `Dataset_Type`: Complete, File, Directory, Training, Testing,
  Validation, Split, Labeled, Unlabeled; etc.).

**Link form: relative sibling links** (`Workflow.md`, not `/Workflow.md`).
Because all 26 table docs are siblings in `table/`, these resolve correctly no
matter where the whole `concepts/` tree is located or copied to — the strongest
"works regardless of bundle location" guarantee. (This deliberately diverges
from the design-doc bundle's bundle-absolute form, which was right there because
those docs lived in different per-entity subdirectories; here the linked docs
are co-located siblings.)

The 26 tables and their kinds (from the v1.53.0 source):

- **core:** `Dataset`, `Dataset_Version`, `Workflow`, `Execution`
- **vocabulary:** `Dataset_Type`, `Workflow_Type`, `Execution_Status`,
  `Asset_Type`, `Asset_Role`, `Feature_Name`
- **association:** `Dataset_Dataset_Type`, `Dataset_Dataset` (self),
  `Dataset_Execution`, `Dataset_File`, `Workflow_Workflow_Type`,
  `Execution_Execution` (self), `Execution_Metadata_Asset_Type`,
  `Execution_Metadata_Execution`, `Execution_Asset_Asset_Type`,
  `Execution_Asset_Execution`, `File_Asset_Type`, `File_Execution`
- **asset:** `Execution_Metadata`, `Execution_Asset`, `File`
- **satellite:** `Directory_Dataset`

### `pattern/asset-table.md` (`type: Pattern`)

The invariant **shape** every asset table has — the 5 standard columns
(`Filename`, `URL`, `Length`, `MD5`, `Description`) and the auto-created
`{Name}_Asset_Type` and `{Name}_Execution` (with `Asset_Role`) associations —
and the fact that the 3 built-in asset tables (`Execution_Metadata`,
`Execution_Asset`, `File`) are in this schema while `create_asset` mints **new**
asset tables **in the domain schema** at runtime. Does NOT restate the column
list in depth — **points at `/deriva-ml:work-with-assets`** (which owns it). The
column list here is a one-line summary + the cross-reference.

### `pattern/feature-table.md` (`type: Pattern`)

The runtime-created feature-table shape: named **`Execution_{TargetTable}_{FeatureName}`**
(the *correct* library name, e.g. `Execution_Image_Image_Classification`), with
the always-present FKs (`Execution`, `{TargetTable}`, `Feature_Name`) plus the
per-definition term/asset/metadata columns; `Feature_Name` (the vocabulary)
registers the names. Discovery: any association table with both `Feature_Name`
and `Execution` columns is a feature table. Does NOT restate the full column
detail — **points at `/deriva-ml:create-feature`** (which owns it, *after* the
naming fix below).

## `deriva-ml-context/SKILL.md` change

Add a subsection (near "## The five core abstractions") teaching the two-schema
model — currently only implied by operational examples (`schema="deriva-ml"` vs
`domain_schemas={...}`), never explained as a concept:

- **The `deriva-ml` schema** — the 26 fixed tables backing the five abstractions.
  Library-managed; extend only via the `deriva_ml_*` surface (and `add_term` for
  the built-in vocabularies). The abstractions are *backed by* these tables.
- **The domain schema** — your project's own tables (`Subject`, `Image`, …),
  created per-project, named after the project. Runtime-created **asset** and
  **feature** tables (via `create_asset` / `create_feature`) land here, not in
  `deriva-ml`.
- A pointer: *"For the concrete table-by-table reference — every `deriva-ml`
  table, its foreign keys, and the FK graph — see `references/concepts/index.md`
  (an OKF bundle)."*

Additive only. `name`/`description` frontmatter stays byte-identical.

## `create-feature` fix (pre-existing defect surfaced by the audit)

The library names feature tables `Execution_{TargetTable}_{FeatureName}`
(`core/mixins/feature.py:176`), and 4 skills already use that form
(`ml-data-engineering`, `dataset-lifecycle`, `capture-tacit-knowledge`,
`generate-scripts`). But `create-feature` — the skill that *owns* features —
documents the stale `{FeatureName}_Feature_Value` name in 5 spots:

- `create-feature/references/concepts.md:462`
- `create-feature/references/workflow.md:55, 162, 169, 176`

Fix all 5 to the correct form (e.g. the worked example's
`Tumor_Classification_Feature_Value` → `Execution_Image_Tumor_Classification`).
This makes `create-feature` accurate so the bundle's `pattern/feature-table.md`
points at a correct doc, and removes a real plugin-internal contradiction.

**Out of scope:** `use-annotation-builders/SKILL.md:134` mentions
`Feature_Value_Image_fkey` — that is an *illustrative annotation FK-constraint
name* in a `VisibleForeignKeys` example, not a statement of the feature-table
name. It is a different (illustrative) thing; rewriting it would be scope creep
on an unrelated example. Left as-is, noted here as a conscious exclusion.

## Cross-repo note (`_CONCEPTS_GUIDE` mirror)

`deriva-ml-context/SKILL.md` mirrors `_CONCEPTS_GUIDE` in
`deriva-ml-mcp-plugin/src/deriva_ml_mcp_plugin/prompts.py` (the documented sync
constraint). This change is **additive** — a new references bundle + a new body
subsection — and the conceptual core that the mirror must match (the five
abstractions, the inheritance rule, the vocabulary-extension pattern) is
**unchanged**. So no re-sync of the mirror is required. Recorded here so it's a
conscious call, not an oversight.

## Verification

- Every `table/<T>.md` parses (YAML frontmatter + Markdown), carries `type: Table`
  + a `kind`, and has a `## Foreign Keys` section.
- All FK links resolve as siblings within `table/` (no dangling link; the whole
  bundle is self-contained — moving `concepts/` anywhere keeps links valid).
- The 26 tables exactly match the v1.53.0 inventory (no missing table, no invented
  one); association docs name both sides.
- `index.md` lists all 26 + both patterns + the FK-graph + the abstraction mapping.
- The two `pattern/` docs point at work-with-assets / create-feature and do NOT
  restate the column lists those skills own.
- `deriva-ml-context` body has the two-schema subsection + the pointer; its
  `name`/`description` frontmatter byte-identical.
- `create-feature` no longer contains `{FeatureName}_Feature_Value` /
  `Tumor_Classification_Feature_Value`; uses `Execution_{Target}_{Feature}` form.
- No skill outside `create-feature` is changed by the naming fix (the
  use-annotation-builders line is deliberately untouched).

## Risks / open points

- **Version pinning.** The bundle is a static snapshot of v1.53.0. When the
  library schema changes, the bundle goes stale; `index.md` records the version
  so the staleness is visible. (A future improvement could generate the bundle
  from the live schema, but that's out of scope — YAGNI.)
- **27 files.** Larger surface than a single doc, but each is small and
  single-purpose, the diff localizes which table changed, and progressive
  disclosure (index first, drill on demand) was the explicit reason for the
  per-table split.
- **Relative vs bundle-absolute links** diverge from the design-doc bundle. This
  is deliberate (co-located siblings vs per-entity subdirs) and documented above.
