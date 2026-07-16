DECLARE metrics STRUCT<
    row_count INT64,
    member_count INT64,
    duplicate_key_count INT64,
    minimum_prediction_date DATE,
    maximum_prediction_date DATE,
    unlabelled_row_count INT64,
    final_window_label_mismatch_count INT64,
    minimum_available_days INT64,
    maximum_available_days INT64,
    invalid_available_day_count INT64,
    window_definition_mismatch_count INT64,
    future_activity_leak_count INT64,
    unavailable_record_leak_count INT64,
    invalid_rate_count INT64,
    trend_mismatch_count INT64
>;

SET metrics = (
    WITH bounds AS (
        SELECT
            MAX(prediction_date) AS maximum_prediction_date
        FROM `engagement_features_28d`
    )
    SELECT AS STRUCT
        COUNT(*) AS row_count,
        COUNT(DISTINCT member_id) AS member_count,
        COUNT(*) - COUNT(
            DISTINCT TO_JSON_STRING(
                STRUCT(member_id, prediction_date)
            )
        ) AS duplicate_key_count,
        MIN(prediction_date) AS minimum_prediction_date,
        MAX(prediction_date) AS maximum_prediction_date,
        COUNTIF(
            label_will_miss_goal_next_7_days IS NULL
        ) AS unlabelled_row_count,
        COUNTIF(
            (
                prediction_date > DATE_SUB(
                    bounds.maximum_prediction_date,
                    INTERVAL 7 DAY
                )
            )
            IS DISTINCT FROM
            (
                label_will_miss_goal_next_7_days IS NULL
            )
        ) AS final_window_label_mismatch_count,
        MIN(available_day_count_28d) AS minimum_available_days,
        MAX(available_day_count_28d) AS maximum_available_days,
        COUNTIF(
            available_day_count_28d < 26
            OR available_day_count_28d > 28
            OR unavailable_day_count_28d < 0
            OR available_day_count_28d
                + unavailable_day_count_28d != 28
        ) AS invalid_available_day_count,
        COUNTIF(
            feature_window_start != DATE_SUB(
                prediction_date,
                INTERVAL 28 DAY
            )
            OR feature_window_end != DATE_SUB(
                prediction_date,
                INTERVAL 1 DAY
            )
            OR DATE_DIFF(
                feature_window_end,
                feature_window_start,
                DAY
            ) != 27
        ) AS window_definition_mismatch_count,
        COUNTIF(
            max_source_activity_date > feature_window_end
        ) AS future_activity_leak_count,
        COUNTIF(
            max_source_available_date > prediction_date
        ) AS unavailable_record_leak_count,
        COUNTIF(
            (
                reward_redemption_rate_28d IS NOT NULL
                AND reward_redemption_rate_28d
                    NOT BETWEEN 0.0 AND 1.0
            )
            OR
            (
                intervention_open_rate_28d IS NOT NULL
                AND intervention_open_rate_28d
                    NOT BETWEEN 0.0 AND 1.0
            )
            OR
            (
                intervention_click_rate_28d IS NOT NULL
                AND intervention_click_rate_28d
                    NOT BETWEEN 0.0 AND 1.0
            )
        ) AS invalid_rate_count,
        COUNTIF(
            daily_steps_trend_7d
                IS DISTINCT FROM
                (
                    avg_daily_steps_7d
                    - avg_daily_steps_prior_7d
                )
            OR active_minutes_trend_7d
                IS DISTINCT FROM
                (
                    avg_active_minutes_7d
                    - avg_active_minutes_prior_7d
                )
            OR app_sessions_trend_7d
                IS DISTINCT FROM
                (
                    avg_app_sessions_7d
                    - avg_app_sessions_prior_7d
                )
        ) AS trend_mismatch_count
    FROM `engagement_features_28d`
    CROSS JOIN bounds
);

ASSERT metrics.row_count = 76000
AS 'Expected exactly 76000 feature rows';

ASSERT metrics.member_count = 500
AS 'Expected exactly 500 members in the feature table';

ASSERT metrics.duplicate_key_count = 0
AS 'Duplicate member and prediction-date keys detected';

ASSERT metrics.minimum_prediction_date = DATE '2025-01-29'
AS 'Unexpected minimum prediction date';

ASSERT metrics.maximum_prediction_date = DATE '2025-06-29'
AS 'Unexpected maximum prediction date';

ASSERT metrics.unlabelled_row_count = 3500
AS 'Expected exactly 3500 unlabelled feature rows';

ASSERT metrics.final_window_label_mismatch_count = 0
AS 'Label nulls are not restricted to the final seven-day window';

ASSERT metrics.minimum_available_days = 26
AS 'Unexpected minimum number of available days';

ASSERT metrics.maximum_available_days = 28
AS 'Unexpected maximum number of available days';

ASSERT metrics.invalid_available_day_count = 0
AS 'Available and unavailable day counts are inconsistent';

ASSERT metrics.window_definition_mismatch_count = 0
AS 'A 28-day feature window is defined incorrectly';

ASSERT metrics.future_activity_leak_count = 0
AS 'Feature windows include activity after their permitted end date';

ASSERT metrics.unavailable_record_leak_count = 0
AS 'Feature windows include records unavailable at prediction time';

ASSERT metrics.invalid_rate_count = 0
AS 'A derived rate falls outside the valid zero-to-one range';

ASSERT metrics.trend_mismatch_count = 0
AS 'A seven-day trend feature is inconsistent';
