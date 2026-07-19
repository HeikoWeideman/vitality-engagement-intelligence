"""Governed activation-policy contracts, decisions, and artifacts."""

from vitality_engagement.activation.artifact import (
    ACTIVATION_DECISION_COLUMNS,
    DEFAULT_ACTIVATION_DECISION_PATH,
    DEFAULT_ACTIVATION_METADATA_PATH,
    ActivationArtifactError,
    ActivationArtifactMetadata,
    build_activation_artifact_metadata,
    build_activation_decision_frame,
    verify_activation_artifact,
    write_activation_artifact,
)
from vitality_engagement.activation.engine import (
    ActivationDecisionError,
    ActivationDecisionResult,
    decide_activations,
)
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
    "ACTIVATION_DECISION_COLUMNS",
    "DEFAULT_ACTIVATION_DECISION_PATH",
    "DEFAULT_ACTIVATION_METADATA_PATH",
    "ActivationArtifactError",
    "ActivationArtifactMetadata",
    "ActivationAuditRecord",
    "ActivationContractError",
    "ActivationDecisionError",
    "ActivationDecisionResult",
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
    "build_activation_artifact_metadata",
    "build_activation_decision_frame",
    "build_activation_run_id",
    "calculate_policy_fingerprint",
    "decide_activations",
    "verify_activation_artifact",
    "write_activation_artifact",
]
