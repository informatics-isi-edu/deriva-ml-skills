---
name: experiment-lifecycle
description: "ALWAYS use this skill when designing, planning, running, or iterating on a DerivaML experiment cycle. Names the seven-phase arc that a reproducible ML experiment follows: identify hypothesis -> create configuration -> identify assets -> run model -> update assets -> evaluate -> repeat until done. Owns the design step (the 'what question are we testing and how will we know we have an answer?' content that no other skill covers) plus the cross-step concerns (dry-run -> small-data -> full-data progression discipline, inter-phase gates that catch problems before scaling up, failure-mode triage when a run breaks). Routes to specialists for mechanics: configure-experiment + write-hydra-config for configs, work-with-assets for asset registration, execution-lifecycle for runs, compare-model-runs for evaluation, maintain-experiment-notes for documentation. The data-centric framing matters: the cycle is the unit of evolution; each cycle adds artifacts (configs, assets, executions, feature values) to the catalog; 'repeat until done' means add more cycles, not start over. Triggers on: 'design experiment', 'plan experiment', 'experiment lifecycle', 'experiment cycle', 'run experiment workflow', 'iterate on experiment', 'next iteration', 'what should I test', 'what hypothesis', 'experiment plan', 'set up experiment', 'how do I structure this experiment', 'I want to test', 'I want to compare', 'experiment workflow', 'reproducible experiment', 'evaluate my model', 'should I run another experiment', 'between runs', 'after the dry run', 'before scaling up'."
---

# Experiment Lifecycle in DerivaML

A DerivaML experiment isn't a one-shot script run — it's a cycle. You identify what you want to test, set up the configuration, identify the assets your run will consume, run the model, register the assets the run produces, evaluate the result, and decide whether to iterate. The data-centric framing matters here: **the cycle is the unit of evolution; each cycle adds artifacts (more configs, more assets, more executions, more feature values) to the catalog; "repeat until done" means add more cycles to the same catalog, not start over.**

This skill names the arc and walks you through it. The mechanics of each phase live in specialist skills (this skill routes to them); what *this* skill carries is the design step (phase 1, the gap with no other home), the cross-step disciplines that prevent waste (the dry-run → small-data → full-data progression; inter-phase gates), and the documentation loop (`maintain-experiment-notes` auto-fires anyway, but the lifecycle calls out where it should hit).

> **Cold-start orientation.** Before the first DerivaML MCP call in the conversation, fetch `deriva://deriva-ml/getting-started` (pagination contract, error envelopes, `(hostname, catalog_id)` conventions) and `deriva://deriva-ml/concepts` (the five abstractions). One round trip each, both cached for the rest of the session. See `/deriva-ml:using-deriva-mcp` for the full cold-start discipline.

## The seven phases

```
identify hypothesis  →  create configuration  →  identify assets  →
run model  →  update assets  →  evaluate  →  repeat until done
                                                       ↑
                                                       └── data-centric:
                                                           the cycle is
                                                           the unit of
                                                           evolution;
                                                           artifacts
                                                           accumulate
```

### Phase 1 — Identify hypothesis

The phase no other skill owns. Before writing any config, settle:

- **What question are you testing?** "Does X improve Y?" "Is A better than B for purpose C?" "What's the effect of Z on the metric we care about?" Be specific. A hypothesis you can't write in one sentence is a hypothesis the experiment can't test cleanly.
- **What evidence will answer it?** Which feature value or metric, computed how, on which dataset, with what comparison baseline? "Test accuracy goes up" isn't an answer to a question; "test accuracy on `cifar10_labeled_split` v2.0.0 is at least 5% higher than the baseline cifar10_default execution" is.
- **What's the success criterion?** A run finishes either confirming the hypothesis, refuting it, or being inconclusive. Knowing in advance which is which prevents post-hoc rationalization.
- **What's the cost budget?** Roughly how much compute, how many GPU-hours, how many cycles before you stop iterating regardless of result? This bounds the next phases.

**Deliverable:** the hypothesis written down in `experiment-decisions.md`. The `maintain-experiment-notes` skill auto-fires when you make decisions during this phase and will capture them; the lifecycle's job is to make sure you actually *make* the decision before moving on.

If you can't answer the four questions above, do not advance to phase 2. The most expensive failure mode in ML experimentation is running an experiment that, regardless of result, doesn't tell you anything about your hypothesis. The cost of writing the hypothesis down is small; the cost of finding out you tested the wrong thing after running the cycle is large.

### Phase 2 — Create configuration

Now express the hypothesis as a hydra-zen configuration. The mechanics are owned by two skills:

- **`/deriva-ml:configure-experiment`** — config groups (`deriva_ml`, `datasets`, `assets`, `workflow`, `model_config`, `experiment`, `multiruns`), how they compose, the order to write them in, the project structure they sit in.
- **`/deriva-ml:write-hydra-config`** — per-config-file syntax (`DatasetSpecConfig`, `builds()`, `experiment_config`, `multirun_config`, `with_description`), validation against catalog state.

What this phase adds to the catalog: nothing yet. Configs live in your repo; they reference catalog entities by RID and version. The catalog is unchanged until you run.

**Inter-phase gate:** before advancing to phase 3, run `uv run deriva-ml-run --info` to verify the config tree composes. Hydra config errors are easier to fix when you haven't yet identified the assets and rolled the version forward.

### Phase 3 — Identify assets

Decide which existing catalog assets your config will consume:

- **Datasets** — which dataset RIDs and versions does the experiment depend on? Hardcode them in `configs/datasets.py` via `DatasetSpecConfig(rid=..., version=...)`. Pinning the version is essential — without it, a downstream catalog change can silently move the data your experiment ran against.
- **Model weights / pretrained checkpoints** — registered as Asset rows; referenced from `configs/assets.py`. If the asset doesn't exist yet, register it now (handoff to `/deriva-ml:work-with-assets` for the upload + registration).
- **Vocabularies** — verify any vocabulary terms your config relies on actually exist in the catalog (handoff to `/deriva:manage-vocabulary` for `add_term` if needed).

What this phase adds to the catalog: nothing if all assets already exist; new Asset rows or vocabulary terms otherwise. None of this is "the experiment running" — it's the prerequisite-checking and gap-filling that the run will depend on.

**Inter-phase gate:** before advancing to phase 4, do a dry run: `uv run deriva-ml-run +experiment=<your_experiment> dry_run=true`. Dry-run validates that every referenced asset/dataset/vocabulary term resolves; failures here are config errors, not run errors, and they're cheap to fix. **Do not skip dry-run.** It is the cheapest gate in the whole cycle.

### Phase 4 — Run model

Hand off to `/deriva-ml:execution-lifecycle` for the actual run mechanics. The lifecycle skill covers the state machine (Created → Running → Pending_Upload → Uploaded), the `with ml.create_execution(config) as exe:` pattern, and the upload-output discipline.

What this phase adds to the catalog: an Execution row (with status, timestamps, and the producing-workflow link), feature values produced by the run, output assets registered to the execution.

**Discipline: progression matters.** The first run on a fresh hypothesis should be the smallest run that exercises the full path — not the dry run (that's the gate; it doesn't actually train), but a run on a small representative dataset. The recommended progression:

1. **Dry run** (gate from phase 3) — proves the configs resolve and the catalog state is consistent. No compute.
2. **Small-data run** — a run on a small representative dataset (`cifar10_small_labeled_split` rather than `cifar10_labeled_split`). Proves the model code runs end-to-end, that outputs upload correctly, that feature values land where expected. Minutes of compute, not hours.
3. **Full-scale run** — only after the small-data run succeeded. Hours or days of compute; bound by your phase-1 cost budget.

The cost ratio between the three is roughly 1 : 100 : 10,000. Skipping the small-data step is the second most expensive failure mode in ML experimentation — debugging a broken model on the full dataset wastes orders of magnitude more compute than catching the same bug on a 5-minute small-data run.

**Inter-phase gate:** before advancing from small-data to full-scale, verify (a) the loss curve looks sane (not NaN, not stuck, not collapsed), (b) at least one feature value was actually written to the catalog (otherwise the upload path has a bug that won't be visible until the long run finishes), (c) the run hit the metrics you'd expect on a small dataset (a model that doesn't learn on small data won't learn on big data).

### Phase 5 — Update assets

The run produced new artifacts: model weights as Asset rows, evaluation summaries as Asset rows, feature values for each evaluated record. Decide which become inputs for the *next* cycle:

- **If the next cycle uses these weights as a starting checkpoint** — register them as a new Asset row (already done by the execution's upload step), then reference the new Asset RID from the next cycle's `configs/assets.py`.
- **If the next cycle compares against this cycle's outputs** — note the execution RID and the metric values (the `compare-model-runs` skill auto-fires later for the comparison side; this phase is just about cataloging what we have).
- **If the catalog has evolved during the run** (new dataset versions; new vocabulary terms; new asset types) — review whether the next cycle's configs should be updated. A common pattern: new asset → bump `assets.py` to point at the new RID → next cycle picks it up.

The mechanics of registering and updating asset references are in `/deriva-ml:work-with-assets` (asset side) and `/deriva-ml:write-hydra-config` (config side; specifically the "Adding a new asset to the project" workflow).

What this phase adds to the catalog: usually nothing new (the run already added the asset rows); the work is in the *config repo*, where new asset RIDs get written into the next cycle's configuration. Commit those changes.

### Phase 6 — Evaluate

Compare this cycle's results against the hypothesis from phase 1. Two paths depending on scope:

- **Single-run analysis** — does this run's metrics support, refute, or fail to address the hypothesis? Read the feature values from the catalog (`deriva_ml_list_feature_values(execution_rids=[...])`) and the output assets (model checkpoint, evaluation summary). Document your reading in `experiment-decisions.md` (auto-fired by `maintain-experiment-notes`).
- **Multi-run comparison** — comparing this cycle to previous cycles or to a sweep. Hand off to `/deriva-ml:compare-model-runs` for the ranking/aggregation logic.

> **Surfacing prior runs of the same kind:** `deriva_ml_list_executions(workflow_type="Training", sort=True)` returns every training execution across every workflow in newest-first order — one call instead of "enumerate workflows of that type, then page each one's executions". Pair with `status="Uploaded"` if you only want successful runs. The same `workflow_type=` filter works for `Inference`, `Evaluation`, `Annotation`, etc. — anything in your `Workflow_Type` vocab.

What this phase adds to the catalog: typically nothing — evaluation reads existing artifacts. The new content goes into `experiment-decisions.md` (your notebook of results-and-interpretations).

**Failure-mode triage** — if the run failed, the cause is usually one of:

- **Config error** — the dry run should have caught this in phase 3. If it didn't, there's a config-validation gap worth fixing.
- **Catalog state error** (vocabulary term missing, FK violation, asset RID stale) — check `/deriva-ml:troubleshoot-execution` and `/deriva:troubleshoot-deriva-errors` for the diagnostic patterns.
- **Model code bug** (NaN loss, OOM, dataloader hang) — the small-data run from phase 4 should have caught this. If it didn't, expand what small-data tests cover.
- **Resource exhaustion** (disk full, OOM, GPU unavailable) — usually reproducible at small scale; if not, see `/deriva-ml:manage-storage` for cache cleanup.

The right diagnostic action depends on *which phase* the failure happened in, which is why the lifecycle skill names the phases and the gates between them.

### Phase 7 — Repeat (or stop)

The cycle either terminates or feeds back into phase 1 with an updated hypothesis. Decide deliberately:

- **Stop if** the hypothesis is answered (confirmed, refuted, or shown inconclusive in a way that closes the question).
- **Stop if** the cost budget from phase 1 is exhausted, regardless of result. Document what you learned and why you're stopping; revisit later if useful.
- **Iterate if** the result suggests a refined hypothesis ("X improved Y, but only when Z; let's test Z directly") — go back to phase 1 with the new hypothesis.
- **Iterate if** the result was inconclusive due to a fixable problem (small dataset masked the effect; metric was wrong; baseline was wrong) — go back to whatever phase the problem was in.

The catalog state at the end of one cycle is the starting state of the next: more datasets, more workflows, more executions, more feature values, more assets. Each cycle is a new layer on the same data structure, not a fresh start. **This is what "data-centric" means in practice.** The hypothesis evolves; the catalog accumulates; the project history is the catalog's history.

## Routing summary

| Phase | Primary skill |
|---|---|
| 1. Identify hypothesis | This skill (no other home) |
| 2. Create configuration | `/deriva-ml:configure-experiment`, `/deriva-ml:write-hydra-config` |
| 3. Identify assets | `/deriva-ml:work-with-assets`, `/deriva:manage-vocabulary` |
| 4. Run model | `/deriva-ml:execution-lifecycle` |
| 5. Update assets | `/deriva-ml:work-with-assets`, `/deriva-ml:write-hydra-config` |
| 6. Evaluate | `/deriva-ml:compare-model-runs`, `/deriva-ml:troubleshoot-execution` |
| 7. Repeat | This skill (back to phase 1) |

Auto-fires alongside this lifecycle: `maintain-experiment-notes` (captures decisions throughout); `dataset-lifecycle` (if new datasets get created mid-cycle); `catalog-operations-workflow` (if catalog mutations are needed mid-cycle).

## Related skills

- **`/deriva-ml:dataset-lifecycle`** — sibling lifecycle skill for the dataset side; the experiment cycle frequently depends on dataset versioning decisions named in that lifecycle.
- **`/deriva-ml:execution-lifecycle`** — sibling lifecycle skill for the run mechanics; phase 4 hands off here for the state machine and upload discipline.
- **`/deriva-ml:model-development-workflow`** — higher-level "how to develop a model end-to-end" workflow; the experiment cycle is the inner loop within that arc.
- **`/deriva-ml:maintain-experiment-notes`** (auto-fires) — captures the decisions made in phases 1, 4, 5, 6, 7. The lifecycle skill names *when* to make a decision; this one captures *what was decided*.
- **`/deriva:troubleshoot-deriva-errors`** (deriva-skills) — first stop for catalog-state errors during any phase that touches the catalog.
