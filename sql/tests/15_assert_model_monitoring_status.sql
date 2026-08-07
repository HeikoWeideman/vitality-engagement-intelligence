DECLARE metrics STRUCT<
    check_row_count INT64,
    distinct_check_count INT64,
    distinct_display_order_count INT64,
    pass_count INT64,
    warning_count INT64,
    critical_count INT64,
    invalid_definition_count INT64,
    invalid_value_count INT64,
    invalid_severity_count INT64,
    invalid_governance_count INT64,
    invalid_embedded_status_count INT64
>;

SET metrics = (
    WITH monitoring AS (
        SELECT *
        FROM
            `vitality_engagement_dev.model_monitoring_status`
    ),
    evaluated AS (
        SELECT
            COUNT(*) AS check_row_count,

            COUNT(
                DISTINCT check_name
            ) AS distinct_check_count,

            COUNT(
                DISTINCT display_order
            ) AS distinct_display_order_count,

            COUNTIF(
                severity = 'pass'
            ) AS pass_count,

            COUNTIF(
                severity = 'warning'
            ) AS warning_count,

            COUNTIF(
                severity = 'critical'
            ) AS critical_count,

            COUNTIF(
                CASE check_name
                    WHEN 'scoring_row_count'
                        THEN NOT (
                            display_order = 1
                            AND check_type = 'scoring_volume'
                            AND expected_value = 3500.0
                        )
                    WHEN 'scoring_member_count'
                        THEN NOT (
                            display_order = 2
                            AND check_type = 'scoring_volume'
                            AND expected_value = 500.0
                        )
                    WHEN 'scoring_day_count'
                        THEN NOT (
                            display_order = 3
                            AND check_type = 'scoring_volume'
                            AND expected_value = 7.0
                        )
                    WHEN 'scoring_duplicate_member_date_count'
                        THEN NOT (
                            display_order = 4
                            AND check_type = 'schema_identity'
                            AND expected_value = 0.0
                        )
                    WHEN 'null_probability_count'
                        THEN NOT (
                            display_order = 5
                            AND check_type = 'schema_identity'
                            AND expected_value = 0.0
                        )
                    WHEN 'out_of_range_probability_count'
                        THEN NOT (
                            display_order = 6
                            AND check_type = 'schema_identity'
                            AND expected_value = 0.0
                        )
                    WHEN 'bigquery_threshold_reconciliation_count'
                        THEN NOT (
                            display_order = 7
                            AND check_type = 'threshold_identity'
                            AND expected_value = 0.0
                        )
                    WHEN 'scoring_source_row_reconciliation'
                        THEN NOT (
                            display_order = 8
                            AND check_type = 'schema_identity'
                            AND expected_value = 0.0
                        )
                    WHEN 'latest_scoring_business_date'
                        THEN NOT (
                            display_order = 9
                            AND check_type = 'source_freshness'
                            AND expected_value = 20250629.0
                        )
                    WHEN
                        'previous_goal_streak_training_support_breach_count'
                        THEN NOT (
                            display_order = 10
                            AND check_type = 'numeric_feature_drift'
                            AND expected_value = 0.0
                        )
                    WHEN
                        'previous_failed_goals_training_support_breach_count'
                        THEN NOT (
                            display_order = 11
                            AND check_type = 'numeric_feature_drift'
                            AND expected_value = 0.0
                        )
                    ELSE TRUE
                END
            ) AS invalid_definition_count,

            COUNTIF(
                CASE check_name
                    WHEN 'scoring_row_count'
                        THEN observed_value != 3500.0
                    WHEN 'scoring_member_count'
                        THEN observed_value != 500.0
                    WHEN 'scoring_day_count'
                        THEN observed_value != 7.0
                    WHEN 'scoring_duplicate_member_date_count'
                        THEN observed_value != 0.0
                    WHEN 'null_probability_count'
                        THEN observed_value != 0.0
                    WHEN 'out_of_range_probability_count'
                        THEN observed_value != 0.0
                    WHEN 'bigquery_threshold_reconciliation_count'
                        THEN observed_value != 0.0
                    WHEN 'scoring_source_row_reconciliation'
                        THEN observed_value != 0.0
                    WHEN 'latest_scoring_business_date'
                        THEN observed_value != 20250629.0
                    WHEN
                        'previous_goal_streak_training_support_breach_count'
                        THEN observed_value <= 0.0
                    WHEN
                        'previous_failed_goals_training_support_breach_count'
                        THEN observed_value <= 0.0
                    ELSE TRUE
                END
            ) AS invalid_value_count,

            COUNTIF(
                CASE check_name
                    WHEN
                        'previous_goal_streak_training_support_breach_count'
                        THEN severity != 'critical'
                    WHEN
                        'previous_failed_goals_training_support_breach_count'
                        THEN severity != 'critical'
                    ELSE severity != 'pass'
                END
                OR overall_severity != 'critical'
            ) AS invalid_severity_count,

            COUNTIF(
                model_name != 'bigquery_logistic_baseline'
                OR model_threshold != 0.467
                OR synthetic_data IS DISTINCT FROM TRUE
                OR data_classification != 'fully_synthetic'
                OR governance_metric_class != 'model_monitoring'
                OR operational_action_authorised IS DISTINCT FROM FALSE
                OR source_name
                    != 'engagement_logistic_scoring_predictions,engagement_modeling_split'
                OR source_as_of
                    != TIMESTAMP(
                        DATE '2025-06-29'
                    )
                OR view_refreshed_at IS NULL
                OR details IS NULL
                OR TRIM(details) = ''
            ) AS invalid_governance_count,

            COUNTIF(
                (
                    severity = 'critical'
                    AND (
                        is_valid IS DISTINCT FROM FALSE
                        OR invalid_reason IS NULL
                    )
                )
                OR (
                    severity != 'critical'
                    AND (
                        is_valid IS DISTINCT FROM TRUE
                        OR invalid_reason IS NOT NULL
                    )
                )
            ) AS invalid_embedded_status_count

        FROM
            monitoring
    )
    SELECT AS STRUCT
        evaluated.check_row_count,
        evaluated.distinct_check_count,
        evaluated.distinct_display_order_count,
        evaluated.pass_count,
        evaluated.warning_count,
        evaluated.critical_count,
        evaluated.invalid_definition_count,
        evaluated.invalid_value_count,
        evaluated.invalid_severity_count,
        evaluated.invalid_governance_count,
        evaluated.invalid_embedded_status_count
    FROM
        evaluated
);

ASSERT metrics.check_row_count = 11
AS 'Model monitoring status does not contain exactly eleven governed checks';

ASSERT metrics.distinct_check_count = 11
AS 'Model monitoring status contains duplicate or missing check names';

ASSERT metrics.distinct_display_order_count = 11
AS 'Model monitoring status contains duplicate display-order values';

ASSERT metrics.pass_count = 9
AS 'Unexpected number of passing BigQuery monitoring checks';

ASSERT metrics.warning_count = 0
AS 'The governed BigQuery monitoring contract does not expect warning checks';

ASSERT metrics.critical_count = 2
AS 'Expected two critical training-support findings in the synthetic snapshot';

ASSERT metrics.invalid_definition_count = 0
AS 'BigQuery monitoring definitions do not match the governed check inventory';

ASSERT metrics.invalid_value_count = 0
AS 'BigQuery monitoring observations do not match the governed snapshot';

ASSERT metrics.invalid_severity_count = 0
AS 'BigQuery monitoring severities do not match their governed observations';

ASSERT metrics.invalid_governance_count = 0
AS 'BigQuery monitoring model identity or governance metadata is invalid';

ASSERT metrics.invalid_embedded_status_count = 0
AS 'BigQuery monitoring rows failed embedded validity reconciliation';
