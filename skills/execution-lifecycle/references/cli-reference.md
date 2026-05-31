# Run an Experiment with deriva-ml-run

This skill covers the pre-flight checks and CLI commands for running experiments using `deriva-ml-run`. It assumes your hydra-zen configs are already set up (see the `configure-experiment` skill).

> The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. Substitute your catalog's hostname (e.g., `"data.example.org"`) and catalog ID (e.g., `"1"`) wherever the examples show them. (`deriva-ml-run` itself reads its `hostname`/`catalog` from the Hydra config or from CLI overrides — not affected by MCP statelessness.)

## Pre-Flight Checklist

Before running any experiment, complete these checks. **Stop and fix any issues before proceeding.**

### 1. Check Git Status

```bash
git status
```

**Stop if there are uncommitted changes.** Every execution records the git commit hash. Uncommitted changes make runs non-reproducible.

If there are changes:
```bash
git add -A
git commit -m "Prepare for experiment run"
```

### 2. Check Version

```bash
uv run python -c "import my_project; print(my_project.__version__)"
```

If you have made meaningful changes since the last run, bump the version:

```bash
# Use the MCP tool or CLI:
uv run bump-version patch   # For small changes
uv run bump-version minor   # For new features
```

The `bump-version` command automatically commits and tags. No separate `git add`/`git commit` needed.

### 3. Verify Lock File

```bash
uv lock --check
```

If this fails, regenerate and commit:
```bash
uv lock
git add uv.lock
git commit -m "Update uv.lock"
```

### 4. Get User Confirmation

Before running, present a summary to the user:

```
Ready to run experiment:
  Commit:  abc1234
  Version: 0.3.1
  Branch:  feature/new-model
  Status:  clean (no uncommitted changes)
  Experiment: +experiment=baseline

Proceed? [y/N]
```

Do not run without confirmation for production (non-dry-run) experiments.

## Verify Configuration

Before running, inspect the resolved configuration. There are several ways to view the config without executing anything:

### deriva-ml-run --list-configs (the config menu)

```bash
uv run deriva-ml-run --list-configs
```

This prints the *menu* of registered `group=value` options (the named
experiments, datasets, assets, model configs, workflows, multiruns the
project has registered). It ignores any overrides on the command line —
it answers "what can I select?", not "what does *this* selection resolve
to?". Use it to discover valid override values.

### deriva-ml-run +experiment=X --cfg job (the resolved config)

```bash
uv run deriva-ml-run +experiment=baseline --cfg job
```

This renders the fully *resolved* config that the given overrides compose
to — all defaults, overrides, and interpolations applied — without
executing the run. This is Hydra's native `--cfg`; see the `--cfg`
section below for `--package` scoping. Use it to confirm a specific
experiment resolves the way you expect before running.

`deriva-ml-run` forwards every Hydra command-line flag to Hydra, so the
full Hydra surface is available (`--cfg job|hydra|all`, `--info
config|defaults|searchpath|...`, `--resolve`, `--package`, etc.). See
<https://hydra.cc/docs/advanced/hydra-command-line-flags/>.

### Standard Hydra --cfg (full resolved YAML)

```bash
# Full resolved config as YAML
uv run deriva-ml-run +experiment=baseline --cfg job

# Just the datasets group
uv run deriva-ml-run +experiment=baseline --cfg job --package datasets

# Just the assets group
uv run deriva-ml-run +experiment=baseline --cfg job --package assets

# Just the model config
uv run deriva-ml-run +experiment=baseline --cfg job --package model_config
```

The `--cfg job` output shows exactly what the execution will receive — all defaults, overrides, and interpolations fully resolved. Use `--package` to focus on a specific config group.

### What to verify

- The correct host and catalog are selected
- The expected dataset RIDs and versions appear
- Asset RIDs are correct
- Model parameters are what you intend
- `dry_run` is set as expected

## Running Experiments

### Test First with Dry Run

Always run with `dry_run=True` first to validate the pipeline end-to-end without persisting results:

```bash
uv run deriva-ml-run +experiment=baseline dry_run=True
```

This will:
- Resolve and validate the full config.
- Download datasets and assets.
- Run the training function.
- **Not** upload results to the catalog.

### Production Run

```bash
uv run deriva-ml-run +experiment=baseline
```

Or explicitly:

```bash
uv run deriva-ml-run +experiment=baseline dry_run=False
```

### CLI Options

| Option | Purpose | Example |
|---|---|---|
| `--host` | Override the Deriva host | `--host ml-dev.derivacloud.org` |
| `--catalog` | Override the catalog ID | `--catalog 99` |
| `--list-configs` | Print the menu of registered config groups/options and exit | `--list-configs` |
| `--cfg job` | Print the resolved config (no execution) | `+experiment=baseline --cfg job` |
| `--multirun` | Enable multirun mode for sweeps | `--multirun` |

### Hydra Overrides

Override any config value from the command line:

```bash
# Select a named experiment
uv run deriva-ml-run +experiment=baseline

# Override dataset config group
uv run deriva-ml-run datasets=cell_images_v3

# Override model config group
uv run deriva-ml-run model_config=resnet50_long

# Override individual parameters
uv run deriva-ml-run model_config.learning_rate=0.001 model_config.epochs=50

# Set dry_run
uv run deriva-ml-run +experiment=baseline dry_run=True

# Combine overrides
uv run deriva-ml-run +experiment=baseline model_config.learning_rate=0.01 dry_run=False
```

### Running Sweeps (Multirun)

For parameter sweeps defined with `multirun_config()` (no `--multirun` flag needed):

```bash
uv run deriva-ml-run +multirun=lr_batch_sweep
```

For ad-hoc sweeps using Hydra's comma syntax:

```bash
uv run deriva-ml-run +experiment=baseline model_config.learning_rate=1e-2,1e-3,1e-4 --multirun
```

For running multiple named experiments:

```bash
uv run deriva-ml-run +experiment=baseline,long_training --multirun
```

## Verify Results

### Check Executions

After the run completes, verify the execution was recorded. Use the MCP tools:

- `deriva_ml_list_executions(hostname="data.example.org", catalog_id="1")` to list recent executions.
- `deriva_ml_get_execution(hostname="data.example.org", catalog_id="1", execution_rid="...")` for details on a specific execution.

The same content is available via the resource `deriva://catalog/{hostname}/{catalog_id}/deriva-ml/execution/{rid}`.

### View in Chaise

Open the execution in the web interface. The Chaise URL is typically:

```
https://{host}/chaise/record/#{catalog_id}/{schema}:Execution/RID={execution_rid}
```

Use `cite(hostname, catalog_id, rid)` to generate a permanent URL for an execution.

Verify:
- The execution status is "Completed".
- The correct datasets and versions are linked.
- Output assets and metrics are attached.
- The git commit hash matches your expectation.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `Config error: could not find experiments/X` | Experiment name not registered in store | Check `experiments.py` for the `name=` parameter |
| `Connection refused` | Wrong host or host is down | Verify `--host` value, check network |
| `Authentication error` | Expired or missing credentials | Run `deriva-globus-auth-utils login --host {host}` |
| `Dataset not found: RID=...` | RID does not exist in the target catalog | Verify RIDs match the target catalog (dev vs prod) |
| `Version X not found for dataset` | Requested version does not exist | Check available versions with `deriva_ml_get_dataset(hostname, catalog_id, dataset_rid)` |
| `Dirty git state warning` | Uncommitted changes when running | Commit changes before running |
| `Lock file out of date` | `uv.lock` does not match `pyproject.toml` | Run `uv lock` and commit |
| `ModuleNotFoundError` | Dependencies not installed | Run `uv sync` |
| `Multirun requires --multirun flag` | Ad-hoc sweep without the flag | Add `--multirun` for ad-hoc sweeps; named multiruns (`+multirun=X`) don't need it |
| `dry_run output looks wrong` | Config resolution issue | Use `--cfg job` to inspect the resolved config |
