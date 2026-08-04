DECLARE metrics STRUCT<
    source_run_count INT64,
    view_row_count INT64,
    empty_state_count INT64,
    invalid_empty_state_count INT64,
    governed_run_count INT64,
    invalid_reconciliation_count INT64,
    invalid_capacity_count INT64,
    invalid_metadata_count INT64,
    failed_quality_count INT64
>;

SET metrics = (
    WITH source_metrics AS (
        SELECT
            COUNT(*) AS source_run_count
        FROM
            `vitality_engagement_dev.activation_runs`
    ),
    view_metrics AS (
        SELECT
            COUNT(*) AS view_row_count,

            COUNTIF(
                run_id IS NULL
            ) AS empty_state_count,

            COUNTIF(
                run_id IS NULL
                AND (
                    policy_version IS NOT NULL
                    OR model_name IS NOT NULL
                    OR threshold IS NOT NULL
                    OR decision_timestamp IS NOT NULL
                    OR contact_context_snapshot_timestamp IS NOT NULL
                    OR ingested_at IS NOT NULL
                    OR capacity_limit != 0
                    OR source_row_count != 0
                    OR source_member_count != 0
                    OR superseded_count != 0
                    OR below_threshold_count != 0
                    OR excluded_count != 0
                    OR suppressed_count != 0
                    OR eligible_count != 0
                    OR capacity_not_selected_count != 0
                    OR selected_count != 0
                    OR capacity_utilisation_rate IS NOT NULL
                    OR reconciled_decision_count != 0
                    OR freshness_status != 'empty'
                )
            ) AS invalid_empty_state_count,

            COUNTIF(
                run_id IS NOT NULL
            ) AS governed_run_count,

            COUNTIF(
                run_id IS NOT NULL
                AND (
                    reconciled_decision_count != source_row_count
                    OR eligible_count
                        != selected_count + capacity_not_selected_count
                    OR source_member_count
                        != source_row_count - superseded_count
                )
            ) AS invalid_reconciliation_count,

            COUNTIF(
                run_id IS NOT NULL
                AND (
                    capacity_limit <= 0
                    OR selected_count > capacity_limit
                    OR capacity_utilisation_rate
                        IS DISTINCT FROM
                        SAFE_DIVIDE(
                            selected_count,
                            capacity_limit
                        )
                )
            ) AS invalid_capacity_count,

            COUNTIF(
                synthetic_data IS DISTINCT FROM TRUE
                OR data_classification != 'fully_synthetic'
                OR metric_class != 'activation_audit'
                OR source_name != 'activation_runs'
                OR view_refreshed_at IS NULL
                OR freshness_status NOT IN (
                    'current',
                    'empty'
                )
            ) AS invalid_metadata_count,

            COUNTIF(
                is_valid IS DISTINCT FROM TRUE
                OR invalid_reason IS NOT NULL
            ) AS failed_quality_count

        FROM
            `vitality_engagement_dev.dashboard_activation_run_summary`
    )
    SELECT AS STRUCT
        source_metrics.source_run_count,
        view_metrics.view_row_count,
        view_metrics.empty_state_count,
        view_metrics.invalid_empty_state_count,
        view_metrics.governed_run_count,
        view_metrics.invalid_reconciliation_count,
        view_metrics.invalid_capacity_count,
        view_metrics.invalid_metadata_count,
        view_metrics.failed_quality_count
    FROM
        source_metrics
    CROSS JOIN
        view_metrics
);

ASSERT (
    metrics.source_run_count > 0
    AND metrics.view_row_count = metrics.source_run_count
    AND metrics.governed_run_count = metrics.source_run_count
    AND metrics.empty_state_count = 0
)
OR (
    metrics.source_run_count = 0
    AND metrics.view_row_count = 1
    AND metrics.governed_run_count = 0
    AND metrics.empty_state_count = 1
)
AS 'Activation dashboard row count does not match its governed source state';

ASSERT metrics.invalid_empty_state_count = 0
AS 'Activation dashboard empty state contains fabricated run data';

ASSERT metrics.invalid_reconciliation_count = 0
AS 'Activation dashboard run counts do not reconcile';

ASSERT metrics.invalid_capacity_count = 0
AS 'Activation dashboard capacity metrics are invalid';

ASSERT metrics.invalid_metadata_count = 0
AS 'Activation dashboard governance metadata is invalid';

ASSERT metrics.failed_quality_count = 0
AS 'Activation dashboard rows failed their embedded quality status';
