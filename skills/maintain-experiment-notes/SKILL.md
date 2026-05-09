---
name: maintain-experiment-notes
description: "Use when reading or writing the project's experiment-decisions.md tacit-knowledge log. WRITE triggers: an action a future team member would need to understand has just occurred — running an execution, creating or splitting a dataset, creating a feature or vocabulary, adding a vocabulary term, changing catalog structure (tables/columns/FKs), choosing hyperparameters, writing or modifying a hydra-zen config, loading data into a catalog, bumping versions, creating or cloning a catalog, or resolving a problem with a non-obvious fix. Use in the SAME response as the action. READ triggers: the user is asking why something was done, whether something has been tried before, what was learned from a prior run, where the rationale for a configuration came from, or any other 'why' / 'have we tried' / 'what did we learn' question about this project's models or data. Skip only for routine read-only operations (queries, listing, browsing) that touch neither side."
user-invocable: false
---

# Capture and Consult Experiment Design Decisions

`experiment-decisions.md` (project root) is the project's accumulating record of **tacit knowledge** about its models and data — the intent and reasoning that the catalog cannot store. The catalog is the source of truth for *what* exists (RIDs, configs, numbers, lineage). This file is the source of truth for *why*. Entries connect: a follow-up run often references prior runs by RID, so the file reads top-to-bottom as the project's history of how its understanding evolved.

## When to write

If you have just made or recorded a decision the file would document, append an entry. Append silently — don't ask permission, don't announce. The bar is **intent**, not "alternatives were weighed": first runs, baselines, and pipeline-validation runs all qualify even when the choice felt obvious. Skip routine read-only operations (querying, listing, browsing schemas) — they leave no entry.

## When to read

If the user is asking a question the file would answer — *why* did we choose X, *was there a reason* for Y, *have we tried* Z, *what did we learn* from a prior run, where does the rationale for this configuration live — consult `experiment-decisions.md` *before* answering from configs, current catalog state, or general reasoning.

**If the file is silent on the question, say so explicitly. Do not invent a rationale to fill the gap.** Frame any reconstruction from current state as exactly that — a reconstruction, not a recalled decision — so the user can choose whether to treat it as authoritative or look further. When the file does have an entry, cite it (entity RID + entry title) so the user can verify and follow back-references.

## What an entry contains

Each entry is a short markdown block describing one decision or run, anchored on the RID of the entity it's about. Entries answer questions like *why* a dataset / feature / split / config was chosen, *what* the goal of a run was, *how* the project arrived at the current configuration, and *where* a non-obvious decision came from.

Every entry should answer:

1. **What was run or decided** — the action.
2. **Hypothesis or question** the entry was meant to answer. For non-run events (feature creation, schema change, vocabulary addition, dataset construction) this is the *use case the change exists to serve* — what does this enable, what was missing before — rather than a literal hypothesis.
3. **Reasoning** — what led to this configuration, in plain language a domain scientist can follow. The catalog has the precise numbers.
4. **Immediate observations** *when applicable* — cheap-to-record facts that would be awkward to retrieve later (wall-clock time, headline metric the run printed, anomalies). For schema and feature changes there usually are no observations at write-time; skip part 4 rather than padding it.

**Conclusions are optional and can be deferred.** At write-time you usually have a hypothesis and reasoning, not a settled "what this means." Don't fabricate. Conclusions show up later in whichever entry the reasoning crystallizes in — sometimes the very next run, sometimes much later. A single prior run can spawn multiple follow-ups exploring different angles. Refer back by execution RID so a reader can navigate the chain in either direction.

## Conventions

- **Heading level is `###`.** Each entry is a sibling under the file's top-level `# Experiment Design Decisions` heading.
- **Append new entries at the bottom.** The file reads top-to-bottom as the project's history; chronology is the structure.
- **No dates in titles.** The entity RID carries its creation timestamp in the catalog; a date in the entry duplicates that and rots when the entry is later edited.
- **Title includes the durable handle in parentheses** — the navigation anchor for what the entry refers to. Pick the RID a reader would use to find related artifacts:
   - Model run → **execution RID** (`### ... (execution 8KG)`)
   - Feature creation → **feature RID** (`### ... (feature 9PQ4)`)
   - Vocabulary addition (terms only) → **vocabulary RID** (`### ... (vocabulary 9PR0)`)
   - Dataset creation or split → **dataset RID with version** (`### ... (dataset 7KE v0.4.0)`)
   - Schema change → **table RID** (`### ... (table 5-AB12)`)

  Describing the *kinds* of supporting artifacts ("three terms were created"; "model weights, training log, prediction CSV are linked to the execution") is fine and helpful. Do **not** enumerate every individual supporting RID — they go stale, and the catalog already has them linked to the title's handle.
- **When alternatives were weighed**, state what was rejected and why. When the entry is characterizing intent rather than picking between alternatives, skip the rejection clause.
- **Reference RIDs** for catalog entities; include quantitative evidence (counts, sizes) when known.
- **Length is set by content.** Long enough to answer 1–4 above; short enough to scan in one pass (~5–12 lines in practice).
- Past tense — these are settled records, not plans.

## Examples

A model run:

```markdown
### First end-to-end CIFAR-10 run on localhost catalog 1407 (execution 8KG)

Hypothesis: the cifar10_e2e schema, dataset 7KE, and the deriva-ml-run
pipeline wired together cleanly against a freshly-seeded localhost
catalog. Ran cifar10_quick (small image classifier, fewest training
passes, smallest network) because the question was "does the plumbing
work," not "does the model perform." Picked the labeled split as input
because it was the smallest dataset with ground-truth labels on both
partitions (80 train, 20 test), so a real test number was reachable
at this scale. Run finished in ~30s on CPU; held-out accuracy 20% on
20 images vs a 10% guess-one-of-ten baseline — a learning signal but
within noise at this sample size. Outputs linked to execution 8KG.
```

A non-run event (no part-4 observations because nothing to observe at write-time):

```markdown
### QC status feature added to Image table (feature 9PQ4)

Created `QC_Status` on `Image` (table 5-AB12, ~3,200 rows) backed by a
new `Image_QC_Status` vocabulary (9PR0) in the `histopath` schema —
three terms (pass, blurry, tissue_fold) plus a confidence_score column.
Use case: blurry slides have been silently degrading downstream model
accuracy with no first-class way to mark them. Kept QC concerns separate
from diagnostic concerns rather than extending Image_Annotation with a
"blurry" diagnosis term: the two review workflows have different
reviewers, criteria, and consumers, so collapsing them would entangle
the queues. Values not populated yet — annotator workflow is the next
step.
```

## Commit prompting

After 3+ entries in a session — or at a natural pause — suggest committing `experiment-decisions.md` on its own with a message like "Record experiment design decisions." Don't bundle with unrelated changes; don't prompt after every entry.

## File mechanics

`experiment-decisions.md` lives in the project root and must be tracked in git. See `references/file-mechanics.md` for the gitignore check and first-time-setup details.
