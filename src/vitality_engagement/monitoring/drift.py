"""Deterministic distribution-drift calculations for Stage 7 monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Final

import numpy as np
import pandas as pd
from numpy.typing import NDArray

DEFAULT_SMOOTHING_EPSILON: Final = 1e-6
MISSING_CATEGORY_LABEL: Final = "__missing__"


class DriftCalculationError(ValueError):
    """Raised when drift inputs or calculated distributions are invalid."""


@dataclass(frozen=True)
class NumericDriftResult:
    """Population-stability result for one numeric distribution."""

    psi: float
    bin_edges: tuple[float, ...]
    reference_proportions: tuple[float, ...]
    current_proportions: tuple[float, ...]

    def __post_init__(self) -> None:
        """Validate numeric drift output dimensions and values."""
        if not isfinite(self.psi) or self.psi < 0.0:
            raise DriftCalculationError("Numeric PSI must be finite and non-negative.")

        if len(self.bin_edges) < 2:
            raise DriftCalculationError("Numeric drift requires at least two bin edges.")

        expected_distribution_length = len(self.bin_edges)

        if len(self.reference_proportions) != expected_distribution_length:
            raise DriftCalculationError(
                "Reference proportions must include every numeric bin and missingness."
            )

        if len(self.current_proportions) != expected_distribution_length:
            raise DriftCalculationError(
                "Current proportions must include every numeric bin and missingness."
            )


@dataclass(frozen=True)
class CategoricalDriftResult:
    """Population-stability and unseen-rate result for one categorical feature."""

    psi: float
    unseen_category_rate: float
    categories: tuple[str, ...]
    reference_proportions: tuple[float, ...]
    current_proportions: tuple[float, ...]

    def __post_init__(self) -> None:
        """Validate categorical drift output dimensions and values."""
        if not isfinite(self.psi) or self.psi < 0.0:
            raise DriftCalculationError("Categorical PSI must be finite and non-negative.")

        if (
            not isfinite(self.unseen_category_rate)
            or self.unseen_category_rate < 0.0
            or self.unseen_category_rate > 1.0
        ):
            raise DriftCalculationError("Unseen-category rate must fall between zero and one.")

        if not self.categories:
            raise DriftCalculationError("Categorical drift requires at least one category.")

        if len(self.reference_proportions) != len(self.categories):
            raise DriftCalculationError("Reference proportions must match the categorical domain.")

        if len(self.current_proportions) != len(self.categories):
            raise DriftCalculationError("Current proportions must match the categorical domain.")


def _validate_series(
    values: pd.Series,
    *,
    field_name: str,
) -> None:
    """Require a non-empty pandas Series."""
    if not isinstance(values, pd.Series):
        raise DriftCalculationError(f"{field_name} must be a pandas Series.")

    if values.empty:
        raise DriftCalculationError(f"{field_name} must contain at least one row.")


def _validate_bin_count(bin_count: int) -> None:
    """Require a genuine integer with at least two requested bins."""
    if isinstance(bin_count, bool) or not isinstance(bin_count, int) or bin_count < 2:
        raise DriftCalculationError("bin_count must be an integer of at least two.")


def _numeric_array(
    values: pd.Series,
    *,
    field_name: str,
) -> NDArray[np.float64]:
    """Convert a numeric Series while preserving missing values."""
    _validate_series(
        values,
        field_name=field_name,
    )

    try:
        numeric = pd.to_numeric(
            values,
            errors="raise",
        ).to_numpy(dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise DriftCalculationError(f"{field_name} must contain numeric values.") from error

    if bool(np.isinf(numeric).any()):
        raise DriftCalculationError(f"{field_name} contains infinite values.")

    return numeric


def _smoothed_proportions(
    counts: NDArray[np.int64],
    *,
    smoothing_epsilon: float,
) -> NDArray[np.float64]:
    """Convert counts to strictly positive, normalised proportions."""
    if (
        isinstance(smoothing_epsilon, bool)
        or not isinstance(smoothing_epsilon, (int, float))
        or not isfinite(float(smoothing_epsilon))
        or smoothing_epsilon <= 0.0
    ):
        raise DriftCalculationError("smoothing_epsilon must be finite and positive.")

    smoothed = counts.astype(np.float64) + float(smoothing_epsilon)
    return smoothed / smoothed.sum()


def _population_stability_index(
    reference_proportions: NDArray[np.float64],
    current_proportions: NDArray[np.float64],
) -> float:
    """Calculate PSI from aligned, strictly positive distributions."""
    if reference_proportions.shape != current_proportions.shape:
        raise DriftCalculationError("PSI distributions must have matching dimensions.")

    if bool((reference_proportions <= 0.0).any()) or bool((current_proportions <= 0.0).any()):
        raise DriftCalculationError("PSI proportions must be strictly positive.")

    value = np.sum(
        (current_proportions - reference_proportions)
        * np.log(current_proportions / reference_proportions)
    )
    result = float(value)

    if not isfinite(result):
        raise DriftCalculationError("Calculated PSI is not finite.")

    return max(result, 0.0)


def calculate_numeric_psi(
    reference: pd.Series,
    current: pd.Series,
    *,
    bin_count: int,
    smoothing_epsilon: float = DEFAULT_SMOOTHING_EPSILON,
) -> NumericDriftResult:
    """Calculate numeric PSI using reference-derived quantile bins.

    Missing values are represented as an additional final distribution bin.
    """
    _validate_bin_count(bin_count)

    reference_values = _numeric_array(
        reference,
        field_name="reference",
    )
    current_values = _numeric_array(
        current,
        field_name="current",
    )

    reference_non_missing = reference_values[~np.isnan(reference_values)]
    current_non_missing = current_values[~np.isnan(current_values)]

    if reference_non_missing.size == 0:
        raise DriftCalculationError(
            "Numeric reference distribution must contain a non-missing value."
        )

    quantiles = np.linspace(
        0.0,
        1.0,
        bin_count + 1,
        dtype=np.float64,
    )
    quantile_values = np.quantile(
        reference_non_missing,
        quantiles,
    )
    if float(reference_non_missing.min()) == float(reference_non_missing.max()):
        interior_edges = np.array(
            [np.nextafter(reference_non_missing[0], np.inf)],
            dtype=np.float64,
        )
    else:
        interior_edges = np.unique(quantile_values[1:-1])

    bin_edges = np.concatenate(
        (
            np.array([-np.inf], dtype=np.float64),
            interior_edges.astype(np.float64),
            np.array([np.inf], dtype=np.float64),
        )
    )

    reference_counts = np.histogram(
        reference_non_missing,
        bins=bin_edges,
    )[0].astype(np.int64)
    current_counts = np.histogram(
        current_non_missing,
        bins=bin_edges,
    )[0].astype(np.int64)

    reference_counts = np.append(
        reference_counts,
        np.int64(np.isnan(reference_values).sum()),
    )
    current_counts = np.append(
        current_counts,
        np.int64(np.isnan(current_values).sum()),
    )

    reference_proportions = _smoothed_proportions(
        reference_counts,
        smoothing_epsilon=smoothing_epsilon,
    )
    current_proportions = _smoothed_proportions(
        current_counts,
        smoothing_epsilon=smoothing_epsilon,
    )

    return NumericDriftResult(
        psi=_population_stability_index(
            reference_proportions,
            current_proportions,
        ),
        bin_edges=tuple(float(value) for value in bin_edges),
        reference_proportions=tuple(float(value) for value in reference_proportions),
        current_proportions=tuple(float(value) for value in current_proportions),
    )


def _categorical_values(values: pd.Series, *, field_name: str) -> pd.Series:
    """Normalise categorical values while retaining explicit missingness."""
    _validate_series(
        values,
        field_name=field_name,
    )

    normalised = values.astype("string").fillna(MISSING_CATEGORY_LABEL)

    if bool(normalised.str.strip().eq("").any()):
        raise DriftCalculationError(f"{field_name} contains empty category values.")

    return normalised.astype(str)


def calculate_categorical_psi(
    reference: pd.Series,
    current: pd.Series,
    *,
    smoothing_epsilon: float = DEFAULT_SMOOTHING_EPSILON,
) -> CategoricalDriftResult:
    """Calculate categorical PSI and the current unseen-category rate."""
    reference_values = _categorical_values(
        reference,
        field_name="reference",
    )
    current_values = _categorical_values(
        current,
        field_name="current",
    )

    reference_categories = set(reference_values.tolist())
    current_categories = set(current_values.tolist())
    categories = tuple(sorted(reference_categories | current_categories))

    reference_counts = np.array(
        [int(reference_values.eq(category).sum()) for category in categories],
        dtype=np.int64,
    )
    current_counts = np.array(
        [int(current_values.eq(category).sum()) for category in categories],
        dtype=np.int64,
    )

    reference_proportions = _smoothed_proportions(
        reference_counts,
        smoothing_epsilon=smoothing_epsilon,
    )
    current_proportions = _smoothed_proportions(
        current_counts,
        smoothing_epsilon=smoothing_epsilon,
    )

    unseen_categories = current_categories - reference_categories
    unseen_count = int(current_values.isin(unseen_categories).sum())
    unseen_category_rate = unseen_count / len(current_values)

    return CategoricalDriftResult(
        psi=_population_stability_index(
            reference_proportions,
            current_proportions,
        ),
        unseen_category_rate=float(unseen_category_rate),
        categories=categories,
        reference_proportions=tuple(float(value) for value in reference_proportions),
        current_proportions=tuple(float(value) for value in current_proportions),
    )
