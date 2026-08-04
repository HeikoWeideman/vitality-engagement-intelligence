DECLARE metrics STRUCT<
    source_run_count INT64,
    source_decision_count INT64,
    view_row_count INT64,
    governed_row_count INT64,
    empty_state_count INT64,
    distinct_intervention_count INT64,
    invalid_intervention_definition_count INT64,
    invalid_empty_state_count INT64,
    invalid_reconciliation_count INT64,
    invalid_governance_state_count INT64,
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
                DISTINCT intervention_category
            ) AS distinct_intervention_count,

            COUNTIF(
                CASE intervention_category
                    WHEN 'supportive_check_in'
                        THEN NOT (
                            display_order = 1
                            AND intervention_label = 'Supportive check-in'
                        )
                    WHEN 'goal_planning'
                        THEN NOT (
                            display_order = 2
                            AND intervention_label = 'Goal planning'
                        )
                    WHEN 'activity_reminder'
                        THEN NOT (
                            display_order = 3
                            AND intervention_label = 'Activity reminder'
                        )
                    WHEN 'rewards_education'
                        THEN NOT (
                            display_order = 4
                            AND intervention_label = 'Rewards education'
                        )
                    ELSE TRUE
                END
            ) AS invalid_intervention_definition_count,

            COUNTIF(
                run_id IS NULL
                AND (
                    policy_version IS NOT NULL
                    OR model_name IS NOT NULL
                    OR decision_timestamp IS NOT NULL
                    OR selection_count != 0
                    OR expected_selected_count != 0
                    OR recognised_selected_count != 0
                    OR selection_share IS NOT NULL
                    OR missing_intervention_category_count != 0
                    OR unexpected_intervention_category_count != 0
                    OR non_selected_with_intervention_count != 0
                    OR orphan_decision_count != 0
                    OR source_as_of IS NOT NULL
                    OR freshness_status != 'empty'
                )
            ) AS invalid_empty_state_count,

            COUNTIF(
                run_id IS NOT NULL
                AND (
                    recognised_selected_count != expected_selected_count
                    OR selection_count > expected_selected_count
                    OR missing_intervention_category_count != 0
                    OR unexpected_intervention_category_count != 0
                    OR non_selected_with_intervention_count != 0
                    OR orphan_decision_count != 0
                    OR (
                        expected_selected_count > 0
                        AND selection_share IS DISTINCT FROM SAFE_DIVIDE(
                            selection_count,
                            expected_selected_count
                        )
                    )
                    OR (
                        expected_selected_count = 0
                        AND selection_share IS NOT NULL
                    )
                )
            ) AS invalid_reconciliation_count,

            COUNTIF(
                review_state != 'pending_human_review'
                OR outreach_approval_state != 'not_approved_outreach'
                OR operational_action_authorised IS DISTINCT FROM FALSE
            ) AS invalid_governance_state_count,

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
            `vitality_engagement_dev.dashboard_review_selection_summary`
    )
    SELECT AS STRUCT
        source_metrics.source_run_count,
        source_metrics.source_decision_count,
        view_metrics.view_row_count,
        view_metrics.governed_row_count,
        view_metrics.empty_state_count,
        view_metrics.distinct_intervention_count,
        view_metrics.invalid_intervention_definition_count,
        view_metrics.invalid_empty_state_count,
        view_metrics.invalid_reconciliation_count,
        view_metrics.invalid_governance_state_count,
        view_metrics.invalid_metadata_count,
        view_metrics.failed_quality_count
    FROM
        source_metrics
    CROSS JOIN
        view_metrics
);

ASSERT metrics.distinct_intervention_count = 4
AS 'Review-selection dashboard does not contain exactly four governed intervention categories';

ASSERT metrics.invalid_intervention_definition_count = 0
AS 'Review-selection dashboard intervention definitions do not match the authoritative contract';

ASSERT (
    metrics.source_run_count > 0
    AND metrics.view_row_count = metrics.source_run_count * 4
    AND metrics.governed_row_count = metrics.source_run_count * 4
    AND metrics.empty_state_count = 0
)
OR (
    metrics.source_run_count = 0
    AND metrics.source_decision_count = 0
    AND metrics.view_row_count = 4
    AND metrics.governed_row_count = 0
    AND metrics.empty_state_count = 4
)
AS 'Review-selection dashboard rows do not match the governed source state';

ASSERT metrics.invalid_empty_state_count = 0
AS 'Review-selection dashboard empty state contains fabricated activation data';

ASSERT metrics.invalid_reconciliation_count = 0
AS 'Review-selection dashboard counts or shares do not reconcile';

ASSERT metrics.invalid_governance_state_count = 0
AS 'Review-selection dashboard incorrectly represents approval or operational authority';

ASSERT metrics.invalid_metadata_count = 0
AS 'Review-selection dashboard governance metadata is invalid';

ASSERT metrics.failed_quality_count = 0
AS 'Review-selection dashboard rows failed their embedded quality status';
