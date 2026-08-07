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
            `vitality_engagement_dev.governance_monitoring_status`
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
                    WHEN 'activation_empty_state_validity'
                        THEN NOT (
                            display_order = 1
                            AND check_type = 'activation_empty_state'
                            AND expected_value = 0.0
                            AND critical_threshold = 1.0
                        )
                    WHEN 'dashboard_quality_status'
                        THEN NOT (
                            display_order = 2
                            AND check_type = 'dashboard_quality'
                            AND expected_value = 0.0
                            AND critical_threshold = 1.0
                        )
                    WHEN 'dashboard_lineage_freshness_status'
                        THEN NOT (
                            display_order = 3
                            AND check_type = 'source_freshness'
                            AND expected_value = 0.0
                            AND critical_threshold = 1.0
                        )
                    ELSE TRUE
                END
            ) AS invalid_definition_count,

            COUNTIF(
                observed_value != 0.0
                OR expected_value != 0.0
            ) AS invalid_value_count,

            COUNTIF(
                severity != 'pass'
                OR overall_severity != 'pass'
            ) AS invalid_severity_count,

            COUNTIF(
                synthetic_data IS DISTINCT FROM TRUE
                OR data_classification != 'fully_synthetic'
                OR governance_metric_class
                    != 'governance_monitoring'
                OR operational_action_authorised
                    IS DISTINCT FROM FALSE
                OR source_name
                    != 'dashboard_quality_status,dashboard_lineage_freshness_summary,activation_runs,activation_decisions'
                OR source_as_of IS NULL
                OR view_refreshed_at IS NULL
                OR details IS NULL
                OR TRIM(details) = ''
            ) AS invalid_governance_count,

            COUNTIF(
                is_valid IS DISTINCT FROM TRUE
                OR invalid_reason IS NOT NULL
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

ASSERT metrics.check_row_count = 3
AS 'Governance monitoring status does not contain exactly three governed checks';

ASSERT metrics.distinct_check_count = 3
AS 'Governance monitoring status contains duplicate or missing check names';

ASSERT metrics.distinct_display_order_count = 3
AS 'Governance monitoring status contains duplicate display-order values';

ASSERT metrics.pass_count = 3
AS 'One or more governed governance-monitoring checks did not pass';

ASSERT metrics.warning_count = 0
AS 'Governance monitoring unexpectedly contains warning checks';

ASSERT metrics.critical_count = 0
AS 'Governance monitoring unexpectedly contains critical checks';

ASSERT metrics.invalid_definition_count = 0
AS 'Governance monitoring definitions do not match the governed inventory';

ASSERT metrics.invalid_value_count = 0
AS 'Governance monitoring observations do not match the governed source state';

ASSERT metrics.invalid_severity_count = 0
AS 'Governance monitoring severities do not match their observations';

ASSERT metrics.invalid_governance_count = 0
AS 'Governance monitoring metadata or operational authority is invalid';

ASSERT metrics.invalid_embedded_status_count = 0
AS 'Governance monitoring rows failed embedded validity reconciliation';
