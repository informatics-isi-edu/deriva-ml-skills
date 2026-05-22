# Config bootstrap + whole-file validate APIs — design

**Status:** design, not yet implemented
**Date:** 2026-05-22
**Author:** session with Carl
**Implementation lives in:** `deriva-ml` (Python APIs) + `deriva-ml-mcp` (tool wrappers)
**Consumers:** `deriva-ml-skills/write-hydra-config` + `dataset-lifecycle` + `work-with-assets` + `execution-lifecycle`

## Problem

DerivaML's hydra-zen config files (`src/configs/*.py`) reference catalog
state by RID + version. Three kinds of operation on those files are
worth platform support:

1. **Bootstrap** — given a populated catalog and an empty `src/configs/`,
   produce a populated set of config files that pin sensible RIDs.
2. **Validate** — given a `src/configs/` tree, check that every RID in
   every file resolves in the catalog at the version the file pins.
3. **Update after action** — after creating / releasing / splitting a
   dataset or uploading an asset, offer to write the resulting RID
   into the appropriate config file.

The third (update-after-action) is **already covered as skill prose** —
`dataset-lifecycle`, `work-with-assets`, and `execution-lifecycle` each
own the offer for the operations they perform. That side of the
problem doesn't need new platform code.

The first two (bootstrap + validate) are partly covered today by
composition of existing MCP tools (`deriva_ml_validate_dataset_specs`,
`deriva_ml_lookup_asset`, `deriva_ml_get_dataset_spec`,
`deriva_ml_list_datasets`, etc.), but the composition is N round-trips
per file and the validation logic ends up duplicated across multiple
skill bodies. A platform-level API would consolidate the catalog-read
side; the file-write side stays in skill prose.

## Design choice — Hybrid (Alternative C in the session discussion)

| Concern | Owned by |
|---|---|
| Catalog interrogation (read RIDs, validate versions, find candidate entities) | `deriva-ml` Python API + `deriva-ml-mcp` MCP wrappers |
| File manipulation (writing config entries into the right file with the right grouping and description text) | Per-skill prose — `dataset-lifecycle` for datasets, `work-with-assets` and `execution-lifecycle` for assets |

Rationale:

- **Catalog interrogation is uniform** across dataset / asset / workflow / execution. One implementation, one test suite, one source of truth for what "the canonical spec string for RID X" looks like.
- **File manipulation is contextual** — when `dataset-lifecycle` adds a dataset spec, it knows the user just created a `Training` dataset and wants the right grouping. A generic `add_to_config` API can't reason about the context that drove the operation. Asking the user one question per insertion is the right UX.
- **AST-only validation** keeps the validator safe against arbitrary user code in the configs/ dir. The validator parses; it does not execute.

Alternatives considered and rejected:

- **All in skills (prose only)** — works today but the per-tool composition is hard to test as a unit, and validation logic ends up duplicated. We've already proven this approach with the current skill prose; this design is the next step.
- **Full API-first (Alternative B in the session discussion)** — APIs that read AND write the config files. Rejected: file-mutation APIs are fragile against hand-edited Python (comments, type aliases, hydra-zen `builds()` indirection), and `MCP server's filesystem view ≠ user's filesystem view` makes path-passing brittle.

## API surface

### `deriva-ml` Python API

Two new top-level classes in a new module `deriva_ml.config`:

```python
class ConfigBootstrap:
    """Build suggested config entries by reading the catalog."""

    @classmethod
    def from_catalog(
        cls,
        ml: DerivaML,
        *,
        kinds: list[str] | None = None,
        dataset_type_filter: list[str] | None = None,
    ) -> BootstrapReport:
        """Return suggested config entries for each requested group.

        Args:
            ml: Connected DerivaML instance.
            kinds: Which config groups to bootstrap. None = all of
                ['deriva_ml', 'datasets', 'assets', 'workflow'].
                Skipping 'experiments' / 'multiruns' / 'model_config'
                is intentional — those are project code, not catalog state.
            dataset_type_filter: When bootstrapping 'datasets', limit
                to these Dataset_Type terms (default: ['Training',
                'Testing', 'Validation', 'Complete', 'Labeled']).
                Pass [] to include every type.

        Returns:
            BootstrapReport with per-kind suggestions and per-entry
            commentary (RID, kind, canonical spec string, description,
            heuristics that led to its inclusion).

        Does NOT write files. Caller formats results into the appropriate
        config file -- per-skill prose owns the write.
        """


class ConfigValidator:
    """Walk a config file or directory and validate against the catalog."""

    @classmethod
    def validate_file(
        cls,
        ml: DerivaML,
        path: pathlib.Path | str,
    ) -> ValidationReport:
        """Parse one config file via AST and validate every entry.

        Detects DatasetSpecConfig, AssetSpecConfig, Workflow,
        DerivaMLConfig constructor calls. Reads the file from disk
        WITHOUT executing it. Returns per-entry per-failure-mode
        results.

        Args:
            ml: Connected DerivaML instance.
            path: Path to the config file. Must be readable as Python
                source via tokenize.open().

        Returns:
            ValidationReport with per-entry results (file, line,
            entry_kind, rid, version, valid, reasons, helpful detail).
        """

    @classmethod
    def validate_dir(
        cls,
        ml: DerivaML,
        configs_dir: pathlib.Path | str,
    ) -> ValidationReport:
        """Walk every *.py in configs_dir and validate. Aggregates
        per-file reports into one ValidationReport. Skips files that
        fail to parse (with a parse-error reason).
        """
```

### Pydantic report models

Live in `deriva_ml/config/validation.py` (parallel to
`deriva_ml/dataset/validation.py`):

```python
class BootstrapSuggestion(BaseModel):
    kind: Literal["deriva_ml", "datasets", "assets", "workflow"]
    config_name: str  # what to name the entry in the store (e.g., "cifar10_training")
    spec_string: str  # ready-to-paste Python: 'DatasetSpecConfig(rid="...", version="...")'
    rid: str
    version: str | None = None
    description: str | None = None
    rationale: str  # why this entry was suggested (e.g., "Training type, released version")


class BootstrapReport(BaseModel):
    catalog: dict[str, str]  # {"hostname": ..., "catalog_id": ...}
    suggestions: list[BootstrapSuggestion]
    skipped: list[dict]  # entities considered but not suggested, with reason


class ConfigEntryResult(BaseModel):
    file: str
    line: int
    entry_kind: Literal["DatasetSpecConfig", "AssetSpecConfig",
                        "Workflow", "DerivaMLConfig"]
    rid: str | None  # None when validation failed to extract a RID
    version: str | None
    valid: bool
    reasons: list[str]  # rid_not_found, version_not_found, etc.
    detail: dict  # e.g., {"available_versions": [...]} for version_not_found


class ValidationReport(BaseModel):
    file_count: int
    entry_count: int
    all_valid: bool
    results: list[ConfigEntryResult]
    parse_errors: list[dict]  # {file, line, reason} for files that failed to parse
```

### AST strategy for `ConfigValidator.validate_file`

The implementation walks `ast.Call` nodes whose `func` resolves (by
name match — we don't try to follow imports) to one of the known
spec-class names. For each match:

1. Extract `rid=` kwarg's `Constant` value.
2. Extract `version=` kwarg's `Constant` value if present.
3. Note source location (file + line).
4. Add to a per-kind work queue.

After the AST walk, batch the dataset queue into one
`validate_dataset_specs` call, loop the asset queue through
`lookup_asset`, the workflow queue through `get_workflow`, and the
deriva_ml queue through a heartbeat. Stitch results back into a single
ValidationReport ordered by file + line.

**Edge cases the AST handler must cope with:**

- `with_description(DatasetSpecConfig(rid=...), "...")` — wrapped call;
  unwrap until we find the spec constructor.
- `builds(DatasetSpec, rid=..., version=...)` — hydra-zen's lazy
  partial. Treat `builds(<spec_class>, ...)` the same as the spec
  class call.
- RIDs passed as a module-level constant (`TRAINING_RID = "2-B4C8";
  DatasetSpecConfig(rid=TRAINING_RID, ...)`) — resolve via a single
  pass that builds a name→value map of `ast.Constant` assignments at
  module scope. Don't try to resolve anything more complex; emit a
  `cannot_resolve_rid` reason instead of a false positive.
- Comments containing `DatasetSpecConfig(rid="...")` — AST handles
  these correctly (they're not parsed).

### MCP tool surface

Two new tools, both in `deriva-ml-mcp/src/deriva_ml_mcp/tools/`:

```
deriva_ml_bootstrap_config(
    hostname: str,
    catalog_id: str,
    kinds: list[str] | None = None,
    dataset_type_filter: list[str] | None = None,
) -> JSON string of BootstrapReport
```

```
deriva_ml_validate_config_file(
    hostname: str,
    catalog_id: str,
    file_path: str | None = None,     # absolute path on the MCP server's filesystem
    file_contents: str | None = None,  # OR pass contents directly
) -> JSON string of ValidationReport
```

The `file_path` / `file_contents` either-or shape sidesteps the
"MCP server's filesystem ≠ user's filesystem" problem: callers that
have the file open can pass contents; callers that can mount a path
into the MCP server's view can pass the path. The MCP test profile
mounts `../../../deriva-mcp-core/src` already (see
`deriva-docker/deriva/mcp/docker-compose.yml`); a similar mount for
user configs is doable but not yet wired up.

`deriva_ml_validate_config_dir` is intentionally *not* a separate MCP
tool — let the agent call `validate_config_file` per file. The Python
API exposes `validate_dir` for notebook / CLI users.

## Implementation plan

Three commits, in this order:

1. **deriva-ml**: new `deriva_ml/config/` module — `bootstrap.py`,
   `validation.py` (Pydantic models), `_ast.py` (AST walker),
   `__init__.py` exports. Plus `ConfigBootstrap` and
   `ConfigValidator` classes. Plus tests in `tests/config/` covering:
   - AST: every spec-class constructor pattern, the
     `with_description(...)` wrap, the `builds(...)` indirection,
     module-level constant resolution.
   - Bootstrap: fixture catalog with mixed dataset types; assert
     filter behavior.
   - Validate: fixture configs with known-good and known-bad entries;
     assert per-entry results.

2. **deriva-ml-mcp**: tool wrappers in
   `tools/config/bootstrap.py` and `tools/config/validate.py`. Add
   `deriva_ml.config` to the existing `_pkg` import surface.
   Pydantic response models in `_response_models.py` mirror the
   deriva-ml report models (don't re-export — redeclare locally to
   keep the wire contract independent of upstream).
   Tests in `tests/test_config_bootstrap.py` and
   `tests/test_config_validate.py` patch the underlying deriva-ml
   API the same way `test_dataset_complex.py` does for split.

3. **deriva-ml-skills**: update the skill prose to point at the new
   tools. `write-hydra-config/SKILL.md`:
   - Bootstrap section currently says "Until that lands, the per-tool
     composition above is the canonical recipe." → replace with the
     `deriva_ml_bootstrap_config` call.
   - Validate section currently says the same about
     `deriva_ml_validate_config_file`. → replace.
   - Keep the per-tool composition as a fallback for the case where
     the MCP server is on an old version.

## Open questions

These were not resolved in the design session. Decisions captured here
so the implementer doesn't relitigate:

1. **`bootstrap` heuristics for which workflow RIDs to include.** Most
   projects mint workflows at first-run, so bootstrapping workflow
   RIDs is rare. For now, only suggest workflow entries when the
   `workflow.py` template has a `workflow_store(...)` registration
   AND the catalog has matching `Workflow_Type` terms; otherwise skip.

2. **Whether bootstrap should write a complete `experiments.py`
   stitching.** Open. Default: no — `experiments.py` is composition,
   and the bootstrap can't reasonably guess which datasets pair with
   which workflows. Mention in the report's `skipped` field
   ("experiments composition deferred to user").

3. **Validation depth for `Workflow` entries.** Open. Today's tools
   distinguish a Workflow row from a Workflow_Type term; the
   validator could conflate them. Default: report both as separate
   `reasons` (`workflow_rid_not_found` vs `workflow_type_term_unknown`).

4. **What to do about parse errors mid-walk?** Open. Default: include
   them in `ValidationReport.parse_errors`, don't abort. A single
   broken file shouldn't hide validation issues in the others.

5. **`assets.py` is structurally different from `datasets.py`** — assets
   are usually grouped (a single config name pins multiple asset
   RIDs from one execution). Bootstrap suggestion shape needs to
   reflect this. Default: one `BootstrapSuggestion` per asset RID;
   the writer (skill prose) groups them.

## Out of scope

- File mutation. The platform never writes config files. Skill prose
  owns that.
- Mutation diff preview. If we add mutation later, it goes through
  a separate `ConfigEditor` class with a `propose_diff` → `apply_diff`
  shape. Not in this plan.
- Format preservation. AST-based validation reads source but doesn't
  rewrite it. If we add mutation later, we use `libcst` (not `ast`)
  for round-trip-safe edits.
- Whole-project audit (cross-file consistency, "does this experiment
  config reference a dataset that exists in datasets.py"). The
  composition is a `ValidationReport` cross-walk that lives in skill
  prose for now. If it becomes a pattern, lift to a third
  classmethod `validate_project`.

## Estimated scope

- **deriva-ml**: ~500 LOC implementation + ~400 LOC tests
- **deriva-ml-mcp**: ~250 LOC tool wrappers + ~250 LOC tests
- **deriva-ml-skills**: ~50 LOC of skill prose updates (replace the
  "until it lands" placeholders)
- **Release coordination**: deriva-ml patch release → deriva-ml-mcp
  lockfile bump + patch release → model-template lockfile bump

Single careful session, probably 4–6 hours of writing + testing + the
release dance.
