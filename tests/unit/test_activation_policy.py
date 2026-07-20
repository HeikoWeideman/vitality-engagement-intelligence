"""Tests for deterministic activation policy configuration."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest

from vitality_engagement.activation.policy import (
    ActivationPolicy,
    build_activation_run_id,
    calculate_policy_fingerprint,
)
from vitality_engagement.activation.schema import (
    ActivationContractError,
    ContactContextLineage,
)

SCORING_DIGEST = "a" * 64
DECISION_TIMESTAMP = datetime(2025, 6, 30, 8, 0, tzinfo=UTC)
CONTACT_CONTEXT_LINEAGE = ContactContextLineage(
    artifact_path="artifacts/activation/contact_context.parquet",
    artifact_sha256="b" * 64,
    source_name="approved_contact_context_snapshot",
    source_snapshot_reference=("snapshot-2025-06-30T07:30:00Z"),
    source_query_sha256="c" * 64,
    snapshot_timestamp=datetime(
        2025,
        6,
        30,
        7,
        30,
        tzinfo=UTC,
    ),
)


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
        contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
        decision_timestamp=DECISION_TIMESTAMP,
    )
    second = build_activation_run_id(
        policy=policy,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
        decision_timestamp=DECISION_TIMESTAMP,
    )

    assert first == second
    assert first.startswith("act_")
    assert len(first) == 28


def test_activation_run_id_normalises_equivalent_timezones() -> None:
    policy = ActivationPolicy()
    south_africa_timezone = timezone(timedelta(hours=2))

    utc_run_id = build_activation_run_id(
        policy=policy,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
        decision_timestamp=DECISION_TIMESTAMP,
    )
    equivalent_run_id = build_activation_run_id(
        policy=policy,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
        decision_timestamp=datetime(
            2025,
            6,
            30,
            10,
            0,
            tzinfo=south_africa_timezone,
        ),
    )

    assert utc_run_id == equivalent_run_id


def test_activation_run_id_changes_when_timestamp_changes() -> None:
    policy = ActivationPolicy()

    first = build_activation_run_id(
        policy=policy,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
        decision_timestamp=DECISION_TIMESTAMP,
    )
    second = build_activation_run_id(
        policy=policy,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
        decision_timestamp=DECISION_TIMESTAMP + timedelta(minutes=1),
    )

    assert first != second


def test_activation_run_id_changes_when_contact_context_changes() -> None:
    first = build_activation_run_id(
        policy=ActivationPolicy(),
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
        decision_timestamp=DECISION_TIMESTAMP,
    )
    second = build_activation_run_id(
        policy=ActivationPolicy(),
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256=SCORING_DIGEST,
        contact_context_lineage=replace(
            CONTACT_CONTEXT_LINEAGE,
            artifact_sha256="d" * 64,
        ),
        decision_timestamp=DECISION_TIMESTAMP,
    )

    assert first != second


def test_activation_run_id_rejects_naive_timestamp() -> None:
    with pytest.raises(ActivationContractError, match="timezone-aware"):
        build_activation_run_id(
            policy=ActivationPolicy(),
            model_name="python_logistic_baseline",
            threshold=0.431,
            scoring_artifact_sha256=SCORING_DIGEST,
            contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
            decision_timestamp=datetime(2025, 6, 30, 8, 0),
        )


def test_activation_run_id_rejects_invalid_artifact_digest() -> None:
    with pytest.raises(ActivationContractError, match="SHA-256"):
        build_activation_run_id(
            policy=ActivationPolicy(),
            model_name="python_logistic_baseline",
            threshold=0.431,
            scoring_artifact_sha256="not-a-digest",
            contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
            decision_timestamp=DECISION_TIMESTAMP,
        )
