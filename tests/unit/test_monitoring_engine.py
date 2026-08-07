"""Tests for deterministic Stage 7 monitoring evaluation."""

from pathlib import Path

import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from vitality_engagement.models.baseline import fit_logistic_baseline
from vitality_engagement.models.load_data import (
    ChronologicalModelingData,
    build_chronological_modeling_data,
)
from vitality_engagement.models.persistence import (
    ModelArtifactMetadata,
    build_model_metadata,
)
from vitality_engagement.models.predict import (
    PredictionBatch,
    predict_with_pipeline,
)
from vitality_engagement.models.schema import (
    EXPORT_COLUMNS,
    MODEL_FEATURE_COLUMNS,
    SPLIT_COLUMN,
    TARGET_COLUMN,
)
from vitality_engagement.models.scoring_artifact import (
    VerifiedScoringArtifact,
    load_verified_scoring_artifact,
    write_scoring_artifact,
)
from vitality_engagement.monitoring.engine import (
    MonitoringEngineError,
    evaluate_monitoring_run,
)
from vitality_engagement.monitoring.policy import MonitoringPolicy
from vitality_engagement.monitoring.schema import (
    MonitoringCheckType,
    MonitoringSeverity,
)


def make_monitoring_data() -> ChronologicalModelingData:
    """Create compact governed data with aligned reference and scoring features."""
    split_dates = {
        "train": "2025-04-30",
        "validation": "2025-05-31",
        "test": "2025-06-22",
        "scoring": "2025-06-29",
    }
    age_bands = (
        "18-24",
        "25-34",
        "35-44",
        "45-54",
    )
    activity_levels = (
        "low",
        "moderate",
        "high",
        "moderate",
    )
    reward_profiles = (
        "low",
        "medium",
        "high",
        "medium",
    )
    rows: list[dict[str, object]] = []

    for split_name, prediction_date in split_dates.items():
        for member_number in range(4):
            row: dict[str, object] = {
                "member_id": f"member-{member_number:03d}",
                "prediction_date": pd.Timestamp(prediction_date),
                SPLIT_COLUMN: split_name,
                TARGET_COLUMN: (None if split_name == "scoring" else bool(member_number % 2)),
            }

            for feature_index, feature_name in enumerate(
                MODEL_FEATURE_COLUMNS,
            ):
                if feature_name == "age_band_as_of":
                    value: object = age_bands[member_number]
                elif feature_name == "activity_level_as_of":
                    value = activity_levels[member_number]
                elif feature_name == "reward_profile_as_of":
                    value = reward_profiles[member_number]
                else:
                    value = float(member_number + feature_index + 1)

                row[feature_name] = value

            rows.append(row)

    frame = (
        pd.DataFrame(
            rows,
            columns=list(EXPORT_COLUMNS),
        )
        .sort_values(
            [
                "prediction_date",
                "member_id",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    return build_chronological_modeling_data(
        frame,
        expected_split_row_counts={
            "train": 4,
            "validation": 4,
            "test": 4,
            "scoring": 4,
        },
        expected_member_count=4,
    )


def make_verified_scoring_artifact(
    tmp_path: Path,
    data: ChronologicalModelingData,
) -> tuple[Pipeline, ModelArtifactMetadata, VerifiedScoringArtifact]:
    """Fit, score, persist, and independently verify a compact artifact."""
    fitted = fit_logistic_baseline(data)
    model_metadata = build_model_metadata()
    scoring_result = predict_with_pipeline(
        fitted.pipeline,
        PredictionBatch(
            identifiers=data.scoring.identifiers,
            features=data.scoring.features,
        ),
        model_name=model_metadata.model_name,
        threshold=model_metadata.selected_threshold,
    )

    prediction_path = tmp_path / "predictions.parquet"
    metadata_path = tmp_path / "predictions.metadata.json"

    write_scoring_artifact(
        scoring_result,
        prediction_path=prediction_path,
        metadata_path=metadata_path,
    )

    return (
        fitted.pipeline,
        model_metadata,
        load_verified_scoring_artifact(
            prediction_path,
            metadata_path,
        ),
    )


def compact_policy() -> MonitoringPolicy:
    """Return monitoring expectations for the compact test batch."""
    return MonitoringPolicy(
        expected_scoring_row_count=4,
        expected_scoring_member_count=4,
        expected_scoring_prediction_day_count=1,
    )


def test_monitoring_engine_returns_complete_passing_result(
    tmp_path: Path,
) -> None:
    data = make_monitoring_data()
    pipeline, model_metadata, scoring_artifact = make_verified_scoring_artifact(
        tmp_path,
        data,
    )

    result = evaluate_monitoring_run(
        data=data,
        pipeline=pipeline,
        model_metadata=model_metadata,
        scoring_artifact=scoring_artifact,
        policy=compact_policy(),
    )

    assert result.overall_severity is MonitoringSeverity.PASS
    assert result.reference_row_count == 4
    assert result.current_row_count == 4
    assert result.model_name == "python_logistic_baseline"
    assert result.threshold == pytest.approx(0.431)
    assert len(result.checks) == 57
    assert all(check.severity is MonitoringSeverity.PASS for check in result.checks)


def test_monitoring_engine_contains_all_feature_checks(
    tmp_path: Path,
) -> None:
    data = make_monitoring_data()
    pipeline, model_metadata, scoring_artifact = make_verified_scoring_artifact(
        tmp_path,
        data,
    )

    result = evaluate_monitoring_run(
        data=data,
        pipeline=pipeline,
        model_metadata=model_metadata,
        scoring_artifact=scoring_artifact,
        policy=compact_policy(),
    )

    numeric_checks = [
        check
        for check in result.checks
        if check.check_type is MonitoringCheckType.NUMERIC_FEATURE_DRIFT
    ]
    categorical_checks = [
        check
        for check in result.checks
        if check.check_type is MonitoringCheckType.CATEGORICAL_FEATURE_DRIFT
    ]
    category_domain_checks = [
        check
        for check in result.checks
        if check.check_type is MonitoringCheckType.UNSEEN_CATEGORY_RATE
    ]

    assert len(numeric_checks) == 44
    assert len(categorical_checks) == 3
    assert len(category_domain_checks) == 3


def test_unexpected_category_rate_becomes_critical(
    tmp_path: Path,
) -> None:
    data = make_monitoring_data()
    pipeline, model_metadata, scoring_artifact = make_verified_scoring_artifact(
        tmp_path,
        data,
    )
    data.scoring.features.loc[
        0,
        "age_band_as_of",
    ] = "unsupported-age-band"

    result = evaluate_monitoring_run(
        data=data,
        pipeline=pipeline,
        model_metadata=model_metadata,
        scoring_artifact=scoring_artifact,
        policy=compact_policy(),
    )

    category_check = next(
        check
        for check in result.checks
        if check.check_name == "unexpected_category_rate__age_band_as_of"
    )

    assert category_check.observed_value == pytest.approx(0.25)
    assert category_check.severity is MonitoringSeverity.CRITICAL
    assert result.overall_severity is MonitoringSeverity.CRITICAL


def test_scoring_volume_mismatch_becomes_critical(
    tmp_path: Path,
) -> None:
    data = make_monitoring_data()
    pipeline, model_metadata, scoring_artifact = make_verified_scoring_artifact(
        tmp_path,
        data,
    )
    policy = MonitoringPolicy(
        expected_scoring_row_count=5,
        expected_scoring_member_count=4,
        expected_scoring_prediction_day_count=1,
    )

    result = evaluate_monitoring_run(
        data=data,
        pipeline=pipeline,
        model_metadata=model_metadata,
        scoring_artifact=scoring_artifact,
        policy=policy,
    )

    row_count_check = next(
        check for check in result.checks if check.check_name == "scoring_row_count"
    )

    assert row_count_check.observed_value == pytest.approx(4.0)
    assert row_count_check.expected_value == pytest.approx(5.0)
    assert row_count_check.severity is MonitoringSeverity.CRITICAL
    assert result.overall_severity is MonitoringSeverity.CRITICAL


def test_scoring_feature_identifier_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    data = make_monitoring_data()
    pipeline, model_metadata, scoring_artifact = make_verified_scoring_artifact(
        tmp_path,
        data,
    )
    data.scoring.identifiers.loc[
        0,
        "member_id",
    ] = "different-member"

    with pytest.raises(
        MonitoringEngineError,
        match="different identifiers",
    ):
        evaluate_monitoring_run(
            data=data,
            pipeline=pipeline,
            model_metadata=model_metadata,
            scoring_artifact=scoring_artifact,
            policy=compact_policy(),
        )
