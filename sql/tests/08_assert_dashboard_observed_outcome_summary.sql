DECLARE metrics STRUCT<
    daily_row_count INT64,
    total_labelled_row_count INT64,
    total_missed_goal_count INT64,
    total_goal_met_count INT64,
    minimum_prediction_date DATE,
    maximum_prediction_date DATE,
    minimum_outcome_window_end DATE,
    maximum_outcome_window_end DATE,
    duplicate_date_count INT64,
    invalid_daily_row_count INT64,
    invalid_outcome_reconciliation_count INT64,
    invalid_rate_count INT64,
    invalid_metadata_count INT64,
    failed_quality_count INT64
>;

SET metrics = (
    SELECT AS STRUCT
        COUNT(*) AS daily_row_count,
        SUM(observed_labelled_row_count) AS total_labelled_row_count,
        SUM(observed_missed_goal_count) AS total_missed_goal_count,
        SUM(observed_goal_met_count) AS total_goal_met_count,
        MIN(prediction_date) AS minimum_prediction_date,
        MAX(prediction_date) AS maximum_prediction_date,
        MIN(outcome_window_end) AS minimum_outcome_window_end,
        MAX(outcome_window_end) AS maximum_outcome_window_end,

        COUNT(*)
        - COUNT(DISTINCT prediction_date)
            AS duplicate_date_count,

        COUNTIF(
            observed_labelled_row_count != 500
        ) AS invalid_daily_row_count,

        COUNTIF(
            observed_missed_goal_count
            + observed_goal_met_count
            != observed_labelled_row_count
        ) AS invalid_outcome_reconciliation_count,

        COUNTIF(
            observed_missed_goal_rate
            IS DISTINCT FROM
            SAFE_DIVIDE(
                observed_missed_goal_count,
                observed_labelled_row_count
            )
            OR observed_missed_goal_rate < 0.0
            OR observed_missed_goal_rate > 1.0
        ) AS invalid_rate_count,

        COUNTIF(
            synthetic_data IS DISTINCT FROM TRUE
            OR data_classification != 'fully_synthetic'
            OR metric_class != 'observed_outcome'
            OR source_name != 'engagement_features_28d'
            OR source_as_of != DATE '2025-06-22'
            OR view_refreshed_at IS NULL
        ) AS invalid_metadata_count,

        COUNTIF(
            is_valid IS DISTINCT FROM TRUE
            OR invalid_reason IS NOT NULL
        ) AS failed_quality_count

    FROM
        `vitality_engagement_dev.dashboard_observed_outcome_summary`
);

ASSERT metrics.daily_row_count = 145
AS 'Expected exactly 145 completed outcome dates';

ASSERT metrics.total_labelled_row_count = 72500
AS 'Completed outcome rows do not reconcile to the feature source';

ASSERT metrics.total_missed_goal_count = 14078
AS 'Observed missed-goal outcomes do not reconcile';

ASSERT metrics.total_goal_met_count = 58422
AS 'Observed goal-met outcomes do not reconcile';

ASSERT metrics.minimum_prediction_date = DATE '2025-01-29'
AS 'Unexpected minimum completed-outcome prediction date';

ASSERT metrics.maximum_prediction_date = DATE '2025-06-22'
AS 'Unexpected maximum completed-outcome prediction date';

ASSERT metrics.minimum_outcome_window_end = DATE '2025-02-05'
AS 'Unexpected minimum outcome-window end date';

ASSERT metrics.maximum_outcome_window_end = DATE '2025-06-29'
AS 'Unexpected maximum outcome-window end date';

ASSERT metrics.duplicate_date_count = 0
AS 'Observed-outcome view contains duplicate prediction dates';

ASSERT metrics.invalid_daily_row_count = 0
AS 'A completed outcome date does not contain 500 rows';

ASSERT metrics.invalid_outcome_reconciliation_count = 0
AS 'Observed missed and met outcomes do not reconcile';

ASSERT metrics.invalid_rate_count = 0
AS 'An observed missed-goal rate is invalid';

ASSERT metrics.invalid_metadata_count = 0
AS 'Observed-outcome governance metadata is invalid';

ASSERT metrics.failed_quality_count = 0
AS 'Observed-outcome rows failed their embedded quality status';
