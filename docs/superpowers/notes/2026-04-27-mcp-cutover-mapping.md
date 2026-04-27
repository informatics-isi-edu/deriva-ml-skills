# Legacy `deriva-mcp` → New `deriva-mcp-core` + `deriva-ml-mcp` Cut-Over Mapping

**Date:** 2026-04-27
**Context:** Phase 4 of the deriva-skills two-plugin restructure (see `../plans/2026-04-27-skills-restructure.md`). This doc is the authoritative rename / removal table that the Phase 4 sweep applies across all 37 skills (14 tier-1 + 23 tier-2).

## Architectural shifts (apply to every skill)

| Concept | Legacy (deriva-mcp) | New (deriva-mcp-core) |
|---|---|---|
| **Connection management** | Stateful: `connect_catalog(hostname, catalog_id, ...)` once, then bare tool calls | **Stateless**: every tool takes `hostname=` and `catalog_id=` arguments explicitly. **No** `connect_catalog`, `disconnect_catalog`, `set_active_catalog`, or `set_default_schema`. |
| **Annotation editing** | Stage edits locally + `apply_annotations()` to commit | **Immediate apply** via `model.apply()` underlying every annotation-mutating tool. **No** `apply_annotations` or `apply_catalog_annotations`. |
| **Active-catalog state** | "active connection" + "active catalog" concepts in skill prompts | Skills should drop "ensure you're connected" preludes and always show full `hostname=` and `catalog_id=` parameters. |
| **Domain plugin separation** | All ML-domain tools bare (no prefix) | **All deriva-ml-mcp tools prefixed `deriva_ml_*`** to prevent collision with sibling plugins. |

## Core tool renames (deriva-mcp-core)

These are the renames that apply across both tiers when skills reference generic catalog operations:

| Legacy (deriva-mcp) | New (deriva-mcp-core) | Notes |
|---|---|---|
| `connect_catalog(hostname, catalog_id, ...)` | (removed; pass `hostname=`, `catalog_id=` to every tool) | Every example needs rewriting |
| `disconnect_catalog()` | (removed) | Drop from skill prompts |
| `set_active_catalog(...)` | (removed) | Drop from skill prompts |
| `set_default_schema(schema)` | (removed; pass schema names explicitly per-tool) | Skill examples that relied on a "default schema" need explicit schema args |
| `preview_table(table_name, ...)` | `query_attribute(hostname, catalog_id, schema, table, ...)` for filtered queries; `get_table_sample_data(hostname, catalog_id, schema, table)` for unfiltered samples | Two split replacements; pick by use case |
| `get_record(table_name, rid)` | `get_entities(hostname, catalog_id, schema, table, filter={"RID": rid})` | RID becomes a filter, not a positional arg |
| `validate_rids(rids)` | `get_entities(...)` with check on returned rows | No dedicated tool; use generic entity fetch |
| `insert_records(table_name, records)` | `insert_entities(hostname, catalog_id, schema, table, entities=[...])` | Renamed; arg shape unchanged |
| `update_record(table_name, record)` | `update_entities(hostname, catalog_id, schema, table, entities=[...])` | Renamed; arg shape unchanged |
| `apply_annotations()` | (removed; immediate apply) | Drop the staging step from any annotation example |
| `apply_catalog_annotations()` | (removed; immediate apply) | Same |

## DerivaML domain tool renames (deriva-ml-mcp; all prefixed)

The full bare-name → prefixed-name mapping for the 39 deriva-ml-mcp tools. Apply by word-boundary regex.

### Read tools

| Legacy | New |
|---|---|
| `get_dataset(rid)` | `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)` |
| `get_dataset_spec(rid)` | `deriva_ml_get_dataset_spec(hostname, catalog_id, dataset_rid)` |
| `get_execution(rid)` | `deriva_ml_get_execution(hostname, catalog_id, execution_rid)` |
| `get_workflow(rid)` | `deriva_ml_get_workflow(hostname, catalog_id, workflow_rid)` |
| `get_feature(table, name)` | `deriva_ml_get_feature(hostname, catalog_id, target_table, feature_name)` |
| `list_datasets()` | `deriva_ml_list_datasets(hostname, catalog_id, ...)` |
| `list_workflows()` | `deriva_ml_list_workflows(hostname, catalog_id, ...)` |
| `list_executions()` | `deriva_ml_list_executions(hostname, catalog_id, ...)` |
| `list_features()` | `deriva_ml_list_features(hostname, catalog_id, ...)` |
| `list_dataset_members(rid)` | `deriva_ml_list_dataset_members(hostname, catalog_id, dataset_rid)` |
| `list_dataset_relations(rid)` | `deriva_ml_list_dataset_relations(hostname, catalog_id, dataset_rid)` |
| `list_dataset_element_types(rid)` | `deriva_ml_list_dataset_element_types(hostname, catalog_id, dataset_rid)` |
| `list_execution_children(rid)` | `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)` |
| `list_execution_parents(rid)` | `deriva_ml_list_execution_parents(hostname, catalog_id, execution_rid)` |
| `list_feature_values(table, name)` | `deriva_ml_list_feature_values(hostname, catalog_id, target_table, feature_name, selector=...)` |
| `list_assets(...)` | `deriva_ml_list_assets(hostname, catalog_id, ...)` |
| `list_asset_tables()` | `deriva_ml_list_asset_tables(hostname, catalog_id)` |
| `lookup_asset(...)` | `deriva_ml_lookup_asset(hostname, catalog_id, ...)` |
| `find_workflow_by_url(url)` | `deriva_ml_find_workflow_by_url(hostname, catalog_id, url)` |
| `find_workflow_executions(workflow_rid)` | `deriva_ml_find_workflow_executions(hostname, catalog_id, workflow_rid)` |
| `bag_info(rid)` | `deriva_ml_bag_info(hostname, catalog_id, dataset_rid)` |
| `denormalize_dataset(rid)` | `deriva_ml_denormalize_dataset(hostname, catalog_id, dataset_rid)` |

### Mutation tools

| Legacy | New |
|---|---|
| `create_dataset(...)` | `deriva_ml_create_dataset(hostname, catalog_id, ...)` |
| `update_dataset(...)` | `deriva_ml_update_dataset(hostname, catalog_id, ...)` |
| `delete_dataset(rid)` | `deriva_ml_delete_dataset(hostname, catalog_id, dataset_rid)` |
| `add_dataset_members(rid, members)` | `deriva_ml_add_dataset_members(hostname, catalog_id, dataset_rid, members)` |
| `delete_dataset_members(rid, members)` | `deriva_ml_delete_dataset_members(hostname, catalog_id, dataset_rid, members)` |
| `add_dataset_element_type(rid, table)` | `deriva_ml_add_dataset_element_type(hostname, catalog_id, dataset_rid, element_table)` |
| `increment_dataset_version(rid, ...)` | `deriva_ml_increment_dataset_version(hostname, catalog_id, dataset_rid, ...)` |
| `cache_dataset(rid)` | `deriva_ml_cache_dataset(hostname, catalog_id, dataset_rid)` |
| `split_dataset(rid, ...)` | `deriva_ml_split_dataset(hostname, catalog_id, dataset_rid, ...)` |
| `create_workflow(...)` | `deriva_ml_create_workflow(hostname, catalog_id, ...)` |
| `update_workflow(...)` | `deriva_ml_update_workflow(hostname, catalog_id, ...)` |
| `create_execution(config)` | `deriva_ml_create_execution(hostname, catalog_id, ...)` |
| `start_execution(rid)` | `deriva_ml_start_execution(hostname, catalog_id, execution_rid)` |
| `commit_execution(rid)` | `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)` |
| `abort_execution(rid)` | `deriva_ml_abort_execution(hostname, catalog_id, execution_rid)` |
| `update_execution(rid, ...)` | `deriva_ml_update_execution(hostname, catalog_id, execution_rid, ...)` |
| `add_nested_execution(parent, child)` | `deriva_ml_add_nested_execution(hostname, catalog_id, parent_rid, child_rid)` |
| `create_execution_dataset(...)` | `deriva_ml_create_execution_dataset(hostname, catalog_id, ...)` |
| `create_feature(...)` | `deriva_ml_create_feature(hostname, catalog_id, ...)` |
| `delete_feature(table, name)` | `deriva_ml_delete_feature(hostname, catalog_id, target_table, feature_name)` |
| `add_feature_values(table, name, values)` | `deriva_ml_add_feature_values(hostname, catalog_id, target_table, feature_name, values)` |
| `update_asset(rid, ...)` | `deriva_ml_update_asset(hostname, catalog_id, asset_rid, ...)` |

### Maintenance tools (v1.1, v1.4)

| Legacy | New |
|---|---|
| (n/a) | `deriva_ml_reindex_vocabularies(hostname, catalog_id, vocab=None)` |
| (n/a) | `deriva_ml_resync_indexes(hostname, catalog_id, target=None)` |

## Legacy tools with NO new equivalent (workarounds)

These tools existed in legacy but were not ported. Skills that referenced them must be rewritten.

| Legacy tool | What it did | Workaround in new surface | Status |
|---|---|---|---|
| `add_asset_type(name, ...)` | Extends `Asset_Type` vocab with a domain-specific type | `add_term(hostname, catalog_id, schema="deriva-ml", table="Asset_Type", name=..., description=..., synonyms=[...])` | Generic `add_term` works |
| `add_workflow_type(name, ...)` | Extends `Workflow_Type` vocab | `add_term(..., schema="deriva-ml", table="Workflow_Type", ...)` | Generic `add_term` works |
| `create_dataset_type_term(name, ...)` | Extends `Dataset_Type` vocab | `add_term(..., schema="deriva-ml", table="Dataset_Type", ...)` | Generic `add_term` works |
| `delete_dataset_type_term(name)` | Removes a `Dataset_Type` term | `delete_term(..., schema="deriva-ml", table="Dataset_Type", name=...)` | Generic `delete_term` works |
| `remove_dataset_type(rid, type)` | Untag a dataset from a type | `update_entities(...)` on the dataset's type-association table | Manual; deriva-ml-mcp-#?? to file |
| `add_asset_type_to_asset(asset_rid, type)` | Tag an asset with a type | `update_entities(...)` on the asset row's `Asset_Type` column | Manual |
| `remove_asset_type_from_asset(asset_rid, type)` | Untag an asset | `update_entities(...)` clearing the `Asset_Type` column | Manual |
| `create_asset_table(name, ...)` | DDL for an asset table with hatrac column + standard annotations | `create_table(...)` + manual hatrac column setup + manual `Asset_Type` FK + manual annotations | **Real gap** — file upstream issue |
| `restore_execution(rid)` | Resume an aborted execution | (no equivalent) | **Real gap** — file upstream issue |
| `add_dataset_child(parent, child)` | Add a dataset as child of another | `deriva_ml_add_dataset_members(parent_rid, [child_rid])` (children are members of element-type Dataset) | Slight semantic shift; document in skill |
| `list_dataset_parents(rid)` | List parent datasets of a child | `deriva_ml_list_dataset_relations(rid)` (returns both directions) | Renamed/generalized |
| `list_nested_executions(rid)` | List executions nested under a parent | `deriva_ml_list_execution_children(rid)` (descendants); `deriva_ml_list_execution_parents(rid)` (ancestors) | Split into two |
| `list_asset_executions(rid)` | List executions that produced an asset | `deriva_ml_lookup_asset(asset_rid)` returns producer; `deriva_ml_find_workflow_executions(...)` for the broader query | Different shape |
| `lookup_workflow_by_url(url)` | Find a Workflow by its URL | `deriva_ml_find_workflow_by_url(url)` | Renamed |
| `preview_denormalized_dataset(rid)` | Get a wide-table view of a dataset | `deriva_ml_denormalize_dataset(rid)` | Renamed |
| `bag_info(rid)` | Bag size + manifest preview | `deriva_ml_bag_info(rid)` | Renamed (with prefix) |
| `estimate_bag_size(rid)` | Just the size estimate | `deriva_ml_bag_info(rid)` (subsumed) | Subsumed |
| `set_dataset_description(rid, desc)` | Set just the description column | `deriva_ml_update_dataset(rid, description=desc)` | Subsumed by update |
| `set_execution_description(rid, desc)` | Same for execution | `deriva_ml_update_execution(rid, description=desc)` | Subsumed |
| `set_workflow_description(rid, desc)` | Same for workflow | `deriva_ml_update_workflow(rid, description=desc)` | Subsumed |
| `update_execution_status(rid, status, ...)` | Set execution status + message | `deriva_ml_update_execution(rid, status=..., message=...)` | Subsumed; OR for the standard transitions, use `deriva_ml_commit_execution` / `deriva_ml_abort_execution` |
| `add_feature_value(...)` | Single value | `deriva_ml_add_feature_values(...)` (plural; pass a single-element list) | Renamed + made plural |
| `add_feature_value_record(...)` | Same | `deriva_ml_add_feature_values(...)` | Subsumed |
| `stop_execution(rid)` | Mark execution stopped | `deriva_ml_commit_execution(rid)` for success; `deriva_ml_abort_execution(rid)` for failure | **Split** — pick the right one |
| `invalidate_cache()` | Clear client-side cache | (removed; no client-side caching in mcp-core) | Drop from skill |
| `list_cached_results()` | List cached results | (removed) | Drop from skill |
| `query_cached_result(...)` | Re-query a cached result | (removed) | Drop from skill |
| `list_catalog_registry(hostname)` | List catalogs on a host | `get_catalog_info(hostname, catalog_id)` per-catalog; or `get_catalog_history_bounds(hostname, catalog_id)` | Different shape |

## Resource URI changes

Resource URIs in skills also need rewriting. The most common patterns:

| Legacy URI | New URI |
|---|---|
| `deriva://catalog/connections` | (removed; no connection state to inspect) |
| `deriva://catalog/vocabularies` | (per-catalog; use `catalog_schema(hostname, catalog_id)` then filter for vocab tables) |
| `deriva://vocabulary/{name}` | (per-catalog; use `list_vocabulary_terms(hostname, catalog_id, schema, table)`) |
| `deriva://vocabulary/{name}/{term}` | `lookup_term(hostname, catalog_id, schema, table, name)` |
| `deriva://catalog/datasets` | `deriva://catalog/{h}/{c}/ml/datasets` |
| `deriva://dataset/{rid}` | `deriva://catalog/{h}/{c}/ml/dataset/{rid}` |
| `deriva://catalog/workflows` | `deriva://catalog/{h}/{c}/ml/workflows` |
| `deriva://workflow/{rid}` | `deriva://catalog/{h}/{c}/ml/workflow/{rid}` |
| `deriva://catalog/executions` | `deriva://catalog/{h}/{c}/ml/executions` |
| `deriva://execution/{rid}` | `deriva://catalog/{h}/{c}/ml/execution/{rid}` |
| `deriva://catalog/dataset-types`, `/workflow-types` | `deriva://catalog/{h}/{c}/ml/registries` |
| `deriva://server/version` | `server_status(hostname=None)` tool returns the same info |

## Application strategy

For each skill SKILL.md and references/*.md:

1. **Drop the connect step** — every "Prerequisite: Connect to a Catalog" section comes out. Replace with: "every tool call below takes `hostname=` and `catalog_id=` parameters; substitute your catalog's values."
2. **Apply core tool renames** — `preview_table` → `query_attribute`/`get_table_sample_data`, `get_record` → `get_entities`, etc.
3. **Apply `deriva_ml_*` prefix** — every bare ml-domain tool name gets the prefix.
4. **Update URIs** — apply the URI mapping table above.
5. **Drop annotation staging** — any "stage edits then `apply_annotations()`" pattern becomes immediate apply.
6. **Document gaps** — for the two real gaps (`restore_execution`, `create_asset_table`), add a workaround note + cross-reference to the upstream issue.
7. **Update steering callouts** — `deriva-ml-context` and `manage-vocabulary` steering principles need to drop the dedicated extender tool names that no longer exist; replace with "use generic `add_term` on the named vocabulary".
