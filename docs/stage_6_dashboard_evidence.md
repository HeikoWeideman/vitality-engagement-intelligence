 Stage 6 Dashboard Evidence

## Report identity

- Report name: Vitality Engagement Intelligence - Governed Dashboard
- Platform: Google Looker Studio
- Environment: Development
- BigQuery project: vitality-engagement-43999
- BigQuery dataset: vitality_engagement_dev
- BigQuery location: asia-southeast1
- Dashboard pages: 5
- Evidence captured in View mode
- Data classification: Fully synthetic technical-demonstration data

## Governance statement

The dashboard is read-only, descriptive, aggregated, non-operational, and fully synthetic.

Forecasts are not confirmed outcomes. Observed outcomes are descriptive and not causal. Selected for review means pending human review and does not mean approved outreach. Dashboard visibility does not authorise operational action. Valid governed empty states are displayed without fabricating activation records.

## Page 1 - Executive overview

- Screenshot: dashboards/screenshots/01_executive_overview.png
- Validation status: Pass
- Governed assets passing: 8
- Latest governed business date: 2025-06-29
- Forecast rows: 3,500
- Completed outcome windows: 72,500
- Governed activation runs: 0
- Activation state: Valid governed empty state; no activation records were fabricated

## Page 2 - Model scoring overview

- Screenshot: dashboards/screenshots/02_model_scoring_overview.png
- Validation status: Pass
- Model: bigquery_logistic_baseline
- Frozen BigQuery comparison-baseline threshold: 0.467
- Forecast rows: 3,500 across seven prediction dates
- Forecast rows per prediction date: 500
- High-risk forecasts: 1,091
- Overall high-risk forecast rate: 31.17%
- Risk distribution: Five governed risk bands displayed in ascending order
- Interpretation: Forecasts are model estimates, not confirmed outcomes
- Stage distinction: This is not the selected Stage 4 activation model

## Page 3 - Observed outcomes

- Screenshot: dashboards/screenshots/03_observed_outcomes.png
- Validation status: Pass
- Completed outcome windows: 72,500
- Observed missed-goal count: 14,078
- Observed met-goal count: 58,422
- Overall observed missed-goal rate: 19.42%
- Completed prediction-date coverage: 2025-01-29 through 2025-06-22
- Latest completed outcome-window date: 2025-06-29
- Interpretation: Completed synthetic outcome labels are descriptive, not causal
- Limitation: Results do not demonstrate intervention effectiveness or model accuracy


## Page 4 - Activation audit

- Screenshot: dashboards/screenshots/04_activation_audit.png
- Validation status: Pass
- Governed activation runs: 0
- Activation outcomes: 6 governed empty-state rows, all with decision_count = 0
- Activation reasons: 11 governed empty-state rows, all with reason_count = 0
- Supportive intervention categories: 4 rows, all with selection_count = 0
- Review state: pending_human_review
- Outreach approval state: not_approved_outreach
- Interpretation: Selected for review means pending human review, not approved outreach
- Empty-state control: No activation, contact-context, or review records were fabricated

## Page 5 - Lineage and quality

- Screenshot: dashboards/screenshots/05_lineage_and_quality.png
- Validation status: Pass
- Governed dashboard assets: 8
- Quality status: All governed assets pass
- Governed lineage rows: 7
- Lineage status: Complete for all governed sources
- Forecast and observed sources: historical_snapshot
- Activation sources: Valid governed empty states
- Invalid reasons: None
- Interpretation: Historical snapshots and valid empty states are not quality failures

## Final validation

- All five report pages opened successfully in Looker Studio View mode
- No missing-data, configuration, or chart-rendering errors were observed
- Forecast and observed-outcome pages remained semantically separate
- The BigQuery comparison-baseline threshold remained fixed at 0.467
- Activation and review-selection sources displayed explicit governed empty states
- No member-level data, operational dispatch controls, or outreach-authorisation controls were included
- Dashboard visibility does not authorise operational action

## Reviewer sign-off

- Reviewer: Heiko Weideman
- Review date: 2026-08-06
- Review result: Pass
- Approved for final Stage 6 repository closure
