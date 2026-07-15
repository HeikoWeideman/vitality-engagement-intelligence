"""Tests for the synthetic member-day skeleton generator."""

from datetime import date

import pandas as pd
from pandas.testing import assert_frame_equal

from vitality_engagement.data.generate_engagement import (
    generate_member_day_skeleton,
)
from vitality_engagement.data.schema import GenerationConfig


def test_skeleton_has_expected_shape_and_columns() -> None:
    """The skeleton should contain one row per member per date."""
    config = GenerationConfig(
        member_count=3,
        day_count=4,
        random_seed=42,
        start_date=date(2025, 1, 1),
    )

    skeleton = generate_member_day_skeleton(config)

    assert skeleton.shape == (12, 7)
    assert list(skeleton.columns) == [
        "member_id",
        "age_band",
        "membership_months",
        "activity_level",
        "reward_profile",
        "intervention_profile",
        "date",
    ]


def test_skeleton_uses_configured_date_range() -> None:
    """Dates should begin on the configured date and remain consecutive."""
    config = GenerationConfig(
        member_count=2,
        day_count=5,
        random_seed=42,
        start_date=date(2025, 3, 10),
    )

    skeleton = generate_member_day_skeleton(config)
    unique_dates = skeleton["date"].drop_duplicates().reset_index(drop=True)

    expected_dates = pd.Series(
        pd.date_range(
            start="2025-03-10",
            periods=5,
            freq="D",
        ),
        name="date",
    )

    pd.testing.assert_series_equal(
        unique_dates,
        expected_dates,
        check_dtype=False,
    )


def test_member_date_key_is_unique() -> None:
    """Each member-date combination should appear exactly once."""
    config = GenerationConfig(
        member_count=10,
        day_count=7,
        random_seed=42,
    )

    skeleton = generate_member_day_skeleton(config)

    duplicate_count = skeleton.duplicated(subset=["member_id", "date"]).sum()

    assert duplicate_count == 0


def test_each_member_has_configured_number_of_days() -> None:
    """Every member should have the same configured observation period."""
    config = GenerationConfig(
        member_count=10,
        day_count=14,
        random_seed=42,
    )

    skeleton = generate_member_day_skeleton(config)
    rows_per_member = skeleton.groupby("member_id").size()

    assert (rows_per_member == 14).all()


def test_skeleton_is_reproducible() -> None:
    """Identical configurations should produce identical results."""
    config = GenerationConfig(
        member_count=20,
        day_count=10,
        random_seed=17,
    )

    first_result = generate_member_day_skeleton(config)
    second_result = generate_member_day_skeleton(config)

    assert_frame_equal(first_result, second_result)
