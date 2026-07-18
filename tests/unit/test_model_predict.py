"""Tests for the typed selected-model prediction interface."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from vitality_engagement.models.baseline import fit_logistic_baseline
from vitality_engagement.models.load_data import (
    ChronologicalModelingData,
    build_chronological_modeling_data,
)
from vitality_engagement.models.persistence import save_selected_model
from vitality_engagement.models.predict import (
    HIGH_RISK_COLUMN,
    MODEL_NAME_COLUMN,
    PREDICTION_OUTPUT_COLUMNS,
    RISK_PROBABILITY_COLUMN,
    THRESHOLD_COLUMN,
    PredictionBatch,
    PredictionInputError,
    predict_with_pipeline,
    score_with_persisted_model,
)
from vitality_engagement.models.schema import (
    CATEGORICAL_FEATURE_COLUMNS,
    EXPORT_COLUMNS,
    MODEL_FEATURE_COLUMNS,
    SPLIT_COLUMN,
    TARGET_COLUMN,
)
from vitality_engagement.models.selection import (
    PYTHON_LOGISTIC_SELECTION,
)


def make_modeling_data() -> ChronologicalModelingData:
    """Create compact chronological data for prediction tests."""
    split_dates = {
        "train": "2025-04-30",
        "validation": "2025-05-31",
        "test": "2025-06-22",
        "scoring": "2025-06-29",
    }
    rows: list[dict[str, object]] = []

    for split_name, prediction_date in split_dates.items():
        for member_number in range(6):
            row: dict[str, object] = {
                "member_id": f"member-{member_number:03d}",
                "prediction_date": pd.Timestamp(prediction_date),
                SPLIT_COLUMN: split_name,
                TARGET_COLUMN: (None if split_name == "scoring" else bool(member_number % 2)),
            }

            for feature_name in MODEL_FEATURE_COLUMNS:
                if feature_name in CATEGORICAL_FEATURE_COLUMNS:
                    value: object = "category-a" if member_number % 2 == 0 else "category-b"
                else:
                    value = float(member_number + 1)

                row[feature_name] = value

            rows.append(row)

    frame = (
        pd.DataFrame(rows, columns=list(EXPORT_COLUMNS))
        .sort_values(
            ["prediction_date", "member_id"],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    return build_chronological_modeling_data(
        frame,
        expected_split_row_counts={
            "train": 6,
            "validation": 6,
            "test": 6,
            "scoring": 6,
        },
        expected_member_count=6,
    )


def make_scoring_batch(
    data: ChronologicalModelingData,
) -> PredictionBatch:
    """Build a valid scoring batch."""
    return PredictionBatch(
        identifiers=data.scoring.identifiers,
        features=data.scoring.features,
    )


def test_prediction_output_uses_frozen_threshold() -> None:
    data = make_modeling_data()
    fitted = fit_logistic_baseline(data)

    result = predict_with_pipeline(
        fitted.pipeline,
        make_scoring_batch(data),
        model_name=PYTHON_LOGISTIC_SELECTION.model_name,
        threshold=PYTHON_LOGISTIC_SELECTION.threshold,
    )

    assert list(result.predictions.columns) == list(PREDICTION_OUTPUT_COLUMNS)
    assert result.row_count == 6
    assert result.threshold == pytest.approx(0.431)

    probabilities = result.predictions[RISK_PROBABILITY_COLUMN].to_numpy(dtype=float)
    classifications = result.predictions[HIGH_RISK_COLUMN].to_numpy(dtype=bool)

    assert np.array_equal(
        classifications,
        probabilities >= 0.431,
    )


def test_prediction_output_preserves_identifiers() -> None:
    data = make_modeling_data()
    fitted = fit_logistic_baseline(data)
    batch = make_scoring_batch(data)

    result = predict_with_pipeline(
        fitted.pipeline,
        batch,
        model_name=PYTHON_LOGISTIC_SELECTION.model_name,
        threshold=PYTHON_LOGISTIC_SELECTION.threshold,
    )

    pd.testing.assert_frame_equal(
        result.predictions[["member_id", "prediction_date"]],
        batch.identifiers.reset_index(drop=True),
    )
    assert set(result.predictions[MODEL_NAME_COLUMN]) == {"python_logistic_baseline"}
    assert set(result.predictions[THRESHOLD_COLUMN]) == {0.431}


def test_prediction_batch_rejects_wrong_feature_schema() -> None:
    data = make_modeling_data()
    invalid_features = data.scoring.features.drop(columns=["avg_daily_steps_28d"])

    with pytest.raises(
        PredictionInputError,
        match="Feature columns",
    ):
        PredictionBatch(
            identifiers=data.scoring.identifiers,
            features=invalid_features,
        )


def test_prediction_batch_rejects_duplicate_identifiers() -> None:
    data = make_modeling_data()
    identifiers = data.scoring.identifiers.copy()
    identifiers.loc[1, "member_id"] = identifiers.loc[0, "member_id"]
    identifiers.loc[1, "prediction_date"] = identifiers.loc[
        0,
        "prediction_date",
    ]

    with pytest.raises(
        PredictionInputError,
        match="Duplicate member",
    ):
        PredictionBatch(
            identifiers=identifiers,
            features=data.scoring.features,
        )


def test_persisted_model_can_score_batch(tmp_path: Path) -> None:
    data = make_modeling_data()
    model_path = tmp_path / "model.pkl"
    metadata_path = tmp_path / "model.metadata.json"

    save_selected_model(
        data,
        model_path=model_path,
        metadata_path=metadata_path,
    )

    result = score_with_persisted_model(
        make_scoring_batch(data),
        model_path=model_path,
        metadata_path=metadata_path,
    )

    assert result.row_count == 6
    assert result.model_name == "python_logistic_baseline"
    assert result.threshold == pytest.approx(0.431)
    assert (
        result.predictions[RISK_PROBABILITY_COLUMN]
        .between(
            0.0,
            1.0,
        )
        .all()
    )
