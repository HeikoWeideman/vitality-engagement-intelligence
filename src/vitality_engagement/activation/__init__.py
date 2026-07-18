"""Governed activation-policy contracts for Stage 5."""

from vitality_engagement.activation.policy import (
    ActivationPolicy,
    build_activation_run_id,
    calculate_policy_fingerprint,
)
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

__all__ = [
    "ActivationAuditRecord",
    "ActivationContractError",
    "ActivationPolicy",
    "ActivationRunMetadata",
    "DecisionOutcome",
    "EligiblePrediction",
    "ExcludedPrediction",
    "InterventionCategory",
    "InterventionRecommendation",
    "MemberActivationContext",
    "ReasonCode",
    "ScoredPrediction",
    "SelectedActivation",
    "SuppressedPrediction",
    "build_activation_run_id",
    "calculate_policy_fingerprint",
]
