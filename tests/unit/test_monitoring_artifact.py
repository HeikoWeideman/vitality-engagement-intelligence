"""Tests for governed Stage 7 monitoring artifact persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from vitality_engagement.monitoring.artifact import (
    MONITORING_ARTIFACT_VERSION,
    MONITORING_CHECK_COLUMNS,
    MonitoringArtifactContext,
    MonitoringArtifactError,
    build_monitoring_artifact_metadata,
    build_monitoring_check_frame,
    build_monitoring_run_id,
    verify_monitoring_artifact,
    write_monitoring_artifact,
)
from vitality_engagement.monitoring.engine import MonitoringRunResult
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


def make_monitoring_result() -> MonitoringRunResult:
    """Create a compact valid monitoring result."""
    checks = (
        MonitoringCheckResult(
            check_name="scoring_row_count",
            check_type=MonitoringCheckType.SCORING_VOLUME,
            severity=MonitoringSeverity.PASS,
            observed_value=4.0,
            expected_value=4.0,
            details="Scoring row count matches the governed expectation.",
        ),
        MonitoringCheckResult(
            check_name="probability_population_stability_index",
            check_type=MonitoringCheckType.PROBABILITY_DRIFT,
            severity=MonitoringSeverity.WARNING,
            observed_value=0.15,
            expected_value=0.0,
            warning_threshold=0.10,
            critical_threshold=0.25,
            reference_row_count=8,
            current_row_count=4,
            details="Probability PSI reached the configured warning range.",
        ),
    )

    return MonitoringRunResult(
        policy_version="stage7-test-v1",
        policy_fingerprint="a" * 64,
        model_name="python_logistic_baseline",
        threshold=0.431,
        scoring_artifact_sha256="b" * 64,
        reference_row_count=8,
        current_row_count=4,
        overall_severity=MonitoringSeverity.WARNING,
        checks=checks,
    )


def make_monitoring_context() -> MonitoringArtifactContext:
    """Create compact valid source-lineage context."""
    return MonitoringArtifactContext(
        monitoring_timestamp=MONITORING_TIMESTAMP,
        modeling_data_path="data/modeling/test.parquet",
        modeling_data_sha256="c" * 64,
        model_artifact_path="models/test.pkl",
        model_artifact_sha256="d" * 64,
        model_metadata_path="models/test.metadata.json",
        model_metadata_sha256="e" * 64,
        scoring_artifact_path="artifacts/scoring/test.parquet",
        scoring_artifact_sha256="b" * 64,
        scoring_metadata_path="artifacts/scoring/test.metadata.json",
        scoring_metadata_sha256="f" * 64,
    )


def test_monitoring_run_id_is_deterministic() -> None:
    result = make_monitoring_result()
    context = make_monitoring_context()

    first = build_monitoring_run_id(result, context)
    second = build_monitoring_run_id(result, context)

    assert first == second
    assert first.startswith("mon_")
    assert len(first) == 28


def test_monitoring_frame_and_metadata_reconcile() -> None:
    result = make_monitoring_result()
    context = make_monitoring_context()

    frame = build_monitoring_check_frame(result, context)
    metadata = build_monitoring_artifact_metadata(result, context)

    assert list(frame.columns) == list(MONITORING_CHECK_COLUMNS)
    assert len(frame) == 2
    assert frame["run_id"].nunique() == 1
    assert frame["overall_severity"].eq("warning").all()

    assert metadata.artifact_version == MONITORING_ARTIFACT_VERSION
    assert metadata.check_count == 2
    assert metadata.pass_count == 1
    assert metadata.warning_count == 1
    assert metadata.critical_count == 0
    assert metadata.overall_severity == "warning"


def test_monitoring_artifacts_are_written_and_verified(
    tmp_path: Path,
) -> None:
    check_path = tmp_path / "monitoring.parquet"
    metadata_path = tmp_path / "monitoring.metadata.json"
    result = make_monitoring_result()
    context = make_monitoring_context()

    write_monitoring_artifact(
        result,
        context,
        check_path=check_path,
        metadata_path=metadata_path,
    )

    assert check_path.is_file()
    assert metadata_path.is_file()

    restored = pd.read_parquet(check_path)
    assert len(restored) == 2
    assert list(restored.columns) == list(MONITORING_CHECK_COLUMNS)

    verify_monitoring_artifact(
        check_path,
        metadata_path,
        expected_result=result,
        expected_context=context,
    )


def test_monitoring_artifact_rejects_shared_output_path(
    tmp_path: Path,
) -> None:
    shared_path = tmp_path / "shared-output"

    with pytest.raises(
        MonitoringArtifactError,
        match="must differ",
    ):
        write_monitoring_artifact(
            make_monitoring_result(),
            make_monitoring_context(),
            check_path=shared_path,
            metadata_path=shared_path,
        )


def test_monitoring_check_tampering_is_rejected(
    tmp_path: Path,
) -> None:
    check_path = tmp_path / "monitoring.parquet"
    metadata_path = tmp_path / "monitoring.metadata.json"
    result = make_monitoring_result()
    context = make_monitoring_context()

    write_monitoring_artifact(
        result,
        context,
        check_path=check_path,
        metadata_path=metadata_path,
    )

    restored = pd.read_parquet(check_path)
    restored.loc[
        restored["check_name"].eq("probability_population_stability_index"),
        "observed_value",
    ] = 0.30
    restored.to_parquet(
        check_path,
        index=False,
    )

    with pytest.raises(
        MonitoringArtifactError,
        match="do not match",
    ):
        verify_monitoring_artifact(
            check_path,
            metadata_path,
            expected_result=result,
            expected_context=context,
        )


def test_monitoring_metadata_tampering_is_rejected(
    tmp_path: Path,
) -> None:
    check_path = tmp_path / "monitoring.parquet"
    metadata_path = tmp_path / "monitoring.metadata.json"
    result = make_monitoring_result()
    context = make_monitoring_context()

    write_monitoring_artifact(
        result,
        context,
        check_path=check_path,
        metadata_path=metadata_path,
    )

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["critical_count"] = 1
    metadata_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        MonitoringArtifactError,
        match="metadata does not match",
    ):
        verify_monitoring_artifact(
            check_path,
            metadata_path,
            expected_result=result,
            expected_context=context,
        )


def test_monitoring_context_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(
        MonitoringArtifactError,
        match="timezone-aware",
    ):
        MonitoringArtifactContext(
            monitoring_timestamp=datetime(2025, 6, 30, 9, 0),
            modeling_data_path="data/modeling/test.parquet",
            modeling_data_sha256="c" * 64,
            model_artifact_path="models/test.pkl",
            model_artifact_sha256="d" * 64,
            model_metadata_path="models/test.metadata.json",
            model_metadata_sha256="e" * 64,
            scoring_artifact_path="artifacts/scoring/test.parquet",
            scoring_artifact_sha256="b" * 64,
            scoring_metadata_path="artifacts/scoring/test.metadata.json",
            scoring_metadata_sha256="f" * 64,
        )


def test_monitoring_context_rejects_invalid_digest() -> None:
    with pytest.raises(
        MonitoringArtifactError,
        match="SHA-256",
    ):
        MonitoringArtifactContext(
            monitoring_timestamp=MONITORING_TIMESTAMP,
            modeling_data_path="data/modeling/test.parquet",
            modeling_data_sha256="not-a-digest",
            model_artifact_path="models/test.pkl",
            model_artifact_sha256="d" * 64,
            model_metadata_path="models/test.metadata.json",
            model_metadata_sha256="e" * 64,
            scoring_artifact_path="artifacts/scoring/test.parquet",
            scoring_artifact_sha256="b" * 64,
            scoring_metadata_path="artifacts/scoring/test.metadata.json",
            scoring_metadata_sha256="f" * 64,
        )
