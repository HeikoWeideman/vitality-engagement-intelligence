DECLARE metrics STRUCT<
    daily_row_count INT64,
    total_forecast_row_count INT64,
    total_high_risk_count INT64,
    minimum_prediction_date DATE,
    maximum_prediction_date DATE,
    invalid_daily_count INT64,
    invalid_member_count INT64,
    invalid_probability_count INT64,
    invalid_rate_count INT64,
    invalid_model_count INT64,
    invalid_threshold_count INT64,
    invalid_metadata_count INT64,
    failed_quality_count INT64
>;

SET metrics = (
    SELECT AS STRUCT
        COUNT(*) AS daily_row_count,
        SUM(forecast_row_count) AS total_forecast_row_count,
        SUM(high_risk_forecast_count) AS total_high_risk_count,
        MIN(prediction_date) AS minimum_prediction_date,
        MAX(prediction_date) AS maximum_prediction_date,

        COUNTIF(
            forecast_row_count != 500
        ) AS invalid_daily_count,

        COUNTIF(
            forecast_member_count != 500
        ) AS invalid_member_count,

        COUNTIF(
            mean_forecast_risk < 0.0
            OR mean_forecast_risk > 1.0
        ) AS invalid_probability_count,

        COUNTIF(
            high_risk_forecast_rate
            IS DISTINCT FROM
            SAFE_DIVIDE(
                high_risk_forecast_count,
                forecast_row_count
            )
        ) AS invalid_rate_count,

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
        `vitality_engagement_dev.dashboard_scoring_daily_summary`
);

ASSERT metrics.daily_row_count = 7
AS 'Expected exactly seven dashboard scoring dates';

ASSERT metrics.total_forecast_row_count = 3500
AS 'Dashboard forecast rows do not reconcile to the scoring source';

ASSERT metrics.total_high_risk_count = 1091
AS 'Dashboard high-risk forecasts do not reconcile to the BigQuery baseline';

ASSERT metrics.minimum_prediction_date = DATE '2025-06-23'
AS 'Unexpected minimum dashboard prediction date';

ASSERT metrics.maximum_prediction_date = DATE '2025-06-29'
AS 'Unexpected maximum dashboard prediction date';

ASSERT metrics.invalid_daily_count = 0
AS 'A dashboard date does not contain 500 forecast rows';

ASSERT metrics.invalid_member_count = 0
AS 'A dashboard date does not contain 500 synthetic members';

ASSERT metrics.invalid_probability_count = 0
AS 'A dashboard mean probability falls outside zero to one';

ASSERT metrics.invalid_rate_count = 0
AS 'A dashboard high-risk rate does not reconcile';

ASSERT metrics.invalid_model_count = 0
AS 'Dashboard scoring rows use an unexpected model label';

ASSERT metrics.invalid_threshold_count = 0
AS 'Dashboard scoring rows use an unexpected threshold';

ASSERT metrics.invalid_metadata_count = 0
AS 'Dashboard scoring governance metadata is invalid';

ASSERT metrics.failed_quality_count = 0
AS 'Dashboard scoring rows failed their embedded quality status';
