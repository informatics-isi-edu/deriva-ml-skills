---
name: troubleshoot-execution
description: "ALWAYS use when a DerivaML execution fails, errors, gets stuck, or produces unexpected results. Tier-2: covers errors specific to the deriva-ml execution lifecycle (asset_file_path, upload_execution_outputs, stuck Running status, dataset version mismatch, missing features). For generic catalog errors (auth, permissions, invalid RID, missing record), see the tier-1 troubleshoot-deriva-errors skill."
user-invocable: false
disable-model-invocation: true
---

# Troubleshooting DerivaML Executions

This guide covers errors specific to the **DerivaML execution lifecycle** — the things that can only break when you're using `deriva-ml` and `deriva-ml-mcp` (Python API patterns like `ml.create_execution()`, `exe.asset_file_path()`, `exe.upload_execution_outputs()`; MCP execution-status tools; dataset versioning; feature value uploads).

> **Generic catalog errors** (auth, permissions, invalid RID, missing record, vocabulary term not found, connect failures) are NOT covered here. See the **`/deriva:troubleshoot-deriva-errors`** skill *(tier-1, deriva-skills)* for those — those errors surface in any Deriva catalog operation and don't require the execution machinery to reproduce.

## Stateless model

> The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them. Lifecycle tools also take an explicit `execution_rid` — there is no implicit "active execution".

---

## Problem: "No Active Execution"

**Symptom**: Tools that require an execution context (Python API `exe.asset_file_path()`, `exe.upload_execution_outputs()`) fail with an error about no active execution.

**Cause**: The execution was not properly started, or you are outside the execution context.

**Solution**:
- In Python, always use the context manager pattern:
  ```python
  from deriva_ml import DerivaML, ExecutionConfiguration

  with ml.create_execution(config) as exe:
      # All execution work goes here
  ```
- With MCP tools, ensure you called `deriva_ml_start_execution(hostname, catalog_id, execution_rid)` before attempting execution-scoped operations. The execution_rid must be the one returned by `deriva_ml_create_execution`.
- If the execution was started but the error persists, the execution may have been committed or aborted. Check with `deriva_ml_get_execution(hostname, catalog_id, execution_rid)`.

---

## Problem: "Files Not Uploaded"

**Symptom**: Execution completes but asset files are not visible in the catalog.

**Cause**: Python API `exe.upload_execution_outputs()` was not called, or files were written to the wrong path.

**Solution**:
1. Call `upload_execution_outputs()` **after** the `with` block exits in Python, not inside it. With MCP tools, call it after `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)`.
2. Ensure files are written to the **exact path** returned by `asset_file_path()`. Writing to any other directory will cause the upload to miss those files.
3. Verify the file actually exists at the path before uploading:
   ```python
   path = exe.asset_file_path("Execution_Asset", "output.csv")
   # Write file to `path`
   # Verify: os.path.exists(path) should be True
   ```
4. Check that the execution is still in `Running` status when you attempt the upload. If it was already committed or aborted, uploads will not work.

---

## Problem: "Dataset Not Found"

**Symptom**: Attempting to use a dataset RID returns an error or empty result.

**Cause**: Wrong catalog connection, dataset was deleted, or the RID is incorrect.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("your dataset description", doc_type="catalog-data")` to find datasets by description, type, or purpose. This is the best way to discover the correct RID when you are unsure.
- Verify you are passing the correct `hostname` and `catalog_id` arguments — the new MCP server is stateless, so any tool call against the wrong catalog will quietly miss the record.
- Call `deriva_ml_list_datasets(hostname, catalog_id)` to list available datasets.
- Confirm the RID resolves to a dataset by calling `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)`. If it errors / returns empty, the RID is wrong, the dataset was deleted, or it lives in a different catalog. The legacy `validate_rids` tool was removed; use the typed lookup instead.
- If the dataset was recently created, it should be visible immediately -- there is no propagation delay.
- If the RID resolves to a non-dataset table, that's a generic record-not-found case — see the `/deriva:troubleshoot-deriva-errors` skill *(tier-1, deriva-skills)*.

---

## Problem: "Version Mismatch"

**Symptom**: Dataset contents do not match expectations, or a workflow references an outdated dataset version.

**Cause**: The dataset was modified after the version was pinned, or version tracking was not used.

**Solution**:
- Check the dataset's version history with `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)`.
- Use `deriva_ml_increment_dataset_version(hostname, catalog_id, dataset_rid, ...)` after making changes to a dataset to create a new version snapshot.
- When referencing datasets in workflows, consider pinning to a specific version.
- Use `deriva_ml_get_dataset_spec(hostname, catalog_id, dataset_rid)` to see the current dataset specification and version.

---

## Problem: "Feature Not Found"

**Symptom**: Attempting to add feature values fails because the feature does not exist.

**Cause**: The feature was not created, or the name does not match exactly.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("your feature description", doc_type="catalog-schema")` to find features by name, target table, or vocabulary. This is the best way to discover exact feature names before calling tools.
- Call `deriva_ml_list_features(hostname, catalog_id)` to list existing features.
- Feature names are case-sensitive. Verify exact spelling with `deriva_ml_get_feature(hostname, catalog_id, target_table, feature_name)`.
- **Tool**: `deriva_ml_create_feature(hostname, catalog_id, ...)` to create the feature if it does not exist.
- Ensure the feature is associated with the correct table.

---

## Problem: "Upload Timeout"

**Symptom**: Python API `exe.upload_execution_outputs()` hangs or times out.

**Cause**: Large files, network issues, or server limits.

**Solution**:
- Check your network connectivity.
- For large files, consider breaking them into smaller batches.
- The server may have upload size limits. Check with your catalog administrator.
- Retry the upload -- transient network issues are the most common cause.
- **Tool**: `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to check if partial uploads succeeded.

---

## Problem: "Execution Stuck in Running"

**Symptom**: An execution shows status `Running` but the process has ended or crashed.

**Cause**: The execution context was not properly closed (e.g., crash without cleanup, not using context manager).

**Solution**:
- **Best practice**: Always use the context manager (`with ml.create_execution(config) as exe:`) which automatically handles cleanup on both success and failure.
- To fix a stuck execution manually, pick the right tool for the transition:
  - Failure: `deriva_ml_abort_execution(hostname, catalog_id, execution_rid, reason="<short explanation>")` — sets status to `Failed`/`Aborted`. The `reason` is recorded in the audit log and visible on the execution row.
  - Success: `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)` — sets status to `Completed`. Only use this if the work actually finished.
- **Tool**: `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to inspect the execution's current state and metadata.
- For future runs, always use the context manager to prevent this issue.

---

## Problem: "ML Vocabulary Term Not Found"

**Symptom**: An execution-related operation fails because a required vocabulary term does not exist (e.g., a missing `Workflow_Type`, `Dataset_Type`, or `Asset_Type` term).

**Cause**: The DerivaML built-in vocabulary needs to be extended with a domain-specific term.

**Solution**:
- All DerivaML built-in vocabularies live in the `deriva-ml` schema and are extended with the generic `add_term` tool — the legacy dedicated extender tools (`create_dataset_type_term`, `add_workflow_type`, `add_asset_type`) were removed.
  - `Dataset_Type` → `add_term(hostname, catalog_id, schema="deriva-ml", table="Dataset_Type", name=..., description=...)`
  - `Workflow_Type` → `add_term(hostname, catalog_id, schema="deriva-ml", table="Workflow_Type", name=..., description=...)`
  - `Asset_Type` → `add_term(hostname, catalog_id, schema="deriva-ml", table="Asset_Type", name=..., description=...)`
- For other vocabularies (custom domain vocabs), use `add_term` with the appropriate schema and table.
- For the generic "vocabulary term not found" troubleshooting flow (search-first via `rag_search`, synonym-aware lookup), see the `/deriva:troubleshoot-deriva-errors` skill *(tier-1, deriva-skills)*.

---

## Problem: "I Need to Resume an Aborted Execution"

**Symptom**: An execution failed or was aborted. You want to pick up from where it left off.

**Cause**: This is a known gap, not an error — the legacy `restore_execution` tool has **no equivalent** in the new MCP surface.

**Solution (workaround):**

1. **Inspect the prior execution.** Call `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to retrieve the workflow RID, dataset RIDs, asset RIDs, and description from the original execution.
2. **Decide whether to retry.** If the failure was transient (network, timeout) re-running with the same config makes sense. If it was a code or config bug, fix it first.
3. **Create a fresh execution.** Call `deriva_ml_create_execution(hostname, catalog_id, ...)` with the same workflow, dataset_rids, and asset_rids. This creates a new execution record with a new RID — the prior aborted execution remains in its terminal state for provenance.
4. **Continue the lifecycle as normal.** `deriva_ml_start_execution` → do the work → `deriva_ml_commit_execution`.

**Note:** This means the new execution's RID is different from the old one. If you need to relate them, capture both RIDs in your experiment notes (see the `maintain-experiment-notes` skill) — the catalog itself does not link aborted executions to their re-run replacements.

---

## Reference Resources

- `references/execution-lifecycle.md` — Full execution lifecycle reference: workflow creation, execution configuration, upload tuning (timeouts, chunk sizes, retries), source code detection, nested executions, the re-run-after-abort workaround, and dry run debugging. Read this for the complete execution workflow and parameter details.
- `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` — Inspect execution state, status, and metadata
- `deriva://storage/execution-dirs` — Check execution working directories

## General Debugging Tips (Execution-Specific)

### Inspect Execution State

- **Tool**: `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` to see full execution metadata, status, inputs, and outputs.
- **Tool**: Python API `exe.working_dir` to find the local working directory and inspect files directly.

### Review Recent Executions

- Call `deriva_ml_list_executions(hostname, catalog_id)` to see the latest execution activity, statuses, and any patterns of failure.
- **Tool**: `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)` to see descendants if the execution is the parent of a multirun or pipeline.
- **Tool**: `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)` to find ancestors if this is a nested step.

### Verify Working Directory

- **Tool**: Python API `exe.working_dir` returns the local filesystem path for the active execution.
- Inspect this directory to verify:
  - Input files were downloaded correctly.
  - Output files were written to the correct locations.
  - No unexpected files or directory structures.

### Clean Up

- **Resource**: Read `deriva://storage/execution-dirs` to list local execution working directories. Remove unneeded directories manually to free disk space.

## Related Skills

- **`troubleshoot-deriva-errors`** *(tier-1, deriva-skills)* — Generic catalog errors (auth, permissions, invalid RID, missing record, vocabulary term not found, connect failures). Always check this first if the error doesn't smell execution-specific — many "execution failures" are actually catalog-state issues.
- **`execution-lifecycle`** *(tier-2)* — The forward path: how to start, monitor, and complete executions correctly.
- **`dataset-lifecycle`** *(tier-2)* — Dataset versioning context for the "Version Mismatch" problem.
