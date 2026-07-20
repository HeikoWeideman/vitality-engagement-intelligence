"""Tests for verified member contact-context artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from vitality_engagement.activation.context_artifact import (
    CONTACT_CONTEXT_ARTIFACT_VERSION,
    CONTACT_CONTEXT_COLUMNS,
    ContactContextArtifactError,
    load_verified_contact_context_artifact,
)

SNAPSHOT_TIMESTAMP = datetime(
    2025,
    6,
    30,
    7,
    30,
    tzinfo=UTC,
)
DECISION_TIMESTAMP = datetime(
    2025,
    6,
    30,
    8,
    0,
    tzinfo=UTC,
)


def _valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "member_id": "member-b",
                "contact_allowed": False,
                "opted_out": True,
                "active_case_open": False,
                "last_contacted_at": None,
                "interventions_last_28d": 0,
                "context_as_of": SNAPSHOT_TIMESTAMP,
            },
            {
                "member_id": "member-a",
                "contact_allowed": True,
                "opted_out": False,
                "active_case_open": False,
                "last_contacted_at": datetime(
                    2025,
                    6,
                    25,
                    8,
                    0,
                    tzinfo=UTC,
                ),
                "interventions_last_28d": 1,
                "context_as_of": SNAPSHOT_TIMESTAMP,
            },
        ],
        columns=list(CONTACT_CONTEXT_COLUMNS),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_artifact(
    tmp_path: Path,
    *,
    frame: pd.DataFrame | None = None,
    snapshot_timestamp: datetime = SNAPSHOT_TIMESTAMP,
) -> tuple[Path, Path]:
    context_path = tmp_path / "member_contact_context.parquet"
    metadata_path = tmp_path / "member_contact_context.metadata.json"

    active_frame = _valid_frame() if frame is None else frame
    active_frame.to_parquet(
        context_path,
        index=False,
    )

    metadata = {
        "artifact_version": CONTACT_CONTEXT_ARTIFACT_VERSION,
        "source_name": "approved_contact_governance_view",
        "source_snapshot_reference": ("snapshot-2025-06-30T07:30:00Z"),
        "source_query_sha256": "a" * 64,
        "context_artifact_sha256": _sha256(context_path),
        "snapshot_timestamp": (snapshot_timestamp.isoformat()),
        "row_count": len(active_frame),
        "member_count": int(active_frame["member_id"].nunique()),
        "output_columns": list(CONTACT_CONTEXT_COLUMNS),
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return context_path, metadata_path


def test_valid_artifact_loads_deterministic_contexts(
    tmp_path: Path,
) -> None:
    context_path, metadata_path = _write_artifact(tmp_path)

    artifact = load_verified_contact_context_artifact(
        context_path,
        metadata_path,
        decision_timestamp=DECISION_TIMESTAMP,
    )

    assert artifact.metadata.row_count == 2
    assert artifact.metadata.member_count == 2
    assert [context.member_id for context in artifact.contexts] == [
        "member-a",
        "member-b",
    ]
    assert artifact.contexts[0].interventions_last_28d == 1
    assert artifact.contexts[1].opted_out is True


def test_digest_tampering_is_rejected(
    tmp_path: Path,
) -> None:
    context_path, metadata_path = _write_artifact(tmp_path)

    frame = pd.read_parquet(context_path)
    frame.loc[0, "interventions_last_28d"] = 2
    frame.to_parquet(
        context_path,
        index=False,
    )

    with pytest.raises(
        ContactContextArtifactError,
        match="digest does not match",
    ):
        load_verified_contact_context_artifact(
            context_path,
            metadata_path,
        )


def test_duplicate_member_ids_are_rejected(
    tmp_path: Path,
) -> None:
    frame = _valid_frame()
    frame.loc[1, "member_id"] = frame.loc[
        0,
        "member_id",
    ]
    context_path, metadata_path = _write_artifact(
        tmp_path,
        frame=frame,
    )

    with pytest.raises(
        ContactContextArtifactError,
        match="duplicate member IDs",
    ):
        load_verified_contact_context_artifact(
            context_path,
            metadata_path,
        )


def test_opted_out_contact_allowed_conflict_is_rejected(
    tmp_path: Path,
) -> None:
    frame = _valid_frame()
    frame.loc[0, "contact_allowed"] = True
    context_path, metadata_path = _write_artifact(
        tmp_path,
        frame=frame,
    )

    with pytest.raises(
        ContactContextArtifactError,
        match="cannot also be contact-allowed",
    ):
        load_verified_contact_context_artifact(
            context_path,
            metadata_path,
        )


def test_future_snapshot_is_rejected(
    tmp_path: Path,
) -> None:
    future_snapshot = datetime(
        2025,
        6,
        30,
        9,
        0,
        tzinfo=UTC,
    )
    frame = _valid_frame()
    frame["context_as_of"] = future_snapshot

    context_path, metadata_path = _write_artifact(
        tmp_path,
        frame=frame,
        snapshot_timestamp=future_snapshot,
    )

    with pytest.raises(
        ContactContextArtifactError,
        match="must not be from the future",
    ):
        load_verified_contact_context_artifact(
            context_path,
            metadata_path,
            decision_timestamp=DECISION_TIMESTAMP,
        )


def test_last_contact_must_not_follow_snapshot(
    tmp_path: Path,
) -> None:
    frame = _valid_frame()
    frame.loc[
        1,
        "last_contacted_at",
    ] = datetime(
        2025,
        6,
        30,
        7,
        45,
        tzinfo=UTC,
    )

    context_path, metadata_path = _write_artifact(
        tmp_path,
        frame=frame,
    )

    with pytest.raises(
        ContactContextArtifactError,
        match="must not be later",
    ):
        load_verified_contact_context_artifact(
            context_path,
            metadata_path,
        )


def test_negative_intervention_count_is_rejected(
    tmp_path: Path,
) -> None:
    frame = _valid_frame()
    frame.loc[0, "interventions_last_28d"] = -1

    context_path, metadata_path = _write_artifact(
        tmp_path,
        frame=frame,
    )

    with pytest.raises(
        ContactContextArtifactError,
        match="must not be negative",
    ):
        load_verified_contact_context_artifact(
            context_path,
            metadata_path,
        )


def test_metadata_columns_must_match_contract(
    tmp_path: Path,
) -> None:
    context_path, metadata_path = _write_artifact(tmp_path)

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["output_columns"] = [
        "member_id",
    ]
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
        ContactContextArtifactError,
        match="metadata columns",
    ):
        load_verified_contact_context_artifact(
            context_path,
            metadata_path,
        )
