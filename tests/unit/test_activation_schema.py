"""Tests for typed Stage 5 activation contracts."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from vitality_engagement.activation.schema import (
    ActivationAuditRecord,
    ActivationContractError,
    ActivationRunMetadata,
    DecisionOutcome,
    EligiblePrediction,
    ExcludedPrediction,
    InterventionCategory,
    InterventionRecommendation,
    MemberActivationContext,
    ReasonCode,
    ScoredPrediction,
    SelectedActivation,
    SuppressedPrediction,
)


def _prediction(*, probability: float = 0.8, high_risk: bool = True) -> ScoredPrediction:
    return ScoredPrediction(
        member_id="member-001",
        prediction_date=date(2025, 6, 29),
        risk_probability=probability,
        is_high_risk=high_risk,
        model_name="python_logistic_baseline",
        threshold=0.431,
    )


def _context() -> MemberActivationContext:
    return MemberActivationContext(
        member_id="member-001",
        contact_allowed=True,
        opted_out=False,
        active_case_open=False,
        last_contacted_at=None,
        interventions_last_28d=0,
    )


def test_scored_prediction_requires_frozen_threshold_classification() -> None:
    with pytest.raises(ActivationContractError, match="frozen model threshold"):
        _prediction(probability=0.8, high_risk=False)


def test_member_context_requires_timezone_aware_contact_timestamp() -> None:
    with pytest.raises(ActivationContractError, match="timezone-aware"):
        MemberActivationContext(
            member_id="member-001",
            contact_allowed=True,
            opted_out=False,
            active_case_open=False,
            last_contacted_at=datetime(2025, 6, 20, 9, 0),
            interventions_last_28d=0,
        )


def test_eligible_prediction_requires_matching_member_ids() -> None:
    mismatched_context = MemberActivationContext(
        member_id="member-002",
        contact_allowed=True,
        opted_out=False,
        active_case_open=False,
        last_contacted_at=None,
        interventions_last_28d=0,
    )

    with pytest.raises(ActivationContractError, match="member IDs"):
        EligiblePrediction(
            prediction=_prediction(),
            context=mismatched_context,
            reason_code=ReasonCode.ELIGIBLE_HIGH_RISK,
        )


def test_excluded_prediction_supports_missing_context_fail_closed() -> None:
    excluded = ExcludedPrediction(
        prediction=_prediction(),
        reason_code=ReasonCode.MISSING_ACTIVATION_CONTEXT,
    )

    assert excluded.context is None


def test_audit_record_rejects_outcome_reason_mismatch() -> None:
    with pytest.raises(ActivationContractError, match="inconsistent"):
        ActivationAuditRecord(
            run_id="act_example",
            policy_version="stage5-dev-v1",
            member_id="member-001",
            prediction_date=date(2025, 6, 29),
            decision_timestamp=datetime(2025, 6, 30, 8, 0, tzinfo=UTC),
            outcome=DecisionOutcome.NO_CONTACT_EXCLUDED,
            reason_code=ReasonCode.CAPACITY_LIMIT_REACHED,
            risk_probability=0.8,
            model_name="python_logistic_baseline",
            threshold=0.431,
        )


def test_suppressed_prediction_requires_suppression_reason() -> None:
    with pytest.raises(ActivationContractError, match="suppression reason"):
        SuppressedPrediction(
            prediction=_prediction(),
            context=_context(),
            reason_code=ReasonCode.MEMBER_OPTED_OUT,
            suppression_until=None,
        )


def test_selected_activation_requires_positive_priority_rank() -> None:
    eligible = EligiblePrediction(
        prediction=_prediction(),
        context=_context(),
        reason_code=ReasonCode.ELIGIBLE_HIGH_RISK,
    )
    recommendation = InterventionRecommendation(
        category=InterventionCategory.SUPPORTIVE_CHECK_IN,
        rationale_code=ReasonCode.DEFAULT_SUPPORTIVE_INTERVENTION,
        message_template_key="supportive-check-in-v1",
    )

    with pytest.raises(ActivationContractError, match="at least one"):
        SelectedActivation(
            run_id="act_example",
            eligible_prediction=eligible,
            recommendation=recommendation,
            priority_rank=0,
            selected_at=datetime(2025, 6, 30, 8, 0, tzinfo=UTC),
        )


def test_selected_audit_record_requires_intervention_and_rank() -> None:
    with pytest.raises(ActivationContractError, match="intervention category"):
        ActivationAuditRecord(
            run_id="act_example",
            policy_version="stage5-dev-v1",
            member_id="member-001",
            prediction_date=date(2025, 6, 29),
            decision_timestamp=datetime(2025, 6, 30, 8, 0, tzinfo=UTC),
            outcome=DecisionOutcome.SELECTED_FOR_REVIEW,
            reason_code=ReasonCode.SELECTED_FOR_HUMAN_REVIEW,
            risk_probability=0.8,
            model_name="python_logistic_baseline",
            threshold=0.431,
        )


def test_no_contact_audit_record_rejects_intervention_fields() -> None:
    with pytest.raises(ActivationContractError, match="must not contain"):
        ActivationAuditRecord(
            run_id="act_example",
            policy_version="stage5-dev-v1",
            member_id="member-001",
            prediction_date=date(2025, 6, 29),
            decision_timestamp=datetime(2025, 6, 30, 8, 0, tzinfo=UTC),
            outcome=DecisionOutcome.NO_CONTACT_CAPACITY,
            reason_code=ReasonCode.CAPACITY_LIMIT_REACHED,
            risk_probability=0.8,
            model_name="python_logistic_baseline",
            threshold=0.431,
            intervention_category=InterventionCategory.SUPPORTIVE_CHECK_IN,
        )


def test_activation_run_metadata_reconciles_counts() -> None:
    with pytest.raises(ActivationContractError, match="reconcile"):
        ActivationRunMetadata(
            run_id="act_example",
            policy_version="stage5-dev-v1",
            policy_fingerprint="b" * 64,
            model_name="python_logistic_baseline",
            threshold=0.431,
            scoring_artifact_path="artifacts/scoring/predictions.parquet",
            scoring_artifact_sha256="a" * 64,
            decision_timestamp=datetime(2025, 6, 30, 8, 0, tzinfo=UTC),
            capacity_limit=100,
            source_row_count=3_501,
            source_member_count=500,
            superseded_count=3_000,
            below_threshold_count=250,
            excluded_count=25,
            suppressed_count=25,
            eligible_count=200,
            capacity_not_selected_count=100,
            selected_count=100,
        )
