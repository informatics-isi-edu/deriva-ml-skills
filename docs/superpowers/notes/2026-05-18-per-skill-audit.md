# Per-skill audit — 2026-05-24 refresh

Deterministic cross-reference of every skill file against the source-truth
registry (`2026-05-18-source-truth-registry.md`). Produced by AST-derived
rule sets, not LLM judgment.

**2026-05-24:** Re-run against deriva-ml v1.39 (ADR-0009 unifies the four
legacy upload entry points into `commit_output_assets`). `upload_outputs`
and `upload_pending` added to the not-public list; `version-reference`
and `ADR-reference` added to the HIST-PROSE detector to catch any "v1.39+"
or "per ADR-0009" prose that should be replaced with clean-start text.

## Finding kinds

- **REMOVED-TOOL** — references an MCP tool name in registry §A.4
- **REMOVED-PY** — references a Python method name in registry §B.14 (not public API)
- **SIG_DRIFT** — invokes a current method with stale kwargs
- **LOWER-STATUS** — lowercase `ExecutionStatus` value (§D.1 specifies TitleCase)
- **OLD-STATUS-ENUM** — references the removed `Status.<lowercase>` enum
- **HIST-PROSE** — historical framing ("was X", "(formerly…)", "legacy", "v1.39+", "per ADR-0009", etc.)

All finding kinds are equal-priority. The skills' job is to describe the
current API, no history.

## Summary

- **Skills with findings:** 18 of 29
- **Total findings:** 349

### Per-skill finding counts (sorted by total)

| Skill | Total | Breakdown |
|---|---:|---|
| `execution-lifecycle` | 94 | HIST-PROSE=20, REMOVED-TOOL=74 |
| `dataset-lifecycle` | 48 | HIST-PROSE=27, REMOVED-PY=7, REMOVED-TOOL=9, SIG_DRIFT=5 |
| `troubleshoot-execution` | 46 | HIST-PROSE=16, OLD-STATUS-ENUM=2, REMOVED-TOOL=28 |
| `ml-data-engineering` | 30 | HIST-PROSE=1, SIG_DRIFT=29 |
| `create-feature` | 29 | HIST-PROSE=2, REMOVED-PY=1, REMOVED-TOOL=24, SIG_DRIFT=2 |
| `work-with-assets` | 28 | HIST-PROSE=15, REMOVED-TOOL=8, SIG_DRIFT=5 |
| `deriva-ml-context` | 18 | HIST-PROSE=6, REMOVED-TOOL=12 |
| `manage-storage` | 12 | HIST-PROSE=2, REMOVED-TOOL=9, SIG_DRIFT=1 |
| `model-development-workflow` | 11 | HIST-PROSE=4, REMOVED-TOOL=7 |
| `api-naming-conventions` | 10 | HIST-PROSE=3, REMOVED-TOOL=7 |
| `write-hydra-config` | 5 | HIST-PROSE=5 |
| `generate-scripts` | 4 | REMOVED-PY=4 |
| `new-model` | 4 | SIG_DRIFT=4 |
| `debug-bag-contents` | 3 | HIST-PROSE=3 |
| `generate-descriptions` | 3 | HIST-PROSE=2, REMOVED-TOOL=1 |
| `run-notebook` | 2 | HIST-PROSE=1, REMOVED-TOOL=1 |
| `compare-model-runs` | 1 | REMOVED-TOOL=1 |
| `configure-experiment` | 1 | HIST-PROSE=1 |

### Clean skills (zero findings)

- `browse-erd`
- `catalog-operations-workflow`
- `create-web-app`
- `experiment-lifecycle`
- `help`
- `maintain-experiment-notes`
- `setup-derivaml-project`
- `setup-ml-catalog`
- `setup-notebook-environment`
- `using-deriva-mcp`
- `validate-project-setup`

---

## Findings detail

### `api-naming-conventions`

- `api-naming-conventions/SKILL.md:15` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > > - **MCP tools (deriva-ml)**: **All prefixed `deriva_ml_*`**: `deriva_ml_create_dataset`, `deriva_ml_add_dataset_member
- `api-naming-conventions/SKILL.md:101` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > | `deriva_ml_create_execution` (MCP) / Python API `create_execution` | Create new execution |
- `api-naming-conventions/SKILL.md:102` **REMOVED-TOOL** — `deriva_ml_create_execution_dataset`
  > | `deriva_ml_create_execution_dataset` (MCP) | Create dataset from execution outputs |
- `api-naming-conventions/SKILL.md:116` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > | `deriva_ml_add_feature_values` (MCP) / Python API `add_feature_values` | Add one or more feature values (always plural
- `api-naming-conventions/SKILL.md:120` **REMOVED-TOOL** — `deriva_ml_add_nested_execution`
  > | `deriva_ml_add_nested_execution` (MCP) | Add a child execution under a parent |
- `api-naming-conventions/SKILL.md:166` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > > **Note on description setters**: The legacy `set_dataset_description` / `set_workflow_description` / `set_execution_de
- `api-naming-conventions/SKILL.md:166` **HIST-PROSE** — `legacy-marker`
  > > **Note on description setters**: The legacy `set_dataset_description` / `set_workflow_description` / `set_execution_de
- `api-naming-conventions/SKILL.md:168` **HIST-PROSE** — `legacy-marker`
  > > **Note on connection state**: The legacy `set_default_schema` and `set_active_catalog` are gone — every MCP tool now t
- `api-naming-conventions/SKILL.md:172` **HIST-PROSE** — `legacy-marker`
  > Updates fields on an existing DerivaML domain entity (Dataset / Workflow / Execution / Asset). Replaces the legacy singl
- `api-naming-conventions/SKILL.md:178` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > | `deriva_ml_update_execution` (MCP) | Update execution description, status, message (replaces `update_execution_status`

### `compare-model-runs`

- `compare-model-runs/SKILL.md:352` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > 4. **Do NOT** call `deriva_ml_update_execution(status=..., message=...)` to record metrics — that tool only accepts `des

### `configure-experiment`

- `configure-experiment/references/workflow.md:252` **HIST-PROSE** — `legacy-marker`
  > - The legacy `list_nested_executions` tool was split into the two `_children` / `_parents` calls above

### `create-feature`

- `create-feature/SKILL.md:126` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > | Adding values without an execution | Error — provenance required | `deriva_ml_create_execution` + `deriva_ml_start_exe
- `create-feature/SKILL.md:126` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > | Adding values without an execution | Error — provenance required | `deriva_ml_create_execution` + `deriva_ml_start_exe
- `create-feature/SKILL.md:132` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > | Forgetting `deriva_ml_commit_execution` | Execution stays "running" | Always commit (or `deriva_ml_abort_execution` on
- `create-feature/SKILL.md:132` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > | Forgetting `deriva_ml_commit_execution` | Execution stays "running" | Always commit (or `deriva_ml_abort_execution` on
- `create-feature/SKILL.md:233` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > `deriva_ml_add_feature_values(hostname, catalog_id, table, feature_name, execution_rid, entries=[...])` writes values di
- `create-feature/SKILL.md:233` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > `deriva_ml_add_feature_values(hostname, catalog_id, table, feature_name, execution_rid, entries=[...])` writes values di
- `create-feature/SKILL.md:242` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > deriva_ml_create_execution(hostname, catalog_id, workflow_rid="<wf_rid>")
- `create-feature/SKILL.md:245` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > deriva_ml_add_feature_values(hostname, catalog_id,
- `create-feature/SKILL.md:253` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > # and auto-commits on exit. No separate deriva_ml_commit_execution needed.
- `create-feature/SKILL.md:273` **REMOVED-PY** — `cache_features`
  > For the exploratory-preview MCP tool examples and the full Python API retrieval pattern (`ml.cache_features`, `ml.fetch_
- `create-feature/SKILL.md:293` **HIST-PROSE** — `ADR-reference`
  > - **Dataset versioning** — adding feature values to dataset members does NOT automatically flip the dataset to a dev ver
- `create-feature/references/concepts.md:287` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > When using `deriva_ml_add_feature_values`, optional columns can be:
- `create-feature/references/concepts.md:296` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > deriva_ml_add_feature_values(
- `create-feature/references/concepts.md:442` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"], value_selector=select_highest_confidence,
- `create-feature/references/concepts.md:526` **HIST-PROSE** — `ADR-reference`
  > Adding feature values to records in a dataset does NOT automatically update existing released versions. Released version
- `create-feature/references/concepts.md:587` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > | Add values | `deriva_ml_add_feature_values` | `exe.add_features()` | Plural — pass single-element list for one value |
- `create-feature/references/feature-selectors.md:71` **SIG_DRIFT** — `restructure_assets(value_selector=) → fold into targets={feature: selector}`
  > value_selector=FeatureRecord.select_newest,
- `create-feature/references/workflow.md:77` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > Then call `deriva_ml_create_execution(hostname=..., catalog_id=..., workflow_rid=<workflow_rid>, description=...)`.
- `create-feature/references/workflow.md:79` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > Then call `deriva_ml_start_execution(hostname=..., catalog_id=..., execution_rid=<execution_rid>)`.
- `create-feature/references/workflow.md:81` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > **Step 2:** Add values using `deriva_ml_add_feature_values` (one tool — singular vs multi-column shape was unified):
- `create-feature/references/workflow.md:89` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > **Step 3:** Call `deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid=<execution_rid>)` to finalize. 
- `create-feature/references/workflow.md:89` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > **Step 3:** Call `deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid=<execution_rid>)` to finalize. 
- `create-feature/references/workflow.md:89` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > **Step 3:** Call `deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid=<execution_rid>)` to finalize. 
- `create-feature/references/workflow.md:91` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > > `deriva_ml_add_feature_values` (plural) handles both single and multi-column feature values. Pass a single-element lis
- `create-feature/references/workflow.md:199` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > Call `deriva_ml_create_execution(hostname="data.example.org", catalog_id="1", workflow_rid="<workflow_rid>", description
- `create-feature/references/workflow.md:201` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > Call `deriva_ml_start_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")`.
- `create-feature/references/workflow.md:203` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > Call `deriva_ml_add_feature_values(hostname="data.example.org", catalog_id="1", table="Image", feature_name="Cell_Classi
- `create-feature/references/workflow.md:205` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > Call `deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")` to final
- `create-feature/references/workflow.md:205` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > Call `deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")` to final

### `dataset-lifecycle`

- `dataset-lifecycle/SKILL.md:97` **HIST-PROSE** — `ADR-reference`
  > Datasets carry a **two-state PEP 440 version** per [ADR-0003](https://github.com/informatics-isi-edu/deriva-ml/blob/main
- `dataset-lifecycle/SKILL.md:217` **REMOVED-PY** — `cache_features`
  > - `references/curated-subsets.md` — Phase 3b workflow: filter types, scaffolding, the 8-step subset workflow, `cache_fea
- `dataset-lifecycle/references/bags.md:82` **HIST-PROSE** — `ADR-reference`
  > - To capture recent changes, mutate the dataset (which lands on a dev version per ADR-0003), then call `deriva_ml_releas
- `dataset-lifecycle/references/bags.md:131` **HIST-PROSE** — `legacy-marker`
  > Call `deriva_ml_bag_info` with `hostname`, `catalog_id`, `dataset_rid`, and `version`. Returns row counts, asset file si
- `dataset-lifecycle/references/bags.md:258` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],     # create subdirs by label
- `dataset-lifecycle/references/bags.md:281` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `dataset-lifecycle/references/bags.md:293` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `dataset-lifecycle/references/bags.md:311` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `dataset-lifecycle/references/bags.md:340` **HIST-PROSE** — `legacy-marker`
  > | `deriva_ml_bag_info` | Preview row counts, asset sizes per table, and manifest (subsumes legacy estimate_bag_size) |
- `dataset-lifecycle/references/concepts.md:115` **HIST-PROSE** — `legacy-marker`
  > Custom types are created using the generic `add_term` tool on the `Dataset_Type` vocabulary (the legacy `create_dataset_
- `dataset-lifecycle/references/concepts.md:220` **HIST-PROSE** — `legacy-marker`
  > > Note: the legacy `add_dataset_child(parent, child)` shortcut was removed. Children are now members of the parent's ele
- `dataset-lifecycle/references/concepts.md:266` **HIST-PROSE** — `ADR-reference`
  > ## Dataset Versioning (ADR-0003 dev/release model)
- `dataset-lifecycle/references/concepts.md:268` **HIST-PROSE** — `ADR-reference`
  > Per [ADR-0003](https://github.com/informatics-isi-edu/deriva-ml/blob/main/docs/adr/0003-dataset-dev-versioning-model.md)
- `dataset-lifecycle/references/concepts.md:300` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > | Adding a feature value (via `deriva_ml_add_feature_values` or Python API) | Drift is **not** auto-detected; if you wan
- `dataset-lifecycle/references/concepts.md:306` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > - Reads (`deriva_ml_get_dataset`, `deriva_ml_list_dataset_members`, `deriva_ml_bag_info`, `deriva_ml_cache_dataset`).
- `dataset-lifecycle/references/concepts.md:323` **HIST-PROSE** — `version-reference`
  > - "Fixed 47 mislabeled pneumonia images identified in audit review. Retraining recommended for any model trained on v1.1
- `dataset-lifecycle/references/concepts.md:401` **HIST-PROSE** — `version-reference`
  > members = versioned_dataset.list_dataset_members()  # members at v1.0.0
- `dataset-lifecycle/references/concepts.md:472` **HIST-PROSE** — `legacy-marker`
  > # Both directions in a single call (replaces the legacy split list_dataset_children / list_dataset_parents)
- `dataset-lifecycle/references/concepts.md:482` **HIST-PROSE** — `legacy-marker`
  > > Note: the legacy `list_dataset_parents(rid)` was generalized into `deriva_ml_list_dataset_relations(rid)`, which retur
- `dataset-lifecycle/references/concepts.md:655` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `dataset-lifecycle/references/concepts.md:669` **HIST-PROSE** — `used-to`
  > By default, symlinks are used to save disk space. Set `use_symlinks=False` to copy files.
- `dataset-lifecycle/references/concepts.md:675` **HIST-PROSE** — `legacy-marker`
  > # (the legacy estimate_bag_size is subsumed by this tool)
- `dataset-lifecycle/references/concepts.md:721` **HIST-PROSE** — `legacy-marker`
  > | Update description | `deriva_ml_update_dataset(rid, description=...)` | — | Subsumes legacy set_dataset_description |
- `dataset-lifecycle/references/concepts.md:734` **HIST-PROSE** — `legacy-marker`
  > | Validate RIDs | `get_entities(filters={"RID": "..."})` per candidate table; check for empty result | — | The legacy va
- `dataset-lifecycle/references/concepts.md:735` **HIST-PROSE** — `legacy-marker`
  > | Bag info / size estimate | `deriva_ml_bag_info` (subsumes legacy estimate_bag_size) | `dataset.estimate_bag_size()` | 
- `dataset-lifecycle/references/curated-subsets.md:103` **REMOVED-PY** — `cache_features`
  > ## Caching feature values with `cache_features()`
- `dataset-lifecycle/references/curated-subsets.md:105` **REMOVED-PY** — `cache_features`
  > When filtering by a single feature (e.g., "images with label X"), downloading a full bag just to read labels is overkill
- `dataset-lifecycle/references/curated-subsets.md:110` **REMOVED-PY** — `cache_features`
  > feature_df = ml.cache_features(
- `dataset-lifecycle/references/curated-subsets.md:127` **REMOVED-PY** — `cache_features`
  > - The first call to `cache_features()` fetches from the catalog and stores locally. Subsequent calls within the same scr
- `dataset-lifecycle/references/workflow.md:43` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > Then call `deriva_ml_create_execution` with the returned `workflow_rid` and `description="Create training dataset"`.
- `dataset-lifecycle/references/workflow.md:45` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > Then call `deriva_ml_start_execution` with the returned `execution_rid`.
- `dataset-lifecycle/references/workflow.md:77` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > Call `deriva_ml_commit_execution` with the execution RID. (No need to call Python API `exe.commit_output_assets()` — dat
- `dataset-lifecycle/references/workflow.md:77` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > Call `deriva_ml_commit_execution` with the execution RID. (No need to call Python API `exe.commit_output_assets()` — dat
- `dataset-lifecycle/references/workflow.md:109` **HIST-PROSE** — `legacy-marker`
  > To **remove a type**, call `update_entities` on the dataset's type-association table and remove the row that links the d
- `dataset-lifecycle/references/workflow.md:111` **HIST-PROSE** — `legacy-marker`
  > To **create a new custom type**, call `add_term(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="
- `dataset-lifecycle/references/workflow.md:121` **HIST-PROSE** — `legacy-marker`
  > To **validate RIDs** before adding (catches invalid RIDs early), call `get_entities(hostname="data.example.org", catalog
- `dataset-lifecycle/references/workflow.md:203` **HIST-PROSE** — `legacy-marker`
  > > Note: the legacy split between `list_dataset_children` and `list_dataset_parents` is gone — `deriva_ml_list_dataset_re
- `dataset-lifecycle/references/workflow.md:209` **HIST-PROSE** — `ADR-reference`
  > ## Versioning (ADR-0003 dev/release model)
- `dataset-lifecycle/references/workflow.md:211` **HIST-PROSE** — `ADR-reference`
  > Per ADR-0003 (deriva-ml 1.34+), datasets are at one of two version states at any moment:
- `dataset-lifecycle/references/workflow.md:226` **HIST-PROSE** — `legacy-marker`
  > To **preview** what a bag will contain (size + manifest), call `deriva_ml_bag_info(hostname="data.example.org", catalog_
- `dataset-lifecycle/references/workflow.md:234` **HIST-PROSE** — `legacy-marker`
  > To find **which executions produced or used an asset**, call `deriva_ml_lookup_asset(hostname="data.example.org", catalo
- `dataset-lifecycle/references/workflow.md:359` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > deriva_ml_create_execution(hostname="data.example.org", catalog_id="1", workflow_rid="<workflow_rid>", description="..."
- `dataset-lifecycle/references/workflow.md:360` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > deriva_ml_start_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")
- `dataset-lifecycle/references/workflow.md:371` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="<execution_rid>")
- `dataset-lifecycle/scripts/generate_subset_template.py:29` **HIST-PROSE** — `used-to`
  > - ``{{EXPERIMENT_NAME}}``: The Hydra experiment config name used to run this
- `dataset-lifecycle/scripts/generate_subset_template.py:41` **REMOVED-PY** — `cache_features`
  > - ``ml_instance.cache_features(table, feature, selector=...)`` → pd.DataFrame
- `dataset-lifecycle/scripts/generate_subset_template.py:136` **REMOVED-PY** — `cache_features`
  > feature_df = ml_instance.cache_features(
- `dataset-lifecycle/scripts/generate_subset_template.py:195` **HIST-PROSE** — `ADR-reference`
  > # current_version may be a dev label (per ADR-0003) if member-add

### `debug-bag-contents`

- `debug-bag-contents/SKILL.md:50` **HIST-PROSE** — `legacy-marker`
  > - **Tool**: `deriva_ml_bag_info(hostname="data.example.org", catalog_id="1", dataset_rid="<rid>", version="1.0.0")` retu
- `debug-bag-contents/SKILL.md:221` **HIST-PROSE** — `ADR-reference`
  > - **Tool (ADR-0003 dev/release model)**: any membership change since the last release will have flipped `current_version
- `debug-bag-contents/SKILL.md:278` **HIST-PROSE** — `ADR-reference`
  > | `deriva_ml_release` | Promote a dev period to a released version (per ADR-0003 — replaces the old increment_dataset_ve

### `deriva-ml-context`

- `deriva-ml-context/SKILL.md:12` **HIST-PROSE** — `ADR-reference`
  > Sync") for the full convention. Inheritance-rule rationale: ADR-0001.
- `deriva-ml-context/SKILL.md:24` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > - **`deriva_ml_*` MCP tools** — e.g., `deriva_ml_create_dataset`, `deriva_ml_start_execution`, `deriva_ml_add_feature_va
- `deriva-ml-context/SKILL.md:24` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > - **`deriva_ml_*` MCP tools** — e.g., `deriva_ml_create_dataset`, `deriva_ml_start_execution`, `deriva_ml_add_feature_va
- `deriva-ml-context/SKILL.md:53` **HIST-PROSE** — `ADR-reference`
  > - For **datasets** at a dev version (PEP 440 `is_devrelease`, e.g. `0.4.0.post1.dev3` per ADR-0003), `cite_url` has no s
- `deriva-ml-context/SKILL.md:72` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > | **Dataset** | A versioned collection of catalog rows that an execution consumed or produced. Datasets carry a type (`D
- `deriva-ml-context/SKILL.md:72` **HIST-PROSE** — `ADR-reference`
  > | **Dataset** | A versioned collection of catalog rows that an execution consumed or produced. Datasets carry a type (`D
- `deriva-ml-context/SKILL.md:74` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > | **Execution** | One run of a Workflow against specific input Datasets, producing output Datasets / Features / Assets. 
- `deriva-ml-context/SKILL.md:74` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > | **Execution** | One run of a Workflow against specific input Datasets, producing output Datasets / Features / Assets. 
- `deriva-ml-context/SKILL.md:74` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > | **Execution** | One run of a Workflow against specific input Datasets, producing output Datasets / Features / Assets. 
- `deriva-ml-context/SKILL.md:74` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > | **Execution** | One run of a Workflow against specific input Datasets, producing output Datasets / Features / Assets. 
- `deriva-ml-context/SKILL.md:74` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > | **Execution** | One run of a Workflow against specific input Datasets, producing output Datasets / Features / Assets. 
- `deriva-ml-context/SKILL.md:75` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > | **Feature** | A typed value attached to a row of some target table (e.g., a per-image classification label produced by
- `deriva-ml-context/SKILL.md:76` **HIST-PROSE** — `version-reference`
  > | **Asset** | A file uploaded to hatrac and recorded in the catalog with an Asset_Type and provenance link to its produc
- `deriva-ml-context/SKILL.md:76` **HIST-PROSE** — `ADR-reference`
  > | **Asset** | A file uploaded to hatrac and recorded in the catalog with an Asset_Type and provenance link to its produc
- `deriva-ml-context/SKILL.md:93` **HIST-PROSE** — `ADR-reference`
  > - **Version management** — Datasets carry a two-state PEP 440 version (released / dev) per ADR-0003. The mutation tools 
- `deriva-ml-context/SKILL.md:138` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > | `Execution_Status_Type` | (managed automatically by the execution-state machine — do not extend) | Status transitions 
- `deriva-ml-context/SKILL.md:138` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > | `Execution_Status_Type` | (managed automatically by the execution-state machine — do not extend) | Status transitions 
- `deriva-ml-context/SKILL.md:138` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > | `Execution_Status_Type` | (managed automatically by the execution-state machine — do not extend) | Status transitions 

### `execution-lifecycle`

- `execution-lifecycle/SKILL.md:37` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > 4. **Stage if needed.** Small datasets (< 100 MB) — let the execution download. Large datasets (> 1 GB) — `deriva_ml_cac
- `execution-lifecycle/SKILL.md:47` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > | **MCP Tools** | Claude-driven interactive work | Explicit tool calls (`deriva_ml_create_execution` → `deriva_ml_start_
- `execution-lifecycle/SKILL.md:47` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > | **MCP Tools** | Claude-driven interactive work | Explicit tool calls (`deriva_ml_create_execution` → `deriva_ml_start_
- `execution-lifecycle/SKILL.md:47` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > | **MCP Tools** | Claude-driven interactive work | Explicit tool calls (`deriva_ml_create_execution` → `deriva_ml_start_
- `execution-lifecycle/SKILL.md:47` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > | **MCP Tools** | Claude-driven interactive work | Explicit tool calls (`deriva_ml_create_execution` → `deriva_ml_start_
- `execution-lifecycle/SKILL.md:59` **HIST-PROSE** — `legacy-marker`
  > **I/O goes through the Python API**, not MCP tools: `exe.download_dataset_bag()`, `exe.asset_file_path()`, `exe.commit_o
- `execution-lifecycle/SKILL.md:59` **HIST-PROSE** — `version-reference`
  > **I/O goes through the Python API**, not MCP tools: `exe.download_dataset_bag()`, `exe.asset_file_path()`, `exe.commit_o
- `execution-lifecycle/SKILL.md:59` **HIST-PROSE** — `ADR-reference`
  > **I/O goes through the Python API**, not MCP tools: `exe.download_dataset_bag()`, `exe.asset_file_path()`, `exe.commit_o
- `execution-lifecycle/SKILL.md:111` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > 3. **Every execution needs a workflow** — find with `deriva_ml_find_workflow_by_url` or let `deriva_ml_create_execution`
- `execution-lifecycle/references/concepts.md:39` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > - **In MCP tools**: Pass `execution_rid` to `deriva_ml_get_execution`, `deriva_ml_list_execution_children`, `deriva_ml_l
- `execution-lifecycle/references/concepts.md:111` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > | `Pending` → `Running` | `deriva_ml_start_execution(...)` is called (automatic in the context manager); records the sta
- `execution-lifecycle/references/concepts.md:112` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > | `Running` → `Completed` | `deriva_ml_commit_execution(...)` is called (automatic on context manager exit); records the
- `execution-lifecycle/references/concepts.md:114` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > | Any → `Aborted` | `deriva_ml_abort_execution(hostname, catalog_id, execution_rid, reason="...")`. The state machine fo
- `execution-lifecycle/references/concepts.md:118` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > - `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)` — normal success completion
- `execution-lifecycle/references/concepts.md:119` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > - `deriva_ml_abort_execution(hostname, catalog_id, execution_rid)` — failure marking
- `execution-lifecycle/references/concepts.md:120` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > - `deriva_ml_update_execution(hostname, catalog_id, execution_rid, description="<text>")` — update the execution's descr
- `execution-lifecycle/references/concepts.md:126` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > - **MCP tools (explicit calls):** You call `deriva_ml_create_execution` (sets `Created`), `deriva_ml_start_execution` (s
- `execution-lifecycle/references/concepts.md:126` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > - **MCP tools (explicit calls):** You call `deriva_ml_create_execution` (sets `Created`), `deriva_ml_start_execution` (s
- `execution-lifecycle/references/concepts.md:126` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > - **MCP tools (explicit calls):** You call `deriva_ml_create_execution` (sets `Created`), `deriva_ml_start_execution` (s
- `execution-lifecycle/references/concepts.md:126` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > - **MCP tools (explicit calls):** You call `deriva_ml_create_execution` (sets `Created`), `deriva_ml_start_execution` (s
- `execution-lifecycle/references/concepts.md:162` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > When using MCP tools, `deriva_ml_create_execution` can find or create the workflow for you — pass `workflow_name` and `w
- `execution-lifecycle/references/concepts.md:174` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > | **MCP tools** (`deriva_ml_create_execution`) | You provide `workflow_name` and `workflow_type`; the URL is not auto-de
- `execution-lifecycle/references/concepts.md:226` **HIST-PROSE** — `legacy-marker`
  > Use `deriva_ml_list_execution_children(hostname, catalog_id, execution_rid)` to walk down the tree and `deriva_ml_list_e
- `execution-lifecycle/references/concepts.md:249` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > deriva_ml_create_execution(hostname="data.example.org", catalog_id="1",
- `execution-lifecycle/references/concepts.md:251` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > deriva_ml_start_execution(hostname="data.example.org", catalog_id="1",
- `execution-lifecycle/references/concepts.md:254` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1",
- `execution-lifecycle/references/concepts.md:259` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > deriva_ml_create_execution(hostname="data.example.org", catalog_id="1",
- `execution-lifecycle/references/concepts.md:261` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > deriva_ml_start_execution(hostname="data.example.org", catalog_id="1",
- `execution-lifecycle/references/concepts.md:264` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1",
- `execution-lifecycle/references/concepts.md:269` **REMOVED-TOOL** — `deriva_ml_add_nested_execution`
  > deriva_ml_add_nested_execution(hostname="data.example.org", catalog_id="1",
- `execution-lifecycle/references/concepts.md:353` **HIST-PROSE** — `version-reference`
  > If the caller bypasses the `with` block and calls `commit_output_assets()` on a still-`Running` execution, the method au
- `execution-lifecycle/references/concepts.md:353` **HIST-PROSE** — `ADR-reference`
  > If the caller bypasses the `with` block and calls `commit_output_assets()` on a still-`Running` execution, the method au
- `execution-lifecycle/references/concepts.md:361` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > - In MCP tools, call `deriva_ml_add_feature_values(hostname, catalog_id, table, feature_name, execution_rid="<execution_
- `execution-lifecycle/references/concepts.md:394` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > In MCP tools, the lifecycle is managed through explicit tool calls (`deriva_ml_create_execution`, `deriva_ml_start_execu
- `execution-lifecycle/references/concepts.md:394` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > In MCP tools, the lifecycle is managed through explicit tool calls (`deriva_ml_create_execution`, `deriva_ml_start_execu
- `execution-lifecycle/references/concepts.md:394` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > In MCP tools, the lifecycle is managed through explicit tool calls (`deriva_ml_create_execution`, `deriva_ml_start_execu
- `execution-lifecycle/references/concepts.md:394` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > In MCP tools, the lifecycle is managed through explicit tool calls (`deriva_ml_create_execution`, `deriva_ml_start_execu
- `execution-lifecycle/references/concepts.md:394` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > In MCP tools, the lifecycle is managed through explicit tool calls (`deriva_ml_create_execution`, `deriva_ml_start_execu
- `execution-lifecycle/references/concepts.md:417` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > When using MCP tools, `deriva_ml_create_execution(hostname, catalog_id, ...)` accepts `workflow_name`, `workflow_type`, 
- `execution-lifecycle/references/concepts.md:436` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > - The `with` block automatically transitions the execution to `Running` on entry (equivalent to the MCP `deriva_ml_start
- `execution-lifecycle/references/concepts.md:436` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > - The `with` block automatically transitions the execution to `Running` on entry (equivalent to the MCP `deriva_ml_start
- `execution-lifecycle/references/concepts.md:436` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > - The `with` block automatically transitions the execution to `Running` on entry (equivalent to the MCP `deriva_ml_start
- `execution-lifecycle/references/concepts.md:488` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > In MCP tools, pass `dry_run`: `true` to `deriva_ml_create_execution`. In Python, pass `dry_run=True` to the runner or se
- `execution-lifecycle/references/concepts.md:497` **HIST-PROSE** — `legacy-marker`
  > > **Known gap:** the legacy `restore_execution` tool has **no equivalent** in the new MCP surface. The replacement patte
- `execution-lifecycle/references/concepts.md:503` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > 3. **Create a fresh execution.** Call `deriva_ml_create_execution(hostname, catalog_id, ...)` with the same workflow, da
- `execution-lifecycle/references/concepts.md:504` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > 4. **Continue the lifecycle as normal.** Start it (`deriva_ml_start_execution`), do the work, and commit (`deriva_ml_com
- `execution-lifecycle/references/concepts.md:504` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > 4. **Continue the lifecycle as normal.** Start it (`deriva_ml_start_execution`), do the work, and commit (`deriva_ml_com
- `execution-lifecycle/references/concepts.md:525` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > All of these can be caught before `deriva_ml_start_execution(...)`.
- `execution-lifecycle/references/concepts.md:531` **HIST-PROSE** — `legacy-marker`
  > | Validate RIDs | `deriva_ml_get_dataset` / `get_entities` | All dataset and asset RIDs exist (legacy `validate_rids` wa
- `execution-lifecycle/references/concepts.md:533` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > | Cache data | `deriva_ml_cache_dataset` | Downloads bags/assets into cache without execution provenance |
- `execution-lifecycle/references/concepts.md:543` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > | `not_cached` | No local copy | Call `deriva_ml_cache_dataset` if large |
- `execution-lifecycle/references/concepts.md:544` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > | `cached_metadata_only` | Table data present, assets not fetched | Call `deriva_ml_cache_dataset(..., materialize=True)
- `execution-lifecycle/references/concepts.md:546` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > | `cached_incomplete` | Was cached but assets are missing | Call `deriva_ml_cache_dataset` to re-materialize |
- `execution-lifecycle/references/concepts.md:562` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > The MCP tool `deriva_ml_cache_dataset(hostname, catalog_id, dataset_rid, version)` does the same thing without requiring
- `execution-lifecycle/references/workflow.md:31` **HIST-PROSE** — `legacy-marker`
  > | `deriva_ml_get_dataset` / `get_entities` | Pre-flight: verify RIDs exist (legacy `validate_rids` was removed) |
- `execution-lifecycle/references/workflow.md:33` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > | `deriva_ml_cache_dataset` | Pre-flight: download data into cache without execution |
- `execution-lifecycle/references/workflow.md:34` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > | `deriva_ml_create_execution` | Create execution (finds/creates workflow automatically) |
- `execution-lifecycle/references/workflow.md:35` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > | `deriva_ml_start_execution` | Sets status to `Running`, records start timestamp |
- `execution-lifecycle/references/workflow.md:36` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > | `deriva_ml_commit_execution` | Sets status to `Completed` (success path) |
- `execution-lifecycle/references/workflow.md:37` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > | `deriva_ml_abort_execution` | Sets status to `Failed`/`Aborted` (failure path) |
- `execution-lifecycle/references/workflow.md:38` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > | `deriva_ml_update_execution` | Arbitrary status / message updates (replaces legacy `update_execution_status`) |
- `execution-lifecycle/references/workflow.md:38` **HIST-PROSE** — `legacy-marker`
  > | `deriva_ml_update_execution` | Arbitrary status / message updates (replaces legacy `update_execution_status`) |
- `execution-lifecycle/references/workflow.md:42` **HIST-PROSE** — `legacy-marker`
  > | Python API `exe.commit_output_assets()` | Commit all registered files to catalog — uploads bytes, writes asset rows (d
- `execution-lifecycle/references/workflow.md:42` **HIST-PROSE** — `version-reference`
  > | Python API `exe.commit_output_assets()` | Commit all registered files to catalog — uploads bytes, writes asset rows (d
- `execution-lifecycle/references/workflow.md:42` **HIST-PROSE** — `ADR-reference`
  > | Python API `exe.commit_output_assets()` | Commit all registered files to catalog — uploads bytes, writes asset rows (d
- `execution-lifecycle/references/workflow.md:44` **REMOVED-TOOL** — `deriva_ml_add_nested_execution`
  > | `deriva_ml_add_nested_execution` | Link parent-child executions |
- `execution-lifecycle/references/workflow.md:47` **HIST-PROSE** — `legacy-marker`
  > | (gap) | Re-running an aborted execution: legacy `restore_execution` was removed; create a fresh execution from the pri
- `execution-lifecycle/references/workflow.md:78` **HIST-PROSE** — `legacy-marker`
  > If the workflow type you need doesn't exist, call `add_term(hostname, catalog_id, schema="deriva-ml", table="Workflow_Ty
- `execution-lifecycle/references/workflow.md:90` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > Call `deriva_ml_create_execution(hostname, catalog_id, ...)` with:
- `execution-lifecycle/references/workflow.md:103` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > Call `deriva_ml_start_execution(hostname, catalog_id, execution_rid)`. Sets status to "Running" and records the start ti
- `execution-lifecycle/references/workflow.md:121` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > On success: call `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)`. Sets status to "Completed" and recor
- `execution-lifecycle/references/workflow.md:123` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > On failure: call `deriva_ml_abort_execution(hostname, catalog_id, execution_rid, reason="<explanation>")`. The reason te
- `execution-lifecycle/references/workflow.md:125` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > For mid-run progress recording, use the Python API's `metrics_file` (write JSON-lines to a metrics file as the run progr
- `execution-lifecycle/references/workflow.md:178` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > - The `with` block automatically transitions the execution to `Running` on entry (equivalent to the MCP `deriva_ml_start
- `execution-lifecycle/references/workflow.md:178` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > - The `with` block automatically transitions the execution to `Running` on entry (equivalent to the MCP `deriva_ml_start
- `execution-lifecycle/references/workflow.md:178` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > - The `with` block automatically transitions the execution to `Running` on entry (equivalent to the MCP `deriva_ml_start
- `execution-lifecycle/references/workflow.md:238` **HIST-PROSE** — `legacy-marker`
  > **Note:** The target asset table must already exist in the catalog before you can register files for upload to it. The b
- `execution-lifecycle/references/workflow.md:265` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > In MCP tools, call `deriva_ml_add_feature_values(hostname, catalog_id, table, feature_name, execution_rid="<execution_ri
- `execution-lifecycle/references/workflow.md:265` **HIST-PROSE** — `legacy-marker`
  > In MCP tools, call `deriva_ml_add_feature_values(hostname, catalog_id, table, feature_name, execution_rid="<execution_ri
- `execution-lifecycle/references/workflow.md:325` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > The legacy `update_execution_status` and `set_execution_description` tools were folded into `deriva_ml_update_execution`
- `execution-lifecycle/references/workflow.md:325` **HIST-PROSE** — `legacy-marker`
  > The legacy `update_execution_status` and `set_execution_description` tools were folded into `deriva_ml_update_execution`
- `execution-lifecycle/references/workflow.md:329` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-YYYY")
- `execution-lifecycle/references/workflow.md:333` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > deriva_ml_abort_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-YYYY")
- `execution-lifecycle/references/workflow.md:337` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > deriva_ml_update_execution(hostname="data.example.org", catalog_id="1",
- `execution-lifecycle/references/workflow.md:339` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > deriva_ml_update_execution(hostname="data.example.org", catalog_id="1",
- `execution-lifecycle/references/workflow.md:349` **REMOVED-TOOL** — `deriva_ml_add_nested_execution`
  > Call `deriva_ml_add_nested_execution(hostname, catalog_id, ...)` with:
- `execution-lifecycle/references/workflow.md:356` **HIST-PROSE** — `legacy-marker`
  > The legacy `list_nested_executions` was split into two directional tools:
- `execution-lifecycle/references/workflow.md:363` **HIST-PROSE** — `legacy-marker`
  > > **Known gap:** the legacy `restore_execution` tool has **no equivalent**. To re-run after a failure or abort, manually
- `execution-lifecycle/references/workflow.md:369` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > 3. Call `deriva_ml_create_execution(hostname, catalog_id, ...)` with the same workflow/dataset/asset config — this creat
- `execution-lifecycle/references/workflow.md:379` **REMOVED-TOOL** — `deriva_ml_create_execution_dataset`
  > Call `deriva_ml_create_execution_dataset(hostname, catalog_id, execution_rid, ...)` to create a new dataset linked to th
- `execution-lifecycle/references/workflow.md:394` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > **Step 3:** Call `deriva_ml_create_execution(hostname="data.example.org", catalog_id="1", workflow_rid="2-WF01", descrip
- `execution-lifecycle/references/workflow.md:396` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > **Step 4:** Call `deriva_ml_start_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-YYYY")`.
- `execution-lifecycle/references/workflow.md:406` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > **Step 9:** Call `deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-YYYY")`. (On 
- `execution-lifecycle/references/workflow.md:406` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > **Step 9:** Call `deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="2-YYYY")`. (On 

### `generate-descriptions`

- `generate-descriptions/SKILL.md:17` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > - **Executions** (`deriva_ml_create_execution` -- description parameter)
- `generate-descriptions/references/templates.md:37` **HIST-PROSE** — `version-reference`
  > **Example:** "Train ResNet-50 classifier on chest X-ray dataset 1-ABC4 v1.2.0. Learning rate 0.001, batch size 32, 100 e
- `generate-descriptions/references/templates.md:99` **HIST-PROSE** — `version-reference`
  > Train ResNet-50 on chest X-ray dataset `1-ABC4` v1.2.0.

### `generate-scripts`

- `generate-scripts/SKILL.md:13` **REMOVED-PY** — `cache_features`
  > > **Note:** This skill generates Python scripts that use the DerivaML Python API directly, not MCP tools. Methods like `
- `generate-scripts/SKILL.md:24` **REMOVED-PY** — `cache_features`
  > - DO use the working data cache (`ml.cache_table()`, `ml.cache_features()`, etc.)
- `generate-scripts/SKILL.md:46` **REMOVED-PY** — `cache_features`
  > labels = ml.cache_features("Image", "Classification")
- `generate-scripts/SKILL.md:152` **REMOVED-PY** — `cache_features`
  > features = ml.cache_features("Image", "Classification")

### `manage-storage`

- `manage-storage/SKILL.md:21` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > | `cache/` | Downloaded dataset bags (BDBags), keyed by RID + checksum | Python API `dataset.download_dataset_bag(versio
- `manage-storage/SKILL.md:23` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > | `execution_{RID}/` | Execution working directories — staged output files, logs | `deriva_ml_create_execution` |
- `manage-storage/SKILL.md:83` **HIST-PROSE** — `legacy-marker`
  > (Note: `deriva_ml_bag_info` subsumes both the legacy `bag_info` and `estimate_bag_size` — it works whether or not the ba
- `manage-storage/SKILL.md:148` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > > **Resuming an aborted execution:** there is no MCP tool that resumes an aborted execution. **Workaround:** inspect the
- `manage-storage/SKILL.md:166` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > deriva_ml_cache_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="28CT", version="0.9.0")
- `manage-storage/SKILL.md:174` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > deriva_ml_cache_dataset(hostname="data.example.org", catalog_id="1", dataset_rid="28CT", version="0.9.0", materialize=fa
- `manage-storage/SKILL.md:182` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > deriva_ml_cache_dataset(hostname="data.example.org", catalog_id="1", asset_rid="3WSE")
- `manage-storage/SKILL.md:182` **SIG_DRIFT** — `cache_dataset(asset_rid=) — never existed`
  > deriva_ml_cache_dataset(hostname="data.example.org", catalog_id="1", asset_rid="3WSE")
- `manage-storage/SKILL.md:201` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > 3. **Pre-fetch** — `deriva_ml_cache_dataset(...)` — download anything that's `not_cached`
- `manage-storage/SKILL.md:203` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > 5. **Run** — `deriva_ml_create_execution(...)` → downloads hit cache instantly
- `manage-storage/SKILL.md:219` **HIST-PROSE** — `legacy-marker`
  > - `deriva_ml_bag_info` — Check cache status, size, and manifest for a specific dataset version (subsumes legacy bag_info
- `manage-storage/SKILL.md:220` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > - `deriva_ml_cache_dataset` — Pre-fetch a dataset or asset into cache

### `ml-data-engineering`

- `ml-data-engineering/SKILL.md:41` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"]
- `ml-data-engineering/SKILL.md:175` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/SKILL.md:212` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/SKILL.md:227` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Primary_Diagnosis", "Severity"],  # nested dirs
- `ml-data-engineering/SKILL.md:228` **SIG_DRIFT** — `restructure_assets(value_selector=) → fold into targets={feature: selector}`
  > value_selector=FeatureRecord.select_latest,
- `ml-data-engineering/references/restructure-guide.md:38` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],     # create subdirs by label
- `ml-data-engineering/references/restructure-guide.md:66` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Species"]
- `ml-data-engineering/references/restructure-guide.md:73` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"]
- `ml-data-engineering/references/restructure-guide.md:80` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Classification.Label"]
- `ml-data-engineering/references/restructure-guide.md:80` **SIG_DRIFT** — `restructure_assets group_by="Feature.column" dotted syntax → use target_transform`
  > group_by=["Classification.Label"]
- `ml-data-engineering/references/restructure-guide.md:87` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Species", "Diagnosis"]
- `ml-data-engineering/references/restructure-guide.md:105` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:106` **SIG_DRIFT** — `restructure_assets(value_selector=) → fold into targets={feature: selector}`
  > value_selector=FeatureRecord.select_newest,
- `ml-data-engineering/references/restructure-guide.md:112` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:113` **SIG_DRIFT** — `restructure_assets(value_selector=) → fold into targets={feature: selector}`
  > value_selector=FeatureRecord.select_first,
- `ml-data-engineering/references/restructure-guide.md:122` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:123` **SIG_DRIFT** — `restructure_assets(value_selector=) → fold into targets={feature: selector}`
  > value_selector=RecordClass.select_majority_vote(),
- `ml-data-engineering/references/restructure-guide.md:129` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:130` **SIG_DRIFT** — `restructure_assets(value_selector=) → fold into targets={feature: selector}`
  > value_selector=FeatureRecord.select_majority_vote("Diagnosis_Type"),
- `ml-data-engineering/references/restructure-guide.md:147` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:175` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:191` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:222` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Score"],
- `ml-data-engineering/references/restructure-guide.md:237` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:258` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:385` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `ml-data-engineering/references/restructure-guide.md:386` **SIG_DRIFT** — `restructure_assets(value_selector=) → fold into targets={feature: selector}`
  > value_selector=FeatureRecord.select_newest,
- `ml-data-engineering/references/restructure-guide.md:414` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Primary_Diagnosis", "Severity"],  # nested dirs
- `ml-data-engineering/references/restructure-guide.md:415` **SIG_DRIFT** — `restructure_assets(value_selector=) → fold into targets={feature: selector}`
  > value_selector=FeatureRecord.select_latest,
- `ml-data-engineering/references/restructure-guide.md:428` **HIST-PROSE** — `legacy-marker`
  > | `deriva_ml_bag_info` | Preview row counts, asset sizes, and manifest per table (subsumes legacy estimate_bag_size) |

### `model-development-workflow`

- `model-development-workflow/SKILL.md:117` **HIST-PROSE** — `ADR-reference`
  > After populating the development subset (which will have flipped `current_version` to a dev label per ADR-0003), call `d
- `model-development-workflow/SKILL.md:141` **HIST-PROSE** — `legacy-marker`
  > **If labels are missing**, add them to the development dataset first. The legacy `start_execution` / `stop_execution` pa
- `model-development-workflow/SKILL.md:144` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > deriva_ml_create_execution(
- `model-development-workflow/SKILL.md:150` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > deriva_ml_start_execution(hostname="data.example.org", catalog_id="1", execution_rid="<exec_rid>")
- `model-development-workflow/SKILL.md:151` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > deriva_ml_add_feature_values(
- `model-development-workflow/SKILL.md:158` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid="<exec_rid>")
- `model-development-workflow/SKILL.md:189` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > deriva_ml_create_execution(
- `model-development-workflow/SKILL.md:222` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > 3. `deriva_ml_cache_dataset(hostname=..., catalog_id=..., dataset_rid="...", version="...")` — pre-fetch if needed
- `model-development-workflow/SKILL.md:266` **REMOVED-TOOL** — `deriva_ml_cache_dataset`
  > | 3 | `deriva_ml_cache_dataset(hostname=..., catalog_id=..., dataset_rid=...)` | Pre-fetch large datasets |
- `model-development-workflow/SKILL.md:303` **HIST-PROSE** — `ADR-reference`
  > ADR-0003, feature drift is not auto-detected by the dataset-mutation
- `model-development-workflow/SKILL.md:320` **HIST-PROSE** — `legacy-marker`
  > 1. **Analyze results** — use `deriva_ml_denormalize_dataset(hostname=..., catalog_id=..., dataset_rid=...)` (renamed fro

### `new-model`

- `new-model/SKILL.md:50` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["My_Feature"],
- `new-model/references/runner-interface.md:87` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Image_Classification"],
- `new-model/references/runner-interface.md:147` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Image_Classification"],
- `new-model/references/runner-interface.md:283` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Image_Classification"],

### `run-notebook`

- `run-notebook/references/workflow.md:262` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > | Execution status stuck at "Running" | Notebook crashed without clean exit | Call `deriva_ml_abort_execution(hostname=.
- `run-notebook/references/workflow.md:262` **HIST-PROSE** — `legacy-marker`
  > | Execution status stuck at "Running" | Notebook crashed without clean exit | Call `deriva_ml_abort_execution(hostname=.

### `troubleshoot-execution`

- `troubleshoot-execution/SKILL.md:26` **REMOVED-TOOL** — `deriva_ml_add_feature_values`
  > | `deriva_ml_add_feature_values` or feature-related calls error about a missing feature | "Feature Not Found" |
- `troubleshoot-execution/SKILL.md:51` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > - With MCP tools, ensure you called `deriva_ml_start_execution(hostname, catalog_id, execution_rid)` before attempting e
- `troubleshoot-execution/SKILL.md:51` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > - With MCP tools, ensure you called `deriva_ml_start_execution(hostname, catalog_id, execution_rid)` before attempting e
- `troubleshoot-execution/SKILL.md:63` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > 1. Call `commit_output_assets()` **after** the `with` block exits in Python, not inside it. With MCP tools, call it afte
- `troubleshoot-execution/SKILL.md:63` **HIST-PROSE** — `version-reference`
  > 1. Call `commit_output_assets()` **after** the `with` block exits in Python, not inside it. With MCP tools, call it afte
- `troubleshoot-execution/SKILL.md:63` **HIST-PROSE** — `ADR-reference`
  > 1. Call `commit_output_assets()` **after** the `with` block exits in Python, not inside it. With MCP tools, call it afte
- `troubleshoot-execution/SKILL.md:99` **HIST-PROSE** — `ADR-reference`
  > - Per ADR-0003 (deriva-ml 1.34+), dataset mutations flip `current_version` to a dev label (`<last_release>.post1.devN`).
- `troubleshoot-execution/SKILL.md:141` **HIST-PROSE** — `version-reference`
  > > **Note (v1.39+ behavior change):** CLI-uploaded executions (`deriva-ml-upload`, `deriva-ml-run`) now transition `Stopp
- `troubleshoot-execution/SKILL.md:141` **HIST-PROSE** — `ADR-reference`
  > > **Note (v1.39+ behavior change):** CLI-uploaded executions (`deriva-ml-upload`, `deriva-ml-run`) now transition `Stopp
- `troubleshoot-execution/SKILL.md:148` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > - **`deriva_ml_commit_execution(hostname, catalog_id, execution_rid)`** — drains staged outputs and advances `Running → 
- `troubleshoot-execution/SKILL.md:149` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > - **`deriva_ml_abort_execution(hostname, catalog_id, execution_rid, reason="<short explanation>")`** — transitions to `A
- `troubleshoot-execution/SKILL.md:188` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > | `Created` | No | Execution was registered but `start_execution` was never called. No work happened. | Start it (`deriv
- `troubleshoot-execution/SKILL.md:217` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid="<rid>")
- `troubleshoot-execution/SKILL.md:220` **HIST-PROSE** — `version-reference`
  > This drains the staged work and re-attempts any rows or assets that previously errored. The bag-commit pipeline is idemp
- `troubleshoot-execution/SKILL.md:220` **HIST-PROSE** — `ADR-reference`
  > This drains the staged work and re-attempts any rows or assets that previously errored. The bag-commit pipeline is idemp
- `troubleshoot-execution/SKILL.md:231` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid="<rid>")
- `troubleshoot-execution/SKILL.md:247` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > deriva_ml_abort_execution(hostname=..., catalog_id=..., execution_rid="<bad-rid>",
- `troubleshoot-execution/SKILL.md:251` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > recovery = deriva_ml_create_execution(
- `troubleshoot-execution/SKILL.md:261` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > deriva_ml_start_execution(hostname=..., catalog_id=..., execution_rid=new_rid)
- `troubleshoot-execution/SKILL.md:263` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid=new_rid)
- `troubleshoot-execution/SKILL.md:288` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname=..., catalog_id=..., execution_rid="<bad-rid>")
- `troubleshoot-execution/SKILL.md:296` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > recovery = deriva_ml_create_execution(
- `troubleshoot-execution/references/execution-lifecycle.md:64` **HIST-PROSE** — `legacy-marker`
  > Add custom types via the generic `add_term` tool (the legacy `add_workflow_type` helper was removed):
- `troubleshoot-execution/references/execution-lifecycle.md:113` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > deriva_ml_create_execution(hostname="data.example.org", catalog_id="1",
- `troubleshoot-execution/references/execution-lifecycle.md:117` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > deriva_ml_start_execution(hostname="data.example.org", catalog_id="1",
- `troubleshoot-execution/references/execution-lifecycle.md:243` **HIST-PROSE** — `ADR-reference`
  > The call is idempotent — re-running after a partial failure picks up the failed rows and leaves the already-uploaded one
- `troubleshoot-execution/references/execution-lifecycle.md:293` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > Report progress during long-running workflows. The legacy `update_execution_status` was folded into `deriva_ml_update_ex
- `troubleshoot-execution/references/execution-lifecycle.md:293` **HIST-PROSE** — `legacy-marker`
  > Report progress during long-running workflows. The legacy `update_execution_status` was folded into `deriva_ml_update_ex
- `troubleshoot-execution/references/execution-lifecycle.md:298` **HIST-PROSE** — `legacy-marker`
  > # Arbitrary status with a message (replaces the legacy update_execution_status)
- `troubleshoot-execution/references/execution-lifecycle.md:299` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > deriva_ml_update_execution(hostname="data.example.org", catalog_id="1",
- `troubleshoot-execution/references/execution-lifecycle.md:304` **HIST-PROSE** — `legacy-marker`
  > # Normal completion (replaces the success path of the legacy stop_execution)
- `troubleshoot-execution/references/execution-lifecycle.md:305` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1",
- `troubleshoot-execution/references/execution-lifecycle.md:308` **HIST-PROSE** — `legacy-marker`
  > # Failure marking (replaces the failure path of the legacy stop_execution)
- `troubleshoot-execution/references/execution-lifecycle.md:309` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > deriva_ml_abort_execution(hostname="data.example.org", catalog_id="1",
- `troubleshoot-execution/references/execution-lifecycle.md:319` **OLD-STATUS-ENUM** — `Status.running`
  > exe.update_status(Status.running, "Loading data...")
- `troubleshoot-execution/references/execution-lifecycle.md:324` **OLD-STATUS-ENUM** — `Status.running`
  > exe.update_status(Status.running, f"Epoch {epoch+1}/100 complete")
- `troubleshoot-execution/references/execution-lifecycle.md:375` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > - An execution in `Failed`, `Stopped`, or `Pending_Upload` is salvageable — `deriva_ml_commit_execution` drains the stag
- `troubleshoot-execution/references/execution-lifecycle.md:375` **HIST-PROSE** — `version-reference`
  > - An execution in `Failed`, `Stopped`, or `Pending_Upload` is salvageable — `deriva_ml_commit_execution` drains the stag
- `troubleshoot-execution/references/execution-lifecycle.md:377` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > - A "recovery execution" is a new execution that consumes the failed run's inputs (Branch C) or its surviving outputs (B
- `troubleshoot-execution/references/execution-lifecycle.md:383` **HIST-PROSE** — `legacy-marker`
  > Executions can be nested for complex workflows. The legacy `list_nested_executions` was split into two directional tools
- `troubleshoot-execution/references/execution-lifecycle.md:388` **REMOVED-TOOL** — `deriva_ml_add_nested_execution`
  > deriva_ml_add_nested_execution(hostname="data.example.org", catalog_id="1",
- `troubleshoot-execution/references/execution-lifecycle.md:424` **REMOVED-TOOL** — `deriva_ml_create_execution_dataset`
  > deriva_ml_create_execution_dataset(hostname="data.example.org", catalog_id="1",
- `troubleshoot-execution/references/execution-lifecycle.md:443` **HIST-PROSE** — `legacy-marker`
  > Shows row counts and asset sizes per table (the legacy `estimate_bag_size` is subsumed by `deriva_ml_bag_info`). Use to 
- `troubleshoot-execution/references/execution-lifecycle.md:474` **REMOVED-TOOL** — `deriva_ml_update_execution`
  > | `deriva_ml_update_execution(hostname, catalog_id, execution_rid, description="<text>")` | Update an execution's descri
- `troubleshoot-execution/references/execution-lifecycle.md:475` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > | `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)` | Drain staged outputs (Running/Stopped/Failed/Pendi
- `troubleshoot-execution/references/execution-lifecycle.md:476` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > | `deriva_ml_abort_execution(hostname, catalog_id, execution_rid, reason=...)` | Cancel an execution; **destroys staged 

### `work-with-assets`

- `work-with-assets/SKILL.md:52` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > 1. `deriva_ml_create_execution(hostname, catalog_id, ...)` + `deriva_ml_start_execution(hostname, catalog_id, execution_
- `work-with-assets/SKILL.md:52` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > 1. `deriva_ml_create_execution(hostname, catalog_id, ...)` + `deriva_ml_start_execution(hostname, catalog_id, execution_
- `work-with-assets/SKILL.md:55` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > 4. `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)` — finalize on success (use `deriva_ml_abort_executi
- `work-with-assets/SKILL.md:55` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > 4. `deriva_ml_commit_execution(hostname, catalog_id, execution_rid)` — finalize on success (use `deriva_ml_abort_executi
- `work-with-assets/SKILL.md:111` **HIST-PROSE** — `used-to`
  > - **`/deriva:create-table`** *(deriva-skills)* — Generic table creation via `create_table`, used to build new asset tabl
- `work-with-assets/SKILL.md:113` **HIST-PROSE** — `used-to`
  > - **`/deriva:manage-vocabulary`** *(deriva-skills)* — Generic vocabulary CRUD via `add_term`/`delete_term`, used to mana
- `work-with-assets/references/concepts.md:127` **HIST-PROSE** — `legacy-marker`
  > The legacy `add_asset_type` shortcut was removed. When you create a new asset table by hand (see [Creating an Asset Tabl
- `work-with-assets/references/concepts.md:206` **HIST-PROSE** — `legacy-marker`
  > > **Known gap:** the legacy `create_asset_table` shortcut is gone. To create a new asset table you now use the deriva-sk
- `work-with-assets/references/restructure-guide.md:35` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `work-with-assets/references/restructure-guide.md:51` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Species", "Diagnosis"]
- `work-with-assets/references/restructure-guide.md:102` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `work-with-assets/references/restructure-guide.md:130` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `work-with-assets/references/restructure-guide.md:143` **SIG_DRIFT** — `restructure_assets(group_by=) → use targets=`
  > group_by=["Diagnosis"],
- `work-with-assets/references/restructure-guide.md:175` **HIST-PROSE** — `legacy-marker`
  > | (gap) Creating an asset table | Legacy `create_asset_table` was removed; use the manual `create_table` recipe — see `c
- `work-with-assets/references/restructure-guide.md:176` **HIST-PROSE** — `legacy-marker`
  > | `deriva_ml_bag_info(hostname, catalog_id, dataset_rid, version)` | Preview what a download will contain (subsumes the 
- `work-with-assets/references/workflow.md:40` **HIST-PROSE** — `legacy-marker`
  > To query with filters, call `get_entities(hostname="data.example.org", catalog_id="1", schema=<schema>, table="Image", f
- `work-with-assets/references/workflow.md:48` **HIST-PROSE** — `legacy-marker`
  > For the raw catalog row with all custom metadata columns, call `get_entities(hostname="data.example.org", catalog_id="1"
- `work-with-assets/references/workflow.md:83` **HIST-PROSE** — `legacy-marker`
  > - The legacy `list_asset_executions(asset_rid, asset_role="Input")` was removed. Use `deriva_ml_find_workflow_executions
- `work-with-assets/references/workflow.md:122` **HIST-PROSE** — `legacy-marker`
  > > **Known gap:** the legacy `create_asset_table` shortcut is gone. Build the table by hand using the deriva-skills `crea
- `work-with-assets/references/workflow.md:140` **REMOVED-TOOL** — `deriva_ml_start_execution`
  > Call `deriva_ml_create_execution(hostname="data.example.org", catalog_id="1", workflow_rid="<workflow_rid>", description
- `work-with-assets/references/workflow.md:140` **REMOVED-TOOL** — `deriva_ml_create_execution`
  > Call `deriva_ml_create_execution(hostname="data.example.org", catalog_id="1", workflow_rid="<workflow_rid>", description
- `work-with-assets/references/workflow.md:169` **REMOVED-TOOL** — `deriva_ml_commit_execution`
  > On success: call `deriva_ml_commit_execution(hostname="data.example.org", catalog_id="1", execution_rid=...)` to finaliz
- `work-with-assets/references/workflow.md:171` **REMOVED-TOOL** — `deriva_ml_abort_execution`
  > On failure: call `deriva_ml_abort_execution(hostname="data.example.org", catalog_id="1", execution_rid=...)` instead. (T
- `work-with-assets/references/workflow.md:171` **HIST-PROSE** — `legacy-marker`
  > On failure: call `deriva_ml_abort_execution(hostname="data.example.org", catalog_id="1", execution_rid=...)` instead. (T
- `work-with-assets/references/workflow.md:209` **HIST-PROSE** — `legacy-marker`
  > Call `add_term(hostname="data.example.org", catalog_id="1", schema="deriva-ml", table="Asset_Type", name=..., descriptio
- `work-with-assets/references/workflow.md:213` **HIST-PROSE** — `legacy-marker`
  > > **Known gap:** there is no dedicated tool. Use `update_entities` on the asset row's `Asset_Type` column. (The legacy `
- `work-with-assets/references/workflow.md:225` **HIST-PROSE** — `legacy-marker`
  > > **Known gap:** there is no dedicated tool. Use `update_entities` to clear the `Asset_Type` column (or delete the assoc
- `work-with-assets/references/workflow.md:241` **HIST-PROSE** — `legacy-marker`
  > Call `deriva_ml_lookup_asset(hostname, catalog_id, asset_rid)` — returns the producer execution (RID, workflow, status, 

### `write-hydra-config`

- `write-hydra-config/SKILL.md:3` **HIST-PROSE** — `PLANNED-for-shipped-tool`
  > description: "Write, bootstrap, and validate hydra-zen config files for DerivaML — DatasetSpecConfig, asset_store, build
- `write-hydra-config/SKILL.md:19` **HIST-PROSE** — `PLANNED-for-shipped-tool`
  > - **Validating that config RIDs and versions exist in the catalog** — singular per-group validators, whole-tree composit
- `write-hydra-config/SKILL.md:377` **HIST-PROSE** — `PLANNED-for-shipped-tool`
  > The agent that runs this drives one round-trip per `deriva_ml_get_dataset_spec` / `deriva_ml_lookup_asset`. That's toler
- `write-hydra-config/SKILL.md:426` **HIST-PROSE** — `ADR-reference`
  > > **Why not `dry_run=True`?** Setting `dry_run=True` on an Execution does validate the config, but by actually downloadi
- `write-hydra-config/SKILL.md:430` **HIST-PROSE** — `PLANNED-for-shipped-tool`
  > There's no asset analog to `deriva_ml_validate_dataset_specs` yet (planned for the future `deriva_ml_validate_config_fil
