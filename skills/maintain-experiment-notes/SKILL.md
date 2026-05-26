---
name: maintain-experiment-notes
description: "Use whenever an experiment design decision is being made, proposed, or recalled. Three triggers: (1) WRITE — after any action a future teammate would need to understand (running an execution, creating/splitting a dataset, creating a feature or vocabulary, changing schema, choosing hyperparameters, picking an MCP entry-point when multiple paths existed, resolving a problem with a non-obvious fix). Append a short entry to experiment-decisions.md (project root) in the same response. Fire even when the choice felt obvious. (2) GUIDANCE (forward-looking read) — when the user proposes an action (add a feature, create a vocab term, train a model, change a config, split a dataset, run an experiment) and prior project experience may bear on whether it will work. Consult the file BEFORE executing or recommending. The user will not phrase this as a 'why' question — they'll just propose the action. Fire on the action, not on the phrasing. (3) FORENSIC (backward-looking read) — when the user asks 'why was X chosen', 'have we tried Y', 'what did we learn from Z', any indirect variant ('is this config still right?', 'should we still be using this?'), or is being oriented to the project for the first time. Consult before answering. If the file is silent, say so — do not invent rationale."
user-invocable: false
---

# Capture and Consult Experiment Design Decisions

`experiment-decisions.md` (project root) is the project's accumulating record of **tacit knowledge** about its models and data — the intent and reasoning that the catalog cannot store. The catalog is the source of truth for *what* exists (RIDs, configs, numbers, lineage). This file is the source of truth for *why*. Entries connect: a follow-up run often references prior runs by RID, so the file reads top-to-bottom as the project's history of how its understanding evolved.

**Don't ask this file for catalog-stored facts.** If the question is *what* — what datasets exist, what vocabulary terms are defined, what assets a workflow produced, which version of a dataset is current — fetch the catalog directly (`deriva://catalog/{host}/{cat}/ml/...` resources first; tools next). If the question is *why* — why this dataset was created, why this hyperparameter was chosen, why a previous approach was abandoned — read this file. Entries reference catalog entities by RID and short link, not by inlining their contents.

This file is also the **cross-domain bridge** on multidisciplinary teams. The ML designer writes entries the domain expert needs to *understand* (and vice versa) — not directives for the other discipline to act on. Each entry captures decisions and their rationale in language the other side can read; what the reader chooses to do with that understanding is their decision, in their own time. Neither side writes only for themselves. The entry conventions below name this responsibility explicitly.

## What this file is not

- **Not a TODO list.** Don't write "Analyst should run roc_analysis next" or "we need to release dataset X." Those are workflow directives aimed at a specific person at a specific time; they belong in handoff sections, issue trackers, or a task tool — not here. This file records what *was* decided, not what *should* be done.
- **Not a process or workflow specification.** Don't write step-by-step procedures for a future contributor to follow. Skills, README files, and runbooks own that material. The exception is **recurring-pattern entries** — see Conventions: *"whenever we do X, we also do Y because Z"* is tacit knowledge about a project convention, not a directive. The form is observational ("the pattern in this project is..."), not imperative ("you should...").
- **Not a status board.** Don't write "in progress: training run X." Catalog `Execution_Status` carries that, and it changes; this file's entries don't change once written. If the run finishes, the next entry could reference the *settled outcome*, not a transient state.
- **Not a replacement for the catalog.** See "What doesn't belong here" below — RIDs, versions, vocab contents, schema shape, lineage edges all live in the catalog. This file links to them, doesn't replicate them.

The unifying rule: **entries are past-tense, settled records.** If something might change tomorrow, it doesn't belong here — it belongs in the system that's actually responsible for that state. This file accumulates; it doesn't track.

## When to write

If you have just made or recorded a decision the file would document, append an entry. Append silently — don't ask permission, don't announce. The bar is **intent**, not "alternatives were weighed": first runs, baselines, and pipeline-validation runs all qualify even when the choice felt obvious. Skip routine read-only operations (querying, listing, browsing schemas) — they leave no entry.

## When to read — two distinct modes

### Mode A: Guidance (before you act)

**Before acting on a user request that touches the catalog** — creating a feature, adding a vocab term, changing schema, training with new parameters, splitting a dataset, picking an MCP entry-point — **scan `experiment-decisions.md` for entries about the same entity or the same kind of change**. The user will not phrase this as a "why" question; they'll just propose the action. The skill must fire on the *action*, not on a question keyword.

The bar is low: if the file mentions the entity (by RID) or the change-type ("we tried label smoothing 0.1 on training runs"), surface what it says *before* doing the action. Don't paraphrase — **quote the relevant entry** and let the user decide whether to proceed, adjust, or abandon. The cost of a wasted file-read is seconds; the cost of repeating a documented dead end is hours-to-weeks.

When prior experience contradicts the proposed action, hand the decision back with concrete options rather than blocking — the user may know the original constraints no longer hold.

### Mode B: Forensic (when asked why)

If the user is asking a question the file would answer — *why* did we choose X, *was there a reason* for Y, *have we tried* Z, *what did we learn* from a prior run, *where does the rationale for this configuration live*, or *catch me up on this project* (new collaborator orientation) — consult `experiment-decisions.md` *before* answering from configs, current catalog state, or general reasoning.

### Honesty rule (both modes)

**If the file is silent on the question, say so explicitly. Do not invent a rationale to fill the gap.** Frame any reconstruction from current state as exactly that — a reconstruction, not a recalled decision — so the user can choose whether to treat it as authoritative or look further. When the file does have an entry, cite it (entity RID + entry title) so the user can verify and follow back-references.

## What an entry contains

Each entry is a short markdown block describing one decision or run, anchored on the RID of the entity it's about. Entries answer questions like *why* a dataset / feature / split / config was chosen, *what* the goal of a run was, *how* the project arrived at the current configuration, and *where* a non-obvious decision came from.

Every entry should answer:

1. **What was run or decided** — the action.
2. **Hypothesis or question** the entry was meant to answer. For non-run events (feature creation, schema change, vocabulary addition, dataset construction) this is the *use case the change exists to serve* — what does this enable, what was missing before — rather than a literal hypothesis.
3. **Reasoning** — what led to this configuration, in plain language. **Spell out one term-of-art per entry that a reader from the other discipline wouldn't know** — either inline ("label smoothing 0.1 — softens hard 0/1 targets to discourage overconfidence") or as a parenthetical. The entry's job is to be readable by the discipline you're *not* in. The catalog has the precise numbers.
4. **Immediate observations** *when applicable* — cheap-to-record facts that would be awkward to retrieve later (wall-clock time, headline metric the run printed, anomalies). For schema and feature changes there usually are no observations at write-time; skip part 4 rather than padding it.
5. **Consequences for downstream readers** *when applicable* — factual statements about what this decision means for someone in the *other* discipline, **stated as facts, not as directives**. Past or present tense, never imperative. If an ML run produced something a domain expert should know about, say so factually ("at this accuracy, roughly 8% of slides surface below 0.5 confidence — the queue size the QC team would see if this model were used for triage"). If a schema change affects how ML configs reference the data, say so factually ("after this change, `Subject.age` no longer exists; the equivalent column is `Subject.age_at_intake`"). Skip this part when the change is purely internal to one discipline. The reader decides what to *do* about the consequence; this section's job is to make sure they know.
6. **Weighed alternatives** *when alternatives were genuinely considered* — what else was on the table, and what ruled them out. This is the **comparative-judgment layer**: a future reader needs to see *what was compared*, not just *what was picked*. **Never fabricate this section.** If the reasoning trace doesn't show alternatives, write nothing here, or write `**Weighed alternatives:** *(none captured — choice was [observed] without an articulated comparison)*`. See "Provenance markers" below and "When to inquire" for how to handle uncertain cases.

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

  Describing the *kinds* of supporting artifacts ("three terms were created"; "model weights, training log, prediction CSV are linked to the execution") is fine and helpful. Reference RIDs sparingly, but **always name at least one representative supporting RID** a cross-domain reader can click through to ("the 8KG run that established the 20% baseline"). Don't enumerate every supporting RID — they go stale, and the catalog already has them linked to the title's handle.
- **Dead ends explored.** When alternatives were weighed, state what was rejected and why. Dead ends are the highest-leverage tacit knowledge on a multidisciplinary team — the ML designer doesn't know that "we tried using FFPE stain type as a model input and it didn't work because staining variance dominated the signal" was a year of unproductive work the previous lab burned through. **Standalone dead-end entries are valid** — if you tried something, abandoned it, and there's no successor decision yet, that's still a complete entry. Title it after the dead-end action itself ("### Tried stain_type as model input; abandoned (execution 3-XYZ)").
- **Recurring patterns are also valid.** Entries of the form *"whenever we do X in this project, we also do Y because Z"* are tacit knowledge about the project's conventions — not directives. They're statements about *what this project's pattern is*, written for a future reader who's about to do X and would benefit from knowing the pattern exists. Example: "### Convention — releasing a dataset bumps `src/configs/datasets.py` (rationale: experiment configs pin by version, so a release that isn't reflected in the config is unreachable from runners)." The reader chooses whether to follow the pattern; the entry explains why the pattern exists.
- **Reference RIDs** for catalog entities; include quantitative evidence (counts, sizes) when known.
- **Length is set by content.** Long enough to answer 1–6 above; short enough to scan in one pass (~5–15 lines in practice).
- Past tense — these are settled records, not plans.

## Provenance markers

Every claim in an entry should be readable as one of three things: *what was directly stated*, *what the agent inferred from evidence*, or *what was observed without articulated reasoning*. Default (unmarked) prose is "stated" — the user said this, or the entry's author wrote it directly. Use the explicit markers below for everything else.

| Marker | When to use |
|---|---|
| (none) | The user or author directly stated this. The default reading of unmarked prose. |
| **`[inferred from action]`** | The agent inferred this *fact* from the user's observable actions during the session (e.g., they opened a feature table, then moved on without curating). The action is the evidence. |
| **`[inferred from pattern]`** | The agent inferred this *reason* from prior knowledge, prior entries in this file, or general domain pattern-matching — not from anything the current user actually did or said. The riskiest class; reader-beware. |
| **`[observed]`** | The action happened; no rationale was articulated and none was inferred. The honest "we just did it" record. |

**The `[inferred from pattern]` marker is the riskiest and most fabrication-prone class.** It marks the agent's best guess based on domain knowledge or pattern-matching, not on evidence from this session. A future reader should treat these claims with the same skepticism they'd apply to an LLM's free-form rationalization. Prefer to omit the claim entirely if the pattern-inference is weak; prefer to ask the user to confirm if the claim is load-bearing (see "When to inquire" below).

`[observed]` is not failure. The collective tacit often *doesn't* have a verbalizable explanation. "The author created DAP without articulating a comparison" is a valid, complete record — better than a fabricated rationale. Don't be embarrassed by `[observed]`; it's how honest entries about tacit work look.

## When to inquire

The skill may raise a clarifying question to the user when writing an entry. The agent is *allowed* to inquire in either interactive or autonomous mode — inquiry is distinct from a checkpoint pause, and the test plan's mode flag governs checkpoints, not inquiry. But inquiry is bounded:

- **At most one question per entry.** If multiple ambiguities exist, the agent picks the highest-leverage one to ask about and uses provenance markers for the rest.
- **Only when the answer would materially improve a load-bearing claim.** Cosmetic gaps stay gaps. A `[inferred from pattern]` claim that doesn't affect a future decision isn't worth a question.
- **Confirmatory shape only — never interrogative.** The question must be answerable by yes / no / correction, not by open-ended self-attribution. The user often *can't* honestly answer "why did you do X?" — they just did it. Asking the open form invites confabulation, which is worse than `[observed]` honesty.

**Inquiry shape:**

| ✅ Confirmatory | ❌ Interrogative |
|---|---|
| "I'm about to write that you chose CS0 over CSA because CS0 carries stratified labels. Is that the characterization, a different one, or no articulated reason?" | "Why did you choose CS0?" |
| "I'm inferring this split's rationale is variance-control. Confirm, correct, or 'just did it'?" | "What's the rationale for this split?" |
| "I see traces suggesting you considered the vehicles-only subset. Was that on the table, or was the choice between animals-only and 10-class from the start?" | "What alternatives did you consider?" |

**Response → marker mapping:**

| User response | Marker becomes |
|---|---|
| "Yes / correct" | (none — promote to stated) |
| "Different reason — actually [X]" | (none — record X as stated) |
| "No reason / I just did it / I don't remember" | `[observed]` for the fact; drop any inferred rationale |
| "I didn't consider that alternative" | Remove the inferred alternative entirely |

This pairwise confirmation matches the Law of Comparative Judgment: humans can reliably answer "is this the better characterization?" but unreliably answer "what is the absolute reason?" Confirmatory inquiry preserves *"I just did it"* as a valid answer.

## What doesn't belong here

This file records *why*, not *what*. The catalog is the source of record for facts; this file points at facts but doesn't replicate them. Concretely, **don't write**:

- **Vocabulary term lists.** "The `Workflow_Type` vocab has terms X, Y, Z" goes stale the next time a term is added. Link to `deriva://catalog/{host}/{cat}/ml/vocabularies/deriva-ml/Workflow_Type` and let the reader fetch.
- **Dataset RID / type / description tables.** "13 datasets: 96E (Complete, Labeled, …), 96R (Split, …), …" is catalog data. Link to `deriva://catalog/{host}/{cat}/ml/datasets` instead. (A *short* table mapping the user-facing config name to a stable RID is fine when those names are themselves project decisions — the catalog doesn't store the mapping from `cifar10_small_labeled_split` to `CRR`. That's tacit.)
- **Schema field types or column lists.** Catalog data; fetch `deriva://catalog/{h}/{c}/schema` or the table resource.
- **Workflow URLs / checksums / version strings.** Catalog data; live in `Workflow` rows.
- **Asset MD5s, file sizes, lengths.** Catalog data.
- **Execution status, start/stop times, lineage edges.** Catalog data; fetch `deriva://catalog/{h}/{c}/ml/execution/{rid}` or `…/ml/lineage/{rid}`.

**Do write**: why the dataset was created, why the workflow's type was chosen, why a hyperparameter was selected, what alternatives were rejected and why, what would invalidate this decision, what a future reader needs to know to evaluate whether the decision still holds. Reference catalog entities by their RID and a single-line link rather than inlining their fields.

The rule of thumb: **if the catalog could go stale and break what you wrote, the catalog should answer the question, not this file.**

## Examples

### Example 1 — A model run with cross-domain implications

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

Implications for collaborators: this is a pipeline-validation run, not a
performance baseline — don't cite the 20% number as a model capability
claim. The next end-to-end run on the full dataset is where the
domain-meaningful accuracy comparison starts.
```

### Example 2 — A non-run event (no part-4 observations because nothing to observe at write-time)

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

Implications for collaborators: ML training configs that currently filter
on `Image_Annotation` should also start filtering on
`QC_Status != "blurry"` once values are populated, to avoid training on
images the pathologists have flagged unusable.
```

### Example 3 — A dead end (no successor decision)

```markdown
### Tried stain_type as model input; abandoned (execution 3-XYZ)

Hypothesis: adding the stain_type categorical (H&E vs IHC vs Trichrome)
as a one-hot model input would let the network learn stain-specific
diagnostic patterns. Trained the cifar10_quick architecture with the
extra input channel on dataset 7KE v0.4.0; held-out accuracy actually
dropped 4 points vs the baseline run (execution 8KG) that didn't use
stain_type. Walking the model's gradient attributions showed the network
was using stain_type as a shortcut to predict scanner site, not disease
class — staining variance (which is operator- and lab-specific) was
dominating the signal we wanted. Abandoned this input channel. Not
revisiting unless we get a multi-site dataset where stain protocols are
matched across sites.

Implications for collaborators: the catalog still has the `stain_type`
column on Image — keep populating it (it's correct curation), just
don't pipe it into models without a multi-site dataset.
```

### Example 4 — Confirmatory inquiry promoting an `[inferred from pattern]` claim

User just created an animals-only subset of `cifar10_complete` and didn't articulate alternatives. The agent's reasoning trace shows the user opened the vehicle-class feature values mid-session before moving on. The agent is about to write the entry.

**Agent's draft** *(before inquiry)*:

```markdown
### Created cifar10_animals_subset (DAP) at 0.2.0

300-image filter of cifar10_complete to {bird, cat, deer, dog, frog,
horse}, 50/class. Reserved for the Analyst's confusion-matrix work.

Weighed alternatives:
- Balanced 10-class subset — rejected: doesn't isolate the
  intra-animal confusion mode.
- [inferred from action] Vehicles-only subset was considered (author
  opened the vehicle feature values mid-session) and dropped without
  an articulated reason. [inferred from pattern] *possibly* because
  per-class visual variance within vehicles is higher than within
  animals in CIFAR-10; not confirmed by author.
```

The agent notices that the second alternative carries an `[inferred from pattern]` claim about *why* vehicles-only was rejected — load-bearing, because a future reader trying to understand the curation strategy would treat the variance-reasoning as a stated principle. Per "When to inquire," it asks (one question, confirmatory shape):

> "I'm about to write that you considered the vehicles-only subset and rejected it because per-class visual variance is higher in vehicles than in animals. Is that the reason, a different reason, or no articulated reason?"

**Three response paths:**

| User response | Agent's entry update |
|---|---|
| "Yes, that's right" | Promote `[inferred from pattern]` → unmarked. The variance reasoning is now stated. |
| "I rejected vehicles-only because the Analyst said the confusion mode they care about is cat-vs-dog, not truck-vs-car" | Drop the variance inference. Record the user's stated reason. |
| "I don't remember / I just clicked through and went with animals" | Keep `[inferred from action]` on the fact (the action trace shows it was considered). Drop the `[inferred from pattern]` reasoning entirely. Final entry's alternative reads: `[observed]` Vehicles-only subset was considered (author opened the feature table mid-session) and dropped without an articulated reason. |

The third response is *not failure* — it's the honest tacit-knowledge record. A future reader sees "this was on the table; no recorded reason" and can choose to re-open the comparison if relevant. The agent has resisted fabricating a plausible-sounding rationale to fill the gap.

## Worked example — Mode A firing on a proposed action

**User**: "Add a 'blurry' term to the Image_Annotation vocabulary so we can mark unusable slides."

**Response** *(before adding, the skill consults `experiment-decisions.md` and finds the QC entry above)*:

> Before adding, I checked `experiment-decisions.md` and found:
>
> > ### QC status feature added to Image table (feature 9PQ4)
> > Kept QC concerns separate from diagnostic concerns rather than extending Image_Annotation with a "blurry" diagnosis term: the two review workflows have different reviewers, criteria, and consumers, so collapsing them would entangle the queues.
>
> Adding `blurry` to `Image_Annotation` would reverse that decision. Two options: (a) add the term to the existing `Image_QC_Status` vocabulary (feature 9PQ4, vocabulary 9PR0), which preserves the separation, or (b) revisit the original rationale if the constraints have changed (e.g., the two review pools have merged, or you're explicitly opting into a single combined queue). Which do you want?

Three things this example demonstrates:
1. **Consult before act** — the skill fires on the proposed action, not on a "why" question.
2. **Quote, don't paraphrase** — the user can see the original entry and judge its weight themselves.
3. **Hand decision back with concrete options** — don't block, don't auto-proceed; the user may know the original constraints no longer hold.

## Commit prompting

After 3+ entries in a session — or at a natural pause — suggest committing `experiment-decisions.md` on its own with a message like "Record experiment design decisions." Don't bundle with unrelated changes; don't prompt after every entry.

## File mechanics

`experiment-decisions.md` lives in the project root and must be tracked in git. See `references/file-mechanics.md` for the gitignore check and first-time-setup details.
