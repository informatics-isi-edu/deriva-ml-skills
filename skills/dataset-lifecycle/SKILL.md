---
name: dataset-lifecycle
description: "Creates, populates, splits, subsamples, validates, versions, browses, downloads, and deletes DerivaML datasets, and is the front door for loading or ingesting a new dataset (routes raw files on disk to the user-run setup-ml-catalog phased loader). Use for any DerivaML dataset operation, and after any operation that yields a dataset RID + version, to offer wiring it into src/configs/datasets.py."
when_to_use: "Triggers on: 'load / ingest / import a dataset', 'add a dataset to the catalog', 'create / split / stratify / subsample / browse / download / delete a dataset', 'smaller variant', 'stratified subset', 'curated subset', 'filter by class / by feature', 'held-out test set', 'split by patient', 'freeze the data', 'partition by element vs row', 'Split_Partition', 'Dataset_Type', 'dataset version', 'release a dataset', 'parent/child datasets', 'BDBag', 'training data setup'. Not for: editing configs/ by hand, including pointing an experiment at a dataset version (write-hydra-config), features/labels (create-feature), tables (/deriva:create-table, user-run), running experiments (execution-lifecycle), single assets (work-with-assets), vocabularies (/deriva:manage-vocabulary, user-run), clearing locally cached bags (manage-deriva-storage), or turning a bag into training DataFrames / framework layouts (ml-data-engineering)."
---

# Dataset Lifecycle

A DerivaML dataset is a versioned collection of catalog records (its members).
This skill takes one from design to use: design → assess → plan → create →
validate → version → use. Every MCP tool below takes `hostname=` and
`catalog_id=` explicitly.

## "Load a new dataset" — route first

"Load a dataset" means two different things; pick the path before doing anything:

| Where is the data now? | What "load" means | Go to |
|---|---|---|
| **Raw files on disk** (a directory, CSVs, an image folder — not yet in the catalog) | Register the source files, upload them as typed assets, then group them into a Dataset. | The **phased loader** in `/deriva-ml:setup-ml-catalog` † (`scripts/loader_orchestrator_template.py`, `--phase {schema,register,upload}`). It hands back here to organize the uploaded assets into Datasets. |
| **Already in the catalog** (records exist; you want to group them) | Create a Dataset and add the existing members — no upload. | Stay here: Assess → Create below. |

If unsure, ask. A fresh data drop is almost always the raw-files path; curating a
training subset from existing records is the in-catalog path.

**Use the project's catalog.** Find the hostname and catalog ID in
`src/configs/deriva.py`, `tacit-knowledge.md`, or the project's `CLAUDE.md`. When a
project works on a clone, use the clone, not the catalog it was cloned from. If none
of these says, ask the user.

## Phase 1: Design

Before building, capture what the dataset is *for* and how you'll know it's
correct: `/deriva-ml:design-experiment` writes `docs/design/dataset/<slug>.md`
(purpose, requirements, structure plan, `Dataset_Type` tags, validation criteria,
consumers). Get it to **Approved** before creating anything. A plain reuse needs
only a few lines; a new split, subsample, or curated subset needs a full doc,
because its leakage and balance criteria are what get skipped otherwise.

## Phase 2: Assess

Reuse beats re-creation. `/deriva:semantic-awareness` *(deriva-skills, auto-fires)*
carries the search-before-create discipline, including synonym and spelling
variants.

1. **Search existing datasets.** `rag_search("your purpose", doc_type="ml-dataset")`
   finds datasets by description, type, or purpose. For a snapshot of every dataset,
   read `deriva://catalog/{h}/{c}/deriva-ml/datasets`; for filtered or paginated
   listing, `deriva_ml_list_datasets`.
2. **Check element types.** `deriva_ml_list_dataset_element_types(hostname,
   catalog_id)` lists the tables that can contribute members. Register a missing one
   with `deriva_ml_add_dataset_element_type(hostname, catalog_id, table_name=...)`.
3. **Decide:**

| Situation | Action |
|---|---|
| An existing dataset covers the need | Reuse it: pin its RID + released version in config |
| It needs more members | A few known RIDs: `deriva_ml_add_dataset_members`. Many, or chosen by a query: a script calling `dataset.add_dataset_members(...)` in an execution. Then release. **Never add to a split partition** (`Split_Partition`): it breaks the split's balance and leakage guarantees — add to the source and split again |
| A different train/test split | Script calling `split_dataset(ml, source_rid, exe, ...)` |
| A smaller variant for fast iteration | Script calling `subsample(ml, source_rid, exe, size=, ...)` |
| A subset filtered by data values | Curated subset (`references/curated-subsets.md`) |
| Nothing to start from | Bootstrap from table data (`references/workflow.md` → "Bootstrap dataset") |

## Phase 3: Plan

### Structure

| Pattern | When | How |
|---|---|---|
| Standalone | A new collection | `deriva_ml_create_dataset` |
| Split | Train/val/test partitions | `split_dataset` in a script; children auto-tagged with their role + `Split_Partition` |
| Subsample | One smaller stratified variant | `subsample` in a script; output auto-tagged `Subsample` |
| Curated subset | Filtered by data values | Template — `references/curated-subsets.md` |
| Nesting | Grouping related datasets | `deriva_ml_add_dataset_members(parent_rid, members={"Dataset": [child_rid]})` |

**Split by subject when records share one.** If a patient has several images,
`split_dataset` must assign whole patients, or the test set leaks into training:
`references/structure-and-splits.md` → "Splitting by subject".

**Render splits in the catalog**, as child datasets — never recompute them per run.
A different seed gives a different split, and nothing records which records went
where (`references/workflow.md` → "Why render splits explicitly").

### Types

`Dataset_Type` tags describe three independent axes; give a dataset at least one tag
on each axis that applies, and compose them rather than compounding
(`Training` + `Labeled` + `Fundus`, never `TrainingLabeled`):

- **Role** — `Training`, `Testing`, `Validation`, `Complete`, `Split`: what it is for.
  Never inherited; `split_dataset` assigns each partition's role from its position.
- **Content** — `Labeled`, `Unlabeled`, plus domain tags (`Fundus`, `OCT`): what the
  data is. Propagate explicitly with `training_types=` / `dataset_types=`.
- **Origin** — `Split`, `Split_Partition`, `Subsample`: how it came to exist. Always
  set by the producing operation.

Types are the catalog's record of what a dataset is for: consumers dispatch on them,
never on the name or the description. If a type is wrong or missing, fix it with
`deriva_ml_update_dataset(dataset_types=[...])` rather than working around it.
Full rules, custom types, and examples: `references/dataset-types.md`.

## Phase 4: Create

**Default to a committed script** for anything beyond a handful of members, so the
execution record links the dataset to the code that built it. The MCP tools are for
trivial cases (an empty dataset, two or three known RIDs).

| Situation | Path |
|---|---|
| No source dataset (bootstrap) | Script from `generate-scripts` patterns — `references/workflow.md` → "Bootstrap dataset" |
| Filter or subset an existing dataset | `scripts/generate_subset_template.py` — `references/curated-subsets.md` |
| Partition an existing dataset | `split_dataset` — `references/workflow.md` → "Splitting Datasets" |
| Smaller stratified variant | `subsample` — `references/workflow.md` → "Subsampling Datasets" |
| Trivial case | MCP tools — `references/workflow.md` → "Quick-edit MCP path" |

Every dataset needs a description of its composition, purpose, and key
characteristics ("500 CIFAR-10 images, 50 per class, for rapid iteration" — not
"Training data"); for splits, say the strategy and why. Templates:
`/deriva-ml:generate-descriptions`.

## Phase 5: Validate

Before releasing a new dataset or wiring it into a config, check it against the
validation criteria in its design doc:

- **Balance** — counts per class within the stated tolerance.
- **No leakage** — partition member RIDs are disjoint by construction; check that
  the *subjects* behind them are too (`references/structure-and-splits.md` →
  "Checking for leakage").
- **Bag parity** — a downloaded bag's member RIDs match the catalog's
  (`references/bags.md` → "Download recipe", step 4).
- **Counts** — total members match the target.

Then set the design doc's Status → **Validated**. Released does not mean validated:
nothing stops a release that skipped these checks.

## Phase 6: Version

Datasets carry a two-state PEP 440 version:

- **Released** (`0.4.0`) — a frozen catalog snapshot: citable and reproducible.
- **Dev** (`0.4.0.post1.dev3`) — the mutable state since the last release, with no
  snapshot.

Rules:

1. **Mutations land on dev.** Adding or removing members, or changing types, moves
   the dataset to a dev label (`.dev1`, then `.devN`). A new dataset starts at a
   released `0.1.0`, so adding its members puts it on dev. The outputs of
   `split_dataset` and `subsample` therefore end on dev too, while their source is
   untouched: **release each output before pinning it.**
2. **Only `deriva_ml_release_dataset(..., bump=major|minor|patch, description=...)`
   produces a released version.** Its description becomes the release notes. Bump
   major when the schema under the dataset changed (the user runs `/deriva:evolve-schema` †
   for the migration), minor for new members or annotations, patch for corrections.
3. **New feature values on existing members don't flip the version.** The bag would
   still change, so call `dataset.mark_dev(description)` (Python) after writing
   them, then release.
4. **Execution outputs don't flip it either.** Weights, predictions, and logs link to
   the execution, not to the dataset's members.
5. **Experiments pin released versions only** — `DatasetSpecConfig(rid="28EA",
   version="0.4.0")`, never a dev label or "current".

Python-only drift checks: `dataset.is_dirty()`, `dataset.release_diff()`,
`dataset.compare_versions(v_a, v_b)`. Version history, the lifecycle diagram, and
common mistakes: `references/versioning.md`.

### Offer to wire it into the config

Whenever this skill releases a version a run may consume — a new dataset, a split's
partitions, a subsample — **offer to add or bump its `DatasetSpecConfig` entry in
`src/configs/datasets.py`**, and commit that file before the run that uses it:

> "Released Training `2-TRN1` @ `0.2.0` and Testing `2-TST1` @ `0.2.0`.
> Add them to `src/configs/datasets.py`?"

This skill owns the offer; `/deriva-ml:write-hydra-config` ("Wiring fresh RIDs into
config files") owns the entry format and commit message.

## Phase 7: Use

- **Browse** — the dataset resource `deriva://catalog/{h}/{c}/deriva-ml/dataset/{rid}`
  returns its members, version, and a `cite_url` that opens it in Chaise. Without a
  browser: `references/workflow.md` → "Explore and browse dataset contents".
- **Download** — preview, pin a released version, download, validate:
  `references/bags.md` → "Download recipe". A current dev version also downloads,
  but it returns the live catalog state, so two downloads can differ; release before
  downloading anything you'll train on or cite.
  The download is Python run on the machine that needs the data (a GPU box, a
  laptop); the MCP server can't write to that machine's disk. Set `cache_dir` on
  `DerivaML(...)` there to choose where bags land.
- **Turn the bag into training data** — DataFrames, `restructure_assets` for
  ImageFolder, denormalizing across FK paths, choosing among annotators:
  `/deriva-ml:ml-data-engineering`.
- **Missing data in a bag** — usually a release cut before the data was added, or a
  table the export doesn't reach: `references/bags.md` → "How Bag Contents Are
  Determined". For a full diagnosis the user runs `/deriva-ml:debug-bag-contents` †.

## Delete

`deriva_ml_delete_dataset(hostname, catalog_id, dataset_rid, recurse=False)` is a
soft delete: it sets the dataset's `Deleted` flag, so it drops out of normal
listings while its members, versions, and links stay in the catalog.
`recurse=True` also deletes nested children; a dataset nested inside a parent
can't be deleted until it is removed from that parent. A config or a past execution may still
pin the dataset, so the user runs `/deriva-ml:schema-evolution-impact` † first;
until they do, list what references it before deleting. Clearing *downloaded* copies
is local cleanup — `/deriva-ml:manage-deriva-storage`.

## References

- `references/workflow.md` — step-by-step procedures: bootstrap, quick MCP edits,
  splitting, subsampling, exploring, deleting, a complete example.
- `references/dataset-types.md` — what a dataset is, the `Dataset_Type` axes, custom
  types, composition, examples, element types.
- `references/structure-and-splits.md` — nesting, `split_dataset`, `subsample`.
- `references/curated-subsets.md` — filtered subsets from the template.
- `references/versioning.md` — the dev/release model in full.
- `references/bags.md` — bag contents, the download recipe, caching, timeouts.
- `references/navigation.md` — discovering and navigating datasets.
- `references/lifecycle-ops.md` — every operation as MCP tool vs Python API.
- `scripts/generate_subset_template.py`, `scripts/subset_filters.py` — curated-subset
  templates; copy to the project's `src/scripts/`.
- The deriva-ml user guide: `rag_search("...", doc_type="ml-docs")`
  (`user-guide/datasets.md`).

† = only the user can run it; suggest the command.
