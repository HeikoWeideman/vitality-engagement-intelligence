CREATE OR REPLACE VIEW
    `vitality_engagement_dev.dashboard_scoring_daily_summary`
OPTIONS (
    description = 'Read-only aggregate forecast summary for the synthetic Stage 3 BigQuery logistic baseline.'
)
AS
WITH source_quality AS (
    SELECT
        COUNT(*) AS source_row_count,
        COUNTIF(
            predicted_probability IS NULL
        ) AS null_probability_count,
        COUNTIF(
            predicted_probability < 0.0
            OR predicted_probability > 1.0
        ) AS invalid_probability_count,
        COUNTIF(
            predicted_high_risk
            IS DISTINCT FROM
            (predicted_probability >= 0.467)
        ) AS threshold_mismatch_count,
        COUNT(*)
        - COUNT(
            DISTINCT TO_JSON_STRING(
                STRUCT(
                    member_id,
                    prediction_date
                )
            )
        ) AS duplicate_key_count,
        MAX(prediction_date) AS source_as_of
    FROM
        `vitality_engagement_dev.engagement_logistic_scoring_predictions`
),
daily_summary AS (
    SELECT
        prediction_date,
        COUNT(*) AS forecast_row_count,
        COUNT(DISTINCT member_id) AS forecast_member_count,
        AVG(predicted_probability) AS mean_forecast_risk,
        COUNTIF(predicted_high_risk) AS high_risk_forecast_count,
        SAFE_DIVIDE(
            COUNTIF(predicted_high_risk),
            COUNT(*)
        ) AS high_risk_forecast_rate
    FROM
        `vitality_engagement_dev.engagement_logistic_scoring_predictions`
    GROUP BY
        prediction_date
)
SELECT
    daily_summary.prediction_date,
    'bigquery_logistic_baseline' AS model_name,
    0.467 AS threshold,
    daily_summary.forecast_row_count,
    daily_summary.forecast_member_count,
    daily_summary.mean_forecast_risk,
    daily_summary.high_risk_forecast_count,
    daily_summary.high_risk_forecast_rate,
    TRUE AS synthetic_data,
    'fully_synthetic' AS data_classification,
    'forecast' AS metric_class,
    'engagement_logistic_scoring_predictions' AS source_name,
    source_quality.source_as_of,
    CURRENT_TIMESTAMP() AS view_refreshed_at,
    (
        source_quality.source_row_count > 0
        AND source_quality.null_probability_count = 0
        AND source_quality.invalid_probability_count = 0
        AND source_quality.threshold_mismatch_count = 0
        AND source_quality.duplicate_key_count = 0
    ) AS is_valid,
    CASE
        WHEN source_quality.source_row_count = 0
            THEN 'Scoring source is empty'
        WHEN source_quality.null_probability_count > 0
            THEN 'Scoring source contains null probabilities'
        WHEN source_quality.invalid_probability_count > 0
            THEN 'Scoring source contains probabilities outside zero to one'
        WHEN source_quality.threshold_mismatch_count > 0
            THEN 'Scoring classifications do not match the frozen BigQuery threshold'
        WHEN source_quality.duplicate_key_count > 0
            THEN 'Scoring source contains duplicate member-date keys'
        ELSE NULL
    END AS invalid_reason
FROM
    daily_summary
CROSS JOIN
    source_quality;
