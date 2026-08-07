"""Tests for deterministic Stage 7 drift calculations."""

import math

import pandas as pd
import pytest

from vitality_engagement.monitoring.drift import (
    MISSING_CATEGORY_LABEL,
    DriftCalculationError,
    calculate_categorical_psi,
    calculate_numeric_psi,
)


def test_identical_numeric_distributions_have_zero_psi() -> None:
    reference = pd.Series(
        [1.0, 2.0, 3.0, 4.0, 5.0, None],
        dtype="float64",
    )

    result = calculate_numeric_psi(
        reference,
        reference.copy(),
        bin_count=4,
    )

    assert result.psi == pytest.approx(0.0)
    assert len(result.reference_proportions) == len(result.bin_edges)
    assert len(result.current_proportions) == len(result.bin_edges)
    assert sum(result.reference_proportions) == pytest.approx(1.0)
    assert sum(result.current_proportions) == pytest.approx(1.0)


def test_shifted_numeric_distribution_has_positive_psi() -> None:
    reference = pd.Series(
        list(range(100)),
        dtype="float64",
    )
    current = pd.Series(
        list(range(100, 200)),
        dtype="float64",
    )

    result = calculate_numeric_psi(
        reference,
        current,
        bin_count=10,
    )

    assert result.psi > 0.0
    assert math.isfinite(result.psi)


def test_numeric_psi_tracks_missingness_as_separate_bin() -> None:
    reference = pd.Series(
        [1.0, 2.0, 3.0, 4.0],
        dtype="float64",
    )
    current = pd.Series(
        [1.0, None, None, None],
        dtype="float64",
    )

    result = calculate_numeric_psi(
        reference,
        current,
        bin_count=2,
    )

    assert result.psi > 0.0
    assert result.current_proportions[-1] > result.reference_proportions[-1]


def test_constant_numeric_reference_is_supported() -> None:
    reference = pd.Series(
        [5.0, 5.0, 5.0, 5.0],
        dtype="float64",
    )
    current = pd.Series(
        [5.0, 5.0, 6.0, 6.0],
        dtype="float64",
    )

    result = calculate_numeric_psi(
        reference,
        current,
        bin_count=10,
    )

    assert result.bin_edges[0] == -math.inf
    assert result.bin_edges[-1] == math.inf
    assert len(result.reference_proportions) == 3
    assert result.psi > 0.0
    assert math.isfinite(result.psi)


def test_numeric_psi_rejects_empty_reference() -> None:
    with pytest.raises(
        DriftCalculationError,
        match="at least one row",
    ):
        calculate_numeric_psi(
            pd.Series([], dtype="float64"),
            pd.Series([1.0], dtype="float64"),
            bin_count=2,
        )


def test_numeric_psi_rejects_all_missing_reference() -> None:
    with pytest.raises(
        DriftCalculationError,
        match="non-missing value",
    ):
        calculate_numeric_psi(
            pd.Series([None, None], dtype="float64"),
            pd.Series([1.0, 2.0], dtype="float64"),
            bin_count=2,
        )


def test_numeric_psi_rejects_infinite_values() -> None:
    with pytest.raises(
        DriftCalculationError,
        match="infinite",
    ):
        calculate_numeric_psi(
            pd.Series([1.0, float("inf")]),
            pd.Series([1.0, 2.0]),
            bin_count=2,
        )


def test_numeric_psi_rejects_invalid_bin_count() -> None:
    with pytest.raises(
        DriftCalculationError,
        match="at least two",
    ):
        calculate_numeric_psi(
            pd.Series([1.0, 2.0]),
            pd.Series([1.0, 2.0]),
            bin_count=1,
        )


def test_identical_categorical_distributions_have_zero_psi() -> None:
    reference = pd.Series(
        ["low", "moderate", "high", None],
        dtype="string",
    )

    result = calculate_categorical_psi(
        reference,
        reference.copy(),
    )

    assert result.psi == pytest.approx(0.0)
    assert result.unseen_category_rate == pytest.approx(0.0)
    assert MISSING_CATEGORY_LABEL in result.categories
    assert sum(result.reference_proportions) == pytest.approx(1.0)
    assert sum(result.current_proportions) == pytest.approx(1.0)


def test_categorical_psi_reports_unseen_category_rate() -> None:
    reference = pd.Series(
        ["low", "low", "high", "high"],
        dtype="string",
    )
    current = pd.Series(
        ["low", "new", "new", "high"],
        dtype="string",
    )

    result = calculate_categorical_psi(
        reference,
        current,
    )

    assert result.psi > 0.0
    assert result.unseen_category_rate == pytest.approx(0.5)
    assert "new" in result.categories


def test_categorical_distribution_shift_without_unseen_values() -> None:
    reference = pd.Series(
        ["low"] * 90 + ["high"] * 10,
        dtype="string",
    )
    current = pd.Series(
        ["low"] * 10 + ["high"] * 90,
        dtype="string",
    )

    result = calculate_categorical_psi(
        reference,
        current,
    )

    assert result.psi > 0.0
    assert result.unseen_category_rate == pytest.approx(0.0)


def test_categorical_psi_rejects_empty_values() -> None:
    with pytest.raises(
        DriftCalculationError,
        match="empty category",
    ):
        calculate_categorical_psi(
            pd.Series(["low", ""]),
            pd.Series(["low", "high"]),
        )


def test_categorical_psi_rejects_empty_series() -> None:
    with pytest.raises(
        DriftCalculationError,
        match="at least one row",
    ):
        calculate_categorical_psi(
            pd.Series([], dtype="string"),
            pd.Series(["low"], dtype="string"),
        )
