DECLARE metrics STRUCT<
    source_run_count INT64,
    source_decision_count INT64,
    view_row_count INT64,
    governed_row_count INT64,
    empty_state_count INT64,
    distinct_outcome_count INT64,
    invalid_outcome_definition_count INT64,
    invalid_empty_state_count INT64,
    invalid_reconciliation_count INT64,
    invalid_metadata_count INT64,
    failed_quality_count INT64
>;

SET metrics = (
    WITH source_metrics AS (
        SELECT
            (
                SELECT COUNT(*)
                FROM `vitality_engagement_dev.activation_runs`
            ) AS source_run_count,

            (
                SELECT COUNT(*)
                FROM `vitality_engagement_dev.activation_decisions`
            ) AS source_decision_count
    ),
    view_metrics AS (
        SELECT
            COUNT(*) AS view_row_count,

            COUNTIF(
                run_id IS NOT NULL
            ) AS governed_row_count,

            COUNTIF(
                run_id IS NULL
            ) AS empty_state_count,

            COUNT(
                DISTINCT outcome
            ) AS distinct_outcome_count,

            COUNTIF(
                CASE outcome
                    WHEN 'selected_for_review'
                        THEN NOT (
                            display_order = 1
                            AND outcome_label = 'Selected for review'
                            AND is_selected_for_review
                            AND outcome_semantics
                                = 'pending_human_review_not_approved_outreach'
                        )
                    WHEN 'no_contact_superseded'
                        THEN NOT (
                            display_order = 2
                            AND outcome_label = 'No contact - superseded'
                            AND NOT is_selected_for_review
                            AND outcome_semantics = 'explicit_no_contact'
                        )
                    WHEN 'no_contact_below_threshold'
                        THEN NOT (
                            display_order = 3
                            AND outcome_label = 'No contact - below threshold'
                            AND NOT is_selected_for_review
                            AND outcome_semantics = 'explicit_no_contact'
                        )
                    WHEN 'no_contact_excluded'
                        THEN NOT (
                            display_order = 4
                            AND outcome_label = 'No contact - excluded'
                            AND NOT is_selected_for_review
                            AND outcome_semantics = 'explicit_no_contact'
                        )
                    WHEN 'no_contact_suppressed'
                        THEN NOT (
                            display_order = 5
                            AND outcome_label = 'No contact - suppressed'
                            AND NOT is_selected_for_review
                            AND outcome_semantics = 'explicit_no_contact'
                        )
                    WHEN 'no_contact_capacity'
                        THEN NOT (
                            display_order = 6
                            AND outcome_label = 'No contact - capacity'
                            AND NOT is_selected_for_review
                            AND outcome_semantics = 'explicit_no_contact'
                        )
                    ELSE TRUE
                END
            ) AS invalid_outcome_definition_count,

            COUNTIF(
                run_id IS NULL
                AND (
                    policy_version IS NOT NULL
                    OR model_name IS NOT NULL
                    OR decision_timestamp IS NOT NULL
                    OR decision_count != 0
                    OR expected_decision_count != 0
                    OR total_decision_count != 0
                    OR decision_rate IS NOT NULL
                    OR recognised_decision_count != 0
                    OR unexpected_decision_count != 0
                    OR orphan_decision_count != 0
                    OR source_as_of IS NOT NULL
                    OR freshness_status != 'empty'
                )
            ) AS invalid_empty_state_count,

            COUNTIF(
                run_id IS NOT NULL
                AND (
                    decision_count != expected_decision_count
                    OR recognised_decision_count != total_decision_count
                    OR unexpected_decision_count != 0
                    OR orphan_decision_count != 0
                    OR (
                        total_decision_count > 0
                        AND decision_rate IS DISTINCT FROM SAFE_DIVIDE(
                            decision_count,
                            total_decision_count
                        )
                    )
                    OR (
                        total_decision_count = 0
                        AND decision_rate IS NOT NULL
                    )
                )
            ) AS invalid_reconciliation_count,

            COUNTIF(
                synthetic_data IS DISTINCT FROM TRUE
                OR data_classification != 'fully_synthetic'
                OR metric_class != 'activation_audit'
                OR source_name != 'activation_decisions'
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
            `vitality_engagement_dev.dashboard_activation_outcome_summary`
    )
    SELECT AS STRUCT
        source_metrics.source_run_count,
        source_metrics.source_decision_count,
        view_metrics.view_row_count,
        view_metrics.governed_row_count,
        view_metrics.empty_state_count,
        view_metrics.distinct_outcome_count,
        view_metrics.invalid_outcome_definition_count,
        view_metrics.invalid_empty_state_count,
        view_metrics.invalid_reconciliation_count,
        view_metrics.invalid_metadata_count,
        view_metrics.failed_quality_count
    FROM
        source_metrics
    CROSS JOIN
        view_metrics
);

ASSERT metrics.distinct_outcome_count = 6
AS 'Activation dashboard does not contain exactly six governed outcomes';

ASSERT metrics.invalid_outcome_definition_count = 0
AS 'Activation dashboard outcome definitions do not match the authoritative contract';

ASSERT (
    metrics.source_run_count > 0
    AND metrics.view_row_count = metrics.source_run_count * 6
    AND metrics.governed_row_count = metrics.source_run_count * 6
    AND metrics.empty_state_count = 0
)
OR (
    metrics.source_run_count = 0
    AND metrics.source_decision_count = 0
    AND metrics.view_row_count = 6
    AND metrics.governed_row_count = 0
    AND metrics.empty_state_count = 6
)
AS 'Activation outcome dashboard rows do not match the governed source state';

ASSERT metrics.invalid_empty_state_count = 0
AS 'Activation outcome dashboard empty state contains fabricated activation data';

ASSERT metrics.invalid_reconciliation_count = 0
AS 'Activation outcome dashboard counts or rates do not reconcile';

ASSERT metrics.invalid_metadata_count = 0
AS 'Activation outcome dashboard governance metadata is invalid';

ASSERT metrics.failed_quality_count = 0
AS 'Activation outcome dashboard rows failed their embedded quality status';
