# DerivaML Notebook Workflow Reference

This reference covers the full notebook development lifecycle, from environment setup through production execution and troubleshooting.

## Contents

1. [Environment Setup](#environment-setup)
2. [Development Cycle In Detail](#development-cycle-in-detail)
3. [How run_notebook() Works](#how-run_notebook-works)
4. [How the CLI Runner Works](#how-the-cli-runner-works)
5. [Configuration Patterns](#configuration-patterns)
6. [Overriding Configuration at Runtime](#overriding-configuration-at-runtime)
7. [Troubleshooting](#troubleshooting)

---

## Environment Setup

Before starting, confirm your environment is ready.

```bash
# Install dependencies including Jupyter support
uv sync --group=jupyter

# Verify the project kernel is installed
uv run jupyter kernelspec list   # Should show your project kernel

# Verify catalog authentication
uv run deriva-globus-auth-utils login --host ml.derivacloud.org --no-browser
```

See the `setup-notebook-environment` skill for detailed setup instructions (kernel installation, nbstripout configuration, authentication).

---

## Development Cycle In Detail

### Stage 1: Interactive Cell-by-Cell

Open the notebook in JupyterLab and run the initialization cell first:

```python
from deriva_ml.execution import run_notebook

ml, execution, config = run_notebook("my_analysis")
```

This creates a live connection to the catalog and downloads any configured datasets/assets into the execution's working directory. From here, run subsequent cells one at a time. This lets you:

- Inspect `config` to verify parameters resolved correctly
- Check `execution.asset_paths` to see what was downloaded
- Query the catalog via `ml` to explore data
- Prototype analysis logic with immediate feedback
- Debug data loading, transforms, and visualizations

**Tips for interactive development:**

- Use `overrides=["dry_run=true"]` in the `run_notebook()` call to skip creating a catalog execution record while iterating
- If the kernel disconnects mid-session, re-running the init cell creates a new execution context — any state from previous cells is lost
- Keep imports in their own cell at the top (before `run_notebook()`) so they survive kernel restarts

### Stage 2: Restart & Run All

This is the gate between "it works on my machine" and "it actually works." Hidden state dependencies are the most common notebook bug — for example, a variable defined in a cell you deleted still exists in memory because you ran it earlier.

In JupyterLab: **Kernel → Restart Kernel and Run All Cells**

Common failures at this stage:
- `NameError` — a variable was defined in a cell you ran interactively but later removed or moved
- Import ordering — a function uses a library imported in a later cell
- Cell output dependencies — a cell uses the display output of a previous cell rather than a variable

Fix these until the notebook runs cleanly from top to bottom.

### Stage 3: CLI Production Run

```bash
# Always dry-run first
uv run deriva-ml-run-notebook notebooks/my_analysis.ipynb dry_run=true

# Commit code (the runner records the git hash)
git add -A && git commit -m "Notebook ready for production"

# Production run
uv run deriva-ml-run-notebook notebooks/my_analysis.ipynb
```

---

## How run_notebook() Works

The `run_notebook()` Python function (from `deriva_ml.execution`) is what the notebook calls in its first code cell. It handles all the setup that would otherwise require manual boilerplate.

```python
def run_notebook(
    config_name: str,
    overrides: list[str] | None = None,
    workflow_name: str | None = None,
    workflow_type: str = "Analysis Notebook",
    ml_class: type[DerivaML] | None = None,
    config_package: str = "configs",
) -> tuple[DerivaML, Execution, BaseConfig]
```

**What it does internally:**

1. **Loads config modules** — auto-discovers all Python modules in `src/configs/` and registers their hydra-zen stores
2. **Resolves configuration** — composes the named config with any overrides using Hydra's resolver
3. **Creates DerivaML connection** — instantiates `DerivaML(hostname, catalog_id)` from the resolved `deriva_ml` config group
4. **Creates workflow** — calls `ml.create_workflow()` using the git repo URL (if available) or a local path
5. **Creates execution** — builds an `ExecutionConfiguration` with the resolved datasets and assets, then creates an `Execution` which downloads inputs to its working directory
6. **Returns the tuple** — `(ml, execution, config)` ready for the notebook to use

**Key design choice:** Configuration is Python code (hydra-zen dataclasses), not YAML or papermill parameters. This means:
- Type checking and IDE autocomplete work on config objects
- Complex config (nested structures, cross-references) is natural Python
- No tagged parameter cells needed — the config name in `run_notebook("name")` is the only link between the notebook and its configuration

---

## How the CLI Runner Works

The `deriva-ml-run-notebook` command is the production execution path. It wraps the notebook in a full provenance-tracked pipeline.

**What happens when you run `deriva-ml-run-notebook notebooks/my_analysis.ipynb`:**

1. **Environment setup** — sets environment variables for the notebook:
   - `DERIVA_ML_WORKFLOW_URL`: git remote URL (or local path if not in a repo)
   - `DERIVA_ML_WORKFLOW_CHECKSUM`: MD5 of the notebook file
   - `DERIVA_ML_NOTEBOOK_PATH`: absolute path to the notebook
   - `DERIVA_ML_HYDRA_OVERRIDES`: JSON-encoded list of any Hydra overrides from the CLI

2. **Notebook execution** — runs the notebook via papermill, which executes every cell top-to-bottom and captures all outputs (plots, print statements, tables)

3. **Metadata extraction** — reads the execution RID and connection details that the notebook saved during `run_notebook()`. If the notebook was in dry-run mode, stops here.

4. **Execution restoration** — reconnects to the catalog and restores the execution context created by the notebook

5. **Notebook conversion** — converts the executed notebook to Markdown:
   - HTML DataFrame tables become Markdown tables
   - Plot images become base64-encoded data URIs (self-contained, no external files)

6. **Asset registration** — registers both the executed `.ipynb` and the `.md` as `Execution_Asset` records with type `notebook_output`

7. **Upload** — calls `upload_execution_outputs()` which uploads:
   - The executed `.ipynb` (with all cell outputs preserved)
   - The `.md` conversion (human-readable, renders in catalog UI)
   - Any assets the notebook itself registered via `asset_file_path()`

8. **Status update** — marks the execution as complete and prints the execution URL

**The output notebook is a first-class catalog asset.** It's linked to the execution record alongside any other outputs (plots, CSVs, model weights). Anyone reviewing the execution can open the notebook to see exactly what ran and what it produced.

---

## Configuration Patterns

### The Configuration Cell

The first code cell in every DerivaML notebook is the configuration cell:

```python
from deriva_ml.execution import run_notebook

ml, execution, config = run_notebook("<config_name>")
```

This replaces the old pattern of papermill parameter cells with tagged cells. There are no `# Parameters` comments, no cell tags to set, no manual `DerivaML()` construction. The config name is the single point of connection between the notebook and its hydra-zen configuration.

### Why Not Papermill Parameters?

Papermill injects parameters by inserting a new cell after a tagged "parameters" cell. This approach has limitations:
- Parameters are flat key-value pairs (no nesting, no complex types)
- No type checking or validation
- No composition — can't build on shared base configs
- YAML parameter files are disconnected from code

Hydra-zen configuration provides:
- **Typed dataclass configs** with IDE support and validation
- **Composition** via config groups (swap asset sets, dataset versions, connection targets)
- **Defaults** that cascade naturally
- **Python-native** — configs live in `src/configs/` as importable modules

### BaseConfig Fields

Every notebook config inherits from `BaseConfig`, which provides:

| Field | Type | Purpose |
|-------|------|---------|
| `assets` | list[str] | Asset RIDs to download |
| `datasets` | list[DatasetSpecConfig] | Dataset specs to download |
| `dry_run` | bool | Skip catalog writes when True |
| `deriva_ml` | DerivaMLConfig | Connection settings (host, catalog, schema) |

Custom config classes add domain-specific parameters on top of these.

### Config Groups

Configs compose via hydra-zen groups. The `defaults` dict in `notebook_config()` selects which group members to use:

```python
notebook_config(
    "my_analysis",
    defaults={
        "assets": "my_asset_set",       # selects from assets group
        "datasets": "my_dataset",        # selects from datasets group
        "deriva_ml": "default_deriva",   # selects connection target
    },
)
```

Each group is defined in its own config module (e.g., `src/configs/assets.py`, `src/configs/datasets.py`).

---

## Overriding Configuration at Runtime

### Interactive (in notebook)

Pass overrides as a list of strings:

```python
ml, execution, config = run_notebook(
    "roc_analysis",
    overrides=["assets=roc_lr_sweep", "dry_run=true"],
)
```

### CLI

Pass overrides as positional arguments after the notebook path:

```bash
# Override asset group
uv run deriva-ml-run-notebook notebooks/roc_analysis.ipynb assets=roc_lr_sweep

# Override connection
uv run deriva-ml-run-notebook notebooks/roc_analysis.ipynb \
    --host www.example.org --catalog 2

# Override custom parameters
uv run deriva-ml-run-notebook notebooks/roc_analysis.ipynb \
    show_per_class=false confidence_threshold=0.5

# Dry run
uv run deriva-ml-run-notebook notebooks/roc_analysis.ipynb dry_run=true

# Show available configs
uv run deriva-ml-run-notebook notebooks/roc_analysis.ipynb --info
```

**Important:** `--config` does NOT override the config name inside the `run_notebook()` call. Use positional Hydra overrides to change specific values.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `NameError` on config variables | Config name mismatch or no `notebook_config()` with that name | Verify the string in `run_notebook("name")` matches a `notebook_config("name")` call |
| `No kernel named X` | Project kernel not installed | Run `uv run deriva-ml-install-kernel` |
| Execution status stuck at "Running" | Notebook crashed without clean exit | Use `update_execution_status` MCP tool to set to "Failed" |
| Outputs still in committed notebook | `nbstripout` not installed | Run `uv run nbstripout --install` |
| `PapermillExecutionError` | A cell raised an exception during CLI run | Check the output notebook for the traceback |
| `AuthenticationError` during execution | Credentials expired mid-run | Re-authenticate and re-run |
| Files not appearing in catalog | `upload_execution_outputs()` not called or not in final cell | Add it as the last code cell |
| Dry run skips upload | Expected behavior | Remove `dry_run=true` for production runs |
| `--config` doesn't change notebook behavior | `--config` is a CLI flag, not a Hydra override | Use positional overrides: `assets=other_assets` |
| Config attribute missing on `config` object | Custom parameter not in the config dataclass | Add it to your `BaseConfig` subclass |
