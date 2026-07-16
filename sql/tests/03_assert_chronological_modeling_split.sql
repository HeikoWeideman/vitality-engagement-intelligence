DECLARE metrics STRUCT<
    total_row_count INT64,
    train_row_count INT64,
    validation_row_count INT64,
    test_row_count INT64,
    scoring_row_count INT64,
    train_member_count INT64,
    validation_member_count INT64,
    test_member_count INT64,
    scoring_member_count INT64,
    train_minimum_date DATE,
    train_maximum_date DATE,
    validation_minimum_date DATE,
    validation_maximum_date DATE,
    test_minimum_date DATE,
    test_maximum_date DATE,
    scoring_minimum_date DATE,
    scoring_maximum_date DATE,
    labelled_split_null_count INT64,
    scoring_non_null_count INT64,
    unassigned_row_count INT64
>;

SET metrics = (
    SELECT AS STRUCT
        COUNT(*) AS total_row_count,

        COUNTIF(dataset_split = 'train')
            AS train_row_count,

        COUNTIF(dataset_split = 'validation')
            AS validation_row_count,

        COUNTIF(dataset_split = 'test')
            AS test_row_count,

        COUNTIF(dataset_split = 'scoring')
            AS scoring_row_count,

        COUNT(
            DISTINCT IF(
                dataset_split = 'train',
                member_id,
                NULL
            )
        ) AS train_member_count,

        COUNT(
            DISTINCT IF(
                dataset_split = 'validation',
                member_id,
                NULL
            )
        ) AS validation_member_count,

        COUNT(
            DISTINCT IF(
                dataset_split = 'test',
                member_id,
                NULL
            )
        ) AS test_member_count,

        COUNT(
            DISTINCT IF(
                dataset_split = 'scoring',
                member_id,
                NULL
            )
        ) AS scoring_member_count,

        MIN(
            IF(
                dataset_split = 'train',
                prediction_date,
                NULL
            )
        ) AS train_minimum_date,

        MAX(
            IF(
                dataset_split = 'train',
                prediction_date,
                NULL
            )
        ) AS train_maximum_date,

        MIN(
            IF(
                dataset_split = 'validation',
                prediction_date,
                NULL
            )
        ) AS validation_minimum_date,

        MAX(
            IF(
                dataset_split = 'validation',
                prediction_date,
                NULL
            )
        ) AS validation_maximum_date,

        MIN(
            IF(
                dataset_split = 'test',
                prediction_date,
                NULL
            )
        ) AS test_minimum_date,

        MAX(
            IF(
                dataset_split = 'test',
                prediction_date,
                NULL
            )
        ) AS test_maximum_date,

        MIN(
            IF(
                dataset_split = 'scoring',
                prediction_date,
                NULL
            )
        ) AS scoring_minimum_date,

        MAX(
            IF(
                dataset_split = 'scoring',
                prediction_date,
                NULL
            )
        ) AS scoring_maximum_date,

        COUNTIF(
            dataset_split IN (
                'train',
                'validation',
                'test'
            )
            AND label_will_miss_goal_next_7_days IS NULL
        ) AS labelled_split_null_count,

        COUNTIF(
            dataset_split = 'scoring'
            AND label_will_miss_goal_next_7_days IS NOT NULL
        ) AS scoring_non_null_count,

        COUNTIF(
            dataset_split NOT IN (
                'train',
                'validation',
                'test',
                'scoring'
            )
            OR dataset_split IS NULL
        ) AS unassigned_row_count

    FROM `engagement_modeling_split`
);

ASSERT metrics.total_row_count = 76000
AS 'Expected exactly 76000 modelling split rows';

ASSERT metrics.train_row_count = 46000
AS 'Unexpected training row count';

ASSERT metrics.validation_row_count = 15500
AS 'Unexpected validation row count';

ASSERT metrics.test_row_count = 11000
AS 'Unexpected test row count';

ASSERT metrics.scoring_row_count = 3500
AS 'Unexpected scoring row count';

ASSERT metrics.train_member_count = 500
AS 'Expected 500 members in the training split';

ASSERT metrics.validation_member_count = 500
AS 'Expected 500 members in the validation split';

ASSERT metrics.test_member_count = 500
AS 'Expected 500 members in the test split';

ASSERT metrics.scoring_member_count = 500
AS 'Expected 500 members in the scoring split';

ASSERT (
    metrics.train_minimum_date = DATE '2025-01-29'
    AND metrics.train_maximum_date = DATE '2025-04-30'
)
AS 'Unexpected training date range';

ASSERT (
    metrics.validation_minimum_date = DATE '2025-05-01'
    AND metrics.validation_maximum_date = DATE '2025-05-31'
)
AS 'Unexpected validation date range';

ASSERT (
    metrics.test_minimum_date = DATE '2025-06-01'
    AND metrics.test_maximum_date = DATE '2025-06-22'
)
AS 'Unexpected test date range';

ASSERT (
    metrics.scoring_minimum_date = DATE '2025-06-23'
    AND metrics.scoring_maximum_date = DATE '2025-06-29'
)
AS 'Unexpected scoring date range';

ASSERT metrics.labelled_split_null_count = 0
AS 'Train, validation, or test contains null labels';

ASSERT metrics.scoring_non_null_count = 0
AS 'Scoring rows unexpectedly contain labels';

ASSERT metrics.unassigned_row_count = 0
AS 'Unassigned modelling rows detected';

ASSERT metrics.train_maximum_date
    < metrics.validation_minimum_date
AS 'Training and validation periods overlap';

ASSERT metrics.validation_maximum_date
    < metrics.test_minimum_date
AS 'Validation and test periods overlap';

ASSERT metrics.test_maximum_date
    < metrics.scoring_minimum_date
AS 'Test and scoring periods overlap';
