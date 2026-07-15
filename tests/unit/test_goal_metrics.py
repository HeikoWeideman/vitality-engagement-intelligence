"""Tests for weekly goal metrics and future outcomes."""

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from vitality_engagement.data.generate_engagement import (
    generate_daily_engagement,
    generate_modeling_dataset,
)
from vitality_engagement.data.goal_metrics import (
    add_goal_metrics_and_target,
)
from vitality_engagement.data.schema import GenerationConfig


def test_goal_metrics_preserve_member_day_rows() -> None:
    """Adding goal metrics should not create or remove daily records."""
    config = GenerationConfig(
        member_count=5,
        day_count=20,
        random_seed=42,
    )

    engagement = generate_daily_engagement(config)
    result = add_goal_metrics_and_target(engagement)

    assert len(result) == len(engagement)
    assert not result.duplicated(subset=["member_id", "date"]).any()


def test_weekly_progress_resets_at_new_week() -> None:
    """Weekly active-minute progress should restart every Monday."""
    engagement = pd.DataFrame(
        {
            "member_id": ["M000001"] * 10,
            "date": pd.date_range(
                start="2025-01-06",
                periods=10,
                freq="D",
            ),
            "active_minutes": [10] * 10,
            "weekly_goal": [100] * 10,
        }
    )

    result = add_goal_metrics_and_target(engagement)

    assert result.loc[0, "weekly_active_minutes_so_far"] == 10
    assert result.loc[6, "weekly_active_minutes_so_far"] == 70
    assert result.loc[7, "weekly_active_minutes_so_far"] == 10


def test_previous_streaks_and_failures_use_prior_weeks() -> None:
    """Historical metrics must not use the current week's result."""
    active_minutes = [20] * 7 + [15] * 7 + [5] * 7 + [20] * 7

    engagement = pd.DataFrame(
        {
            "member_id": ["M000001"] * 28,
            "date": pd.date_range(
                start="2025-01-06",
                periods=28,
                freq="D",
            ),
            "active_minutes": active_minutes,
            "weekly_goal": [100] * 28,
        }
    )

    result = add_goal_metrics_and_target(engagement)

    weekly_rows = (
        result.groupby(
            "week_start",
            sort=True,
        )
        .head(1)
        .reset_index(drop=True)
    )

    assert weekly_rows["previous_goal_streak"].tolist() == [
        0,
        1,
        2,
        0,
    ]

    assert weekly_rows["previous_failed_goals"].tolist() == [
        0,
        0,
        0,
        1,
    ]


def test_future_target_matches_future_active_minutes() -> None:
    """The target should reflect whether the next seven days miss the goal."""
    result = generate_modeling_dataset(
        GenerationConfig(
            member_count=10,
            day_count=30,
            random_seed=42,
        )
    )

    labelled = result.dropna(subset=["future_7_day_active_minutes"])

    expected_target = labelled["future_7_day_active_minutes"] < labelled["weekly_goal"]

    actual_target = labelled["will_miss_goal_next_7_days"].astype(bool)

    assert np.array_equal(
        actual_target.to_numpy(),
        expected_target.to_numpy(),
    )


def test_final_seven_days_have_no_future_label() -> None:
    """The final seven days cannot have a complete future window."""
    result = generate_modeling_dataset(
        GenerationConfig(
            member_count=10,
            day_count=30,
            random_seed=42,
        )
    )

    final_rows = result.groupby(
        "member_id",
        sort=False,
    ).tail(7)

    assert final_rows["future_7_day_active_minutes"].isna().all()
    assert final_rows["next_week_goal_completed"].isna().all()
    assert final_rows["will_miss_goal_next_7_days"].isna().all()


def test_modeling_dataset_is_reproducible() -> None:
    """Identical configuration should generate identical results."""
    config = GenerationConfig(
        member_count=20,
        day_count=30,
        random_seed=17,
    )

    first_result = generate_modeling_dataset(config)
    second_result = generate_modeling_dataset(config)

    assert_frame_equal(first_result, second_result)
