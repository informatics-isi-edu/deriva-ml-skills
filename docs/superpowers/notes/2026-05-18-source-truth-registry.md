# Source-truth registry — 2026-05-18

Canonical reference of every API surface skills in this plugin are
allowed to mention. Built directly from `deriva-ml` HEAD and
`deriva-ml-mcp` HEAD via AST inspection — no human transcription of
signatures, no copy-paste from old docs.

**Maintenance rule.** When upstream changes land, refresh this file
*first*, then update any skill that mentions a changed entry. Skills
must not mention anything that isn't in this registry. The
`scripts/check_drift.py` cross-reference detector enforces tool/prompt
names — but signature drift is the maintainer's responsibility, and
this file is the source of truth.

**Update mechanics**: re-run the extraction commands at the bottom
of this file against current upstream HEAD. Diff the output, update
this file, then sweep any newly-stale skill mentions.

---

## Section A — MCP tools (43 entries: 41 tools + 2 prompts)

Every entry below was extracted by AST-walking `deriva-ml-mcp/src/`
for `@ctx.tool` and `@ctx.prompt` decorators on `deriva_ml_*` names.

### A.1 Tools — read-only (28)

| Tool | Signature | Source |
|---|---|---|
| `deriva_ml_bag_info` | `(hostname, catalog_id, dataset_rid, version, exclude_tables=None)` | read.py:741 |
| `deriva_ml_bootstrap_config` | `(hostname, catalog_id, kinds=None, dataset_type_filter=None)` | read.py:1096 |
| `deriva_ml_denormalize_dataset` | `(hostname, catalog_id, include_tables, dataset_rid=None, version=None, row_per=None, via=None, limit, after_rid=None, preflight_count=False)` | complex.py:88 |
| `deriva_ml_find_workflow_by_url` | `(hostname, catalog_id, url_or_checksum)` | workflow.py:293 |
| `deriva_ml_find_workflow_executions` | `(hostname, catalog_id, workflow_rid, status=None, limit, after_rid=None, preflight_count=False, sort=False)` | read.py:537 |
| `deriva_ml_get_dataset` | `(hostname, catalog_id, dataset_rid, include_history=False)` | read.py:365 |
| `deriva_ml_get_dataset_spec` | `(hostname, catalog_id, dataset_rid, version=None)` | read.py:801 |
| `deriva_ml_get_execution` | `(hostname, catalog_id, execution_rid)` | read.py:492 |
| `deriva_ml_get_feature` | `(hostname, catalog_id, table, feature_name)` | feature.py:222 |
| `deriva_ml_get_lineage` | `(hostname, catalog_id, rid, depth=None, max_executions)` | read.py:756 |
| `deriva_ml_get_workflow` | `(hostname, catalog_id, workflow_rid)` | workflow.py:249 |
| `deriva_ml_list_assets` | `(hostname, catalog_id, asset_table, limit, after_rid=None, preflight_count=False)` | asset.py:234 |
| `deriva_ml_list_dataset_element_types` | `(hostname, catalog_id)` | read.py:689 |
| `deriva_ml_list_dataset_members` | `(hostname, catalog_id, dataset_rid, element_table=None, limit, after_rid=None, preflight_count=False, recurse=False, version=None)` | read.py:446 |
| `deriva_ml_list_dataset_relations` | `(hostname, catalog_id, dataset_rid, direction: 'parents'\|'children'\|'both', recurse=False, limit, after_rid=None, version=None)` | read.py:573 |
| `deriva_ml_list_datasets` | `(hostname, catalog_id, include_deleted=False, limit, after_rid=None, preflight_count=False, sort=False)` | read.py:239 |
| `deriva_ml_list_execution_children` | `(hostname, catalog_id, execution_rid, recurse=False)` | read.py:632 |
| `deriva_ml_list_execution_parents` | `(hostname, catalog_id, execution_rid, recurse=False)` | read.py:697 |
| `deriva_ml_list_executions` | `(hostname, catalog_id, workflow_rid=None, workflow_type=None, status=None, limit, after_rid=None, preflight_count=False, sort=False)` | read.py:389 |
| `deriva_ml_list_feature_values` | `(hostname, catalog_id, table, feature_name, selector: 'none'\|'newest'\|'first'\|'latest'\|'majority_vote'\|'by_workflow'\|'by_execution', selector_workflow=None, selector_execution_rid=None, dataset_rid=None, limit, after_rid=None, preflight_count=False, execution_rids=None, max_results)` | feature.py:292 |
| `deriva_ml_list_features` | `(hostname, catalog_id, table=None, limit, after_rid=None, preflight_count=False)` | feature.py:140 |
| `deriva_ml_list_workflows` | `(hostname, catalog_id, limit, after_rid=None, preflight_count=False, sort=False)` | workflow.py:167 |
| `deriva_ml_lookup_asset` | `(hostname, catalog_id, asset_rid)` | asset.py:333 |
| `deriva_ml_validate_config_file` | `(hostname, catalog_id, file_contents)` | read.py:1013 |
| `deriva_ml_validate_dataset_specs` | `(hostname, catalog_id, specs)` | read.py:861 |
| `deriva_ml_validate_execution_configuration` | `(hostname, catalog_id, config)` | read.py:929 |

### A.2 Tools — mutating (13)

| Tool | Signature | Source |
|---|---|---|
| `deriva_ml_add_dataset_element_type` | `(hostname, catalog_id, table_name)` | mutate.py:637 |
| `deriva_ml_add_dataset_members` | `(hostname, catalog_id, dataset_rid, member_rids=None, members_by_table=None, description, execution_rid=None)` | mutate.py:246 |
| `deriva_ml_create_dataset` | `(hostname, catalog_id, execution_rid, dataset_types=None, description, version=None)` | mutate.py:85 |
| `deriva_ml_create_feature` | `(hostname, catalog_id, target_table, feature_name, terms=None, assets=None, metadata=None, optional=None, comment)` | feature.py:520 |
| `deriva_ml_create_vocabulary` | `(hostname, catalog_id, vocab_name, comment, schema=None, update_navbar=True)` | vocabulary.py:62 |
| `deriva_ml_create_workflow` | `(hostname, catalog_id, name, workflow_type, url, checksum=None, version=None, description)` | workflow.py:357 |
| `deriva_ml_delete_dataset` | `(hostname, catalog_id, dataset_rid, recurse=False)` | mutate.py:174 |
| `deriva_ml_delete_dataset_members` | `(hostname, catalog_id, dataset_rid, member_rids, description, execution_rid=None)` | mutate.py:365 |
| `deriva_ml_delete_feature` | `(hostname, catalog_id, table, feature_name)` | feature.py:608 |
| `deriva_ml_reindex_vocabularies` | `(hostname, catalog_id, vocab=None)` | maintenance.py:66 |
| `deriva_ml_release` | `(hostname, catalog_id, dataset_rid, bump: 'major'\|'minor'\|'patch', description, execution_rid=None)` | mutate.py:693 |
| `deriva_ml_resync_indexes` | `(hostname, catalog_id, target=None)` | maintenance.py:130 |
| `deriva_ml_update_asset` | `(hostname, catalog_id, asset_rid, asset_types=None, description=None)` | asset.py:408 |
| `deriva_ml_update_dataset` | `(hostname, catalog_id, dataset_rid, dataset_types=None, description=None)` | mutate.py:457 |
| `deriva_ml_update_workflow` | `(hostname, catalog_id, workflow_rid, description=None, workflow_type=None)` | workflow.py:552 |

### A.3 Prompts (2)

| Prompt | Source |
|---|---|
| `deriva_ml_concepts` | prompts.py:1000 |
| `deriva_ml_getting_started` | prompts.py:1011 |

### A.4 Tools that DO NOT EXIST — never reference these

The following names appear in older skill text but are NOT registered
in current `deriva-ml-mcp`. Skills must not name any of them:

- `deriva_ml_create_execution`
- `deriva_ml_start_execution`
- `deriva_ml_commit_execution`
- `deriva_ml_abort_execution`
- `deriva_ml_update_execution`
- `deriva_ml_add_feature_values`
- `deriva_ml_create_execution_dataset`
- `deriva_ml_add_nested_execution`
- `deriva_ml_cache_dataset`
- `deriva_ml_split_dataset`
- `deriva_ml_increment_dataset_version`
- `deriva_ml_resume_execution`

The replacement pattern for any of these is **a runnable script
template** under `skills/<name>/scripts/` that uses the Python API
from §B. See §C for the canonical script-template shape.

---

## Section B — Python API surface

Only the methods listed here are public. Anything not listed should
not appear in skill text. Names prefixed with `_` are private and
must never appear in skill examples.

### B.1 `DerivaML` (entry-point class)

Construct via `DerivaML(host, catalog_id, ...)` or `from_context()`.

**Catalog / connection:**
- `instantiate(cls, config: DerivaMLConfig) -> Self`
- `from_context(cls, path=None) -> Self`
- `mode() -> ConnectionMode` (property)
- `catalog_snapshot(version_snapshot) -> Self`
- `is_snapshot() -> bool`

**Schema:**
- `refresh_schema(force=False) -> None`
- `pin_schema(reason=None) -> SchemaDiff | None`
- `unpin_schema() -> None`
- `pin_status() -> PinStatus`
- `diff_schema() -> SchemaDiff`

**Cache + storage:**
- `cache_table(table_name, force=False) -> pd.DataFrame`
- `download_dir(cached=True) -> Path`
- `clear_cache(older_than_days=None) -> dict[str, int]`
- `get_cache_size() -> dict[str, int | float]`
- `list_execution_dirs() -> list[dict]`
- `clean_execution_dirs(older_than_days=None, exclude_rids=None) -> dict[str, int]`
- `get_storage_summary() -> dict`

**Citation / URL:**
- `chaise_url(table) -> str`
- `cite(entity, current=False) -> str`
- `catalog_provenance() -> CatalogProvenance | None`
- `apply_catalog_annotations(navbar_brand_text=..., head_title=...) -> None`

### B.2 ExecutionMixin (methods on `DerivaML`)

- `create_execution(configuration=None, datasets=None, assets=None, workflow=None, description=None, dry_run=False) -> Execution`
- `lookup_execution(execution_rid: RID) -> ExecutionRecord`
- `list_executions(status=None, workflow_rid=None, mode=None, since=None) -> list[ExecutionSnapshot]`
- `find_executions(workflow=None, workflow_type=None, status=None, sort=None) -> Iterable[ExecutionRecord]`
- `find_incomplete_executions() -> list[ExecutionSnapshot]`
- `resume_execution(execution_rid: RID) -> Execution`
- `gc_executions(older_than=None, status=None, delete_working_dir=False) -> int`
- `lookup_experiment(execution_rid) -> Experiment`
- `find_experiments(workflow_rid=None, status=None) -> Iterable[Experiment]`
- `pending_summary() -> WorkspacePendingSummary`
- `upload_pending(execution_rids=None, retry_failed=False) -> UploadReport`
- `lookup_lineage(rid, depth=None, max_executions) -> LineageResult`

### B.3 DatasetMixin (methods on `DerivaML`)

- `find_datasets(deleted=False, sort=None) -> Iterable[Dataset]`
- `lookup_dataset(dataset, deleted=False) -> Dataset`
- `delete_dataset(dataset, recurse=False) -> None`
- `list_dataset_element_types() -> Iterable[Table]`
- `add_dataset_element_type(element) -> Table`
- `download_dataset_bag(dataset: DatasetSpec) -> DatasetBag`
- `cache_dataset(dataset: DatasetSpec, materialize=True) -> dict`
- `estimate_bag_size(dataset: DatasetSpec) -> dict`
- `bag_info(dataset: DatasetSpec) -> dict`
- `estimate_denormalized_size(include_tables) -> dict`
- `validate_dataset_specs(specs) -> DatasetSpecValidationReport`
- `validate_execution_configuration(config) -> ExecutionConfigurationValidationReport`
- `validate_config_file(path) -> ConfigValidationReport`
- `validate_config_directory(configs_dir, recursive=False) -> ConfigValidationReport`
- `bootstrap_config(kinds=None, dataset_type_filter=None) -> BootstrapReport`

### B.4 WorkflowMixin (methods on `DerivaML`)

- `create_workflow(name, workflow_type, description) -> Workflow`
- `find_workflows(sort=None) -> list[Workflow]`
- `lookup_workflow(rid) -> Workflow`
- `lookup_workflow_by_url(url_or_checksum) -> Workflow`

### B.5 FeatureMixin (methods on `DerivaML`)

- `create_feature(target_table, feature_name, terms=None, assets=None, metadata=None, optional=None, comment, update_navbar=True) -> type[FeatureRecord]`
- `feature_record_class(table, feature_name) -> type[FeatureRecord]`
- `delete_feature(table, feature_name) -> bool`
- `lookup_feature(table, feature_name) -> Feature`
- `find_features(table=None) -> list[Feature]`
- `add_features() -> int`  *(prefer the Execution method form: `exe.add_features(records)`)*
- `feature_values(table, feature_name, selector=None, materialize_limit=None, execution_rids=None) -> Iterable[FeatureRecord]`
- `list_workflow_executions(workflow) -> list[str]`

### B.6 AssetMixin (methods on `DerivaML`)

- `create_asset(asset_name, column_defs=None, fkey_defs=None, referenced_tables=None, comment, schema=None, update_navbar=True) -> Table`
- `list_assets(asset_table) -> list[Asset]`
- `list_asset_executions(asset_rid, asset_role=None) -> list[ExecutionRecord]`
- `lookup_asset(asset_rid) -> Asset`
- `list_asset_tables() -> list[Table]`
- `find_assets(asset_table=None, asset_type=None) -> Iterable[Asset]`
- `asset_record_class(asset_table_name) -> type`

### B.7 AnnotationMixin (methods on `DerivaML`)

- `get_table_annotations(table) -> dict`
- `get_column_annotations(table, column_name) -> dict`
- `set_display_annotation(table, annotation=None, column_name=None) -> str`
- `set_visible_columns(table, annotation=None) -> str`
- `set_visible_foreign_keys(table, annotation=None) -> str`
- `set_table_display(table, annotation=None) -> str`
- `set_column_display(table, column_name, annotation=None) -> str`
- `apply_annotations() -> None`
- `set_strict_preallocated_rid(table, strict=True) -> str`
- `is_strict_preallocated_rid(table) -> bool`
- `add_visible_column(table, context, column, position=None) -> list`
- `remove_visible_column(table, context, column) -> list`
- `reorder_visible_columns(table, context, new_order) -> list`
- `add_visible_foreign_key(table, context, foreign_key, position=None) -> list`
- `remove_visible_foreign_key(table, context, foreign_key) -> list`
- `reorder_visible_foreign_keys(table, context, new_order) -> list`
- `get_handlebars_template_variables(table) -> dict`

### B.8 VocabularyMixin (methods on `DerivaML`)

- `create_vocabulary(vocab_name, comment, schema=None, update_navbar=True) -> Table`
- `add_term(table, term_name, description, synonyms=None, exists_ok=False) -> VocabularyTermHandle`
- `lookup_term(table, term_name) -> VocabularyTermHandle`
- `list_vocabulary_terms(table) -> list[VocabularyTerm]`
- `delete_term(table, term_name) -> None`
- `clear_vocabulary_cache(table=None) -> None`

### B.9 `Execution` (context-manager class)

Always use as `with ml.create_execution(...) as exe:`. Public methods:

**Lifecycle:**
- `update_status(target: ExecutionStatus, error=None) -> None`
- `execution_start() -> None`  *(usually called by `__enter__`)*
- `execution_stop() -> None`  *(usually called by `__exit__`)*
- `abort() -> None`
- `is_nested() -> bool`
- `is_parent() -> bool`
- `add_nested_execution(nested_execution, sequence=None) -> None`
- `execute() -> Execution`

**Properties (read-only):**
- `status -> ExecutionStatus`
- `error -> str | None`
- `start_time -> datetime | None`
- `stop_time -> datetime | None`
- `working_dir -> Path`
- `catalog -> DerivaML`
- `datasets -> DatasetCollection`
- `uploaded_assets -> dict[str, list[AssetFilePath]]`
- `execution_record -> ExecutionRecord | None`
- `database_catalog -> DerivaMLBagView | None`

**Inputs:**
- `download_asset(asset_rid, dest_dir=None, update_catalog=False, use_cache=True, _asset_table=None) -> AssetFilePath`
- `download_dataset_bag(dataset: DatasetSpec) -> DatasetBag`
- `list_input_datasets() -> list[Dataset]`
- `list_assets(asset_role=None) -> list[Asset]`

**Output staging:**
- `add_features(features: list[FeatureRecord]) -> int`
- `add_files(files, dataset_types=None, description) -> Dataset`
- `create_dataset(dataset_types=None, version=None, description) -> Dataset`
- `asset_file_path(asset_name, file_name, asset_types=None, copy_file, rename_file=None, metadata, description=None) -> AssetFilePath`
- `metrics_file(filename='metrics.jsonl') -> AssetFilePath`
- `table_path(table) -> Path`

**Upload (post-`with`):**
- `upload_outputs(retry_failed=False) -> UploadReport`  *(canonical name)*
- `upload_execution_outputs(clean_folder=None, progress_callback=None) -> dict[str, list[AssetFilePath]]`  *(retained for back-compat; prefer `upload_outputs`)*
- `pending_summary() -> PendingSummary`

### B.10 `ExecutionRecord` (live catalog-backed)

Returned by `lookup_execution()`, `find_executions()`, `asset.list_executions()`, etc. Live, mutable, ERMrest-backed.

- `workflow -> Workflow | None` (property)
- `workflow_rid -> RID | None` (property)
- `status -> ExecutionStatus` (property; settable)
- `description -> str | None` (property; settable)
- `update_status(status: ExecutionStatus, status_detail) -> None`
- `is_nested() -> bool`
- `is_parent() -> bool`
- `list_execution_children(recurse=False) -> Iterable[ExecutionRecord]`
- `list_execution_parents(recurse=False) -> Iterable[ExecutionRecord]`
- `add_nested_execution(child, sequence=None) -> None`
- `list_input_datasets() -> list[Dataset]`
- `list_assets(asset_role=None) -> list[Asset]`

### B.11 `ExecutionSnapshot` (frozen value object)

Returned by `ml.list_executions()` and `ml.find_incomplete_executions()`. SQLite-backed frozen Pydantic model. Use for inspection of stored state; switch to `Execution.from_registry()` (or the snapshot's own helpers) for actions.

- `from_row(cls, row, pending_rows, failed_rows, pending_files, failed_files) -> ExecutionSnapshot`
- `pending_summary(ml) -> PendingSummary`
- `upload_outputs(ml, retry_failed=False) -> UploadReport`
- `update_status(target, ml, error=None) -> None`

### B.12 `Dataset` (catalog-backed)

- `description -> str` (property; settable)
- `dataset_types -> list[str]` (property)
- `current_version -> DatasetVersion` (property)
- `release(bump: VersionPart, description, execution=None) -> DatasetVersion`
- `mark_dev(description, execution=None) -> None`
- `is_dirty() -> bool`
- `release_diff() -> dict[str, int]`
- `compare_versions(v_a, v_b) -> dict[str, int]`
- `add_dataset_members(members, validate=True, description=None, execution_rid=None) -> None`
- `delete_dataset_members(members, description, execution_rid=None) -> None`
- `add_dataset_type(dataset_type) -> None`
- `remove_dataset_type(dataset_type) -> None`
- `add_dataset_types(dataset_types) -> None`
- `list_dataset_element_types() -> Iterable[Table]`
- `list_dataset_members(recurse=False, limit=None, version=None) -> dict[str, list[dict]]`
- `list_dataset_parents(recurse=False, version=None) -> list[Self]`
- `list_dataset_children(recurse=False, version=None) -> list[Self]`
- `list_executions() -> list[Execution]`
- `list_members(table) -> list[str]`
- `find_features(table=None) -> Iterable[Feature]`
- `lookup_feature(table, feature_name) -> Feature`
- `feature_values(table, feature_name, selector=None, materialize_limit=None, execution_rids=None) -> Iterable[FeatureRecord]`
- `download_dataset_bag(version, materialize=True, use_minid=False, exclude_tables=None, timeout=None, fetch_concurrency) -> DatasetBag`
- `cache(version, materialize=True, exclude_tables=None, timeout=None, fetch_concurrency) -> dict`
- `bag_info(version, exclude_tables=None) -> dict`
- `estimate_bag_size(version, exclude_tables=None) -> dict`
- `get_denormalized_as_dataframe(include_tables, row_per=None, via=None, ignore_unrelated_anchors=False, version=None) -> pd.DataFrame`
- `get_denormalized_as_dict(include_tables, ...) -> Generator[dict]`
- `cache_denormalized(include_tables, version=None, force=False, ...) -> pd.DataFrame`
- `list_denormalized_columns(include_tables, row_per=None, via=None, version=None) -> list[tuple]`
- `describe_denormalized(include_tables, ...) -> dict`
- `list_schema_paths(tables=None, version=None) -> dict`
- `dataset_history() -> list[DatasetHistory]`
- `get_chaise_url() -> str`
- `to_markdown(show_children=False, indent=0) -> str`
- `display_markdown(show_children=False, indent=0) -> None`

### B.13 `DatasetBag` (downloaded, SQLite-backed)

Returned by `dataset.download_dataset_bag(...)` and `exe.download_dataset_bag(...)`.

- `path -> Path` (property)
- `current_version -> DatasetVersion` (property)
- `list_tables() -> list[str]`
- `get_table_as_dict(table) -> Generator[dict]`
- `get_table_as_dataframe(table) -> pd.DataFrame`
- `list_dataset_members(recurse=False, limit=None) -> dict[str, list[dict]]`
- `list_dataset_parents(recurse=False) -> list[Self]`
- `list_dataset_children(recurse=False) -> list[Self]`
- `list_dataset_element_types() -> Iterable[Table]`
- `list_executions() -> list[RID]`
- `find_features(table=None) -> Iterable[Feature]`
- `lookup_feature(table, feature_name) -> Feature`
- `feature_values(table, feature_name, selector=None, materialize_limit=None, execution_rids=None) -> Iterable[FeatureRecord]`
- `list_workflow_executions(workflow) -> list[str]`
- `dataset_history() -> list[DatasetHistory]`
- `get_denormalized_as_dataframe(include_tables, row_per=None, via=None, ignore_unrelated_anchors=False) -> pd.DataFrame`
- `get_denormalized_as_dict(include_tables, ...) -> Generator[dict]`
- `list_denormalized_columns(include_tables, ...) -> list[tuple]`
- `describe_denormalized(include_tables, ...) -> dict`
- `list_schema_paths(tables=None) -> dict`
- `as_torch_dataset(element_type, sample_loader=None, transform=None, targets=None, target_transform=None, missing='unknown') -> torch.utils.data.Dataset`
- `as_tf_dataset(element_type, sample_loader=None, transform=None, targets=None, target_transform=None, missing='unknown', output_signature=None) -> tf.data.Dataset`
- `restructure_assets(output_dir, asset_table=None, targets=None, target_transform=None, missing='unknown', use_symlinks=True, type_selector=None, type_to_dir_map=None, enforce_vocabulary=True, file_transformer=None) -> dict[Path, Path]`

### B.14 Methods that DO NOT EXIST — never reference these

These names appear in older skill text but are NOT in the current
public Python API. Skills must not name any of them:

- `ml.prefetch_dataset(...)` — use `ml.cache_dataset(spec)`
- `ml.list_foreign_keys(...)` — no replacement; the operation had no callers
- `ml.add_page(...)`, `ml.user_list(...)`, `ml.globus_login(...)` — removed
- `ml.cache_features(...)` — use `ml.feature_values(...)`
- `ml.increment_dataset_version(...)` — use `dataset.release(bump=..., description=..., execution=...)`
- `ml.retrieve_rid(...)` — use `ml.resolve_rid(...)`
- `ml.add_workflow(...)` — use `ml.create_workflow(...)`
- `ml.start_upload(...)`, `ml.domain_path(...)`, `ml.table_path(...)` — private now
- `AssetRIDConfig` — never existed; the real classes are `AssetSpec` (runtime Pydantic) and `AssetSpecConfig` (hydra-zen)
- `Status.<lowercase>` — replaced by `ExecutionStatus.<TitleCase>` (see §D.1)

---

## Section C — Resource URIs (18 entries)

Resource templates that the MCP server publishes. Skills may
reference these by exact template — clients resolve the `{...}`
placeholders.

### C.1 Static (no parameters)

- `deriva://deriva-ml/concepts`
- `deriva://deriva-ml/getting-started`

### C.2 Parameterized

- `deriva://catalog/{hostname}/{catalog_id}/ml/asset/{asset_rid}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/assets/{schema}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/assets/{schema}/{asset_table}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/dataset/{dataset_rid}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/dataset/{dataset_rid}/bag-preview`
- `deriva://catalog/{hostname}/{catalog_id}/ml/dataset/{dataset_rid}/members`
- `deriva://catalog/{hostname}/{catalog_id}/ml/dataset/{dataset_rid}/spec`
- `deriva://catalog/{hostname}/{catalog_id}/ml/datasets`
- `deriva://catalog/{hostname}/{catalog_id}/ml/execution/{execution_rid}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/executions`
- `deriva://catalog/{hostname}/{catalog_id}/ml/features/{table_name}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/lineage/{rid}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/vocabularies/{schema}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/vocabularies/{schema}/{vocab_name}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/workflow/{workflow_rid}`
- `deriva://catalog/{hostname}/{catalog_id}/ml/workflows`

---

## Section D — Enums, exceptions, controlled vocabularies

### D.1 `ExecutionStatus` (StrEnum)

Title-case values (no lowercase form exists):
- `ExecutionStatus.Created` = `"Created"`
- `ExecutionStatus.Running` = `"Running"`
- `ExecutionStatus.Stopped` = `"Stopped"`
- `ExecutionStatus.Failed` = `"Failed"`
- `ExecutionStatus.Pending_Upload` = `"Pending_Upload"`
- `ExecutionStatus.Uploaded` = `"Uploaded"`
- `ExecutionStatus.Aborted` = `"Aborted"`

Legal transitions:
- `Created → Running → {Stopped, Failed} → Pending_Upload → {Uploaded, Failed}`
- `Created → Aborted`
- `Running → Aborted`
- `Running → Pending_Upload` (crash-recovery direct transition; legal)

### D.2 `ConnectionMode` (StrEnum)

- `ConnectionMode.online` = `"online"` (default; full network)
- `ConnectionMode.offline` = `"offline"` (read-only; cached schema; mutations raise `DerivaMLReadOnlyError`)

Construct via `DerivaML(host, catalog_id, mode=ConnectionMode.offline)`.

### D.3 `MLVocab` (StrEnum — vocabulary table names)

- `MLVocab.dataset_type` = `"Dataset_Type"`
- `MLVocab.workflow_type` = `"Workflow_Type"`
- `MLVocab.asset_type` = `"Asset_Type"`
- `MLVocab.asset_role` = `"Asset_Role"`
- `MLVocab.execution_status` = `"Execution_Status"`
- `MLVocab.feature_name` = `"Feature_Name"`

### D.4 `ExecMetadataType` (StrEnum — execution-metadata asset types)

- `ExecMetadataType.execution_config` = `"Execution_Config"`
- `ExecMetadataType.runtime_env` = `"Runtime_Env"`
- `ExecMetadataType.hydra_config` = `"Hydra_Config"`
- `ExecMetadataType.deriva_config` = `"Deriva_Config"`
- `ExecMetadataType.metrics_file` = `"Metrics_File"`  *(use `Execution.metrics_file()` to write metrics)*

### D.5 Asset-role auto-tags

Every execution-linked asset carries:
- `Asset_Role` ∈ {`"Input"`, `"Output"`} (column on `Execution_<AssetTable>` association)
- `Asset_Type` containing the directional tag (`"Input_File"` or `"Output_File"`) in its list

DerivaML assigns both; callers must not supply them. Skills filtering
on `asset_types` should never assume the list contains only domain
types — the directional tag is always present too.

### D.6 Exception hierarchy

Root: `DerivaMLException(Exception)`

**Configuration tree:**
- `DerivaMLConfigurationError`
- `DerivaMLSchemaError`
- `DerivaMLSchemaRefreshBlocked`
- `DerivaMLSchemaPinned`
- `DerivaMLAuthenticationError`
- `DerivaMLOfflineError`

**Data tree:**
- `DerivaMLDataError`
- `DerivaMLNotFoundError`
- `DerivaMLDatasetNotFound`
- `DerivaMLTableNotFound`
- `DerivaMLFeatureNotFound`
- `DerivaMLInvalidTerm`
- `DerivaMLRidsNotFound` (carries `missing_rids: set[str]`)
- `DerivaMLTableTypeError`
- `DerivaMLValidationError`
- `DerivaMLMaterializeLimitExceeded` (carries `actual_count`, `limit`)
- `DerivaMLCycleError`
- `DerivaMLStateInconsistency`

**Execution tree:**
- `DerivaMLExecutionError`
- `DerivaMLWorkflowError`
- `DerivaMLDirtyWorkflowError`
- `DerivaMLUploadError`

**Other:**
- `DerivaMLReadOnlyError` (raised by `CatalogStub` when offline + write attempted)
- `DerivaMLDenormalizeError` (+ 5 subclasses for path-planner errors)

Selector / association exceptions raised inside vocabulary + feature code:
- `NoAssociationException` (subclass of `DerivaMLNotFoundError`)
- `AmbiguousAssociationException` (subclass of `DerivaMLDataError`; carries `count`)

---

## Section E — Canonical patterns (skill-text reference)

### E.1 The bundled-script-template pattern

For any operation that creates / mutates an execution (was: removed
MCP execution-mutating tools), skills must route the LLM to a
bundled script template under `skills/<name>/scripts/<task>.py`,
*not* generate inline Python in the model turn. Rationale: a
workflow's URL + checksum must resolve to **committed** code for
provenance to mean anything; inline-generated Python has no URL.

Canonical template skeleton (this is what every bundled template
should look like; bullets are the things that vary per task):

```python
#!/usr/bin/env python3
"""<one-line task description>.

<3-5 lines explaining when to use, what it produces, and how to
adapt the parameters.>
"""

from __future__ import annotations

import argparse
import sys
from deriva_ml import DerivaML
from deriva_ml.execution import ExecutionConfiguration
# import any task-specific helpers


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--hostname", required=True)
    p.add_argument("--catalog-id", required=True)
    p.add_argument("--workflow-type", required=True)
    p.add_argument("--dry-run", action="store_true",
                   help="Validate without making catalog changes.")
    # ... task-specific arguments
    args = p.parse_args()

    ml = DerivaML(args.hostname, args.catalog_id)

    workflow = ml.create_workflow(
        name="<task name>",
        workflow_type=args.workflow_type,
        description="<task description>",
    )

    config = ExecutionConfiguration(
        description="<execution description>",
    )

    with ml.create_execution(config, workflow=workflow,
                             dry_run=args.dry_run) as execution:
        # task-specific work using `execution` and `ml`
        # e.g. execution.add_features(records)
        #      execution.create_dataset(...)
        ...

    # Upload happens AFTER the with block.
    execution.upload_outputs()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Standard CLI conventions:
- `--hostname` and `--catalog-id` always required
- `--dry-run` mandatory (validate without writing)
- Task-specific arguments named after their semantic role
- No hardcoded host / catalog / vocab values
- Workflow type passed in, not hardcoded
- `execution.upload_outputs()` AFTER the `with` block, never inside

### E.2 MCP-tool vs Python boundary

| Surface | Used for | Example |
|---|---|---|
| **MCP tools** (§A) | Observation: read catalogs, datasets, workflows, executions, features, lineage. Stateless; safe to call from any LLM turn. | `deriva_ml_list_executions(workflow_type='Training')` |
| **Bundled script templates** (§E.1) | Authorship: create executions, stage feature values, upload outputs, cache bags. Committed code → workflow URL + checksum resolve. | `uv run python src/scripts/train_model.py --dry-run` |

---

## Section F — How to regenerate this registry

When upstream changes land, refresh this file:

```bash
# 1. MCP tools + prompts
cd /Users/carl/GitHub/DerivaML/deriva-ml-mcp
python3 -c '
import ast
from pathlib import Path
src = Path("src/deriva_ml_mcp")
for py in sorted(src.rglob("*.py")):
    try: tree = ast.parse(py.read_text())
    except SyntaxError: continue
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
        if not node.name.startswith("deriva_ml_"): continue
        for deco in node.decorator_list:
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute):
                if deco.func.attr in ("tool", "prompt"):
                    args = node.args.args + node.args.kwonlyargs
                    sig = "(" + ", ".join(a.arg for a in args) + ")"
                    print(f"{deco.func.attr:6s} {node.name}{sig}  [{py.name}:{node.lineno}]")
'

# 2. Resource URIs
grep -rh "@ctx.resource" src/deriva_ml_mcp/ | sed -E 's/.*"([^"]+)".*/\1/' | sort -u

# 3. Python public API
cd /Users/carl/GitHub/DerivaML
# (run the script in §A's "How I built this" block)

# 4. Exceptions
grep -E "^class Deriva[A-Z]" src/deriva_ml/core/exceptions.py

# 5. Enums
grep -A 30 "class ExecutionStatus\|class MLVocab\|class ExecMetadataType\|class ConnectionMode" src/deriva_ml/core/enums.py src/deriva_ml/execution/state_store.py src/deriva_ml/core/connection_mode.py
```

If any output diverges from what's recorded above, **update the
registry first, then sweep affected skills**. The registry is
authoritative; the skill text describes only what the registry
says exists.
