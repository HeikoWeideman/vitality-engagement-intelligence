CREATE OR REPLACE VIEW
    `vitality_engagement_dev.dashboard_activation_outcome_summary`
OPTIONS (
    description = 'Read-only aggregate activation outcomes with explicit no-contact states and a valid synthetic empty state.'
)
AS
WITH outcome_dimension AS (
    SELECT *
    FROM UNNEST([
        STRUCT(
            1 AS display_order,
            'selected_for_review' AS outcome,
            'Selected for review' AS outcome_label,
            TRUE AS is_selected_for_review,
            'pending_human_review_not_approved_outreach' AS outcome_semantics
        ),
        STRUCT(
            2 AS display_order,
            'no_contact_superseded' AS outcome,
            'No contact - superseded' AS outcome_label,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS outcome_semantics
        ),
        STRUCT(
            3 AS display_order,
            'no_contact_below_threshold' AS outcome,
            'No contact - below threshold' AS outcome_label,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS outcome_semantics
        ),
        STRUCT(
            4 AS display_order,
            'no_contact_excluded' AS outcome,
            'No contact - excluded' AS outcome_label,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS outcome_semantics
        ),
        STRUCT(
            5 AS display_order,
            'no_contact_suppressed' AS outcome,
            'No contact - suppressed' AS outcome_label,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS outcome_semantics
        ),
        STRUCT(
            6 AS display_order,
            'no_contact_capacity' AS outcome,
            'No contact - capacity' AS outcome_label,
            FALSE AS is_selected_for_review,
            'explicit_no_contact' AS outcome_semantics
        )
    ])
),
decision_counts AS (
    SELECT
        run_id,
        outcome,
        COUNT(*) AS decision_count
    FROM
        `vitality_engagement_dev.activation_decisions`
    GROUP BY
        run_id,
        outcome
),
run_reconciliation AS (
    SELECT
        run_id,
        COUNTIF(
            outcome IN (
                'selected_for_review',
                'no_contact_superseded',
                'no_contact_below_threshold',
                'no_contact_excluded',
                'no_contact_suppressed',
                'no_contact_capacity'
            )
        ) AS recognised_decision_count,
        COUNTIF(
            outcome NOT IN (
                'selected_for_review',
                'no_contact_superseded',
                'no_contact_below_threshold',
                'no_contact_excluded',
                'no_contact_suppressed',
                'no_contact_capacity'
            )
        ) AS unexpected_decision_count
    FROM
        `vitality_engagement_dev.activation_decisions`
    GROUP BY
        run_id
),
source_quality AS (
    SELECT
        COUNTIF(
            activation_runs.run_id IS NULL
        ) AS orphan_decision_count
    FROM
        `vitality_engagement_dev.activation_decisions` AS activation_decisions
    LEFT JOIN
        `vitality_engagement_dev.activation_runs` AS activation_runs
        USING (run_id)
),
governed_outcomes AS (
    SELECT
        activation_runs.run_id,
        activation_runs.policy_version,
        activation_runs.model_name,
        activation_runs.decision_timestamp,

        outcome_dimension.display_order,
        outcome_dimension.outcome,
        outcome_dimension.outcome_label,
        outcome_dimension.is_selected_for_review,
        outcome_dimension.outcome_semantics,

        COALESCE(
            decision_counts.decision_count,
            0
        ) AS decision_count,

        CASE outcome_dimension.outcome
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
        END AS expected_decision_count,

        activation_runs.source_row_count AS total_decision_count,

        SAFE_DIVIDE(
            COALESCE(
                decision_counts.decision_count,
                0
            ),
            activation_runs.source_row_count
        ) AS decision_rate,

        COALESCE(
            run_reconciliation.recognised_decision_count,
            0
        ) AS recognised_decision_count,

        COALESCE(
            run_reconciliation.unexpected_decision_count,
            0
        ) AS unexpected_decision_count,

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
                decision_counts.decision_count,
                0
            ) = CASE outcome_dimension.outcome
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
            AND COALESCE(
                run_reconciliation.recognised_decision_count,
                0
            ) = activation_runs.source_row_count
            AND COALESCE(
                run_reconciliation.unexpected_decision_count,
                0
            ) = 0
            AND source_quality.orphan_decision_count = 0
            AND (
                SAFE_DIVIDE(
                    COALESCE(
                        decision_counts.decision_count,
                        0
                    ),
                    activation_runs.source_row_count
                ) BETWEEN 0.0 AND 1.0
                OR activation_runs.source_row_count = 0
            )
        ) AS is_valid,

        CASE
            WHEN source_quality.orphan_decision_count > 0
                THEN 'Activation decisions contain run IDs absent from activation runs'
            WHEN COALESCE(
                run_reconciliation.unexpected_decision_count,
                0
            ) > 0
                THEN 'Activation decisions contain an unexpected outcome'
            WHEN COALESCE(
                run_reconciliation.recognised_decision_count,
                0
            ) != activation_runs.source_row_count
                THEN 'Recognised activation decisions do not reconcile to the run total'
            WHEN COALESCE(
                decision_counts.decision_count,
                0
            ) != CASE outcome_dimension.outcome
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
                THEN 'Activation outcome count does not match the run audit summary'
            ELSE NULL
        END AS invalid_reason

    FROM
        `vitality_engagement_dev.activation_runs` AS activation_runs
    CROSS JOIN
        outcome_dimension
    LEFT JOIN
        decision_counts
        ON activation_runs.run_id = decision_counts.run_id
        AND outcome_dimension.outcome = decision_counts.outcome
    LEFT JOIN
        run_reconciliation
        ON activation_runs.run_id = run_reconciliation.run_id
    CROSS JOIN
        source_quality
),
empty_state AS (
    SELECT
        CAST(NULL AS STRING) AS run_id,
        CAST(NULL AS STRING) AS policy_version,
        CAST(NULL AS STRING) AS model_name,
        CAST(NULL AS TIMESTAMP) AS decision_timestamp,

        outcome_dimension.display_order,
        outcome_dimension.outcome,
        outcome_dimension.outcome_label,
        outcome_dimension.is_selected_for_review,
        outcome_dimension.outcome_semantics,

        0 AS decision_count,
        0 AS expected_decision_count,
        0 AS total_decision_count,
        CAST(NULL AS FLOAT64) AS decision_rate,
        0 AS recognised_decision_count,
        0 AS unexpected_decision_count,
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
        outcome_dimension
    CROSS JOIN
        source_quality
    WHERE NOT EXISTS (
        SELECT 1
        FROM `vitality_engagement_dev.activation_runs`
    )
)
SELECT *
FROM governed_outcomes

UNION ALL

SELECT *
FROM empty_state;
