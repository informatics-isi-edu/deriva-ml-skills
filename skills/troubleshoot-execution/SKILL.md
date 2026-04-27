---
name: troubleshoot-execution
description: "ALWAYS use when a DerivaML execution fails, errors, gets stuck, or produces unexpected results. Tier-2: covers errors specific to the deriva-ml execution lifecycle (asset_file_path, upload_execution_outputs, stuck Running status, dataset version mismatch, missing features). For generic catalog errors (auth, permissions, invalid RID, missing record), see the tier-1 troubleshoot-deriva-errors skill."
user-invocable: false
disable-model-invocation: true
---

# Troubleshooting DerivaML Executions

This guide covers errors specific to the **DerivaML execution lifecycle** — the things that can only break when you're using `deriva-ml` and `deriva-ml-mcp` (Python API patterns like `ml.create_execution()`, `exe.asset_file_path()`, `exe.upload_execution_outputs()`; MCP execution-status tools; dataset versioning; feature value uploads).

> **Generic catalog errors** (auth, permissions, invalid RID, missing record, vocabulary term not found, connect failures) are NOT covered here. See the **`troubleshoot-deriva-errors`** skill in `deriva-skills` for those — those errors surface in any Deriva catalog operation and don't require the execution machinery to reproduce.

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
- With MCP tools, ensure you called `start_execution()` before attempting execution-scoped operations.
- If the execution was started but the error persists, the execution may have been stopped or may have failed. Check with resource `deriva://execution/{rid}`.

---

## Problem: "Files Not Uploaded"

**Symptom**: Execution completes but asset files are not visible in the catalog.

**Cause**: Python API `exe.upload_execution_outputs()` was not called, or files were written to the wrong path.

**Solution**:
1. Call `upload_execution_outputs()` **after** the `with` block exits in Python, not inside it. With MCP tools, call it after `stop_execution()`.
2. Ensure files are written to the **exact path** returned by `asset_file_path()`. Writing to any other directory will cause the upload to miss those files.
3. Verify the file actually exists at the path before uploading:
   ```python
   path = exe.asset_file_path("Execution_Asset", "output.csv")
   # Write file to `path`
   # Verify: os.path.exists(path) should be True
   ```
4. Check that the execution is still in `Running` status when you attempt the upload. If it was already stopped or failed, uploads will not work.

---

## Problem: "Dataset Not Found"

**Symptom**: Attempting to use a dataset RID returns an error or empty result.

**Cause**: Wrong catalog connection, dataset was deleted, or the RID is incorrect.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("your dataset description", doc_type="catalog-data")` to find datasets by description, type, or purpose. This is the best way to discover the correct RID when you are unsure.
- Verify you are connected to the correct catalog with `connect_catalog` or check the active catalog.
- Check the dataset resources to list available datasets.
- Use `validate_rids` to confirm the RID is valid and belongs to a dataset table.
- If the dataset was recently created, it should be visible immediately -- there is no propagation delay.
- If the RID resolves to a non-dataset table, that's a generic record-not-found case — see the tier-1 `troubleshoot-deriva-errors` skill.

---

## Problem: "Version Mismatch"

**Symptom**: Dataset contents do not match expectations, or a workflow references an outdated dataset version.

**Cause**: The dataset was modified after the version was pinned, or version tracking was not used.

**Solution**:
- Check the dataset's version history through the dataset resources.
- Use `increment_dataset_version` after making changes to a dataset to create a new version snapshot.
- When referencing datasets in workflows, consider pinning to a specific version.
- Use `get_dataset_spec` to see the current dataset specification and version.

---

## Problem: "Feature Not Found"

**Symptom**: Attempting to add feature values fails because the feature does not exist.

**Cause**: The feature was not created, or the name does not match exactly.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("your feature description", doc_type="catalog-schema")` to find features by name, target table, or vocabulary. This is the best way to discover exact feature names before calling tools.
- Check the feature resources to list existing features.
- Feature names are case-sensitive. Verify exact spelling.
- **Tool**: `create_feature` to create the feature if it does not exist.
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
- **Tool**: resource `deriva://execution/{rid}` to check if partial uploads succeeded.

---

## Problem: "Execution Stuck in Running"

**Symptom**: An execution shows status `Running` but the process has ended or crashed.

**Cause**: The execution context was not properly closed (e.g., crash without cleanup, not using context manager).

**Solution**:
- **Best practice**: Always use the context manager (`with ml.create_execution(config) as exe:`) which automatically handles cleanup on both success and failure.
- To fix a stuck execution manually:
  - **Tool**: `update_execution_status` with `status="Failed"` and `message="Manually marked as failed"` (or `status="Completed"` if the work actually finished).
- **Tool**: resource `deriva://execution/{rid}` to inspect the execution's current state and metadata.
- For future runs, always use the context manager to prevent this issue.

---

## Problem: "ML Vocabulary Term Not Found"

**Symptom**: An execution-related operation fails because a required vocabulary term does not exist (e.g., a missing `Workflow_Type`, `Dataset_Type`, or `Asset_Type` term).

**Cause**: The DerivaML built-in vocabulary needs to be extended with a domain-specific term.

**Solution**:
- For DerivaML built-in vocabularies, use the dedicated extender tools rather than generic `add_term`:
  - `Dataset_Type` → `create_dataset_type_term`
  - `Workflow_Type` → `add_workflow_type`
  - `Asset_Type` → `add_asset_type`
- For other vocabularies (custom domain vocabs), use `add_term`.
- For the generic "vocabulary term not found" troubleshooting flow (search-first via `rag_search`, synonym-aware lookup), see the tier-1 `troubleshoot-deriva-errors` skill.

---

## Reference Resources

- `references/execution-lifecycle.md` — Full execution lifecycle reference: workflow creation, execution configuration, upload tuning (timeouts, chunk sizes, retries), source code detection, nested executions, restoring executions, and dry run debugging. Read this for the complete execution workflow and parameter details.
- `deriva://execution/{rid}` — Inspect execution state, status, and metadata
- `deriva://storage/execution-dirs` — Check execution working directories

## General Debugging Tips (Execution-Specific)

### Inspect Execution State

- **Tool**: resource `deriva://execution/{rid}` with the execution RID to see full execution metadata, status, inputs, and outputs.
- **Tool**: Python API `exe.working_dir` to find the local working directory and inspect files directly. (No params -- operates on the active execution.)

### Review Recent Executions

- Check the recent executions resource to see the latest execution activity, statuses, and any patterns of failure.
- **Tool**: `list_nested_executions` if the execution is part of a larger workflow to see the full execution tree.
- **Tool**: resource `deriva://execution/{rid}` to find the parent execution if this is a nested step.

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
