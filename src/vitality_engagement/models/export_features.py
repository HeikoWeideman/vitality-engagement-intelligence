"""Export the leakage-safe BigQuery modelling table to local Parquet."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, cast

import pandas as pd
from google.cloud import bigquery

from vitality_engagement.models.schema import (
    EXPECTED_MEMBER_COUNT,
    EXPECTED_SPLIT_ROW_COUNTS,
    EXPECTED_TOTAL_ROW_COUNT,
    EXPORT_COLUMNS,
    IDENTIFIER_COLUMNS,
    MODEL_FEATURE_COLUMNS,
    SOURCE_TARGET_COLUMN,
    SPLIT_COLUMN,
    TARGET_COLUMN,
)

DEFAULT_PROJECT_ID: Final = "vitality-engagement-43999"
DEFAULT_DATASET_ID: Final = "vitality_engagement_dev"
DEFAULT_TABLE_ID: Final = "engagement_modeling_split"
DEFAULT_LOCATION: Final = "asia-southeast1"
DEFAULT_OUTPUT_PATH: Final = Path("data/modeling/engagement_modeling_split.parquet")

LABELLED_SPLITS: Final = frozenset({"train", "validation", "test"})
SCORING_SPLIT: Final = "scoring"


class _ArrowTableLike(Protocol):
    """Minimal interface required from a BigQuery Arrow result."""

    def to_pandas(self) -> pd.DataFrame:
        """Convert the Arrow table to a pandas DataFrame."""


class ModelExportValidationError(ValueError):
    """Raised when exported modelling data violates its expected contract."""


@dataclass(frozen=True)
class ExportConfig:
    """Configuration for a BigQuery modelling-data export."""

    project_id: str = DEFAULT_PROJECT_ID
    dataset_id: str = DEFAULT_DATASET_ID
    table_id: str = DEFAULT_TABLE_ID
    location: str = DEFAULT_LOCATION
    output_path: Path = DEFAULT_OUTPUT_PATH

    @property
    def fully_qualified_table(self) -> str:
        """Return the fully qualified BigQuery source table name."""
        return f"{self.project_id}.{self.dataset_id}.{self.table_id}"


def build_export_query(config: ExportConfig) -> str:
    """Build the deterministic, leakage-safe feature export query."""
    select_expressions = [
        (f"{SOURCE_TARGET_COLUMN} AS {TARGET_COLUMN}" if column == TARGET_COLUMN else column)
        for column in EXPORT_COLUMNS
    ]
    select_clause = ",\n    ".join(select_expressions)

    return (
        "SELECT\n"
        f"    {select_clause}\n"
        f"FROM `{config.fully_qualified_table}`\n"
        "ORDER BY prediction_date, member_id"
    )


def validate_export_frame(
    frame: pd.DataFrame,
    *,
    expected_split_row_counts: Mapping[str, int] = EXPECTED_SPLIT_ROW_COUNTS,
    expected_member_count: int = EXPECTED_MEMBER_COUNT,
) -> None:
    """Validate an exported modelling frame before it is persisted."""
    expected_columns = list(EXPORT_COLUMNS)
    actual_columns = [str(column) for column in frame.columns]

    if actual_columns != expected_columns:
        raise ModelExportValidationError(
            "Export columns do not match the approved modelling schema."
        )

    expected_total = sum(expected_split_row_counts.values())
    if len(frame) != expected_total:
        raise ModelExportValidationError(f"Expected {expected_total} rows, found {len(frame)}.")

    actual_split_counts = {
        str(split_name): int(row_count)
        for split_name, row_count in frame[SPLIT_COLUMN].value_counts(dropna=False).items()
    }
    if actual_split_counts != dict(expected_split_row_counts):
        raise ModelExportValidationError("Chronological split row counts do not match Stage 3.")

    member_count = int(frame["member_id"].nunique(dropna=True))
    if member_count != expected_member_count:
        raise ModelExportValidationError(
            f"Expected {expected_member_count} members, found {member_count}."
        )

    if bool(frame.loc[:, list(IDENTIFIER_COLUMNS)].isna().any().any()):
        raise ModelExportValidationError("Identifier columns contain null values.")

    if bool(frame.duplicated(subset=list(IDENTIFIER_COLUMNS)).any()):
        raise ModelExportValidationError("Duplicate member and prediction-date keys detected.")

    identifier_frame = frame.loc[:, list(IDENTIFIER_COLUMNS)].reset_index(drop=True)
    sorted_identifier_frame = identifier_frame.sort_values(
        ["prediction_date", "member_id"],
        kind="stable",
    ).reset_index(drop=True)

    if not identifier_frame.equals(sorted_identifier_frame):
        raise ModelExportValidationError(
            "Export rows are not ordered by prediction date and member."
        )

    labelled_mask = frame[SPLIT_COLUMN].isin(LABELLED_SPLITS)
    scoring_mask = frame[SPLIT_COLUMN].eq(SCORING_SPLIT)

    if bool(frame.loc[labelled_mask, TARGET_COLUMN].isna().any()):
        raise ModelExportValidationError("Train, validation, or test contains null target values.")

    if bool(frame.loc[scoring_mask, TARGET_COLUMN].notna().any()):
        raise ModelExportValidationError("Scoring rows unexpectedly contain target values.")

    labelled_targets = frame.loc[labelled_mask, TARGET_COLUMN]
    if not bool(labelled_targets.isin([True, False]).all()):
        raise ModelExportValidationError("Labelled target values must be Boolean.")

    feature_frame = frame.loc[:, list(MODEL_FEATURE_COLUMNS)]
    if bool(feature_frame.isna().all(axis=0).any()):
        raise ModelExportValidationError("At least one model feature is entirely null.")


def fetch_export_frame(
    client: bigquery.Client,
    config: ExportConfig,
) -> pd.DataFrame:
    """Query BigQuery and return the modelling export as a DataFrame."""
    query_job = client.query(
        build_export_query(config),
        location=config.location,
        job_config=bigquery.QueryJobConfig(use_legacy_sql=False),
    )
    rows = query_job.result()
    arrow_result = rows.to_arrow(create_bqstorage_client=False)

    if arrow_result is None:
        raise RuntimeError("BigQuery returned no Arrow table.")

    arrow_table = cast(_ArrowTableLike, arrow_result)
    return arrow_table.to_pandas()


def write_export_frame(
    frame: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write validated modelling data atomically to Parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")

    if temporary_path.exists():
        temporary_path.unlink()

    frame.to_parquet(temporary_path, index=False)
    temporary_path.replace(output_path)

    restored_frame = pd.read_parquet(
        output_path,
        columns=["member_id"],
    )
    if len(restored_frame) != len(frame):
        raise RuntimeError("Persisted Parquet row count does not match the validated export.")


def export_modeling_features(
    config: ExportConfig,
    *,
    client: bigquery.Client | None = None,
) -> Path:
    """Export, validate, and persist the modelling feature table."""
    active_client = client or bigquery.Client(project=config.project_id)
    frame = fetch_export_frame(active_client, config)
    validate_export_frame(frame)
    write_export_frame(frame, config.output_path)
    return config.output_path


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=("Export Stage 3 modelling features from BigQuery to Parquet.")
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--table-id", default=DEFAULT_TABLE_ID)
    parser.add_argument("--location", default=DEFAULT_LOCATION)
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the modelling feature export."""
    arguments = build_argument_parser().parse_args(argv)
    config = ExportConfig(
        project_id=arguments.project_id,
        dataset_id=arguments.dataset_id,
        table_id=arguments.table_id,
        location=arguments.location,
        output_path=arguments.output_path,
    )

    output_path = export_modeling_features(config)
    print(f"Exported {EXPECTED_TOTAL_ROW_COUNT} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
