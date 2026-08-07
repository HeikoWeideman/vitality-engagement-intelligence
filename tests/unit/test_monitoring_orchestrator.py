"""Tests for fail-closed local Stage 7 monitoring orchestration."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from vitality_engagement.models.load_data import (
    ChronologicalModelingData,
    LabelledModelSplit,
    ScoringModelSplit,
)
from vitality_engagement.models.persistence import (
    ModelArtifactMetadata,
    build_model_metadata,
)
from vitality_engagement.models.predict import (
    HIGH_RISK_COLUMN,
    MODEL_NAME_COLUMN,
    PREDICTION_OUTPUT_COLUMNS,
    RISK_PROBABILITY_COLUMN,
    THRESHOLD_COLUMN,
    PredictionResult,
)
from vitality_engagement.models.schema import MODEL_FEATURE_COLUMNS
from vitality_engagement.models.scoring_artifact import (
    ScoringArtifactError,
    write_scoring_artifact,
)
from vitality_engagement.monitoring.engine import MonitoringRunResult
from vitality_engagement.monitoring.orchestrator import (
    MonitoringOrchestrationError,
    orchestrate_local_monitoring,
)
from vitality_engagement.monitoring.schema import (
    MonitoringCheckResult,
    MonitoringCheckType,
    MonitoringSeverity,
)

MONITORING_TIMESTAMP = datetime(
    2025,
    6,
    30,
    9,
    0,
    tzinfo=UTC,
)


def _minimal_modeling_data() -> ChronologicalModelingData:
    """Create structurally valid compact chronological model data."""
    identifiers = pd.DataFrame(
        {
            "member_id": ["member-001"],
            "prediction_date": [pd.Timestamp("2025-06-29")],
        }
    )
    feature_row: dict[str, object] = {feature_name: 1.0 for feature_name in MODEL_FEATURE_COLUMNS}
    feature_row["age_band_as_of"] = "18-24"
    feature_row["activity_level_as_of"] = "low"
    feature_row["reward_profile_as_of"] = "low"
    features = pd.DataFrame(
        [feature_row],
        columns=list(MODEL_FEATURE_COLUMNS),
    )
    target = pd.Series([False], dtype=bool)

    return ChronologicalModelingData(
        train=LabelledModelSplit(
            name="train",
            identifiers=identifiers.copy(),
            features=features.copy(),
            target=target.copy(),
        ),
        validation=LabelledModelSplit(
            name="validation",
            identifiers=identifiers.copy(),
            features=features.copy(),
            target=target.copy(),
        ),
        test=LabelledModelSplit(
            name="test",
            identifiers=identifiers.copy(),
            features=features.copy(),
            target=target.copy(),
        ),
        scoring=ScoringModelSplit(
            identifiers=identifiers.copy(),
            features=features.copy(),
        ),
    )


def _monitoring_result() -> MonitoringRunResult:
    """Create a compact passing monitoring result."""
    check = MonitoringCheckResult(
        check_name="scoring_row_count",
        check_type=MonitoringCheckType.SCORING_VOLUME,
        severity=MonitoringSeverity.PASS,
        observed_value=1.0,
        expected_value=1.0,
        details="Scoring row count matches the governed expectation.",
    )

    return MonitoringRunResult(
        policy_version="stage7-test-v1",
        policy_fingerprint="a" * 64,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256="b" * 64,
        reference_row_count=1,
        current_row_count=1,
        overall_severity=MonitoringSeverity.PASS,
        checks=(check,),
    )


def _write_scoring_artifacts(
    tmp_path: Path,
) -> tuple[Path, Path]:
    """Write one valid governed scoring artifact pair."""
    prediction_path = tmp_path / "predictions.parquet"
    metadata_path = tmp_path / "predictions.metadata.json"
    threshold = 0.431

    predictions = pd.DataFrame(
        {
            "member_id": ["member-001"],
            "prediction_date": [pd.Timestamp("2025-06-29")],
            RISK_PROBABILITY_COLUMN: [0.60],
            HIGH_RISK_COLUMN: [True],
            MODEL_NAME_COLUMN: ["python_logistic_baseline"],
            THRESHOLD_COLUMN: [threshold],
        },
        columns=list(PREDICTION_OUTPUT_COLUMNS),
    )

    write_scoring_artifact(
        PredictionResult(
            predictions=predictions,
            model_name="python_logistic_baseline",
            threshold=threshold,
            row_count=1,
        ),
        prediction_path=prediction_path,
        metadata_path=metadata_path,
    )

    return prediction_path, metadata_path


def _write_other_inputs(
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    """Write local files required for immutable lineage hashing."""
    modeling_data_path = tmp_path / "modeling.parquet"
    model_path = tmp_path / "model.pkl"
    model_metadata_path = tmp_path / "model.metadata.json"

    modeling_data_path.write_bytes(b"modeling-data")
    model_path.write_bytes(b"trusted-model")
    model_metadata_path.write_bytes(b"trusted-model-metadata")

    return (
        modeling_data_path,
        model_path,
        model_metadata_path,
    )


def _patch_verified_components(
    monkeypatch: pytest.MonkeyPatch,
) -> ModelArtifactMetadata:
    """Replace heavyweight loaders and evaluation with governed test values."""
    model_metadata = build_model_metadata()

    monkeypatch.setattr(
        "vitality_engagement.monitoring.orchestrator.load_chronological_modeling_data",
        lambda path: _minimal_modeling_data(),
    )
    monkeypatch.setattr(
        "vitality_engagement.monitoring.orchestrator.load_selected_model",
        lambda **kwargs: (
            Pipeline(steps=[]),
            model_metadata,
        ),
    )
    monkeypatch.setattr(
        "vitality_engagement.monitoring.orchestrator.evaluate_monitoring_run",
        lambda **kwargs: _monitoring_result(),
    )

    return model_metadata


def test_orchestrator_verifies_and_writes_local_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_verified_components(monkeypatch)

    modeling_data_path, model_path, model_metadata_path = _write_other_inputs(tmp_path)
    prediction_path, scoring_metadata_path = _write_scoring_artifacts(tmp_path)
    check_path = tmp_path / "monitoring.parquet"
    metadata_path = tmp_path / "monitoring.metadata.json"

    result = orchestrate_local_monitoring(
        monitoring_timestamp=MONITORING_TIMESTAMP,
        modeling_data_path=modeling_data_path,
        model_path=model_path,
        model_metadata_path=model_metadata_path,
        scoring_prediction_path=prediction_path,
        scoring_metadata_path=scoring_metadata_path,
        monitoring_check_path=check_path,
        monitoring_metadata_path=metadata_path,
    )

    assert result.check_path == check_path
    assert result.metadata_path == metadata_path
    assert check_path.is_file()
    assert metadata_path.is_file()
    assert result.monitoring_result.overall_severity is (MonitoringSeverity.PASS)
    assert result.artifact_context.modeling_data_sha256 == (
        hashlib.sha256(modeling_data_path.read_bytes()).hexdigest()
    )
    assert result.artifact_context.scoring_artifact_sha256 == (
        hashlib.sha256(prediction_path.read_bytes()).hexdigest()
    )


def test_scoring_failure_writes_no_monitoring_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_verified_components(monkeypatch)

    modeling_data_path, model_path, model_metadata_path = _write_other_inputs(tmp_path)
    prediction_path, scoring_metadata_path = _write_scoring_artifacts(tmp_path)
    check_path = tmp_path / "monitoring.parquet"
    metadata_path = tmp_path / "monitoring.metadata.json"

    restored = pd.read_parquet(prediction_path)
    restored.loc[0, RISK_PROBABILITY_COLUMN] = 0.20
    restored.to_parquet(
        prediction_path,
        index=False,
    )

    with pytest.raises(ScoringArtifactError):
        orchestrate_local_monitoring(
            monitoring_timestamp=MONITORING_TIMESTAMP,
            modeling_data_path=modeling_data_path,
            model_path=model_path,
            model_metadata_path=model_metadata_path,
            scoring_prediction_path=prediction_path,
            scoring_metadata_path=scoring_metadata_path,
            monitoring_check_path=check_path,
            monitoring_metadata_path=metadata_path,
        )

    assert not check_path.exists()
    assert not metadata_path.exists()


def test_path_collision_is_rejected_before_inputs_are_loaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modeling_data_path, model_path, model_metadata_path = _write_other_inputs(tmp_path)
    prediction_path, scoring_metadata_path = _write_scoring_artifacts(tmp_path)
    metadata_path = tmp_path / "monitoring.metadata.json"
    original_digest = hashlib.sha256(modeling_data_path.read_bytes()).hexdigest()

    def fail_if_loaded(path: Path) -> ChronologicalModelingData:
        raise AssertionError("Input loading must not occur after path collision.")

    monkeypatch.setattr(
        "vitality_engagement.monitoring.orchestrator.load_chronological_modeling_data",
        fail_if_loaded,
    )

    with pytest.raises(
        MonitoringOrchestrationError,
        match="must use distinct paths",
    ):
        orchestrate_local_monitoring(
            monitoring_timestamp=MONITORING_TIMESTAMP,
            modeling_data_path=modeling_data_path,
            model_path=model_path,
            model_metadata_path=model_metadata_path,
            scoring_prediction_path=prediction_path,
            scoring_metadata_path=scoring_metadata_path,
            monitoring_check_path=modeling_data_path,
            monitoring_metadata_path=metadata_path,
        )

    assert hashlib.sha256(modeling_data_path.read_bytes()).hexdigest() == (original_digest)
    assert not metadata_path.exists()


def test_missing_lineage_file_writes_no_monitoring_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_verified_components(monkeypatch)

    modeling_data_path, model_path, model_metadata_path = _write_other_inputs(tmp_path)
    prediction_path, scoring_metadata_path = _write_scoring_artifacts(tmp_path)
    model_path.unlink()

    check_path = tmp_path / "monitoring.parquet"
    metadata_path = tmp_path / "monitoring.metadata.json"

    with pytest.raises(
        FileNotFoundError,
        match="does not exist",
    ):
        orchestrate_local_monitoring(
            monitoring_timestamp=MONITORING_TIMESTAMP,
            modeling_data_path=modeling_data_path,
            model_path=model_path,
            model_metadata_path=model_metadata_path,
            scoring_prediction_path=prediction_path,
            scoring_metadata_path=scoring_metadata_path,
            monitoring_check_path=check_path,
            monitoring_metadata_path=metadata_path,
        )

    assert not check_path.exists()
    assert not metadata_path.exists()
