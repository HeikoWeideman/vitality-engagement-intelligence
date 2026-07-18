"""Tests for deterministic activation policy configuration."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from vitality_engagement.activation.policy import (
    ActivationPolicy,
    build_activation_run_id,
    calculate_policy_fingerprint,
)
from vitality_engagement.activation.schema import ActivationContractError

SCORING_DIGEST = "a" * 64


def test_default_policy_preserves_required_safety_controls() -> None:
    policy = ActivationPolicy()

    assert policy.high_risk_only is True
    assert policy.human_review_required is True
    assert policy.supportive_use_only is True
    assert policy.maximum_activations_per_run == 100
    assert policy.contact_cooldown_days == 7


def test_policy_rejects_disabled_human_review() -> None:
    with pytest.raises(ActivationContractError, match="Human review"):
        ActivationPolicy(human_review_required=False)


def test_policy_rejects_zero_capacity() -> None:
    with pytest.raises(ActivationContractError, match="at least one"):
        ActivationPolicy(maximum_activations_per_run=0)


def test_policy_fingerprint_is_stable_and_sensitive_to_configuration() -> None:
    policy = ActivationPolicy()

    assert calculate_policy_fingerprint(policy) == calculate_policy_fingerprint(policy)
    assert calculate_policy_fingerprint(policy) != calculate_policy_fingerprint(
        replace(policy, maximum_activations_per_run=50)
    )


def test_activation_run_id_is_deterministic() -> None:
    policy = ActivationPolicy()

    first = build_activation_run_id(
        policy=policy,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        decision_date=date(2025, 6, 30),
    )
    second = build_activation_run_id(
        policy=policy,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        decision_date=date(2025, 6, 30),
    )

    assert first == second
    assert first.startswith("act_")
    assert len(first) == 28


def test_activation_run_id_changes_when_governed_input_changes() -> None:
    policy = ActivationPolicy()

    first = build_activation_run_id(
        policy=policy,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        decision_date=date(2025, 6, 30),
    )
    second = build_activation_run_id(
        policy=policy,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        decision_date=date(2025, 7, 1),
    )

    assert first != second


def test_activation_run_id_rejects_invalid_artifact_digest() -> None:
    with pytest.raises(ActivationContractError, match="SHA-256"):
        build_activation_run_id(
            policy=ActivationPolicy(),
            model_name="python_logistic_baseline",
            threshold=0.431,
            scoring_artifact_sha256="not-a-digest",
            decision_date=date(2025, 6, 30),
        )
