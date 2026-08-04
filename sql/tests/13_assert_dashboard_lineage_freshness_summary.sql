DECLARE metrics STRUCT<
    view_row_count INT64,
    distinct_view_count INT64,
    distinct_display_order_count INT64,
    invalid_definition_count INT64,
    invalid_source_count INT64,
    invalid_freshness_count INT64,
    invalid_metadata_count INT64,
    failed_quality_count INT64
>;

SET metrics = (
    WITH source_metrics AS (
        SELECT
            (
                SELECT COUNT(*)
                FROM `vitality_engagement_dev.engagement_logistic_scoring_predictions`
            ) AS scoring_row_count,

            (
                SELECT MAX(prediction_date)
                FROM `vitality_engagement_dev.engagement_logistic_scoring_predictions`
            ) AS scoring_latest_date,

            (
                SELECT COUNT(*)
                FROM `vitality_engagement_dev.engagement_features_28d`
            ) AS feature_row_count,

            (
                SELECT MAX(prediction_date)
                FROM `vitality_engagement_dev.engagement_features_28d`
            ) AS feature_latest_date,

            (
                SELECT COUNT(*)
                FROM `vitality_engagement_dev.activation_runs`
            ) AS activation_run_count,

            (
                SELECT COUNT(*)
                FROM `vitality_engagement_dev.activation_decisions`
            ) AS activation_decision_count
    ),
    view_metrics AS (
        SELECT
            COUNT(*) AS view_row_count,

            COUNT(
                DISTINCT dashboard_view_name
            ) AS distinct_view_count,

            COUNT(
                DISTINCT display_order
            ) AS distinct_display_order_count,

            COUNTIF(
                CASE dashboard_view_name
                    WHEN 'dashboard_scoring_daily_summary'
                        THEN NOT (
                            display_order = 1
                            AND metric_class = 'forecast'
                            AND source_table_names
                                = 'engagement_logistic_scoring_predictions'
                            AND source_table_count = 1
                            AND lineage_type = 'direct_aggregate'
                        )
                    WHEN 'dashboard_risk_distribution'
                        THEN NOT (
                            display_order = 2
                            AND metric_class = 'forecast'
                            AND source_table_names
                                = 'engagement_logistic_scoring_predictions'
                            AND source_table_count = 1
                            AND lineage_type = 'direct_aggregate'
                        )
                    WHEN 'dashboard_observed_outcome_summary'
                        THEN NOT (
                            display_order = 3
                            AND metric_class = 'observed_outcome'
                            AND source_table_names = 'engagement_features_28d'
                            AND source_table_count = 1
                            AND lineage_type = 'filtered_aggregate'
                        )
                    WHEN 'dashboard_activation_run_summary'
                        THEN NOT (
                            display_order = 4
                            AND metric_class = 'activation_audit'
                            AND source_table_names = 'activation_runs'
                            AND source_table_count = 1
                            AND lineage_type = 'direct_aggregate'
                        )
                    WHEN 'dashboard_activation_outcome_summary'
                        THEN NOT (
                            display_order = 5
                            AND metric_class = 'activation_audit'
                            AND source_table_names
                                = 'activation_runs,activation_decisions'
                            AND source_table_count = 2
                            AND lineage_type = 'joined_dimension_aggregate'
                        )
                    WHEN 'dashboard_activation_reason_summary'
                        THEN NOT (
                            display_order = 6
                            AND metric_class = 'activation_audit'
                            AND source_table_names
                                = 'activation_runs,activation_decisions'
                            AND source_table_count = 2
                            AND lineage_type = 'joined_dimension_aggregate'
                        )
                    WHEN 'dashboard_review_selection_summary'
                        THEN NOT (
                            display_order = 7
                            AND metric_class = 'activation_audit'
                            AND source_table_names
                                = 'activation_runs,activation_decisions'
                            AND source_table_count = 2
                            AND lineage_type = 'filtered_dimension_aggregate'
                        )
                    ELSE TRUE
                END
            ) AS invalid_definition_count,

            COUNTIF(
                CASE dashboard_view_name
                    WHEN 'dashboard_scoring_daily_summary'
                        THEN source_row_count != source_metrics.scoring_row_count
                            OR latest_business_date
                                IS DISTINCT FROM source_metrics.scoring_latest_date
                    WHEN 'dashboard_risk_distribution'
                        THEN source_row_count != source_metrics.scoring_row_count
                            OR latest_business_date
                                IS DISTINCT FROM source_metrics.scoring_latest_date
                    WHEN 'dashboard_observed_outcome_summary'
                        THEN source_row_count != source_metrics.feature_row_count
                            OR latest_business_date
                                IS DISTINCT FROM source_metrics.feature_latest_date
                    WHEN 'dashboard_activation_run_summary'
                        THEN source_row_count
                            != source_metrics.activation_run_count
                    WHEN 'dashboard_activation_outcome_summary'
                        THEN source_row_count
                            != (
                                source_metrics.activation_run_count
                                + source_metrics.activation_decision_count
                            )
                    WHEN 'dashboard_activation_reason_summary'
                        THEN source_row_count
                            != (
                                source_metrics.activation_run_count
                                + source_metrics.activation_decision_count
                            )
                    WHEN 'dashboard_review_selection_summary'
                        THEN source_row_count
                            != (
                                source_metrics.activation_run_count
                                + source_metrics.activation_decision_count
                            )
                    ELSE TRUE
                END
                OR storage_row_count < 0
            ) AS invalid_source_count,

            COUNTIF(
                lineage_status != 'complete'
                OR CASE
                    WHEN metric_class IN (
                        'forecast',
                        'observed_outcome'
                    )
                        THEN freshness_status != 'historical_snapshot'
                            OR latest_business_date IS NULL
                            OR latest_source_timestamp IS NULL
                    WHEN metric_class = 'activation_audit'
                        AND source_row_count = 0
                        THEN freshness_status != 'empty'
                            OR latest_business_date IS NOT NULL
                            OR latest_source_timestamp IS NOT NULL
                    WHEN metric_class = 'activation_audit'
                        AND source_row_count > 0
                        THEN freshness_status != 'available'
                            OR latest_source_timestamp IS NULL
                    ELSE TRUE
                END
            ) AS invalid_freshness_count,

            COUNTIF(
                synthetic_data IS DISTINCT FROM TRUE
                OR data_classification != 'fully_synthetic'
                OR governance_metric_class != 'lineage'
                OR metadata_source
                    != 'BigQuery __TABLES__ metadata and governed source aggregates'
                OR view_refreshed_at IS NULL
                OR freshness_interpretation IS NULL
                OR TRIM(freshness_interpretation) = ''
            ) AS invalid_metadata_count,

            COUNTIF(
                is_valid IS DISTINCT FROM TRUE
                OR invalid_reason IS NOT NULL
            ) AS failed_quality_count

        FROM
            `vitality_engagement_dev.dashboard_lineage_freshness_summary`
        CROSS JOIN
            source_metrics
    )
    SELECT AS STRUCT
        view_metrics.view_row_count,
        view_metrics.distinct_view_count,
        view_metrics.distinct_display_order_count,
        view_metrics.invalid_definition_count,
        view_metrics.invalid_source_count,
        view_metrics.invalid_freshness_count,
        view_metrics.invalid_metadata_count,
        view_metrics.failed_quality_count
    FROM
        view_metrics
);

ASSERT metrics.view_row_count = 7
AS 'Dashboard lineage summary does not contain exactly seven governed views';

ASSERT metrics.distinct_view_count = 7
AS 'Dashboard lineage summary contains duplicate or missing view names';

ASSERT metrics.distinct_display_order_count = 7
AS 'Dashboard lineage summary contains duplicate display-order values';

ASSERT metrics.invalid_definition_count = 0
AS 'Dashboard lineage definitions do not match the governed view inventory';

ASSERT metrics.invalid_source_count = 0
AS 'Dashboard lineage source counts or business dates do not match their sources';

ASSERT metrics.invalid_freshness_count = 0
AS 'Dashboard lineage freshness states are inconsistent with their source states';

ASSERT metrics.invalid_metadata_count = 0
AS 'Dashboard lineage governance metadata is invalid';

ASSERT metrics.failed_quality_count = 0
AS 'Dashboard lineage rows failed their embedded quality status';
