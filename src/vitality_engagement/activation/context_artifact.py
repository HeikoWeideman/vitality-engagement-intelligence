"""Load and verify governed member contact-context artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

import pandas as pd
from pandas.api.types import is_bool_dtype, is_integer_dtype

from vitality_engagement.activation.schema import (
    MemberActivationContext,
)

CONTACT_CONTEXT_ARTIFACT_VERSION: Final = 1

MEMBER_ID_COLUMN: Final = "member_id"
CONTACT_ALLOWED_COLUMN: Final = "contact_allowed"
OPTED_OUT_COLUMN: Final = "opted_out"
ACTIVE_CASE_OPEN_COLUMN: Final = "active_case_open"
LAST_CONTACTED_AT_COLUMN: Final = "last_contacted_at"
INTERVENTIONS_LAST_28D_COLUMN: Final = "interventions_last_28d"
CONTEXT_AS_OF_COLUMN: Final = "context_as_of"

CONTACT_CONTEXT_COLUMNS: Final = (
    MEMBER_ID_COLUMN,
    CONTACT_ALLOWED_COLUMN,
    OPTED_OUT_COLUMN,
    ACTIVE_CASE_OPEN_COLUMN,
    LAST_CONTACTED_AT_COLUMN,
    INTERVENTIONS_LAST_28D_COLUMN,
    CONTEXT_AS_OF_COLUMN,
)

_BOOLEAN_COLUMNS: Final = (
    CONTACT_ALLOWED_COLUMN,
    OPTED_OUT_COLUMN,
    ACTIVE_CASE_OPEN_COLUMN,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ContactContextArtifactError(RuntimeError):
    """Raised when a contact-context artifact violates governance."""


@dataclass(frozen=True)
class ContactContextArtifactMetadata:
    """Lineage metadata for one immutable contact-context snapshot."""

    artifact_version: int
    source_name: str
    source_snapshot_reference: str
    source_query_sha256: str
    context_artifact_sha256: str
    snapshot_timestamp: str
    row_count: int
    member_count: int
    output_columns: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate required lineage and artifact metadata."""
        if self.artifact_version != CONTACT_CONTEXT_ARTIFACT_VERSION:
            raise ContactContextArtifactError("Unsupported contact-context artifact version.")

        value: object

        for field_name, value in (
            ("source_name", self.source_name),
            (
                "source_snapshot_reference",
                self.source_snapshot_reference,
            ),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ContactContextArtifactError(f"{field_name} must be a non-empty string.")

        for field_name, value in (
            ("source_query_sha256", self.source_query_sha256),
            (
                "context_artifact_sha256",
                self.context_artifact_sha256,
            ),
        ):
            if not _SHA256_PATTERN.fullmatch(value):
                raise ContactContextArtifactError(
                    f"{field_name} must contain a lowercase SHA-256 digest."
                )

        _parse_aware_timestamp(
            self.snapshot_timestamp,
            "snapshot_timestamp",
        )

        for field_name, value in (
            ("row_count", self.row_count),
            ("member_count", self.member_count),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ContactContextArtifactError(f"{field_name} must be a non-negative integer.")

        if self.member_count > self.row_count:
            raise ContactContextArtifactError("member_count must not exceed row_count.")

        if self.output_columns != CONTACT_CONTEXT_COLUMNS:
            raise ContactContextArtifactError(
                "Contact-context metadata columns do not match the governed contract."
            )


@dataclass(frozen=True)
class VerifiedContactContextArtifact:
    """Verified contexts and immutable source metadata."""

    metadata: ContactContextArtifactMetadata
    contexts: tuple[MemberActivationContext, ...]


def _parse_aware_timestamp(
    value: str,
    field_name: str,
) -> datetime:
    """Parse an ISO timestamp and require timezone awareness."""
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise ContactContextArtifactError(f"{field_name} must be a valid ISO timestamp.") from error

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ContactContextArtifactError(f"{field_name} must be timezone-aware.")

    return timestamp.astimezone(UTC)


def _coerce_aware_datetime(
    value: object,
    field_name: str,
) -> datetime:
    """Require a timezone-aware datetime value from Parquet."""
    timestamp: datetime

    if isinstance(value, pd.Timestamp):
        timestamp = value.to_pydatetime()
    elif isinstance(value, datetime):
        timestamp = value
    else:
        raise ContactContextArtifactError(f"{field_name} must contain datetime values.")

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ContactContextArtifactError(f"{field_name} must contain timezone-aware values.")

    return timestamp.astimezone(UTC)


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for block in iter(
            lambda: file_handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def _load_metadata(
    metadata_path: Path,
) -> ContactContextArtifactMetadata:
    """Load and strictly validate contact-context metadata JSON."""
    if not metadata_path.is_file():
        raise FileNotFoundError(
            f"Contact-context metadata artifact does not exist: {metadata_path}"
        )

    raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    if not isinstance(raw_metadata, dict):
        raise ContactContextArtifactError("Contact-context metadata must contain a JSON object.")

    expected_keys = {field.name for field in fields(ContactContextArtifactMetadata)}

    if set(raw_metadata) != expected_keys:
        raise ContactContextArtifactError(
            "Contact-context metadata fields do not match the governed contract."
        )

    raw_columns = raw_metadata["output_columns"]

    if not isinstance(raw_columns, list) or not all(
        isinstance(column, str) for column in raw_columns
    ):
        raise ContactContextArtifactError("output_columns must contain a JSON string array.")

    return ContactContextArtifactMetadata(
        artifact_version=raw_metadata["artifact_version"],
        source_name=raw_metadata["source_name"],
        source_snapshot_reference=(raw_metadata["source_snapshot_reference"]),
        source_query_sha256=raw_metadata["source_query_sha256"],
        context_artifact_sha256=(raw_metadata["context_artifact_sha256"]),
        snapshot_timestamp=raw_metadata["snapshot_timestamp"],
        row_count=raw_metadata["row_count"],
        member_count=raw_metadata["member_count"],
        output_columns=tuple(raw_columns),
    )


def load_verified_contact_context_artifact(
    context_path: Path,
    metadata_path: Path,
    *,
    decision_timestamp: datetime | None = None,
) -> VerifiedContactContextArtifact:
    """Verify and load one immutable contact-context snapshot."""
    if not context_path.is_file():
        raise FileNotFoundError(f"Contact-context Parquet artifact does not exist: {context_path}")

    metadata = _load_metadata(metadata_path)

    if _sha256_file(context_path) != metadata.context_artifact_sha256:
        raise ContactContextArtifactError("Contact-context Parquet digest does not match metadata.")

    frame = pd.read_parquet(context_path)

    actual_columns = tuple(str(column) for column in frame.columns)

    if actual_columns != CONTACT_CONTEXT_COLUMNS:
        raise ContactContextArtifactError(
            "Contact-context columns do not match the governed contract."
        )

    if len(frame) != metadata.row_count:
        raise ContactContextArtifactError("Contact-context row count does not match metadata.")

    if bool(frame[MEMBER_ID_COLUMN].isna().any()):
        raise ContactContextArtifactError("Contact-context member IDs contain null values.")

    member_ids = frame[MEMBER_ID_COLUMN].astype(str)

    if bool(member_ids.str.strip().eq("").any()):
        raise ContactContextArtifactError("Contact-context member IDs contain empty values.")

    if bool(frame.duplicated(subset=[MEMBER_ID_COLUMN]).any()):
        raise ContactContextArtifactError("Contact-context artifact contains duplicate member IDs.")

    if int(member_ids.nunique()) != metadata.member_count:
        raise ContactContextArtifactError("Contact-context member count does not match metadata.")

    for column in _BOOLEAN_COLUMNS:
        if bool(frame[column].isna().any()):
            raise ContactContextArtifactError(f"{column} contains null values.")

        if not is_bool_dtype(frame[column].dtype):
            raise ContactContextArtifactError(f"{column} must contain Boolean values.")

    intervention_counts = frame[INTERVENTIONS_LAST_28D_COLUMN]

    if bool(intervention_counts.isna().any()):
        raise ContactContextArtifactError("interventions_last_28d contains null values.")

    if not is_integer_dtype(intervention_counts.dtype):
        raise ContactContextArtifactError("interventions_last_28d must contain integers.")

    if bool((intervention_counts < 0).any()):
        raise ContactContextArtifactError("interventions_last_28d must not be negative.")

    if bool((frame[CONTACT_ALLOWED_COLUMN] & frame[OPTED_OUT_COLUMN]).any()):
        raise ContactContextArtifactError("An opted-out member cannot also be contact-allowed.")

    snapshot_timestamp = _parse_aware_timestamp(
        metadata.snapshot_timestamp,
        "snapshot_timestamp",
    )

    context_as_of_values = tuple(
        _coerce_aware_datetime(
            value,
            CONTEXT_AS_OF_COLUMN,
        )
        for value in frame[CONTEXT_AS_OF_COLUMN].tolist()
    )

    if any(value != snapshot_timestamp for value in context_as_of_values):
        raise ContactContextArtifactError(
            "context_as_of values do not match the metadata snapshot timestamp."
        )

    if decision_timestamp is not None:
        if decision_timestamp.tzinfo is None or decision_timestamp.utcoffset() is None:
            raise ContactContextArtifactError("decision_timestamp must be timezone-aware.")

        if snapshot_timestamp > decision_timestamp.astimezone(UTC):
            raise ContactContextArtifactError("Contact context must not be from the future.")

    contexts: list[MemberActivationContext] = []

    ordered_frame = frame.sort_values(
        MEMBER_ID_COLUMN,
        kind="stable",
    )

    for row in ordered_frame.to_dict(orient="records"):
        raw_last_contacted = row[LAST_CONTACTED_AT_COLUMN]

        last_contacted_at = (
            None
            if pd.isna(raw_last_contacted)
            else _coerce_aware_datetime(
                raw_last_contacted,
                LAST_CONTACTED_AT_COLUMN,
            )
        )

        if last_contacted_at is not None and last_contacted_at > snapshot_timestamp:
            raise ContactContextArtifactError(
                "last_contacted_at must not be later than context_as_of."
            )

        contexts.append(
            MemberActivationContext(
                member_id=str(row[MEMBER_ID_COLUMN]),
                contact_allowed=cast(
                    bool,
                    row[CONTACT_ALLOWED_COLUMN],
                ),
                opted_out=cast(
                    bool,
                    row[OPTED_OUT_COLUMN],
                ),
                active_case_open=cast(
                    bool,
                    row[ACTIVE_CASE_OPEN_COLUMN],
                ),
                last_contacted_at=last_contacted_at,
                interventions_last_28d=int(row[INTERVENTIONS_LAST_28D_COLUMN]),
            )
        )

    return VerifiedContactContextArtifact(
        metadata=metadata,
        contexts=tuple(contexts),
    )
