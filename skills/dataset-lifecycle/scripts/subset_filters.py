"""Filter Registry for Dataset Subset Generation.

Provides common filter implementations for selecting records from
denormalized DataFrames. Each filter takes a dict of DataFrames
(keyed by source dataset RID) and returns selected RIDs with a
description of the selection.

Custom filters can be registered with @register_filter("name") and
referenced by name in hydra configs via filter_name parameter.

Built-in filters:
  - all_records: All records from the element table (no filtering)
  - has_feature: Records that have a non-null value for a feature column
  - feature_equals: Records where a feature column matches a specific value
  - feature_in: Records where a feature column is in a list of values
  - numeric_range: Records where a numeric column is within bounds
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class FilterFunction(Protocol):
    """Protocol for filter functions.

    Args:
        dataframes: Dict mapping source dataset RID to its denormalized DataFrame.
            For single-source subsets, this has one entry.
        element_table: Table whose RIDs are collected for the new dataset.
        **kwargs: Filter-specific parameters from filter_params config.

    Returns:
        Tuple of (list of selected RIDs, human-readable description of selection).
    """

    def __call__(
        self,
        dataframes: dict[str, pd.DataFrame],
        *,
        element_table: str,
        **kwargs,
    ) -> tuple[list[str], str]: ...


FILTER_REGISTRY: dict[str, FilterFunction] = {}


def register_filter(name: str):
    """Decorator to register a filter function by name."""
    def decorator(fn):
        FILTER_REGISTRY[name] = fn
        return fn
    return decorator


def get_filter(name: str) -> FilterFunction:
    """Look up a registered filter by name with a helpful error message."""
    if name not in FILTER_REGISTRY:
        available = ", ".join(sorted(FILTER_REGISTRY.keys()))
        raise ValueError(f"Unknown filter '{name}'. Available filters: {available}")
    return FILTER_REGISTRY[name]


# =============================================================================
# Shared helpers
# =============================================================================


def _merge_dataframes(
    dataframes: dict[str, pd.DataFrame],
    element_table: str,
) -> pd.DataFrame:
    """Concatenate source DataFrames and validate the RID column exists.

    Raises:
        ValueError: If no source DataFrames are provided.
        KeyError: If the expected RID column is missing.
    """
    if not dataframes:
        raise ValueError("No source DataFrames provided — source_dataset_rids may be empty")
    df = pd.concat(dataframes.values(), ignore_index=True)
    rid_col = f"{element_table}.RID"
    if rid_col not in df.columns:
        available = sorted(c for c in df.columns if c.endswith(".RID"))
        raise KeyError(
            f"Column '{rid_col}' not found in DataFrame. "
            f"RID columns available: {available}"
        )
    return df


def _extract_rids(df: pd.DataFrame, element_table: str) -> list[str]:
    """Extract unique RIDs from a DataFrame."""
    return df[f"{element_table}.RID"].unique().tolist()


def _validate_column(df: pd.DataFrame, column: str) -> None:
    """Validate that a column exists in the DataFrame.

    Raises:
        KeyError: If the column is not present, with a list of available columns.
    """
    if column not in df.columns:
        available = sorted(c for c in df.columns if not c.startswith("_"))
        raise KeyError(
            f"Column '{column}' not found in DataFrame. "
            f"Available columns: {available}"
        )


# =============================================================================
# Built-in filters
# =============================================================================


@register_filter("all_records")
def all_records(
    dataframes: dict[str, pd.DataFrame],
    *,
    element_table: str,
    **kwargs,
) -> tuple[list[str], str]:
    """Select all records from the element table — no filtering.

    Use this to create a dataset containing every record in a table.
    The subset template treats this as a pass-through filter.
    """
    df = _merge_dataframes(dataframes, element_table)
    rids = _extract_rids(df, element_table)

    desc = f"Selected all {len(rids)} records from {element_table}"
    return rids, desc


@register_filter("has_feature")
def has_feature(
    dataframes: dict[str, pd.DataFrame],
    *,
    element_table: str,
    column: str,
    **kwargs,
) -> tuple[list[str], str]:
    """Select records that have a non-null value for a feature column.

    Use this to build datasets of labeled records from a larger set that
    may contain unlabeled data. For example, selecting all images that
    have an Image_Class label.
    """
    df = _merge_dataframes(dataframes, element_table)
    _validate_column(df, column)
    selected = df[df[column].notna()]
    rids = _extract_rids(selected, element_table)

    total = df[f"{element_table}.RID"].nunique()
    desc = f"Selected {len(rids)} of {total} records that have a value for {column}"
    return rids, desc


@register_filter("feature_equals")
def feature_equals(
    dataframes: dict[str, pd.DataFrame],
    *,
    element_table: str,
    column: str,
    value: str,
    **kwargs,
) -> tuple[list[str], str]:
    """Select records where a feature column matches a specific value."""
    df = _merge_dataframes(dataframes, element_table)
    _validate_column(df, column)
    selected = df[df[column] == value]
    rids = _extract_rids(selected, element_table)

    desc = f"Selected {len(rids)} records where {column} = '{value}'"
    return rids, desc


@register_filter("feature_in")
def feature_in(
    dataframes: dict[str, pd.DataFrame],
    *,
    element_table: str,
    column: str,
    values: list[str],
    **kwargs,
) -> tuple[list[str], str]:
    """Select records where a feature column is in a list of values."""
    df = _merge_dataframes(dataframes, element_table)
    _validate_column(df, column)
    selected = df[df[column].isin(values)]
    rids = _extract_rids(selected, element_table)

    if len(values) > 10:
        values_str = ", ".join(values[:10]) + f", ... ({len(values)} total)"
    else:
        values_str = ", ".join(values)
    desc = f"Selected {len(rids)} records where {column} in: {values_str}"
    return rids, desc


@register_filter("numeric_range")
def numeric_range(
    dataframes: dict[str, pd.DataFrame],
    *,
    element_table: str,
    column: str,
    min_val: float | None = None,
    max_val: float | None = None,
    **kwargs,
) -> tuple[list[str], str]:
    """Select records where a numeric column is within bounds.

    At least one of min_val or max_val must be specified.
    """
    if min_val is None and max_val is None:
        raise ValueError(
            "numeric_range requires at least one of min_val or max_val. "
            "Use 'all_records' or 'has_feature' if no bounds are needed."
        )
    df = _merge_dataframes(dataframes, element_table)
    _validate_column(df, column)
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise TypeError(
            f"Column '{column}' has dtype '{df[column].dtype}', expected a numeric type"
        )
    mask = df[column].notna()
    if min_val is not None:
        mask = mask & (df[column] >= min_val)
    if max_val is not None:
        mask = mask & (df[column] <= max_val)
    selected = df[mask]
    rids = _extract_rids(selected, element_table)

    bounds = []
    if min_val is not None:
        bounds.append(f">= {min_val}")
    if max_val is not None:
        bounds.append(f"<= {max_val}")
    desc = f"Selected {len(rids)} records where {column} {' and '.join(bounds)}"
    return rids, desc
