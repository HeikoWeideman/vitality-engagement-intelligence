"""Typed contracts for governed activation decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from math import isfinite
from typing import Final


class ActivationContractError(ValueError):
    """Raised when an activation object violates its contract."""


class InterventionCategory(StrEnum):
    """Supportive intervention categories available to human reviewers."""

    SUPPORTIVE_CHECK_IN = "supportive_check_in"
    GOAL_PLANNING = "goal_planning"
    ACTIVITY_REMINDER = "activity_reminder"
    REWARDS_EDUCATION = "rewards_education"


class ReasonCode(StrEnum):
    """Traceable reasons used by eligibility and activation decisions."""

    ELIGIBLE_HIGH_RISK = "eligible_high_risk"
    SUPERSEDED_BY_LATEST_PREDICTION = "superseded_by_latest_prediction"
    BELOW_FROZEN_THRESHOLD = "below_frozen_threshold"
    PREDICTION_TOO_OLD = "prediction_too_old"
    MISSING_ACTIVATION_CONTEXT = "missing_activation_context"
    CONTACT_NOT_PERMITTED = "contact_not_permitted"
    MEMBER_OPTED_OUT = "member_opted_out"
    ACTIVE_CASE_OPEN = "active_case_open"
    CONTACT_COOLDOWN_ACTIVE = "contact_cooldown_active"
    PRIOR_INTERVENTION_LIMIT_REACHED = "prior_intervention_limit_reached"
    CAPACITY_LIMIT_REACHED = "capacity_limit_reached"
    SELECTED_FOR_HUMAN_REVIEW = "selected_for_human_review"
    DEFAULT_SUPPORTIVE_INTERVENTION = "default_supportive_intervention"


class DecisionOutcome(StrEnum):
    """Auditable activation outcomes, including explicit no-contact states."""

    SELECTED_FOR_REVIEW = "selected_for_review"
    NO_CONTACT_SUPERSEDED = "no_contact_superseded"
    NO_CONTACT_BELOW_THRESHOLD = "no_contact_below_threshold"
    NO_CONTACT_EXCLUDED = "no_contact_excluded"
    NO_CONTACT_SUPPRESSED = "no_contact_suppressed"
    NO_CONTACT_CAPACITY = "no_contact_capacity"


EXCLUSION_REASON_CODES: Final[frozenset[ReasonCode]] = frozenset(
    {
        ReasonCode.MISSING_ACTIVATION_CONTEXT,
        ReasonCode.CONTACT_NOT_PERMITTED,
        ReasonCode.MEMBER_OPTED_OUT,
    }
)

SUPPRESSION_REASON_CODES: Final[frozenset[ReasonCode]] = frozenset(
    {
        ReasonCode.PREDICTION_TOO_OLD,
        ReasonCode.ACTIVE_CASE_OPEN,
        ReasonCode.CONTACT_COOLDOWN_ACTIVE,
        ReasonCode.PRIOR_INTERVENTION_LIMIT_REACHED,
    }
)


def _require_non_empty(value: str, field_name: str) -> None:
    """Require a non-empty string value."""
    if not value.strip():
        raise ActivationContractError(f"{field_name} must not be empty.")


def _require_aware(timestamp: datetime, field_name: str) -> None:
    """Require a timezone-aware timestamp."""
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ActivationContractError(f"{field_name} must be timezone-aware.")


def _require_sha256(value: str, field_name: str) -> None:
    """Require a lowercase hexadecimal SHA-256 digest."""
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ActivationContractError(f"{field_name} must be a lowercase SHA-256 digest.")


@dataclass(frozen=True)
class ScoredPrediction:
    """One validated row from the Stage 4 scoring artifact."""

    member_id: str
    prediction_date: date
    risk_probability: float
    is_high_risk: bool
    model_name: str
    threshold: float

    def __post_init__(self) -> None:
        """Validate the frozen scoring contract."""
        _require_non_empty(self.member_id, "member_id")
        _require_non_empty(self.model_name, "model_name")

        if not isfinite(self.risk_probability):
            raise ActivationContractError("risk_probability must be finite.")

        if self.risk_probability < 0.0 or self.risk_probability > 1.0:
            raise ActivationContractError("risk_probability must fall between zero and one.")

        if not isfinite(self.threshold) or self.threshold < 0.0 or self.threshold > 1.0:
            raise ActivationContractError("threshold must fall between zero and one.")

        if self.is_high_risk != (self.risk_probability >= self.threshold):
            raise ActivationContractError(
                "is_high_risk must be derived from the frozen model threshold."
            )


@dataclass(frozen=True)
class MemberActivationContext:
    """Governed contact and intervention context for one member."""

    member_id: str
    contact_allowed: bool
    opted_out: bool
    active_case_open: bool
    last_contacted_at: datetime | None
    interventions_last_28d: int

    def __post_init__(self) -> None:
        """Validate contact-governance inputs."""
        _require_non_empty(self.member_id, "member_id")

        if self.last_contacted_at is not None:
            _require_aware(self.last_contacted_at, "last_contacted_at")

        if self.interventions_last_28d < 0:
            raise ActivationContractError("interventions_last_28d must not be negative.")


@dataclass(frozen=True)
class EligiblePrediction:
    """Prediction that passed threshold, exclusion, and suppression checks."""

    prediction: ScoredPrediction
    context: MemberActivationContext
    reason_code: ReasonCode

    def __post_init__(self) -> None:
        """Validate an eligible prediction."""
        if self.prediction.member_id != self.context.member_id:
            raise ActivationContractError("Prediction and context member IDs must match.")

        if not self.prediction.is_high_risk:
            raise ActivationContractError("Eligible predictions must be classified as high risk.")

        if self.reason_code is not ReasonCode.ELIGIBLE_HIGH_RISK:
            raise ActivationContractError(
                "Eligible predictions must use the eligible_high_risk reason code."
            )


@dataclass(frozen=True)
class ExcludedPrediction:
    """Prediction withheld by a non-temporary exclusion rule."""

    prediction: ScoredPrediction
    reason_code: ReasonCode
    context: MemberActivationContext | None = None

    def __post_init__(self) -> None:
        """Validate an excluded prediction."""
        if self.reason_code not in EXCLUSION_REASON_CODES:
            raise ActivationContractError("Excluded predictions require an exclusion reason.")

        if self.reason_code is ReasonCode.MISSING_ACTIVATION_CONTEXT:
            if self.context is not None:
                raise ActivationContractError(
                    "Missing-context exclusions must not contain member context."
                )
        elif self.context is None:
            raise ActivationContractError("This exclusion reason requires member context.")
        elif self.prediction.member_id != self.context.member_id:
            raise ActivationContractError("Prediction and context member IDs must match.")


@dataclass(frozen=True)
class SuppressedPrediction:
    """Prediction withheld temporarily by a governed suppression rule."""

    prediction: ScoredPrediction
    context: MemberActivationContext
    reason_code: ReasonCode
    suppression_until: date | None

    def __post_init__(self) -> None:
        """Validate a suppressed prediction."""
        if self.prediction.member_id != self.context.member_id:
            raise ActivationContractError("Prediction and context member IDs must match.")

        if self.reason_code not in SUPPRESSION_REASON_CODES:
            raise ActivationContractError("Suppressed predictions require a suppression reason.")


@dataclass(frozen=True)
class InterventionRecommendation:
    """Supportive recommendation presented for human review."""

    category: InterventionCategory
    rationale_code: ReasonCode
    message_template_key: str
    requires_human_review: bool = True

    def __post_init__(self) -> None:
        """Validate recommendation safety controls."""
        _require_non_empty(self.message_template_key, "message_template_key")

        if self.rationale_code is not ReasonCode.DEFAULT_SUPPORTIVE_INTERVENTION:
            raise ActivationContractError(
                "Stage 5.1 recommendations must use the default supportive rationale."
            )

        if not self.requires_human_review:
            raise ActivationContractError("Activation recommendations require human review.")


@dataclass(frozen=True)
class SelectedActivation:
    """Capacity-selected recommendation awaiting human review."""

    run_id: str
    eligible_prediction: EligiblePrediction
    recommendation: InterventionRecommendation
    priority_rank: int
    selected_at: datetime

    def __post_init__(self) -> None:
        """Validate a selected activation."""
        _require_non_empty(self.run_id, "run_id")
        _require_aware(self.selected_at, "selected_at")

        if self.priority_rank < 1:
            raise ActivationContractError("priority_rank must be at least one.")


@dataclass(frozen=True)
class ActivationAuditRecord:
    """Flattened, immutable audit record for one activation decision."""

    run_id: str
    policy_version: str
    member_id: str
    prediction_date: date
    decision_timestamp: datetime
    outcome: DecisionOutcome
    reason_code: ReasonCode
    risk_probability: float
    model_name: str
    threshold: float
    intervention_category: InterventionCategory | None = None
    priority_rank: int | None = None

    def __post_init__(self) -> None:
        """Validate audit consistency for selected and no-contact outcomes."""
        _require_non_empty(self.run_id, "run_id")
        _require_non_empty(self.policy_version, "policy_version")
        _require_non_empty(self.member_id, "member_id")
        _require_non_empty(self.model_name, "model_name")
        _require_aware(self.decision_timestamp, "decision_timestamp")

        if not isfinite(self.risk_probability):
            raise ActivationContractError("risk_probability must be finite.")

        if self.risk_probability < 0.0 or self.risk_probability > 1.0:
            raise ActivationContractError("risk_probability must fall between zero and one.")

        if not isfinite(self.threshold) or self.threshold < 0.0 or self.threshold > 1.0:
            raise ActivationContractError("threshold must fall between zero and one.")

        expected_reason_sets = {
            DecisionOutcome.NO_CONTACT_SUPERSEDED: frozenset(
                {ReasonCode.SUPERSEDED_BY_LATEST_PREDICTION}
            ),
            DecisionOutcome.NO_CONTACT_BELOW_THRESHOLD: frozenset(
                {ReasonCode.BELOW_FROZEN_THRESHOLD}
            ),
            DecisionOutcome.NO_CONTACT_EXCLUDED: EXCLUSION_REASON_CODES,
            DecisionOutcome.NO_CONTACT_SUPPRESSED: SUPPRESSION_REASON_CODES,
            DecisionOutcome.NO_CONTACT_CAPACITY: frozenset({ReasonCode.CAPACITY_LIMIT_REACHED}),
        }

        if self.outcome is DecisionOutcome.SELECTED_FOR_REVIEW:
            if self.reason_code is not ReasonCode.SELECTED_FOR_HUMAN_REVIEW:
                raise ActivationContractError("Selected audit records require the selected reason.")
            if self.intervention_category is None:
                raise ActivationContractError(
                    "Selected audit records require an intervention category."
                )
            if self.priority_rank is None or self.priority_rank < 1:
                raise ActivationContractError("Selected audit records require a positive rank.")
            return

        if self.reason_code not in expected_reason_sets[self.outcome]:
            raise ActivationContractError("Audit outcome and reason code are inconsistent.")

        if self.intervention_category is not None or self.priority_rank is not None:
            raise ActivationContractError(
                "No-contact audit records must not contain an intervention or rank."
            )


@dataclass(frozen=True)
class ActivationRunMetadata:
    """Lineage and summary metadata for one deterministic activation run."""

    run_id: str
    policy_version: str
    policy_fingerprint: str
    model_name: str
    threshold: float
    scoring_artifact_path: str
    scoring_artifact_sha256: str
    decision_timestamp: datetime
    capacity_limit: int
    source_row_count: int
    source_member_count: int
    superseded_count: int
    below_threshold_count: int
    excluded_count: int
    suppressed_count: int
    eligible_count: int
    capacity_not_selected_count: int
    selected_count: int

    def __post_init__(self) -> None:
        """Validate run-level lineage and decision counts."""
        _require_non_empty(self.run_id, "run_id")
        _require_non_empty(self.policy_version, "policy_version")
        _require_non_empty(self.model_name, "model_name")
        _require_non_empty(self.scoring_artifact_path, "scoring_artifact_path")
        _require_sha256(self.policy_fingerprint, "policy_fingerprint")
        _require_sha256(self.scoring_artifact_sha256, "scoring_artifact_sha256")
        _require_aware(self.decision_timestamp, "decision_timestamp")

        if not isfinite(self.threshold) or self.threshold < 0.0 or self.threshold > 1.0:
            raise ActivationContractError("threshold must fall between zero and one.")

        counts = (
            self.capacity_limit,
            self.source_row_count,
            self.source_member_count,
            self.superseded_count,
            self.below_threshold_count,
            self.excluded_count,
            self.suppressed_count,
            self.eligible_count,
            self.capacity_not_selected_count,
            self.selected_count,
        )
        if any(count < 0 for count in counts):
            raise ActivationContractError("Activation run counts must not be negative.")

        if self.selected_count > self.capacity_limit:
            raise ActivationContractError("selected_count must not exceed capacity_limit.")

        if self.eligible_count != self.selected_count + self.capacity_not_selected_count:
            raise ActivationContractError(
                "eligible_count must equal selected plus capacity-not-selected counts."
            )

        decision_total = (
            self.superseded_count
            + self.below_threshold_count
            + self.excluded_count
            + self.suppressed_count
            + self.capacity_not_selected_count
            + self.selected_count
        )
        if decision_total != self.source_row_count:
            raise ActivationContractError(
                "Activation decision counts must reconcile to source_row_count."
            )

        if self.source_row_count - self.superseded_count != self.source_member_count:
            raise ActivationContractError(
                "Non-superseded rows must reconcile to source_member_count."
            )
