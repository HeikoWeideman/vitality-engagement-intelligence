"""Persist and verify local human-review queue artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, cast

import pandas as pd

from vitality_engagement.activation.artifact import (
    DECISION_TIMESTAMP_COLUMN,
    INTERVENTION_CATEGORY_COLUMN,
    MEMBER_ID_COLUMN,
    MODEL_NAME_COLUMN,
    POLICY_VERSION_COLUMN,
    PREDICTION_DATE_COLUMN,
    PRIORITY_RANK_COLUMN,
    RISK_PROBABILITY_COLUMN,
    RUN_ID_COLUMN,
    THRESHOLD_COLUMN,
    verify_activation_artifact,
)
from vitality_engagement.activation.engine import ActivationDecisionResult
from vitality_engagement.activation.schema import DecisionOutcome

DEFAULT_REVIEW_QUEUE_PATH: Final = Path("artifacts/activation/human_review_queue.parquet")
DEFAULT_REVIEW_QUEUE_METADATA_PATH: Final = Path(
    "artifacts/activation/human_review_queue.metadata.json"
)
REVIEW_QUEUE_ARTIFACT_VERSION: Final = 1
REVIEW_STATUS_COLUMN: Final = "review_status"
PENDING_HUMAN_REVIEW_STATUS: Final = "pending_human_review"

REVIEW_QUEUE_COLUMNS: Final = (
    RUN_ID_COLUMN,
    POLICY_VERSION_COLUMN,
    MEMBER_ID_COLUMN,
    PREDICTION_DATE_COLUMN,
    DECISION_TIMESTAMP_COLUMN,
    RISK_PROBABILITY_COLUMN,
    MODEL_NAME_COLUMN,
    THRESHOLD_COLUMN,
    INTERVENTION_CATEGORY_COLUMN,
    PRIORITY_RANK_COLUMN,
    REVIEW_STATUS_COLUMN,
)


class ReviewQueueArtifactError(RuntimeError):
    """Raised when a review-queue artifact violates its contract."""


@dataclass(frozen=True)
class ReviewQueueArtifactMetadata:
    """Persisted lineage for one local human-review queue."""

    artifact_version: int
    run_id: str
    policy_version: str
    policy_fingerprint: str
    model_name: str
    threshold: float
    decision_timestamp: str
    source_activation_decision_path: str
    source_activation_decision_sha256: str
    source_activation_metadata_path: str
    source_activation_metadata_sha256: str
    source_row_count: int
    selected_count: int
    review_status: str
    output_columns: tuple[str, ...]


def _sha256(path: Path) -> str:
    """Return the lowercase SHA-256 digest for one file."""
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _temporary_path(output_path: Path) -> Path:
    """Return a temporary path beside a requested final output."""
    return output_path.parent / f".{output_path.name}.tmp"


def _metadata_payload(
    metadata: ReviewQueueArtifactMetadata,
) -> dict[str, object]:
    """Return the JSON-compatible metadata representation."""
    serialized = json.loads(
        json.dumps(
            asdict(metadata),
            sort_keys=True,
        )
    )

    if not isinstance(serialized, dict):
        raise ReviewQueueArtifactError("Review-queue metadata must serialize to an object.")

    return cast(dict[str, object], serialized)


def _validate_distinct_paths(
    *,
    activation_decision_path: Path,
    activation_metadata_path: Path,
    review_queue_path: Path,
    review_metadata_path: Path,
) -> None:
    """Prevent review outputs from overwriting source activation artifacts."""
    named_paths = {
        "activation_decision_path": activation_decision_path,
        "activation_metadata_path": activation_metadata_path,
        "review_queue_path": review_queue_path,
        "review_metadata_path": review_metadata_path,
    }
    resolved: dict[Path, str] = {}

    for field_name, path in named_paths.items():
        normalised = path.resolve()

        if normalised in resolved:
            raise ReviewQueueArtifactError(
                f"{field_name} and {resolved[normalised]} must use distinct paths."
            )

        resolved[normalised] = field_name


def build_review_queue_frame(
    result: ActivationDecisionResult,
) -> pd.DataFrame:
    """Project selected activation audits into deterministic review order."""
    selected_records = sorted(
        (
            record
            for record in result.audit_records
            if record.outcome is DecisionOutcome.SELECTED_FOR_REVIEW
        ),
        key=lambda record: cast(int, record.priority_rank),
    )
    rows: list[dict[str, object]] = []

    for record in selected_records:
        if record.intervention_category is None or record.priority_rank is None:
            raise ReviewQueueArtifactError(
                "Selected activation audits require an intervention and rank."
            )

        rows.append(
            {
                RUN_ID_COLUMN: record.run_id,
                POLICY_VERSION_COLUMN: record.policy_version,
                MEMBER_ID_COLUMN: record.member_id,
                PREDICTION_DATE_COLUMN: record.prediction_date,
                DECISION_TIMESTAMP_COLUMN: record.decision_timestamp,
                RISK_PROBABILITY_COLUMN: record.risk_probability,
                MODEL_NAME_COLUMN: record.model_name,
                THRESHOLD_COLUMN: record.threshold,
                INTERVENTION_CATEGORY_COLUMN: record.intervention_category.value,
                PRIORITY_RANK_COLUMN: record.priority_rank,
                REVIEW_STATUS_COLUMN: PENDING_HUMAN_REVIEW_STATUS,
            }
        )

    frame = pd.DataFrame.from_records(
        rows,
        columns=list(REVIEW_QUEUE_COLUMNS),
    )

    if len(frame) != result.metadata.selected_count:
        raise ReviewQueueArtifactError(
            "Review-queue rows do not match the selected activation count."
        )

    expected_ranks = list(range(1, result.metadata.selected_count + 1))
    actual_ranks = frame[PRIORITY_RANK_COLUMN].tolist()

    if actual_ranks != expected_ranks:
        raise ReviewQueueArtifactError("Review-queue priority ranks must be contiguous.")

    return frame


def build_review_queue_metadata(
    result: ActivationDecisionResult,
    *,
    activation_decision_path: Path,
    activation_metadata_path: Path,
) -> ReviewQueueArtifactMetadata:
    """Build review-queue metadata from verified activation artifacts."""
    if not activation_decision_path.is_file():
        raise FileNotFoundError(
            f"Source activation decision artifact does not exist: {activation_decision_path}"
        )

    if not activation_metadata_path.is_file():
        raise FileNotFoundError(
            f"Source activation metadata artifact does not exist: {activation_metadata_path}"
        )

    metadata = result.metadata

    return ReviewQueueArtifactMetadata(
        artifact_version=REVIEW_QUEUE_ARTIFACT_VERSION,
        run_id=metadata.run_id,
        policy_version=metadata.policy_version,
        policy_fingerprint=metadata.policy_fingerprint,
        model_name=metadata.model_name,
        threshold=metadata.threshold,
        decision_timestamp=metadata.decision_timestamp.isoformat(),
        source_activation_decision_path=str(activation_decision_path),
        source_activation_decision_sha256=_sha256(activation_decision_path),
        source_activation_metadata_path=str(activation_metadata_path),
        source_activation_metadata_sha256=_sha256(activation_metadata_path),
        source_row_count=metadata.source_row_count,
        selected_count=metadata.selected_count,
        review_status=PENDING_HUMAN_REVIEW_STATUS,
        output_columns=REVIEW_QUEUE_COLUMNS,
    )


def _normalise_review_queue_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalise persisted values for exact contract comparison."""
    normalised = frame.copy()
    normalised[PREDICTION_DATE_COLUMN] = [
        pd.Timestamp(value).date() for value in normalised[PREDICTION_DATE_COLUMN].tolist()
    ]
    normalised[DECISION_TIMESTAMP_COLUMN] = pd.to_datetime(
        normalised[DECISION_TIMESTAMP_COLUMN],
        errors="raise",
        utc=True,
    )
    normalised[PRIORITY_RANK_COLUMN] = normalised[PRIORITY_RANK_COLUMN].astype("int64")
    return normalised


def verify_review_queue_artifact(
    review_queue_path: Path,
    review_metadata_path: Path,
    *,
    expected_result: ActivationDecisionResult,
    activation_decision_path: Path,
    activation_metadata_path: Path,
) -> None:
    """Verify a local review queue against governed activation decisions."""
    verify_activation_artifact(
        activation_decision_path,
        activation_metadata_path,
        expected_result=expected_result,
    )

    if not review_queue_path.is_file():
        raise FileNotFoundError(f"Review-queue artifact does not exist: {review_queue_path}")

    if not review_metadata_path.is_file():
        raise FileNotFoundError(f"Review-queue metadata does not exist: {review_metadata_path}")

    restored = pd.read_parquet(review_queue_path)

    if tuple(str(column) for column in restored.columns) != REVIEW_QUEUE_COLUMNS:
        raise ReviewQueueArtifactError("Persisted review-queue columns do not match the contract.")

    expected_frame = build_review_queue_frame(expected_result)

    try:
        pd.testing.assert_frame_equal(
            _normalise_review_queue_frame(restored),
            _normalise_review_queue_frame(expected_frame),
            check_dtype=False,
            check_exact=True,
        )
    except AssertionError as error:
        raise ReviewQueueArtifactError(
            "Persisted review queue does not match selected activation records."
        ) from error

    expected_metadata = build_review_queue_metadata(
        expected_result,
        activation_decision_path=activation_decision_path,
        activation_metadata_path=activation_metadata_path,
    )
    raw_metadata = json.loads(review_metadata_path.read_text(encoding="utf-8"))

    if not isinstance(raw_metadata, dict):
        raise ReviewQueueArtifactError(
            "Persisted review-queue metadata must contain a JSON object."
        )

    if raw_metadata != _metadata_payload(expected_metadata):
        raise ReviewQueueArtifactError(
            "Persisted review-queue metadata does not match the source artifacts."
        )


def write_review_queue_artifact(
    result: ActivationDecisionResult,
    *,
    activation_decision_path: Path,
    activation_metadata_path: Path,
    review_queue_path: Path = DEFAULT_REVIEW_QUEUE_PATH,
    review_metadata_path: Path = DEFAULT_REVIEW_QUEUE_METADATA_PATH,
) -> tuple[Path, Path]:
    """Persist and verify a local queue for authorised human review only."""
    _validate_distinct_paths(
        activation_decision_path=activation_decision_path,
        activation_metadata_path=activation_metadata_path,
        review_queue_path=review_queue_path,
        review_metadata_path=review_metadata_path,
    )
    verify_activation_artifact(
        activation_decision_path,
        activation_metadata_path,
        expected_result=result,
    )

    frame = build_review_queue_frame(result)
    metadata = build_review_queue_metadata(
        result,
        activation_decision_path=activation_decision_path,
        activation_metadata_path=activation_metadata_path,
    )
    temporary_queue_path = _temporary_path(review_queue_path)
    temporary_metadata_path = _temporary_path(review_metadata_path)

    try:
        temporary_queue_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_metadata_path.parent.mkdir(parents=True, exist_ok=True)

        if temporary_queue_path.exists():
            temporary_queue_path.unlink()

        if temporary_metadata_path.exists():
            temporary_metadata_path.unlink()

        frame.to_parquet(
            temporary_queue_path,
            index=False,
        )
        temporary_metadata_path.write_text(
            json.dumps(
                _metadata_payload(metadata),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        verify_review_queue_artifact(
            temporary_queue_path,
            temporary_metadata_path,
            expected_result=result,
            activation_decision_path=activation_decision_path,
            activation_metadata_path=activation_metadata_path,
        )

        review_queue_path.parent.mkdir(parents=True, exist_ok=True)
        review_metadata_path.parent.mkdir(parents=True, exist_ok=True)

        os.replace(temporary_queue_path, review_queue_path)
        os.replace(temporary_metadata_path, review_metadata_path)
    finally:
        if temporary_queue_path.exists():
            temporary_queue_path.unlink()

        if temporary_metadata_path.exists():
            temporary_metadata_path.unlink()

    return review_queue_path, review_metadata_path
