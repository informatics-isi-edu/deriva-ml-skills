---
name: api-naming-conventions
description: "Reference for DerivaML API naming conventions — when to use lookup_ vs find_ vs list_ vs get_ vs create_ vs add_ method prefixes. Use when choosing the right method name or understanding why a method is named the way it is."
user-invocable: false
disable-model-invocation: true
---

# DerivaML API Naming Conventions

Consistent naming conventions for API methods ensure discoverability and predictable behavior. Use this reference when calling DerivaML tools or writing scripts.

> **MCP tools vs Python API**: This reference covers both **MCP tools** (available directly in Claude conversations via `deriva-mcp-core` and the `deriva-ml-mcp` plugin) and **Python API methods** (available only in Python scripts and notebooks via `from deriva_ml import DerivaML`). The distinction matters:
>
> - **MCP tools (core)**: Generic catalog operations with bare names: `add_term`, `delete_term`, `query_attribute`, `get_table_sample_data`, `get_entities`, `insert_entities`, `update_entities`, `lookup_term`. All take `hostname=` and `catalog_id=` parameters explicitly.
> - **MCP tools (deriva-ml)**: **All prefixed `deriva_ml_*`**: `deriva_ml_create_dataset`, `deriva_ml_add_dataset_members`, `deriva_ml_create_feature`, `deriva_ml_release`, etc. Same calling convention. MCP is the observation + catalog-state-mutation surface; execution authorship (the `with ml.create_execution(...) as exe:` lifecycle and `add_features` / `commit_output_assets`) lives in user-local Python via bundled script templates.
> - **Python API only**: Must be used in Python scripts or notebooks. Used for execution authorship (`create_execution`, `add_features`, `commit_output_assets`), file I/O (`asset_file_path`, `download_asset`), and any operation that needs local filesystem access. When working via MCP, use the corresponding MCP tool for the **read** side (e.g., `deriva_ml_list_datasets`, `deriva_ml_get_execution`, `rag_search()`, `query_attribute`); for the **write** side, copy a bundled script template from `skills/<name>/scripts/`.
> - **MCP resources**: Read-only data accessed via `deriva://catalog/{hostname}/{catalog_id}/...` URIs. These provide catalog state without requiring a tool call.

## Method Prefixes

### `lookup_*(identifier)` -- Single Entity by Identifier

Returns a single entity. Raises an error if not found.

| Method | Description |
|--------|-------------|
| Python API `lookup_dataset` | Find dataset by RID |
| `deriva_ml_lookup_asset` (MCP) / Python API `lookup_asset` | Find asset by RID |
| `lookup_term` (MCP, core) / Python API `lookup_term` | Find vocabulary term by name or RID |
| Python API `lookup_workflow` | Find workflow by name or RID |
| Python API `lookup_feature` | Find feature by name |

**Behavior**: Expects exactly one result. Fails loudly if the entity doesn't exist. Use when you have a known identifier and need the entity.

### `find_*(filters)` -- Search with Filters

Returns an iterable of matching entities. Empty result is valid (not an error).

| Method | Description |
|--------|-------------|
| Python API `find_datasets` | Search datasets by type, name, etc. |
| Python API `find_assets` | Search assets by type, metadata |
| Python API `find_features` | Search features by target table, vocabulary |
| `deriva_ml_find_workflow_by_url` (MCP) | Find a workflow by its URL |
| `deriva_ml_find_workflow_executions` (MCP) | Find executions of a workflow |

**Behavior**: Returns zero or more results. Use for search and discovery when you don't know the exact identifier.

### `list_*(context)` -- All Items in Context

Returns all items of a type within a given context.

| Method | Description |
|--------|-------------|
| `list_vocabulary_terms` (MCP, core) / Python API `list_vocabulary_terms` | All terms in a vocabulary |
| Python API `list_tables` | All tables in a schema |
| `deriva_ml_list_datasets` (MCP) | All datasets |
| `deriva_ml_list_workflows` (MCP) | All workflows |
| `deriva_ml_list_executions` (MCP) | All executions |
| `deriva_ml_list_features` (MCP) | All features |
| `deriva_ml_list_assets` (MCP) | All assets of a type |
| `deriva_ml_list_dataset_members` (MCP) | All members of a dataset |
| `deriva_ml_list_dataset_relations` (MCP) | All parent and child datasets of a dataset |
| `deriva_ml_list_dataset_element_types` (MCP) | All element types of a dataset |
| `deriva_ml_list_execution_children` (MCP) | All nested (descendant) executions |
| `deriva_ml_list_execution_parents` (MCP) | All ancestor executions |
| `deriva_ml_list_feature_values` (MCP) | All values for a feature |

**Behavior**: Returns a complete list. No filtering -- returns everything in scope.

### `get_*(params)` -- Data with Transformation

Returns data in a specific format or with transformation applied.

| Method | Description |
|--------|-------------|
| `query_attribute` (MCP, core) | Filtered query against any table |
| `get_table_sample_data` (MCP, core) | Get sample rows from a table |
| `get_entities` (MCP, core) | Get one or more records by filter (e.g., `filters={"RID": "..."}`) |
| `deriva_ml_get_dataset` (MCP) | Get a dataset by RID |
| `deriva_ml_get_dataset_spec` (MCP) | Get dataset specification |
| `deriva_ml_get_workflow` (MCP) | Get a workflow by RID |
| `deriva_ml_get_execution` (MCP) | Get an execution by RID |
| `deriva_ml_get_feature` (MCP) | Get a feature definition |
| `deriva_ml_bag_info` (MCP) | Get bag size and manifest preview for a dataset |
| Python API `exe.working_dir` | Get execution working directory path |

**Behavior**: Returns a specific data type or transformed view. Use when you need data in a particular format.

### `create_*(params)` -- New Entity

Creates a new entity and returns it.

| Method | Description |
|--------|-------------|
| `deriva_ml_create_dataset` (MCP) / Python API `create_dataset` | Create new dataset |
| `deriva_ml_create_workflow` (MCP) / Python API `create_workflow` | Create new workflow |
| `deriva_ml_create_feature` (MCP) / Python API `create_feature` | Create new feature |
| `create_table` (MCP, core) | Create new table |
| `deriva_ml_create_vocabulary` (MCP) | Create new vocabulary (deriva-ml-aware: applies project curie prefix, refreshes navbar) |
| Python API `ml.create_execution(config, workflow=..., dry_run=...)` | Open a new execution context manager. **No MCP equivalent** — execution authorship belongs in committed scripts; copy a template from `skills/execution-lifecycle/scripts/`. |
| Python API `exe.create_dataset(...)` inside an execution context | Create dataset linked to the execution as an output. **No MCP equivalent** for the same reason. |

**Behavior**: Creates and returns the new entity. Fails if entity already exists (where applicable).

### `add_*(target, item)` -- Add to Existing

Adds an item to an existing entity.

| Method | Description |
|--------|-------------|
| `deriva_ml_add_dataset_members` (MCP) / Python API `add_dataset_members` | Add members to a dataset |
| `deriva_ml_add_dataset_element_type` (MCP) | Add element type to dataset |
| `add_term` (MCP, core) | Add term to any vocabulary (including built-in `Dataset_Type` / `Workflow_Type` / `Asset_Type` via `schema="deriva-ml"`) |
| `add_synonym` (MCP, core) | Add synonym to term |
| Python API `exe.add_features(records)` inside an execution context | Add one or more feature values (always plural). For bulk-loading from a CSV, use `skills/create-feature/scripts/populate_feature_values.py`. **No MCP equivalent** — feature value authorship goes through the execution context manager. |
| `add_visible_column` (MCP, core) | Add column to visible columns |
| `add_visible_foreign_key` (MCP, core) | Add FK to visible foreign keys |
| `add_column` (MCP, core) | Add column to table |
| Python API `parent_exe.add_nested_execution(child_exe, sequence=...)` | Link a child execution under a parent. See `skills/execution-lifecycle/scripts/nested_execution.py`. **No MCP equivalent.** |

**Behavior**: Modifies an existing entity. Returns None.

> **Extending built-in DerivaML vocabularies** (`Workflow_Type`, `Asset_Type`, `Dataset_Type`): use the generic `add_term` with `schema="deriva-ml"` and `table=` set to the vocabulary table. To tag a specific asset with an Asset_Type, use `update_entities` on the asset's row.

> **Dataset hierarchy**: to make a dataset a child of another dataset, use `deriva_ml_add_dataset_members(parent_rid, members={"Dataset": [child_rid]})` — children are members with element-type `Dataset`.

### `delete_*` / `remove_*` -- Remove Items

Removes entities or relationships.

| Method | Description |
|--------|-------------|
| `deriva_ml_delete_dataset` (MCP) | Delete a dataset |
| `deriva_ml_delete_dataset_members` (MCP) | Remove members from dataset |
| `deriva_ml_delete_feature` (MCP) | Delete a feature |
| `delete_term` (MCP, core) | Delete vocabulary term (e.g., `delete_term(schema="deriva-ml", table="Dataset_Type", name=...)` for built-in vocabs) |
| `remove_synonym` (MCP, core) | Remove synonym from term |
| `remove_visible_column` (MCP, core) | Remove from visible columns |
| `remove_visible_foreign_key` (MCP, core) | Remove from visible FKs |

**Behavior**: Removes the specified entity or relationship. Returns None.

> **Removing terms or type associations**: use `delete_term` for vocab-term deletion (with `schema="deriva-ml"` for built-ins), or `update_entities` on the dataset/asset row to clear a type association.

### `set_*` -- Set/Update Properties

Sets a property on an existing entity. (Core annotation tools immediately apply — there is no separate staging/apply step.)

| Method | Description |
|--------|-------------|
| `set_table_description` (MCP, core) | Set table description |
| `set_column_description` (MCP, core) | Set column description |
| `set_table_display_name` (MCP, core) | Set table display name |
| `set_column_display_name` (MCP, core) | Set column display name |
| `set_row_name_pattern` (MCP, core) | Set row name display pattern |
| `set_visible_columns` (MCP, core) | Set all visible columns |
| `set_visible_foreign_keys` (MCP, core) | Set all visible FKs |
| `set_display_annotation` (MCP, core) | Set display annotation |
| `set_table_display` (MCP, core) | Set table display config |
| `set_column_display` (MCP, core) | Set column display config |
| `set_column_nullok` (MCP, core) | Set column nullability |

**Behavior**: Overwrites the specified property. Returns None.

> **Note on connection state**: Every MCP tool takes `hostname=`, `catalog_id=`, and `schema=` arguments explicitly. There is no connection state.

### `update_*(rid, ...)` -- Update Domain Entity

Updates fields on an existing DerivaML domain entity (Dataset / Workflow / Execution / Asset).

| Method | Description |
|--------|-------------|
| `deriva_ml_update_dataset` (MCP) | Update dataset description, type, etc. |
| `deriva_ml_update_workflow` (MCP) | Update workflow description, type |
| `deriva_ml_update_asset` (MCP) | Update asset metadata, including Asset_Type tagging |
| Python API `exe.update_status(target, error=...)` inside an execution context | Transition the execution's status (`ExecutionStatus.Failed`, `ExecutionStatus.Pending_Upload`, etc.). Used by `salvage_execution.py` and `crash_recovery.py`. |
| `update_entities` (MCP, core) | Generic entity update — use only when no domain wrapper exists |

## Parameter Naming

- Use semantic names: `dataset_rid`, `asset_rid`, `execution_rid`
- Table/column parameters: `table_name`, `column_name`, `feature_name`, `vocab_name`
- Boolean parameters: use positive names with `bool` type (e.g., `cache=True`, `dry_run=False`)

## Return Types Summary

| Prefix | Returns |
|--------|---------|
| `lookup_` | Single entity (raises on not found) |
| `find_` | Iterable of entities (may be empty) |
| `list_` | List or dict of entities |
| `get_` | Specific data type |
| `create_` | Created entity |
| `add_` | None |
| `delete_` / `remove_` | None |
| `set_` | None |
