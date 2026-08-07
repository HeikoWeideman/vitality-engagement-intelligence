CREATE OR REPLACE VIEW
    `vitality_engagement_dev.governance_monitoring_status`
OPTIONS (
    description = 'Read-only governance monitoring for valid activation empty states, dashboard quality, and lineage freshness. No operational action is authorised.'
)
AS
WITH runtime AS (
    SELECT
        CURRENT_TIMESTAMP() AS view_refreshed_at
),
activation_source_state AS (
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
activation_view_state AS (
    SELECT
        'dashboard_activation_run_summary' AS dashboard_view_name,
        freshness_status,
        is_valid,
        invalid_reason
    FROM
        `vitality_engagement_dev.dashboard_activation_run_summary`

    UNION ALL

    SELECT
        'dashboard_activation_outcome_summary',
        freshness_status,
        is_valid,
        invalid_reason
    FROM
        `vitality_engagement_dev.dashboard_activation_outcome_summary`

    UNION ALL

    SELECT
        'dashboard_activation_reason_summary',
        freshness_status,
        is_valid,
        invalid_reason
    FROM
        `vitality_engagement_dev.dashboard_activation_reason_summary`

    UNION ALL

    SELECT
        'dashboard_review_selection_summary',
        freshness_status,
        is_valid,
        invalid_reason
    FROM
        `vitality_engagement_dev.dashboard_review_selection_summary`
),
activation_empty_state_evaluation AS (
    SELECT
        COUNTIF(
            activation_view_state.is_valid IS DISTINCT FROM TRUE
            OR activation_view_state.invalid_reason IS NOT NULL
            OR CASE activation_view_state.dashboard_view_name
                WHEN 'dashboard_activation_run_summary'
                    THEN (
                        activation_source_state.activation_run_count = 0
                        AND activation_view_state.freshness_status != 'empty'
                    )
                    OR (
                        activation_source_state.activation_run_count > 0
                        AND activation_view_state.freshness_status != 'current'
                    )
                ELSE (
                    activation_source_state.activation_run_count = 0
                    AND activation_source_state.activation_decision_count = 0
                    AND activation_view_state.freshness_status != 'empty'
                )
                OR (
                    (
                        activation_source_state.activation_run_count > 0
                        OR activation_source_state.activation_decision_count > 0
                    )
                    AND activation_view_state.freshness_status != 'current'
                )
            END
        ) AS invalid_activation_state_count,

        activation_source_state.activation_run_count,
        activation_source_state.activation_decision_count

    FROM
        activation_view_state
    CROSS JOIN
        activation_source_state
    GROUP BY
        activation_source_state.activation_run_count,
        activation_source_state.activation_decision_count
),
dashboard_quality_evaluation AS (
    SELECT
        COUNT(*) AS dashboard_asset_count,

        COUNTIF(
            quality_status != 'pass'
            OR is_valid IS DISTINCT FROM TRUE
            OR invalid_reason IS NOT NULL
            OR operational_action_authorised IS DISTINCT FROM FALSE
        ) AS invalid_dashboard_asset_count

    FROM
        `vitality_engagement_dev.dashboard_quality_status`
),
lineage_evaluation AS (
    SELECT
        COUNT(*) AS lineage_row_count,

        COUNTIF(
            lineage_status != 'complete'
            OR freshness_status NOT IN (
                'historical_snapshot',
                'available',
                'empty'
            )
            OR is_valid IS DISTINCT FROM TRUE
            OR invalid_reason IS NOT NULL
        ) AS invalid_lineage_row_count

    FROM
        `vitality_engagement_dev.dashboard_lineage_freshness_summary`
),
checks AS (
    SELECT
        1 AS display_order,
        'activation_empty_state_validity' AS check_name,
        'activation_empty_state' AS check_type,

        CAST(
            activation_empty_state_evaluation.invalid_activation_state_count
            AS FLOAT64
        ) AS observed_value,

        0.0 AS expected_value,
        CAST(NULL AS FLOAT64) AS warning_threshold,
        1.0 AS critical_threshold,

        CASE
            WHEN
                activation_empty_state_evaluation.invalid_activation_state_count
                = 0
                THEN 'pass'
            ELSE 'critical'
        END AS severity,

        CONCAT(
            'Activation dashboards must preserve valid empty states without fabricating records; activation runs=',
            CAST(
                activation_empty_state_evaluation.activation_run_count
                AS STRING
            ),
            ', activation decisions=',
            CAST(
                activation_empty_state_evaluation.activation_decision_count
                AS STRING
            )
        ) AS details

    FROM
        activation_empty_state_evaluation

    UNION ALL

    SELECT
        2,
        'dashboard_quality_status',
        'dashboard_quality',

        CAST(
            dashboard_quality_evaluation.invalid_dashboard_asset_count
            AS FLOAT64
        ),

        0.0,
        CAST(NULL AS FLOAT64),
        1.0,

        CASE
            WHEN
                dashboard_quality_evaluation.dashboard_asset_count = 8
                AND dashboard_quality_evaluation.invalid_dashboard_asset_count
                    = 0
                THEN 'pass'
            ELSE 'critical'
        END,

        CONCAT(
            'All eight governed dashboard assets must pass embedded quality checks; governed assets=',
            CAST(
                dashboard_quality_evaluation.dashboard_asset_count
                AS STRING
            )
        )

    FROM
        dashboard_quality_evaluation

    UNION ALL

    SELECT
        3,
        'dashboard_lineage_freshness_status',
        'source_freshness',

        CAST(
            lineage_evaluation.invalid_lineage_row_count
            AS FLOAT64
        ),

        0.0,
        CAST(NULL AS FLOAT64),
        1.0,

        CASE
            WHEN
                lineage_evaluation.lineage_row_count = 7
                AND lineage_evaluation.invalid_lineage_row_count = 0
                THEN 'pass'
            ELSE 'critical'
        END,

        CONCAT(
            'All seven governed dashboard lineage rows must be complete and valid; lineage rows=',
            CAST(
                lineage_evaluation.lineage_row_count
                AS STRING
            )
        )

    FROM
        lineage_evaluation
),
evaluated AS (
    SELECT
        checks.*,

        CASE
            MAX(
                CASE checks.severity
                    WHEN 'critical' THEN 2
                    WHEN 'warning' THEN 1
                    ELSE 0
                END
            ) OVER ()
            WHEN 2 THEN 'critical'
            WHEN 1 THEN 'warning'
            ELSE 'pass'
        END AS overall_severity

    FROM
        checks
)
SELECT
    evaluated.*,
    TRUE AS synthetic_data,
    'fully_synthetic' AS data_classification,
    'governance_monitoring' AS governance_metric_class,
    FALSE AS operational_action_authorised,
    'dashboard_quality_status,dashboard_lineage_freshness_summary,activation_runs,activation_decisions'
        AS source_name,
    runtime.view_refreshed_at AS source_as_of,
    runtime.view_refreshed_at,

    evaluated.severity != 'critical' AS is_valid,

    CASE
        WHEN evaluated.severity = 'critical'
            THEN evaluated.details
        ELSE NULL
    END AS invalid_reason

FROM
    evaluated
CROSS JOIN
    runtime;
