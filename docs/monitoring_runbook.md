# Stage 7 Monitoring Runbook

## Purpose

This runbook covers the governed Stage 7 monitoring workflow for the Vitality Engagement Intelligence Engine.

The workflow verifies local modelling, model, and scoring artifacts; evaluates deterministic monitoring checks; writes verified local monitoring artifacts; and validates read-only BigQuery monitoring views.

It does not upload local monitoring artifacts, contact members, dispatch interventions, approve outreach, create cases, change eligibility, assign treatment, retrain models, promote models, or change thresholds.

All data is fully synthetic technical-demonstration data.

## Governed model identities

The two model implementations are separate:

| Model | Threshold | Role |
| --- | ---: | --- |
| `python_logistic_baseline` | `0.431` | Selected Stage 4 Python model |
| `bigquery_logistic_baseline` | `0.467` | Stage 3 comparison baseline |

Do not substitute one threshold for the other.

## Preconditions

Before running local monitoring, confirm:

1. The virtual environment is active.
2. The repository contains the expected Stage 4 modelling and model artifacts.
3. The verified scoring artifact and metadata exist.
4. The monitoring timestamp includes a timezone offset.
5. Input and output paths do not overlap.
6. The run is being performed for technical monitoring and human review only.
7. No automatic operational action is connected to the command.
8. Existing artifacts that may be replaced have been preserved when evidence retention is required.

## Default local inputs

The default monitored inputs are:

- `data/modeling/engagement_modeling_split.parquet`
- The persisted selected Python model
- The persisted selected-model metadata
- `artifacts/scoring/python_logistic_scoring_predictions.parquet`
- `artifacts/scoring/python_logistic_scoring_predictions.metadata.json`

The exact model and metadata paths are defined by the Stage 4 persistence module defaults.

## Local command

Run monitoring with an explicit timezone-aware timestamp:

    python -m vitality_engagement.monitoring.cli `
        --monitoring-timestamp "2026-08-06T11:22:00+07:00"

The timestamp above is the governed Stage 7 evidence-run timestamp. Use a new explicit timestamp for any later monitoring run.

## Expected local outputs

The default outputs are:

- `artifacts/monitoring/monitoring_checks.parquet`
- `artifacts/monitoring/monitoring_checks.metadata.json`

The Parquet artifact contains one row per monitoring check.

The metadata records:

- Deterministic monitoring run ID
- Monitoring timestamp
- Policy version and fingerprint
- Overall severity
- Selected Python model identity and threshold
- Source paths
- SHA-256 lineage
- Reference and current row counts
- Check counts by severity
- Exact output columns

## Local exit codes

| Exit code | Meaning |
| ---: | --- |
| `0` | Overall severity is pass or warning |
| `2` | At least one governed check is critical |
| Other non-zero value | Execution, verification, or argument failure |

Exit code `2` represents a completed monitoring run with a critical governed finding. It is not equivalent to an unhandled execution failure.

## Expected local evidence result

The governed Stage 7 evidence run produced:

- Run ID: `mon_d1edeb08deb3cfb3e379837f`
- Checks evaluated: `57`
- Passing checks: `53`
- Warning checks: `2`
- Critical checks: `2`
- Overall severity: `critical`
- CLI exit code: `2`

Non-passing checks:

| Check | Observed value | Severity |
| --- | ---: | --- |
| Probability PSI | `0.155921` | Warning |
| `previous_goal_streak_as_of` PSI | `1.559510` | Critical |
| `previous_failed_goals_as_of` PSI | `0.290255` | Critical |
| `avg_goal_completion_percentage_28d` PSI | `0.109969` | Warning |

## Interpreting the current critical result

The critical result is retained as a genuine monitoring finding.

The two critical features contain historical goal-state values that extend beyond the training support:

- Training maximum: `17`
- Scoring maximum: `25`

BigQuery confirms:

- `1,708` scoring rows exceed the training maximum for `previous_goal_streak_as_of`
- `268` scoring rows exceed the training maximum for `previous_failed_goals_as_of`

These values indicate temporal shift and model extrapolation risk. They must not be silently suppressed or reclassified merely to produce a passing result.

The result does not prove data corruption, clinical risk, causal effect, or intervention need.

## Inspecting non-passing local checks

Use:

    @'
    import pandas as pd

    checks = pd.read_parquet(
        "artifacts/monitoring/monitoring_checks.parquet"
    )

    columns = [
        "check_name",
        "check_type",
        "severity",
        "feature_name",
        "observed_value",
        "expected_value",
        "warning_threshold",
        "critical_threshold",
        "details",
    ]

    print(
        checks.loc[
            checks["severity"].isin(["warning", "critical"]),
            columns,
        ].to_string(index=False)
    )
    '@ | python -

## Fail-closed local behaviour

The local workflow rejects:

- Missing source files
- Invalid model or scoring metadata
- Scoring-artifact tampering
- Invalid SHA-256 lineage
- Duplicate scoring identifiers
- Probability values outside zero to one
- Model or threshold mismatches
- Feature-schema mismatches
- Invalid monitoring policy values
- Naive timestamps
- Non-finite monitoring values
- Input/output path collisions
- Monitoring metadata mismatches
- Monitoring artifact tampering

The orchestrator validates path safety before loading inputs.

Monitoring artifacts are written to temporary files, reloaded, verified, and atomically moved into place only after successful reconciliation.

## BigQuery monitoring views

Stage 7 creates:

- `vitality_engagement_dev.model_monitoring_status`
- `vitality_engagement_dev.governance_monitoring_status`

The model-monitoring view evaluates the BigQuery comparison baseline using threshold `0.467`.

The governance-monitoring view evaluates:

- Activation empty-state validity
- Dashboard quality status
- Dashboard lineage and freshness status

Both views are read-only and set `operational_action_authorised` to `FALSE`.

## BigQuery execution

The governed SQL runner is:

- `scripts/run_bigquery_sql.ps1`

Dry-run a view before creation:

    .\scripts\run_bigquery_sql.ps1 `
        -SqlFile .\sql\monitoring\01_create_model_monitoring_status.sql `
        -ProjectId "vitality-engagement-43999" `
        -DatasetId "vitality_engagement_dev" `
        -Location "asia-southeast1" `
        -MaximumBytesBilled 100000000 `
        -DryRun

Create the model-monitoring view:

    .\scripts\run_bigquery_sql.ps1 `
        -SqlFile .\sql\monitoring\01_create_model_monitoring_status.sql `
        -ProjectId "vitality-engagement-43999" `
        -DatasetId "vitality_engagement_dev" `
        -Location "asia-southeast1" `
        -MaximumBytesBilled 100000000

Run its assertions:

    .\scripts\run_bigquery_sql.ps1 `
        -SqlFile .\sql\tests\15_assert_model_monitoring_status.sql `
        -ProjectId "vitality-engagement-43999" `
        -DatasetId "vitality_engagement_dev" `
        -Location "asia-southeast1" `
        -MaximumBytesBilled 100000000

Create the governance-monitoring view:

    .\scripts\run_bigquery_sql.ps1 `
        -SqlFile .\sql\monitoring\02_create_governance_monitoring_status.sql `
        -ProjectId "vitality-engagement-43999" `
        -DatasetId "vitality_engagement_dev" `
        -Location "asia-southeast1" `
        -MaximumBytesBilled 100000000

Run its assertions:

    .\scripts\run_bigquery_sql.ps1 `
        -SqlFile .\sql\tests\16_assert_governance_monitoring_status.sql `
        -ProjectId "vitality-engagement-43999" `
        -DatasetId "vitality_engagement_dev" `
        -Location "asia-southeast1" `
        -MaximumBytesBilled 100000000

## Expected BigQuery evidence

### Model monitoring

Expected result:

- Governed checks: `11`
- Passing checks: `9`
- Warning checks: `0`
- Critical checks: `2`
- Overall severity: `critical`
- Model: `bigquery_logistic_baseline`
- Threshold: `0.467`

Expected critical checks:

- `previous_goal_streak_training_support_breach_count`: `1,708`
- `previous_failed_goals_training_support_breach_count`: `268`

### Governance monitoring

Expected result:

- Governed checks: `3`
- Passing checks: `3`
- Warning checks: `0`
- Critical checks: `0`
- Overall severity: `pass`

Expected source state:

- Activation runs: `0`
- Activation decisions: `0`
- Governed dashboard assets: `8`
- Governed lineage rows: `7`

The empty activation state is valid and must not be replaced with fabricated records.

## Warning-response procedure

For a warning:

1. Preserve the monitoring artifacts and source lineage.
2. Record the affected check and observed value.
3. Compare reference and scoring distributions.
4. Review feature construction and time boundaries.
5. Assess whether the shift is expected or unexplained.
6. Record the review decision before the next governed scoring release.

## Critical-response procedure

For a critical result:

1. Preserve all local and warehouse evidence.
2. Confirm model name, threshold, schema, and SHA-256 lineage.
3. Reproduce the result using frozen inputs.
4. Inspect the affected feature distributions.
5. Check missingness, category domains, temporal accumulation, and support boundaries.
6. Determine whether the cause is corruption, implementation error, expected shift, or model extrapolation.
7. Record unresolved risks.
8. Require explicit human review before future model-development or scoring-release decisions.

Do not clear a critical result solely by changing a monitoring threshold.

## Prohibited automated responses

A monitoring finding must not automatically trigger:

- Member contact
- Outreach
- Intervention delivery
- Case creation
- Eligibility changes
- Penalties
- Treatment assignment
- Model retraining
- Model replacement
- Model promotion
- Threshold changes

## Review checklist

Before closing a monitoring run, confirm:

- The timestamp was timezone-aware.
- The expected model and threshold were used.
- The scoring artifact passed verification.
- All source digests were recorded.
- The check count reconciles.
- The overall severity equals the maximum check severity.
- Warning and critical findings were preserved.
- Local outputs passed artifact verification.
- BigQuery assertions passed.
- Valid activation empty states remained empty.
- Dashboard quality and lineage checks passed.
- No operational action was authorised.
- The review outcome and unresolved risks were documented.

## Human accountability

A successful command or passing assertion does not replace human review.

The reviewer remains responsible for interpreting findings, preserving limitations, deciding whether the technical demonstration remains suitable, and ensuring no monitoring result is used as an operational, clinical, eligibility, or outreach decision.
