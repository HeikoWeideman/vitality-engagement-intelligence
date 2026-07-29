"""Tests for governed Stage 6 dashboard controls."""

from __future__ import annotations

from dataclasses import replace

import pytest

from vitality_engagement.dashboard import (
    REQUIRED_DASHBOARD_DISCLAIMERS,
    DashboardAudience,
    DashboardContractError,
    DashboardGovernancePolicy,
    DashboardProhibitedUse,
)


def test_default_policy_preserves_dashboard_safety_controls() -> None:
    policy = DashboardGovernancePolicy()

    assert policy.synthetic_data_only is True
    assert policy.read_only is True
    assert policy.governed_views_only is True
    assert policy.member_level_access_allowed is False
    assert policy.operational_actions_allowed is False
    assert policy.subgroup_minimum_cell_count == 10
    assert set(policy.allowed_audiences) == set(DashboardAudience)
    assert set(policy.prohibited_uses) == set(DashboardProhibitedUse)
    assert policy.required_disclaimer_ids == frozenset(REQUIRED_DASHBOARD_DISCLAIMERS)


def test_policy_rejects_missing_approved_audience() -> None:
    with pytest.raises(DashboardContractError, match="approved dashboard audience"):
        DashboardGovernancePolicy(allowed_audiences=frozenset())


def test_policy_rejects_non_synthetic_sources() -> None:
    with pytest.raises(DashboardContractError, match="synthetic-only"):
        DashboardGovernancePolicy(synthetic_data_only=False)


def test_policy_rejects_writable_dashboard() -> None:
    with pytest.raises(DashboardContractError, match="read-only"):
        DashboardGovernancePolicy(read_only=False)


def test_policy_rejects_direct_ungoverned_sources() -> None:
    with pytest.raises(DashboardContractError, match="governed views"):
        DashboardGovernancePolicy(governed_views_only=False)


def test_policy_rejects_member_level_access() -> None:
    with pytest.raises(DashboardContractError, match="Member-level"):
        DashboardGovernancePolicy(member_level_access_allowed=True)


def test_policy_rejects_operational_actions() -> None:
    with pytest.raises(DashboardContractError, match="Operational dashboard actions"):
        DashboardGovernancePolicy(operational_actions_allowed=True)


def test_policy_rejects_small_subgroup_cell_threshold() -> None:
    with pytest.raises(DashboardContractError, match="at least 10"):
        DashboardGovernancePolicy(subgroup_minimum_cell_count=9)


def test_policy_rejects_missing_required_disclaimer() -> None:
    policy = DashboardGovernancePolicy()

    with pytest.raises(DashboardContractError, match="synthetic_data"):
        replace(
            policy,
            required_disclaimer_ids=(policy.required_disclaimer_ids - {"synthetic_data"}),
        )


def test_policy_rejects_missing_prohibited_use() -> None:
    policy = DashboardGovernancePolicy()

    with pytest.raises(DashboardContractError, match="outreach_approval"):
        replace(
            policy,
            prohibited_uses=(policy.prohibited_uses - {DashboardProhibitedUse.OUTREACH_APPROVAL}),
        )
