# Stage 7 Monitoring and Governance Evidence

## Evidence identity

- Project: Vitality Engagement Intelligence Engine
- Stage: Stage 7 — Monitoring and governance
- Environment: Development
- Evidence date: 2026-08-06
- Data classification: Fully synthetic technical-demonstration data
- BigQuery project: `vitality-engagement-43999`
- BigQuery dataset: `vitality_engagement_dev`
- BigQuery location: `asia-southeast1`

## Governance statement

The Stage 7 monitoring implementation is read-only, descriptive, non-operational, and fully synthetic.

Monitoring results do not authorise member contact, outreach, intervention delivery, case creation, eligibility changes, penalties, treatment assignment, model promotion, model replacement, retraining, or threshold changes.

Forecasts are not confirmed outcomes. Critical monitoring findings are preserved for human review and are not silently suppressed to obtain a passing status.

## Model identity separation

| Model | Threshold | Role |
| --- | ---: | --- |
| `python_logistic_baseline` | `0.431` | Selected Stage 4 Python model |
| `bigquery_logistic_baseline` | `0.467` | Stage 3 BigQuery comparison baseline |

The model names and thresholds remained separate throughout Stage 7 validation.

## Local Python monitoring evidence

### Command

    python -m vitality_engagement.monitoring.cli `
        --monitoring-timestamp "2026-08-06T11:22:00+07:00"

### Run result

- Run ID: `mon_d1edeb08deb3cfb3e379837f`
- Monitoring timestamp: 2026-08-06T11:22:00+07:00
- Monitoring timestamp in UTC: 2026-08-06T04:22:00+00:00
- Monitoring artifact: `artifacts/monitoring/monitoring_checks.parquet`
- Monitoring metadata: `artifacts/monitoring/monitoring_checks.metadata.json`
- Checks evaluated: 57
- Passing checks: 53
- Warning checks: 2
- Critical checks: 2
- Overall severity: Critical
- CLI exit code: `2`
- Execution mode: Local artifacts only
- External alerting: Disabled
- Operational actions: Disabled

Exit code `2` represents a successfully completed monitoring run containing at least one governed critical finding.

## Local non-passing checks

| Check | Type | Observed value | Warning threshold | Critical threshold | Severity |
| --- | --- | ---: | ---: | ---: | --- |
| Probability population stability index | Probability drift | `0.155921` | `0.10` | `0.25` | Warning |
| `previous_goal_streak_as_of` PSI | Numeric feature drift | `1.559510` | `0.10` | `0.25` | Critical |
| `previous_failed_goals_as_of` PSI | Numeric feature drift | `0.290255` | `0.10` | `0.25` | Critical |
| `avg_goal_completion_percentage_28d` PSI | Numeric feature drift | `0.109969` | `0.10` | `0.25` | Warning |

## Distribution investigation

### `previous_goal_streak_as_of`

| Statistic | Training | Scoring |
| --- | ---: | ---: |
| Rows | 46,000 | 3,500 |
| Missing rate | `0.000000` | `0.000000` |
| Unique values | 18 | 26 |
| Mean | `6.420826` | `12.836000` |
| Median | `6.000000` | `16.000000` |
| 75th percentile | `10.000000` | `24.000000` |
| Maximum | `17.000000` | `25.000000` |

### `previous_failed_goals_as_of`

| Statistic | Training | Scoring |
| --- | ---: | ---: |
| Rows | 46,000 | 3,500 |
| Missing rate | `0.000000` | `0.000000` |
| Unique values | 18 | 26 |
| Mean | `2.167217` | `5.184857` |
| Median | `1.000000` | `2.000000` |
| 75th percentile | `3.000000` | `8.000000` |
| Maximum | `17.000000` | `25.000000` |

### `avg_goal_completion_percentage_28d`

| Statistic | Training | Scoring |
| --- | ---: | ---: |
| Rows | 46,000 | 3,500 |
| Missing rate | `0.000000` | `0.000000` |
| Unique values | 28,493 | 3,326 |
| Mean | `71.340385` | `68.197270` |
| Median | `71.253571` | `69.278571` |
| 75th percentile | `78.882143` | `78.141964` |
| Maximum | `113.270370` | `115.821429` |

## Finding interpretation

The feature-generation source confirms:

- `previous_failed_goals` is a cumulative count of prior failed goals.
- `previous_goal_streak` measures consecutive prior completed goals.
- Both values are carried into the feature table as the latest historical value available at each prediction anchor.
- `avg_goal_completion_percentage_28d` is a rolling 28-day historical average.

The two critical findings therefore represent genuine temporal shift and model extrapolation concerns. They are not treated as missingness, schema, or execution defects.

The results do not prove data corruption, clinical risk, intervention need, or causal effect.

## Local artifact controls

The local monitoring workflow verified:

- Modelling-data lineage
- Persisted-model lineage
- Model-metadata lineage
- Scoring-prediction lineage
- Scoring-metadata lineage
- Model identity
- Threshold identity
- Feature-schema identity
- Scoring identifier reconciliation
- Probability validity
- Monitoring metadata reconciliation
- Atomic temporary-file verification
- Input/output path separation
- Tamper rejection

The metadata preserves SHA-256 digests for all governed source artifacts.

## Python test evidence

The complete Stage 7 Python test slice passed, including:

- Monitoring policy tests
- Monitoring schema tests
- PSI and drift tests
- Monitoring engine tests
- Atomic artifact tests
- Orchestrator tests
- CLI tests
- Existing activation CLI regression tests

Static validation passed for the monitoring package:

- Ruff format check: Pass
- Ruff lint check: Pass
- Mypy: Pass

## BigQuery model-monitoring evidence

### View

- `vitality_engagement_dev.model_monitoring_status`

### SQL assertion

- `sql/tests/15_assert_model_monitoring_status.sql`

### Validation result

- Dry run: Pass
- View creation: Pass
- Assertions: 11 of 11 successful
- Governed checks: 11
- Passing checks: 9
- Warning checks: 0
- Critical checks: 2
- Overall severity: Critical
- Model: `bigquery_logistic_baseline`
- Threshold: `0.467`
- Operational action authorised: False

### BigQuery passing checks

- Scoring row count: `3,500`
- Distinct scoring members: `500`
- Distinct scoring dates: `7`
- Duplicate member-date keys: `0`
- Null probabilities: `0`
- Out-of-range probabilities: `0`
- Threshold mismatches: `0`
- Scoring-source row difference: `0`
- Latest governed scoring date: `2025-06-29`

### BigQuery critical checks

| Check | Observed value | Expected value | Severity |
| --- | ---: | ---: | --- |
| `previous_goal_streak_training_support_breach_count` | `1,708` | `0` | Critical |
| `previous_failed_goals_training_support_breach_count` | `268` | `0` | Critical |

Training support maximum for both features was `17`; the scoring maximum was `25`.

## BigQuery governance-monitoring evidence

### View

- `vitality_engagement_dev.governance_monitoring_status`

### SQL assertion

- `sql/tests/16_assert_governance_monitoring_status.sql`

### Validation result

- Dry run: Pass
- View creation: Pass
- Assertions: 11 of 11 successful
- Governed checks: 3
- Passing checks: 3
- Warning checks: 0
- Critical checks: 0
- Overall severity: Pass
- Operational action authorised: False

### Governance checks

| Check | Observed value | Expected value | Severity |
| --- | ---: | ---: | --- |
| Activation empty-state validity | `0` invalid states | `0` | Pass |
| Dashboard quality status | `0` invalid assets | `0` | Pass |
| Dashboard lineage and freshness | `0` invalid lineage rows | `0` | Pass |

Supporting source state:

- Activation runs: `0`
- Activation decisions: `0`
- Governed dashboard assets: `8`
- Governed dashboard lineage rows: `7`

The empty activation state remained valid. No activation or review records were fabricated.

## BigQuery correction evidence

Initial execution of the model-monitoring assertion exposed an unsupported BigQuery expression:

- Unsupported expression: `COUNT(DISTINCT STRUCT(...))`
- BigQuery error: Aggregate functions with `DISTINCT` cannot use `STRUCT` arguments

The view was corrected to calculate duplicate member-date rows through a grouped key-count CTE.

After correction:

- Dry run: Pass
- View replacement: Pass
- All assertions: Pass

The failure and correction were preserved rather than bypassed.

## Safety and governance validation

Stage 7 confirmed:

- All data remained fully synthetic.
- Monitoring remained read-only.
- The Python and BigQuery model identities remained separate.
- Critical findings were not reclassified merely to pass.
- Valid empty activation states remained empty.
- Dashboard quality remained passing.
- Dashboard lineage remained complete.
- No member-level operational export was created.
- No external alert or webhook was configured.
- No operational action was authorised.
- Human review remains required for interpretation and escalation.

## Final review status

- Implementation validation: Pass
- Monitoring execution: Completed
- Critical findings preserved: Yes
- Governance checks: Pass
- BigQuery assertions: Pass
- Full repository quality gate: Pass
- Repository closure actions: Commit, push, hash verification, and clean-tree confirmation follow this evidence update

## Reviewer sign-off

- Reviewer: Heiko Weideman
- Review date: 2026-08-06
- Review result: Pass
- Approved for final Stage 7 repository closure
