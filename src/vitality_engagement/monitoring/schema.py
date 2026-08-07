"""Typed contracts for deterministic Stage 7 monitoring results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class MonitoringContractError(ValueError):
    """Raised when a monitoring result violates its governed contract."""


class MonitoringSeverity(StrEnum):
    """Approved monitoring severity levels."""

    PASS = "pass"
    WARNING = "warning"
    CRITICAL = "critical"


class MonitoringCheckType(StrEnum):
    """Approved classes of Stage 7 monitoring checks."""

    SCORING_VOLUME = "scoring_volume"
    MODEL_IDENTITY = "model_identity"
    THRESHOLD_IDENTITY = "threshold_identity"
    SCHEMA_IDENTITY = "schema_identity"
    PROBABILITY_DRIFT = "probability_drift"
    NUMERIC_FEATURE_DRIFT = "numeric_feature_drift"
    CATEGORICAL_FEATURE_DRIFT = "categorical_feature_drift"
    UNSEEN_CATEGORY_RATE = "unseen_category_rate"
    SOURCE_FRESHNESS = "source_freshness"
    ACTIVATION_EMPTY_STATE = "activation_empty_state"
    DASHBOARD_QUALITY = "dashboard_quality"


FEATURE_LEVEL_CHECK_TYPES = frozenset(
    {
        MonitoringCheckType.NUMERIC_FEATURE_DRIFT,
        MonitoringCheckType.CATEGORICAL_FEATURE_DRIFT,
        MonitoringCheckType.UNSEEN_CATEGORY_RATE,
    }
)


@dataclass(frozen=True)
class MonitoringCheckResult:
    """One validated, non-operational monitoring observation."""

    check_name: str
    check_type: MonitoringCheckType
    severity: MonitoringSeverity
    observed_value: float
    details: str
    feature_name: str | None = None
    expected_value: float | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    reference_row_count: int | None = None
    current_row_count: int | None = None

    def __post_init__(self) -> None:
        """Validate one monitoring result without weakening governance."""
        if not self.check_name.strip():
            raise MonitoringContractError("check_name must not be empty.")

        if not self.details.strip():
            raise MonitoringContractError("details must not be empty.")

        self._validate_finite(
            self.observed_value,
            field_name="observed_value",
        )

        if self.expected_value is not None:
            self._validate_finite(
                self.expected_value,
                field_name="expected_value",
            )

        thresholds = (
            self.warning_threshold,
            self.critical_threshold,
        )

        if any(value is None for value in thresholds) and any(
            value is not None for value in thresholds
        ):
            raise MonitoringContractError(
                "warning_threshold and critical_threshold must be provided together."
            )

        if self.warning_threshold is not None and self.critical_threshold is not None:
            self._validate_finite(
                self.warning_threshold,
                field_name="warning_threshold",
            )
            self._validate_finite(
                self.critical_threshold,
                field_name="critical_threshold",
            )

            if self.warning_threshold < 0.0:
                raise MonitoringContractError("warning_threshold must not be negative.")

            if self.warning_threshold >= self.critical_threshold:
                raise MonitoringContractError("warning_threshold must be below critical_threshold.")

        self._validate_optional_count(
            self.reference_row_count,
            field_name="reference_row_count",
        )
        self._validate_optional_count(
            self.current_row_count,
            field_name="current_row_count",
        )

        if self.check_type in FEATURE_LEVEL_CHECK_TYPES and (
            self.feature_name is None or not self.feature_name.strip()
        ):
            raise MonitoringContractError("Feature-level monitoring checks require feature_name.")

        if self.feature_name is not None and not self.feature_name.strip():
            raise MonitoringContractError("feature_name must not be empty when provided.")

    @staticmethod
    def _validate_finite(
        value: float,
        *,
        field_name: str,
    ) -> None:
        """Require a genuine finite numeric value."""
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(float(value))
        ):
            raise MonitoringContractError(f"{field_name} must be finite.")

    @staticmethod
    def _validate_optional_count(
        value: int | None,
        *,
        field_name: str,
    ) -> None:
        """Require positive integer row counts when supplied."""
        if value is None:
            return

        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise MonitoringContractError(f"{field_name} must be a positive integer when provided.")


def classify_upper_threshold(
    value: float,
    *,
    warning_threshold: float,
    critical_threshold: float,
) -> MonitoringSeverity:
    """Classify a metric where larger values represent greater concern."""
    values = (
        value,
        warning_threshold,
        critical_threshold,
    )

    if any(
        isinstance(item, bool) or not isinstance(item, (int, float)) or not isfinite(float(item))
        for item in values
    ):
        raise MonitoringContractError("Threshold classification values must be finite.")

    if warning_threshold < 0.0:
        raise MonitoringContractError("warning_threshold must not be negative.")

    if warning_threshold >= critical_threshold:
        raise MonitoringContractError("warning_threshold must be below critical_threshold.")

    if value >= critical_threshold:
        return MonitoringSeverity.CRITICAL

    if value >= warning_threshold:
        return MonitoringSeverity.WARNING

    return MonitoringSeverity.PASS


def maximum_severity(
    *severities: MonitoringSeverity,
) -> MonitoringSeverity:
    """Return the most serious supplied monitoring severity."""
    if not severities:
        raise MonitoringContractError("At least one severity is required.")

    severity_rank = {
        MonitoringSeverity.PASS: 0,
        MonitoringSeverity.WARNING: 1,
        MonitoringSeverity.CRITICAL: 2,
    }
    return max(
        severities,
        key=severity_rank.__getitem__,
    )
