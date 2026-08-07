"""Command-line entry point for governed local Stage 7 monitoring."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from vitality_engagement.models.load_data import DEFAULT_MODELING_DATA_PATH
from vitality_engagement.models.persistence import (
    DEFAULT_METADATA_PATH as DEFAULT_MODEL_METADATA_PATH,
)
from vitality_engagement.models.persistence import DEFAULT_MODEL_PATH
from vitality_engagement.models.scoring_artifact import (
    DEFAULT_PREDICTION_PATH,
    DEFAULT_SCORING_METADATA_PATH,
)
from vitality_engagement.monitoring.artifact import (
    DEFAULT_MONITORING_CHECK_PATH,
    DEFAULT_MONITORING_METADATA_PATH,
    build_monitoring_run_id,
)
from vitality_engagement.monitoring.orchestrator import (
    orchestrate_local_monitoring,
)
from vitality_engagement.monitoring.schema import MonitoringSeverity


def _aware_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp and require an explicit UTC offset."""
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "monitoring timestamp must be a valid ISO-8601 timestamp"
        ) from error

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise argparse.ArgumentTypeError("monitoring timestamp must include a timezone offset")

    return timestamp.astimezone(UTC)


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the local-only monitoring command parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify governed modelling, model, and scoring artifacts; "
            "evaluate deterministic monitoring checks; and write local "
            "monitoring artifacts."
        )
    )
    parser.add_argument(
        "--monitoring-timestamp",
        type=_aware_timestamp,
        required=True,
        help="Timezone-aware ISO-8601 timestamp for the monitoring run.",
    )
    parser.add_argument(
        "--modeling-data-path",
        type=Path,
        default=DEFAULT_MODELING_DATA_PATH,
        help="Validated chronological modelling-data Parquet artifact.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Trusted persisted Python model artifact.",
    )
    parser.add_argument(
        "--model-metadata-path",
        type=Path,
        default=DEFAULT_MODEL_METADATA_PATH,
        help="Metadata JSON for the trusted persisted model.",
    )
    parser.add_argument(
        "--scoring-prediction-path",
        type=Path,
        default=DEFAULT_PREDICTION_PATH,
        help="Verified scoring prediction Parquet artifact.",
    )
    parser.add_argument(
        "--scoring-metadata-path",
        type=Path,
        default=DEFAULT_SCORING_METADATA_PATH,
        help="Metadata JSON for the scoring prediction artifact.",
    )
    parser.add_argument(
        "--monitoring-check-path",
        type=Path,
        default=DEFAULT_MONITORING_CHECK_PATH,
        help="Local Parquet path for monitoring checks.",
    )
    parser.add_argument(
        "--monitoring-metadata-path",
        type=Path,
        default=DEFAULT_MONITORING_METADATA_PATH,
        help="Local JSON path for monitoring run metadata.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run verified local monitoring orchestration."""
    arguments = build_argument_parser().parse_args(argv)

    result = orchestrate_local_monitoring(
        monitoring_timestamp=arguments.monitoring_timestamp,
        modeling_data_path=arguments.modeling_data_path,
        model_path=arguments.model_path,
        model_metadata_path=arguments.model_metadata_path,
        scoring_prediction_path=arguments.scoring_prediction_path,
        scoring_metadata_path=arguments.scoring_metadata_path,
        monitoring_check_path=arguments.monitoring_check_path,
        monitoring_metadata_path=arguments.monitoring_metadata_path,
    )

    monitoring_result = result.monitoring_result
    checks = monitoring_result.checks
    run_id = build_monitoring_run_id(
        monitoring_result,
        result.artifact_context,
    )

    print(f"Run ID: {run_id}")
    print(f"Monitoring checks: {result.check_path}")
    print(f"Monitoring metadata: {result.metadata_path}")
    print(f"Overall severity: {monitoring_result.overall_severity.value}")
    print(f"Checks evaluated: {len(checks)}")
    print(f"Passing checks: {sum(check.severity is MonitoringSeverity.PASS for check in checks)}")
    print(
        f"Warning checks: {sum(check.severity is MonitoringSeverity.WARNING for check in checks)}"
    )
    print(
        f"Critical checks: {sum(check.severity is MonitoringSeverity.CRITICAL for check in checks)}"
    )
    print("Mode: local artifacts only; no external alerts or operational actions")

    if monitoring_result.overall_severity is MonitoringSeverity.CRITICAL:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
