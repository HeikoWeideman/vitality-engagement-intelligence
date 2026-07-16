CREATE OR REPLACE TABLE `engagement_modeling_split`
OPTIONS (
    description = 'Chronological train, validation, test, and scoring split.'
)
AS
SELECT
    features.*,
    CASE
        WHEN prediction_date BETWEEN
            DATE '2025-01-29'
            AND DATE '2025-04-30'
            THEN 'train'

        WHEN prediction_date BETWEEN
            DATE '2025-05-01'
            AND DATE '2025-05-31'
            THEN 'validation'

        WHEN prediction_date BETWEEN
            DATE '2025-06-01'
            AND DATE '2025-06-22'
            THEN 'test'

        WHEN prediction_date BETWEEN
            DATE '2025-06-23'
            AND DATE '2025-06-29'
            THEN 'scoring'

        ELSE 'unassigned'
    END AS dataset_split
FROM `engagement_features_28d` AS features;

CREATE OR REPLACE VIEW `engagement_train` AS
SELECT *
FROM `engagement_modeling_split`
WHERE dataset_split = 'train';

CREATE OR REPLACE VIEW `engagement_validation` AS
SELECT *
FROM `engagement_modeling_split`
WHERE dataset_split = 'validation';

CREATE OR REPLACE VIEW `engagement_test` AS
SELECT *
FROM `engagement_modeling_split`
WHERE dataset_split = 'test';

CREATE OR REPLACE VIEW `engagement_scoring` AS
SELECT *
FROM `engagement_modeling_split`
WHERE dataset_split = 'scoring';
