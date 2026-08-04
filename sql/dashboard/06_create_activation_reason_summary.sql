CREATE OR REPLACE VIEW
    `vitality_engagement_dev.dashboard_activation_reason_summary`
OPTIONS (
    description = 'Read-only aggregate activation decision reasons with governed outcome mappings and a valid synthetic empty state.'
)
AS
WITH reason_dimension AS (
    SELECT *
    FROM UNNEST([
        STRUCT(
            1 AS display_order,
            'selected_for_human_review' AS reason_code,
            'Selected for human review' AS reason_label,
            'selected_for_review' AS outcome,
            'Selected for review' AS outcome_label,
            'review_selection' AS reason_group,
            TRUE AS is_selected_for_review,
            'pending_human_review_not_approved_outreach' AS reason_semantics
        ),
        STRUCT(
            2 AS display_order,
            'superseded_by_latest_prediction' AS reason_code,
            'Superseded by latest prediction' AS reason_label,
            'no_contact_superseded' AS outcome,
            'No contact - superseded' AS outcome_label,
            'superseded' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        ),
        STRUCT(
            3 AS display_order,
            'below_frozen_threshold' AS reason_code,
            'Below frozen threshold' AS reason_label,
            'no_contact_below_threshold' AS outcome,
            'No contact - below threshold' AS outcome_label,
            'below_threshold' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        ),
        STRUCT(
            4 AS display_order,
            'missing_activation_context' AS reason_code,
            'Missing activation context' AS reason_label,
            'no_contact_excluded' AS outcome,
            'No contact - excluded' AS outcome_label,
            'exclusion' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        ),
        STRUCT(
            5 AS display_order,
            'contact_not_permitted' AS reason_code,
            'Contact not permitted' AS reason_label,
            'no_contact_excluded' AS outcome,
            'No contact - excluded' AS outcome_label,
            'exclusion' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        ),
        STRUCT(
            6 AS display_order,
            'member_opted_out' AS reason_code,
            'Member opted out' AS reason_label,
            'no_contact_excluded' AS outcome,
            'No contact - excluded' AS outcome_label,
            'exclusion' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        ),
        STRUCT(
            7 AS display_order,
            'prediction_too_old' AS reason_code,
            'Prediction too old' AS reason_label,
            'no_contact_suppressed' AS outcome,
            'No contact - suppressed' AS outcome_label,
            'suppression' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        ),
        STRUCT(
            8 AS display_order,
            'active_case_open' AS reason_code,
            'Active case open' AS reason_label,
            'no_contact_suppressed' AS outcome,
            'No contact - suppressed' AS outcome_label,
            'suppression' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        ),
        STRUCT(
            9 AS display_order,
            'contact_cooldown_active' AS reason_code,
            'Contact cooldown active' AS reason_label,
            'no_contact_suppressed' AS outcome,
            'No contact - suppressed' AS outcome_label,
            'suppression' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        ),
        STRUCT(
            10 AS display_order,
            'prior_intervention_limit_reached' AS reason_code,
            'Prior intervention limit reached' AS reason_label,
            'no_contact_suppressed' AS outcome,
            'No contact - suppressed' AS outcome_label,
            'suppression' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        ),
        STRUCT(
            11 AS display_order,
            'capacity_limit_reached' AS reason_code,
            'Capacity limit reached' AS reason_label,
            'no_contact_capacity' AS outcome,
            'No contact - capacity' AS outcome_label,
            'capacity' AS reason_group,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS reason_semantics
        )
    ])
),
decision_counts AS (
    SELECT
        run_id,
        outcome,
        reason_code,
        COUNT(*) AS reason_count
    FROM
        `vitality_engagement_dev.activation_decisions`
    GROUP BY
        run_id,
        outcome,
        reason_code
),
mapped_decisions AS (
    SELECT
        activation_decisions.run_id,
        activation_decisions.outcome,
        activation_decisions.reason_code,
        reason_dimension.reason_code IS NOT NULL AS has_known_reason,
        reason_dimension.reason_code IS NOT NULL
            AND reason_dimension.outcome = activation_decisions.outcome
            AS has_valid_outcome_mapping
    FROM
        `vitality_engagement_dev.activation_decisions`
        AS activation_decisions
    LEFT JOIN
        reason_dimension
        ON activation_decisions.reason_code = reason_dimension.reason_code
),
run_reconciliation AS (
    SELECT
        run_id,

        COUNTIF(
            has_known_reason
            AND has_valid_outcome_mapping
        ) AS recognised_reason_count,

        COUNTIF(
            NOT has_known_reason
        ) AS unexpected_reason_count,

        COUNTIF(
            has_known_reason
            AND NOT has_valid_outcome_mapping
        ) AS invalid_outcome_reason_count

    FROM
        mapped_decisions
    GROUP BY
        run_id
),
outcome_reason_totals AS (
    SELECT
        mapped_decisions.run_id,
        mapped_decisions.outcome,
        COUNT(*) AS outcome_reason_total_count
    FROM
        mapped_decisions
    WHERE
        mapped_decisions.has_known_reason
        AND mapped_decisions.has_valid_outcome_mapping
    GROUP BY
        mapped_decisions.run_id,
        mapped_decisions.outcome
),
source_quality AS (
    SELECT
        COUNTIF(
            activation_runs.run_id IS NULL
        ) AS orphan_decision_count
    FROM
        `vitality_engagement_dev.activation_decisions`
        AS activation_decisions
    LEFT JOIN
        `vitality_engagement_dev.activation_runs`
        AS activation_runs
        USING (run_id)
),
governed_reasons AS (
    SELECT
        activation_runs.run_id,
        activation_runs.policy_version,
        activation_runs.model_name,
        activation_runs.decision_timestamp,

        reason_dimension.display_order,
        reason_dimension.reason_code,
        reason_dimension.reason_label,
        reason_dimension.outcome,
        reason_dimension.outcome_label,
        reason_dimension.reason_group,
        reason_dimension.is_selected_for_review,
        reason_dimension.reason_semantics,

        COALESCE(
            decision_counts.reason_count,
            0
        ) AS reason_count,

        COALESCE(
            outcome_reason_totals.outcome_reason_total_count,
            0
        ) AS outcome_reason_total_count,

        CASE reason_dimension.outcome
            WHEN 'selected_for_review'
                THEN activation_runs.selected_count
            WHEN 'no_contact_superseded'
                THEN activation_runs.superseded_count
            WHEN 'no_contact_below_threshold'
                THEN activation_runs.below_threshold_count
            WHEN 'no_contact_excluded'
                THEN activation_runs.excluded_count
            WHEN 'no_contact_suppressed'
                THEN activation_runs.suppressed_count
            WHEN 'no_contact_capacity'
                THEN activation_runs.capacity_not_selected_count
        END AS expected_outcome_count,

        activation_runs.source_row_count AS total_decision_count,

        SAFE_DIVIDE(
            COALESCE(
                decision_counts.reason_count,
                0
            ),
            activation_runs.source_row_count
        ) AS reason_rate,

        SAFE_DIVIDE(
            COALESCE(
                decision_counts.reason_count,
                0
            ),
            CASE reason_dimension.outcome
                WHEN 'selected_for_review'
                    THEN activation_runs.selected_count
                WHEN 'no_contact_superseded'
                    THEN activation_runs.superseded_count
                WHEN 'no_contact_below_threshold'
                    THEN activation_runs.below_threshold_count
                WHEN 'no_contact_excluded'
                    THEN activation_runs.excluded_count
                WHEN 'no_contact_suppressed'
                    THEN activation_runs.suppressed_count
                WHEN 'no_contact_capacity'
                    THEN activation_runs.capacity_not_selected_count
            END
        ) AS within_outcome_rate,

        COALESCE(
            run_reconciliation.recognised_reason_count,
            0
        ) AS recognised_reason_count,

        COALESCE(
            run_reconciliation.unexpected_reason_count,
            0
        ) AS unexpected_reason_count,

        COALESCE(
            run_reconciliation.invalid_outcome_reason_count,
            0
        ) AS invalid_outcome_reason_count,

        source_quality.orphan_decision_count,

        TRUE AS synthetic_data,
        'fully_synthetic' AS data_classification,
        'activation_audit' AS metric_class,
        'activation_decisions' AS source_name,
        activation_runs.decision_timestamp AS source_as_of,
        CURRENT_TIMESTAMP() AS view_refreshed_at,
        'current' AS freshness_status,

        (
            activation_runs.run_id IS NOT NULL
            AND activation_runs.policy_version IS NOT NULL
            AND activation_runs.model_name IS NOT NULL
            AND activation_runs.decision_timestamp IS NOT NULL
            AND activation_runs.source_row_count >= 0
            AND COALESCE(
                run_reconciliation.recognised_reason_count,
                0
            ) = activation_runs.source_row_count
            AND COALESCE(
                run_reconciliation.unexpected_reason_count,
                0
            ) = 0
            AND COALESCE(
                run_reconciliation.invalid_outcome_reason_count,
                0
            ) = 0
            AND source_quality.orphan_decision_count = 0
            AND COALESCE(
                outcome_reason_totals.outcome_reason_total_count,
                0
            ) = CASE reason_dimension.outcome
                WHEN 'selected_for_review'
                    THEN activation_runs.selected_count
                WHEN 'no_contact_superseded'
                    THEN activation_runs.superseded_count
                WHEN 'no_contact_below_threshold'
                    THEN activation_runs.below_threshold_count
                WHEN 'no_contact_excluded'
                    THEN activation_runs.excluded_count
                WHEN 'no_contact_suppressed'
                    THEN activation_runs.suppressed_count
                WHEN 'no_contact_capacity'
                    THEN activation_runs.capacity_not_selected_count
            END
        ) AS is_valid,

        CASE
            WHEN source_quality.orphan_decision_count > 0
                THEN 'Activation decisions contain run IDs absent from activation runs'
            WHEN COALESCE(
                run_reconciliation.unexpected_reason_count,
                0
            ) > 0
                THEN 'Activation decisions contain an unexpected reason code'
            WHEN COALESCE(
                run_reconciliation.invalid_outcome_reason_count,
                0
            ) > 0
                THEN 'Activation decision reason code does not match its outcome'
            WHEN COALESCE(
                run_reconciliation.recognised_reason_count,
                0
            ) != activation_runs.source_row_count
                THEN 'Recognised activation reasons do not reconcile to the run total'
            WHEN COALESCE(
                outcome_reason_totals.outcome_reason_total_count,
                0
            ) != CASE reason_dimension.outcome
                WHEN 'selected_for_review'
                    THEN activation_runs.selected_count
                WHEN 'no_contact_superseded'
                    THEN activation_runs.superseded_count
                WHEN 'no_contact_below_threshold'
                    THEN activation_runs.below_threshold_count
                WHEN 'no_contact_excluded'
                    THEN activation_runs.excluded_count
                WHEN 'no_contact_suppressed'
                    THEN activation_runs.suppressed_count
                WHEN 'no_contact_capacity'
                    THEN activation_runs.capacity_not_selected_count
            END
                THEN 'Activation reason totals do not reconcile to the outcome total'
            ELSE NULL
        END AS invalid_reason

    FROM
        `vitality_engagement_dev.activation_runs`
        AS activation_runs
    CROSS JOIN
        reason_dimension
    LEFT JOIN
        decision_counts
        ON activation_runs.run_id = decision_counts.run_id
        AND reason_dimension.outcome = decision_counts.outcome
        AND reason_dimension.reason_code = decision_counts.reason_code
    LEFT JOIN
        run_reconciliation
        ON activation_runs.run_id = run_reconciliation.run_id
    LEFT JOIN
        outcome_reason_totals
        ON activation_runs.run_id = outcome_reason_totals.run_id
        AND reason_dimension.outcome = outcome_reason_totals.outcome
    CROSS JOIN
        source_quality
),
empty_state AS (
    SELECT
        CAST(NULL AS STRING) AS run_id,
        CAST(NULL AS STRING) AS policy_version,
        CAST(NULL AS STRING) AS model_name,
        CAST(NULL AS TIMESTAMP) AS decision_timestamp,

        reason_dimension.display_order,
        reason_dimension.reason_code,
        reason_dimension.reason_label,
        reason_dimension.outcome,
        reason_dimension.outcome_label,
        reason_dimension.reason_group,
        reason_dimension.is_selected_for_review,
        reason_dimension.reason_semantics,

        0 AS reason_count,
        0 AS outcome_reason_total_count,
        0 AS expected_outcome_count,
        0 AS total_decision_count,
        CAST(NULL AS FLOAT64) AS reason_rate,
        CAST(NULL AS FLOAT64) AS within_outcome_rate,
        0 AS recognised_reason_count,
        0 AS unexpected_reason_count,
        0 AS invalid_outcome_reason_count,
        source_quality.orphan_decision_count,

        TRUE AS synthetic_data,
        'fully_synthetic' AS data_classification,
        'activation_audit' AS metric_class,
        'activation_decisions' AS source_name,
        CAST(NULL AS TIMESTAMP) AS source_as_of,
        CURRENT_TIMESTAMP() AS view_refreshed_at,
        'empty' AS freshness_status,

        source_quality.orphan_decision_count = 0 AS is_valid,

        CASE
            WHEN source_quality.orphan_decision_count > 0
                THEN 'Activation decisions exist without a corresponding activation run'
            ELSE NULL
        END AS invalid_reason

    FROM
        reason_dimension
    CROSS JOIN
        source_quality
    WHERE NOT EXISTS (
        SELECT 1
        FROM `vitality_engagement_dev.activation_runs`
    )
)
SELECT *
FROM governed_reasons

UNION ALL

SELECT *
FROM empty_state;
