---
name: catalog-operations-workflow
description: "ALWAYS use when performing Deriva catalog operations that modify data (dataset creation, splitting, ETL, feature loading, data import). Generate a committed Python script for full code provenance tracking instead of using interactive MCP tools."
user-invocable: false
disable-model-invocation: true
---

# Script-Based Workflow for Catalog Operations

For catalog operations that need to be reproducible, auditable, or shareable — dataset creation, splitting, ETL, feature creation, and data loading — use a committed script rather than interactive MCP tools.

## When to Use Scripts vs Interactive MCP

| Situation | Approach |
|-----------|----------|
| One-off exploration, quick queries, checking state | Interactive MCP tools |
| Setting descriptions, display names, annotations | Interactive MCP tools |
| Operations you'll need to reproduce or share | Committed script |
| Dataset creation, splitting, ETL, data loading | Committed script |
| Operations others need to audit or re-run | Committed script |

The key distinction: DerivaML records the git commit hash with every execution. A committed script gives the execution record a code reference that anyone can trace back. Interactive MCP operations have no such reference.

## Workflow: Develop, Test, Commit, Run

1. **Generate** a Python script in the `scripts/` directory using the DerivaML Python API. Use the base script template and common patterns from `references/script-patterns.md`.
2. **Test** with `--dry-run` to verify correctness without creating catalog records.
3. **Commit** the script so the git commit hash in the execution record points to the actual code. DerivaML enforces this: `DerivaMLDirtyWorkflowError` is raised if uncommitted changes exist. Use `--allow-dirty` only for debugging (degraded provenance).
4. **Run** for real. The execution record captures git commit hash, repository URL, input datasets and versions, output assets and datasets, and execution parameters.

For detailed script templates (base template, dataset creation, splitting, feature population, ETL), see [Script Pattern Templates](references/script-patterns.md).

## When MCP Tools Are Still Appropriate

Not everything needs a script. Use MCP tools directly for:

- **Exploratory work**: Browsing catalog structure, querying data, checking entity states
- **One-time admin tasks**: Setting descriptions, display names, annotations
- **Read-only operations**: Listing datasets, viewing features, checking versions
- **Quick debugging**: Inspecting specific records, checking execution status

## Branch Workflow and Code Provenance

DerivaML execution records capture the **git commit hash** and **repository URL** at run time. This means the branch you run from matters:

- **Worktrees and feature branches** are temporary — if deleted before merging, the commit hash in the execution record becomes unreachable, breaking the provenance link.
- **Main branch commits** are permanent — anyone can trace the execution back to the exact code.

**Recommended workflow:**

1. **Develop** scripts in a branch or worktree (iterate freely, test with `--dry-run`)
2. **Merge to main** once the script is working correctly
3. **Run for real from main** so execution records reference permanent, reachable commits
4. **Bump version** after merging, not before — the version tag should include all changes

This is especially important for:
- Dataset creation scripts that establish the foundation for downstream experiments
- ETL/data loading scripts that others will need to audit
- Any script whose execution record will be cited or shared

**What to avoid:**
- Running catalog-modifying scripts from unmerged branches — the provenance link may break
- Bumping versions before merging feature work — the tag won't include the new code
- Deleting branches that have execution records pointing to them

## When to Suggest Scripts

When a user asks to perform a data-modifying operation interactively, suggest:

> "For full provenance tracking, I recommend creating a script that we can commit. This ensures the operation is reproducible and the execution record will reference the exact code. Shall I generate the script?"

Then follow the Develop, Test, Commit, Run workflow.
