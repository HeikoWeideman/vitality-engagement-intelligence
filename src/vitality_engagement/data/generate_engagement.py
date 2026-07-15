"""Generate the synthetic member-day engagement structure."""

import pandas as pd

from vitality_engagement.data.generate_members import generate_members
from vitality_engagement.data.schema import GenerationConfig


def generate_member_day_skeleton(
    config: GenerationConfig,
) -> pd.DataFrame:
    """Create one row for every synthetic member and calendar date.

    Args:
        config: Reproducible data-generation configuration.

    Returns:
        A DataFrame containing one row per member per date.
    """
    members = generate_members(config)

    dates = pd.DataFrame(
        {
            "date": pd.date_range(
                start=config.start_date,
                periods=config.day_count,
                freq="D",
            )
        }
    )

    skeleton = members.merge(dates, how="cross")

    return skeleton.sort_values(
        ["member_id", "date"],
        ignore_index=True,
    )
