DECLARE metrics STRUCT<
    view_row_count INT64,
    distinct_view_count INT64,
    distinct_display_order_count INT64,
    passing_view_count INT64,
    invalid_definition_count INT64,
    invalid_row_count INT64,
    invalid_availability_count INT64,
    invalid_summary_count INT64,
    invalid_governance_count INT64,
    failed_quality_count INT64
>;

SET metrics = (
    WITH activation_source_state AS (
        SELECT
            (
                SELECT COUNT(*)
                FROM `vitality_engagement_dev.activation_runs`
            ) AS activation_run_count,

            (
                SELECT COUNT(*)
                FROM `vitality_engagement_dev.activation_decisions`
            ) AS activation_decision_count
    ),
    expected_view_counts AS (
        SELECT
            'dashboard_scoring_daily_summary'
                AS dashboard_view_name,
            (
                SELECT COUNT(*)
                FROM
                    `vitality_engagement_dev.dashboard_scoring_daily_summary`
            ) AS expected_view_row_count

        UNION ALL

        SELECT
            'dashboard_risk_distribution',
            (
                SELECT COUNT(*)
                FROM
                    `vitality_engagement_dev.dashboard_risk_distribution`
            )

        UNION ALL

        SELECT
            'dashboard_observed_outcome_summary',
            (
                SELECT COUNT(*)
                FROM
                    `vitality_engagement_dev.dashboard_observed_outcome_summary`
            )

        UNION ALL

        SELECT
            'dashboard_activation_run_summary',
            (
                SELECT COUNT(*)
                FROM
                    `vitality_engagement_dev.dashboard_activation_run_summary`
            )

        UNION ALL

        SELECT
            'dashboard_activation_outcome_summary',
            (
                SELECT COUNT(*)
                FROM
                    `vitality_engagement_dev.dashboard_activation_outcome_summary`
            )

        UNION ALL

        SELECT
            'dashboard_activation_reason_summary',
            (
                SELECT COUNT(*)
                FROM
                    `vitality_engagement_dev.dashboard_activation_reason_summary`
            )

        UNION ALL

        SELECT
            'dashboard_review_selection_summary',
            (
                SELECT COUNT(*)
                FROM
                    `vitality_engagement_dev.dashboard_review_selection_summary`
            )

        UNION ALL

        SELECT
            'dashboard_lineage_freshness_summary',
            (
                SELECT COUNT(*)
                FROM
                    `vitality_engagement_dev.dashboard_lineage_freshness_summary`
            )
    ),
    view_metrics AS (
        SELECT
            COUNT(*) AS view_row_count,

            COUNT(
                DISTINCT quality.dashboard_view_name
            ) AS distinct_view_count,

            COUNT(
                DISTINCT quality.display_order
            ) AS distinct_display_order_count,

            COUNTIF(
                quality.quality_status = 'pass'
            ) AS passing_view_count,

            COUNTIF(
                CASE quality.dashboard_view_name
                    WHEN 'dashboard_scoring_daily_summary'
                        THEN NOT (
                            quality.display_order = 1
                            AND quality.dashboard_label
                                = 'Daily scoring summary'
                            AND quality.metric_class = 'forecast'
                        )
                    WHEN 'dashboard_risk_distribution'
                        THEN NOT (
                            quality.display_order = 2
                            AND quality.dashboard_label
                                = 'Risk distribution'
                            AND quality.metric_class = 'forecast'
                        )
                    WHEN 'dashboard_observed_outcome_summary'
                        THEN NOT (
                            quality.display_order = 3
                            AND quality.dashboard_label
                                = 'Observed outcome summary'
                            AND quality.metric_class = 'observed_outcome'
                        )
                    WHEN 'dashboard_activation_run_summary'
                        THEN NOT (
                            quality.display_order = 4
                            AND quality.dashboard_label
                                = 'Activation run summary'
                            AND quality.metric_class = 'activation_audit'
                        )
                    WHEN 'dashboard_activation_outcome_summary'
                        THEN NOT (
                            quality.display_order = 5
                            AND quality.dashboard_label
                                = 'Activation outcome summary'
                            AND quality.metric_class = 'activation_audit'
                        )
                    WHEN 'dashboard_activation_reason_summary'
                        THEN NOT (
                            quality.display_order = 6
                            AND quality.dashboard_label
                                = 'Activation reason summary'
                            AND quality.metric_class = 'activation_audit'
                        )
                    WHEN 'dashboard_review_selection_summary'
                        THEN NOT (
                            quality.display_order = 7
                            AND quality.dashboard_label
                                = 'Review selection summary'
                            AND quality.metric_class = 'activation_audit'
                        )
                    WHEN 'dashboard_lineage_freshness_summary'
                        THEN NOT (
                            quality.display_order = 8
                            AND quality.dashboard_label
                                = 'Lineage and freshness summary'
                            AND quality.metric_class = 'lineage'
                        )
                    ELSE TRUE
                END
            ) AS invalid_definition_count,

            COUNTIF(
                quality.view_row_count
                    != expected_view_counts.expected_view_row_count
                OR quality.view_row_count <= 0
                OR quality.invalid_row_count != 0
                OR quality.invalid_reason_count != 0
                OR quality.invalid_governance_metadata_count != 0
            ) AS invalid_row_count,

            COUNTIF(
                CASE quality.dashboard_view_name
                    WHEN 'dashboard_scoring_daily_summary'
                        THEN quality.availability_status != 'available'
                            OR quality.freshness_status
                                != 'historical_snapshot'
                    WHEN 'dashboard_risk_distribution'
                        THEN quality.availability_status != 'available'
                            OR quality.freshness_status
                                != 'historical_snapshot'
                    WHEN 'dashboard_observed_outcome_summary'
                        THEN quality.availability_status != 'available'
                            OR quality.freshness_status
                                != 'historical_snapshot'
                    WHEN 'dashboard_activation_run_summary'
                        THEN (
                            activation_source_state.activation_run_count = 0
                            AND (
                                quality.availability_status != 'empty'
                                OR quality.freshness_status != 'empty'
                            )
                        )
                        OR (
                            activation_source_state.activation_run_count > 0
                            AND (
                                quality.availability_status != 'available'
                                OR quality.freshness_status != 'available'
                            )
                        )
                    WHEN 'dashboard_activation_outcome_summary'
                        THEN (
                            activation_source_state.activation_run_count = 0
                            AND activation_source_state.activation_decision_count = 0
                            AND (
                                quality.availability_status != 'empty'
                                OR quality.freshness_status != 'empty'
                            )
                        )
                        OR (
                            (
                                activation_source_state.activation_run_count > 0
                                OR activation_source_state.activation_decision_count > 0
                            )
                            AND (
                                quality.availability_status != 'available'
                                OR quality.freshness_status != 'available'
                            )
                        )
                    WHEN 'dashboard_activation_reason_summary'
                        THEN (
                            activation_source_state.activation_run_count = 0
                            AND activation_source_state.activation_decision_count = 0
                            AND (
                                quality.availability_status != 'empty'
                                OR quality.freshness_status != 'empty'
                            )
                        )
                        OR (
                            (
                                activation_source_state.activation_run_count > 0
                                OR activation_source_state.activation_decision_count > 0
                            )
                            AND (
                                quality.availability_status != 'available'
                                OR quality.freshness_status != 'available'
                            )
                        )
                    WHEN 'dashboard_review_selection_summary'
                        THEN (
                            activation_source_state.activation_run_count = 0
                            AND activation_source_state.activation_decision_count = 0
                            AND (
                                quality.availability_status != 'empty'
                                OR quality.freshness_status != 'empty'
                            )
                        )
                        OR (
                            (
                                activation_source_state.activation_run_count > 0
                                OR activation_source_state.activation_decision_count > 0
                            )
                            AND (
                                quality.availability_status != 'available'
                                OR quality.freshness_status != 'available'
                            )
                        )
                    WHEN 'dashboard_lineage_freshness_summary'
                        THEN quality.availability_status != 'available'
                            OR quality.freshness_status != 'available'
                    ELSE TRUE
                END
            ) AS invalid_availability_count,

            COUNTIF(
                quality.quality_status = 'pass'
                AND (
                    (
                        quality.availability_status = 'empty'
                        AND quality.quality_summary
                            != 'Valid governed empty state'
                    )
                    OR (
                        quality.availability_status != 'empty'
                        AND quality.quality_summary
                            != 'All governed quality checks passed'
                    )
                )
            ) AS invalid_summary_count,

            COUNTIF(
                quality.lineage_status != 'complete'
                OR quality.synthetic_data IS DISTINCT FROM TRUE
                OR quality.data_classification != 'fully_synthetic'
                OR quality.governance_metric_class != 'data_quality'
                OR quality.operational_action_authorised
                    IS DISTINCT FROM FALSE
                OR quality.view_refreshed_at IS NULL
            ) AS invalid_governance_count,

            COUNTIF(
                quality.quality_status != 'pass'
                OR quality.quality_failure_reason IS NOT NULL
                OR quality.is_valid IS DISTINCT FROM TRUE
                OR quality.invalid_reason IS NOT NULL
            ) AS failed_quality_count

        FROM
            `vitality_engagement_dev.dashboard_quality_status`
            AS quality
        JOIN
            expected_view_counts
            USING (dashboard_view_name)
        CROSS JOIN
            activation_source_state
    )
    SELECT AS STRUCT
        view_metrics.view_row_count,
        view_metrics.distinct_view_count,
        view_metrics.distinct_display_order_count,
        view_metrics.passing_view_count,
        view_metrics.invalid_definition_count,
        view_metrics.invalid_row_count,
        view_metrics.invalid_availability_count,
        view_metrics.invalid_summary_count,
        view_metrics.invalid_governance_count,
        view_metrics.failed_quality_count
    FROM
        view_metrics
);

ASSERT metrics.view_row_count = 8
AS 'Dashboard quality status does not contain exactly eight governed assets';

ASSERT metrics.distinct_view_count = 8
AS 'Dashboard quality status contains duplicate or missing view names';

ASSERT metrics.distinct_display_order_count = 8
AS 'Dashboard quality status contains duplicate display-order values';

ASSERT metrics.passing_view_count = 8
AS 'One or more governed dashboard assets did not pass quality checks';

ASSERT metrics.invalid_definition_count = 0
AS 'Dashboard quality definitions do not match the governed asset inventory';

ASSERT metrics.invalid_row_count = 0
AS 'Dashboard quality row counts or embedded validation counts are invalid';

ASSERT metrics.invalid_availability_count = 0
AS 'Dashboard availability or freshness status does not match its source state';

ASSERT metrics.invalid_summary_count = 0
AS 'Dashboard quality summaries do not match their governed availability state';

ASSERT metrics.invalid_governance_count = 0
AS 'Dashboard quality governance metadata or operational authority is invalid';

ASSERT metrics.failed_quality_count = 0
AS 'Dashboard quality-status rows failed their embedded validation';
