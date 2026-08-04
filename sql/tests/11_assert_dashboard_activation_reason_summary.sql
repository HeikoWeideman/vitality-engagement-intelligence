DECLARE metrics STRUCT<
    source_run_count INT64,
    source_decision_count INT64,
    view_row_count INT64,
    governed_row_count INT64,
    empty_state_count INT64,
    distinct_reason_count INT64,
    invalid_reason_definition_count INT64,
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
                DISTINCT reason_code
            ) AS distinct_reason_count,

            COUNTIF(
                CASE reason_code
                    WHEN 'selected_for_human_review'
                        THEN NOT (
                            display_order = 1
                            AND reason_label = 'Selected for human review'
                            AND outcome = 'selected_for_review'
                            AND outcome_label = 'Selected for review'
                            AND reason_group = 'review_selection'
                            AND is_selected_for_review
                            AND reason_semantics
                                = 'pending_human_review_not_approved_outreach'
                        )
                    WHEN 'superseded_by_latest_prediction'
                        THEN NOT (
                            display_order = 2
                            AND reason_label = 'Superseded by latest prediction'
                            AND outcome = 'no_contact_superseded'
                            AND outcome_label = 'No contact - superseded'
                            AND reason_group = 'superseded'
                            AND NOT is_selected_for_review
                            AND reason_semantics = 'explicit_no_contact'
                        )
                    WHEN 'below_frozen_threshold'
                        THEN NOT (
                            display_order = 3
                            AND reason_label = 'Below frozen threshold'
                            AND outcome = 'no_contact_below_threshold'
                            AND outcome_label = 'No contact - below threshold'
                            AND reason_group = 'below_threshold'
                            AND NOT is_selected_for_review
                            AND reason_semantics = 'explicit_no_contact'
                        )
                    WHEN 'missing_activation_context'
                        THEN NOT (
                            display_order = 4
                            AND outcome = 'no_contact_excluded'
                            AND reason_group = 'exclusion'
                        )
                    WHEN 'contact_not_permitted'
                        THEN NOT (
                            display_order = 5
                            AND outcome = 'no_contact_excluded'
                            AND reason_group = 'exclusion'
                        )
                    WHEN 'member_opted_out'
                        THEN NOT (
                            display_order = 6
                            AND outcome = 'no_contact_excluded'
                            AND reason_group = 'exclusion'
                        )
                    WHEN 'prediction_too_old'
                        THEN NOT (
                            display_order = 7
                            AND outcome = 'no_contact_suppressed'
                            AND reason_group = 'suppression'
                        )
                    WHEN 'active_case_open'
                        THEN NOT (
                            display_order = 8
                            AND outcome = 'no_contact_suppressed'
                            AND reason_group = 'suppression'
                        )
                    WHEN 'contact_cooldown_active'
                        THEN NOT (
                            display_order = 9
                            AND outcome = 'no_contact_suppressed'
                            AND reason_group = 'suppression'
                        )
                    WHEN 'prior_intervention_limit_reached'
                        THEN NOT (
                            display_order = 10
                            AND outcome = 'no_contact_suppressed'
                            AND reason_group = 'suppression'
                        )
                    WHEN 'capacity_limit_reached'
                        THEN NOT (
                            display_order = 11
                            AND reason_label = 'Capacity limit reached'
                            AND outcome = 'no_contact_capacity'
                            AND outcome_label = 'No contact - capacity'
                            AND reason_group = 'capacity'
                            AND NOT is_selected_for_review
                            AND reason_semantics = 'explicit_no_contact'
                        )
                    ELSE TRUE
                END
            ) AS invalid_reason_definition_count,

            COUNTIF(
                run_id IS NULL
                AND (
                    policy_version IS NOT NULL
                    OR model_name IS NOT NULL
                    OR decision_timestamp IS NOT NULL
                    OR reason_count != 0
                    OR outcome_reason_total_count != 0
                    OR expected_outcome_count != 0
                    OR total_decision_count != 0
                    OR reason_rate IS NOT NULL
                    OR within_outcome_rate IS NOT NULL
                    OR recognised_reason_count != 0
                    OR unexpected_reason_count != 0
                    OR invalid_outcome_reason_count != 0
                    OR orphan_decision_count != 0
                    OR source_as_of IS NOT NULL
                    OR freshness_status != 'empty'
                )
            ) AS invalid_empty_state_count,

            COUNTIF(
                run_id IS NOT NULL
                AND (
                    outcome_reason_total_count != expected_outcome_count
                    OR recognised_reason_count != total_decision_count
                    OR unexpected_reason_count != 0
                    OR invalid_outcome_reason_count != 0
                    OR orphan_decision_count != 0
                    OR (
                        total_decision_count > 0
                        AND reason_rate IS DISTINCT FROM SAFE_DIVIDE(
                            reason_count,
                            total_decision_count
                        )
                    )
                    OR (
                        total_decision_count = 0
                        AND reason_rate IS NOT NULL
                    )
                    OR (
                        expected_outcome_count > 0
                        AND within_outcome_rate IS DISTINCT FROM SAFE_DIVIDE(
                            reason_count,
                            expected_outcome_count
                        )
                    )
                    OR (
                        expected_outcome_count = 0
                        AND within_outcome_rate IS NOT NULL
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
            `vitality_engagement_dev.dashboard_activation_reason_summary`
    )
    SELECT AS STRUCT
        source_metrics.source_run_count,
        source_metrics.source_decision_count,
        view_metrics.view_row_count,
        view_metrics.governed_row_count,
        view_metrics.empty_state_count,
        view_metrics.distinct_reason_count,
        view_metrics.invalid_reason_definition_count,
        view_metrics.invalid_empty_state_count,
        view_metrics.invalid_reconciliation_count,
        view_metrics.invalid_metadata_count,
        view_metrics.failed_quality_count
    FROM
        source_metrics
    CROSS JOIN
        view_metrics
);

ASSERT metrics.distinct_reason_count = 11
AS 'Activation reason dashboard does not contain exactly 11 governed final reason codes';

ASSERT metrics.invalid_reason_definition_count = 0
AS 'Activation reason dashboard definitions do not match the authoritative contract';

ASSERT (
    metrics.source_run_count > 0
    AND metrics.view_row_count = metrics.source_run_count * 11
    AND metrics.governed_row_count = metrics.source_run_count * 11
    AND metrics.empty_state_count = 0
)
OR (
    metrics.source_run_count = 0
    AND metrics.source_decision_count = 0
    AND metrics.view_row_count = 11
    AND metrics.governed_row_count = 0
    AND metrics.empty_state_count = 11
)
AS 'Activation reason dashboard rows do not match the governed source state';

ASSERT metrics.invalid_empty_state_count = 0
AS 'Activation reason dashboard empty state contains fabricated activation data';

ASSERT metrics.invalid_reconciliation_count = 0
AS 'Activation reason dashboard counts or rates do not reconcile';

ASSERT metrics.invalid_metadata_count = 0
AS 'Activation reason dashboard governance metadata is invalid';

ASSERT metrics.failed_quality_count = 0
AS 'Activation reason dashboard rows failed their embedded quality status';
