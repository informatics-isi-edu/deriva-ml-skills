---
name: api-naming-conventions
description: "Reference for DerivaML API naming conventions — when to use lookup_ vs find_ vs list_ vs get_ vs create_ vs add_ method prefixes. Use when choosing the right method name or understanding why a method is named the way it is."
user-invocable: false
disable-model-invocation: true
---

# DerivaML API Naming Conventions

Consistent naming conventions for API methods ensure discoverability and predictable behavior. Use this reference when calling DerivaML tools or writing scripts.

> **MCP tools vs Python API**: This reference covers both **MCP tools** (available directly in Claude conversations via the Deriva MCP server) and **Python API methods** (available only in Python scripts and notebooks via `from deriva_ml import DerivaML`). The distinction matters:
>
> - **MCP tools**: Can be called interactively during a Claude session. These appear in the tool tables below without any qualifier (e.g., `create_dataset`, `add_term`, `preview_table`).
> - **Python API only**: Must be used in Python scripts or notebooks. These are marked with "Python API" in the tables below (e.g., `lookup_dataset`, `find_datasets`, `list_vocabulary_terms`, `list_tables`). When working via MCP, use the corresponding MCP resource or tool instead (e.g., `deriva://catalog/datasets` resource, `rag_search()`, `preview_table`).
> - **MCP resources**: Read-only data accessed via `deriva://...` URIs. These provide catalog state without requiring a tool call (e.g., `deriva://dataset/{rid}/members`, `deriva://catalog/schema`).

## Method Prefixes

### `lookup_*(identifier)` -- Single Entity by Identifier

Returns a single entity. Raises an error if not found.

| Method | Description |
|--------|-------------|
| `lookup_dataset` | Find dataset by RID |
| `lookup_asset` | Find asset by RID |
| `lookup_term` | Find vocabulary term by name or RID |
| `lookup_workflow` | Find workflow by name or RID |
| `lookup_feature` | Find feature by name |

**Behavior**: Expects exactly one result. Fails loudly if the entity doesn't exist. Use when you have a known identifier and need the entity.

### `find_*(filters)` -- Search with Filters

Returns an iterable of matching entities. Empty result is valid (not an error).

| Method | Description |
|--------|-------------|
| `find_datasets` | Search datasets by type, name, etc. |
| `find_assets` | Search assets by type, metadata |
| `find_features` | Search features by target table, vocabulary |

**Behavior**: Returns zero or more results. Use for search and discovery when you don't know the exact identifier.

### `list_*(context)` -- All Items in Context

Returns all items of a type within a given context.

| Method | Description |
|--------|-------------|
| `list_vocabulary_terms` | All terms in a vocabulary |
| `list_tables` | All tables in a schema |
| `list_assets` | All assets of a type |
| resource `deriva://dataset/{rid}/members` | All members of a dataset |
| `list_dataset_parents` | All parent datasets |
| resource `deriva://dataset/{rid}` | All child datasets |
| `list_nested_executions` | All nested executions |
| resource `deriva://execution/{rid}` | All parent executions |

**Behavior**: Returns a complete list. No filtering -- returns everything in scope.

### `get_*(params)` -- Data with Transformation

Returns data in a specific format or with transformation applied.

| Method | Description |
|--------|-------------|
| `preview_table` | Get table schema/definition |
| `get_table_sample_data` | Get sample rows from a table |
| `get_record` | Get a specific record by RID |
| `get_dataset_spec` | Get dataset specification |
| resource `deriva://execution/{rid}` | Get execution details |
| Python API `exe.working_dir` | Get execution working directory path |

**Behavior**: Returns a specific data type or transformed view. Use when you need data in a particular format.

### `create_*(params)` -- New Entity

Creates a new entity and returns it.

| Method | Description |
|--------|-------------|
| `create_dataset` | Create new dataset |
| `create_workflow` | Create new workflow |
| `create_feature` | Create new feature |
| `create_table` | Create new table |
| `create_vocabulary` | Create new vocabulary |
| `create_execution` | Create new execution |
| `create_execution_dataset` | Create dataset from execution outputs |

**Behavior**: Creates and returns the new entity. Fails if entity already exists (where applicable).

### `add_*(target, item)` -- Add to Existing

Adds an item to an existing entity.

| Method | Description |
|--------|-------------|
| `add_dataset_members` | Add members to a dataset |
| `add_dataset_type` | Add a type to a dataset |
| `add_dataset_element_type` | Add element type to dataset |
| `add_dataset_child` | Add child relationship |
| `add_asset_type` | Add type to asset table |
| `add_asset_type_to_asset` | Assign type to specific asset |
| `add_term` | Add term to vocabulary |
| `add_synonym` | Add synonym to term |
| `add_feature_value` | Add feature value |
| `add_feature_value_record` | Add individual feature value record |
| `add_visible_column` | Add column to visible columns |
| `add_visible_foreign_key` | Add FK to visible foreign keys |
| `add_column` | Add column to table |
| `add_nested_execution` | Add nested execution |
| `add_workflow_type` | Add workflow type |

**Behavior**: Modifies an existing entity. Returns None.

### `delete_*` / `remove_*` -- Remove Items

Removes entities or relationships.

| Method | Description |
|--------|-------------|
| `delete_dataset` | Delete a dataset |
| `delete_dataset_members` | Remove members from dataset |
| `delete_dataset_type_term` | Remove type from dataset |
| `delete_feature` | Delete a feature |
| `delete_term` | Delete vocabulary term |
| `remove_asset_type_from_asset` | Remove type from asset |
| `remove_dataset_type` | Remove dataset type |
| `remove_synonym` | Remove synonym from term |
| `remove_visible_column` | Remove from visible columns |
| `remove_visible_foreign_key` | Remove from visible FKs |

**Behavior**: Removes the specified entity or relationship. Returns None.

### `set_*` -- Set/Update Properties

Sets a property on an existing entity.

| Method | Description |
|--------|-------------|
| `set_table_description` | Set table description |
| `set_column_description` | Set column description |
| `set_table_display_name` | Set table display name |
| `set_column_display_name` | Set column display name |
| `set_row_name_pattern` | Set row name display pattern |
| `set_visible_columns` | Set all visible columns |
| `set_visible_foreign_keys` | Set all visible FKs |
| `set_dataset_description` | Set dataset description |
| `set_execution_description` | Set execution description |
| `set_workflow_description` | Set workflow description |
| `set_display_annotation` | Set display annotation |
| `set_table_display` | Set table display config |
| `set_column_display` | Set column display config |
| `set_column_nullok` | Set column nullability |
| `set_default_schema` | Set default schema |
| `set_active_catalog` | Set active catalog |

**Behavior**: Overwrites the specified property. Returns None.

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
