# Stage 6 Looker Studio Dashboard

## Status

Stage 6 is in progress.

Completed repository work:

- Dashboard governance requirements
- Governed metric inventory
- Nine governed BigQuery dashboard views
- BigQuery assertions and consolidated quality status
- Looker Studio build specification
- Looker Studio field mapping
- Looker Studio validation checklist

Not yet completed:

- Looker Studio report construction
- Page configuration and chart validation
- Genuine screenshot evidence
- Reviewer sign-off
- Stage 6 evidence summary
- Root README completion update

Do not mark Stage 6 complete until the actual report is built, validated, evidenced, reviewed, committed, and pushed.

## Purpose

This directory contains the governed construction and validation documentation for the Stage 6 Looker Studio dashboard.

The dashboard must remain:

- Read-only
- Fully synthetic
- Aggregate-only
- Descriptive
- Non-operational
- Explicit about empty and invalid states
- Clear that forecasts are not observed outcomes
- Clear that selected for review is not approved outreach

## Documentation

### `looker_studio_build_spec.md`

Defines:

- Report identity
- Approved audiences
- Approved BigQuery data-source boundary
- Global governance language
- Six required dashboard pages
- Chart types
- Dimensions and metrics
- Filters and sorting
- Empty-state behaviour
- Refresh behaviour
- Completion criteria

### `looker_studio_field_mapping.md`

Defines:

- Approved Looker Studio field roles
- Default aggregations
- Display labels
- Safe calculated fields
- Formatting
- Validation-only fields
- Prohibited interpretations
- Per-view field restrictions

### `looker_studio_validation_checklist.md`

Defines the evidence-based checks required for:

- Report access
- Governance language
- Governed source connections
- Field configuration
- Privacy boundaries
- Six dashboard pages
- Filters and interactions
- Empty states
- Refresh behaviour
- Export and sharing restrictions
- Screenshots
- Reviewer sign-off
- Final Stage 6 acceptance

## Approved governed views

Looker Studio may connect only to:

- `dashboard_scoring_daily_summary`
- `dashboard_risk_distribution`
- `dashboard_observed_outcome_summary`
- `dashboard_activation_run_summary`
- `dashboard_activation_outcome_summary`
- `dashboard_activation_reason_summary`
- `dashboard_review_selection_summary`
- `dashboard_lineage_freshness_summary`
- `dashboard_quality_status`

Do not connect Looker Studio directly to upstream raw, staging, feature, scoring, activation, local artifact, or review-queue sources.

## Required dashboard pages

1. Executive overview
2. Model scoring overview
3. Activation governance
4. Human-review summary
5. Data quality and lineage
6. Methodology and limitations

## Required visible statements

Every page must visibly state:

> All dashboard data is fully synthetic and is shown for technical demonstration only.

Every page must also display or prominently link to these statements:

- Predictions are forecasts, not confirmed missed-goal outcomes.
- Selected for review means pending authorised human review, not approved outreach.
- Dashboard content is descriptive and does not establish causal intervention effects.
- Dashboard visibility does not authorise contact, messaging, case changes, eligibility changes, penalties, treatment, or clinical conclusions.

## Model distinction

| Model | Threshold | Dashboard status |
| --- | ---: | --- |
| `python_logistic_baseline` | `0.431` | Selected Stage 4 model; local artifact is not connected to Looker Studio |
| `bigquery_logistic_baseline` | `0.467` | Stage 3 comparison baseline used by governed forecast views |

The two thresholds must never be mixed.

## Current governed activation state

The warehouse currently contains:

```text
activation_runs: 0 rows
activation_decisions: 0 rows
```

This is a valid governed empty state.

The dashboard must not fabricate activation runs, decisions, contact context, or review records to populate charts.

Expected empty-state representations:

- One activation-run summary row
- Six activation-outcome rows
- Eleven activation-reason rows
- Four review-selection rows
- Zero counts
- Null rates
- Explicit empty-state language

## Screenshot evidence

Use this directory only after genuine report screenshots exist:

```text
dashboards/screenshots/
```

Do not commit placeholders, mock screenshots, or fabricated evidence.

## Build order

1. Connect only the approved governed views.
2. Verify field types and default aggregations.
3. Add global governance language.
4. Build the six report pages.
5. Validate filters, sorting, labels, and calculations.
6. Validate the governed activation empty state.
7. Validate access, sharing, export, and refresh controls.
8. Capture genuine screenshots.
9. Record reviewer results.
10. Add Stage 6 evidence documentation.
11. Update the root README and project status.
12. Run the complete repository quality gate.
13. Commit, push, verify hashes, and confirm a clean tree.

## Repository quality gate

Before staging or committing:

```powershell
ruff format --check .
```

```powershell
ruff check .
```

```powershell
mypy ".\src" ".\tests"
```

```powershell
pytest -q
```

```powershell
pre-commit run --all-files
```

```powershell
git diff --check
```

For changed files, run targeted hooks first.

After staging:

```powershell
git diff --cached --check
```

```powershell
git diff --cached --stat
```

## Completion boundary

This directory documents how to build and validate the dashboard. Documentation alone does not complete Stage 6.

Stage 6 is complete only after the actual Looker Studio report, genuine evidence, reviewer guidance, repository updates, full validation gate, commit, push, matching hashes, and clean working tree are all confirmed.
