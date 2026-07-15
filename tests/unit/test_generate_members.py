"""Tests for the synthetic member generator."""

import pandas as pd
from pandas.testing import assert_frame_equal

from vitality_engagement.data.generate_members import generate_members
from vitality_engagement.data.schema import (
    ActivityLevel,
    GenerationConfig,
    ResponseProfile,
)


def test_generate_members_has_expected_shape_and_columns() -> None:
    """The generator should return one correctly structured row per member."""
    config = GenerationConfig(
        member_count=25,
        day_count=30,
        random_seed=42,
    )

    members = generate_members(config)

    assert members.shape == (25, 6)
    assert list(members.columns) == [
        "member_id",
        "age_band",
        "membership_months",
        "activity_level",
        "reward_profile",
        "intervention_profile",
    ]


def test_generate_members_creates_unique_member_ids() -> None:
    """Every generated member should have a unique stable identifier."""
    config = GenerationConfig(
        member_count=100,
        day_count=30,
        random_seed=42,
    )

    members = generate_members(config)

    assert members["member_id"].is_unique
    assert members.iloc[0]["member_id"] == "M000001"
    assert members.iloc[-1]["member_id"] == "M000100"


def test_generate_members_is_reproducible() -> None:
    """Identical configurations should produce identical profiles."""
    config = GenerationConfig(
        member_count=50,
        day_count=30,
        random_seed=7,
    )

    first_result = generate_members(config)
    second_result = generate_members(config)

    assert_frame_equal(first_result, second_result)


def test_generate_members_changes_with_random_seed() -> None:
    """Changing the random seed should change the profiles."""
    first_result = generate_members(
        GenerationConfig(
            member_count=50,
            day_count=30,
            random_seed=7,
        )
    )
    second_result = generate_members(
        GenerationConfig(
            member_count=50,
            day_count=30,
            random_seed=8,
        )
    )

    assert not first_result.equals(second_result)


def test_generate_members_respects_expected_values() -> None:
    """Generated values should remain within documented categories."""
    config = GenerationConfig(
        member_count=500,
        day_count=30,
        random_seed=42,
    )

    members = generate_members(config)

    expected_activity_levels = {level.value for level in ActivityLevel}
    expected_response_profiles = {profile.value for profile in ResponseProfile}
    expected_age_bands = {
        "18-24",
        "25-34",
        "35-44",
        "45-54",
        "55+",
    }

    assert members["membership_months"].between(1, 120).all()
    assert set(members["age_band"]) <= expected_age_bands
    assert set(members["activity_level"]) <= expected_activity_levels
    assert set(members["reward_profile"]) <= expected_response_profiles
    assert set(members["intervention_profile"]) <= expected_response_profiles
    assert not members.isna().any().any()


def test_generate_members_returns_dataframe() -> None:
    """The public generator should return a pandas DataFrame."""
    members = generate_members(GenerationConfig())

    assert isinstance(members, pd.DataFrame)
