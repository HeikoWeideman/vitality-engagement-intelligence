"""Tests for the governed local Stage 7 monitoring command-line entry point."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vitality_engagement.monitoring import cli
from vitality_engagement.monitoring.schema import (
    MonitoringCheckResult,
    MonitoringCheckType,
    MonitoringSeverity,
)


@dataclass(frozen=True)
class _FakeMonitoringResult:
    overall_severity: MonitoringSeverity
    checks: tuple[MonitoringCheckResult, ...]


@dataclass(frozen=True)
class _FakeArtifactContext:
    marker: str = "test-context"


@dataclass(frozen=True)
class _FakeOrchestrationResult:
    monitoring_result: _FakeMonitoringResult
    artifact_context: _FakeArtifactContext
    check_path: Path
    metadata_path: Path


def _make_check(
    severity: MonitoringSeverity,
) -> MonitoringCheckResult:
    """Create one compact CLI-summary check."""
    return MonitoringCheckResult(
        check_name=f"{severity.value}_check",
        check_type=MonitoringCheckType.SCORING_VOLUME,
        severity=severity,
        observed_value=1.0,
        expected_value=1.0,
        details="Compact monitoring CLI test check.",
    )


def test_parser_requires_monitoring_timestamp() -> None:
    parser = cli.build_argument_parser()

    with pytest.raises(SystemExit) as error:
        parser.parse_args([])

    assert error.value.code == 2


def test_parser_rejects_naive_monitoring_timestamp() -> None:
    parser = cli.build_argument_parser()

    with pytest.raises(SystemExit) as error:
        parser.parse_args(
            [
                "--monitoring-timestamp",
                "2025-06-30T08:00:00",
            ]
        )

    assert error.value.code == 2


def test_parser_normalises_aware_timestamp_to_utc() -> None:
    arguments = cli.build_argument_parser().parse_args(
        [
            "--monitoring-timestamp",
            "2025-06-30T10:00:00+02:00",
        ]
    )

    assert arguments.monitoring_timestamp == datetime(
        2025,
        6,
        30,
        8,
        0,
        tzinfo=UTC,
    )


def test_help_exposes_no_remote_alert_or_action_options() -> None:
    help_text = cli.build_argument_parser().format_help().lower()

    for prohibited_term in (
        "bigquery",
        "warehouse",
        "upload",
        "dispatch",
        "send",
        "outreach",
        "webhook",
    ):
        assert prohibited_term not in help_text


def test_main_runs_local_orchestrator_and_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    check_path = tmp_path / "monitoring.parquet"
    metadata_path = tmp_path / "monitoring.metadata.json"
    checks = (
        _make_check(MonitoringSeverity.PASS),
        _make_check(MonitoringSeverity.WARNING),
    )

    def fake_orchestrate_local_monitoring(
        **arguments: object,
    ) -> _FakeOrchestrationResult:
        captured.update(arguments)
        return _FakeOrchestrationResult(
            monitoring_result=_FakeMonitoringResult(
                overall_severity=MonitoringSeverity.WARNING,
                checks=checks,
            ),
            artifact_context=_FakeArtifactContext(),
            check_path=check_path,
            metadata_path=metadata_path,
        )

    monkeypatch.setattr(
        cli,
        "orchestrate_local_monitoring",
        fake_orchestrate_local_monitoring,
    )
    monkeypatch.setattr(
        cli,
        "build_monitoring_run_id",
        lambda result, context: "mon_test_run",
    )

    exit_code = cli.main(
        [
            "--monitoring-timestamp",
            "2025-06-30T10:00:00+02:00",
            "--modeling-data-path",
            str(tmp_path / "modeling.parquet"),
            "--model-path",
            str(tmp_path / "model.pkl"),
            "--model-metadata-path",
            str(tmp_path / "model.metadata.json"),
            "--scoring-prediction-path",
            str(tmp_path / "predictions.parquet"),
            "--scoring-metadata-path",
            str(tmp_path / "predictions.metadata.json"),
            "--monitoring-check-path",
            str(check_path),
            "--monitoring-metadata-path",
            str(metadata_path),
        ]
    )

    assert exit_code == 0
    assert captured["monitoring_timestamp"] == datetime(
        2025,
        6,
        30,
        8,
        0,
        tzinfo=UTC,
    )
    assert captured["modeling_data_path"] == (tmp_path / "modeling.parquet")
    assert captured["model_path"] == tmp_path / "model.pkl"
    assert captured["model_metadata_path"] == (tmp_path / "model.metadata.json")
    assert captured["scoring_prediction_path"] == (tmp_path / "predictions.parquet")
    assert captured["scoring_metadata_path"] == (tmp_path / "predictions.metadata.json")
    assert captured["monitoring_check_path"] == check_path
    assert captured["monitoring_metadata_path"] == metadata_path

    output = capsys.readouterr().out

    assert "Run ID: mon_test_run" in output
    assert f"Monitoring checks: {check_path}" in output
    assert f"Monitoring metadata: {metadata_path}" in output
    assert "Overall severity: warning" in output
    assert "Checks evaluated: 2" in output
    assert "Passing checks: 1" in output
    assert "Warning checks: 1" in output
    assert "Critical checks: 0" in output
    assert "Mode: local artifacts only" in output
    assert "no external alerts or operational actions" in output


def test_main_returns_two_for_critical_monitoring_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    check_path = tmp_path / "monitoring.parquet"
    metadata_path = tmp_path / "monitoring.metadata.json"

    monkeypatch.setattr(
        cli,
        "orchestrate_local_monitoring",
        lambda **arguments: _FakeOrchestrationResult(
            monitoring_result=_FakeMonitoringResult(
                overall_severity=MonitoringSeverity.CRITICAL,
                checks=(_make_check(MonitoringSeverity.CRITICAL),),
            ),
            artifact_context=_FakeArtifactContext(),
            check_path=check_path,
            metadata_path=metadata_path,
        ),
    )
    monkeypatch.setattr(
        cli,
        "build_monitoring_run_id",
        lambda result, context: "mon_critical_run",
    )

    exit_code = cli.main(
        [
            "--monitoring-timestamp",
            "2025-06-30T08:00:00Z",
            "--monitoring-check-path",
            str(check_path),
            "--monitoring-metadata-path",
            str(metadata_path),
        ]
    )

    assert exit_code == 2
