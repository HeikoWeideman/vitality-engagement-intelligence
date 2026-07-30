DECLARE metrics STRUCT<
    view_row_count INT64,
    prediction_date_count INT64,
    risk_band_count INT64,
    total_forecast_row_count INT64,
    invalid_daily_total_count INT64,
    invalid_daily_rate_count INT64,
    invalid_member_count INT64,
    invalid_band_count INT64,
    invalid_band_order_count INT64,
    invalid_model_count INT64,
    invalid_threshold_count INT64,
    invalid_metadata_count INT64,
    failed_quality_count INT64
>;

SET metrics = (
    WITH daily_reconciliation AS (
        SELECT
            prediction_date,
            SUM(forecast_row_count) AS daily_forecast_row_count,
            SUM(risk_band_forecast_rate) AS daily_forecast_rate,
            COUNT(*) AS daily_risk_band_count
        FROM
            `vitality_engagement_dev.dashboard_risk_distribution`
        GROUP BY
            prediction_date
    ),
    view_metrics AS (
        SELECT
            COUNT(*) AS view_row_count,
            COUNT(DISTINCT prediction_date) AS prediction_date_count,
            COUNT(DISTINCT risk_band) AS risk_band_count,
            SUM(forecast_row_count) AS total_forecast_row_count,

            COUNTIF(
                forecast_member_count != forecast_row_count
            ) AS invalid_member_count,

            COUNTIF(
                risk_band NOT IN (
                    '0.00_to_0.20',
                    '0.20_to_0.40',
                    '0.40_to_0.60',
                    '0.60_to_0.80',
                    '0.80_to_1.00'
                )
            ) AS invalid_band_count,

            COUNTIF(
                risk_band_order != CASE risk_band
                    WHEN '0.00_to_0.20' THEN 1
                    WHEN '0.20_to_0.40' THEN 2
                    WHEN '0.40_to_0.60' THEN 3
                    WHEN '0.60_to_0.80' THEN 4
                    WHEN '0.80_to_1.00' THEN 5
                    ELSE NULL
                END
            ) AS invalid_band_order_count,

            COUNTIF(
                model_name != 'bigquery_logistic_baseline'
            ) AS invalid_model_count,

            COUNTIF(
                threshold != 0.467
            ) AS invalid_threshold_count,

            COUNTIF(
                synthetic_data IS DISTINCT FROM TRUE
                OR data_classification != 'fully_synthetic'
                OR metric_class != 'forecast'
                OR source_name != 'engagement_logistic_scoring_predictions'
                OR source_as_of != DATE '2025-06-29'
                OR view_refreshed_at IS NULL
            ) AS invalid_metadata_count,

            COUNTIF(
                is_valid IS DISTINCT FROM TRUE
                OR invalid_reason IS NOT NULL
            ) AS failed_quality_count

        FROM
            `vitality_engagement_dev.dashboard_risk_distribution`
    ),
    reconciliation_metrics AS (
        SELECT
            COUNTIF(
                daily_forecast_row_count != 500
            ) AS invalid_daily_total_count,

            COUNTIF(
                ABS(daily_forecast_rate - 1.0) > 0.000000001
            ) AS invalid_daily_rate_count,

            COUNTIF(
                daily_risk_band_count != 5
            ) AS invalid_daily_band_count

        FROM
            daily_reconciliation
    )
    SELECT AS STRUCT
        view_metrics.view_row_count,
        view_metrics.prediction_date_count,
        view_metrics.risk_band_count,
        view_metrics.total_forecast_row_count,
        reconciliation_metrics.invalid_daily_total_count,
        reconciliation_metrics.invalid_daily_rate_count,
        view_metrics.invalid_member_count,
        view_metrics.invalid_band_count
            + reconciliation_metrics.invalid_daily_band_count
            AS invalid_band_count,
        view_metrics.invalid_band_order_count,
        view_metrics.invalid_model_count,
        view_metrics.invalid_threshold_count,
        view_metrics.invalid_metadata_count,
        view_metrics.failed_quality_count
    FROM
        view_metrics
    CROSS JOIN
        reconciliation_metrics
);

ASSERT metrics.view_row_count = 35
AS 'Expected seven dates and five governed risk bands';

ASSERT metrics.prediction_date_count = 7
AS 'Expected exactly seven risk-distribution dates';

ASSERT metrics.risk_band_count = 5
AS 'Expected exactly five governed risk bands';

ASSERT metrics.total_forecast_row_count = 3500
AS 'Risk-band forecasts do not reconcile to the scoring source';

ASSERT metrics.invalid_daily_total_count = 0
AS 'A risk-distribution date does not reconcile to 500 forecasts';

ASSERT metrics.invalid_daily_rate_count = 0
AS 'Risk-band rates do not sum to one for a prediction date';

ASSERT metrics.invalid_member_count = 0
AS 'Risk-band member and row counts do not reconcile';

ASSERT metrics.invalid_band_count = 0
AS 'Risk-distribution rows contain missing or unsupported bands';

ASSERT metrics.invalid_band_order_count = 0
AS 'Risk-band ordering is inconsistent';

ASSERT metrics.invalid_model_count = 0
AS 'Risk-distribution rows use an unexpected model label';

ASSERT metrics.invalid_threshold_count = 0
AS 'Risk-distribution rows use an unexpected threshold';

ASSERT metrics.invalid_metadata_count = 0
AS 'Risk-distribution governance metadata is invalid';

ASSERT metrics.failed_quality_count = 0
AS 'Risk-distribution rows failed their embedded quality status';
