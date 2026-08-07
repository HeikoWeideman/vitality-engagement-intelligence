CREATE OR REPLACE VIEW
    `vitality_engagement_dev.model_monitoring_status`
OPTIONS (
    description = 'Read-only monitoring status for the governed synthetic BigQuery logistic baseline. This view reports checks only and authorises no operational action.'
)
AS
WITH scoring_predictions AS (
    SELECT
        member_id,
        prediction_date,
        predicted_probability,
        predicted_high_risk
    FROM
        `vitality_engagement_dev.engagement_logistic_scoring_predictions`
),
scoring_features AS (
    SELECT
        member_id,
        prediction_date,
        previous_goal_streak_as_of,
        previous_failed_goals_as_of
    FROM
        `vitality_engagement_dev.engagement_modeling_split`
    WHERE
        dataset_split = 'scoring'
),
training_features AS (
    SELECT
        previous_goal_streak_as_of,
        previous_failed_goals_as_of
    FROM
        `vitality_engagement_dev.engagement_modeling_split`
    WHERE
        dataset_split = 'train'
),
prediction_key_stats AS (
    SELECT
        COALESCE(
            SUM(key_row_count - 1),
            0
        ) AS duplicate_key_count
    FROM (
        SELECT
            member_id,
            prediction_date,
            COUNT(*) AS key_row_count
        FROM
            scoring_predictions
        GROUP BY
            member_id,
            prediction_date
    )
),
prediction_stats AS (
    SELECT
        COUNT(*) AS prediction_row_count,
        COUNT(DISTINCT member_id) AS prediction_member_count,
        COUNT(DISTINCT prediction_date) AS prediction_day_count,
        MAX(prediction_date) AS latest_prediction_date,

        (
            SELECT duplicate_key_count
            FROM prediction_key_stats
        ) AS duplicate_key_count,

        COUNTIF(
            predicted_probability IS NULL
        ) AS null_probability_count,

        COUNTIF(
            predicted_probability NOT BETWEEN 0.0 AND 1.0
        ) AS out_of_range_probability_count,

        COUNTIF(
            predicted_high_risk
                IS DISTINCT FROM (
                    predicted_probability >= 0.467
                )
        ) AS threshold_mismatch_count

    FROM
        scoring_predictions
),
scoring_feature_stats AS (
    SELECT
        COUNT(*) AS scoring_feature_row_count,
        COUNT(DISTINCT member_id) AS scoring_feature_member_count,
        COUNT(DISTINCT prediction_date) AS scoring_feature_day_count,
        MAX(prediction_date) AS latest_scoring_feature_date,
        MAX(previous_goal_streak_as_of) AS scoring_goal_streak_max,
        MAX(previous_failed_goals_as_of) AS scoring_failed_goals_max
    FROM
        scoring_features
),
training_support AS (
    SELECT
        MAX(previous_goal_streak_as_of) AS training_goal_streak_max,
        MAX(previous_failed_goals_as_of) AS training_failed_goals_max
    FROM
        training_features
),
support_breaches AS (
    SELECT
        COUNTIF(
            scoring_features.previous_goal_streak_as_of
                > training_support.training_goal_streak_max
        ) AS goal_streak_support_breach_count,

        COUNTIF(
            scoring_features.previous_failed_goals_as_of
                > training_support.training_failed_goals_max
        ) AS failed_goals_support_breach_count

    FROM
        scoring_features
    CROSS JOIN
        training_support
),
checks AS (
    SELECT
        1 AS display_order,
        'scoring_row_count' AS check_name,
        'scoring_volume' AS check_type,
        CAST(
            prediction_stats.prediction_row_count
            AS FLOAT64
        ) AS observed_value,
        3500.0 AS expected_value,
        CAST(NULL AS FLOAT64) AS warning_threshold,
        3500.0 AS critical_threshold,

        CASE
            WHEN prediction_stats.prediction_row_count = 3500
                THEN 'pass'
            ELSE 'critical'
        END AS severity,

        'Expected 3,500 synthetic scoring rows for the governed seven-day snapshot'
            AS details

    FROM
        prediction_stats

    UNION ALL

    SELECT
        2,
        'scoring_member_count',
        'scoring_volume',
        CAST(
            prediction_stats.prediction_member_count
            AS FLOAT64
        ),
        500.0,
        CAST(NULL AS FLOAT64),
        500.0,

        CASE
            WHEN prediction_stats.prediction_member_count = 500
                THEN 'pass'
            ELSE 'critical'
        END,

        'Expected 500 distinct synthetic members in the scoring snapshot'

    FROM
        prediction_stats

    UNION ALL

    SELECT
        3,
        'scoring_day_count',
        'scoring_volume',
        CAST(
            prediction_stats.prediction_day_count
            AS FLOAT64
        ),
        7.0,
        CAST(NULL AS FLOAT64),
        7.0,

        CASE
            WHEN prediction_stats.prediction_day_count = 7
                THEN 'pass'
            ELSE 'critical'
        END,

        'Expected seven distinct scoring dates from 2025-06-23 through 2025-06-29'

    FROM
        prediction_stats

    UNION ALL

    SELECT
        4,
        'scoring_duplicate_member_date_count',
        'schema_identity',
        CAST(
            prediction_stats.duplicate_key_count
            AS FLOAT64
        ),
        0.0,
        CAST(NULL AS FLOAT64),
        1.0,

        CASE
            WHEN prediction_stats.duplicate_key_count = 0
                THEN 'pass'
            ELSE 'critical'
        END,

        'Each synthetic member and prediction date must identify exactly one score'

    FROM
        prediction_stats

    UNION ALL

    SELECT
        5,
        'null_probability_count',
        'schema_identity',
        CAST(
            prediction_stats.null_probability_count
            AS FLOAT64
        ),
        0.0,
        CAST(NULL AS FLOAT64),
        1.0,

        CASE
            WHEN prediction_stats.null_probability_count = 0
                THEN 'pass'
            ELSE 'critical'
        END,

        'Predicted probabilities must not be null'

    FROM
        prediction_stats

    UNION ALL

    SELECT
        6,
        'out_of_range_probability_count',
        'schema_identity',
        CAST(
            prediction_stats.out_of_range_probability_count
            AS FLOAT64
        ),
        0.0,
        CAST(NULL AS FLOAT64),
        1.0,

        CASE
            WHEN prediction_stats.out_of_range_probability_count = 0
                THEN 'pass'
            ELSE 'critical'
        END,

        'Predicted probabilities must remain between zero and one'

    FROM
        prediction_stats

    UNION ALL

    SELECT
        7,
        'bigquery_threshold_reconciliation_count',
        'threshold_identity',
        CAST(
            prediction_stats.threshold_mismatch_count
            AS FLOAT64
        ),
        0.0,
        CAST(NULL AS FLOAT64),
        1.0,

        CASE
            WHEN prediction_stats.threshold_mismatch_count = 0
                THEN 'pass'
            ELSE 'critical'
        END,

        'BigQuery predicted_high_risk must reconcile to the frozen 0.467 warehouse threshold'

    FROM
        prediction_stats

    UNION ALL

    SELECT
        8,
        'scoring_source_row_reconciliation',
        'schema_identity',
        CAST(
            prediction_stats.prediction_row_count
                - scoring_feature_stats.scoring_feature_row_count
            AS FLOAT64
        ),
        0.0,
        CAST(NULL AS FLOAT64),
        1.0,

        CASE
            WHEN prediction_stats.prediction_row_count
                = scoring_feature_stats.scoring_feature_row_count
                THEN 'pass'
            ELSE 'critical'
        END,

        'Scoring predictions must reconcile one-to-one with the governed scoring split'

    FROM
        prediction_stats
    CROSS JOIN
        scoring_feature_stats

    UNION ALL

    SELECT
        9,
        'latest_scoring_business_date',
        'source_freshness',
        CAST(
            FORMAT_DATE(
                '%Y%m%d',
                prediction_stats.latest_prediction_date
            )
            AS FLOAT64
        ),
        20250629.0,
        CAST(NULL AS FLOAT64),
        20250629.0,

        CASE
            WHEN prediction_stats.latest_prediction_date
                = DATE '2025-06-29'
                AND scoring_feature_stats.latest_scoring_feature_date
                    = DATE '2025-06-29'
                THEN 'pass'
            ELSE 'critical'
        END,

        'This repository contains a governed historical synthetic snapshot ending 2025-06-29, not a live feed'

    FROM
        prediction_stats
    CROSS JOIN
        scoring_feature_stats

    UNION ALL

    SELECT
        10,
        'previous_goal_streak_training_support_breach_count',
        'numeric_feature_drift',
        CAST(
            support_breaches.goal_streak_support_breach_count
            AS FLOAT64
        ),
        0.0,
        0.0,
        1.0,

        CASE
            WHEN support_breaches.goal_streak_support_breach_count = 0
                THEN 'pass'
            ELSE 'critical'
        END,

        CONCAT(
            'Scoring values above the training maximum indicate extrapolation risk; training max=',
            CAST(
                training_support.training_goal_streak_max
                AS STRING
            ),
            ', scoring max=',
            CAST(
                scoring_feature_stats.scoring_goal_streak_max
                AS STRING
            )
        )

    FROM
        support_breaches
    CROSS JOIN
        training_support
    CROSS JOIN
        scoring_feature_stats

    UNION ALL

    SELECT
        11,
        'previous_failed_goals_training_support_breach_count',
        'numeric_feature_drift',
        CAST(
            support_breaches.failed_goals_support_breach_count
            AS FLOAT64
        ),
        0.0,
        0.0,
        1.0,

        CASE
            WHEN support_breaches.failed_goals_support_breach_count = 0
                THEN 'pass'
            ELSE 'critical'
        END,

        CONCAT(
            'Scoring values above the training maximum indicate extrapolation risk; training max=',
            CAST(
                training_support.training_failed_goals_max
                AS STRING
            ),
            ', scoring max=',
            CAST(
                scoring_feature_stats.scoring_failed_goals_max
                AS STRING
            )
        )

    FROM
        support_breaches
    CROSS JOIN
        training_support
    CROSS JOIN
        scoring_feature_stats
),
evaluated AS (
    SELECT
        checks.*,

        CASE
            MAX(
                CASE checks.severity
                    WHEN 'critical' THEN 2
                    WHEN 'warning' THEN 1
                    ELSE 0
                END
            ) OVER ()
            WHEN 2 THEN 'critical'
            WHEN 1 THEN 'warning'
            ELSE 'pass'
        END AS overall_severity

    FROM
        checks
)
SELECT
    evaluated.*,
    'bigquery_logistic_baseline' AS model_name,
    0.467 AS model_threshold,
    TRUE AS synthetic_data,
    'fully_synthetic' AS data_classification,
    'model_monitoring' AS governance_metric_class,
    FALSE AS operational_action_authorised,
    'engagement_logistic_scoring_predictions,engagement_modeling_split'
        AS source_name,
    TIMESTAMP(
        DATE '2025-06-29'
    ) AS source_as_of,
    CURRENT_TIMESTAMP() AS view_refreshed_at,

    evaluated.severity != 'critical' AS is_valid,

    CASE
        WHEN evaluated.severity = 'critical'
            THEN evaluated.details
        ELSE NULL
    END AS invalid_reason

FROM
    evaluated;
