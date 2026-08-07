"""Tests for fail-closed Stage 7 monitoring policy controls."""

from dataclasses import replace
from typing import Literal

import pytest

from vitality_engagement.monitoring.policy import (
    MonitoringPolicy,
    MonitoringPolicyError,
    calculate_monitoring_policy_fingerprint,
)

GovernanceBooleanField = Literal[
    "synthetic_data_only",
    "local_artifacts_only",
    "external_alerting_allowed",
    "operational_actions_allowed",
]

IntegerControlField = Literal[
    "probability_bin_count",
    "numeric_feature_bin_count",
    "expected_scoring_row_count",
    "expected_scoring_member_count",
    "expected_scoring_prediction_day_count",
]


def _replace_governance_control(
    policy: MonitoringPolicy,
    *,
    field_name: GovernanceBooleanField,
    value: bool,
) -> MonitoringPolicy:
    """Replace one Boolean governance field without dynamic keyword typing."""
    match field_name:
        case "synthetic_data_only":
            return replace(policy, synthetic_data_only=value)
        case "local_artifacts_only":
            return replace(policy, local_artifacts_only=value)
        case "external_alerting_allowed":
            return replace(policy, external_alerting_allowed=value)
        case "operational_actions_allowed":
            return replace(policy, operational_actions_allowed=value)

    raise AssertionError("Unsupported governance field.")


def _replace_integer_control(
    policy: MonitoringPolicy,
    *,
    field_name: IntegerControlField,
    value: int,
) -> MonitoringPolicy:
    """Replace one integer policy field without dynamic keyword typing."""
    match field_name:
        case "probability_bin_count":
            return replace(policy, probability_bin_count=value)
        case "numeric_feature_bin_count":
            return replace(policy, numeric_feature_bin_count=value)
        case "expected_scoring_row_count":
            return replace(policy, expected_scoring_row_count=value)
        case "expected_scoring_member_count":
            return replace(policy, expected_scoring_member_count=value)
        case "expected_scoring_prediction_day_count":
            return replace(
                policy,
                expected_scoring_prediction_day_count=value,
            )

    raise AssertionError("Unsupported integer policy field.")


def test_default_monitoring_policy_preserves_governance_controls() -> None:
    policy = MonitoringPolicy()

    assert policy.synthetic_data_only is True
    assert policy.local_artifacts_only is True
    assert policy.external_alerting_allowed is False
    assert policy.operational_actions_allowed is False
    assert policy.psi_warning_threshold < policy.psi_critical_threshold
    assert policy.unseen_category_warning_rate < policy.unseen_category_critical_rate


@pytest.mark.parametrize(
    ("field_name", "unsafe_value", "message"),
    [
        ("synthetic_data_only", False, "synthetic-only"),
        ("local_artifacts_only", False, "local-artifact only"),
        ("external_alerting_allowed", True, "External alert dispatch"),
        ("operational_actions_allowed", True, "operational actions"),
    ],
)
def test_monitoring_policy_rejects_weakened_governance(
    field_name: GovernanceBooleanField,
    unsafe_value: bool,
    message: str,
) -> None:
    default_policy = MonitoringPolicy()

    with pytest.raises(MonitoringPolicyError, match=message):
        _replace_governance_control(
            default_policy,
            field_name=field_name,
            value=unsafe_value,
        )


@pytest.mark.parametrize(
    ("field_name", "unsafe_value"),
    [
        ("probability_bin_count", 1),
        ("numeric_feature_bin_count", 1),
        ("expected_scoring_row_count", 0),
        ("expected_scoring_member_count", 0),
        ("expected_scoring_prediction_day_count", 0),
    ],
)
def test_monitoring_policy_rejects_invalid_integer_controls(
    field_name: IntegerControlField,
    unsafe_value: int,
) -> None:
    default_policy = MonitoringPolicy()

    with pytest.raises(MonitoringPolicyError):
        _replace_integer_control(
            default_policy,
            field_name=field_name,
            value=unsafe_value,
        )


def test_monitoring_policy_rejects_reversed_psi_thresholds() -> None:
    with pytest.raises(
        MonitoringPolicyError,
        match="warning_threshold must be below",
    ):
        MonitoringPolicy(
            psi_warning_threshold=0.25,
            psi_critical_threshold=0.10,
        )


def test_monitoring_policy_rejects_reversed_unseen_category_thresholds() -> None:
    with pytest.raises(
        MonitoringPolicyError,
        match="warning rate must be below",
    ):
        MonitoringPolicy(
            unseen_category_warning_rate=0.05,
            unseen_category_critical_rate=0.01,
        )


def test_monitoring_policy_fingerprint_is_stable_and_complete() -> None:
    policy = MonitoringPolicy()
    same_policy = MonitoringPolicy()
    changed_policy = replace(
        policy,
        psi_warning_threshold=0.12,
    )

    assert calculate_monitoring_policy_fingerprint(policy) == (
        calculate_monitoring_policy_fingerprint(same_policy)
    )
    assert calculate_monitoring_policy_fingerprint(policy) != (
        calculate_monitoring_policy_fingerprint(changed_policy)
    )
    assert len(calculate_monitoring_policy_fingerprint(policy)) == 64
