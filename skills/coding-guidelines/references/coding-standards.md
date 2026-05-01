# Coding Standards Reference

Detailed templates, examples, and configuration for DerivaML project coding standards.

## Docstring Format

Use Google-style docstrings for all public functions and classes.

### Function Docstring Template

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """One-line summary of what the function does.

    Optional extended description providing additional context,
    algorithm details, or usage notes.

    Args:
        param1: Description of the first parameter.
        param2: Description of the second parameter.

    Returns:
        Description of the return value. For complex returns,
        describe the structure, e.g. {"accuracy": 0.95, "loss": 0.12}.

    Raises:
        ValueError: When the input is invalid.
        FileNotFoundError: When the expected file is missing.
    """
```

### Class Docstring Template

```python
class MyModel(DerivaModel):
    """One-line summary of the class.

    Optional extended description covering the purpose of the class,
    its relationship to other components, and usage patterns.

    Attributes:
        model: The underlying neural network.
        optimizer: Training optimizer instance.
    """
```

### Full Example

```python
def train_model(config: ModelConfig, dataset_path: Path) -> dict[str, float]:
    """Train the classification model on the provided dataset.

    Args:
        config: Model hyperparameters and architecture configuration.
        dataset_path: Path to the downloaded and extracted dataset.

    Returns:
        Dictionary of metric names to final values, e.g.
        {"accuracy": 0.95, "loss": 0.12}.

    Raises:
        ValueError: If the dataset contains no samples.
    """
```

## Type Hint Conventions

Use type hints on all function signatures. Use modern Python typing syntax (Python 3.11+).

### Preferred Patterns

```python
from pathlib import Path
from collections.abc import Sequence, Iterator

# Use lowercase generics (Python 3.11+), not typing.List/Dict/Optional
def load_images(directory: Path, extensions: list[str] | None = None) -> list[Path]:
    ...

def compute_metrics(predictions: dict[str, list[float]]) -> dict[str, float]:
    ...

# Use X | None instead of Optional[X]
def find_checkpoint(run_dir: Path) -> Path | None:
    ...

# Use collections.abc for abstract types
def process_batches(batches: Sequence[torch.Tensor]) -> Iterator[dict[str, float]]:
    ...
```

### Key Rules

- Always annotate function parameters and return types.
- Use `X | None` instead of `Optional[X]`.
- Use lowercase `list`, `dict`, `tuple`, `set` instead of `typing.List`, etc.
- Use `collections.abc.Sequence`, `collections.abc.Iterator`, etc. for abstract container types.
- Omit type hints on `self` and `cls` parameters.

## Ruff Configuration

Configure ruff in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

### Rule Sets

| Code | Category | What It Catches |
|------|----------|-----------------|
| `E` | pycodestyle errors | Syntax and style errors |
| `F` | Pyflakes | Unused imports, undefined names |
| `I` | isort | Import ordering |
| `N` | pep8-naming | Naming conventions |
| `W` | pycodestyle warnings | Style warnings |
| `UP` | pyupgrade | Modernize syntax for target Python version |

### Running Ruff

```bash
uv run ruff check src/       # Lint
uv run ruff check src/ --fix  # Lint with auto-fix
uv run ruff format src/       # Format
```

## Semantic Versioning

DerivaML projects follow semantic versioning. The version is recorded in every execution, creating a direct link between code and results.

| Change Type | Version Bump | Example |
|---|---|---|
| Fix a bug in data loading | patch | 0.1.0 -> 0.1.1 |
| Add a new model architecture | minor | 0.1.1 -> 0.2.0 |
| Restructure the config system | major | 0.2.0 -> 1.0.0 |

The version lives in `pyproject.toml` and is managed by the `bump-version` tool.

```bash
uv run bump-version patch  # 0.1.0 -> 0.1.1
uv run bump-version minor  # 0.1.1 -> 0.2.0
uv run bump-version major  # 0.2.0 -> 1.0.0
```
