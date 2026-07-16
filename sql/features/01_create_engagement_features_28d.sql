CREATE OR REPLACE TABLE `engagement_features_28d`
OPTIONS (
    description = 'Leakage-safe 28-day features for predicting seven-day goal misses.'
)
AS
WITH member_bounds AS (
    SELECT
        member_id,
        MIN(activity_date) AS first_activity_date
    FROM `engagement_staging`
    GROUP BY member_id
),
anchors AS (
    SELECT
        staging.member_id,
        staging.activity_date AS prediction_date,
        staging.will_miss_goal_next_7_days
            AS label_will_miss_goal_next_7_days
    FROM `engagement_staging` AS staging
    INNER JOIN member_bounds
        USING (member_id)
    WHERE staging.activity_date >= DATE_ADD(
        member_bounds.first_activity_date,
        INTERVAL 28 DAY
    )
),
aggregated AS (
    SELECT
        anchors.member_id,
        anchors.prediction_date,
        DATE_SUB(
            anchors.prediction_date,
            INTERVAL 28 DAY
        ) AS feature_window_start,
        DATE_SUB(
            anchors.prediction_date,
            INTERVAL 1 DAY
        ) AS feature_window_end,
        anchors.label_will_miss_goal_next_7_days,

        (
            ARRAY_AGG(
                history.age_band IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS age_band_as_of,

        (
            ARRAY_AGG(
                history.membership_months IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS membership_months_as_of,

        (
            ARRAY_AGG(
                history.activity_level IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS activity_level_as_of,

        (
            ARRAY_AGG(
                history.reward_profile IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS reward_profile_as_of,

        (
            ARRAY_AGG(
                history.intervention_profile IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS intervention_profile_as_of,

        (
            ARRAY_AGG(
                history.weekly_goal IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS weekly_goal_as_of,

        (
            ARRAY_AGG(
                history.weekly_active_minutes_so_far IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS weekly_active_minutes_so_far_as_of,

        (
            ARRAY_AGG(
                history.goal_completion_percentage IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS goal_completion_percentage_as_of,

        (
            ARRAY_AGG(
                history.previous_goal_streak IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS previous_goal_streak_as_of,

        (
            ARRAY_AGG(
                history.previous_failed_goals IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS previous_failed_goals_as_of,

        (
            ARRAY_AGG(
                history.days_since_last_app_session IGNORE NULLS
                ORDER BY history.activity_date DESC
                LIMIT 1
            )
        )[SAFE_OFFSET(0)] AS days_since_last_app_session_as_of,

        COUNT(history.activity_date) AS available_day_count_28d,
        28 - COUNT(history.activity_date) AS unavailable_day_count_28d,
        MAX(history.activity_date) AS max_source_activity_date,
        MAX(history.available_date) AS max_source_available_date,

        AVG(history.daily_steps) AS avg_daily_steps_28d,
        STDDEV_SAMP(history.daily_steps) AS stddev_daily_steps_28d,

        AVG(
            IF(
                history.activity_date >= DATE_SUB(
                    anchors.prediction_date,
                    INTERVAL 7 DAY
                ),
                history.daily_steps,
                NULL
            )
        ) AS avg_daily_steps_7d,

        AVG(
            IF(
                history.activity_date BETWEEN
                    DATE_SUB(
                        anchors.prediction_date,
                        INTERVAL 14 DAY
                    )
                    AND DATE_SUB(
                        anchors.prediction_date,
                        INTERVAL 8 DAY
                    ),
                history.daily_steps,
                NULL
            )
        ) AS avg_daily_steps_prior_7d,

        SUM(history.active_minutes) AS sum_active_minutes_28d,
        AVG(history.active_minutes) AS avg_active_minutes_28d,
        STDDEV_SAMP(
            history.active_minutes
        ) AS stddev_active_minutes_28d,

        AVG(
            IF(
                history.activity_date >= DATE_SUB(
                    anchors.prediction_date,
                    INTERVAL 7 DAY
                ),
                history.active_minutes,
                NULL
            )
        ) AS avg_active_minutes_7d,

        AVG(
            IF(
                history.activity_date BETWEEN
                    DATE_SUB(
                        anchors.prediction_date,
                        INTERVAL 14 DAY
                    )
                    AND DATE_SUB(
                        anchors.prediction_date,
                        INTERVAL 8 DAY
                    ),
                history.active_minutes,
                NULL
            )
        ) AS avg_active_minutes_prior_7d,

        COUNTIF(
            history.active_minutes > 0
        ) AS active_day_count_28d,

        AVG(history.sleep_hours) AS avg_sleep_hours_28d,

        AVG(
            IF(
                history.activity_date >= DATE_SUB(
                    anchors.prediction_date,
                    INTERVAL 7 DAY
                ),
                history.sleep_hours,
                NULL
            )
        ) AS avg_sleep_hours_7d,

        COUNT(history.sleep_hours) AS sleep_observation_count_28d,

        COUNTIF(
            history.sleep_hours_missing
        ) AS sleep_missing_day_count_28d,

        SUM(history.app_sessions) AS sum_app_sessions_28d,
        AVG(history.app_sessions) AS avg_app_sessions_28d,

        AVG(
            IF(
                history.activity_date >= DATE_SUB(
                    anchors.prediction_date,
                    INTERVAL 7 DAY
                ),
                history.app_sessions,
                NULL
            )
        ) AS avg_app_sessions_7d,

        AVG(
            IF(
                history.activity_date BETWEEN
                    DATE_SUB(
                        anchors.prediction_date,
                        INTERVAL 14 DAY
                    )
                    AND DATE_SUB(
                        anchors.prediction_date,
                        INTERVAL 8 DAY
                    ),
                history.app_sessions,
                NULL
            )
        ) AS avg_app_sessions_prior_7d,

        COUNT(
            history.app_sessions
        ) AS app_session_observation_count_28d,

        COUNTIF(
            history.app_sessions_missing
        ) AS app_sessions_missing_day_count_28d,

        SUM(history.rewards_viewed) AS rewards_viewed_28d,
        SUM(history.rewards_redeemed) AS rewards_redeemed_28d,

        SAFE_DIVIDE(
            SUM(history.rewards_redeemed),
            SUM(history.rewards_viewed)
        ) AS reward_redemption_rate_28d,

        COUNTIF(
            history.intervention_received
        ) AS interventions_received_28d,

        COUNTIF(
            history.intervention_opened
        ) AS interventions_opened_28d,

        COUNTIF(
            history.intervention_clicked
        ) AS interventions_clicked_28d,

        SAFE_DIVIDE(
            COUNTIF(history.intervention_opened),
            COUNTIF(history.intervention_received)
        ) AS intervention_open_rate_28d,

        SAFE_DIVIDE(
            COUNTIF(history.intervention_clicked),
            COUNTIF(history.intervention_received)
        ) AS intervention_click_rate_28d,

        COUNTIF(
            history.is_step_outlier
        ) AS step_outlier_day_count_28d,

        COUNTIF(
            history.is_late_record
        ) AS late_record_count_28d,

        COUNTIF(
            history.activity_level_changed
        ) AS activity_level_change_count_28d,

        AVG(
            history.goal_completion_percentage
        ) AS avg_goal_completion_percentage_28d

    FROM anchors
    LEFT JOIN `engagement_staging` AS history
        ON anchors.member_id = history.member_id
        AND history.activity_date BETWEEN
            DATE_SUB(
                anchors.prediction_date,
                INTERVAL 28 DAY
            )
            AND DATE_SUB(
                anchors.prediction_date,
                INTERVAL 1 DAY
            )
        AND history.available_date <= anchors.prediction_date
    GROUP BY
        anchors.member_id,
        anchors.prediction_date,
        anchors.label_will_miss_goal_next_7_days
)
SELECT
    aggregated.*,
    avg_daily_steps_7d
        - avg_daily_steps_prior_7d
        AS daily_steps_trend_7d,
    avg_active_minutes_7d
        - avg_active_minutes_prior_7d
        AS active_minutes_trend_7d,
    avg_app_sessions_7d
        - avg_app_sessions_prior_7d
        AS app_sessions_trend_7d
FROM aggregated;
