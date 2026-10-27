# The repo's planning artifacts — and how they connect

A project keeps several Markdown files that describe its experiments from
different angles. They are **distinct views joined by a shared `<slug>`**, not
duplicates — knowing which is which (and that they link) prevents treating one as
a substitute for another:

| File | The view it gives | Authored / generated | Format |
|---|---|---|---|
| `docs/design/<entity>/<slug>.md` | **The plan & verdict** for one experiment / dataset / feature / model — Goal, Validation criteria, Outcome | hand-authored up-front (`/deriva-ml:design-experiment`), Outcome filled after the run | OKF concept doc (`Experiment Design`, …) |
| `docs/design/index.md` | **The design corpus index** — one line per design doc across all four entity types | maintained as docs are authored | OKF `type: Index` (bundle root) |
| `Experiments.md` (project root) | **The runnable/config view** — every *configured* experiment + multirun, with config-group overrides, key params, purpose, and a link to each experiment's design doc | generated from `src/configs/experiments.py` + `multiruns.py` | OKF `type: Index` (config-derived registry; the runnable-view sibling of `docs/design/index.md`) |
| `src/configs/experiments.py` | **The executable definition** — the hydra-zen config the run actually loads | hand-authored | Python (hydra-zen) |
| `tacit-knowledge.md` | **The running journal** — *why* decisions were made, what was learned | appended as you work | OKF `Log` |

**How they connect (the join is the experiment `<slug>`):**

- `docs/design/experiment/<slug>.md` ↔ `src/configs/experiments.py`: the design is
  the contract; the config implements it. The design doc's **Status & links** names
  its config entry; the config's `description` carries the design doc's URL (see the
  RID/URL-link rule below and `/deriva-ml:write-hydra-config`).
- `Experiments.md` ↔ the design docs: `Experiments.md` is the *config* index (what's
  runnable); `docs/design/index.md` is the *design* index (what's planned). They are
  two indexes of the same experiments — `Experiments.md`'s per-experiment detail
  **links to** the matching `docs/design/experiment/<slug>.md`, so a reader on the
  runnable view can jump to the plan, and vice-versa. An experiment can be
  designed-but-not-yet-configured (in the design index, not yet in `Experiments.md`)
  or configured-without-a-design (the reverse) — the two indexes make that gap visible.
- **Multiple models:** one experiment config composes a `model_config` + `datasets`;
  each model has its own `docs/design/model/<slug>.md`, linked from the experiment
  design's "Upstream designs" with the **runs** verb. So a compound or
  multi-model experiment is one experiment-design doc that links several model
  designs — the design bundle is the graph that ties them together.

Bottom line: **`Experiments.md` = the runnable view (from configs); `docs/design/`
= the planned view (the OKF design bundle); they are connected by slug and by
explicit links, not merged.** Owned by `/deriva-ml:configure-experiment`
(Experiments.md) and `/deriva-ml:design-experiment` (the design bundle).

**Keeping them in sync:** because these are views of one experiment, a change to
one usually means a change to the others — the direction of truth is config →
`Experiments.md` (the registry is regenerated from the config) and design doc ↔
config (the doc is the contract). When you add or change an experiment config,
update `Experiments.md`, link the design doc both ways, and add the design-index
line **in the same commit**. The full sync checklist lives in
this skill's SKILL.md → "Keeping the planning artifacts in sync"; the
end-to-end design → config → update-registry → run flow is `/deriva-ml:experiment-lifecycle`.
