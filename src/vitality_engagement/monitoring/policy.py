"""Fail-closed Stage 7 monitoring policy configuration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Final

DEFAULT_MONITORING_POLICY_VERSION: Final = "stage7-dev-v1"


class MonitoringPolicyError(ValueError):
    """Raised when monitoring controls are unsafe or internally inconsistent."""


@dataclass(frozen=True)
class MonitoringPolicy:
    """Immutable controls for deterministic local monitoring runs."""

    policy_version: str = DEFAULT_MONITORING_POLICY_VERSION
    probability_bin_count: int = 10
    numeric_feature_bin_count: int = 10
    psi_warning_threshold: float = 0.10
    psi_critical_threshold: float = 0.25
    unseen_category_warning_rate: float = 0.01
    unseen_category_critical_rate: float = 0.05
    expected_scoring_row_count: int = 3_500
    expected_scoring_member_count: int = 500
    expected_scoring_prediction_day_count: int = 7
    synthetic_data_only: bool = True
    local_artifacts_only: bool = True
    external_alerting_allowed: bool = False
    operational_actions_allowed: bool = False

    def __post_init__(self) -> None:
        """Reject weakened safety controls and invalid thresholds."""
        if not self.policy_version.strip():
            raise MonitoringPolicyError("policy_version must not be empty.")

        self._validate_positive_integer(
            self.probability_bin_count,
            field_name="probability_bin_count",
            minimum=2,
        )
        self._validate_positive_integer(
            self.numeric_feature_bin_count,
            field_name="numeric_feature_bin_count",
            minimum=2,
        )
        self._validate_rate(
            self.psi_warning_threshold,
            field_name="psi_warning_threshold",
        )
        self._validate_rate(
            self.psi_critical_threshold,
            field_name="psi_critical_threshold",
        )
        self._validate_rate(
            self.unseen_category_warning_rate,
            field_name="unseen_category_warning_rate",
        )
        self._validate_rate(
            self.unseen_category_critical_rate,
            field_name="unseen_category_critical_rate",
        )

        if self.psi_warning_threshold >= self.psi_critical_threshold:
            raise MonitoringPolicyError(
                "psi_warning_threshold must be below psi_critical_threshold."
            )

        if self.unseen_category_warning_rate >= self.unseen_category_critical_rate:
            raise MonitoringPolicyError(
                "unseen-category warning rate must be below the critical rate."
            )

        self._validate_positive_integer(
            self.expected_scoring_row_count,
            field_name="expected_scoring_row_count",
        )
        self._validate_positive_integer(
            self.expected_scoring_member_count,
            field_name="expected_scoring_member_count",
        )
        self._validate_positive_integer(
            self.expected_scoring_prediction_day_count,
            field_name="expected_scoring_prediction_day_count",
        )

        if self.expected_scoring_member_count > self.expected_scoring_row_count:
            raise MonitoringPolicyError(
                "expected_scoring_member_count must not exceed the row count."
            )

        if not self.synthetic_data_only:
            raise MonitoringPolicyError("Stage 7 monitoring must remain synthetic-only.")

        if not self.local_artifacts_only:
            raise MonitoringPolicyError("Stage 7 monitoring must remain local-artifact only.")

        if self.external_alerting_allowed:
            raise MonitoringPolicyError("External alert dispatch is not permitted.")

        if self.operational_actions_allowed:
            raise MonitoringPolicyError("Monitoring must not authorise operational actions.")

    @staticmethod
    def _validate_positive_integer(
        value: int,
        *,
        field_name: str,
        minimum: int = 1,
    ) -> None:
        """Require a genuine integer at or above the configured minimum."""
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise MonitoringPolicyError(f"{field_name} must be an integer of at least {minimum}.")

    @staticmethod
    def _validate_rate(
        value: float,
        *,
        field_name: str,
    ) -> None:
        """Require a finite rate between zero and one."""
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(float(value))
            or float(value) < 0.0
            or float(value) > 1.0
        ):
            raise MonitoringPolicyError(
                f"{field_name} must be a finite value between zero and one."
            )


def calculate_monitoring_policy_fingerprint(
    policy: MonitoringPolicy,
) -> str:
    """Return a stable SHA-256 fingerprint for the complete policy."""
    encoded_payload = json.dumps(
        asdict(policy),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded_payload).hexdigest()
