# Round 5 refinement — addendum to 2026-05-02 plan

This addendum records the refinement interview for Round 5 of the
[2026-05-02 tier-2 audit cleanup plan](2026-05-02-tier-2-audit-cleanup-plan.md).
The interview reshaped Round 5 from "decide where three borderline
skills belong" (the parent plan's framing) to a sharper set of three
decisions plus a content-distribution exercise:

- **`use-annotation-builders`** moves to tier-1 as its own skill.
- **`coding-guidelines`** is reframed: the skill name is misleading; the
  content is mostly project-structure-and-operations, not generic Python
  conventions. The skill is **deleted**, and its 13 atoms are
  distributed across **a new tier-2 `setup-derivaml-project` skill**
  (the bootstrap moment), `setup-notebook-environment` (dev-env
  operations), `model-development-workflow` (workflow-cycle
  conventions), and **deletion** for the atoms that are already
  canonically carried elsewhere.
- **`create-web-app`** stays in tier-2 with a small description reframe
  to lead with the `deriva-ml-apps` server prerequisite.

Eight design questions resolved.

## Audit findings revisited

The parent plan's Round 5 framing identified three borderline skills
and recommended a tier placement for each:

- `coding-guidelines` (154 lines, currently tier-2) — recommend tier-1
  or split.
- `use-annotation-builders` (175 lines, currently tier-2) — recommend
  tier-1.
- `create-web-app` (161 lines, currently tier-2) — recommend keep in
  tier-2 with possible rename.

Round 5's refinement validated the `use-annotation-builders` move and
the `create-web-app` decision, but reshaped `coding-guidelines`
substantially. Reading the actual content section-by-section showed
that "coding standards" is one minor section out of eight; the rest is
project-bootstrap, environment management, git workflow, version
bumping, notebook conventions, and DerivaML extensibility — the
conventions a deriva-ml project follows throughout its lifetime, not
generic Python style. Most of that content is already canonically
carried in other tier-2 skills (`execution-lifecycle` carries
commit-before-running with stronger framing; `setup-notebook-environment`
carries env install + nbstripout; `validate-project-setup` carries the
project-shape verification). The right move is to redistribute the
content to where it's needed, not to relocate it as a single skill.

The user also flagged that all three skills are already
`disable-model-invocation: true` (Round 4's principle), so Round 5 is
about discoverability and ownership (which plugin's namespace, which
README they appear in), not always-on weight.

## Resolved decisions

| # | Question | Resolution |
|---|---|---|
| 1 | `use-annotation-builders` placement: keep tier-2, move to tier-1 as own skill, or absorb into tier-1 `customize-display`? | **Move to tier-1 as own skill.** Two paths (interactive MCP vs. Python builders) are different kinds of work for different kinds of users; splitting them across two skills with different descriptions lets the LLM trigger correctly on either workflow. Absorbing into `customize-display` would bury the builder content one click away from the skill list. |
| 2 | `coding-guidelines` placement: tier-1, tier-2-keep, or split? | **Reframed.** The skill is misnamed — it's mostly repo bootstrap and project operations, not generic Python conventions. Resolved in Q3 below. |
| 3 | What is `coding-guidelines` actually about? | **Project-structure and operations**, not coding standards. Most content (env management, git workflow, version bumping, notebook conventions, extensibility) applies throughout the project's lifetime. The 8-line generic coding-standards section is a small leaf, not the trunk. The skill name was misleading. Decision: **option (C)** — distribute the content to the skills where it's actually needed; delete the source skill. |
| 4 | Per-atom distribution table for the 13 content atoms in `coding-guidelines` | **Approved with one revision** (atom 8, version-bumping decision matrix, lands in `model-development-workflow` Phase 6 rather than `execution-lifecycle` Phase 1 — the bump *decision* is made when releasing a project version, which is the model-dev concern). See full distribution table below. |
| 5 | `create-web-app` placement: keep tier-2, move to tier-1, or split? | **Keep in tier-2 as-is, with a small reframe.** Sharpen the description to lead with the `deriva-ml-apps` server prerequisite. The skill's headline value IS the deriva-ml-apps server; tier-1-only users without the server can't actually use the generic-half patterns (the proxy paths aren't present at the URL). Splitting would create maintenance cost without proportional discoverability benefit. |
| 6 | Commit shape: 8-10 small commits, 5 logical groupings, or 2 repo-aligned mega-commits? | **5 logical groupings.** (1) tier-1: new `use-annotation-builders` skill + tier-1 marketplace + tier-1 README + tier-1 `customize-display` cross-reference. (2) tier-2: distribute `coding-guidelines` content + delete the skill + new `setup-derivaml-project` + tier-2 marketplace + tier-2 README + tier-2 cross-references. Within commit 2: content-first ordering (distribute → create new → cross-reference cleanup → delete). (3) tier-2: reframe `create-web-app`. (4) tier-2: README's broken Chaise-annotations role description (Round 5 noticed it; tier-1 framing now reflects post-move reality). (5) tier-2: refinement addendum + handoff doc update. |
| 7 | Verification gate: atom-tracking checklist or diff preview? | **Atom-tracking checklist for commit 2** (the multi-skill distribution). For commit 1 (tier-1 move) and commit 3 (`create-web-app` reframe), simpler diff preview is enough — those are smaller and don't have multi-skill distribution risk. |
| 8 | Name for the new bootstrap tier-2 skill | **`setup-derivaml-project`**. Longer than `bootstrap-project` but honest about what it does, and matches the existing `setup-notebook-environment` naming pattern. Composes with the existing project-setup arc: `setup-derivaml-project` → `setup-notebook-environment` → `validate-project-setup` → lifecycle skills. |

## Per-atom distribution table for `coding-guidelines`

The skill's 13 content atoms (numbered by reading order) and their destinations:

| # | Atom | Destination | Notes |
|---|---|---|---|
| 1 | `mkdir` + `cd` + `git init` + `uv init` | New `setup-derivaml-project` | Bootstrap moment |
| 2 | `uv add deriva-ml` + commit `uv.lock` rationale | New `setup-derivaml-project` | Bootstrap moment |
| 3 | `pyproject.toml` template (deps, dependency-groups, setuptools_scm, project.scripts) | New `setup-derivaml-project` | The exact template a new project should start with |
| 4 | `uv sync` / `uv sync --group=jupyter` / `uv run` rules | `setup-notebook-environment` | Already covers `uv sync --group=jupyter`; absorbing the generic rules makes it the canonical home for dev-env operations |
| 5 | Install `gh` + `gh auth login` | New `setup-derivaml-project` | One-time setup; needed before the PR loop |
| 6 | Branch strategy + PRs (feature branches, keep main clean, use PRs even for solo) | `model-development-workflow` | Already has model-dev cycle phases; branch-and-PR conventions live with the workflow that uses them |
| 7 | Commit-before-running discipline | **DELETE** | Already canonically in `execution-lifecycle` (Git Commit Enforcement section + Critical Rule #6 + Phase 1 Step 5) and `catalog-operations-workflow` Step 3, with stronger framing (names the actual `DerivaMLDirtyWorkflowError`) |
| 8 | Version-bumping mechanics + patch/minor/major decision matrix | `model-development-workflow` Phase 6 (Production Run) | The bump decision is a model-dev concern; `execution-lifecycle` only checks that the bump was done |
| 9 | Coding standards (docstrings + type hints + ruff + semver pointer) | New `setup-derivaml-project` | Conventions adopted at bootstrap |
| 10 | Notebook guidelines (nbstripout + Restart-and-Run-All) | `setup-notebook-environment` | Already covers nbstripout install; absorbing the discipline keeps notebook conventions in one place |
| 11 | Experiments-and-Data pointer block | **DELETE** | Pure cross-reference list; the receiving skills already exist and the inheritance rule (Round 3) means the LLM finds them |
| 12 | Extensibility (`DerivaML` subclass example) | `model-development-workflow` (or `new-model`) | Pattern shows up at model-authoring/extending time |
| 13 | Summary checklist | **DELETE** (or fold the 2-3 still-load-bearing bullets into `setup-derivaml-project`) | Most bullets restate moved content |

Net effect: **`coding-guidelines` deleted**; one new tier-2 skill (`setup-derivaml-project`) carries the bootstrap moment; the remaining content distributes to 2 existing tier-2 skills.

## Operating principles confirmed

- **Each round ships as N independent commits, content-first ordering** — within commit 2, distribute the content to its new homes BEFORE deleting the source skill, so cross-references never point at vanished content.
- **Guide-shaped vs tool-shaped** — all three Round 5 skills are already tool-shaped (`disable-model-invocation: true`); Round 5 doesn't change any auto-fire weight.
- **The inheritance-with-override rule** (Round 3, ADR-0001) — when `use-annotation-builders` lands in tier-1, it's an inheritance case (no deriva-ml override exists for the Python builder pattern), so the rule routes correctly without per-skill carve-outs.
- **The Round 4 always-on rule** — `setup-derivaml-project` ships as `disable-model-invocation: true` (tool-shaped, slash-only) like the other setup skills. It's a one-time operation, not a discipline.

## Execution shape

Five commits in deriva-ml-skills + one commit in deriva-skills.

### Commit 1 (deriva-skills, tier-1)

`use-annotation-builders: new tier-1 skill (moved from deriva-ml-skills)`

- Create `deriva-skills/skills/use-annotation-builders/` with the SKILL.md content moved from tier-2. Adjust frontmatter and any tier-2-specific framing.
- Add to `deriva-skills/.claude-plugin/marketplace.json` skills list.
- Add row to deriva-skills README.
- Add cross-reference from tier-1 `customize-display` (the Round 5 audit found the gap).
- Bump tier-1 version (minor — new skill).
- Diff preview before commit (Q7).

### Commit 2 (deriva-ml-skills, tier-2 — the heaviest)

`coding-guidelines: distribute content; delete; create setup-derivaml-project`

Within this commit, content-first ordering (Q6 sub-question):

1. Distribute atoms 4 + 10 to `setup-notebook-environment`.
2. Distribute atoms 6 + 8 + 12 to `model-development-workflow`.
3. Create new `setup-derivaml-project` skill (atoms 1 + 2 + 3 + 5 + 9, plus survivors from atom 13).
4. Cross-reference cleanup: scan tier-2 for `/deriva-ml:coding-guidelines` and `/deriva-ml:use-annotation-builders` references; update to point at new homes (or `/deriva:use-annotation-builders` for the latter).
5. Delete `skills/coding-guidelines/` directory.
6. Update `marketplace.json`: add `setup-derivaml-project`, remove `coding-guidelines`, remove `use-annotation-builders`.
7. Update README skill table.

Atom-tracking checklist before commit (Q7).

### Commit 3 (deriva-ml-skills)

`create-web-app: sharpen description to lead with deriva-ml-apps server prerequisite`

- Frontmatter description rewrite.
- Optional rename to `create-deriva-ml-app` (decided at commit time; if rename, also update marketplace, README, and any cross-references).

### Commit 4 (deriva-ml-skills)

`README: update Tier-1 vs Tier-2 framing for post-Round-5 reality`

- Fix the broken "Chaise display annotations" claim under tier-1 (now true with the move).
- Update the steering-principle paragraph to reflect ADR-0001's inheritance-with-override rule (carryover from Round 3 the README didn't catch).
- Reflect the new `setup-derivaml-project` skill in the project-setup arc framing.

### Commit 5 (deriva-ml-skills)

`docs: round 5 handoff update`

- Mark Round 5 ✅ Done in `2026-05-02-tier-2-audit-cleanup-session-handoff.md`.
- Record the five commits' hashes (deriva-ml-skills) and the one tier-1 commit hash.
- Carry Round 6 forward as the next pickup point.

## Estimated effort

- Commit 1 (tier-1): ~30-45 min (move + marketplace + README + cross-reference + version bump).
- Commit 2 (tier-2 redistribute): ~60-90 min (largest — multi-skill distribution + new skill creation + cleanup).
- Commit 3 (create-web-app reframe): ~10-15 min.
- Commit 4 (README update): ~10-15 min.
- Commit 5 (handoff): ~10-15 min.

**Total:** ~2-3 hours. Slightly over the parent plan's "2-3 hr" estimate because the `coding-guidelines` distribution is more involved than the parent plan's "move to tier-1" framing assumed.

## Pickup notes

When this round ships:

- Update the parent session-handoff document to mark Round 5 ✅ Done; record the six commits' hashes (5 in deriva-ml-skills + 1 in deriva-skills); note the tier-1 version bump.
- Round 6 (MCP tool and resource additions: `get_lineage`, `rank_executions`, `validate_dataset_spec`) becomes the natural next round.
- Note for Round 6: this is the heaviest round — touches deriva-ml-mcp source code, needs new tools + resources + tests + version bump. The cross-repo asks (`add_instructions`, `exclude_paths`) raised in parallel from Round 2 should be checked for status before starting; if they've landed, the architectural sequencing changes.
