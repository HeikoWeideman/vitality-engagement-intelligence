"""Tests for local human-review queue artifacts."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest

from vitality_engagement.activation.artifact import write_activation_artifact
from vitality_engagement.activation.engine import (
    ActivationDecisionResult,
    decide_activations,
)
from vitality_engagement.activation.policy import ActivationPolicy
from vitality_engagement.activation.review_queue import (
    PENDING_HUMAN_REVIEW_STATUS,
    REVIEW_QUEUE_COLUMNS,
    ReviewQueueArtifactError,
    build_review_queue_frame,
    verify_review_queue_artifact,
    write_review_queue_artifact,
)
from vitality_engagement.activation.schema import (
    ContactContextLineage,
    MemberActivationContext,
    ScoredPrediction,
)

DECISION_TIMESTAMP = datetime(2025, 6, 30, 8, 0, tzinfo=UTC)
CONTACT_CONTEXT_LINEAGE = ContactContextLineage(
    artifact_path="approved/contact_context.parquet",
    artifact_sha256="b" * 64,
    source_name="approved_contact_context_snapshot",
    source_snapshot_reference="snapshot-2025-06-30T07:30:00Z",
    source_query_sha256="c" * 64,
    snapshot_timestamp=datetime(2025, 6, 30, 7, 30, tzinfo=UTC),
)


def _prediction(
    member_id: str,
    *,
    probability: float,
) -> ScoredPrediction:
    return ScoredPrediction(
        member_id=member_id,
        prediction_date=date(2025, 6, 29),
        risk_probability=probability,
        is_high_risk=probability >= 0.431,
        model_name="python_logistic_baseline",
        threshold=0.431,
    )


def _context(member_id: str) -> MemberActivationContext:
    return MemberActivationContext(
        member_id=member_id,
        contact_allowed=True,
        opted_out=False,
        active_case_open=False,
        last_contacted_at=None,
        interventions_last_28d=0,
    )


def _result(
    *,
    probabilities: tuple[float, ...] = (0.95, 0.85, 0.75),
    capacity: int = 2,
) -> ActivationDecisionResult:
    member_ids = tuple(f"member-{index}" for index in range(1, len(probabilities) + 1))

    return decide_activations(
        predictions=[
            _prediction(member_id, probability=probability)
            for member_id, probability in zip(
                member_ids,
                probabilities,
                strict=True,
            )
        ],
        contexts=[_context(member_id) for member_id in member_ids],
        policy=ActivationPolicy(
            maximum_activations_per_run=capacity,
        ),
        decision_timestamp=DECISION_TIMESTAMP,
        scoring_artifact_path="artifacts/scoring/predictions.parquet",
        scoring_artifact_sha256="a" * 64,
        contact_context_lineage=CONTACT_CONTEXT_LINEAGE,
    )


def _write_source_activation(
    tmp_path: Path,
    result: ActivationDecisionResult,
) -> tuple[Path, Path]:
    decision_path = tmp_path / "activation_decisions.parquet"
    metadata_path = tmp_path / "activation_decisions.metadata.json"

    write_activation_artifact(
        result,
        decision_path=decision_path,
        metadata_path=metadata_path,
    )

    return decision_path, metadata_path


def test_review_queue_contains_only_selected_records_in_rank_order() -> None:
    result = _result()
    frame = build_review_queue_frame(result)

    assert tuple(str(column) for column in frame.columns) == REVIEW_QUEUE_COLUMNS
    assert len(frame) == result.metadata.selected_count
    assert frame["priority_rank"].tolist() == [1, 2]
    assert frame["member_id"].tolist() == ["member-1", "member-2"]
    assert set(frame["review_status"].tolist()) == {PENDING_HUMAN_REVIEW_STATUS}


def test_empty_review_queue_is_valid() -> None:
    result = _result(
        probabilities=(0.20,),
        capacity=1,
    )
    frame = build_review_queue_frame(result)

    assert frame.empty
    assert tuple(str(column) for column in frame.columns) == REVIEW_QUEUE_COLUMNS


def test_write_and_verify_review_queue_artifact(tmp_path: Path) -> None:
    result = _result()
    activation_decision_path, activation_metadata_path = _write_source_activation(tmp_path, result)
    queue_path = tmp_path / "human_review_queue.parquet"
    queue_metadata_path = tmp_path / "human_review_queue.metadata.json"

    written_queue, written_metadata = write_review_queue_artifact(
        result,
        activation_decision_path=activation_decision_path,
        activation_metadata_path=activation_metadata_path,
        review_queue_path=queue_path,
        review_metadata_path=queue_metadata_path,
    )

    assert written_queue == queue_path
    assert written_metadata == queue_metadata_path
    assert queue_path.is_file()
    assert queue_metadata_path.is_file()

    verify_review_queue_artifact(
        queue_path,
        queue_metadata_path,
        expected_result=result,
        activation_decision_path=activation_decision_path,
        activation_metadata_path=activation_metadata_path,
    )

    payload = json.loads(queue_metadata_path.read_text(encoding="utf-8"))

    assert payload["selected_count"] == result.metadata.selected_count
    assert payload["review_status"] == PENDING_HUMAN_REVIEW_STATUS
    assert len(payload["source_activation_decision_sha256"]) == 64
    assert len(payload["source_activation_metadata_sha256"]) == 64


def test_writer_rejects_source_and_output_path_collision(
    tmp_path: Path,
) -> None:
    result = _result()
    activation_decision_path, activation_metadata_path = _write_source_activation(tmp_path, result)

    with pytest.raises(
        ReviewQueueArtifactError,
        match="must use distinct paths",
    ):
        write_review_queue_artifact(
            result,
            activation_decision_path=activation_decision_path,
            activation_metadata_path=activation_metadata_path,
            review_queue_path=activation_decision_path,
            review_metadata_path=tmp_path / "review.metadata.json",
        )


def test_verifier_detects_queue_tampering(tmp_path: Path) -> None:
    result = _result()
    activation_decision_path, activation_metadata_path = _write_source_activation(tmp_path, result)
    queue_path = tmp_path / "human_review_queue.parquet"
    queue_metadata_path = tmp_path / "human_review_queue.metadata.json"

    write_review_queue_artifact(
        result,
        activation_decision_path=activation_decision_path,
        activation_metadata_path=activation_metadata_path,
        review_queue_path=queue_path,
        review_metadata_path=queue_metadata_path,
    )

    restored = pd.read_parquet(queue_path)
    restored.at[0, "review_status"] = "approved_for_contact"
    restored.to_parquet(queue_path, index=False)

    with pytest.raises(
        ReviewQueueArtifactError,
        match="does not match selected activation records",
    ):
        verify_review_queue_artifact(
            queue_path,
            queue_metadata_path,
            expected_result=result,
            activation_decision_path=activation_decision_path,
            activation_metadata_path=activation_metadata_path,
        )
