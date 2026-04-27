---
name: new-model
description: "ALWAYS use this skill when creating a new DerivaML model function or adding a model to a project. Triggers on: 'create model', 'add model', 'new model', 'scaffold model', 'model function', 'write training code', 'add a training pipeline'. This skill covers authoring the model function itself and wiring it to configs, workflows, and experiments — the end-to-end process for adding a new model to a DerivaML project."
argument-hint: "[model-name]"
disable-model-invocation: true
---

# Create a New DerivaML Model

A DerivaML model is a plain Python function. The framework injects a DerivaML instance and an execution context at runtime — everything else becomes a configurable hyperparameter via hydra-zen. The runner handles the execution lifecycle (create, start, stop, upload), so the model function focuses on doing the work.

For how the runner interfaces with the model, data access patterns, and Python API `bag.restructure_assets()`, see `references/runner-interface.md`.

## Critical Rules

1. **`ml_instance` and `execution` go last** — they must have default `None` and are injected at runtime via `zen_partial=True`.
2. **Use `execution.asset_file_path()` for all outputs** — this both creates the file path and registers it for upload. Never write directly to the working directory.
3. **Use `"Execution_Asset"` for model outputs** — predictions, weights, plots. `"Execution_Metadata"` is reserved for framework-generated files.
4. **Access data through the execution object** — `execution.datasets` for downloaded bags, `execution.asset_paths` for individual assets. Never fetch data from the catalog directly.
5. **The model function returns `None`** — results are captured through registered output files, not return values.

## Steps

### 1. Create the model file

Create `src/models/<model_name>.py`:

```python
from deriva_ml import DerivaML
from deriva_ml.execution import Execution


def my_model(
    # Your hyperparameters (become configurable)
    learning_rate: float = 1e-3,
    epochs: int = 10,
    batch_size: int = 64,
    hidden_size: int = 128,
    # Framework-injected (always last, always default None)
    ml_instance: DerivaML | None = None,
    execution: Execution | None = None,
) -> None:
    """Train my model on the provided datasets."""
    # execution.datasets returns DatasetBag objects (not Dataset)
    # DatasetBag has: restructure_assets(), get_table_as_dict(), get_table_as_dataframe(), list_tables()
    for dataset in execution.datasets:
        dataset.restructure_assets(
            asset_table="Image",
            output_dir=execution.working_dir / "data",
            group_by=["My_Feature"],
        )

    # ... training logic ...

    # Save outputs — ALWAYS use asset_file_path
    output_path = execution.asset_file_path("Execution_Asset", "results.csv")
    # ... write results to output_path ...
```

### 2. Create the model config

Create `src/configs/<model_name>.py`. Use `builds()` with `zen_partial=True`:

```python
from hydra_zen import builds, store
from models.my_model import my_model

MyModelConfig = builds(
    my_model,
    learning_rate=1e-3,
    epochs=10,
    batch_size=64,
    hidden_size=128,
    populate_full_signature=True,
    zen_partial=True,
)

model_store = store(group="model_config")

model_store(
    MyModelConfig,
    name="default_model",
    zen_meta={"description": "Default config: 10 epochs, lr=1e-3, batch 64."},
)

# Variants override specific parameters
model_store(
    MyModelConfig,
    name="my_model_quick",
    epochs=3,
    batch_size=128,
    zen_meta={"description": "Quick run: 3 epochs for pipeline validation."},
)
```

See the `write-hydra-config` skill for the full config API reference.

### 3. Create a workflow

Add to `src/configs/workflow.py`:

```python
from hydra_zen import store, builds
from deriva_ml.execution import Workflow

MyWorkflow = builds(
    Workflow,
    name="My Model Training",
    workflow_type=["Training"],
    description="Train my model on the dataset. Outputs predictions and metrics.",
    populate_full_signature=True,
)

workflow_store = store(group="workflow")
workflow_store(MyWorkflow, name="my_workflow")
```

If this is the project's first or primary model, also set it as `default_workflow`.

### 4. Add experiments

Add to `src/configs/experiments.py`:

```python
from hydra_zen import make_config, store, MISSING
from configs.base import DerivaModelConfig

# IMPORTANT: group must be "experiment" (singular), package on constructor
experiment_store = store(group="experiment", package="_global_")

experiment_store(
    make_config(
        hydra_defaults=[
            "_self_",
            {"override /model_config": "my_model_quick"},
            {"override /datasets": "my_dataset"},
            {"override /workflow": "my_workflow"},
        ],
        description="Quick test of my model on the small dataset",
        bases=(DerivaModelConfig,),
    ),
    name="my_model_quick",
)
```

### 5. Test locally

```bash
# Check config resolves
uv run deriva-ml-run +experiment=my_model_quick --info

# Dry run (downloads data, runs model, no catalog writes)
uv run deriva-ml-run +experiment=my_model_quick dry_run=true
```

### 6. Git workflow for model development

Model development should follow a branch-based workflow. DerivaML records the git commit hash for provenance, so code must be committed and merged before production runs.

**Create a feature branch:**

```bash
git checkout -b feature/my-model
```

**Develop iteratively on the branch:**
- Write the model function, configs, workflow, and experiments (steps 1–4)
- Test with `dry_run=true` — dry runs don't record provenance, so uncommitted code is fine
- Commit working increments as you go:

```bash
git add src/models/my_model.py src/configs/my_model.py src/configs/workflow.py src/configs/experiments.py
git commit -m "Add my_model with quick and default configs"
```

**Push and create a pull request:**

```bash
git push -u origin feature/my-model
gh pr create --title "Add my_model training pipeline" --body "..."
```

**Use a PR even if you're the only developer.** PRs create a permanent record of what changed and why — this is especially valuable for ML projects where you may need to trace back why a model was structured a certain way months later. The PR description becomes part of the project's institutional memory alongside `experiment-decisions.md`.

The PR should include:
- Model function (`src/models/`)
- Config files (`src/configs/`)
- Updated `Experiments.md` if maintained
- Any new dependencies in `pyproject.toml`

**Using the GitHub CLI (`gh`):** If you have the [GitHub CLI](https://cli.github.com/) installed, Claude Code can create PRs, review diffs, and merge directly from the terminal. This makes the branch workflow lightweight even for solo developers — ask Claude to "create a PR and merge it" and it will handle the `gh pr create` and `gh pr merge` commands.

**Merge and bump version:**

After the PR is merged (or after you merge it yourself with `gh pr merge`):

```bash
git checkout main
git pull
uv run bump-version minor   # New model = new feature = minor bump
# Or use the MCP tool: bump_version("minor")
```

The version bump creates a git tag, giving production runs a clean version reference. Use `minor` for a new model; use `patch` if you're fixing an existing model.

**Now run for real** — see the `run-experiment` skill for the pre-flight checklist. The key point: production runs (without `dry_run=true`) should only happen on `main` after the merge and version bump, so the recorded commit hash and version tag are meaningful.

## Related Skills

- **`write-hydra-config`** — Config file syntax for every config group
- **`configure-experiment`** — Project structure, config groups, and experiment descriptions
- **`execution-lifecycle`** — Pre-flight checks, execution lifecycle, provenance, and CLI commands
- **`ml-data-engineering`** — Dataset downloading, splitting, and restructuring
