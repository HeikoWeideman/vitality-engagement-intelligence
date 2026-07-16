CREATE OR REPLACE TABLE `engagement_staging`
OPTIONS (
    description = 'Normalized staging data for the Vitality Engagement Intelligence Engine.'
)
AS
SELECT
    member_id,
    age_band,
    membership_months,
    activity_level,
    reward_profile,
    intervention_profile,
    DATE(`date`) AS activity_date,
    daily_steps,
    active_minutes,
    sleep_hours,
    weekly_goal,
    app_sessions,
    days_since_last_app_session,
    rewards_viewed,
    rewards_redeemed,
    intervention_received,
    intervention_type,
    intervention_opened,
    intervention_clicked,
    DATE(week_start) AS week_start,
    weekly_active_minutes_so_far,
    goal_completion_percentage,
    previous_goal_streak,
    previous_failed_goals,
    future_7_day_active_minutes,
    next_week_goal_completed,
    will_miss_goal_next_7_days,
    sleep_hours_missing,
    app_sessions_missing,
    is_step_outlier,
    is_late_record,
    record_delay_days,
    DATE(available_date) AS available_date,
    activity_level_changed
FROM `engagement_raw`;
