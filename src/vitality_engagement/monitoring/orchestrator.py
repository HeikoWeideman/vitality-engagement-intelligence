"""Fail-closed local orchestration for governed Stage 7 monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sklearn.pipeline import Pipeline

from vitality_engagement.models.load_data import (
    DEFAULT_MODELING_DATA_PATH,
    ChronologicalModelingData,
    load_chronological_modeling_data,
)
from vitality_engagement.models.persistence import (
    DEFAULT_METADATA_PATH as DEFAULT_MODEL_METADATA_PATH,
)
from vitality_engagement.models.persistence import (
    DEFAULT_MODEL_PATH,
    ModelArtifactMetadata,
    load_selected_model,
)
from vitality_engagement.models.scoring_artifact import (
    DEFAULT_PREDICTION_PATH,
    DEFAULT_SCORING_METADATA_PATH,
    VerifiedScoringArtifact,
    load_verified_scoring_artifact,
)
from vitality_engagement.monitoring.artifact import (
    DEFAULT_MONITORING_CHECK_PATH,
    DEFAULT_MONITORING_METADATA_PATH,
    MonitoringArtifactContext,
    calculate_file_sha256,
    write_monitoring_artifact,
)
from vitality_engagement.monitoring.engine import (
    MonitoringRunResult,
    evaluate_monitoring_run,
)
from vitality_engagement.monitoring.policy import MonitoringPolicy


class MonitoringOrchestrationError(RuntimeError):
    """Raised when monitoring inputs or paths are unsafe or ambiguous."""


@dataclass(frozen=True)
class MonitoringOrchestrationResult:
    """Verified inputs, deterministic checks, and local artifact paths."""

    modeling_data: ChronologicalModelingData
    pipeline: Pipeline
    model_metadata: ModelArtifactMetadata
    scoring_artifact: VerifiedScoringArtifact
    monitoring_result: MonitoringRunResult
    artifact_context: MonitoringArtifactContext
    check_path: Path
    metadata_path: Path


def _validate_distinct_paths(
    *,
    modeling_data_path: Path,
    model_path: Path,
    model_metadata_path: Path,
    scoring_prediction_path: Path,
    scoring_metadata_path: Path,
    monitoring_check_path: Path,
    monitoring_metadata_path: Path,
) -> None:
    """Prevent outputs from overlapping governed inputs or one another."""
    named_paths = {
        "modeling_data_path": modeling_data_path,
        "model_path": model_path,
        "model_metadata_path": model_metadata_path,
        "scoring_prediction_path": scoring_prediction_path,
        "scoring_metadata_path": scoring_metadata_path,
        "monitoring_check_path": monitoring_check_path,
        "monitoring_metadata_path": monitoring_metadata_path,
    }

    resolved: dict[Path, str] = {}

    for field_name, path in named_paths.items():
        normalised = path.resolve()

        if normalised in resolved:
            raise MonitoringOrchestrationError(
                f"{field_name} and {resolved[normalised]} must use distinct paths."
            )

        resolved[normalised] = field_name


def _build_artifact_context(
    *,
    monitoring_timestamp: datetime,
    modeling_data_path: Path,
    model_path: Path,
    model_metadata_path: Path,
    scoring_prediction_path: Path,
    scoring_metadata_path: Path,
    scoring_artifact: VerifiedScoringArtifact,
) -> MonitoringArtifactContext:
    """Build immutable lineage from verified local source artifacts."""
    scoring_artifact_sha256 = calculate_file_sha256(scoring_prediction_path)

    if scoring_artifact_sha256 != scoring_artifact.prediction_artifact_sha256:
        raise MonitoringOrchestrationError(
            "Verified scoring-artifact SHA-256 does not match the source file."
        )

    return MonitoringArtifactContext(
        monitoring_timestamp=monitoring_timestamp,
        modeling_data_path=str(modeling_data_path),
        modeling_data_sha256=calculate_file_sha256(modeling_data_path),
        model_artifact_path=str(model_path),
        model_artifact_sha256=calculate_file_sha256(model_path),
        model_metadata_path=str(model_metadata_path),
        model_metadata_sha256=calculate_file_sha256(model_metadata_path),
        scoring_artifact_path=str(scoring_prediction_path),
        scoring_artifact_sha256=scoring_artifact_sha256,
        scoring_metadata_path=str(scoring_metadata_path),
        scoring_metadata_sha256=calculate_file_sha256(scoring_metadata_path),
    )


def orchestrate_local_monitoring(
    *,
    monitoring_timestamp: datetime,
    policy: MonitoringPolicy | None = None,
    modeling_data_path: Path = DEFAULT_MODELING_DATA_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    model_metadata_path: Path = DEFAULT_MODEL_METADATA_PATH,
    scoring_prediction_path: Path = DEFAULT_PREDICTION_PATH,
    scoring_metadata_path: Path = DEFAULT_SCORING_METADATA_PATH,
    monitoring_check_path: Path = DEFAULT_MONITORING_CHECK_PATH,
    monitoring_metadata_path: Path = DEFAULT_MONITORING_METADATA_PATH,
) -> MonitoringOrchestrationResult:
    """Verify inputs, evaluate checks, and write local monitoring artifacts."""
    _validate_distinct_paths(
        modeling_data_path=modeling_data_path,
        model_path=model_path,
        model_metadata_path=model_metadata_path,
        scoring_prediction_path=scoring_prediction_path,
        scoring_metadata_path=scoring_metadata_path,
        monitoring_check_path=monitoring_check_path,
        monitoring_metadata_path=monitoring_metadata_path,
    )

    modeling_data = load_chronological_modeling_data(modeling_data_path)
    pipeline, model_metadata = load_selected_model(
        model_path=model_path,
        metadata_path=model_metadata_path,
    )
    scoring_artifact = load_verified_scoring_artifact(
        scoring_prediction_path,
        scoring_metadata_path,
    )

    monitoring_result = evaluate_monitoring_run(
        data=modeling_data,
        pipeline=pipeline,
        model_metadata=model_metadata,
        scoring_artifact=scoring_artifact,
        policy=policy,
    )

    artifact_context = _build_artifact_context(
        monitoring_timestamp=monitoring_timestamp,
        modeling_data_path=modeling_data_path,
        model_path=model_path,
        model_metadata_path=model_metadata_path,
        scoring_prediction_path=scoring_prediction_path,
        scoring_metadata_path=scoring_metadata_path,
        scoring_artifact=scoring_artifact,
    )

    written_check_path, written_metadata_path = write_monitoring_artifact(
        monitoring_result,
        artifact_context,
        check_path=monitoring_check_path,
        metadata_path=monitoring_metadata_path,
    )

    return MonitoringOrchestrationResult(
        modeling_data=modeling_data,
        pipeline=pipeline,
        model_metadata=model_metadata,
        scoring_artifact=scoring_artifact,
        monitoring_result=monitoring_result,
        artifact_context=artifact_context,
        check_path=written_check_path,
        metadata_path=written_metadata_path,
    )
