# OKF deriva-ml Schema Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an OKF bundle to `deriva-ml-context` documenting the 26 fixed deriva-ml schema tables + FK graph + two runtime patterns, teach the domain-vs-deriva-ml-schema distinction in the skill body, and fix a stale feature-table name in create-feature.

**Architecture:** A new OKF bundle at `skills/deriva-ml-context/references/concepts/` — `index.md` (type:Index, entry point), `table/<T>.md` ×26 (type:Table, one per fixed table, FKs as relative-sibling links), `pattern/{asset-table,feature-table}.md` (type:Pattern, pointing at owning skills). The per-table content is **derived from the deriva-ml v1.53.0 source** (`deriva-ml/src/deriva_ml/schema/create_schema.py`), not invented. Plus a new SKILL.md subsection and a create-feature naming fix.

**Tech Stack:** Markdown + YAML frontmatter (OKF). Schema source of truth: `/Users/carl/GitHub/DerivaML/deriva-ml/src/deriva_ml/schema/create_schema.py` (and `core/mixins/feature.py` for the feature naming). No code runtime; "tests" are conformance checks (YAML parses, `type`/`kind` present, FK links resolve as siblings, table set matches the source inventory).

## Global Constraints

- **Schema source of truth (read it; do not invent FKs/columns):** `/Users/carl/GitHub/DerivaML/deriva-ml/src/deriva_ml/schema/create_schema.py`. Pin the bundle to **deriva-ml v1.53.0** (record in `index.md`).
- **The 26 fixed tables and their kinds (exact):**
  - core: `Dataset`, `Dataset_Version`, `Workflow`, `Execution`
  - vocabulary: `Dataset_Type`, `Workflow_Type`, `Execution_Status`, `Asset_Type`, `Asset_Role`, `Feature_Name`
  - association: `Dataset_Dataset_Type`, `Dataset_Dataset`, `Dataset_Execution`, `Dataset_File`, `Workflow_Workflow_Type`, `Execution_Execution`, `Execution_Metadata_Asset_Type`, `Execution_Metadata_Execution`, `Execution_Asset_Asset_Type`, `Execution_Asset_Execution`, `File_Asset_Type`, `File_Execution`
  - asset: `Execution_Metadata`, `Execution_Asset`, `File`
  - satellite: `Directory_Dataset`
- **Per-table doc:** frontmatter `type: Table`, `title: <Table>`, `kind: <core|vocabulary|association|asset|satellite>`, `description:`. Body: purpose paragraph, a `## Foreign Keys` section (each FK = a **relative sibling** Markdown link `[RefTable](RefTable.md)` + FK column + relationship in prose; **association tables name BOTH sides**; tables with no outbound FK say so), notable columns. Vocabulary docs also list seeded terms.
- **Link form: relative sibling** (`[Workflow](Workflow.md)`), NEVER bundle-absolute (`/Workflow.md`) — the bundle must resolve regardless of where `concepts/` is located.
- **Points-at, does-not-restate:** `pattern/asset-table.md` → `/deriva-ml:work-with-assets`; `pattern/feature-table.md` → `/deriva-ml:create-feature`; `Execution_Status.md` names its 7 values but points at `/deriva-ml:execution-lifecycle` for the state machine. Don't re-dump the asset 5-column list or the feature column categories — summarize + link.
- **Correct feature-table name (library truth):** `Execution_{TargetTable}_{FeatureName}` (e.g. `Execution_Image_Image_Classification`). NOT `{FeatureName}_Feature_Value`.
- **`deriva-ml-context` `name`/`description` frontmatter byte-identical** (additive body change only).
- **OKF spec URL (verbatim):** `https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md`
- **Do NOT touch** `use-annotation-builders` (its `Feature_Value_Image_fkey` is an illustrative annotation FK example, not the table-name defect).
- Spec: `docs/superpowers/specs/2026-06-27-okf-schema-bundle.md`.

---

### Task 1: Dataset-cluster table docs (8 tables)

**Files:**
- Create: `skills/deriva-ml-context/references/concepts/table/Dataset.md`, `Dataset_Version.md`, `Dataset_Type.md`, `Dataset_Dataset_Type.md`, `Dataset_Dataset.md`, `Dataset_Execution.md`, `Dataset_File.md`, `Directory_Dataset.md`

**Interfaces:**
- Produces: the canonical `type: Table` doc shape Tasks 2–4 mirror. Establishes the FK-link convention `[RefTable](RefTable.md)`. Sibling table docs these reference (`Workflow.md`, `Execution.md`, `Execution_Asset.md`, `Asset_Type.md`, `Asset_Role.md`, `File.md`) are created in later tasks — relative-sibling links to not-yet-created siblings are fine (OKF tolerates; the conformance check in Task 7 confirms all resolve once the bundle is complete).

- [ ] **Step 1: Read the source for this cluster.** Read `/Users/carl/GitHub/DerivaML/deriva-ml/src/deriva_ml/schema/create_schema.py` — the functions `create_dataset_table`, `define_table_dataset_version`, `directory_dataset_table_def`, and the `Table.define_association` calls for `Dataset_Dataset_Type`, `Dataset_Dataset`, `Dataset_Execution`, `Dataset_File`. Note each table's exact FK columns + referenced tables + notable columns. Do not proceed on memory — the doc content must match the source.

- [ ] **Step 2: Write the 8 docs**, each in this exact shape (here is `Dataset.md` fully; the others follow the same template with their own source-derived FKs/columns):

```markdown
---
type: Table
title: Dataset
kind: core
description: A versioned collection of catalog rows an execution consumed or produced.
---

# Dataset

A **versioned collection** of catalog rows (assets, files, nested datasets) that
an execution consumed or produced. Soft-deletable. The backing table of the
DerivaML **Dataset** abstraction; its version history lives in
[Dataset_Version](Dataset_Version.md).

## Foreign Keys

- `Version` → [Dataset_Version](Dataset_Version.md) — points at this dataset's
  **current** version row.

## Notable columns

- `Description` (markdown) — human-readable purpose.
- `Deleted` (boolean) — soft-delete flag.
- `Version` — FK to the current `Dataset_Version`.
```

For the others (source-derived):
- `Dataset_Version.md` (core): FKs `Dataset` → [Dataset](Dataset.md), `Execution` → [Execution](Execution.md) (nullable — the producing execution; output-dataset provenance lives here); notable: `Version` (PEP 440, default 0.1.0), `Description`, `Snapshot` (catalog snapshot id, NULL on dev rows), `Minid`, `Minid_Spec_Hash`; unique key `(Dataset, Version)`.
- `Dataset_Type.md` (vocabulary): no outbound FK; seeded terms — `Complete`, `File`, `Directory`, `Training`, `Testing`, `Validation`, `Split`, `Labeled`, `Unlabeled`. Note the three-axis framing is owned by `/deriva-ml:dataset-lifecycle`.
- `Dataset_Dataset_Type.md` (association): BOTH sides — `Dataset` → [Dataset](Dataset.md), `Dataset_Type` → [Dataset_Type](Dataset_Type.md).
- `Dataset_Dataset.md` (association, self): `Dataset` → [Dataset](Dataset.md) (parent), `Nested_Dataset` → [Dataset](Dataset.md) (member). Note `split_dataset` does NOT create this edge (source is an execution input instead).
- `Dataset_Execution.md` (association): `Dataset` → [Dataset](Dataset.md), `Execution` → [Execution](Execution.md), `Dataset_Version` → [Dataset_Version](Dataset_Version.md) (nullable). This is the **input** edge (execution consumed the dataset); contrast output via `Dataset_Version.Execution`.
- `Dataset_File.md` (association): `Dataset` → [Dataset](Dataset.md), `File` → [File](File.md).
- `Directory_Dataset.md` (satellite): `Dataset` → [Dataset](Dataset.md) (also unique key — one row per dataset); notable: `Path` (source directory; `"."` for ingest root). Created by `add_files`.

- [ ] **Step 3: Verify each parses + carries type/kind + has a Foreign Keys section.**

Run:
```bash
for t in Dataset Dataset_Version Dataset_Type Dataset_Dataset_Type Dataset_Dataset Dataset_Execution Dataset_File Directory_Dataset; do
  f="skills/deriva-ml-context/references/concepts/table/$t.md"
  awk '/^---$/{c++;next} c==1' "$f" | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Table' and d.get('kind'); print('$t', d['kind'])" && grep -q '^## Foreign Keys' "$f" && echo "  OK $t" || echo "  FAIL $t"
done
```
Expected: `OK` for all 8 with the right kind.

- [ ] **Step 4: Commit.**

```bash
git add skills/deriva-ml-context/references/concepts/table/
git commit -m "feat(deriva-ml-context): OKF schema docs — Dataset cluster (8 tables)"
```

---

### Task 2: Workflow + Execution cluster table docs (6 tables)

**Files:**
- Create: `table/Workflow.md`, `Workflow_Type.md`, `Workflow_Workflow_Type.md`, `Execution.md`, `Execution_Execution.md`, `Execution_Status.md`

**Interfaces:**
- Consumes: the doc shape + FK-link convention from Task 1.

- [ ] **Step 1: Read the source.** In `create_schema.py`: `create_workflow_table`, `create_execution_table`, the `Workflow_Workflow_Type` and `Execution_Execution` associations, and `initialize_ml_schema` for the `Workflow_Type` + `Execution_Status` seeded terms. Note exact FKs/columns.

- [ ] **Step 2: Write the 6 docs** (same `type: Table` shape as Task 1), source-derived:
- `Workflow.md` (core): no outbound FK (system only); notable `Name`, `Description`, `URL`, `Checksum` (git commit), `Version`. Content-addressed by `(URL, Checksum)`. Backing table of the **Workflow** abstraction.
- `Workflow_Type.md` (vocabulary): no outbound FK; seeded terms `Training`, `Testing`, `Prediction`, `Feature_Creation`, `Visualization`, `Analysis`, `Ingest`, `Data_Cleaning`, `Dataset_Management`.
- `Workflow_Workflow_Type.md` (association): BOTH sides — `Workflow` → [Workflow](Workflow.md), `Workflow_Type` → [Workflow_Type](Workflow_Type.md).
- `Execution.md` (core): FKs `Workflow` → [Workflow](Workflow.md), `Status` → [Execution_Status](Execution_Status.md); notable `Status_Detail`, `Execution_Duration`, `Download_Duration`, `Upload_Duration`, `Description`. Backing table of the **Execution** abstraction.
- `Execution_Execution.md` (association, self): `Execution` → [Execution](Execution.md) (parent), `Nested_Execution` → [Execution](Execution.md) (child); notable `Sequence` (int, nullable — orders children).
- `Execution_Status.md` (vocabulary): no outbound FK; seeded terms `Created`, `Running`, `Stopped`, `Pending_Upload`, `Uploaded`, `Failed`, `Aborted`. **Point at `/deriva-ml:execution-lifecycle` for the state-machine transitions** (don't redraw the diagram).

- [ ] **Step 3: Verify (same loop as Task 1, this cluster's 6 names).**

Run:
```bash
for t in Workflow Workflow_Type Workflow_Workflow_Type Execution Execution_Execution Execution_Status; do
  f="skills/deriva-ml-context/references/concepts/table/$t.md"
  awk '/^---$/{c++;next} c==1' "$f" | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Table' and d.get('kind')" && grep -q '^## Foreign Keys' "$f" && echo "  OK $t" || echo "  FAIL $t"
done
```
Expected: `OK` ×6.

- [ ] **Step 4: Commit.**

```bash
git add skills/deriva-ml-context/references/concepts/table/
git commit -m "feat(deriva-ml-context): OKF schema docs — Workflow + Execution cluster (6 tables)"
```

---

### Task 3: Asset + File cluster table docs (8 tables)

**Files:**
- Create: `table/Execution_Metadata.md`, `Execution_Metadata_Asset_Type.md`, `Execution_Metadata_Execution.md`, `Execution_Asset.md`, `Execution_Asset_Asset_Type.md`, `Execution_Asset_Execution.md`, `File.md`, `File_Asset_Type.md`, `File_Execution.md` — **wait, that's 9.** Correct set for this task is the 8 asset/file tables: `Execution_Metadata`, `Execution_Metadata_Asset_Type`, `Execution_Metadata_Execution`, `Execution_Asset`, `Execution_Asset_Asset_Type`, `Execution_Asset_Execution`, `File`, `File_Asset_Type`, `File_Execution` — that is 9 files. Create all 9 here (the asset/file cluster is 9 tables: 3 asset tables + 6 associations).

**Interfaces:**
- Consumes: the doc shape from Task 1.

- [ ] **Step 1: Read the source.** In `create_schema.py`: `create_asset_table` (used for `Execution_Metadata`, `Execution_Asset`, and `File` with `use_hatrac=False`), and the `*_Asset_Type` / `*_Execution` associations each creates (note the `Asset_Role` FK added to the `*_Execution` associations via `create_reference`).

- [ ] **Step 2: Write the 9 docs** (same shape), source-derived:
- `Execution_Metadata.md` (asset): standard asset shape; notable `URL`, `Filename`, `Length`, `MD5`, `Description`. Built-in asset table for execution environment/config files. Note the asset-table *shape* is documented in `pattern/asset-table.md` → `/deriva-ml:work-with-assets`.
- `Execution_Metadata_Asset_Type.md` (association): `Execution_Metadata` → [Execution_Metadata](Execution_Metadata.md), `Asset_Type` → [Asset_Type](Asset_Type.md).
- `Execution_Metadata_Execution.md` (association): `Execution_Metadata` → [Execution_Metadata](Execution_Metadata.md), `Execution` → [Execution](Execution.md), `Asset_Role` → [Asset_Role](Asset_Role.md).
- `Execution_Asset.md` (asset): standard asset shape; built-in table for execution data outputs (weights, CSVs, plots). Same shape note + link.
- `Execution_Asset_Asset_Type.md` (association): `Execution_Asset` → [Execution_Asset](Execution_Asset.md), `Asset_Type` → [Asset_Type](Asset_Type.md).
- `Execution_Asset_Execution.md` (association): `Execution_Asset` → [Execution_Asset](Execution_Asset.md), `Execution` → [Execution](Execution.md), `Asset_Role` → [Asset_Role](Asset_Role.md).
- `File.md` (asset): standard asset shape but **by-reference** (`use_hatrac=False`) — `URL` points at bytes the catalog references but does not host. Used by `add_files`.
- `File_Asset_Type.md` (association): `File` → [File](File.md), `Asset_Type` → [Asset_Type](Asset_Type.md).
- `File_Execution.md` (association): `File` → [File](File.md), `Execution` → [Execution](Execution.md), `Asset_Role` → [Asset_Role](Asset_Role.md).

- [ ] **Step 3: Verify (same loop, this cluster's 9 names).**

Run:
```bash
for t in Execution_Metadata Execution_Metadata_Asset_Type Execution_Metadata_Execution Execution_Asset Execution_Asset_Asset_Type Execution_Asset_Execution File File_Asset_Type File_Execution; do
  f="skills/deriva-ml-context/references/concepts/table/$t.md"
  awk '/^---$/{c++;next} c==1' "$f" | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Table' and d.get('kind')" && grep -q '^## Foreign Keys' "$f" && echo "  OK $t" || echo "  FAIL $t"
done
```
Expected: `OK` ×9.

- [ ] **Step 4: Commit.**

```bash
git add skills/deriva-ml-context/references/concepts/table/
git commit -m "feat(deriva-ml-context): OKF schema docs — Asset + File cluster (9 tables)"
```

---

### Task 4: Remaining vocabulary table docs (3 tables)

**Files:**
- Create: `table/Asset_Type.md`, `table/Asset_Role.md`, `table/Feature_Name.md`

**Interfaces:**
- Consumes: the doc shape from Task 1. These are the vocabulary tables referenced by Tasks 1–3's association docs.

- [ ] **Step 1: Read the source.** In `create_schema.py` `initialize_ml_schema`: the seeded terms for `Asset_Type` and `Asset_Role`; and `create_ml_schema` for the `Feature_Name` vocabulary.

- [ ] **Step 2: Write the 3 docs** (`type: Table`, `kind: vocabulary`, no outbound FK):
- `Asset_Type.md`: seeded terms `Execution_Config`, `Runtime_Env`, `Hydra_Config`, `Deriva_Config`, `Metrics_File`, `Execution_Metadata`, `Execution_Asset`, `File`, `Input_File`, `Output_File`, `Model_File`, `Notebook_Output`. Classifies assets; referenced by every `{Asset}_Asset_Type` association.
- `Asset_Role.md`: seeded terms `Input`, `Output`. Distinguishes direction on every `{Asset}_Execution` association.
- `Feature_Name.md`: registry of feature names; every `create_feature` adds a term here. Referenced by every feature table (`Execution_{Target}_{Feature}`) — note the feature-table shape is in `pattern/feature-table.md` → `/deriva-ml:create-feature`.

- [ ] **Step 3: Verify.**

Run:
```bash
for t in Asset_Type Asset_Role Feature_Name; do
  f="skills/deriva-ml-context/references/concepts/table/$t.md"
  awk '/^---$/{c++;next} c==1' "$f" | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Table' and d['kind']=='vocabulary'" && echo "  OK $t" || echo "  FAIL $t"
done
echo "Total table docs: $(ls skills/deriva-ml-context/references/concepts/table/*.md | wc -l | tr -d ' ') (want 26)"
```
Expected: `OK` ×3; total = 26.

- [ ] **Step 4: Commit.**

```bash
git add skills/deriva-ml-context/references/concepts/table/
git commit -m "feat(deriva-ml-context): OKF schema docs — vocabulary tables (Asset_Type, Asset_Role, Feature_Name)"
```

---

### Task 5: The two pattern docs

**Files:**
- Create: `skills/deriva-ml-context/references/concepts/pattern/asset-table.md`, `pattern/feature-table.md`

**Interfaces:**
- Consumes: the `table/` docs (these patterns reference the built-in asset tables and `Feature_Name`). Pattern docs link UP to the owning skills, not into `table/` (different relative depth — see note).

- [ ] **Step 1: Write `asset-table.md`** (`type: Pattern`). It describes the invariant asset-table SHAPE and the runtime-creation fact, then points at work-with-assets — it does NOT re-dump the column list:

```markdown
---
type: Pattern
title: Asset table shape
description: The invariant shape every DerivaML asset table has, fixed and runtime-created.
---

# Asset table shape

Every DerivaML **asset table** has the same shape: the five standard columns
(`Filename`, `URL`, `Length`, `MD5`, `Description`) plus two auto-created
association tables — `{Name}_Asset_Type` (tags the asset with
[Asset_Type](../table/Asset_Type.md) terms) and `{Name}_Execution` (links it to
an [Execution](../table/Execution.md) with an [Asset_Role](../table/Asset_Role.md)
of Input or Output).

The `deriva-ml` schema ships **three built-in** asset tables:
[Execution_Metadata](../table/Execution_Metadata.md),
[Execution_Asset](../table/Execution_Asset.md), and
[File](../table/File.md) (by-reference). **Domain asset tables** (`Image`,
`Model_Weights`, …) are created at runtime by `create_asset` and live in your
**project's domain schema**, not in `deriva-ml`.

For the full column reference, the `create_asset_table` mechanics, and how to
work with assets, see **`/deriva-ml:work-with-assets`** (it owns this surface).
```

- [ ] **Step 2: Write `feature-table.md`** (`type: Pattern`), using the CORRECT library naming:

```markdown
---
type: Pattern
title: Feature table shape
description: The runtime-created shape of a DerivaML feature-value table.
---

# Feature table shape

A DerivaML **feature** is stored in a runtime-created association table named
`Execution_{TargetTable}_{FeatureName}` — for example, an `Image_Classification`
feature on the `Image` table is stored in `Execution_Image_Image_Classification`.
`create_feature` mints one such table per `(target_table, feature_name)` pair and
registers the name in the [Feature_Name](../table/Feature_Name.md) vocabulary.

Every feature table carries these FKs: `Execution` →
[Execution](../table/Execution.md), `{TargetTable}` → the annotated domain table,
and `Feature_Name` → [Feature_Name](../table/Feature_Name.md) — plus one column
per vocabulary term, asset, and metadata field the feature defines. **Discovery:**
any association table with both `Feature_Name` and `Execution` columns is a
feature table.

Feature tables live in the **domain schema** (alongside the target table), not in
`deriva-ml`. For the full column reference and how to create/populate features,
see **`/deriva-ml:create-feature`** (it owns this surface).
```

- [ ] **Step 3: Verify both parse + are type:Pattern + point at the right skills + link siblings with `../table/`.**

Run:
```bash
for p in asset-table feature-table; do
  f="skills/deriva-ml-context/references/concepts/pattern/$p.md"
  awk '/^---$/{c++;next} c==1' "$f" | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Pattern'; print('  OK $p')"
done
grep -q "work-with-assets" skills/deriva-ml-context/references/concepts/pattern/asset-table.md && echo "  asset→work-with-assets OK"
grep -q "create-feature" skills/deriva-ml-context/references/concepts/pattern/feature-table.md && echo "  feature→create-feature OK"
grep -q "Execution_{TargetTable}_{FeatureName}\|Execution_Image_Image_Classification" skills/deriva-ml-context/references/concepts/pattern/feature-table.md && echo "  feature name CORRECT" || echo "  FAIL feature name"
```
Expected: both `OK Pattern`, both skill pointers present, feature name correct.

- [ ] **Step 4: Commit.**

```bash
git add skills/deriva-ml-context/references/concepts/pattern/
git commit -m "feat(deriva-ml-context): OKF schema patterns — asset-table + feature-table (point at owning skills)"
```

---

### Task 6: The bundle index

**Files:**
- Create: `skills/deriva-ml-context/references/concepts/index.md`

**Interfaces:**
- Consumes: all 26 `table/` docs + the 2 `pattern/` docs (links them).

- [ ] **Step 1: Write `index.md`** (`type: Index`) — the bundle root and single entry point:

```markdown
---
type: Index
title: deriva-ml catalog schema
description: >
  The fixed deriva-ml catalog schema — every table, its foreign keys, and the
  FK graph — as an OKF bundle.
---

# deriva-ml catalog schema

These documents follow the
[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
— Markdown + YAML frontmatter. This bundle is the static reference for the
**fixed `deriva-ml` schema** as of **deriva-ml v1.53.0**; re-check it against the
library when the schema changes. For a live visual of a *specific* catalog, use
`/deriva-ml:browse-erd`.

> **`deriva-ml` schema vs domain schema.** These 26 tables are the fixed
> `deriva-ml` schema that backs the five abstractions — library-managed. Your
> project's own tables (`Subject`, `Image`, …) live in a separate **domain
> schema** named after the project; runtime-created asset and feature tables
> land there too (see the patterns below).

## Tables

**Core** — [Dataset](table/Dataset.md), [Dataset_Version](table/Dataset_Version.md), [Workflow](table/Workflow.md), [Execution](table/Execution.md)

**Vocabulary** — [Dataset_Type](table/Dataset_Type.md), [Workflow_Type](table/Workflow_Type.md), [Execution_Status](table/Execution_Status.md), [Asset_Type](table/Asset_Type.md), [Asset_Role](table/Asset_Role.md), [Feature_Name](table/Feature_Name.md)

**Association** — [Dataset_Dataset_Type](table/Dataset_Dataset_Type.md), [Dataset_Dataset](table/Dataset_Dataset.md), [Dataset_Execution](table/Dataset_Execution.md), [Dataset_File](table/Dataset_File.md), [Workflow_Workflow_Type](table/Workflow_Workflow_Type.md), [Execution_Execution](table/Execution_Execution.md), [Execution_Metadata_Asset_Type](table/Execution_Metadata_Asset_Type.md), [Execution_Metadata_Execution](table/Execution_Metadata_Execution.md), [Execution_Asset_Asset_Type](table/Execution_Asset_Asset_Type.md), [Execution_Asset_Execution](table/Execution_Asset_Execution.md), [File_Asset_Type](table/File_Asset_Type.md), [File_Execution](table/File_Execution.md)

**Asset** — [Execution_Metadata](table/Execution_Metadata.md), [Execution_Asset](table/Execution_Asset.md), [File](table/File.md)

**Satellite** — [Directory_Dataset](table/Directory_Dataset.md)

## Runtime-created patterns

- [Asset table shape](pattern/asset-table.md) — `create_asset` mints domain asset tables.
- [Feature table shape](pattern/feature-table.md) — `create_feature` mints `Execution_{Target}_{Feature}` tables.

## Foreign-key graph (shape)

- `Execution` → `Workflow` (every execution runs a workflow); `Execution.Status` → `Execution_Status`.
- `Dataset.Version` → `Dataset_Version` (current version); `Dataset_Version.Dataset` → `Dataset` (each version belongs to one dataset).
- **Output-dataset provenance:** `Dataset_Version.Execution` → `Execution` (the run that produced the version).
- **Input-dataset edge:** `Dataset_Execution` links `Dataset` ↔ `Execution` (consumed), optionally pinning `Dataset_Version`.
- **Asset provenance:** each `{Asset}_Execution` association (`Execution_Metadata_Execution`, `Execution_Asset_Execution`, `File_Execution`) links the asset ↔ `Execution` with an `Asset_Role` (Input/Output).
- **Tagging:** `Dataset_Dataset_Type`, `Workflow_Workflow_Type`, and each `{Asset}_Asset_Type` link an entity to its vocabulary terms.
- **Self-nesting:** `Dataset_Dataset` (parent ↔ nested dataset), `Execution_Execution` (parent ↔ nested execution).

## Five abstractions → backing tables

| Abstraction | Backing tables |
|---|---|
| **Dataset** | `Dataset`, `Dataset_Version`, `Dataset_Type`/`Dataset_Dataset_Type`, `Dataset_Dataset`, `Dataset_Execution`, `Dataset_File`, `Directory_Dataset` |
| **Workflow** | `Workflow`, `Workflow_Type`/`Workflow_Workflow_Type` |
| **Execution** | `Execution`, `Execution_Status`, `Execution_Execution` |
| **Feature** | runtime `Execution_{Target}_{Feature}` tables + the `Feature_Name` registry (see the pattern) |
| **Asset** | built-in `Execution_Metadata`, `Execution_Asset`, `File` + their `*_Asset_Type`/`*_Execution` associations; domain asset tables via `create_asset` (see the pattern) |
```

- [ ] **Step 2: Verify the index parses, declares OKF + version, and every link target exists.**

Run:
```bash
f="skills/deriva-ml-context/references/concepts/index.md"
awk '/^---$/{c++;next} c==1' "$f" | python3 -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['type']=='Index'; print('index type OK')"
grep -q "Open Knowledge Format" "$f" && grep -q "v1.53.0" "$f" && echo "OKF + version decl OK"
# every link target in the index resolves from concepts/
cd skills/deriva-ml-context/references/concepts
miss=0; for l in $(grep -oE '\((table/[A-Za-z_]+\.md|pattern/[a-z-]+\.md)\)' index.md | tr -d '()'); do [ -f "$l" ] || { echo "  MISSING $l"; miss=1; }; done
[ $miss -eq 0 ] && echo "all index links resolve"
```
Expected: index type OK, OKF+version OK, all index links resolve.

- [ ] **Step 3: Commit.**

```bash
git add skills/deriva-ml-context/references/concepts/index.md
git commit -m "feat(deriva-ml-context): OKF schema bundle index (FK graph + abstraction mapping)"
```

---

### Task 7: Bundle conformance sweep (all sibling FK links resolve)

**Files:**
- Audit only (read-only); fix any dangling link found in `table/`.

**Interfaces:**
- Consumes: the complete bundle from Tasks 1–6.

- [ ] **Step 1: Verify every relative-sibling FK link in every table doc resolves to a sibling file.**

Run:
```bash
cd skills/deriva-ml-context/references/concepts/table
miss=0
for f in *.md; do
  for l in $(grep -oE '\]\([A-Za-z_]+\.md\)' "$f" | sed -E 's/\]\(|\)//g' | sort -u); do
    [ -f "$l" ] || { echo "  DANGLING in $f → $l"; miss=1; }
  done
done
[ $miss -eq 0 ] && echo "ALL sibling FK links resolve" || echo "DANGLING LINKS FOUND"
echo "table docs: $(ls *.md | wc -l | tr -d ' ') (want 26)"
```
Expected: ALL sibling FK links resolve; 26 docs.

- [ ] **Step 2: Verify the 26 table names exactly match the Global Constraints inventory (no missing, no extra).**

Run:
```bash
cd skills/deriva-ml-context/references/concepts/table
ls *.md | sed 's/.md$//' | sort > /tmp/got.txt
cat > /tmp/want.txt <<'NAMES'
Asset_Role
Asset_Type
Dataset
Dataset_Dataset
Dataset_Dataset_Type
Dataset_Execution
Dataset_File
Dataset_Type
Dataset_Version
Directory_Dataset
Execution
Execution_Asset
Execution_Asset_Asset_Type
Execution_Asset_Execution
Execution_Execution
Execution_Metadata
Execution_Metadata_Asset_Type
Execution_Metadata_Execution
Execution_Status
Feature_Name
File
File_Asset_Type
File_Execution
Workflow
Workflow_Type
Workflow_Workflow_Type
NAMES
sort /tmp/want.txt -o /tmp/want.txt
diff /tmp/got.txt /tmp/want.txt && echo "TABLE SET MATCHES (26)" || echo "TABLE SET MISMATCH"
```
Expected: TABLE SET MATCHES (26).

- [ ] **Step 3: If Steps 1–2 found issues, fix the offending table doc(s) and re-run. Commit any fixes.**

```bash
git add skills/deriva-ml-context/references/concepts/table/
git commit -m "fix(deriva-ml-context): resolve dangling FK link in schema bundle (sweep)"
```
(Skip the commit if the sweep was clean.)

---

### Task 8: `deriva-ml-context` SKILL.md — two-schema subsection + pointer

**Files:**
- Modify: `skills/deriva-ml-context/SKILL.md`

**Interfaces:**
- Consumes: the bundle index path `references/concepts/index.md`.

- [ ] **Step 1: Find the insertion point** — after the "## The five core abstractions" section (and its subsections), before "## The rule: inheritance with override". Read those lines first.

Run: `grep -n "^## The five core abstractions\|^## The rule: inheritance with override\|^### Carry structure" skills/deriva-ml-context/SKILL.md`

- [ ] **Step 2: Insert the subsection** after the five-abstractions material (adapt the exact heading level/placement to read coherently):

```markdown
## Two schemas: `deriva-ml` vs your domain schema

A deriva-ml catalog has two kinds of schema, and knowing which is which prevents
most confusion about where a table lives:

- **The `deriva-ml` schema** — 26 fixed tables that back the five abstractions
  (Dataset/Workflow/Execution + the asset and vocabulary machinery).
  Library-managed: you extend it only through the `deriva_ml_*` surface and
  through `add_term` on its built-in vocabularies — never by hand-editing these
  tables.
- **Your domain schema** — your project's own tables (`Subject`, `Image`,
  `Specimen`, …), named after the project, created per-project. The asset tables
  and feature tables you create at runtime (`create_asset`, `create_feature`)
  land in the domain schema, not in `deriva-ml`.

For the concrete table-by-table reference — every `deriva-ml` table, its foreign
keys, the FK graph, and the five-abstractions → backing-tables mapping — see the
OKF schema bundle at `references/concepts/index.md`. (For a live visual of a
specific catalog, use `/deriva-ml:browse-erd`.)
```

- [ ] **Step 3: Verify frontmatter byte-identical + the pointer + the two-schema framing present.**

Run:
```bash
git diff skills/deriva-ml-context/SKILL.md | grep -E "^[-+](name:|description:)" | grep -vE "^[-+][-+]" | wc -l
grep -c "references/concepts/index.md" skills/deriva-ml-context/SKILL.md
grep -c "Two schemas\|domain schema" skills/deriva-ml-context/SKILL.md
```
Expected: frontmatter diff = 0; pointer ≥ 1; two-schema framing ≥ 1.

- [ ] **Step 4: Commit.**

```bash
git add skills/deriva-ml-context/SKILL.md
git commit -m "docs(deriva-ml-context): teach domain-schema vs deriva-ml-schema + point at the OKF schema bundle"
```

---

### Task 9: Fix the stale feature-table name in `create-feature`

**Files:**
- Modify: `skills/create-feature/references/concepts.md` (line ~462), `skills/create-feature/references/workflow.md` (lines ~55, ~162, ~169, ~176)

**Interfaces:**
- None (standalone fix). The correct name is `Execution_{TargetTable}_{FeatureName}`; the worked example `Image` + `Tumor_Classification` → `Execution_Image_Tumor_Classification`.

- [ ] **Step 1: Find every stale reference.**

Run: `grep -rn "Feature_Value" skills/create-feature/`
Expected: the 5 spots (concepts.md ×1, workflow.md ×4).

- [ ] **Step 2: Fix `concepts.md`** — the naming sentence. Read it, then replace the stale pattern + example. New text:

> When you create a feature, DerivaML creates an association table to store feature values. The table name follows the pattern `Execution_{TargetTable}_{FeatureName}` — for example, creating a feature named `"Tumor_Classification"` on the `Image` table creates an `Execution_Image_Tumor_Classification` table.

- [ ] **Step 3: Fix `workflow.md`** — all four spots: the "This creates … a `{FeatureName}_Feature_Value` association table" sentence → `Execution_{TargetTable}_{FeatureName}`; and the three `table="Tumor_Classification_Feature_Value"` / `path="<schema>:Tumor_Classification_Feature_Value/..."` occurrences → `Execution_Image_Tumor_Classification`. Read each line first, replace exactly.

- [ ] **Step 4: Verify the stale name is gone from create-feature and the correct form is present.**

Run:
```bash
grep -rn "Feature_Value" skills/create-feature/ && echo "STILL STALE" || echo "no stale Feature_Value in create-feature"
grep -rc "Execution_Image_Tumor_Classification\|Execution_{TargetTable}_{FeatureName}" skills/create-feature/references/concepts.md skills/create-feature/references/workflow.md
```
Expected: "no stale Feature_Value in create-feature"; correct form present in both files.

- [ ] **Step 5: Confirm use-annotation-builders was NOT touched** (the illustrative annotation FK example is deliberately out of scope).

Run: `git diff --name-only | grep use-annotation-builders && echo "ERROR: touched out-of-scope file" || echo "use-annotation-builders untouched (correct)"`
Expected: untouched.

- [ ] **Step 6: Commit.**

```bash
git add skills/create-feature/references/
git commit -m "fix(create-feature): correct stale feature-table name {FeatureName}_Feature_Value -> Execution_{Target}_{Feature}"
```

---

## Self-Review

**1. Spec coverage:**
- OKF bundle at concepts/ with index + table/ + pattern/ → Tasks 1–6. ✓
- 26 fixed tables, one type:Table doc each, grouped by kind → Tasks 1–4 (8+6+9+3 = 26). ✓
- FKs as relative-sibling links, both sides for associations, no-FK stated → Tasks 1–4 doc shape + Task 7 sweep. ✓
- Vocabulary docs list seeded terms → Tasks 1 (Dataset_Type), 2 (Workflow_Type, Execution_Status), 4 (Asset_Type, Asset_Role, Feature_Name). ✓
- Execution_Status names values + points at execution-lifecycle → Task 2. ✓
- Two pattern docs pointing at work-with-assets / create-feature, not restating → Task 5. ✓
- index.md: OKF decl + v1.53.0 pin + tables by kind + patterns + FK graph + abstraction mapping → Task 6. ✓
- deriva-ml-context two-schema subsection + pointer, frontmatter byte-identical → Task 8. ✓
- create-feature stale-name fix (5 spots), use-annotation-builders untouched → Task 9. ✓
- Relative sibling link form throughout → Tasks 1–4 + Task 7 sweep. ✓
- Pinned v1.53.0, source-derived (read create_schema.py) → Global Constraints + each cluster task Step 1. ✓
- Cross-repo _CONCEPTS_GUIDE mirror: additive, no re-sync (no task touches it — correctly absent). ✓

**2. Placeholder scan:** The `<T>`/`<Table>`/`{Name}`/`{TargetTable}` are naming conventions (literal template content in the docs), not plan placeholders. Each cluster task gives the source functions to read AND the per-table FK/column facts to write (from the inventory in the spec), so no "fill in details" — but every cluster task's Step 1 mandates reading create_schema.py to confirm against source, because the FK/column detail must be source-accurate, not transcribed. That is a verification directive, not a placeholder.

**3. Type consistency:** `type: Table` + `kind:` used uniformly Tasks 1–4; `type: Pattern` Task 5; `type: Index` Task 6. FK links are `[RefTable](RefTable.md)` (sibling) in table/ docs and `[RefTable](../table/RefTable.md)` in pattern/ docs (correct relative depth — patterns are one level down in pattern/). The 26-name set in Task 7's `/tmp/want.txt` matches the Global Constraints list exactly (cross-checked: 4 core + 6 vocab + 12 association + 3 asset + 1 satellite = 26). Feature-table name is `Execution_{TargetTable}_{FeatureName}` consistently in Task 5 and Task 9.
