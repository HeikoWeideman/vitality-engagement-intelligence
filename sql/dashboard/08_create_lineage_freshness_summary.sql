CREATE OR REPLACE VIEW
    `vitality_engagement_dev.dashboard_lineage_freshness_summary`
OPTIONS (
    description = 'Read-only lineage and source-state summary for governed synthetic dashboard views. Historical snapshots are not represented as live operational data.'
)
AS
WITH runtime AS (
    SELECT
        CURRENT_TIMESTAMP() AS view_refreshed_at
),
storage_metadata AS (
    SELECT
        table_id AS table_name,

        CASE type
            WHEN 1 THEN 'BASE TABLE'
            WHEN 2 THEN 'VIEW'
            WHEN 3 THEN 'EXTERNAL'
            ELSE 'UNKNOWN'
        END AS table_type,

        row_count AS total_rows,
        TIMESTAMP_MILLIS(creation_time) AS creation_time,
        TIMESTAMP_MILLIS(last_modified_time)
            AS storage_last_modified_time

    FROM
        `vitality_engagement_dev.__TABLES__`

    WHERE
        table_id IN (
            'engagement_features_28d',
            'engagement_logistic_scoring_predictions',
            'activation_runs',
            'activation_decisions'
        )
),
feature_stats AS (
    SELECT
        COUNT(*) AS source_row_count,
        MAX(prediction_date) AS latest_business_date,
        TIMESTAMP(MAX(prediction_date)) AS latest_source_timestamp
    FROM
        `vitality_engagement_dev.engagement_features_28d`
),
scoring_stats AS (
    SELECT
        COUNT(*) AS source_row_count,
        MAX(prediction_date) AS latest_business_date,
        TIMESTAMP(MAX(prediction_date)) AS latest_source_timestamp
    FROM
        `vitality_engagement_dev.engagement_logistic_scoring_predictions`
),
activation_run_stats AS (
    SELECT
        COUNT(*) AS source_row_count,
        DATE(MAX(decision_timestamp)) AS latest_business_date,
        MAX(decision_timestamp) AS latest_source_timestamp,
        MAX(ingested_at) AS latest_ingested_at
    FROM
        `vitality_engagement_dev.activation_runs`
),
activation_decision_stats AS (
    SELECT
        COUNT(*) AS source_row_count,
        MAX(prediction_date) AS latest_business_date,
        MAX(decision_timestamp) AS latest_source_timestamp,
        MAX(ingested_at) AS latest_ingested_at
    FROM
        `vitality_engagement_dev.activation_decisions`
),
feature_storage AS (
    SELECT
        COUNTIF(
            table_name = 'engagement_features_28d'
            AND table_type = 'BASE TABLE'
        ) AS source_table_count,
        COALESCE(
            SUM(total_rows),
            0
        ) AS storage_row_count,
        MIN(creation_time) AS earliest_source_created_at,
        MAX(storage_last_modified_time) AS storage_last_modified_at
    FROM
        storage_metadata
    WHERE
        table_name = 'engagement_features_28d'
),
scoring_storage AS (
    SELECT
        COUNTIF(
            table_name = 'engagement_logistic_scoring_predictions'
            AND table_type = 'BASE TABLE'
        ) AS source_table_count,
        COALESCE(
            SUM(total_rows),
            0
        ) AS storage_row_count,
        MIN(creation_time) AS earliest_source_created_at,
        MAX(storage_last_modified_time) AS storage_last_modified_at
    FROM
        storage_metadata
    WHERE
        table_name = 'engagement_logistic_scoring_predictions'
),
activation_run_storage AS (
    SELECT
        COUNTIF(
            table_name = 'activation_runs'
            AND table_type = 'BASE TABLE'
        ) AS source_table_count,
        COALESCE(
            SUM(total_rows),
            0
        ) AS storage_row_count,
        MIN(creation_time) AS earliest_source_created_at,
        MAX(storage_last_modified_time) AS storage_last_modified_at
    FROM
        storage_metadata
    WHERE
        table_name = 'activation_runs'
),
activation_storage AS (
    SELECT
        COUNTIF(
            table_name IN (
                'activation_runs',
                'activation_decisions'
            )
            AND table_type = 'BASE TABLE'
        ) AS source_table_count,
        COALESCE(
            SUM(total_rows),
            0
        ) AS storage_row_count,
        MIN(creation_time) AS earliest_source_created_at,
        MAX(storage_last_modified_time) AS storage_last_modified_at
    FROM
        storage_metadata
    WHERE
        table_name IN (
            'activation_runs',
            'activation_decisions'
        )
),
lineage_rows AS (
    SELECT
        1 AS display_order,
        'dashboard_scoring_daily_summary' AS dashboard_view_name,
        'forecast' AS metric_class,
        'engagement_logistic_scoring_predictions' AS source_table_names,
        scoring_storage.source_table_count,
        scoring_stats.source_row_count,
        scoring_storage.storage_row_count,
        scoring_stats.latest_business_date,
        scoring_stats.latest_source_timestamp,
        CAST(NULL AS TIMESTAMP) AS latest_ingested_at,
        scoring_storage.earliest_source_created_at,
        scoring_storage.storage_last_modified_at,
        'direct_aggregate' AS lineage_type,

        CASE
            WHEN scoring_storage.source_table_count != 1
                THEN 'missing_source'
            ELSE 'complete'
        END AS lineage_status,

        CASE
            WHEN scoring_storage.source_table_count != 1
                THEN 'missing'
            WHEN scoring_stats.source_row_count = 0
                THEN 'missing_data'
            ELSE 'historical_snapshot'
        END AS freshness_status,

        'Synthetic forecast snapshot; not a live operational feed'
            AS freshness_interpretation,

        (
            scoring_storage.source_table_count = 1
            AND scoring_stats.source_row_count > 0
            AND scoring_stats.latest_business_date IS NOT NULL
            AND scoring_stats.latest_source_timestamp IS NOT NULL
        ) AS is_valid,

        CASE
            WHEN scoring_storage.source_table_count != 1
                THEN 'Required scoring source table is missing'
            WHEN scoring_stats.source_row_count = 0
                THEN 'Scoring source contains no forecast rows'
            WHEN scoring_stats.latest_business_date IS NULL
                THEN 'Scoring source has no latest business date'
            ELSE NULL
        END AS invalid_reason

    FROM
        scoring_stats
    CROSS JOIN
        scoring_storage

    UNION ALL

    SELECT
        2,
        'dashboard_risk_distribution',
        'forecast',
        'engagement_logistic_scoring_predictions',
        scoring_storage.source_table_count,
        scoring_stats.source_row_count,
        scoring_storage.storage_row_count,
        scoring_stats.latest_business_date,
        scoring_stats.latest_source_timestamp,
        CAST(NULL AS TIMESTAMP),
        scoring_storage.earliest_source_created_at,
        scoring_storage.storage_last_modified_at,
        'direct_aggregate',
        CASE
            WHEN scoring_storage.source_table_count != 1
                THEN 'missing_source'
            ELSE 'complete'
        END,
        CASE
            WHEN scoring_storage.source_table_count != 1
                THEN 'missing'
            WHEN scoring_stats.source_row_count = 0
                THEN 'missing_data'
            ELSE 'historical_snapshot'
        END,
        'Synthetic forecast snapshot; not a live operational feed',
        (
            scoring_storage.source_table_count = 1
            AND scoring_stats.source_row_count > 0
            AND scoring_stats.latest_business_date IS NOT NULL
            AND scoring_stats.latest_source_timestamp IS NOT NULL
        ),
        CASE
            WHEN scoring_storage.source_table_count != 1
                THEN 'Required scoring source table is missing'
            WHEN scoring_stats.source_row_count = 0
                THEN 'Scoring source contains no forecast rows'
            WHEN scoring_stats.latest_business_date IS NULL
                THEN 'Scoring source has no latest business date'
            ELSE NULL
        END
    FROM
        scoring_stats
    CROSS JOIN
        scoring_storage

    UNION ALL

    SELECT
        3,
        'dashboard_observed_outcome_summary',
        'observed_outcome',
        'engagement_features_28d',
        feature_storage.source_table_count,
        feature_stats.source_row_count,
        feature_storage.storage_row_count,
        feature_stats.latest_business_date,
        feature_stats.latest_source_timestamp,
        CAST(NULL AS TIMESTAMP),
        feature_storage.earliest_source_created_at,
        feature_storage.storage_last_modified_at,
        'filtered_aggregate',
        CASE
            WHEN feature_storage.source_table_count != 1
                THEN 'missing_source'
            ELSE 'complete'
        END,
        CASE
            WHEN feature_storage.source_table_count != 1
                THEN 'missing'
            WHEN feature_stats.source_row_count = 0
                THEN 'missing_data'
            ELSE 'historical_snapshot'
        END,
        'Synthetic completed-label snapshot; descriptive and not causal',
        (
            feature_storage.source_table_count = 1
            AND feature_stats.source_row_count > 0
            AND feature_stats.latest_business_date IS NOT NULL
            AND feature_stats.latest_source_timestamp IS NOT NULL
        ),
        CASE
            WHEN feature_storage.source_table_count != 1
                THEN 'Required feature source table is missing'
            WHEN feature_stats.source_row_count = 0
                THEN 'Feature source contains no rows'
            WHEN feature_stats.latest_business_date IS NULL
                THEN 'Feature source has no latest business date'
            ELSE NULL
        END
    FROM
        feature_stats
    CROSS JOIN
        feature_storage

    UNION ALL

    SELECT
        4,
        'dashboard_activation_run_summary',
        'activation_audit',
        'activation_runs',
        activation_run_storage.source_table_count,
        activation_run_stats.source_row_count,
        activation_run_storage.storage_row_count,
        activation_run_stats.latest_business_date,
        activation_run_stats.latest_source_timestamp,
        activation_run_stats.latest_ingested_at,
        activation_run_storage.earliest_source_created_at,
        activation_run_storage.storage_last_modified_at,
        'direct_aggregate',

        CASE
            WHEN activation_run_storage.source_table_count != 1
                THEN 'missing_source'
            ELSE 'complete'
        END,

        CASE
            WHEN activation_run_storage.source_table_count != 1
                THEN 'missing'
            WHEN activation_run_stats.source_row_count = 0
                THEN 'empty'
            ELSE 'available'
        END,

        'Empty is a valid governed activation state; no run is fabricated',

        (
            activation_run_storage.source_table_count = 1
            AND (
                activation_run_stats.source_row_count = 0
                OR (
                    activation_run_stats.latest_business_date IS NOT NULL
                    AND activation_run_stats.latest_source_timestamp IS NOT NULL
                    AND activation_run_stats.latest_ingested_at IS NOT NULL
                )
            )
        ),

        CASE
            WHEN activation_run_storage.source_table_count != 1
                THEN 'Required activation run source table is missing'
            WHEN activation_run_stats.source_row_count > 0
                AND activation_run_stats.latest_source_timestamp IS NULL
                THEN 'Activation runs have no latest decision timestamp'
            WHEN activation_run_stats.source_row_count > 0
                AND activation_run_stats.latest_ingested_at IS NULL
                THEN 'Activation runs have no latest ingestion timestamp'
            ELSE NULL
        END

    FROM
        activation_run_stats
    CROSS JOIN
        activation_run_storage

    UNION ALL

    SELECT
        display_order,
        dashboard_view_name,
        'activation_audit',
        'activation_runs,activation_decisions',
        activation_storage.source_table_count,
        activation_run_stats.source_row_count
            + activation_decision_stats.source_row_count,
        activation_storage.storage_row_count,

        CASE
            WHEN activation_run_stats.latest_business_date IS NULL
                THEN activation_decision_stats.latest_business_date
            WHEN activation_decision_stats.latest_business_date IS NULL
                THEN activation_run_stats.latest_business_date
            ELSE GREATEST(
                activation_run_stats.latest_business_date,
                activation_decision_stats.latest_business_date
            )
        END,

        CASE
            WHEN activation_run_stats.latest_source_timestamp IS NULL
                THEN activation_decision_stats.latest_source_timestamp
            WHEN activation_decision_stats.latest_source_timestamp IS NULL
                THEN activation_run_stats.latest_source_timestamp
            ELSE GREATEST(
                activation_run_stats.latest_source_timestamp,
                activation_decision_stats.latest_source_timestamp
            )
        END,

        CASE
            WHEN activation_run_stats.latest_ingested_at IS NULL
                THEN activation_decision_stats.latest_ingested_at
            WHEN activation_decision_stats.latest_ingested_at IS NULL
                THEN activation_run_stats.latest_ingested_at
            ELSE GREATEST(
                activation_run_stats.latest_ingested_at,
                activation_decision_stats.latest_ingested_at
            )
        END,

        activation_storage.earliest_source_created_at,
        activation_storage.storage_last_modified_at,
        lineage_type,

        CASE
            WHEN activation_storage.source_table_count != 2
                THEN 'missing_source'
            ELSE 'complete'
        END,

        CASE
            WHEN activation_storage.source_table_count != 2
                THEN 'missing'
            WHEN activation_run_stats.source_row_count = 0
                AND activation_decision_stats.source_row_count = 0
                THEN 'empty'
            ELSE 'available'
        END,

        freshness_interpretation,

        (
            activation_storage.source_table_count = 2
            AND (
                (
                    activation_run_stats.source_row_count = 0
                    AND activation_decision_stats.source_row_count = 0
                )
                OR (
                    activation_run_stats.latest_source_timestamp IS NOT NULL
                    OR activation_decision_stats.latest_source_timestamp IS NOT NULL
                )
            )
        ),

        CASE
            WHEN activation_storage.source_table_count != 2
                THEN 'Required activation source tables are missing'
            WHEN (
                activation_run_stats.source_row_count > 0
                OR activation_decision_stats.source_row_count > 0
            )
            AND activation_run_stats.latest_source_timestamp IS NULL
            AND activation_decision_stats.latest_source_timestamp IS NULL
                THEN 'Activation sources have no latest decision timestamp'
            ELSE NULL
        END

    FROM
        UNNEST([
            STRUCT(
                5 AS display_order,
                'dashboard_activation_outcome_summary'
                    AS dashboard_view_name,
                'joined_dimension_aggregate' AS lineage_type,
                'Empty is valid; selected for review is not approved outreach'
                    AS freshness_interpretation
            ),
            STRUCT(
                6,
                'dashboard_activation_reason_summary',
                'joined_dimension_aggregate',
                'Empty is valid; reason codes describe auditable decisions'
            ),
            STRUCT(
                7,
                'dashboard_review_selection_summary',
                'filtered_dimension_aggregate',
                'Empty is valid; review selection remains pending human review'
            )
        ])
    CROSS JOIN
        activation_run_stats
    CROSS JOIN
        activation_decision_stats
    CROSS JOIN
        activation_storage
)
SELECT
    lineage_rows.*,

    TRUE AS synthetic_data,
    'fully_synthetic' AS data_classification,
    'lineage' AS governance_metric_class,
    'BigQuery __TABLES__ metadata and governed source aggregates'
        AS metadata_source,
    runtime.view_refreshed_at

FROM
    lineage_rows
CROSS JOIN
    runtime;
