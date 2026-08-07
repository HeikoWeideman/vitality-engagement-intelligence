# Stage 7 Monitoring and Governance Policy

## Purpose

This policy defines the governed monitoring controls for the Vitality Engagement Intelligence Engine.

Stage 7 evaluates model inputs, scoring outputs, artifact lineage, warehouse scoring integrity, dashboard quality, lineage freshness, and valid activation empty states.

The monitoring layer is read-only and descriptive. It does not contact members, dispatch interventions, approve outreach, assign treatment, determine eligibility, apply penalties, or authorise operational action.

## Scope

The governed monitoring implementation includes:

- Local Python monitoring for the selected Stage 4 model
- Verified local Parquet and JSON monitoring artifacts
- BigQuery monitoring for the separate Stage 3 comparison baseline
- Dashboard quality and lineage monitoring
- Activation empty-state monitoring
- Deterministic severity classification
- Human review and incident-response guidance

All data is fully synthetic technical-demonstration data.

## Model identity boundary

The two model implementations must remain explicitly separate.

| Model | Threshold | Governed role |
| --- | ---: | --- |
| `python_logistic_baseline` | `0.431` | Selected Stage 4 Python model |
| `bigquery_logistic_baseline` | `0.467` | Stage 3 BigQuery comparison baseline |

The BigQuery baseline must not be represented as the selected activation model.

Monitoring results from one model must not be attributed to the other model. Thresholds must not be mixed or silently substituted.

## Reference and current populations

Local Python drift monitoring uses:

- Reference features: chronological training split
- Current features: final seven-day scoring split
- Reference probabilities: frozen selected Python model applied to the training split
- Current probabilities: verified Python scoring artifact
- Validation and test rows: excluded from the drift reference

The governed historical split is:

- Training: 2025-01-29 through 2025-04-30
- Validation: 2025-05-01 through 2025-05-31
- Test: 2025-06-01 through 2025-06-22
- Scoring: 2025-06-23 through 2025-06-29

This is a historical synthetic snapshot, not a live production feed.

## Local monitoring checks

The local monitoring engine evaluates 57 checks:

- Expected scoring row count
- Expected distinct member count
- Expected scoring-day count
- Model identity
- Threshold identity
- Feature-schema identity
- Scoring-feature and prediction-key reconciliation
- Probability population stability index
- Numeric feature population stability index
- Categorical feature population stability index
- Unexpected categorical value rate

The expected scoring population is:

- 3,500 rows
- 500 distinct synthetic members
- Seven scoring dates

## Population stability index thresholds

Population stability index thresholds are:

| PSI value | Severity |
| ---: | --- |
| Below `0.10` | Pass |
| `0.10` to below `0.25` | Warning |
| `0.25` or above | Critical |

PSI is a distribution-comparison signal. It does not establish data corruption, model failure, causality, clinical significance, or intervention effectiveness.

Missing numeric values are evaluated as an explicit additional bin. Categorical missingness is represented explicitly.

## Unexpected categorical values

Unexpected-category rates use the approved synthetic categorical domains.

| Unexpected rate | Severity |
| ---: | --- |
| Below `0.01` | Pass |
| `0.01` to below `0.05` | Warning |
| `0.05` or above | Critical |

The selected model can technically process unseen categories, but their appearance remains a governed monitoring signal.

## Severity classification

### Pass

A pass means the observed value remains within the governed contract or configured monitoring threshold.

A pass does not prove real-world validity, fairness, clinical value, causal effectiveness, or production readiness.

### Warning

A warning means a measurable shift has reached the configured review range.

Warnings require documented human review before a future scoring release is treated as routine.

Warnings do not automatically invalidate artifacts or authorise corrective operational action.

### Critical

A critical result means one or more governed contracts, support boundaries, or critical thresholds were breached.

The local CLI returns exit code `2` when the overall severity is critical.

A critical result must be preserved and investigated. Thresholds must not be weakened merely to produce a passing result.

Critical monitoring does not itself authorise model replacement, member contact, intervention delivery, eligibility changes, penalties, or clinical action.

## Current governed Stage 7 finding

The verified historical scoring snapshot produced the following local findings:

| Check | Observed value | Severity |
| --- | ---: | --- |
| Probability PSI | `0.155921` | Warning |
| `previous_goal_streak_as_of` PSI | `1.559510` | Critical |
| `previous_failed_goals_as_of` PSI | `0.290255` | Critical |
| `avg_goal_completion_percentage_28d` PSI | `0.109969` | Warning |

The cumulative and streak-related features extend beyond the training support:

- Training maximum: `17`
- Scoring maximum: `25`
- BigQuery scoring rows above the training maximum for `previous_goal_streak_as_of`: `1,708`
- BigQuery scoring rows above the training maximum for `previous_failed_goals_as_of`: `268`

These findings are retained as genuine extrapolation and temporal-shift concerns. They are not suppressed as implementation errors.

## BigQuery monitoring boundary

The BigQuery monitoring layer evaluates the Stage 3 comparison baseline using threshold `0.467`.

It verifies:

- Scoring row, member, and day counts
- Member-date key uniqueness
- Non-null probabilities
- Probability range
- Threshold reconciliation
- Scoring-source row reconciliation
- Historical scoring date
- Training-support breaches for cumulative goal features

The BigQuery monitoring view is:

- `vitality_engagement_dev.model_monitoring_status`

The governance monitoring view is:

- `vitality_engagement_dev.governance_monitoring_status`

These are read-only views and authorise no operational action.

## Dashboard and activation governance checks

Governance monitoring verifies:

- All eight governed dashboard assets pass their embedded quality checks
- All seven dashboard lineage rows are complete and valid
- Empty activation sources remain explicit valid empty states
- No activation records are fabricated merely to make monitoring pass
- Operational action remains unauthorised

Selected for review means pending human review only. It does not mean approved outreach.

## Artifact and lineage controls

The local monitoring workflow writes:

- `artifacts/monitoring/monitoring_checks.parquet`
- `artifacts/monitoring/monitoring_checks.metadata.json`

The workflow records SHA-256 lineage for:

- Modelling data
- Persisted model
- Model metadata
- Scoring predictions
- Scoring metadata

The monitoring run ID is deterministic for the governed inputs and monitoring timestamp.

Temporary files are written, reloaded, reconciled, and verified before atomically replacing final outputs.

Input and output paths must remain distinct.

## Fail-closed behaviour

The monitoring workflow rejects:

- Missing input artifacts
- Invalid SHA-256 lineage
- Invalid or inconsistent model metadata
- Invalid scoring artifacts
- Duplicate scoring identifiers
- Probability values outside zero to one
- Model or threshold mismatches
- Unexpected output schemas
- Non-finite monitoring observations
- Metadata reconciliation failures
- Naive monitoring timestamps
- Input and output path collisions
- Tampered monitoring artifacts

Verification failures must occur before final monitoring outputs are written.

## Review and escalation policy

### Warning review

For a warning:

1. Preserve the original artifacts and metadata.
2. Record the affected check and observed value.
3. Compare the reference and scoring distributions.
4. Check whether the shift follows known synthetic temporal construction.
5. Assess whether the affected feature materially contributes to predictions.
6. Document the review outcome before the next governed scoring release.

### Critical review

For a critical result:

1. Stop treating the scoring release as routine.
2. Preserve all source and monitoring artifacts.
3. Confirm model, threshold, schema, and SHA-256 lineage.
4. Reproduce the result using the same frozen inputs.
5. Investigate feature support, temporal construction, missingness, and category domains.
6. Compare probability and feature shifts.
7. Document whether the finding represents corruption, implementation error, expected temporal accumulation, or model extrapolation.
8. Require explicit human approval before any future model promotion or scoring release decision.

No critical result may be cleared solely by increasing a threshold.

## Prohibited interpretations and actions

Monitoring output must not be used to claim:

- Clinical risk
- Diagnosis
- Treatment need
- Causal intervention effectiveness
- Member eligibility
- Insurance or employment suitability
- Fault, blame, or misconduct
- Confirmed future behaviour

Monitoring output must not automatically trigger:

- Member messaging
- Outreach
- Intervention delivery
- Case creation
- Eligibility changes
- Penalties
- Treatment assignment
- Model retraining
- Model promotion
- Threshold changes

## Human accountability

A human reviewer remains responsible for:

- Interpreting warnings and critical findings
- Confirming whether artifacts remain suitable for technical demonstration
- Approving any model-development response
- Recording limitations and unresolved risks
- Ensuring all downstream use remains synthetic, read-only, and non-operational
