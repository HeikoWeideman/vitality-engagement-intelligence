CREATE OR REPLACE VIEW
    `vitality_engagement_dev.dashboard_observed_outcome_summary`
OPTIONS (
    description = 'Read-only daily summary of completed synthetic seven-day goal outcomes.'
)
AS
WITH source_quality AS (
    SELECT
        COUNT(*) AS source_row_count,
        COUNTIF(
            label_will_miss_goal_next_7_days IS NOT NULL
        ) AS labelled_row_count,
        COUNTIF(
            label_will_miss_goal_next_7_days IS NULL
        ) AS unlabelled_row_count,
        COUNT(*)
        - COUNT(
            DISTINCT TO_JSON_STRING(
                STRUCT(
                    member_id,
                    prediction_date
                )
            )
        ) AS duplicate_key_count,
        MIN(
            IF(
                label_will_miss_goal_next_7_days IS NOT NULL,
                prediction_date,
                NULL
            )
        ) AS minimum_labelled_prediction_date,
        MAX(
            IF(
                label_will_miss_goal_next_7_days IS NOT NULL,
                prediction_date,
                NULL
            )
        ) AS source_as_of
    FROM
        `vitality_engagement_dev.engagement_features_28d`
),
daily_summary AS (
    SELECT
        prediction_date,
        DATE_ADD(
            prediction_date,
            INTERVAL 7 DAY
        ) AS outcome_window_end,
        COUNT(*) AS observed_labelled_row_count,
        COUNTIF(
            label_will_miss_goal_next_7_days IS TRUE
        ) AS observed_missed_goal_count,
        COUNTIF(
            label_will_miss_goal_next_7_days IS FALSE
        ) AS observed_goal_met_count,
        SAFE_DIVIDE(
            COUNTIF(
                label_will_miss_goal_next_7_days IS TRUE
            ),
            COUNT(*)
        ) AS observed_missed_goal_rate
    FROM
        `vitality_engagement_dev.engagement_features_28d`
    WHERE
        label_will_miss_goal_next_7_days IS NOT NULL
    GROUP BY
        prediction_date
)
SELECT
    daily_summary.prediction_date,
    daily_summary.outcome_window_end,
    daily_summary.observed_labelled_row_count,
    daily_summary.observed_missed_goal_count,
    daily_summary.observed_goal_met_count,
    daily_summary.observed_missed_goal_rate,
    TRUE AS synthetic_data,
    'fully_synthetic' AS data_classification,
    'observed_outcome' AS metric_class,
    'engagement_features_28d' AS source_name,
    source_quality.source_as_of,
    CURRENT_TIMESTAMP() AS view_refreshed_at,
    (
        source_quality.source_row_count > 0
        AND source_quality.labelled_row_count > 0
        AND source_quality.unlabelled_row_count >= 0
        AND source_quality.duplicate_key_count = 0
    ) AS is_valid,
    CASE
        WHEN source_quality.source_row_count = 0
            THEN 'Feature source is empty'
        WHEN source_quality.labelled_row_count = 0
            THEN 'No completed outcome windows are available'
        WHEN source_quality.duplicate_key_count > 0
            THEN 'Feature source contains duplicate member-date keys'
        ELSE NULL
    END AS invalid_reason
FROM
    daily_summary
CROSS JOIN
    source_quality;
