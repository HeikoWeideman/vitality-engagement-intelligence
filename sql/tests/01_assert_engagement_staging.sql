DECLARE metrics STRUCT<
    row_count INT64,
    member_count INT64,
    distinct_member_date_count INT64,
    minimum_date DATE,
    maximum_date DATE,
    required_null_count INT64,
    invalid_age_band_count INT64,
    invalid_activity_level_count INT64,
    invalid_reward_profile_count INT64,
    sleep_missing_mismatch_count INT64,
    app_missing_mismatch_count INT64,
    late_record_mismatch_count INT64,
    future_outcome_null_mismatch_count INT64,
    unlabelled_row_count INT64,
    goal_completion_mismatch_count INT64,
    goal_miss_mismatch_count INT64,
    target_rate FLOAT64,
    sleep_missing_rate FLOAT64,
    app_missing_rate FLOAT64,
    step_outlier_rate FLOAT64,
    late_record_rate FLOAT64
>;

SET metrics = (
    SELECT AS STRUCT
        COUNT(*) AS row_count,
        COUNT(DISTINCT member_id) AS member_count,
        COUNT(
            DISTINCT TO_JSON_STRING(
                STRUCT(member_id, activity_date)
            )
        ) AS distinct_member_date_count,
        MIN(activity_date) AS minimum_date,
        MAX(activity_date) AS maximum_date,
        COUNTIF(
            member_id IS NULL
            OR activity_date IS NULL
            OR available_date IS NULL
            OR weekly_goal IS NULL
        ) AS required_null_count,
        COUNTIF(
            age_band NOT IN (
                '18-24',
                '25-34',
                '35-44',
                '45-54',
                '55+'
            )
            OR age_band IS NULL
        ) AS invalid_age_band_count,
        COUNTIF(
            activity_level NOT IN (
                'low',
                'moderate',
                'high'
            )
            OR activity_level IS NULL
        ) AS invalid_activity_level_count,
        COUNTIF(
            reward_profile NOT IN (
                'low',
                'medium',
                'high'
            )
            OR reward_profile IS NULL
        ) AS invalid_reward_profile_count,
        COUNTIF(
            sleep_hours_missing
            IS DISTINCT FROM
            (sleep_hours IS NULL)
        ) AS sleep_missing_mismatch_count,
        COUNTIF(
            app_sessions_missing
            IS DISTINCT FROM
            (app_sessions IS NULL)
        ) AS app_missing_mismatch_count,
        COUNTIF(
            record_delay_days < 0
            OR available_date < activity_date
            OR record_delay_days
                IS DISTINCT FROM DATE_DIFF(
                    available_date,
                    activity_date,
                    DAY
                )
            OR is_late_record
                IS DISTINCT FROM (record_delay_days > 0)
        ) AS late_record_mismatch_count,
        COUNTIF(
            NOT (
                (
                    future_7_day_active_minutes IS NULL
                    AND next_week_goal_completed IS NULL
                    AND will_miss_goal_next_7_days IS NULL
                )
                OR
                (
                    future_7_day_active_minutes IS NOT NULL
                    AND next_week_goal_completed IS NOT NULL
                    AND will_miss_goal_next_7_days IS NOT NULL
                )
            )
        ) AS future_outcome_null_mismatch_count,
        COUNTIF(
            will_miss_goal_next_7_days IS NULL
        ) AS unlabelled_row_count,
        COUNTIF(
            future_7_day_active_minutes IS NOT NULL
            AND next_week_goal_completed
                IS DISTINCT FROM (
                    future_7_day_active_minutes >= weekly_goal
                )
        ) AS goal_completion_mismatch_count,
        COUNTIF(
            will_miss_goal_next_7_days IS NOT NULL
            AND will_miss_goal_next_7_days
                IS DISTINCT FROM NOT next_week_goal_completed
        ) AS goal_miss_mismatch_count,
        SAFE_DIVIDE(
            COUNTIF(will_miss_goal_next_7_days),
            COUNTIF(will_miss_goal_next_7_days IS NOT NULL)
        ) AS target_rate,
        SAFE_DIVIDE(
            COUNTIF(sleep_hours_missing),
            COUNT(*)
        ) AS sleep_missing_rate,
        SAFE_DIVIDE(
            COUNTIF(app_sessions_missing),
            COUNT(*)
        ) AS app_missing_rate,
        SAFE_DIVIDE(
            COUNTIF(is_step_outlier),
            COUNT(*)
        ) AS step_outlier_rate,
        SAFE_DIVIDE(
            COUNTIF(is_late_record),
            COUNT(*)
        ) AS late_record_rate
    FROM `engagement_staging`
);

ASSERT metrics.row_count = 90000
AS 'Expected exactly 90000 staging rows';

ASSERT metrics.member_count = 500
AS 'Expected exactly 500 members';

ASSERT metrics.distinct_member_date_count = metrics.row_count
AS 'Duplicate member and activity-date keys detected';

ASSERT (
    metrics.minimum_date = DATE '2025-01-01'
    AND metrics.maximum_date = DATE '2025-06-29'
)
AS 'Unexpected staging date range';

ASSERT metrics.required_null_count = 0
AS 'Required staging fields contain null values';

ASSERT metrics.invalid_age_band_count = 0
AS 'Unexpected age-band category detected';

ASSERT metrics.invalid_activity_level_count = 0
AS 'Unexpected activity-level category detected';

ASSERT metrics.invalid_reward_profile_count = 0
AS 'Unexpected reward-profile category detected';

ASSERT metrics.sleep_missing_mismatch_count = 0
AS 'Sleep missingness indicator is inconsistent';

ASSERT metrics.app_missing_mismatch_count = 0
AS 'App-session missingness indicator is inconsistent';

ASSERT metrics.late_record_mismatch_count = 0
AS 'Late-record fields are inconsistent';

ASSERT metrics.future_outcome_null_mismatch_count = 0
AS 'Future outcome fields have inconsistent null states';

ASSERT metrics.unlabelled_row_count = 3500
AS 'Expected exactly 3500 unlabelled final-window rows';

ASSERT metrics.goal_completion_mismatch_count = 0
AS 'Goal-completion outcome is inconsistent';

ASSERT metrics.goal_miss_mismatch_count = 0
AS 'Goal-miss target is inconsistent';

ASSERT metrics.target_rate BETWEEN 0.12 AND 0.30
AS 'Goal-miss target rate is outside the approved range';

ASSERT metrics.sleep_missing_rate BETWEEN 0.02 AND 0.04
AS 'Sleep missingness rate is outside its expected range';

ASSERT metrics.app_missing_rate BETWEEN 0.01 AND 0.03
AS 'App-session missingness rate is outside its expected range';

ASSERT metrics.step_outlier_rate BETWEEN 0.002 AND 0.008
AS 'Step-outlier rate is outside its expected range';

ASSERT metrics.late_record_rate BETWEEN 0.02 AND 0.04
AS 'Late-record rate is outside its expected range';
