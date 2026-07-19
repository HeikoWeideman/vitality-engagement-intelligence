"""Tests for deterministic activation decisions and prioritisation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from vitality_engagement.activation.engine import (
    ActivationDecisionError,
    decide_activations,
)
from vitality_engagement.activation.policy import ActivationPolicy
from vitality_engagement.activation.schema import (
    DecisionOutcome,
    MemberActivationContext,
    ReasonCode,
    ScoredPrediction,
)

DECISION_TIMESTAMP = datetime(2025, 6, 30, 8, 0, tzinfo=UTC)
SCORING_DIGEST = "a" * 64
SCORING_PATH = "artifacts/scoring/python_logistic_scoring_predictions.parquet"


def _prediction(
    member_id: str,
    *,
    prediction_date: date = date(2025, 6, 29),
    probability: float = 0.8,
) -> ScoredPrediction:
    return ScoredPrediction(
        member_id=member_id,
        prediction_date=prediction_date,
        risk_probability=probability,
        is_high_risk=probability >= 0.431,
        model_name="python_logistic_baseline",
        threshold=0.431,
    )


def _context(
    member_id: str,
    *,
    contact_allowed: bool = True,
    opted_out: bool = False,
    active_case_open: bool = False,
    last_contacted_at: datetime | None = None,
    interventions_last_28d: int = 0,
) -> MemberActivationContext:
    return MemberActivationContext(
        member_id=member_id,
        contact_allowed=contact_allowed,
        opted_out=opted_out,
        active_case_open=active_case_open,
        last_contacted_at=last_contacted_at,
        interventions_last_28d=interventions_last_28d,
    )


def test_latest_prediction_supersedes_older_member_rows() -> None:
    result = decide_activations(
        predictions=[
            _prediction(
                "member-001",
                prediction_date=date(2025, 6, 28),
                probability=0.9,
            ),
            _prediction(
                "member-001",
                prediction_date=date(2025, 6, 29),
                probability=0.8,
            ),
        ],
        contexts=[_context("member-001")],
        policy=ActivationPolicy(),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    assert result.metadata.superseded_count == 1
    assert result.metadata.source_member_count == 1
    assert result.metadata.selected_count == 1

    superseded = next(
        record
        for record in result.audit_records
        if record.outcome is DecisionOutcome.NO_CONTACT_SUPERSEDED
    )
    assert superseded.prediction_date == date(2025, 6, 28)


def test_below_threshold_precedes_missing_context() -> None:
    result = decide_activations(
        predictions=[_prediction("member-001", probability=0.2)],
        contexts=[],
        policy=ActivationPolicy(),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    assert result.metadata.below_threshold_count == 1
    assert result.metadata.excluded_count == 0
    assert result.audit_records[0].reason_code is ReasonCode.BELOW_FROZEN_THRESHOLD


def test_missing_context_fails_closed() -> None:
    result = decide_activations(
        predictions=[_prediction("member-001")],
        contexts=[],
        policy=ActivationPolicy(),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    assert result.metadata.excluded_count == 1
    assert result.excluded_predictions[0].reason_code is ReasonCode.MISSING_ACTIVATION_CONTEXT


def test_contact_not_permitted_precedes_opt_out() -> None:
    result = decide_activations(
        predictions=[_prediction("member-001")],
        contexts=[
            _context(
                "member-001",
                contact_allowed=False,
                opted_out=True,
            )
        ],
        policy=ActivationPolicy(),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    assert result.excluded_predictions[0].reason_code is ReasonCode.CONTACT_NOT_PERMITTED


def test_stale_prediction_precedes_active_case_suppression() -> None:
    result = decide_activations(
        predictions=[
            _prediction(
                "member-001",
                prediction_date=date(2025, 6, 20),
            )
        ],
        contexts=[_context("member-001", active_case_open=True)],
        policy=ActivationPolicy(maximum_prediction_age_days=7),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    assert result.suppressed_predictions[0].reason_code is ReasonCode.PREDICTION_TOO_OLD


def test_contact_cooldown_sets_suppression_until_date() -> None:
    last_contacted_at = datetime(2025, 6, 25, 8, 0, tzinfo=UTC)

    result = decide_activations(
        predictions=[_prediction("member-001")],
        contexts=[
            _context(
                "member-001",
                last_contacted_at=last_contacted_at,
            )
        ],
        policy=ActivationPolicy(contact_cooldown_days=7),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    suppression = result.suppressed_predictions[0]
    assert suppression.reason_code is ReasonCode.CONTACT_COOLDOWN_ACTIVE
    assert suppression.suppression_until == date(2025, 7, 2)


def test_prior_intervention_limit_suppresses_member() -> None:
    result = decide_activations(
        predictions=[_prediction("member-001")],
        contexts=[
            _context(
                "member-001",
                interventions_last_28d=2,
            )
        ],
        policy=ActivationPolicy(maximum_interventions_per_member_28d=2),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    assert (
        result.suppressed_predictions[0].reason_code is ReasonCode.PRIOR_INTERVENTION_LIMIT_REACHED
    )


def test_ranking_uses_probability_date_then_member_id() -> None:
    result = decide_activations(
        predictions=[
            _prediction(
                "member-a",
                prediction_date=date(2025, 6, 28),
                probability=0.9,
            ),
            _prediction(
                "member-c",
                prediction_date=date(2025, 6, 29),
                probability=0.9,
            ),
            _prediction(
                "member-b",
                prediction_date=date(2025, 6, 29),
                probability=0.9,
            ),
        ],
        contexts=[
            _context("member-a"),
            _context("member-b"),
            _context("member-c"),
        ],
        policy=ActivationPolicy(maximum_activations_per_run=2),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    selected_members = [
        selected.eligible_prediction.prediction.member_id
        for selected in result.selected_activations
    ]

    assert selected_members == ["member-b", "member-c"]
    assert result.metadata.capacity_not_selected_count == 1

    capacity_record = next(
        record
        for record in result.audit_records
        if record.outcome is DecisionOutcome.NO_CONTACT_CAPACITY
    )
    assert capacity_record.member_id == "member-a"


def test_decision_is_independent_of_source_input_order() -> None:
    predictions = [
        _prediction("member-a", probability=0.7),
        _prediction("member-b", probability=0.9),
        _prediction("member-c", probability=0.8),
    ]
    contexts = [
        _context("member-a"),
        _context("member-b"),
        _context("member-c"),
    ]
    policy = ActivationPolicy(maximum_activations_per_run=2)

    first = decide_activations(
        predictions=predictions,
        contexts=contexts,
        policy=policy,
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )
    second = decide_activations(
        predictions=list(reversed(predictions)),
        contexts=list(reversed(contexts)),
        policy=policy,
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    assert first.metadata == second.metadata
    assert first.audit_records == second.audit_records
    assert first.selected_activations == second.selected_activations


def test_engine_rejects_empty_prediction_input() -> None:
    with pytest.raises(ActivationDecisionError, match="At least one"):
        decide_activations(
            predictions=[],
            contexts=[],
            policy=ActivationPolicy(),
            decision_timestamp=DECISION_TIMESTAMP,
            scoring_artifact_path=SCORING_PATH,
            scoring_artifact_sha256=SCORING_DIGEST,
        )


def test_engine_rejects_duplicate_source_identifiers() -> None:
    duplicate = _prediction("member-001")

    with pytest.raises(ActivationDecisionError, match="Duplicate member"):
        decide_activations(
            predictions=[duplicate, duplicate],
            contexts=[_context("member-001")],
            policy=ActivationPolicy(),
            decision_timestamp=DECISION_TIMESTAMP,
            scoring_artifact_path=SCORING_PATH,
            scoring_artifact_sha256=SCORING_DIGEST,
        )


def test_engine_rejects_duplicate_member_contexts() -> None:
    with pytest.raises(ActivationDecisionError, match="Duplicate activation context"):
        decide_activations(
            predictions=[_prediction("member-001")],
            contexts=[
                _context("member-001"),
                _context("member-001"),
            ],
            policy=ActivationPolicy(),
            decision_timestamp=DECISION_TIMESTAMP,
            scoring_artifact_path=SCORING_PATH,
            scoring_artifact_sha256=SCORING_DIGEST,
        )


def test_engine_rejects_future_prediction_date() -> None:
    with pytest.raises(ActivationDecisionError, match="later than the decision date"):
        decide_activations(
            predictions=[
                _prediction(
                    "member-001",
                    prediction_date=date(2025, 7, 1),
                )
            ],
            contexts=[_context("member-001")],
            policy=ActivationPolicy(),
            decision_timestamp=DECISION_TIMESTAMP,
            scoring_artifact_path=SCORING_PATH,
            scoring_artifact_sha256=SCORING_DIGEST,
        )


def test_engine_rejects_future_contact_timestamp() -> None:
    with pytest.raises(
        ActivationDecisionError,
        match="later than the decision timestamp",
    ):
        decide_activations(
            predictions=[_prediction("member-001")],
            contexts=[
                _context(
                    "member-001",
                    last_contacted_at=DECISION_TIMESTAMP + timedelta(hours=1),
                )
            ],
            policy=ActivationPolicy(),
            decision_timestamp=DECISION_TIMESTAMP,
            scoring_artifact_path=SCORING_PATH,
            scoring_artifact_sha256=SCORING_DIGEST,
        )


def test_policy_change_changes_run_metadata_identity() -> None:
    predictions = [_prediction("member-001")]
    contexts = [_context("member-001")]
    policy = ActivationPolicy()

    first = decide_activations(
        predictions=predictions,
        contexts=contexts,
        policy=policy,
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )
    second = decide_activations(
        predictions=predictions,
        contexts=contexts,
        policy=replace(policy, maximum_activations_per_run=50),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path=SCORING_PATH,
        scoring_artifact_sha256=SCORING_DIGEST,
    )

    assert first.metadata.run_id != second.metadata.run_id
    assert first.metadata.policy_fingerprint != second.metadata.policy_fingerprint
