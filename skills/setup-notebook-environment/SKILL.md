---
name: setup-notebook-environment
description: "Set up the environment for running DerivaML Jupyter notebooks — install kernel, uv sync --group=jupyter, configure nbstripout, authenticate with Deriva. Use before developing or running notebooks for the first time."
disable-model-invocation: true
---

# Set Up Environment for DerivaML Notebooks

This skill walks through every step needed to set up a working environment for developing and running DerivaML Jupyter notebooks.

## Prerequisites

Before starting, ensure you have:

- Python 3.11 or later installed.
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`).
- A DerivaML project repository cloned locally.
- A Globus account with access to the target Deriva catalog.

## Step-by-Step Setup

### Step 1: Install Project Dependencies

```bash
uv sync
```

This installs the project and all its core dependencies in an isolated virtual environment.

### Step 2: Install Jupyter Dependencies

```bash
uv sync --group=jupyter
```

This installs JupyterLab, papermill, and any other notebook-related dependencies defined in the project's `pyproject.toml` under `[dependency-groups]`.

If the project does not have a `jupyter` dependency group, add the dependencies manually:

```bash
uv add --group jupyter jupyterlab papermill ipykernel
```

### Step 3: Install nbstripout

```bash
uv run nbstripout --install
```

**Why this matters:** `nbstripout` installs a Git filter that automatically strips notebook outputs (cell outputs, execution counts, metadata) before they are staged for commit. Without it:

- Notebook outputs bloat the repository with binary data (images, large tables).
- Every run creates merge conflicts in output cells.
- Sensitive data (file paths, credentials, intermediate results) may be committed accidentally.

The `--install` flag registers the filter in the repository's `.git/config` so it runs automatically on every `git add`.

Verify it is installed:
```bash
uv run nbstripout --status
```

### Step 4: Install the Jupyter Kernel

```bash
uv run deriva-ml-install-kernel
```

This registers the project's virtual environment as a Jupyter kernel. The kernel name is derived from the project name in `pyproject.toml`.

Alternatively, use the MCP tool:
- CLI `uv run deriva-ml-install-kernel` to install the kernel programmatically.

To verify the kernel was installed:
```bash
uv run jupyter kernelspec list
```

You should see an entry for your project (e.g., `my-ml-project`).

### Step 5: Authenticate to Deriva

```bash
uv run deriva-globus-auth-utils login --host ml.derivacloud.org
```

Replace `ml.derivacloud.org` with your target host. This opens a browser for Globus authentication and stores credentials locally.

To authenticate to multiple hosts:
```bash
uv run deriva-globus-auth-utils login --host ml.derivacloud.org
uv run deriva-globus-auth-utils login --host ml-dev.derivacloud.org
```

To verify authentication:
```bash
uv run deriva-globus-auth-utils login --host ml.derivacloud.org --no-browser
```

If already authenticated, this will confirm without opening a browser.

### Step 6: Verify the Setup

Start JupyterLab:

```bash
uv run jupyter lab
```

Then verify:

1. **Select the correct kernel**: In JupyterLab, create a new notebook or open an existing one. Select the kernel matching your project name (not the default Python 3 kernel).

2. **Test the import**: In the first cell, run:

```python
from deriva_ml import DerivaML

ml = DerivaML(hostname="ml.derivacloud.org", catalog_id="1")
print(f"Connected to {ml.host}, catalog {ml.catalog_id}")
```

If this succeeds without errors, your environment is ready.

## Optional: ML Framework Dependencies

Many DerivaML projects need additional ML framework dependencies. These are typically organized as dependency groups:

### PyTorch

```bash
uv sync --group=pytorch
# or if not predefined:
uv add torch torchvision torchaudio
```

### TensorFlow

```bash
uv sync --group=tensorflow
# or if not predefined:
uv add tensorflow
```

### JAX

```bash
uv add jax jaxlib
```

### scikit-learn

```bash
uv add scikit-learn
```

Check the project's `pyproject.toml` for predefined dependency groups before adding packages manually.

## Complete Checklist

- [ ] `uv sync` completed successfully
- [ ] `uv sync --group=jupyter` completed successfully
- [ ] `nbstripout --install` ran (verify with `--status`)
- [ ] Jupyter kernel installed (verify with `jupyter kernelspec list`)
- [ ] Authenticated to Deriva (verify with `login --no-browser`)
- [ ] JupyterLab starts and the project kernel is available
- [ ] `from deriva_ml import DerivaML` imports without error
- [ ] Can connect to the target catalog

## Reference Resources

- `deriva://docs/notebooks` — Notebook documentation
- `deriva://docs/install` — Installation reference
- `deriva://docs/deriva-py/install` — Deriva-Py installation guide

## Troubleshooting

### Kernel Not Showing in JupyterLab

**Symptom**: The project kernel does not appear in JupyterLab's kernel list.

**Fix**: Re-install the kernel and restart JupyterLab:
```bash
uv run deriva-ml-install-kernel
# Restart JupyterLab (stop and start again)
uv run jupyter lab
```

If that does not work, install manually:
```bash
uv run python -m ipykernel install --user --name my-project --display-name "My Project"
```

### nbstripout Not Working

**Symptom**: Notebook outputs are still being committed.

**Fix**: Verify the Git filter is installed:
```bash
uv run nbstripout --status
```

If it reports "not installed", re-run:
```bash
uv run nbstripout --install
```

Also check that `.gitattributes` contains:
```
*.ipynb filter=nbstripout
```

### Authentication Errors

**Symptom**: `AuthenticationError` or `401 Unauthorized` when connecting to Deriva.

**Fix**:
1. Re-authenticate:
   ```bash
   uv run deriva-globus-auth-utils login --host ml.derivacloud.org
   ```
2. Ensure you are authenticating to the correct host.
3. Verify your Globus identity has been granted access to the catalog.

### Missing Dependencies

**Symptom**: `ModuleNotFoundError` when importing packages.

**Fix**:
1. Make sure you ran `uv sync` (not just `uv install`).
2. Make sure you are using the correct kernel in JupyterLab (the project kernel, not the default).
3. Check if the missing package is in an optional dependency group:
   ```bash
   uv sync --group=jupyter  # or --group=pytorch, etc.
   ```

### JupyterLab Won't Start

**Symptom**: `jupyter lab` command not found or crashes.

**Fix**:
```bash
uv sync --group=jupyter
uv run jupyter lab
```

Note the `uv run` prefix -- this ensures JupyterLab runs within the project's virtual environment.
