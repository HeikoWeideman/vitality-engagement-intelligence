CREATE OR REPLACE VIEW
    `vitality_engagement_dev.dashboard_activation_run_summary`
OPTIONS (
    description = 'Read-only activation-run governance summary with an explicit valid empty state.'
)
AS
WITH governed_runs AS (
    SELECT
        run_id,
        policy_version,
        model_name,
        threshold,
        decision_timestamp,
        contact_context_snapshot_timestamp,
        ingested_at,
        capacity_limit,
        source_row_count,
        source_member_count,
        superseded_count,
        below_threshold_count,
        excluded_count,
        suppressed_count,
        eligible_count,
        capacity_not_selected_count,
        selected_count,

        SAFE_DIVIDE(
            selected_count,
            capacity_limit
        ) AS capacity_utilisation_rate,

        (
            superseded_count
            + below_threshold_count
            + excluded_count
            + suppressed_count
            + capacity_not_selected_count
            + selected_count
        ) AS reconciled_decision_count,

        TRUE AS synthetic_data,
        'fully_synthetic' AS data_classification,
        'activation_audit' AS metric_class,
        'activation_runs' AS source_name,
        decision_timestamp AS source_as_of,
        CURRENT_TIMESTAMP() AS view_refreshed_at,
        'current' AS freshness_status,

        (
            run_id IS NOT NULL
            AND policy_version IS NOT NULL
            AND model_name IS NOT NULL
            AND threshold BETWEEN 0.0 AND 1.0
            AND decision_timestamp IS NOT NULL
            AND contact_context_snapshot_timestamp IS NOT NULL
            AND contact_context_snapshot_timestamp <= decision_timestamp
            AND ingested_at IS NOT NULL
            AND capacity_limit > 0
            AND selected_count <= capacity_limit
            AND eligible_count
                = selected_count + capacity_not_selected_count
            AND source_member_count
                = source_row_count - superseded_count
            AND source_row_count
                = (
                    superseded_count
                    + below_threshold_count
                    + excluded_count
                    + suppressed_count
                    + capacity_not_selected_count
                    + selected_count
                )
        ) AS is_valid,

        CASE
            WHEN run_id IS NULL
                THEN 'Activation run ID is missing'
            WHEN threshold NOT BETWEEN 0.0 AND 1.0
                THEN 'Activation threshold falls outside zero to one'
            WHEN contact_context_snapshot_timestamp > decision_timestamp
                THEN 'Contact-context snapshot is later than the decision timestamp'
            WHEN capacity_limit <= 0
                THEN 'Activation capacity must be positive'
            WHEN selected_count > capacity_limit
                THEN 'Selected count exceeds capacity'
            WHEN eligible_count
                != selected_count + capacity_not_selected_count
                THEN 'Eligible count does not reconcile'
            WHEN source_member_count
                != source_row_count - superseded_count
                THEN 'Source member count does not reconcile'
            WHEN source_row_count
                != (
                    superseded_count
                    + below_threshold_count
                    + excluded_count
                    + suppressed_count
                    + capacity_not_selected_count
                    + selected_count
                )
                THEN 'Activation decision outcomes do not reconcile'
            ELSE NULL
        END AS invalid_reason

    FROM
        `vitality_engagement_dev.activation_runs`
),
empty_state AS (
    SELECT
        CAST(NULL AS STRING) AS run_id,
        CAST(NULL AS STRING) AS policy_version,
        CAST(NULL AS STRING) AS model_name,
        CAST(NULL AS FLOAT64) AS threshold,
        CAST(NULL AS TIMESTAMP) AS decision_timestamp,
        CAST(NULL AS TIMESTAMP) AS contact_context_snapshot_timestamp,
        CAST(NULL AS TIMESTAMP) AS ingested_at,
        0 AS capacity_limit,
        0 AS source_row_count,
        0 AS source_member_count,
        0 AS superseded_count,
        0 AS below_threshold_count,
        0 AS excluded_count,
        0 AS suppressed_count,
        0 AS eligible_count,
        0 AS capacity_not_selected_count,
        0 AS selected_count,
        CAST(NULL AS FLOAT64) AS capacity_utilisation_rate,
        0 AS reconciled_decision_count,
        TRUE AS synthetic_data,
        'fully_synthetic' AS data_classification,
        'activation_audit' AS metric_class,
        'activation_runs' AS source_name,
        CAST(NULL AS TIMESTAMP) AS source_as_of,
        CURRENT_TIMESTAMP() AS view_refreshed_at,
        'empty' AS freshness_status,
        TRUE AS is_valid,
        CAST(NULL AS STRING) AS invalid_reason
    FROM
        UNNEST([1])
    WHERE NOT EXISTS (
        SELECT 1
        FROM `vitality_engagement_dev.activation_runs`
    )
)
SELECT *
FROM governed_runs

UNION ALL

SELECT *
FROM empty_state;
