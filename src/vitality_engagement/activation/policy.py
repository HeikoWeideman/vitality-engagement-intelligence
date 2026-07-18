"""Deterministic Stage 5 activation policy configuration and identifiers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Final

from vitality_engagement.activation.schema import (
    ActivationContractError,
    InterventionCategory,
)

DEFAULT_POLICY_VERSION: Final = "stage5-dev-v1"
DEFAULT_INTERVENTION_CATEGORIES: Final = (
    InterventionCategory.SUPPORTIVE_CHECK_IN,
    InterventionCategory.GOAL_PLANNING,
    InterventionCategory.ACTIVITY_REMINDER,
    InterventionCategory.REWARDS_EDUCATION,
)


@dataclass(frozen=True)
class ActivationPolicy:
    """Configurable, deterministic controls for one activation run."""

    policy_version: str = DEFAULT_POLICY_VERSION
    high_risk_only: bool = True
    maximum_prediction_age_days: int = 7
    contact_cooldown_days: int = 7
    maximum_interventions_per_member_28d: int = 2
    maximum_activations_per_run: int = 100
    allowed_intervention_categories: tuple[InterventionCategory, ...] = (
        DEFAULT_INTERVENTION_CATEGORIES
    )
    human_review_required: bool = True
    supportive_use_only: bool = True

    def __post_init__(self) -> None:
        """Validate policy safety and capacity controls."""
        if not self.policy_version.strip():
            raise ActivationContractError("policy_version must not be empty.")

        if not self.high_risk_only:
            raise ActivationContractError("Stage 5 activation must remain high-risk only.")

        if self.maximum_prediction_age_days < 0:
            raise ActivationContractError("maximum_prediction_age_days must not be negative.")

        if self.contact_cooldown_days < 0:
            raise ActivationContractError("contact_cooldown_days must not be negative.")

        if self.maximum_interventions_per_member_28d < 1:
            raise ActivationContractError(
                "maximum_interventions_per_member_28d must be at least one."
            )

        if self.maximum_activations_per_run < 1:
            raise ActivationContractError("maximum_activations_per_run must be at least one.")

        if not self.allowed_intervention_categories:
            raise ActivationContractError("At least one intervention category is required.")

        if len(set(self.allowed_intervention_categories)) != len(
            self.allowed_intervention_categories
        ):
            raise ActivationContractError("Intervention categories must not contain duplicates.")

        if not self.human_review_required:
            raise ActivationContractError("Human review must remain required.")

        if not self.supportive_use_only:
            raise ActivationContractError("The activation policy must remain supportive-only.")


def _policy_payload(policy: ActivationPolicy) -> dict[str, object]:
    """Return a canonical JSON-compatible policy representation."""
    return {
        "allowed_intervention_categories": [
            category.value for category in policy.allowed_intervention_categories
        ],
        "contact_cooldown_days": policy.contact_cooldown_days,
        "high_risk_only": policy.high_risk_only,
        "human_review_required": policy.human_review_required,
        "maximum_activations_per_run": policy.maximum_activations_per_run,
        "maximum_interventions_per_member_28d": (policy.maximum_interventions_per_member_28d),
        "maximum_prediction_age_days": policy.maximum_prediction_age_days,
        "policy_version": policy.policy_version,
        "supportive_use_only": policy.supportive_use_only,
    }


def calculate_policy_fingerprint(policy: ActivationPolicy) -> str:
    """Return a stable SHA-256 fingerprint for the complete policy."""
    encoded_payload = json.dumps(
        _policy_payload(policy),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded_payload).hexdigest()


def _validate_sha256(value: str) -> None:
    """Validate a lowercase hexadecimal SHA-256 digest."""
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ActivationContractError("scoring_artifact_sha256 must be a lowercase SHA-256 digest.")


def build_activation_run_id(
    *,
    policy: ActivationPolicy,
    model_name: str,
    threshold: float,
    scoring_artifact_sha256: str,
    decision_date: date,
) -> str:
    """Build an idempotent run ID from governed immutable inputs."""
    if not model_name.strip():
        raise ActivationContractError("model_name must not be empty.")

    if not isfinite(threshold) or threshold < 0.0 or threshold > 1.0:
        raise ActivationContractError("threshold must fall between zero and one.")

    _validate_sha256(scoring_artifact_sha256)

    payload = {
        "decision_date": decision_date.isoformat(),
        "model_name": model_name,
        "policy_fingerprint": calculate_policy_fingerprint(policy),
        "scoring_artifact_sha256": scoring_artifact_sha256,
        "threshold": threshold,
    }
    encoded_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded_payload).hexdigest()
    return f"act_{digest[:24]}"
