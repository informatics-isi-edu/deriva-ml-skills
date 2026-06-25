# Tacit-Knowledge Entry Examples

Five worked examples illustrating the entry conventions from the
`capture-tacit-knowledge` skill. Read the one that matches the situation you're
in — the skill body carries the rules; these show the rules applied end-to-end.
The canonical Mode-A "consult before acting" illustration stays in the skill
body itself; these are the *write-time* shapes.

| # | Shape | Illustrates |
|---|---|---|
| [1](#example-1--a-model-run-with-cross-domain-implications) | A model run with cross-domain implications | All six entry parts; `Implications for collaborators` stated as facts |
| [2](#example-2--a-non-run-event) | A non-run event (feature/vocab creation) | Part-4 observations skipped (nothing to observe at write-time); use-case-as-hypothesis |
| [3](#example-3--a-dead-end) | A dead end (no successor decision) | Dead-end entries stand alone; the highest-leverage tacit knowledge |
| [4](#example-4--snapshot-vs-convention) | Snapshot vs convention | Record the durable convention, not the audit-time count that rots |
| [5](#example-5--confirmatory-inquiry) | Confirmatory inquiry | Promoting an `[inferred from pattern]` claim to stated — or dropping it |

---

## Example 1 — A model run with cross-domain implications

```markdown
<a id="tk-007"></a>
### tk-007 — First end-to-end CIFAR-10 run on localhost catalog 1407 ([execution 8KG](https://localhost/id/96/8KG@2P-XYZW))
**When:** 2026-04-12T15:22:00-07:00
**By:** Carl Kesselman (https://auth.globus.org/abc12345-67ef-8901-2345-67890abcdef0)
**Supported by:** [tk-003](#tk-003) (created the labeled split this run consumed)

Hypothesis: the cifar10_e2e schema, dataset [7KE](https://localhost/id/96/7KE@2P-XYZW),
and the deriva-ml-run pipeline wired together cleanly against a
freshly-seeded localhost catalog. Ran cifar10_quick (small image
classifier, fewest training passes, smallest network) because the
question was "does the plumbing work," not "does the model perform."
Picked the labeled split as input because it was the smallest dataset
with ground-truth labels on both partitions (80 train, 20 test), so a
real test number was reachable at this scale. Run finished in ~30s on
CPU; held-out accuracy 20% on 20 images vs a 10% guess-one-of-ten
baseline — a learning signal but within noise at this sample size.
Outputs linked to execution [8KG](https://localhost/id/96/8KG@2P-XYZW).

Implications for collaborators: this is a pipeline-validation run, not a
performance baseline — don't cite the 20% number as a model capability
claim. The next end-to-end run on the full dataset is where the
domain-meaningful accuracy comparison starts.
```

## Example 2 — A non-run event

(No part-4 observations because nothing to observe at write-time.)

```markdown
<a id="tk-018"></a>
### tk-018 — QC status feature added to Image table ([feature 9PQ4](https://localhost/id/96/9PQ4@2P-XYZW))
**When:** 2026-04-23T10:05:00-07:00
**By:** Dr. Pathologist (https://auth.globus.org/d4e8f200-9c2b-4a1d-bf3e-1234567890ab), Carl Kesselman (https://auth.globus.org/abc12345-67ef-8901-2345-67890abcdef0)

Created `QC_Status` on `Image`
([table 5-AB12](https://localhost/id/96/5-AB12@2P-XYZW), ~3,200 rows)
backed by a new `Image_QC_Status`
[vocabulary 9PR0](https://localhost/id/96/9PR0@2P-XYZW) in the
`histopath` schema — three terms (pass, blurry, tissue_fold) plus a
confidence_score column. Use case: blurry slides have been silently
degrading downstream model accuracy with no first-class way to mark
them. Kept QC concerns separate from diagnostic concerns rather than
extending Image_Annotation with a "blurry" diagnosis term: the two
review workflows have different reviewers, criteria, and consumers,
so collapsing them would entangle the queues. Values not populated
yet — annotator workflow is the next step.

Implications for collaborators: ML training configs that currently filter
on `Image_Annotation` should also start filtering on
`QC_Status != "blurry"` once values are populated, to avoid training on
images the pathologists have flagged unusable.
```

## Example 3 — A dead end

(No successor decision required — the dead end is the whole entry.)

```markdown
<a id="tk-026"></a>
### tk-026 — Tried stain_type as model input; abandoned ([execution 3-XYZ](https://localhost/id/96/3-XYZ@2P-XYZW))
**When:** 2026-05-04T09:18:00-07:00
**By:** Carl Kesselman (https://auth.globus.org/abc12345-67ef-8901-2345-67890abcdef0)
**Supported by:** [tk-007](#tk-007) (baseline 8KG run this is compared against), [tk-018](#tk-018) (QC_Status feature is the well-typed alternative to stain_type for model input)

Hypothesis: adding the stain_type categorical (H&E vs IHC vs Trichrome)
as a one-hot model input would let the network learn stain-specific
diagnostic patterns. Trained the cifar10_quick architecture with the
extra input channel on dataset [7KE v0.4.0](https://localhost/id/96/7KE@2P-XYZW);
held-out accuracy actually dropped 4 points vs the baseline run
([execution 8KG](https://localhost/id/96/8KG@2P-XYZW), recorded in
[tk-007](#tk-007)) that didn't use stain_type. Walking the model's
gradient attributions showed the network was using stain_type as a
shortcut to predict scanner site, not disease class — staining variance
(which is operator- and lab-specific) was dominating the signal we
wanted. Abandoned this input channel. Not revisiting unless we get a
multi-site dataset where stain protocols are matched across sites.

Implications for collaborators: the catalog still has the `stain_type`
column on Image — keep populating it (it's correct curation), just
don't pipe it into models without a multi-site dataset.
```

## Example 4 — Snapshot vs convention

Recording the durable shape, not the audit-time count.

A Curator auditing a freshly-bootstrapped catalog runs a direct query against the `Image_Classification` feature table and verifies: 1500 rows, 1500 distinct images, every image labeled exactly once. The temptation is to write that finding as a clean, quotable fact for downstream readers.

**Draft that ages out (don't write this):**

```markdown
<a id="tk-NNN"></a>
### tk-NNN — Image_Classification ground-truth audit clean ([feature 7AB](https://localhost/id/96/7AB@2P-XYZW))
... 1500 rows in Execution_Image_Image_Classification covering 1500
distinct images — no missing labels, no duplicate labels (no need for
the `newest` selector when reading this feature).
```

The audit is correct *at this instant*, but `Image_Classification` is the same table the Modeler's prediction-recording step writes into. The moment the next training execution runs, the table contains both ground-truth rows (written by the loader execution, `Confidence IS NULL`) and prediction rows (written by training executions, `Confidence` populated). The unfiltered count goes to 1800+, the same image carries multiple label rows, and a reader who quotes "no need for `newest` selector" in good faith gets the wrong result. The entry didn't lie when it was written; the catalog moved underneath it.

**Durable rewrite — capture the convention, not the snapshot:**

```markdown
<a id="tk-NNN"></a>
### tk-NNN — Convention — Image_Classification is dual-purpose (ground truth + predictions)
**When:** ...
**By:** ...

`Image_Classification` ([feature 7AB](https://localhost/id/96/7AB@2P-XYZW))
is written by two distinct kinds of execution and the rows are not
distinguishable by table membership alone: the loader execution writes
ground-truth rows with `Confidence IS NULL`; training executions write
prediction rows with `Confidence` populated. After any training run,
the same image will carry multiple rows in this feature.

Implications for collaborators: when reading this feature as ground
truth, filter by execution (the loader exec RID) or by `Confidence IS
NULL`. An unfiltered `ml.feature_values("Image", "Image_Classification")`
returns GT + every recorded prediction interleaved, which is rarely
what an analysis wants. The `newest` selector is also not a safe
substitute — "newest" is whichever execution last wrote, not "ground
truth."
```

If the audit-time snapshot still feels worth recording, scope it explicitly to the partition that *will* remain stable — e.g. "the loader-execution rows form a 1500-of-1500 clean GT layer; this scope doesn't grow with subsequent training runs." That framing makes the durability boundary visible to a future reader.

The shape to learn: **audits surface conventions.** When an audit finds a clean count or a clean shape, the count is the symptom; the convention that explains *why* the table has that shape (and what about it will or won't survive the next write) is the entry.

## Example 5 — Confirmatory inquiry

Promoting an `[inferred from pattern]` claim.

User just created an animals-only subset of `cifar10_complete` and didn't articulate alternatives. The agent's reasoning trace shows the user opened the vehicle-class feature values mid-session before moving on. The agent is about to write the entry.

**Agent's draft** *(before inquiry)*:

```markdown
<a id="tk-042"></a>
### tk-042 — Created cifar10_animals_subset ([dataset DAP v0.2.0](https://localhost/id/96/DAP@2P-XYZW))
**When:** 2026-05-25T16:08:00-07:00
**By:** Carl Kesselman (https://auth.globus.org/abc12345-67ef-8901-2345-67890abcdef0)
**Supported by:** [tk-019](#tk-019) (created cifar10_labeled_split that this filters from), [tk-038](#tk-038) [inferred from pattern] (Developer handoff named confusion-matrix work)

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
