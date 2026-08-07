"""Persist and verify governed Stage 7 monitoring artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd

from vitality_engagement.monitoring.engine import MonitoringRunResult
from vitality_engagement.monitoring.schema import (
    MonitoringCheckType,
    MonitoringSeverity,
)

DEFAULT_MONITORING_CHECK_PATH: Final = Path("artifacts/monitoring/monitoring_checks.parquet")
DEFAULT_MONITORING_METADATA_PATH: Final = Path(
    "artifacts/monitoring/monitoring_checks.metadata.json"
)
MONITORING_ARTIFACT_VERSION: Final = 1

RUN_ID_COLUMN: Final = "run_id"
MONITORING_TIMESTAMP_COLUMN: Final = "monitoring_timestamp"
POLICY_VERSION_COLUMN: Final = "policy_version"
POLICY_FINGERPRINT_COLUMN: Final = "policy_fingerprint"
OVERALL_SEVERITY_COLUMN: Final = "overall_severity"
CHECK_NAME_COLUMN: Final = "check_name"
CHECK_TYPE_COLUMN: Final = "check_type"
SEVERITY_COLUMN: Final = "severity"
FEATURE_NAME_COLUMN: Final = "feature_name"
OBSERVED_VALUE_COLUMN: Final = "observed_value"
EXPECTED_VALUE_COLUMN: Final = "expected_value"
WARNING_THRESHOLD_COLUMN: Final = "warning_threshold"
CRITICAL_THRESHOLD_COLUMN: Final = "critical_threshold"
REFERENCE_ROW_COUNT_COLUMN: Final = "reference_row_count"
CURRENT_ROW_COUNT_COLUMN: Final = "current_row_count"
DETAILS_COLUMN: Final = "details"

MONITORING_CHECK_COLUMNS: Final = (
    RUN_ID_COLUMN,
    MONITORING_TIMESTAMP_COLUMN,
    POLICY_VERSION_COLUMN,
    POLICY_FINGERPRINT_COLUMN,
    OVERALL_SEVERITY_COLUMN,
    CHECK_NAME_COLUMN,
    CHECK_TYPE_COLUMN,
    SEVERITY_COLUMN,
    FEATURE_NAME_COLUMN,
    OBSERVED_VALUE_COLUMN,
    EXPECTED_VALUE_COLUMN,
    WARNING_THRESHOLD_COLUMN,
    CRITICAL_THRESHOLD_COLUMN,
    REFERENCE_ROW_COUNT_COLUMN,
    CURRENT_ROW_COUNT_COLUMN,
    DETAILS_COLUMN,
)


class MonitoringArtifactError(RuntimeError):
    """Raised when a monitoring artifact violates its governed contract."""


@dataclass(frozen=True)
class MonitoringArtifactContext:
    """Verified source lineage for one local monitoring run."""

    monitoring_timestamp: datetime
    modeling_data_path: str
    modeling_data_sha256: str
    model_artifact_path: str
    model_artifact_sha256: str
    model_metadata_path: str
    model_metadata_sha256: str
    scoring_artifact_path: str
    scoring_artifact_sha256: str
    scoring_metadata_path: str
    scoring_metadata_sha256: str

    def __post_init__(self) -> None:
        """Validate timestamp, source paths, and immutable digests."""
        if (
            self.monitoring_timestamp.tzinfo is None
            or self.monitoring_timestamp.utcoffset() is None
        ):
            raise MonitoringArtifactError("monitoring_timestamp must be timezone-aware.")

        path_values = (
            self.modeling_data_path,
            self.model_artifact_path,
            self.model_metadata_path,
            self.scoring_artifact_path,
            self.scoring_metadata_path,
        )

        if any(not value.strip() for value in path_values):
            raise MonitoringArtifactError("Monitoring source paths must not be empty.")

        digest_values = (
            self.modeling_data_sha256,
            self.model_artifact_sha256,
            self.model_metadata_sha256,
            self.scoring_artifact_sha256,
            self.scoring_metadata_sha256,
        )

        for digest in digest_values:
            _validate_sha256(digest)


@dataclass(frozen=True)
class MonitoringArtifactMetadata:
    """Persisted lineage and counts for one monitoring artifact."""

    artifact_version: int
    run_id: str
    monitoring_timestamp: str
    policy_version: str
    policy_fingerprint: str
    overall_severity: str
    model_name: str
    threshold: float
    modeling_data_path: str
    modeling_data_sha256: str
    model_artifact_path: str
    model_artifact_sha256: str
    model_metadata_path: str
    model_metadata_sha256: str
    scoring_artifact_path: str
    scoring_artifact_sha256: str
    scoring_metadata_path: str
    scoring_metadata_sha256: str
    reference_row_count: int
    current_row_count: int
    check_count: int
    pass_count: int
    warning_count: int
    critical_count: int
    output_columns: tuple[str, ...]


def _validate_sha256(value: str) -> None:
    """Require a lowercase hexadecimal SHA-256 digest."""
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise MonitoringArtifactError(
            "Monitoring lineage digests must be lowercase SHA-256 values."
        )


def calculate_file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of one local source artifact."""
    if not path.is_file():
        raise FileNotFoundError(f"Monitoring source artifact does not exist: {path}")

    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for block in iter(
            lambda: file_handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def build_monitoring_run_id(
    result: MonitoringRunResult,
    context: MonitoringArtifactContext,
) -> str:
    """Build an idempotent run ID from governed immutable inputs."""
    payload = {
        "model_artifact_sha256": context.model_artifact_sha256,
        "model_metadata_sha256": context.model_metadata_sha256,
        "model_name": result.model_name,
        "modeling_data_sha256": context.modeling_data_sha256,
        "monitoring_timestamp": context.monitoring_timestamp.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
        "policy_fingerprint": result.policy_fingerprint,
        "scoring_artifact_sha256": context.scoring_artifact_sha256,
        "scoring_metadata_sha256": context.scoring_metadata_sha256,
        "threshold": result.threshold,
    }
    encoded_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded_payload).hexdigest()
    return f"mon_{digest[:24]}"


def build_monitoring_check_frame(
    result: MonitoringRunResult,
    context: MonitoringArtifactContext,
) -> pd.DataFrame:
    """Flatten validated monitoring checks into the persisted contract."""
    run_id = build_monitoring_run_id(
        result,
        context,
    )
    monitoring_timestamp = context.monitoring_timestamp.astimezone(UTC)
    rows: list[dict[str, object]] = []

    for check in result.checks:
        rows.append(
            {
                RUN_ID_COLUMN: run_id,
                MONITORING_TIMESTAMP_COLUMN: monitoring_timestamp,
                POLICY_VERSION_COLUMN: result.policy_version,
                POLICY_FINGERPRINT_COLUMN: result.policy_fingerprint,
                OVERALL_SEVERITY_COLUMN: result.overall_severity.value,
                CHECK_NAME_COLUMN: check.check_name,
                CHECK_TYPE_COLUMN: check.check_type.value,
                SEVERITY_COLUMN: check.severity.value,
                FEATURE_NAME_COLUMN: check.feature_name,
                OBSERVED_VALUE_COLUMN: check.observed_value,
                EXPECTED_VALUE_COLUMN: check.expected_value,
                WARNING_THRESHOLD_COLUMN: check.warning_threshold,
                CRITICAL_THRESHOLD_COLUMN: check.critical_threshold,
                REFERENCE_ROW_COUNT_COLUMN: check.reference_row_count,
                CURRENT_ROW_COUNT_COLUMN: check.current_row_count,
                DETAILS_COLUMN: check.details,
            }
        )

    frame = pd.DataFrame.from_records(
        rows,
        columns=list(MONITORING_CHECK_COLUMNS),
    )

    if len(frame) != len(result.checks):
        raise MonitoringArtifactError("Monitoring frame does not match the source check count.")

    if bool(frame[CHECK_NAME_COLUMN].duplicated().any()):
        raise MonitoringArtifactError("Monitoring check names must be unique within a run.")

    return frame


def build_monitoring_artifact_metadata(
    result: MonitoringRunResult,
    context: MonitoringArtifactContext,
) -> MonitoringArtifactMetadata:
    """Build persisted metadata from one validated monitoring result."""
    severity_counts = {
        severity: sum(check.severity is severity for check in result.checks)
        for severity in MonitoringSeverity
    }

    return MonitoringArtifactMetadata(
        artifact_version=MONITORING_ARTIFACT_VERSION,
        run_id=build_monitoring_run_id(
            result,
            context,
        ),
        monitoring_timestamp=context.monitoring_timestamp.astimezone(UTC).isoformat(),
        policy_version=result.policy_version,
        policy_fingerprint=result.policy_fingerprint,
        overall_severity=result.overall_severity.value,
        model_name=result.model_name,
        threshold=result.threshold,
        modeling_data_path=context.modeling_data_path,
        modeling_data_sha256=context.modeling_data_sha256,
        model_artifact_path=context.model_artifact_path,
        model_artifact_sha256=context.model_artifact_sha256,
        model_metadata_path=context.model_metadata_path,
        model_metadata_sha256=context.model_metadata_sha256,
        scoring_artifact_path=context.scoring_artifact_path,
        scoring_artifact_sha256=context.scoring_artifact_sha256,
        scoring_metadata_path=context.scoring_metadata_path,
        scoring_metadata_sha256=context.scoring_metadata_sha256,
        reference_row_count=result.reference_row_count,
        current_row_count=result.current_row_count,
        check_count=len(result.checks),
        pass_count=severity_counts[MonitoringSeverity.PASS],
        warning_count=severity_counts[MonitoringSeverity.WARNING],
        critical_count=severity_counts[MonitoringSeverity.CRITICAL],
        output_columns=MONITORING_CHECK_COLUMNS,
    )


def _metadata_payload(
    metadata: MonitoringArtifactMetadata,
) -> dict[str, object]:
    """Return a canonical JSON-compatible metadata representation."""
    serialized = json.loads(
        json.dumps(
            asdict(metadata),
            sort_keys=True,
        )
    )

    if not isinstance(serialized, dict):
        raise MonitoringArtifactError("Monitoring metadata must serialize to an object.")

    return cast(dict[str, object], serialized)


def _temporary_path(output_path: Path) -> Path:
    """Return a temporary path beside the requested final output."""
    return output_path.parent / f".{output_path.name}.tmp"


def _write_pending_checks(
    frame: pd.DataFrame,
    temporary_path: Path,
) -> None:
    """Write a pending monitoring Parquet artifact."""
    temporary_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if temporary_path.exists():
        temporary_path.unlink()

    frame.to_parquet(
        temporary_path,
        index=False,
    )


def _write_pending_metadata(
    metadata: MonitoringArtifactMetadata,
    temporary_path: Path,
) -> None:
    """Write pending monitoring JSON metadata."""
    temporary_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if temporary_path.exists():
        temporary_path.unlink()

    temporary_path.write_text(
        json.dumps(
            _metadata_payload(metadata),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def verify_monitoring_artifact(
    check_path: Path,
    metadata_path: Path,
    *,
    expected_result: MonitoringRunResult,
    expected_context: MonitoringArtifactContext,
) -> None:
    """Verify persisted monitoring checks and metadata."""
    if not check_path.is_file():
        raise FileNotFoundError(f"Monitoring check artifact does not exist: {check_path}")

    if not metadata_path.is_file():
        raise FileNotFoundError(f"Monitoring metadata artifact does not exist: {metadata_path}")

    restored = pd.read_parquet(check_path)

    if tuple(str(column) for column in restored.columns) != (MONITORING_CHECK_COLUMNS):
        raise MonitoringArtifactError(
            "Persisted monitoring columns do not match the output contract."
        )

    expected_frame = build_monitoring_check_frame(
        expected_result,
        expected_context,
    )
    expected_metadata = build_monitoring_artifact_metadata(
        expected_result,
        expected_context,
    )

    if len(restored) != expected_metadata.check_count:
        raise MonitoringArtifactError("Persisted monitoring check count is inconsistent.")

    if bool(restored[CHECK_NAME_COLUMN].duplicated().any()):
        raise MonitoringArtifactError("Persisted monitoring checks contain duplicate names.")

    allowed_check_types = {check_type.value for check_type in MonitoringCheckType}
    persisted_check_types = set(restored[CHECK_TYPE_COLUMN].astype(str).tolist())

    if not persisted_check_types.issubset(allowed_check_types):
        raise MonitoringArtifactError(
            "Persisted monitoring check types contain unsupported values."
        )

    allowed_severities = {severity.value for severity in MonitoringSeverity}
    persisted_severities = set(restored[SEVERITY_COLUMN].astype(str).tolist())

    if not persisted_severities.issubset(allowed_severities):
        raise MonitoringArtifactError("Persisted monitoring severities contain unsupported values.")

    observed_values = restored[OBSERVED_VALUE_COLUMN].to_numpy(dtype=np.float64)

    if not bool(np.isfinite(observed_values).all()):
        raise MonitoringArtifactError(
            "Persisted monitoring observations contain non-finite values."
        )

    restored_timestamp = pd.to_datetime(
        restored[MONITORING_TIMESTAMP_COLUMN],
        errors="raise",
        utc=True,
    )
    expected_timestamp = pd.Timestamp(expected_context.monitoring_timestamp).tz_convert("UTC")

    if bool((restored_timestamp != expected_timestamp).any()):
        raise MonitoringArtifactError("Persisted monitoring timestamps are inconsistent.")

    restored_sorted = restored.sort_values(
        CHECK_NAME_COLUMN,
        kind="stable",
    ).reset_index(drop=True)
    expected_sorted = expected_frame.sort_values(
        CHECK_NAME_COLUMN,
        kind="stable",
    ).reset_index(drop=True)

    try:
        pd.testing.assert_frame_equal(
            restored_sorted,
            expected_sorted,
            check_dtype=False,
            check_exact=True,
        )
    except AssertionError as error:
        raise MonitoringArtifactError(
            "Persisted monitoring checks do not match the source result."
        ) from error

    raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    if not isinstance(raw_metadata, dict):
        raise MonitoringArtifactError("Persisted monitoring metadata must contain a JSON object.")

    if raw_metadata != _metadata_payload(expected_metadata):
        raise MonitoringArtifactError(
            "Persisted monitoring metadata does not match the source result."
        )


def write_monitoring_artifact(
    result: MonitoringRunResult,
    context: MonitoringArtifactContext,
    *,
    check_path: Path = DEFAULT_MONITORING_CHECK_PATH,
    metadata_path: Path = DEFAULT_MONITORING_METADATA_PATH,
) -> tuple[Path, Path]:
    """Persist and verify monitoring checks plus run metadata."""
    if check_path.resolve() == metadata_path.resolve():
        raise MonitoringArtifactError("Monitoring check and metadata paths must differ.")

    frame = build_monitoring_check_frame(
        result,
        context,
    )
    metadata = build_monitoring_artifact_metadata(
        result,
        context,
    )

    temporary_check_path = _temporary_path(check_path)
    temporary_metadata_path = _temporary_path(metadata_path)

    try:
        _write_pending_checks(
            frame,
            temporary_check_path,
        )
        _write_pending_metadata(
            metadata,
            temporary_metadata_path,
        )
        verify_monitoring_artifact(
            temporary_check_path,
            temporary_metadata_path,
            expected_result=result,
            expected_context=context,
        )

        check_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        metadata_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        os.replace(
            temporary_check_path,
            check_path,
        )
        os.replace(
            temporary_metadata_path,
            metadata_path,
        )
    finally:
        if temporary_check_path.exists():
            temporary_check_path.unlink()

        if temporary_metadata_path.exists():
            temporary_metadata_path.unlink()

    return check_path, metadata_path
