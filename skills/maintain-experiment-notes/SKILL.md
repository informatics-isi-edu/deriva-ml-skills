---
name: maintain-experiment-notes
description: "Use when an action a future team member would need to understand has just occurred — running an execution, creating or splitting a dataset, creating a feature or vocabulary, adding a vocabulary term, changing catalog structure (tables/columns/FKs), choosing hyperparameters, writing or modifying a hydra-zen config, loading data into a catalog, bumping versions, creating or cloning a catalog, or resolving a problem with a non-obvious fix. Use in the SAME response as the action, not later. Skip for routine read-only operations (queries, listing, browsing) that produce no durable artifact and require no judgment."
user-invocable: false
---

# Capture Experiment Design Decisions

`experiment-decisions.md` (project root) is the project's accumulating record of **tacit knowledge** about its models and data — the intent and reasoning that the catalog cannot store. The catalog is the source of truth for *what* exists (RIDs, configs, numbers, lineage). This file is the source of truth for *why*.

Each entry stands alone as a record of one decision or run; together, the entries let a new team member reconstruct how the project's understanding of its data and models evolved. Append silently — don't ask permission, don't announce.

## When to write

Write whenever a future team member — possibly a domain scientist who didn't write this code — would need the entry to understand the project's models or data. The bar is **intent**, not "alternatives were weighed." First runs against a new catalog, baseline numbers, pipeline-validation runs, and characterizations of "what does this mean" all qualify even when the choice felt obvious.

Do not write for routine read-only operations (querying, listing, browsing schemas).

## What goes in an entry

Every entry should answer:

1. **What was run or decided** — the action.
2. **Hypothesis or question** the entry was meant to answer. For non-run events (feature creation, schema change, vocabulary addition, dataset construction) this is the *use case the change exists to serve* — what does this enable, what was missing before — rather than a literal hypothesis.
3. **Reasoning** — what led to this configuration (in plain language a domain scientist can follow; the catalog has the precise numbers).
4. **Immediate observations** *when applicable* — cheap-to-record facts that would be awkward to retrieve later. For runs: wall-clock time, the headline metric the run printed, anomalies (warning, slow epoch, retry). For schema and feature changes there usually are no observations at write-time; skip part 4 rather than padding it with status notes.

**Conclusions are optional and can be deferred.** At write-time you usually have a hypothesis and reasoning, not a settled "what this means." Don't fabricate. Conclusions show up later in whichever entry the reasoning crystallizes in — sometimes the very next run, sometimes much later, and a single prior run can spawn multiple follow-ups exploring different angles. Refer back by execution RID so a reader can navigate the chain in either direction.

## Conventions

- **Heading level is `###`.** Each entry is a sibling of the others under the file's top-level `# Experiment Design Decisions` heading.
- **Append new entries at the bottom of the file.** The file reads top-to-bottom as the project's history; chronology is the structure.
- **Don't put dates in the title.** The execution RID (or other entity RID) carries its creation timestamp in the catalog. Adding a date in the entry duplicates that and rots if the entry is later edited.
- **Title includes the durable handle in parentheses** — the navigation anchor for everything the entry refers to. Pick the RID a reader would use to find related artifacts in the catalog:
   - Model run → **execution RID** (`### ... (execution 8KG)`); outputs, inputs, and the workflow's git hash all hang off it.
   - Feature creation → **feature RID** (`### ... (feature 9PQ4)`); vocabulary, target table, and feature values reach back through it.
   - Vocabulary addition (terms only, no new feature) → **vocabulary RID** (`### ... (vocabulary 9PR0)`).
   - Dataset creation or split → **dataset RID with version** (`### ... (dataset 7KE v0.4.0)`).
   - Schema change (table/column/FK) → **table RID** (`### ... (table 5-AB12)`).

  Describing the *kinds* of supporting RIDs ("three terms were created in this vocabulary"; "model weights, training log, prediction CSV are linked to the execution") is fine and helpful for a reader scanning the entry. Do **not** enumerate every individual supporting RID (`8N4`, `8N6`, `8N8`, `9PT2`, `9PT4`, `9PT6` etc.) — they go stale, and the catalog already has them linked to the handle in the title.
- **When alternatives were weighed**, state what was rejected and why ("chose X over Y because Z"). When the entry is characterizing intent rather than picking between alternatives, skip the rejection clause.
- **Reference RIDs** for catalog entities; include quantitative evidence (counts, sizes) when known.
- **Length is set by content, not lines.** Long enough to answer 1–4 above; short enough to scan in one pass. In practice ~5–12 lines.
- Past tense — these are settled records, not plans.

## Example entry

```markdown
### First end-to-end CIFAR-10 run on localhost catalog 1407 (execution 8KG)

Hypothesis: the cifar10_e2e schema, dataset 7KE, and the deriva-ml-run
pipeline all wired together cleanly against a freshly-seeded localhost
catalog. Ran the cifar10_quick preset (a small image classifier with
the fewest training passes and smallest network) because the question
was "does the plumbing work," not "does the model perform." Picked the
labeled split as input because it was the smallest dataset with
ground-truth labels on both partitions (80 training, 20 held-out for
test), so a real test number was reachable even at this scale. Run
completed in ~30s end-to-end on CPU; final held-out accuracy 20% on 20
images, against a 10% baseline if the model were guessing one of CIFAR-10's
ten classes uniformly — a learning signal but well within noise at this
sample size. Outputs were linked to execution 8KG.
```

The catalog tells you the rest: configs, asset RIDs, training log contents, dataset lineage. Reach them via `deriva_ml_get_execution`, `deriva_ml_get_dataset`, `deriva_ml_lookup_asset`.

A non-run example, for contrast — note that there is no "observations" section because there's nothing to observe at write-time:

```markdown
### QC status feature added to Image table (feature 9PQ4)

Created `QC_Status` on `Image` (table 5-AB12, ~3,200 rows) backed by a
new `Image_QC_Status` vocabulary (9PR0) in the `histopath` schema, with
three terms (pass, blurry, tissue_fold) and a confidence_score column.
Use case: blurry slides have been silently degrading downstream model
accuracy and there was no first-class way to mark them — the QC team
needs a way to triage and the modeling pipeline needs a filter. Kept QC
concerns separate from diagnostic concerns rather than extending the
existing Image_Annotation feature with a "blurry" diagnosis term: the
two review workflows have different reviewers, criteria, and consumers,
so collapsing them would have entangled the queues. Three terms cover
the failure modes the QC team currently triages on; more can be added
later. Values not populated yet — annotator workflow is the next step.
```

## Commit prompting

After 3+ entries in a session — or at a natural pause — suggest committing `experiment-decisions.md` on its own with a message like "Record experiment design decisions." Don't bundle with unrelated changes; don't prompt after every entry.

## File mechanics

`experiment-decisions.md` lives in the project root and must be tracked in git. See `references/file-mechanics.md` for the gitignore check and first-time-setup details.
