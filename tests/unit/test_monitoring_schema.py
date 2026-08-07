"""Tests for governed Stage 7 monitoring result contracts."""

import pytest

from vitality_engagement.monitoring.schema import (
    MonitoringCheckResult,
    MonitoringCheckType,
    MonitoringContractError,
    MonitoringSeverity,
    classify_upper_threshold,
    maximum_severity,
)


def test_valid_probability_drift_result_is_accepted() -> None:
    result = MonitoringCheckResult(
        check_name="probability_population_stability_index",
        check_type=MonitoringCheckType.PROBABILITY_DRIFT,
        severity=MonitoringSeverity.WARNING,
        observed_value=0.15,
        expected_value=0.0,
        warning_threshold=0.10,
        critical_threshold=0.25,
        reference_row_count=46_000,
        current_row_count=3_500,
        details="Probability PSI reached the configured warning range.",
    )

    assert result.severity is MonitoringSeverity.WARNING
    assert result.feature_name is None
    assert result.reference_row_count == 46_000
    assert result.current_row_count == 3_500


@pytest.mark.parametrize(
    "check_type",
    [
        MonitoringCheckType.NUMERIC_FEATURE_DRIFT,
        MonitoringCheckType.CATEGORICAL_FEATURE_DRIFT,
        MonitoringCheckType.UNSEEN_CATEGORY_RATE,
    ],
)
def test_feature_level_checks_require_feature_name(
    check_type: MonitoringCheckType,
) -> None:
    with pytest.raises(
        MonitoringContractError,
        match="require feature_name",
    ):
        MonitoringCheckResult(
            check_name="feature_check",
            check_type=check_type,
            severity=MonitoringSeverity.PASS,
            observed_value=0.0,
            details="Feature-level result without a feature name.",
        )


def test_monitoring_result_rejects_incomplete_threshold_pair() -> None:
    with pytest.raises(
        MonitoringContractError,
        match="provided together",
    ):
        MonitoringCheckResult(
            check_name="probability_drift",
            check_type=MonitoringCheckType.PROBABILITY_DRIFT,
            severity=MonitoringSeverity.PASS,
            observed_value=0.05,
            warning_threshold=0.10,
            details="Only one threshold was provided.",
        )


def test_monitoring_result_rejects_reversed_thresholds() -> None:
    with pytest.raises(
        MonitoringContractError,
        match="below critical_threshold",
    ):
        MonitoringCheckResult(
            check_name="probability_drift",
            check_type=MonitoringCheckType.PROBABILITY_DRIFT,
            severity=MonitoringSeverity.PASS,
            observed_value=0.05,
            warning_threshold=0.25,
            critical_threshold=0.10,
            details="Threshold ordering is invalid.",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.00, MonitoringSeverity.PASS),
        (0.099, MonitoringSeverity.PASS),
        (0.10, MonitoringSeverity.WARNING),
        (0.249, MonitoringSeverity.WARNING),
        (0.25, MonitoringSeverity.CRITICAL),
        (0.50, MonitoringSeverity.CRITICAL),
    ],
)
def test_upper_threshold_classification(
    value: float,
    expected: MonitoringSeverity,
) -> None:
    assert (
        classify_upper_threshold(
            value,
            warning_threshold=0.10,
            critical_threshold=0.25,
        )
        is expected
    )


def test_upper_threshold_classification_rejects_invalid_threshold_order() -> None:
    with pytest.raises(
        MonitoringContractError,
        match="below critical_threshold",
    ):
        classify_upper_threshold(
            0.10,
            warning_threshold=0.25,
            critical_threshold=0.10,
        )


@pytest.mark.parametrize(
    ("severities", "expected"),
    [
        (
            (
                MonitoringSeverity.PASS,
                MonitoringSeverity.PASS,
            ),
            MonitoringSeverity.PASS,
        ),
        (
            (
                MonitoringSeverity.PASS,
                MonitoringSeverity.WARNING,
            ),
            MonitoringSeverity.WARNING,
        ),
        (
            (
                MonitoringSeverity.WARNING,
                MonitoringSeverity.CRITICAL,
                MonitoringSeverity.PASS,
            ),
            MonitoringSeverity.CRITICAL,
        ),
    ],
)
def test_maximum_severity_returns_most_serious_result(
    severities: tuple[MonitoringSeverity, ...],
    expected: MonitoringSeverity,
) -> None:
    assert maximum_severity(*severities) is expected


def test_maximum_severity_requires_at_least_one_value() -> None:
    with pytest.raises(
        MonitoringContractError,
        match="At least one severity",
    ):
        maximum_severity()
