# Round 1 refinement — addendum to 2026-05-02 plan

This addendum records the refinement interview for Round 1 of the
[2026-05-02 tier-2 audit cleanup plan](2026-05-02-tier-2-audit-cleanup-plan.md).
It captures the design decisions that were not specified in the original
plan, the resolutions reached during the refinement interview, and the
final execution shape for Round 1.

The interview was conducted as relentless one-question-at-a-time
walking down the design tree, with each question carrying a recommended
answer for the user to approve, modify, or reject.

## Audit findings that motivated Round 1

(For full audit context, see the parent plan document.)

Round 1's scope was originally framed as "tier-2 mechanical cleanup":
delete two router skills, fix 11 stale references to deleted tier-1
skills, add cross-references to new tier-1 skills, update README/CLAUDE.md
counts. Estimated 30-45 minutes; very low risk.

The refinement surfaced two pieces of substance the original framing
missed:

1. The two routers carried real concepts that would be lost on
   deletion. `route-project-setup` implicitly named the validate-the-
   project-shape concern (the assumption that a DerivaML project repo
   matches the `deriva-ml-model-template` shape). `route-run-workflows`
   implicitly named the experiment lifecycle arc (design → configure →
   identify assets → run → update assets → evaluate → repeat).
   Neither concept currently has a named home; deletion-without-replacement
   would lose them.

2. `check-deriva-ml-versions` is structurally broken. Its bash command
   examples reference a script (`check_versions.py`) that lives in
   tier-1 — but that script was deleted in commit `b407acf` when the
   tier-1 `check-deriva-versions` skill was removed and versioning
   was folded into `troubleshoot-deriva-errors`. Four of the skill's
   command examples now point at a non-existent file. Fixing this is
   not a one-line edit; it's a structural rewrite.

These two findings expanded Round 1 from "stale-reference cleanup" to
"cleanup + two new skills + one structural fold." Estimated effort
revised to 60-90 minutes.

## Resolved decisions

The interview resolved twelve design questions. Each row records the
question, the recommended answer the assistant proposed, and the user's
final decision.

| # | Question | Recommended | Decision |
|---|---|---|---|
| 1 | Delete routers wholesale or audit triggers first? | Audit first to redistribute unique triggers | Audit first |
| 2 | Just delete routers, or replace with new real skills? | Replace with new skills (option b) | Replace with new skills |
| 3 | What cross-step content does `experiment-lifecycle` carry that doesn't live elsewhere? | Items 2/3/5: progression discipline, inter-phase gates, failure-mode triage | Items 2/3/5, plus phase 1 owns the "identify hypothesis" design content (the gap with no current home) |
| 4 | Where do "define experiment", "set up config", "update config with new assets" go? | Define-experiment goes to `experiment-lifecycle` phase 1; set-up-config routes to existing specialists; update-with-new-assets goes as a new section in `write-hydra-config` | Approved |
| 5 | `experiment-lifecycle` shape: 7 sequential phases or philosophy-led conceptual frames? | Hybrid leaning toward sequential phases (matches existing lifecycle skills) | Approved |
| 6 | `validate-project-setup` form: checklist only, bundled script, or both? | Conceptual checklist only for v1 | Approved |
| 7 | Stale-reference fixes: file-by-file or survey-first table? | Survey first, single approval, mechanical execution | Survey first |
| 8 | Approve the 11-row replacement table + structural fold of `check-deriva-ml-versions`? | Yes to both | Approved |
| 9 | Within-Round-1 ordering: content-first, deletion-first, or single mega-commit? | Content-first; 7 separate commits | Content-first; 7 commits |
| 10 | Frontmatter for the two new skills? | `experiment-lifecycle` auto-fires + slash-typeable; `validate-project-setup` slash-only + user-invocable | Approved |
| 11 | `execution-lifecycle` consistency: auto-fire (match `dataset-lifecycle`) or stay slash-only? | Auto-fire — bring the lifecycle trio into consistent behavior | Approved |
| 12 | Final confirmations on naming, phase 1 deliverable, README/CLAUDE.md framing | Keep `validate-project-setup` name; written-down hypothesis as phase 1 deliverable; user-commands-vs-guides framing in README; maintainer convention in CLAUDE.md | All approved |

## Operating principle established

The interview surfaced an operating principle that was implicit in the
audit but never named: **guide-shaped skills auto-fire ("looking over
the shoulder of the ML developer to guide them"); tool-shaped skills
are on-demand.**

The lifecycle trio (`dataset-lifecycle`, `execution-lifecycle`,
`experiment-lifecycle`) and the discipline skills (`maintain-experiment-notes`,
`catalog-operations-workflow`, `model-development-workflow`) are
guide-shaped — they watch what the user is doing and inject framing
before mistakes happen. The verification, troubleshooting, and setup
skills (`validate-project-setup`, `troubleshoot-execution`,
`troubleshoot-deriva-errors`, `setup-notebook-environment`,
`coding-guidelines`) are tool-shaped — they're invoked when the user
explicitly needs them.

This distinction shapes:

- Whether `disable-model-invocation` is set (guide → unset; tool → true)
- Whether the skill description leads with "ALWAYS use this skill when
  …" (guide-shaped pushiness) or "Use when …" (tool-shaped neutrality)
- Whether the skill body leads with framing that orients the user
  (guide-shaped) or a procedure that produces a result (tool-shaped)
- How the skill is documented in README (guides in the auto-invoked
  table; tools in the user-commands table)

## CLAUDE.md vs README.md scope

A separate clarification from the interview: **CLAUDE.md is
maintainer-only.** It ships in the source repo but is not packaged
into the installable plugin. End users never see it.

The implication: **end-user-critical content does not go in CLAUDE.md.**
Critical content for users lives in:

- README.md (visible on the marketplace listing and the GitHub repo
  page)
- The skill descriptions and bodies themselves (read by the LLM; user
  experiences them indirectly through the LLM's behavior)

CLAUDE.md is for maintainer concerns: release process, file layout
conventions, gotchas when editing skills, cross-repo coordination
notes, conventions to follow when adding new skills.

This shapes Round 1's commit 7: README gets the user-facing rebuild
(separating user commands from auto-invoked guides; updated skill
table); CLAUDE.md gets the maintainer-facing version (skill counts
updated; the guide-shaped vs tool-shaped convention codified for
future skill additions).

## Final Round 1 execution plan: seven commits

Round 1 ships as seven focused commits, each independently revertable,
in this order:

### Commit 1 — Versioning section in `troubleshoot-execution`

Build a "Versioning and updates" section in `troubleshoot-execution`
mirroring the structure that tier-1's `troubleshoot-deriva-errors` got
when its sibling skill was deleted:

- Check installed versions (the three components: `deriva-ml`,
  `deriva-ml-mcp`, `deriva-ml-skills`) using direct primitives
  (`uv pip show`, `server_status`, plugin.json read)
- Where to find the latest release of each
- Update path for each component
- The "errors started after an update" debugging trail

Self-contained content addition; expands trigger phrases on the
description ("check ml versions", "update deriva-ml", etc.).

### Commit 2 — Delete `check-deriva-ml-versions`; update routing

Delete the broken skill from disk; update marketplace.json; update
`help/SKILL.md` and `deriva-ml-context/SKILL.md` to point at
`troubleshoot-execution`'s new versioning section instead.

This commit is the deletion-plus-pointer-fix together so the repo is
never in a state where the deleted skill is still referenced.

### Commit 3 — Stale-reference fixes (the route-catalog-schema set)

Apply replacement table items 1-6: the `route-catalog-schema`
references in `work-with-assets` (3 places),
`create-web-app/SKILL.md`, `model-development-workflow/SKILL.md`,
plus the references to `/deriva:check-deriva-versions` in
`help/SKILL.md` and `deriva-ml-context/SKILL.md` that haven't already
been fixed by commits 1-2.

Mechanical batch; no design decisions.

### Commit 4 — Delete the two routers; redistribute orphan triggers

Delete `route-project-setup` and `route-run-workflows` from disk.
Update marketplace.json. Apply the three small specialist-description
tweaks (mostly to `setup-notebook-environment` whose triggers are
thin) so orphan trigger phrases don't go uncaught.

### Commit 5 — New skill: `experiment-lifecycle`

Build the new skill in full. Estimated 150-200 lines:

- Brief framing paragraph (data-centric; the cycle is the unit of
  evolution; "repeat until done" means add cycles, don't start over)
- Seven phase sections (identify hypothesis → create configuration →
  identify assets → run model → update assets → evaluate → repeat)
- Each phase explicitly notes what gets added to the catalog
- Each phase routes to the specialist for mechanics
- Cross-step concerns interleaved: progression discipline (dry-run →
  small-data → full-data), inter-phase gates, failure-mode triage
- Phase 1 owns substantive content (the "identify hypothesis" design
  step) with the user's deliverable being a written-down hypothesis
  that `maintain-experiment-notes` will capture
- Frontmatter: auto-fires + slash-typeable

Update marketplace.json to include the new skill.

### Commit 6 — New skill: `validate-project-setup`

Build the new skill: conceptual checklist only, no bundled script.
Walks the LLM through verifying a DerivaML project against the
`deriva-ml-model-template` shape (configs/, models/, scripts/,
notebooks/, pyproject.toml entry points, experiment-decisions.md,
Experiments.md, etc.). Reports each as present/missing/partial with
a one-line note on what to do about gaps.

Frontmatter: slash-only, user-invocable. Updates marketplace.json.

### Commit 7 — README/CLAUDE.md catch-up + `execution-lifecycle` consistency fix

Two combined changes:

- README.md: rebuild with the user-commands-vs-auto-invoked-guides
  framing (the tier-1 `7ca1fad` pattern). Update the skill table:
  new skills added; deleted skills removed; the lifecycle trio
  explicitly framed as auto-fired guides that "look over the user's
  shoulder."
- CLAUDE.md: maintainer-facing updates. Skill count goes from 29 to
  30 (delete 2 routers + delete check-deriva-ml-versions; add 2 new
  skills; net +0 then +1 for the troubleshoot-execution expansion).
  Codify the guide-shaped vs tool-shaped convention as a maintainer
  rule for future skill additions.
- Drop `disable-model-invocation: true` from
  `execution-lifecycle/SKILL.md` to bring it into consistent behavior
  with the rest of the lifecycle trio.

## Skill count change for Round 1

| Phase | Count | Delta | Note |
|---|---|---|---|
| Start | 29 | — | Original plan inventory |
| After commit 2 | 28 | -1 | `check-deriva-ml-versions` deleted |
| After commit 4 | 26 | -2 | Two routers deleted |
| After commit 5 | 27 | +1 | `experiment-lifecycle` added |
| After commit 6 | 28 | +1 | `validate-project-setup` added |
| End | 28 | -1 net | One fewer skill; broken/redundant ones replaced by substantive ones |

## Estimated effort

Original Round 1 estimate: 30-45 min.

Revised after refinement: 60-90 min — the structural fold of
`check-deriva-ml-versions` and the two new skills add real content
work beyond the mechanical cleanup. Still single-sitting; still very
low risk; still tier-2-only changes (no MCP source edits).

## Dependencies and follow-up

Round 1 has no upstream dependencies; it can execute immediately.

After Round 1 ships, three follow-up items become easier:

- Round 2 (MCP lifecycle prompts) can mirror the new
  `experiment-lifecycle` skill content as a `_EXPERIMENT_LIFECYCLE_GUIDE`
  prompt, joining the symmetric set the round establishes.
- Round 3 (precedence map + ML-extension philosophy) can cite the
  data-centric framing in `experiment-lifecycle`'s opener as the
  worked example of how tier-2 extends tier-1's data-centric
  philosophy.
- Round 4 (always-on weight reduction) inherits a clean set of
  always-on guides to slim — the lifecycle trio plus the discipline
  skills — without any router noise to work around.
