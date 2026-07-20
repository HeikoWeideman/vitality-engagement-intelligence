"""Deterministic eligibility, suppression, ranking, and capacity decisions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Final

from vitality_engagement.activation.policy import (
    ActivationPolicy,
    build_activation_run_id,
    calculate_policy_fingerprint,
)
from vitality_engagement.activation.schema import (
    ActivationAuditRecord,
    ActivationRunMetadata,
    ContactContextLineage,
    DecisionOutcome,
    EligiblePrediction,
    ExcludedPrediction,
    InterventionRecommendation,
    MemberActivationContext,
    ReasonCode,
    ScoredPrediction,
    SelectedActivation,
    SuppressedPrediction,
)

DEFAULT_MESSAGE_TEMPLATE_VERSION: Final = "v1"


class ActivationDecisionError(ValueError):
    """Raised when activation decision inputs or outputs are inconsistent."""


@dataclass(frozen=True)
class ActivationDecisionResult:
    """Complete deterministic result for one activation run."""

    eligible_predictions: tuple[EligiblePrediction, ...]
    excluded_predictions: tuple[ExcludedPrediction, ...]
    suppressed_predictions: tuple[SuppressedPrediction, ...]
    selected_activations: tuple[SelectedActivation, ...]
    audit_records: tuple[ActivationAuditRecord, ...]
    metadata: ActivationRunMetadata

    def __post_init__(self) -> None:
        """Validate result counts, lineage, audit uniqueness, and ranking."""
        if len(self.audit_records) != self.metadata.source_row_count:
            raise ActivationDecisionError("Audit-record count must equal the source-row count.")

        if len(self.eligible_predictions) != self.metadata.eligible_count:
            raise ActivationDecisionError("Eligible-prediction count does not match run metadata.")

        if len(self.excluded_predictions) != self.metadata.excluded_count:
            raise ActivationDecisionError("Excluded-prediction count does not match run metadata.")

        if len(self.suppressed_predictions) != self.metadata.suppressed_count:
            raise ActivationDecisionError(
                "Suppressed-prediction count does not match run metadata."
            )

        if len(self.selected_activations) != self.metadata.selected_count:
            raise ActivationDecisionError("Selected-activation count does not match run metadata.")

        audit_keys = tuple(
            (record.member_id, record.prediction_date) for record in self.audit_records
        )
        if len(audit_keys) != len(set(audit_keys)):
            raise ActivationDecisionError(
                "Every member and prediction date must have exactly one audit record."
            )

        if any(record.run_id != self.metadata.run_id for record in self.audit_records):
            raise ActivationDecisionError("Audit records contain an inconsistent run ID.")

        expected_ranks = tuple(range(1, len(self.selected_activations) + 1))
        actual_ranks = tuple(activation.priority_rank for activation in self.selected_activations)
        if actual_ranks != expected_ranks:
            raise ActivationDecisionError(
                "Selected activation ranks must be contiguous and one-based."
            )


def _require_aware_timestamp(timestamp: datetime) -> None:
    """Require a timezone-aware timestamp."""
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ActivationDecisionError("decision_timestamp must be timezone-aware.")


def _build_context_map(
    contexts: Sequence[MemberActivationContext],
) -> dict[str, MemberActivationContext]:
    """Build a unique member-context mapping."""
    context_map: dict[str, MemberActivationContext] = {}

    for context in contexts:
        if context.member_id in context_map:
            raise ActivationDecisionError(
                f"Duplicate activation context for member: {context.member_id}"
            )
        context_map[context.member_id] = context

    return context_map


def _validate_predictions(
    predictions: Sequence[ScoredPrediction],
    *,
    decision_timestamp: datetime,
) -> tuple[str, float]:
    """Validate source uniqueness, chronology, model, and threshold."""
    if not predictions:
        raise ActivationDecisionError("At least one scored prediction is required.")

    identifiers: set[tuple[str, date]] = set()
    model_names: set[str] = set()
    thresholds: set[float] = set()
    decision_date = decision_timestamp.date()

    for prediction in predictions:
        identifier = (prediction.member_id, prediction.prediction_date)

        if identifier in identifiers:
            raise ActivationDecisionError(
                "Duplicate member and prediction-date source row detected."
            )

        identifiers.add(identifier)
        model_names.add(prediction.model_name)
        thresholds.add(prediction.threshold)

        if prediction.prediction_date > decision_date:
            raise ActivationDecisionError(
                "Prediction dates must not be later than the decision date."
            )

    if len(model_names) != 1:
        raise ActivationDecisionError("All predictions must use one model name.")

    if len(thresholds) != 1:
        raise ActivationDecisionError("All predictions must use one frozen threshold.")

    return next(iter(model_names)), next(iter(thresholds))


def _latest_predictions_by_member(
    predictions: Sequence[ScoredPrediction],
) -> dict[str, ScoredPrediction]:
    """Return the latest prediction for each member."""
    latest: dict[str, ScoredPrediction] = {}

    for prediction in predictions:
        existing = latest.get(prediction.member_id)
        if existing is None or prediction.prediction_date > existing.prediction_date:
            latest[prediction.member_id] = prediction

    return latest


def _audit_record(
    *,
    run_id: str,
    policy: ActivationPolicy,
    prediction: ScoredPrediction,
    decision_timestamp: datetime,
    outcome: DecisionOutcome,
    reason_code: ReasonCode,
    selected: SelectedActivation | None = None,
) -> ActivationAuditRecord:
    """Build one validated audit record."""
    return ActivationAuditRecord(
        run_id=run_id,
        policy_version=policy.policy_version,
        member_id=prediction.member_id,
        prediction_date=prediction.prediction_date,
        decision_timestamp=decision_timestamp,
        outcome=outcome,
        reason_code=reason_code,
        risk_probability=prediction.risk_probability,
        model_name=prediction.model_name,
        threshold=prediction.threshold,
        intervention_category=(None if selected is None else selected.recommendation.category),
        priority_rank=None if selected is None else selected.priority_rank,
    )


def decide_activations(
    *,
    predictions: Sequence[ScoredPrediction],
    contexts: Sequence[MemberActivationContext],
    policy: ActivationPolicy,
    decision_timestamp: datetime,
    scoring_artifact_path: str,
    scoring_artifact_sha256: str,
    contact_context_lineage: ContactContextLineage,
) -> ActivationDecisionResult:
    """Apply governed exclusions, suppressions, ranking, and capacity."""
    _require_aware_timestamp(decision_timestamp)

    prediction_rows = tuple(predictions)
    model_name, threshold = _validate_predictions(
        prediction_rows,
        decision_timestamp=decision_timestamp,
    )
    context_map = _build_context_map(contexts)
    latest_by_member = _latest_predictions_by_member(prediction_rows)

    run_id = build_activation_run_id(
        policy=policy,
        model_name=model_name,
        threshold=threshold,
        scoring_artifact_sha256=scoring_artifact_sha256,
        contact_context_lineage=contact_context_lineage,
        decision_timestamp=decision_timestamp,
    )

    audits: list[ActivationAuditRecord] = []
    excluded: list[ExcludedPrediction] = []
    suppressed: list[SuppressedPrediction] = []
    eligible: list[EligiblePrediction] = []

    superseded_count = 0
    below_threshold_count = 0

    for prediction in prediction_rows:
        latest = latest_by_member[prediction.member_id]

        if prediction.prediction_date < latest.prediction_date:
            superseded_count += 1
            audits.append(
                _audit_record(
                    run_id=run_id,
                    policy=policy,
                    prediction=prediction,
                    decision_timestamp=decision_timestamp,
                    outcome=DecisionOutcome.NO_CONTACT_SUPERSEDED,
                    reason_code=ReasonCode.SUPERSEDED_BY_LATEST_PREDICTION,
                )
            )

    for prediction in sorted(
        latest_by_member.values(),
        key=lambda item: item.member_id,
    ):
        if not prediction.is_high_risk:
            below_threshold_count += 1
            audits.append(
                _audit_record(
                    run_id=run_id,
                    policy=policy,
                    prediction=prediction,
                    decision_timestamp=decision_timestamp,
                    outcome=DecisionOutcome.NO_CONTACT_BELOW_THRESHOLD,
                    reason_code=ReasonCode.BELOW_FROZEN_THRESHOLD,
                )
            )
            continue

        context = context_map.get(prediction.member_id)

        if context is None:
            excluded_prediction = ExcludedPrediction(
                prediction=prediction,
                reason_code=ReasonCode.MISSING_ACTIVATION_CONTEXT,
            )
            excluded.append(excluded_prediction)
            audits.append(
                _audit_record(
                    run_id=run_id,
                    policy=policy,
                    prediction=prediction,
                    decision_timestamp=decision_timestamp,
                    outcome=DecisionOutcome.NO_CONTACT_EXCLUDED,
                    reason_code=excluded_prediction.reason_code,
                )
            )
            continue

        if not context.contact_allowed:
            excluded_prediction = ExcludedPrediction(
                prediction=prediction,
                context=context,
                reason_code=ReasonCode.CONTACT_NOT_PERMITTED,
            )
            excluded.append(excluded_prediction)
            audits.append(
                _audit_record(
                    run_id=run_id,
                    policy=policy,
                    prediction=prediction,
                    decision_timestamp=decision_timestamp,
                    outcome=DecisionOutcome.NO_CONTACT_EXCLUDED,
                    reason_code=excluded_prediction.reason_code,
                )
            )
            continue

        if context.opted_out:
            excluded_prediction = ExcludedPrediction(
                prediction=prediction,
                context=context,
                reason_code=ReasonCode.MEMBER_OPTED_OUT,
            )
            excluded.append(excluded_prediction)
            audits.append(
                _audit_record(
                    run_id=run_id,
                    policy=policy,
                    prediction=prediction,
                    decision_timestamp=decision_timestamp,
                    outcome=DecisionOutcome.NO_CONTACT_EXCLUDED,
                    reason_code=excluded_prediction.reason_code,
                )
            )
            continue

        prediction_age = (decision_timestamp.date() - prediction.prediction_date).days

        if prediction_age > policy.maximum_prediction_age_days:
            suppressed_prediction = SuppressedPrediction(
                prediction=prediction,
                context=context,
                reason_code=ReasonCode.PREDICTION_TOO_OLD,
                suppression_until=None,
            )
            suppressed.append(suppressed_prediction)
            audits.append(
                _audit_record(
                    run_id=run_id,
                    policy=policy,
                    prediction=prediction,
                    decision_timestamp=decision_timestamp,
                    outcome=DecisionOutcome.NO_CONTACT_SUPPRESSED,
                    reason_code=suppressed_prediction.reason_code,
                )
            )
            continue

        if context.active_case_open:
            suppressed_prediction = SuppressedPrediction(
                prediction=prediction,
                context=context,
                reason_code=ReasonCode.ACTIVE_CASE_OPEN,
                suppression_until=None,
            )
            suppressed.append(suppressed_prediction)
            audits.append(
                _audit_record(
                    run_id=run_id,
                    policy=policy,
                    prediction=prediction,
                    decision_timestamp=decision_timestamp,
                    outcome=DecisionOutcome.NO_CONTACT_SUPPRESSED,
                    reason_code=suppressed_prediction.reason_code,
                )
            )
            continue

        if context.last_contacted_at is not None:
            if context.last_contacted_at > decision_timestamp:
                raise ActivationDecisionError(
                    "Contact timestamps must not be later than the decision timestamp."
                )

            cooldown_until = context.last_contacted_at + timedelta(
                days=policy.contact_cooldown_days
            )

            if decision_timestamp < cooldown_until:
                suppressed_prediction = SuppressedPrediction(
                    prediction=prediction,
                    context=context,
                    reason_code=ReasonCode.CONTACT_COOLDOWN_ACTIVE,
                    suppression_until=cooldown_until.date(),
                )
                suppressed.append(suppressed_prediction)
                audits.append(
                    _audit_record(
                        run_id=run_id,
                        policy=policy,
                        prediction=prediction,
                        decision_timestamp=decision_timestamp,
                        outcome=DecisionOutcome.NO_CONTACT_SUPPRESSED,
                        reason_code=suppressed_prediction.reason_code,
                    )
                )
                continue

        if context.interventions_last_28d >= policy.maximum_interventions_per_member_28d:
            suppressed_prediction = SuppressedPrediction(
                prediction=prediction,
                context=context,
                reason_code=ReasonCode.PRIOR_INTERVENTION_LIMIT_REACHED,
                suppression_until=None,
            )
            suppressed.append(suppressed_prediction)
            audits.append(
                _audit_record(
                    run_id=run_id,
                    policy=policy,
                    prediction=prediction,
                    decision_timestamp=decision_timestamp,
                    outcome=DecisionOutcome.NO_CONTACT_SUPPRESSED,
                    reason_code=suppressed_prediction.reason_code,
                )
            )
            continue

        eligible.append(
            EligiblePrediction(
                prediction=prediction,
                context=context,
                reason_code=ReasonCode.ELIGIBLE_HIGH_RISK,
            )
        )

    ranked_eligible = sorted(
        eligible,
        key=lambda item: (
            -item.prediction.risk_probability,
            -item.prediction.prediction_date.toordinal(),
            item.prediction.member_id,
        ),
    )

    selection_count = min(
        len(ranked_eligible),
        policy.maximum_activations_per_run,
    )
    intervention_category = policy.allowed_intervention_categories[0]
    recommendation = InterventionRecommendation(
        category=intervention_category,
        rationale_code=ReasonCode.DEFAULT_SUPPORTIVE_INTERVENTION,
        message_template_key=(f"{intervention_category.value}-{DEFAULT_MESSAGE_TEMPLATE_VERSION}"),
        requires_human_review=True,
    )

    selected: list[SelectedActivation] = []

    for rank, eligible_prediction in enumerate(
        ranked_eligible[:selection_count],
        start=1,
    ):
        selected_activation = SelectedActivation(
            run_id=run_id,
            eligible_prediction=eligible_prediction,
            recommendation=recommendation,
            priority_rank=rank,
            selected_at=decision_timestamp,
        )
        selected.append(selected_activation)
        audits.append(
            _audit_record(
                run_id=run_id,
                policy=policy,
                prediction=eligible_prediction.prediction,
                decision_timestamp=decision_timestamp,
                outcome=DecisionOutcome.SELECTED_FOR_REVIEW,
                reason_code=ReasonCode.SELECTED_FOR_HUMAN_REVIEW,
                selected=selected_activation,
            )
        )

    capacity_not_selected = ranked_eligible[selection_count:]

    for eligible_prediction in capacity_not_selected:
        audits.append(
            _audit_record(
                run_id=run_id,
                policy=policy,
                prediction=eligible_prediction.prediction,
                decision_timestamp=decision_timestamp,
                outcome=DecisionOutcome.NO_CONTACT_CAPACITY,
                reason_code=ReasonCode.CAPACITY_LIMIT_REACHED,
            )
        )

    ordered_audits = tuple(
        sorted(
            audits,
            key=lambda record: (
                record.member_id,
                record.prediction_date,
            ),
        )
    )

    metadata = ActivationRunMetadata(
        run_id=run_id,
        policy_version=policy.policy_version,
        policy_fingerprint=calculate_policy_fingerprint(policy),
        model_name=model_name,
        threshold=threshold,
        scoring_artifact_path=scoring_artifact_path,
        scoring_artifact_sha256=scoring_artifact_sha256,
        contact_context_lineage=contact_context_lineage,
        decision_timestamp=decision_timestamp,
        capacity_limit=policy.maximum_activations_per_run,
        source_row_count=len(prediction_rows),
        source_member_count=len(latest_by_member),
        superseded_count=superseded_count,
        below_threshold_count=below_threshold_count,
        excluded_count=len(excluded),
        suppressed_count=len(suppressed),
        eligible_count=len(ranked_eligible),
        capacity_not_selected_count=len(capacity_not_selected),
        selected_count=len(selected),
    )

    return ActivationDecisionResult(
        eligible_predictions=tuple(ranked_eligible),
        excluded_predictions=tuple(excluded),
        suppressed_predictions=tuple(suppressed),
        selected_activations=tuple(selected),
        audit_records=ordered_audits,
        metadata=metadata,
    )
