"""Introduce controlled data-quality issues into synthetic records."""

from typing import Final

import numpy as np
import pandas as pd

from vitality_engagement.data.schema import GenerationConfig

REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "member_id",
        "date",
        "sleep_hours",
        "app_sessions",
        "daily_steps",
        "activity_level",
    }
)

ALTERNATIVE_ACTIVITY_LEVELS: Final[dict[str, tuple[str, str]]] = {
    "low": ("moderate", "high"),
    "moderate": ("low", "high"),
    "high": ("low", "moderate"),
}


def add_data_quality_issues(
    data: pd.DataFrame,
    config: GenerationConfig,
) -> pd.DataFrame:
    """Add reproducible imperfections to observed synthetic data.

    Target fields should be calculated before this function is called.
    This preserves clean latent outcomes while making observed inputs
    realistically imperfect.

    Args:
        data: Clean synthetic daily records.
        config: Reproducible data-generation configuration.

    Returns:
        Records containing controlled missingness, outliers, delays,
        and category changes.

    Raises:
        ValueError: If required columns are missing.
    """
    missing_columns = REQUIRED_COLUMNS - set(data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required data-quality columns: {missing_text}")

    result = (
        data.sort_values(
            ["member_id", "date"],
        )
        .reset_index(drop=True)
        .copy()
    )

    rng = np.random.default_rng(config.random_seed + 4)
    row_count = len(result)

    sleep_missing_mask = rng.random(row_count) < config.sleep_missing_rate

    app_session_missing_mask = rng.random(row_count) < config.app_session_missing_rate

    step_outlier_mask = rng.random(row_count) < config.step_outlier_rate

    delayed_record_mask = rng.random(row_count) < config.delayed_record_rate

    category_change_mask = rng.random(row_count) < config.category_change_rate

    result["sleep_hours"] = result["sleep_hours"].astype("Float64")
    result.loc[
        sleep_missing_mask,
        "sleep_hours",
    ] = pd.NA

    result["app_sessions"] = result["app_sessions"].astype("Int64")
    result.loc[
        app_session_missing_mask,
        "app_sessions",
    ] = pd.NA

    outlier_count = int(step_outlier_mask.sum())

    if outlier_count > 0:
        result.loc[
            step_outlier_mask,
            "daily_steps",
        ] = rng.integers(
            low=40000,
            high=60001,
            size=outlier_count,
        )

    record_delay_days = np.zeros(
        row_count,
        dtype=np.int64,
    )

    delayed_count = int(delayed_record_mask.sum())

    if delayed_count > 0:
        record_delay_days[delayed_record_mask] = rng.integers(
            low=1,
            high=4,
            size=delayed_count,
        )

    original_activity_levels = result["activity_level"].astype(str).to_numpy()

    changed_activity_levels = original_activity_levels.copy()

    changed_indices = np.flatnonzero(category_change_mask)

    for index in changed_indices:
        current_level = original_activity_levels[index]

        changed_activity_levels[index] = rng.choice(ALTERNATIVE_ACTIVITY_LEVELS[current_level])

    result["activity_level"] = changed_activity_levels

    result["sleep_hours_missing"] = sleep_missing_mask
    result["app_sessions_missing"] = app_session_missing_mask
    result["is_step_outlier"] = step_outlier_mask
    result["is_late_record"] = delayed_record_mask
    result["record_delay_days"] = record_delay_days

    result["available_date"] = result["date"] + pd.to_timedelta(
        record_delay_days,
        unit="D",
    )

    result["activity_level_changed"] = category_change_mask

    return result
