"""Schema definitions for synthetic engagement data."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, PositiveInt


class ActivityLevel(StrEnum):
    """Synthetic baseline activity categories."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ResponseProfile(StrEnum):
    """Synthetic behavioural-response categories."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GenerationConfig(BaseModel):
    """Configuration for reproducible synthetic-data generation."""

    member_count: PositiveInt = 500
    day_count: PositiveInt = 180
    random_seed: int = Field(default=42, ge=0)
    start_date: date = date(2025, 1, 1)

    sleep_missing_rate: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
    )
    app_session_missing_rate: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
    )
    step_outlier_rate: float = Field(
        default=0.005,
        ge=0.0,
        le=1.0,
    )
    delayed_record_rate: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
    )
    category_change_rate: float = Field(
        default=0.002,
        ge=0.0,
        le=1.0,
    )
