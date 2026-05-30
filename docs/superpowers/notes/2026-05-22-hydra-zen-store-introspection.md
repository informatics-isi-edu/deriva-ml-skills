# Hydra-zen `ZenStore` introspection vs. AST parsing for config validation

**Date:** 2026-05-22
**Context:** Investigating whether hydra/hydra-zen exposes APIs that
would let `ConfigValidator` / `ConfigBootstrap` operate on resolved
Python objects instead of parsing source text with `ast`.

## TL;DR

Yes — hydra-zen's `ZenStore` is fully interrogable in-process once
`load_configs("configs")` has run. For the model runner / notebook
runner use case (where configs are already loaded), this is strictly
better than AST parsing. For the static-analysis use case (validating a
single config file on disk without executing user code), AST stays
relevant.

**Recommendation: add store-based introspection as a complementary
path; do not delete the AST walker.**

## What store introspection gives you

After `from deriva_ml.execution.base_config import load_configs;
load_configs("configs")`:

| API | What it returns |
|-----|-----------------|
| `store.groups` | `{None, 'hydra', 'datasets', 'assets', 'deriva_ml', 'workflow', 'model_config', 'experiment'}` |
| `store[group]` | dict-like view of `(group, name) -> node` |
| `store.get_entry(group, name)` | `{'name', 'group', 'package', 'provider', 'node'}` |
| `hydra_zen.get_target(node)` | the actual class (e.g. `deriva_ml.execution.workflow.Workflow`) |
| `dataclasses.fields(node)` | declared fields with defaults — `rid`, `version`, etc. |
| `hydra_zen.instantiate(node)` | the materialized object (`Workflow(...)`, `DatasetSpec(...)`) |

Verified end-to-end against the CIFAR-10 template:

```python
node = store.get_entry('workflow', 'cifar10_cnn')['node']
get_target(node)        # -> <class 'deriva_ml.execution.workflow.Workflow'>
obj = instantiate(node) # -> Workflow(name='CIFAR-10 2-Layer CNN', ...)
obj.rid                 # -> None (or the real RID when set)
```

For list-shaped groups (`datasets`, `assets`):

```python
node = store.get_entry('datasets', 'cifar10_complete')['node']
# -> [DatasetSpecConfig(rid='5-4WG2', version='0.21.0', ...)]
obj = instantiate(node)
# -> [DatasetSpec(rid='5-4WG2', version=<DatasetVersion('0.21.0')>, ...)]
```

## Key insight: store sees the resolved overlay

The base `configs/datasets.py` ships placeholder entries:

```python
datasets_store([], name="cifar10_complete")  # empty list
```

A dev overlay (`configs/dev/datasets_<env>.py`) re-registers with real
RIDs. When you walk the store after `load_configs`, you see the
**post-overlay merged state** — exactly what the model runner consumes.
AST parsing of `datasets.py` alone would see only the placeholders.

This is the single biggest reason store introspection is more accurate:
it operates on the resolved config graph, not on individual files.

## Comparison

|                                | AST walker                 | Store introspection                   |
|--------------------------------|----------------------------|---------------------------------------|
| Requires executing user code   | No                         | **Yes** (`load_configs("configs")`)   |
| Sees defaults composition      | No                         | Yes                                   |
| Sees dev overlay merge         | No                         | Yes                                   |
| Sees `with_description` wraps  | Yes (explicit unwrap)      | Yes (transparent)                     |
| Sees `builds()` indirection    | Yes (explicit handling)    | Yes (just instantiate)                |
| Sees module-level constants    | Yes (constant table)       | Yes (already resolved)                |
| Distinguishes config kinds     | String-matched class names | `get_target()` returns real class     |
| Works on partial / broken file | Yes (per-file)             | No — one bad module breaks the import |
| Works without project install  | Yes                        | No — needs `configs.*` importable     |
| Security                       | Safe (no exec)             | Executes whatever's in `configs/`     |

## Recommended split

**Keep AST walker for:**

- `deriva_ml_validate_config_file(file_path=...)` MCP tool — the
  "validate this one file" use case, where Claude has the file path
  but not necessarily a usable Python environment.
- Static linting in CI before configs are loaded.
- Validating a file with syntax / import errors that would prevent
  store population.

**Add store-introspection path for:**

- A new `validate_loaded_configs()` API that takes the populated
  `ZenStore` (or calls `load_configs` itself) and returns the same
  `ConfigValidationReport`. This is what the runner / notebook runner
  should call before any catalog write — it sees the real merged
  config tree, including dev overlay.
- A new bootstrap variant that *updates* an existing in-memory store
  in addition to / instead of producing source-code suggestions.

## Sketch of the store-based validator

```python
from dataclasses import fields, is_dataclass
from hydra_zen import get_target, instantiate, store

from deriva_ml.config.validation import (
    ConfigEntry,
    ConfigEntryResult,
    ConfigValidationReport,
)
from deriva_ml.dataset import DatasetSpec, DatasetSpecConfig
from deriva_ml.asset import AssetSpec  # etc.
from deriva_ml.execution.workflow import Workflow
from deriva_ml.execution.base_config import DerivaMLConfig

_KIND_BY_TARGET = {
    "deriva_ml.dataset.aux_classes.DatasetSpec": "dataset",
    "deriva_ml.execution.workflow.Workflow": "workflow",
    "deriva_ml.execution.base_config.DerivaMLConfig": "deriva_ml",
    # ...
}

def validate_store(ml) -> ConfigValidationReport:
    entries: list[ConfigEntryResult] = []
    for group in sorted(g for g in store.groups if g not in (None, "hydra")):
        for (g, name), entry in store[group].items():
            node = entry["node"]
            # Handle list-shaped groups
            items = node if isinstance(node, list) else [node]
            for idx, item in enumerate(items):
                kind = _classify(item)
                if kind is None:
                    continue
                obj = instantiate(item)
                rid = getattr(obj, "rid", None)
                # ... validate rid against catalog using existing logic ...
                entries.append(ConfigEntryResult(
                    entry=ConfigEntry(kind=kind, rid=rid, ...),
                    ...,
                ))
    return ConfigValidationReport(entries=entries, ...)
```

The validation half (RID lookup, version check, type check against
catalog) is identical to the AST path — we'd factor `_validate_config_entries`
to take a list of `ConfigEntry` records regardless of source.

## Open question: model-template's `configs/__init__.py`

`load_configs("configs")` exists in `deriva_ml.execution.base_config`
(line 374). It dynamically imports every child module of the package,
which is what fires the `store(group=...)` decorators. We rely on
existing template behavior — if a user removes that helper or
restructures their configs, store introspection breaks silently.
Decision: store-based path should call `load_configs` itself and
surface `ImportError` clearly.

## Next steps (deferred — not in this PR)

1. Add `ConfigValidator.validate_loaded_store()` in `deriva-ml`.
2. Expose `deriva_ml_validate_loaded_configs` MCP tool that takes a
   `configs_package` argument (defaults to `"configs"`) — runs
   `load_configs` then walks the store.
3. Update `write-hydra-config` skill to mention both: file-path
   validation (AST, can target a single file) vs. project-level
   validation (store, sees overlay).
4. Consider whether the runner should call `validate_loaded_store()`
   itself before any catalog write — fast pre-flight that catches
   missing dev overlay before the model trains for an hour.
