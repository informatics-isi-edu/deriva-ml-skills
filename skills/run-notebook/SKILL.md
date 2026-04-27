---
name: run-notebook
description: "ALWAYS use this skill when creating, developing, or running DerivaML Jupyter notebooks with execution tracking. Triggers on: 'create notebook', 'new notebook', 'add notebook', 'scaffold notebook', 'run notebook', 'jupyter', 'notebook structure', 'deriva-ml-run-notebook', 'notebook with provenance', 'notebook_config', 'run_notebook', 'notebook development', 'notebook workflow'."
disable-model-invocation: true
---

# Create and Run a DerivaML Notebook

DerivaML notebooks use hydra-zen configuration (not papermill parameters) and a single `run_notebook()` call that handles connection, execution context, config resolution, and dataset/asset downloading automatically. When run via the CLI runner, the executed notebook with all outputs is stored in the catalog as an execution asset.

## Prerequisite: Connect to a Catalog

Notebooks interact with a Deriva catalog for data and provenance. Ensure a connection exists:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step. Note that `run_notebook()` can also accept `host`/`catalog_id` parameters to establish the connection.

## The Development Cycle

Notebook development follows three stages, each building confidence that the notebook works correctly before committing to a tracked production run.

### Stage 1: Interactive Cell-by-Cell Development

Open the notebook in JupyterLab and run cells one at a time. This is the exploratory phase — experiment with data loading, try different visualizations, debug transforms, iterate on analysis logic.

The first cell calls `run_notebook()`, which creates a real execution context and downloads inputs. All subsequent cells use the `ml`, `execution`, and `config` objects it returns. Use `dry_run=true` as a Hydra override during development to avoid creating catalog records:

```python
ml, execution, config = run_notebook("my_analysis", overrides=["dry_run=true"])
```

This stage is where most of the creative work happens. Add, remove, and reorder cells freely.

### Stage 2: Restart & Run All

Once the notebook works cell-by-cell, restart the kernel and run all cells from top to bottom (**Kernel → Restart Kernel and Run All Cells** in JupyterLab). This catches hidden state dependencies — variables that exist only because you ran cells out of order, imports that got lost when you deleted a cell, etc.

A notebook that only works interactively but fails on Restart & Run All is broken. Fix any issues before moving on.

### Stage 3: Production Run via CLI

The CLI runner (`deriva-ml-run-notebook`) executes the notebook with full provenance tracking and stores the results in the catalog. This is the production step:

```bash
# Dry run first to verify everything works end-to-end
uv run deriva-ml-run-notebook notebooks/my_analysis.ipynb dry_run=true

# Production run (creates execution record, uploads outputs)
uv run deriva-ml-run-notebook notebooks/my_analysis.ipynb
```

The CLI runner does several things beyond what happens interactively:
1. Records the git commit hash and repository URL for code provenance
2. Executes the notebook via papermill (all cells, top to bottom)
3. Converts the executed notebook (with all outputs) to Markdown
4. Uploads both the `.ipynb` and `.md` as `Execution_Asset` records in the catalog
5. Uploads any other assets the notebook registered via `asset_file_path()`

**Commit code before production runs.** The runner records the git commit hash in the execution record. Uncommitted changes mean the execution won't have a valid code reference for reproducibility.

## How the Executed Notebook is Stored

When `deriva-ml-run-notebook` finishes, it stores two versions of the executed notebook as execution assets (type `notebook_output`):

- **The `.ipynb` file** — the full notebook with all cell outputs (plots, tables, print statements). This is the machine-readable record; it can be re-opened in JupyterLab to inspect every output exactly as it appeared.
- **The `.md` file** — a Markdown conversion with images embedded as base64 data URIs and DataFrames converted to Markdown tables. This is the human-readable record; it renders directly in the catalog UI without needing JupyterLab.

Both files are linked to the execution record. Together with the git commit hash, they form a complete provenance trail: the code that ran, the configuration it used, and the exact outputs it produced.

Any additional assets the notebook saved via `execution.asset_file_path()` (plots, CSVs, model weights) are uploaded alongside these notebook files.

## Creating a New Notebook

### Step 1: Define a Configuration Module

Create `src/configs/<notebook_name>.py`. The configuration uses hydra-zen — no YAML files, no papermill parameter cells.

**Simple notebook** (standard fields only — assets, datasets, workflow):
```python
from deriva_ml.execution import notebook_config

notebook_config(
    "<notebook_name>",
    defaults={"assets": "my_assets", "datasets": "my_dataset"},
)
```

**Notebook with custom parameters:**
```python
from dataclasses import dataclass
from deriva_ml.execution import BaseConfig, notebook_config

@dataclass
class MyAnalysisConfig(BaseConfig):
    threshold: float = 0.5
    num_iterations: int = 100

notebook_config(
    "<notebook_name>",
    config_class=MyAnalysisConfig,
    defaults={"assets": "my_assets"},
)
```

`BaseConfig` provides standard fields (`assets`, `datasets`, `dry_run`, `deriva_ml` connection settings) that every notebook gets. Custom parameters extend these — they become attributes on the resolved config object (e.g., `config.threshold`).

Multiple named configs can share one file, referencing different asset or dataset groups:
```python
notebook_config(
    "<notebook_name>",
    defaults={"assets": "my_assets"},
)

notebook_config(
    "<notebook_name>_variant",
    defaults={"assets": "other_assets", "datasets": "other_dataset"},
)
```

See the `write-hydra-config` skill for the full config API reference and rules.

### Step 2: Create the Notebook

Create `notebooks/<notebook_name>.ipynb`. The notebook needs two special cells — an initialization cell at the top and an upload cell at the bottom. Everything in between is your analysis.

**The configuration cell** (first code cell):

```python
from deriva_ml.execution import run_notebook

ml, execution, config = run_notebook("<notebook_name>")
```

This single call replaces what would otherwise be dozens of lines of boilerplate. It:
1. Loads all configuration modules from `src/configs/`
2. Resolves the hydra-zen config by name (merging defaults, overrides, and custom parameters)
3. Creates a DerivaML connection using the resolved host/catalog settings
4. Creates a workflow and execution record in the catalog
5. Downloads any datasets and assets specified in the config

The three return values are everything the rest of the notebook needs:
- **`ml`** — the connected DerivaML instance (query tables, look up assets, etc.)
- **`execution`** — the execution context (working directory with downloaded data, `asset_file_path()` for outputs)
- **`config`** — the resolved configuration object (access custom parameters as attributes)

There are no papermill parameter cells, no tagged cells, no manual connection setup. The config name passed to `run_notebook()` must match a `notebook_config()` name from Step 1.

**The upload cell** (last code cell):

```python
execution.upload_execution_outputs()
```

This uploads all files registered via `execution.asset_file_path()` to the catalog. Place it as the final cell so all outputs are captured.

**Saving output files** — use `asset_file_path()` to register files for upload:

```python
plot_path = execution.asset_file_path("Execution_Asset", "my_plot.jpg")
fig.savefig(plot_path)
```

### Step 3: Run

```bash
# Show available configs and overrides
uv run deriva-ml-run-notebook notebooks/<notebook_name>.ipynb --info

# Run with defaults
uv run deriva-ml-run-notebook notebooks/<notebook_name>.ipynb

# Override assets or datasets (positional Hydra overrides, NOT --config)
uv run deriva-ml-run-notebook notebooks/<notebook_name>.ipynb assets=different_assets

# Override host/catalog
uv run deriva-ml-run-notebook notebooks/<notebook_name>.ipynb \
    --host www.example.org --catalog 2
```

`--config` does NOT override the `run_notebook()` config name in the notebook cell. Use positional Hydra overrides instead.

## Concrete Example: ROC Analysis Notebook

This example from the model template shows a complete notebook that compares model predictions across experiments.

**Config module** (`src/configs/roc_analysis.py`):
```python
from dataclasses import dataclass
from deriva_ml.execution import BaseConfig, notebook_config

@dataclass
class ROCAnalysisConfig(BaseConfig):
    show_per_class: bool = True
    confidence_threshold: float = 0.0

notebook_config(
    "roc_analysis",
    config_class=ROCAnalysisConfig,
    defaults={"assets": "roc_quick_vs_extended", "datasets": "no_datasets"},
    description="ROC curve analysis (default: quick vs extended training)",
)

# Variant for learning rate sweep
notebook_config(
    "roc_lr_sweep",
    config_class=ROCAnalysisConfig,
    defaults={"assets": "roc_lr_sweep", "datasets": "no_datasets"},
    description="ROC analysis: learning rate sweep",
)
```

**Notebook initialization cell**:
```python
from deriva_ml.execution import run_notebook

ml, execution, config = run_notebook("roc_analysis", workflow_type="ROC Analysis Notebook")

# config.assets — list of prediction CSV asset RIDs (downloaded automatically)
# config.show_per_class — whether to plot individual class curves
# config.confidence_threshold — minimum confidence filter
# execution.asset_paths — paths to downloaded asset files
```

**Using downloaded assets** — the execution context makes them available by table name:
```python
for asset_path in execution.asset_paths.get('Execution_Asset', []):
    if asset_path.file_name.name == "prediction_probabilities.csv":
        df = pd.read_csv(asset_path.file_name)
```

**Saving outputs**:
```python
roc_path = execution.asset_file_path("Execution_Asset", "roc_curves.jpg")
fig.savefig(roc_path, format='jpeg', dpi=150)
```

**Running with different configs**:
```bash
# Default: quick vs extended comparison
uv run deriva-ml-run-notebook notebooks/roc_analysis.ipynb

# Learning rate sweep assets instead
uv run deriva-ml-run-notebook notebooks/roc_analysis.ipynb assets=roc_lr_sweep
```

## Critical Rules

1. **Clear outputs before committing** — use `nbstripout` or Kernel → Restart and Clear Outputs
2. **Commit before production runs** — git hash is recorded in the execution record
3. **Test with dry run** — `uv run deriva-ml-run-notebook notebooks/<name>.ipynb dry_run=true`
4. **Use `asset_file_path()` for all output files** — this registers them for upload
5. **Config name must match** — the string in `run_notebook("<name>")` must match a `notebook_config("<name>")` call

## MCP Tools

- `inspect_notebook(notebook_path)` — view notebook structure and tags without running
- `run_notebook(notebook_path, config_name, dry_run, host, catalog_id)` — execute notebook with parameters and return execution RID. The `config_name` selects the named config defined with `notebook_config()`. Use `host`/`catalog_id` to override the catalog connection.

## Pre-Production Checklist

- [ ] Config module created in `src/configs/`
- [ ] `run_notebook("<name>")` call in first cell matches config name
- [ ] `upload_execution_outputs()` in final cell
- [ ] Runs end-to-end with Restart & Run All
- [ ] Outputs cleared, code committed, version bumped

For environment setup (kernel installation, nbstripout, authentication), see the `setup-notebook-environment` skill. For detailed troubleshooting, read `references/workflow.md`.
