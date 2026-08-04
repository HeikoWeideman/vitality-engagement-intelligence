CREATE OR REPLACE VIEW
    `vitality_engagement_dev.dashboard_quality_status`
OPTIONS (
    description = 'Read-only consolidated quality and availability status for the eight governed synthetic dashboard views. Valid empty activation states are not quality failures.'
)
AS
WITH runtime AS (
    SELECT
        CURRENT_TIMESTAMP() AS view_refreshed_at
),
lineage_status AS (
    SELECT
        dashboard_view_name,
        lineage_status,
        freshness_status,
        latest_business_date,
        latest_source_timestamp,
        freshness_interpretation,
        is_valid AS lineage_is_valid,
        invalid_reason AS lineage_invalid_reason
    FROM
        `vitality_engagement_dev.dashboard_lineage_freshness_summary`
),
view_quality AS (
    SELECT
        1 AS display_order,
        'dashboard_scoring_daily_summary' AS dashboard_view_name,
        'Daily scoring summary' AS dashboard_label,
        'forecast' AS metric_class,
        COUNT(*) AS view_row_count,
        COUNTIF(
            is_valid IS DISTINCT FROM TRUE
        ) AS invalid_row_count,
        COUNTIF(
            invalid_reason IS NOT NULL
        ) AS invalid_reason_count,
        COUNTIF(
            synthetic_data IS DISTINCT FROM TRUE
            OR data_classification != 'fully_synthetic'
            OR metric_class != 'forecast'
            OR view_refreshed_at IS NULL
        ) AS invalid_governance_metadata_count
    FROM
        `vitality_engagement_dev.dashboard_scoring_daily_summary`

    UNION ALL

    SELECT
        2,
        'dashboard_risk_distribution',
        'Risk distribution',
        'forecast',
        COUNT(*),
        COUNTIF(
            is_valid IS DISTINCT FROM TRUE
        ),
        COUNTIF(
            invalid_reason IS NOT NULL
        ),
        COUNTIF(
            synthetic_data IS DISTINCT FROM TRUE
            OR data_classification != 'fully_synthetic'
            OR metric_class != 'forecast'
            OR view_refreshed_at IS NULL
        )
    FROM
        `vitality_engagement_dev.dashboard_risk_distribution`

    UNION ALL

    SELECT
        3,
        'dashboard_observed_outcome_summary',
        'Observed outcome summary',
        'observed_outcome',
        COUNT(*),
        COUNTIF(
            is_valid IS DISTINCT FROM TRUE
        ),
        COUNTIF(
            invalid_reason IS NOT NULL
        ),
        COUNTIF(
            synthetic_data IS DISTINCT FROM TRUE
            OR data_classification != 'fully_synthetic'
            OR metric_class != 'observed_outcome'
            OR view_refreshed_at IS NULL
        )
    FROM
        `vitality_engagement_dev.dashboard_observed_outcome_summary`

    UNION ALL

    SELECT
        4,
        'dashboard_activation_run_summary',
        'Activation run summary',
        'activation_audit',
        COUNT(*),
        COUNTIF(
            is_valid IS DISTINCT FROM TRUE
        ),
        COUNTIF(
            invalid_reason IS NOT NULL
        ),
        COUNTIF(
            synthetic_data IS DISTINCT FROM TRUE
            OR data_classification != 'fully_synthetic'
            OR metric_class != 'activation_audit'
            OR view_refreshed_at IS NULL
            OR freshness_status NOT IN (
                'current',
                'empty'
            )
        )
    FROM
        `vitality_engagement_dev.dashboard_activation_run_summary`

    UNION ALL

    SELECT
        5,
        'dashboard_activation_outcome_summary',
        'Activation outcome summary',
        'activation_audit',
        COUNT(*),
        COUNTIF(
            is_valid IS DISTINCT FROM TRUE
        ),
        COUNTIF(
            invalid_reason IS NOT NULL
        ),
        COUNTIF(
            synthetic_data IS DISTINCT FROM TRUE
            OR data_classification != 'fully_synthetic'
            OR metric_class != 'activation_audit'
            OR view_refreshed_at IS NULL
            OR freshness_status NOT IN (
                'current',
                'empty'
            )
        )
    FROM
        `vitality_engagement_dev.dashboard_activation_outcome_summary`

    UNION ALL

    SELECT
        6,
        'dashboard_activation_reason_summary',
        'Activation reason summary',
        'activation_audit',
        COUNT(*),
        COUNTIF(
            is_valid IS DISTINCT FROM TRUE
        ),
        COUNTIF(
            invalid_reason IS NOT NULL
        ),
        COUNTIF(
            synthetic_data IS DISTINCT FROM TRUE
            OR data_classification != 'fully_synthetic'
            OR metric_class != 'activation_audit'
            OR view_refreshed_at IS NULL
            OR freshness_status NOT IN (
                'current',
                'empty'
            )
        )
    FROM
        `vitality_engagement_dev.dashboard_activation_reason_summary`

    UNION ALL

    SELECT
        7,
        'dashboard_review_selection_summary',
        'Review selection summary',
        'activation_audit',
        COUNT(*),
        COUNTIF(
            is_valid IS DISTINCT FROM TRUE
        ),
        COUNTIF(
            invalid_reason IS NOT NULL
        ),
        COUNTIF(
            synthetic_data IS DISTINCT FROM TRUE
            OR data_classification != 'fully_synthetic'
            OR metric_class != 'activation_audit'
            OR view_refreshed_at IS NULL
            OR freshness_status NOT IN (
                'current',
                'empty'
            )
            OR review_state != 'pending_human_review'
            OR outreach_approval_state != 'not_approved_outreach'
            OR operational_action_authorised IS DISTINCT FROM FALSE
        )
    FROM
        `vitality_engagement_dev.dashboard_review_selection_summary`

    UNION ALL

    SELECT
        8,
        'dashboard_lineage_freshness_summary',
        'Lineage and freshness summary',
        'lineage',
        COUNT(*),
        COUNTIF(
            is_valid IS DISTINCT FROM TRUE
        ),
        COUNTIF(
            invalid_reason IS NOT NULL
        ),
        COUNTIF(
            synthetic_data IS DISTINCT FROM TRUE
            OR data_classification != 'fully_synthetic'
            OR governance_metric_class != 'lineage'
            OR view_refreshed_at IS NULL
            OR lineage_status != 'complete'
            OR freshness_status NOT IN (
                'historical_snapshot',
                'available',
                'empty'
            )
        )
    FROM
        `vitality_engagement_dev.dashboard_lineage_freshness_summary`
),
evaluated AS (
    SELECT
        view_quality.display_order,
        view_quality.dashboard_view_name,
        view_quality.dashboard_label,
        view_quality.metric_class,
        view_quality.view_row_count,
        view_quality.invalid_row_count,
        view_quality.invalid_reason_count,
        view_quality.invalid_governance_metadata_count,

        COALESCE(
            lineage_status.lineage_status,
            CASE
                WHEN view_quality.dashboard_view_name
                    = 'dashboard_lineage_freshness_summary'
                    THEN 'complete'
                ELSE 'missing_source'
            END
        ) AS lineage_status,

        COALESCE(
            lineage_status.freshness_status,
            CASE
                WHEN view_quality.dashboard_view_name
                    = 'dashboard_lineage_freshness_summary'
                    THEN 'available'
                ELSE 'missing'
            END
        ) AS freshness_status,

        CASE
            WHEN COALESCE(
                lineage_status.freshness_status,
                CASE
                    WHEN view_quality.dashboard_view_name
                        = 'dashboard_lineage_freshness_summary'
                        THEN 'available'
                    ELSE 'missing'
                END
            ) = 'empty'
                THEN 'empty'
            WHEN COALESCE(
                lineage_status.freshness_status,
                CASE
                    WHEN view_quality.dashboard_view_name
                        = 'dashboard_lineage_freshness_summary'
                        THEN 'available'
                    ELSE 'missing'
                END
            ) IN (
                'historical_snapshot',
                'available'
            )
                THEN 'available'
            ELSE 'unavailable'
        END AS availability_status,

        lineage_status.latest_business_date,
        lineage_status.latest_source_timestamp,

        COALESCE(
            lineage_status.freshness_interpretation,
            'Current governed metadata summary for the eight dashboard views'
        ) AS freshness_interpretation,

        CASE
            WHEN view_quality.view_row_count = 0
                THEN 'fail'
            WHEN view_quality.invalid_row_count > 0
                THEN 'fail'
            WHEN view_quality.invalid_reason_count > 0
                THEN 'fail'
            WHEN view_quality.invalid_governance_metadata_count > 0
                THEN 'fail'
            WHEN COALESCE(
                lineage_status.lineage_is_valid,
                TRUE
            ) IS DISTINCT FROM TRUE
                THEN 'fail'
            WHEN COALESCE(
                lineage_status.lineage_status,
                'complete'
            ) != 'complete'
                THEN 'fail'
            ELSE 'pass'
        END AS quality_status,

        CASE
            WHEN view_quality.view_row_count = 0
                THEN 'Dashboard view returned no governed rows'
            WHEN view_quality.invalid_row_count > 0
                THEN 'Dashboard view contains rows that failed embedded validation'
            WHEN view_quality.invalid_reason_count > 0
                THEN 'Dashboard view contains explicit invalid reasons'
            WHEN view_quality.invalid_governance_metadata_count > 0
                THEN 'Dashboard view governance metadata is invalid'
            WHEN COALESCE(
                lineage_status.lineage_is_valid,
                TRUE
            ) IS DISTINCT FROM TRUE
                THEN COALESCE(
                    lineage_status.lineage_invalid_reason,
                    'Dashboard lineage row failed validation'
                )
            WHEN COALESCE(
                lineage_status.lineage_status,
                'complete'
            ) != 'complete'
                THEN 'Dashboard lineage is incomplete'
            ELSE NULL
        END AS quality_failure_reason

    FROM
        view_quality
    LEFT JOIN
        lineage_status
        USING (dashboard_view_name)
)
SELECT
    evaluated.*,

    CASE
        WHEN evaluated.quality_status = 'pass'
            AND evaluated.availability_status = 'empty'
            THEN 'Valid governed empty state'
        WHEN evaluated.quality_status = 'pass'
            THEN 'All governed quality checks passed'
        ELSE 'One or more governed quality checks failed'
    END AS quality_summary,

    TRUE AS synthetic_data,
    'fully_synthetic' AS data_classification,
    'data_quality' AS governance_metric_class,
    FALSE AS operational_action_authorised,
    runtime.view_refreshed_at,

    evaluated.quality_status = 'pass' AS is_valid,

    CASE
        WHEN evaluated.quality_status = 'fail'
            THEN evaluated.quality_failure_reason
        ELSE NULL
    END AS invalid_reason

FROM
    evaluated
CROSS JOIN
    runtime;
