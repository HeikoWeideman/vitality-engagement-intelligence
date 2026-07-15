"""Calculate weekly goal metrics and future seven-day outcomes."""

from typing import Final

import numpy as np
import pandas as pd

REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "member_id",
        "date",
        "active_minutes",
        "weekly_goal",
    }
)


def _previous_completion_streak(
    completed: pd.Series,
) -> pd.Series:
    """Calculate the completed-week streak before each current week."""
    previous_streaks: list[int] = []
    current_streak = 0

    for completed_week in completed.astype(bool).tolist():
        previous_streaks.append(current_streak)

        if bool(completed_week):
            current_streak += 1
        else:
            current_streak = 0

    return pd.Series(
        previous_streaks,
        index=completed.index,
        dtype="int64",
    )


def _future_seven_day_sum(
    active_minutes: pd.Series,
) -> pd.Series:
    """Sum the seven days immediately after each observation date."""
    return (
        active_minutes.astype(float)
        .rolling(
            window=7,
            min_periods=7,
        )
        .sum()
        .shift(-7)
    )


def add_goal_metrics_and_target(
    engagement: pd.DataFrame,
) -> pd.DataFrame:
    """Add weekly progress, historical goal metrics, and future outcomes.

    Args:
        engagement: Daily engagement records ordered by member and date.

    Returns:
        Daily records with weekly metrics and future seven-day labels.

    Raises:
        ValueError: If required columns are missing.
    """
    missing_columns = REQUIRED_COLUMNS - set(engagement.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required engagement columns: {missing_text}")

    result = (
        engagement.sort_values(
            ["member_id", "date"],
        )
        .reset_index(drop=True)
        .copy()
    )

    result["week_start"] = result["date"] - pd.to_timedelta(
        result["date"].dt.dayofweek,
        unit="D",
    )

    member_week_group = result.groupby(
        ["member_id", "week_start"],
        sort=False,
    )

    result["weekly_active_minutes_so_far"] = (
        member_week_group["active_minutes"].cumsum().astype("int64")
    )

    result["goal_completion_percentage"] = np.round(
        100.0 * result["weekly_active_minutes_so_far"] / result["weekly_goal"],
        1,
    )

    weekly_summary = result.groupby(
        ["member_id", "week_start"],
        as_index=False,
        sort=False,
    ).agg(
        weekly_active_minutes=("active_minutes", "sum"),
        weekly_goal=("weekly_goal", "first"),
    )

    weekly_summary["weekly_goal_completed"] = (
        weekly_summary["weekly_active_minutes"] >= weekly_summary["weekly_goal"]
    )

    weekly_summary["previous_goal_streak"] = (
        weekly_summary.groupby(
            "member_id",
            sort=False,
        )["weekly_goal_completed"]
        .transform(_previous_completion_streak)
        .astype("int64")
    )

    failure_indicator = (~weekly_summary["weekly_goal_completed"]).astype("int64")

    weekly_summary["previous_failed_goals"] = (
        failure_indicator.groupby(
            weekly_summary["member_id"],
            sort=False,
        ).cumsum()
        - failure_indicator
    )

    result = result.merge(
        weekly_summary[
            [
                "member_id",
                "week_start",
                "previous_goal_streak",
                "previous_failed_goals",
            ]
        ],
        on=["member_id", "week_start"],
        how="left",
        validate="many_to_one",
    )

    future_active_minutes = result.groupby(
        "member_id",
        sort=False,
    )["active_minutes"].transform(_future_seven_day_sum)

    result["future_7_day_active_minutes"] = future_active_minutes

    next_week_completed = (future_active_minutes >= result["weekly_goal"]).astype("boolean")

    next_week_completed = next_week_completed.mask(
        future_active_minutes.isna(),
        pd.NA,
    )

    result["next_week_goal_completed"] = next_week_completed

    result["will_miss_goal_next_7_days"] = (~next_week_completed).astype("boolean")

    return result
