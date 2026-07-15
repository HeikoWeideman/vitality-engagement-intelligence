"""Tests for controlled synthetic data-quality issues."""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from vitality_engagement.data.data_quality import (
    add_data_quality_issues,
)
from vitality_engagement.data.generate_engagement import (
    generate_modeling_dataset,
)
from vitality_engagement.data.schema import GenerationConfig


def create_sample_data() -> pd.DataFrame:
    """Create a small valid dataset for data-quality tests."""
    return pd.DataFrame(
        {
            "member_id": ["M000001"] * 4,
            "date": pd.date_range(
                start="2025-01-01",
                periods=4,
                freq="D",
            ),
            "sleep_hours": [7.0, 7.5, 6.5, 8.0],
            "app_sessions": [1, 0, 2, 1],
            "daily_steps": [5000, 6000, 7000, 8000],
            "activity_level": [
                "low",
                "moderate",
                "high",
                "low",
            ],
        }
    )


def test_zero_rates_preserve_observed_values() -> None:
    """Zero issue rates should preserve the original observations."""
    data = create_sample_data()

    config = GenerationConfig(
        member_count=1,
        day_count=4,
        sleep_missing_rate=0.0,
        app_session_missing_rate=0.0,
        step_outlier_rate=0.0,
        delayed_record_rate=0.0,
        category_change_rate=0.0,
    )

    result = add_data_quality_issues(
        data,
        config,
    )

    assert result["sleep_hours"].notna().all()
    assert result["app_sessions"].notna().all()
    assert not result["is_step_outlier"].any()
    assert not result["is_late_record"].any()
    assert not result["activity_level_changed"].any()
    assert result["record_delay_days"].eq(0).all()

    assert (result["available_date"] == result["date"]).all()


def test_full_rates_apply_every_issue() -> None:
    """Rates of one should apply every supported issue."""
    data = create_sample_data()
    original_activity = data["activity_level"].copy()

    config = GenerationConfig(
        member_count=1,
        day_count=4,
        sleep_missing_rate=1.0,
        app_session_missing_rate=1.0,
        step_outlier_rate=1.0,
        delayed_record_rate=1.0,
        category_change_rate=1.0,
    )

    result = add_data_quality_issues(
        data,
        config,
    )

    assert result["sleep_hours"].isna().all()
    assert result["app_sessions"].isna().all()

    assert (
        result["daily_steps"]
        .between(
            40000,
            60000,
        )
        .all()
    )

    assert result["is_step_outlier"].all()
    assert result["is_late_record"].all()
    assert result["activity_level_changed"].all()

    assert (
        result["record_delay_days"]
        .between(
            1,
            3,
        )
        .all()
    )

    assert (
        result["activity_level"].reset_index(drop=True) != original_activity.reset_index(drop=True)
    ).all()


def test_data_quality_generation_is_reproducible() -> None:
    """Identical inputs should produce identical imperfections."""
    data = pd.concat(
        [create_sample_data()] * 25,
        ignore_index=True,
    )

    data["member_id"] = [f"M{index:06d}" for index in range(1, len(data) + 1)]

    config = GenerationConfig(
        member_count=len(data),
        day_count=1,
        random_seed=17,
    )

    first_result = add_data_quality_issues(
        data,
        config,
    )

    second_result = add_data_quality_issues(
        data,
        config,
    )

    assert_frame_equal(
        first_result,
        second_result,
    )


def test_modeling_dataset_contains_quality_metadata() -> None:
    """The complete generator should include monitoring fields."""
    result = generate_modeling_dataset(
        GenerationConfig(
            member_count=20,
            day_count=30,
            random_seed=42,
        )
    )

    expected_columns = {
        "sleep_hours_missing",
        "app_sessions_missing",
        "is_step_outlier",
        "is_late_record",
        "record_delay_days",
        "available_date",
        "activity_level_changed",
    }

    assert expected_columns <= set(result.columns)


def test_data_quality_rejects_missing_columns() -> None:
    """Missing required fields should produce a clear error."""
    incomplete_data = pd.DataFrame(
        {
            "member_id": ["M000001"],
            "date": pd.to_datetime(["2025-01-01"]),
        }
    )

    with pytest.raises(
        ValueError,
        match="Missing required data-quality columns",
    ):
        add_data_quality_issues(
            incomplete_data,
            GenerationConfig(
                member_count=1,
                day_count=1,
            ),
        )
