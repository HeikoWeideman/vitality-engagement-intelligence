"""Governed contracts for the read-only Stage 6 dashboard layer."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class DashboardContractError(ValueError):
    """Raised when a dashboard governance contract is unsafe or incomplete."""


class DashboardAudience(StrEnum):
    """Approved audiences for the synthetic dashboard."""

    TECHNICAL_REVIEWER = "technical_reviewer"
    MODEL_GOVERNANCE_REVIEWER = "model_governance_reviewer"
    DATA_GOVERNANCE_REVIEWER = "data_governance_reviewer"
    AUTHORISED_HUMAN_REVIEWER = "authorised_human_reviewer"


class DashboardMetricClass(StrEnum):
    """Governed semantic classes for dashboard metrics."""

    SYNTHETIC_DESCRIPTIVE = "synthetic_descriptive"
    FORECAST = "forecast"
    OBSERVED_OUTCOME = "observed_outcome"
    ACTIVATION_AUDIT = "activation_audit"
    LINEAGE = "lineage"
    DATA_QUALITY = "data_quality"


class DashboardProhibitedUse(StrEnum):
    """Uses that the dashboard must never enable or imply."""

    OUTREACH_DISPATCH = "outreach_dispatch"
    OUTREACH_APPROVAL = "outreach_approval"
    CASE_MANAGEMENT = "case_management"
    BENEFIT_OR_ELIGIBILITY_CHANGE = "benefit_or_eligibility_change"
    PENALTY = "penalty"
    TREATMENT_ASSIGNMENT = "treatment_assignment"
    CLINICAL_CONCLUSION = "clinical_conclusion"
    CAUSAL_INTERVENTION_CLAIM = "causal_intervention_claim"
    MEMBER_LEVEL_EXPORT = "member_level_export"


REQUIRED_DASHBOARD_DISCLAIMERS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "synthetic_data": (
            "All dashboard data is fully synthetic and is shown for technical demonstration only."
        ),
        "forecast_not_outcome": ("Predictions are forecasts, not confirmed missed-goal outcomes."),
        "review_not_approval": (
            "Selected for review means pending authorised human review, not approved outreach."
        ),
        "descriptive_not_causal": (
            "Dashboard content is descriptive and does not establish causal intervention effects."
        ),
        "visibility_not_authorisation": (
            "Dashboard visibility does not authorise contact, messaging, case changes, "
            "eligibility changes, penalties, treatment, or clinical conclusions."
        ),
    }
)

REQUIRED_DISCLAIMER_IDS: Final[frozenset[str]] = frozenset(REQUIRED_DASHBOARD_DISCLAIMERS)

DEFAULT_ALLOWED_AUDIENCES: Final[frozenset[DashboardAudience]] = frozenset(DashboardAudience)

DEFAULT_PROHIBITED_USES: Final[frozenset[DashboardProhibitedUse]] = frozenset(
    DashboardProhibitedUse
)


@dataclass(frozen=True)
class DashboardGovernancePolicy:
    """Fail-closed governance controls for the Looker Studio layer."""

    allowed_audiences: frozenset[DashboardAudience] = DEFAULT_ALLOWED_AUDIENCES
    prohibited_uses: frozenset[DashboardProhibitedUse] = DEFAULT_PROHIBITED_USES
    required_disclaimer_ids: frozenset[str] = REQUIRED_DISCLAIMER_IDS
    synthetic_data_only: bool = True
    read_only: bool = True
    governed_views_only: bool = True
    member_level_access_allowed: bool = False
    operational_actions_allowed: bool = False
    subgroup_minimum_cell_count: int = 10

    def __post_init__(self) -> None:
        """Reject governance configurations that weaken safety controls."""
        if not self.allowed_audiences:
            raise DashboardContractError("At least one approved dashboard audience is required.")

        if not self.synthetic_data_only:
            raise DashboardContractError("Stage 6 dashboard sources must remain synthetic-only.")

        if not self.read_only:
            raise DashboardContractError("The Stage 6 dashboard must remain read-only.")

        if not self.governed_views_only:
            raise DashboardContractError("The dashboard must connect only to governed views.")

        if self.member_level_access_allowed:
            raise DashboardContractError("Member-level dashboard access is prohibited.")

        if self.operational_actions_allowed:
            raise DashboardContractError("Operational dashboard actions are prohibited.")

        if self.subgroup_minimum_cell_count < 10:
            raise DashboardContractError("Subgroup minimum cell count must be at least 10.")

        missing_disclaimers = REQUIRED_DISCLAIMER_IDS - self.required_disclaimer_ids

        if missing_disclaimers:
            missing_text = ", ".join(sorted(missing_disclaimers))
            raise DashboardContractError(
                f"Required dashboard disclaimers are missing: {missing_text}"
            )

        missing_prohibitions = DEFAULT_PROHIBITED_USES - self.prohibited_uses

        if missing_prohibitions:
            missing_text = ", ".join(sorted(use.value for use in missing_prohibitions))
            raise DashboardContractError(f"Required prohibited uses are missing: {missing_text}")
