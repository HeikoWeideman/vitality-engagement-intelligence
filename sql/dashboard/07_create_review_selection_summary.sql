CREATE OR REPLACE VIEW
    `vitality_engagement_dev.dashboard_review_selection_summary`
OPTIONS (
    description = 'Read-only aggregate pending-review selections by governed supportive intervention category. Selected for review does not mean approved outreach.'
)
AS
WITH intervention_dimension AS (
    SELECT *
    FROM UNNEST([
        STRUCT(
            1 AS display_order,
            'supportive_check_in' AS intervention_category,
            'Supportive check-in' AS intervention_label
        ),
        STRUCT(
            2 AS display_order,
            'goal_planning' AS intervention_category,
            'Goal planning' AS intervention_label
        ),
        STRUCT(
            3 AS display_order,
            'activity_reminder' AS intervention_category,
            'Activity reminder' AS intervention_label
        ),
        STRUCT(
            4 AS display_order,
            'rewards_education' AS intervention_category,
            'Rewards education' AS intervention_label
        )
    ])
),
selection_counts AS (
    SELECT
        run_id,
        intervention_category,
        COUNT(*) AS selection_count
    FROM
        `vitality_engagement_dev.activation_decisions`
    WHERE
        outcome = 'selected_for_review'
    GROUP BY
        run_id,
        intervention_category
),
decision_quality AS (
    SELECT
        activation_decisions.run_id,

        COUNTIF(
            activation_decisions.outcome = 'selected_for_review'
            AND intervention_dimension.intervention_category IS NOT NULL
        ) AS recognised_selected_count,

        COUNTIF(
            activation_decisions.outcome = 'selected_for_review'
            AND activation_decisions.intervention_category IS NULL
        ) AS missing_intervention_category_count,

        COUNTIF(
            activation_decisions.outcome = 'selected_for_review'
            AND activation_decisions.intervention_category IS NOT NULL
            AND intervention_dimension.intervention_category IS NULL
        ) AS unexpected_intervention_category_count,

        COUNTIF(
            activation_decisions.outcome != 'selected_for_review'
            AND activation_decisions.intervention_category IS NOT NULL
        ) AS non_selected_with_intervention_count

    FROM
        `vitality_engagement_dev.activation_decisions`
        AS activation_decisions
    LEFT JOIN
        intervention_dimension
        ON activation_decisions.intervention_category
            = intervention_dimension.intervention_category
    GROUP BY
        activation_decisions.run_id
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
governed_selections AS (
    SELECT
        activation_runs.run_id,
        activation_runs.policy_version,
        activation_runs.model_name,
        activation_runs.decision_timestamp,

        intervention_dimension.display_order,
        intervention_dimension.intervention_category,
        intervention_dimension.intervention_label,

        COALESCE(
            selection_counts.selection_count,
            0
        ) AS selection_count,

        activation_runs.selected_count AS expected_selected_count,

        COALESCE(
            decision_quality.recognised_selected_count,
            0
        ) AS recognised_selected_count,

        SAFE_DIVIDE(
            COALESCE(
                selection_counts.selection_count,
                0
            ),
            activation_runs.selected_count
        ) AS selection_share,

        COALESCE(
            decision_quality.missing_intervention_category_count,
            0
        ) AS missing_intervention_category_count,

        COALESCE(
            decision_quality.unexpected_intervention_category_count,
            0
        ) AS unexpected_intervention_category_count,

        COALESCE(
            decision_quality.non_selected_with_intervention_count,
            0
        ) AS non_selected_with_intervention_count,

        source_quality.orphan_decision_count,

        'pending_human_review' AS review_state,
        'not_approved_outreach' AS outreach_approval_state,
        FALSE AS operational_action_authorised,

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
            AND activation_runs.selected_count >= 0
            AND COALESCE(
                decision_quality.recognised_selected_count,
                0
            ) = activation_runs.selected_count
            AND COALESCE(
                decision_quality.missing_intervention_category_count,
                0
            ) = 0
            AND COALESCE(
                decision_quality.unexpected_intervention_category_count,
                0
            ) = 0
            AND COALESCE(
                decision_quality.non_selected_with_intervention_count,
                0
            ) = 0
            AND source_quality.orphan_decision_count = 0
            AND COALESCE(
                selection_counts.selection_count,
                0
            ) <= activation_runs.selected_count
        ) AS is_valid,

        CASE
            WHEN source_quality.orphan_decision_count > 0
                THEN 'Activation decisions contain run IDs absent from activation runs'
            WHEN COALESCE(
                decision_quality.missing_intervention_category_count,
                0
            ) > 0
                THEN 'Selected-for-review decisions are missing an intervention category'
            WHEN COALESCE(
                decision_quality.unexpected_intervention_category_count,
                0
            ) > 0
                THEN 'Selected-for-review decisions contain an unexpected intervention category'
            WHEN COALESCE(
                decision_quality.non_selected_with_intervention_count,
                0
            ) > 0
                THEN 'No-contact decisions contain an intervention category'
            WHEN COALESCE(
                decision_quality.recognised_selected_count,
                0
            ) != activation_runs.selected_count
                THEN 'Recognised review selections do not reconcile to the run selected count'
            ELSE NULL
        END AS invalid_reason

    FROM
        `vitality_engagement_dev.activation_runs`
        AS activation_runs
    CROSS JOIN
        intervention_dimension
    LEFT JOIN
        selection_counts
        ON activation_runs.run_id = selection_counts.run_id
        AND intervention_dimension.intervention_category
            = selection_counts.intervention_category
    LEFT JOIN
        decision_quality
        ON activation_runs.run_id = decision_quality.run_id
    CROSS JOIN
        source_quality
),
empty_state AS (
    SELECT
        CAST(NULL AS STRING) AS run_id,
        CAST(NULL AS STRING) AS policy_version,
        CAST(NULL AS STRING) AS model_name,
        CAST(NULL AS TIMESTAMP) AS decision_timestamp,

        intervention_dimension.display_order,
        intervention_dimension.intervention_category,
        intervention_dimension.intervention_label,

        0 AS selection_count,
        0 AS expected_selected_count,
        0 AS recognised_selected_count,
        CAST(NULL AS FLOAT64) AS selection_share,
        0 AS missing_intervention_category_count,
        0 AS unexpected_intervention_category_count,
        0 AS non_selected_with_intervention_count,
        source_quality.orphan_decision_count,

        'pending_human_review' AS review_state,
        'not_approved_outreach' AS outreach_approval_state,
        FALSE AS operational_action_authorised,

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
        intervention_dimension
    CROSS JOIN
        source_quality
    WHERE NOT EXISTS (
        SELECT 1
        FROM `vitality_engagement_dev.activation_runs`
    )
)
SELECT *
FROM governed_selections

UNION ALL

SELECT *
FROM empty_state;
