CREATE OR REPLACE VIEW
    `vitality_engagement_dev.dashboard_risk_distribution`
OPTIONS (
    description = 'Read-only aggregate forecast risk-band distribution for the synthetic Stage 3 BigQuery logistic baseline.'
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
prediction_dates AS (
    SELECT DISTINCT
        prediction_date
    FROM
        `vitality_engagement_dev.engagement_logistic_scoring_predictions`
),
risk_bands AS (
    SELECT
        1 AS risk_band_order,
        '0.00_to_0.20' AS risk_band
    UNION ALL
    SELECT
        2,
        '0.20_to_0.40'
    UNION ALL
    SELECT
        3,
        '0.40_to_0.60'
    UNION ALL
    SELECT
        4,
        '0.60_to_0.80'
    UNION ALL
    SELECT
        5,
        '0.80_to_1.00'
),
banded_predictions AS (
    SELECT
        member_id,
        prediction_date,
        CASE
            WHEN predicted_probability < 0.20
                THEN '0.00_to_0.20'
            WHEN predicted_probability < 0.40
                THEN '0.20_to_0.40'
            WHEN predicted_probability < 0.60
                THEN '0.40_to_0.60'
            WHEN predicted_probability < 0.80
                THEN '0.60_to_0.80'
            ELSE '0.80_to_1.00'
        END AS risk_band
    FROM
        `vitality_engagement_dev.engagement_logistic_scoring_predictions`
),
band_counts AS (
    SELECT
        prediction_date,
        risk_band,
        COUNT(*) AS forecast_row_count,
        COUNT(DISTINCT member_id) AS forecast_member_count
    FROM
        banded_predictions
    GROUP BY
        prediction_date,
        risk_band
),
daily_totals AS (
    SELECT
        prediction_date,
        COUNT(*) AS daily_forecast_row_count
    FROM
        `vitality_engagement_dev.engagement_logistic_scoring_predictions`
    GROUP BY
        prediction_date
)
SELECT
    prediction_dates.prediction_date,
    'bigquery_logistic_baseline' AS model_name,
    0.467 AS threshold,
    risk_bands.risk_band_order,
    risk_bands.risk_band,
    COALESCE(
        band_counts.forecast_row_count,
        0
    ) AS forecast_row_count,
    COALESCE(
        band_counts.forecast_member_count,
        0
    ) AS forecast_member_count,
    SAFE_DIVIDE(
        COALESCE(
            band_counts.forecast_row_count,
            0
        ),
        daily_totals.daily_forecast_row_count
    ) AS risk_band_forecast_rate,
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
    prediction_dates
CROSS JOIN
    risk_bands
INNER JOIN
    daily_totals
    USING (prediction_date)
LEFT JOIN
    band_counts
    ON prediction_dates.prediction_date = band_counts.prediction_date
    AND risk_bands.risk_band = band_counts.risk_band
CROSS JOIN
    source_quality;
