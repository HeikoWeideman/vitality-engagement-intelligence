"""Generate reproducible synthetic member profiles."""

from typing import Final

import numpy as np
import pandas as pd

from vitality_engagement.data.schema import (
    ActivityLevel,
    GenerationConfig,
    ResponseProfile,
)

AGE_BANDS: Final[tuple[str, ...]] = (
    "18-24",
    "25-34",
    "35-44",
    "45-54",
    "55+",
)

AGE_BAND_PROBABILITIES: Final[tuple[float, ...]] = (
    0.18,
    0.30,
    0.28,
    0.16,
    0.08,
)

ACTIVITY_LEVELS: Final[tuple[str, ...]] = tuple(level.value for level in ActivityLevel)

ACTIVITY_LEVEL_PROBABILITIES: Final[tuple[float, ...]] = (
    0.35,
    0.45,
    0.20,
)

RESPONSE_PROFILES: Final[tuple[str, ...]] = tuple(profile.value for profile in ResponseProfile)

REWARD_PROFILE_PROBABILITIES: Final[tuple[float, ...]] = (
    0.30,
    0.50,
    0.20,
)

INTERVENTION_PROFILE_PROBABILITIES: Final[tuple[float, ...]] = (
    0.25,
    0.50,
    0.25,
)


def generate_members(config: GenerationConfig) -> pd.DataFrame:
    """Generate one synthetic profile for each member."""
    rng = np.random.default_rng(config.random_seed)

    member_ids = [f"M{member_number:06d}" for member_number in range(1, config.member_count + 1)]

    membership_months = np.clip(
        rng.geometric(p=0.05, size=config.member_count),
        1,
        120,
    )

    return pd.DataFrame(
        {
            "member_id": member_ids,
            "age_band": rng.choice(
                AGE_BANDS,
                size=config.member_count,
                p=AGE_BAND_PROBABILITIES,
            ),
            "membership_months": membership_months,
            "activity_level": rng.choice(
                ACTIVITY_LEVELS,
                size=config.member_count,
                p=ACTIVITY_LEVEL_PROBABILITIES,
            ),
            "reward_profile": rng.choice(
                RESPONSE_PROFILES,
                size=config.member_count,
                p=REWARD_PROFILE_PROBABILITIES,
            ),
            "intervention_profile": rng.choice(
                RESPONSE_PROFILES,
                size=config.member_count,
                p=INTERVENTION_PROFILE_PROBABILITIES,
            ),
        }
    )
