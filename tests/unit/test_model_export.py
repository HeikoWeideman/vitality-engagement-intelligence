"""Tests for the deterministic BigQuery modelling export."""

from pathlib import Path

import pandas as pd
import pytest

from vitality_engagement.models.export_features import (
    ExportConfig,
    ModelExportValidationError,
    build_export_query,
    validate_export_frame,
    write_export_frame,
)
from vitality_engagement.models.schema import (
    CATEGORICAL_FEATURE_COLUMNS,
    EXPORT_COLUMNS,
    MODEL_FEATURE_COLUMNS,
    SPLIT_COLUMN,
    TARGET_COLUMN,
)


def make_valid_export_frame() -> pd.DataFrame:
    """Create a small frame that follows the production export contract."""
    split_dates = {
        "train": "2025-04-30",
        "validation": "2025-05-31",
        "test": "2025-06-22",
        "scoring": "2025-06-29",
    }
    rows: list[dict[str, object]] = []

    for split_name, prediction_date in split_dates.items():
        for member_number in range(2):
            row: dict[str, object] = {
                "member_id": f"member-{member_number:03d}",
                "prediction_date": pd.Timestamp(prediction_date),
                SPLIT_COLUMN: split_name,
                TARGET_COLUMN: None if split_name == "scoring" else bool(member_number),
            }

            for feature_name in MODEL_FEATURE_COLUMNS:
                row[feature_name] = (
                    "category"
                    if feature_name in CATEGORICAL_FEATURE_COLUMNS
                    else float(member_number + 1)
                )

            rows.append(row)

    frame = pd.DataFrame(rows, columns=list(EXPORT_COLUMNS))
    return frame.sort_values(
        ["prediction_date", "member_id"],
        kind="stable",
    ).reset_index(drop=True)


def expected_small_split_counts() -> dict[str, int]:
    return {
        "train": 2,
        "validation": 2,
        "test": 2,
        "scoring": 2,
    }


def test_build_export_query_uses_explicit_approved_columns() -> None:
    query = build_export_query(ExportConfig())

    assert "label_will_miss_goal_next_7_days AS will_miss_goal_next_7_days" in query
    assert (
        "FROM "
        "`vitality-engagement-43999."
        "vitality_engagement_dev."
        "engagement_modeling_split`" in query
    )
    assert query.endswith("ORDER BY prediction_date, member_id")
    assert "feature_window_start" not in query
    assert "intervention_profile_as_of" not in query


def test_validate_export_frame_accepts_valid_contract() -> None:
    frame = make_valid_export_frame()

    validate_export_frame(
        frame,
        expected_split_row_counts=expected_small_split_counts(),
        expected_member_count=2,
    )


def test_validate_export_frame_rejects_wrong_columns() -> None:
    frame = make_valid_export_frame().drop(columns=["avg_daily_steps_28d"])

    with pytest.raises(
        ModelExportValidationError,
        match="columns do not match",
    ):
        validate_export_frame(
            frame,
            expected_split_row_counts=expected_small_split_counts(),
            expected_member_count=2,
        )


def test_validate_export_frame_rejects_duplicate_keys() -> None:
    frame = make_valid_export_frame()
    frame.loc[1, "member_id"] = frame.loc[0, "member_id"]
    frame.loc[1, "prediction_date"] = frame.loc[0, "prediction_date"]

    with pytest.raises(
        ModelExportValidationError,
        match="Duplicate member",
    ):
        validate_export_frame(
            frame,
            expected_split_row_counts=expected_small_split_counts(),
            expected_member_count=2,
        )


def test_validate_export_frame_rejects_split_count_changes() -> None:
    frame = make_valid_export_frame()
    frame.loc[0, SPLIT_COLUMN] = "validation"

    with pytest.raises(
        ModelExportValidationError,
        match="split row counts",
    ):
        validate_export_frame(
            frame,
            expected_split_row_counts=expected_small_split_counts(),
            expected_member_count=2,
        )


def test_validate_export_frame_rejects_scoring_labels() -> None:
    frame = make_valid_export_frame()
    scoring_index = frame.index[frame[SPLIT_COLUMN] == "scoring"][0]
    frame.loc[scoring_index, TARGET_COLUMN] = True

    with pytest.raises(
        ModelExportValidationError,
        match="Scoring rows unexpectedly",
    ):
        validate_export_frame(
            frame,
            expected_split_row_counts=expected_small_split_counts(),
            expected_member_count=2,
        )


def test_write_export_frame_creates_readable_parquet(tmp_path: Path) -> None:
    frame = make_valid_export_frame()
    output_path = tmp_path / "modeling.parquet"

    write_export_frame(frame, output_path)

    restored = pd.read_parquet(output_path)
    assert output_path.exists()
    assert len(restored) == len(frame)
    assert list(restored.columns) == list(EXPORT_COLUMNS)
