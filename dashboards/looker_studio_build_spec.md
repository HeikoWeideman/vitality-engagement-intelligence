# Stage 6 Looker Studio Build Specification

## Status

This specification defines the governed construction contract for the Stage 6 Looker Studio dashboard.

The dashboard is a read-only technical demonstration using fully synthetic, aggregate data. It is not an operational system and does not authorise outreach, approval, case management, eligibility changes, penalties, treatment decisions, clinical conclusions, or causal claims.

## Report identity

- Report title: `Vitality Engagement Intelligence — Governed Dashboard`
- GCP project: `vitality-engagement-43999`
- BigQuery dataset: `vitality_engagement_dev`
- BigQuery location: `asia-southeast1`
- Access mode: Read-only
- Data classification: Fully synthetic
- Dashboard grain: Aggregate only

## Approved audiences

- Technical reviewer
- Model governance reviewer
- Data governance reviewer
- Authorised human reviewer

Dashboard access does not grant operational authority.

## Global governance banner

Every page must visibly display:

> All dashboard data is fully synthetic and is shown for technical demonstration only.

Every page must also display or provide a clearly visible link to these statements:

- Predictions are forecasts, not confirmed missed-goal outcomes.
- Selected for review means pending authorised human review, not approved outreach.
- Dashboard content is descriptive and does not establish causal intervention effects.
- Dashboard visibility does not authorise contact, messaging, case changes, eligibility changes, penalties, treatment, or clinical conclusions.

## Approved data-source boundary

Looker Studio may connect only to these governed aggregate views:

- `dashboard_scoring_daily_summary`
- `dashboard_risk_distribution`
- `dashboard_observed_outcome_summary`
- `dashboard_activation_run_summary`
- `dashboard_activation_outcome_summary`
- `dashboard_activation_reason_summary`
- `dashboard_review_selection_summary`
- `dashboard_lineage_freshness_summary`
- `dashboard_quality_status`

Direct Looker Studio access is prohibited for:

- Raw and staging tables
- `engagement_features_28d`
- `engagement_logistic_scoring_predictions`
- `activation_runs`
- `activation_decisions`
- Local Parquet artifacts
- Local human-review queue artifacts
- Member-level sources
- Dataset-level wildcard sources

## Global interaction controls

Allowed controls:

- Date-range controls
- Governed model-name filters
- Governed policy-version filters
- Aggregate outcome filters
- Aggregate intervention-category filters
- Navigation between report pages
- Informational links to repository documentation

Prohibited controls:

- Member search
- Member drill-through
- Row-level downloads
- Write-back
- Approval buttons
- Outreach controls
- Messaging controls
- Case controls
- Status-change controls
- Webhooks
- Embedded operational applications
- Links containing member identifiers

## Global display rules

- Forecast and observed-outcome metrics must remain visually and semantically distinct.
- Forecast metrics must never be labelled confirmed outcomes.
- Observed outcomes must never be labelled forecasts.
- Activation empty states must remain visible and must not be converted into fabricated records.
- Suppressed subgroup values must not be converted to zero.
- No member identifiers, member-level probabilities, exact priority ranks, or contact-context fields may appear.
- Looker Studio calculated fields may be used only for safe display formatting, approved labels, safe date grouping, and percentages derived from one governed view.
- Threshold logic, suppression, reconciliation, model selection, and business logic must remain in governed SQL views.

## Page 1 — Executive overview

### Purpose

Provide a high-level governed summary of asset availability, quality, forecast volume, observed labelled volume, and activation status.

### Data sources

- `dashboard_quality_status`
- `dashboard_lineage_freshness_summary`
- `dashboard_scoring_daily_summary`
- `dashboard_observed_outcome_summary`

### Components

| Component | Chart type | Source | Dimension | Metric | Filter or sort | Empty-state behaviour |
| --- | --- | --- | --- | --- | --- | --- |
| Synthetic-data banner | Text | None | None | None | None | Always visible |
| Governed asset health | Scorecard | `dashboard_quality_status` | None | `COUNT_DISTINCT(dashboard_view_name)` | Filter `quality_status = pass` | Show unavailable if source is invalid |
| Asset availability | Table | `dashboard_quality_status` | `dashboard_label` | `availability_status`, `quality_status`, `quality_summary` | Sort by `display_order` | Preserve `empty` as a valid governed state |
| Latest business date | Scorecard | `dashboard_lineage_freshness_summary` | None | Maximum latest business date | Exclude null dates | Show `No business date available` |
| Forecast volume | Scorecard | `dashboard_scoring_daily_summary` | None | Sum of forecast row count | All governed dates | Show zero only when governed source reports zero |
| Observed labelled volume | Scorecard | `dashboard_observed_outcome_summary` | None | Sum of observed labelled row count | Completed outcome windows only | Show unavailable if no completed windows exist |
| Activation state | Scorecard or text | `dashboard_activation_run_summary` | Freshness status | Source row count or run count | Latest governed run | Show `No governed activation runs are available` |
| Governance limitations | Text panel | None | None | None | None | Always visible |

### Required visible language

- Fully synthetic technical demonstration.
- Forecasts are not confirmed outcomes.
- Observed outcomes are descriptive and not causal.
- Dashboard visibility does not authorise operational action.

## Page 2 — Model scoring overview

### Purpose

Monitor aggregate Stage 3 BigQuery comparison-baseline forecasts without representing them as observed outcomes or as the selected Stage 4 activation model.

### Data sources

- `dashboard_scoring_daily_summary`
- `dashboard_risk_distribution`

### Components

| Component | Chart type | Source | Dimension | Metric | Filter or sort | Empty-state behaviour |
| --- | --- | --- | --- | --- | --- | --- |
| Forecast rows | Scorecard | `dashboard_scoring_daily_summary` | None | Sum of forecast row count | Selected date range | Show zero only if governed source reports zero |
| Daily forecast members | Scorecard | `dashboard_scoring_daily_summary` | None | `forecast_member_count` | Require one selected `prediction_date`; never sum across dates | Show unavailable unless one prediction date is selected |
| Mean forecast risk | Scorecard | `dashboard_scoring_daily_summary` | None | `SUM(mean_forecast_risk * forecast_row_count) / SUM(forecast_row_count)` | Selected date range; use fields from this governed view only | Show unavailable if denominator is zero |
| High-risk forecasts | Scorecard | `dashboard_scoring_daily_summary` | None | Sum of high-risk forecast count | Selected date range | Do not label as confirmed missed goals |
| High-risk forecast rate | Scorecard | `dashboard_scoring_daily_summary` | None | `SUM(high_risk_forecast_count) / SUM(forecast_row_count)` | Selected date range; use fields from this governed view only | Show unavailable if denominator is zero |
| Forecast count by date | Time series | `dashboard_scoring_daily_summary` | Prediction date | Forecast row count | Sort ascending by date | Show explicit no-data message |
| Mean forecast risk by date | Time series | `dashboard_scoring_daily_summary` | Prediction date | Mean forecast risk | Sort ascending by date | Show explicit no-data message |
| High-risk forecasts by date | Time series | `dashboard_scoring_daily_summary` | Prediction date | High-risk forecast count and rate | Sort ascending by date | Show explicit no-data message |
| Risk-band distribution | Stacked bar or 100% stacked bar | `dashboard_risk_distribution` | `prediction_date`, `risk_band` | `forecast_row_count` or `risk_band_forecast_rate` | Sort by `prediction_date`, then `risk_band_order` | Keep zero-count bands visible |
| Model contract | Text or table | Governed scoring sources | Model name | Frozen threshold | None | Always display model and threshold |

### Required model label

- Model: `bigquery_logistic_baseline`
- Dashboard label: `BigQuery comparison baseline`
- Frozen threshold: `0.467`
- Status: Stage 3 comparison baseline

The Stage 4 selected Python logistic threshold of `0.431` must not be substituted into these BigQuery forecast views.

### Required visible warning

> Forecasts are not confirmed outcomes.

## Page 3 — Activation governance

### Purpose

Show governed activation-run reconciliation, decision outcomes, reason-code distributions, and capacity metrics when legitimate activation runs exist.

### Data sources

- `dashboard_activation_run_summary`
- `dashboard_activation_outcome_summary`
- `dashboard_activation_reason_summary`

### Components

| Component | Chart type | Source | Dimension | Metric | Filter or sort | Empty-state behaviour |
| --- | --- | --- | --- | --- | --- | --- |
| Activation run state | Scorecard or text | `dashboard_activation_run_summary` | `freshness_status` | `COUNT(run_id)` or `source_row_count` | Latest governed run | Show `No governed activation runs are available` |
| Source rows | Scorecard | `dashboard_activation_run_summary` | None | Source row count | Selected run | Show zero in governed empty state |
| Source members | Scorecard | `dashboard_activation_run_summary` | None | Source member count | Selected run | Show zero in governed empty state |
| Eligible records | Scorecard | `dashboard_activation_run_summary` | None | Eligible count | Selected run | Show zero in governed empty state |
| Selected for review | Scorecard | `dashboard_activation_run_summary` | None | `selected_count` | Selected run | Label as pending authorised human review |
| Capacity utilisation | Gauge or scorecard | `dashboard_activation_run_summary` | None | Capacity utilisation rate | Selected run | Show unavailable when capacity is absent |
| Outcome distribution | Bar chart | `dashboard_activation_outcome_summary` | `outcome_label` | `decision_count` | Sort by `display_order` | Keep all six outcomes visible |
| Reason distribution | Bar chart | `dashboard_activation_reason_summary` | `reason_label` | `reason_count` | Sort by `display_order` | Keep all final reason categories visible |
| Reconciliation status | Table | `dashboard_activation_run_summary` | Run ID | Reconciliation fields and validity | Selected run | Show valid governed empty state |

### Required empty-state display

> No governed activation runs are available.

> Valid governed empty state.

No activation run, contact-context record, decision record, or review record may be fabricated to populate this page.

### Required visible warnings

- Selected for review means pending authorised human review.
- Selected for review does not mean approved outreach.
- No operational action is authorised from this dashboard.

## Page 4 — Human-review summary

### Purpose

Show aggregate supportive-intervention categories for records pending authorised human review without exposing a row-level review queue.

### Data source

- `dashboard_review_selection_summary`

### Components

| Component | Chart type | Source | Dimension | Metric | Filter or sort | Empty-state behaviour |
| --- | --- | --- | --- | --- | --- | --- |
| Pending human-review total | Scorecard | `dashboard_review_selection_summary` | None | `SUM(selection_count)` | Selected run if available | Show zero in governed empty state |
| Review selection distribution | Bar or donut chart | `dashboard_review_selection_summary` | `intervention_label` | `selection_count` | Sort by `display_order` | Keep all four categories visible |
| Selection share | Table or bar chart | `dashboard_review_selection_summary` | `intervention_label` | `selection_share` | Sort by `display_order`; selected run if available | Show unavailable when denominator is zero |
| Review governance state | Table | `dashboard_review_selection_summary` | Review state | Outreach approval state and operational-authorisation flag | None | Display pending/not-approved/false state |

### Approved supportive intervention categories

- Supportive check-in
- Goal planning
- Activity reminder
- Rewards education

### Required visible warnings

- Pending authorised human review.
- Not approved outreach.
- Dashboard visibility does not authorise contact.
- No row-level review queue is available in Looker Studio.

## Page 5 — Data quality and lineage

### Purpose

Expose aggregate source lineage, availability, freshness, governed row counts, and validation status.

### Data sources

- `dashboard_lineage_freshness_summary`
- `dashboard_quality_status`

### Components

| Component | Chart type | Source | Dimension | Metric | Filter or sort | Empty-state behaviour |
| --- | --- | --- | --- | --- | --- | --- |
| Governed asset inventory | Table | `dashboard_quality_status` | `dashboard_label` | `metric_class`, `availability_status`, `quality_status`, `quality_summary` | Sort by `display_order` | Preserve valid empty states |
| Quality pass count | Scorecard | `dashboard_quality_status` | None | `COUNT_DISTINCT(dashboard_view_name)` | Filter `quality_status = pass` | Show unavailable if quality source is invalid |
| Availability distribution | Bar or donut chart | `dashboard_quality_status` | `availability_status` | `COUNT_DISTINCT(dashboard_view_name)` | Sort by `availability_status` | Keep `available`, `empty`, and `unavailable` distinct |
| Lineage inventory | Table | `dashboard_lineage_freshness_summary` | `dashboard_view_name` | `source_table_names`, `source_table_count`, `lineage_status` | Sort by `display_order` | Show missing fields explicitly |
| Source row counts | Bar chart | `dashboard_lineage_freshness_summary` | `dashboard_view_name` | `source_row_count` | Sort descending by `source_row_count` | Preserve zero for legitimate empty sources |
| Latest business dates | Table | `dashboard_lineage_freshness_summary` | `dashboard_view_name` | `latest_business_date` | Sort descending by `latest_business_date` | Show unavailable for empty activation sources |
| Freshness state | Table | `dashboard_lineage_freshness_summary` | `dashboard_view_name` | `freshness_status`, `freshness_interpretation` | Sort by `display_order` | Distinguish `historical_snapshot`, `available`, `empty`, `missing`, and `missing_data` |
| Invalid reasons | Table | Both governed views | Governed asset | Invalid reason | Filter to invalid only when needed | Never expose member-level examples |

### Required visible language

- Historical snapshot means valid historical synthetic data, not current production data.
- Empty means a valid governed source currently contains no records.
- Missing and invalid states must not be hidden.
- Quality status does not authorise operational use.

## Page 6 — Methodology and limitations

### Purpose

Document metric semantics, source boundaries, model distinctions, empty-state handling, privacy controls, refresh behaviour, and prohibited interpretations.

### Data sources

No analytical source is required. Optional summary tables may use:

- `dashboard_quality_status`
- `dashboard_lineage_freshness_summary`

### Required sections

- Dashboard purpose
- Fully synthetic data statement
- Approved audiences
- Approved source boundary
- Metric classes
- Forecast-versus-observed distinction
- Stage 3 and Stage 4 model distinction
- Activation terminology
- Human-review terminology
- Minimum-cell suppression
- Empty activation-state policy
- Refresh behaviour
- Prohibited uses
- Known limitations
- Repository documentation references

### Model distinction

| Model | Threshold | Dashboard status |
| --- | ---: | --- |
| `python_logistic_baseline` | `0.431` | Selected Stage 4 model; local artifact not connected to Looker Studio |
| `bigquery_logistic_baseline` | `0.467` | Stage 3 BigQuery comparison baseline used by governed forecast views |

### Required limitations

- All data is synthetic.
- Synthetic results are not production evidence.
- Forecasts are not observed outcomes.
- Observed trends are descriptive, not causal.
- No intervention-effect claim is supported.
- No member-level access is provided.
- No outreach approval or operational action is provided.
- Empty activation sources are valid and are not populated with fabricated data.
- The minimum cell count of 10 is an engineering default for this portfolio project, not a claimed legal or production privacy standard.

## Refresh behaviour

- Refresh is read-only.
- Refresh may reevaluate governed BigQuery views.
- Refresh must not trigger scoring.
- Refresh must not create activation runs.
- Refresh must not upload local artifacts.
- Refresh must not create review records.
- Refresh must not approve outreach.
- Refresh must not initiate messaging or other downstream operations.
- Source freshness and business-date fields must remain visible where applicable.

## Empty-state validation

The completed dashboard must demonstrate:

- Forecast pages render governed historical snapshot data.
- Observed-outcome pages render completed non-null outcome windows.
- Activation pages display the valid governed empty state.
- All six activation outcomes remain represented with zero counts.
- All final activation reason categories remain represented with zero counts.
- All four supportive intervention categories remain represented with zero counts.
- Null rates remain unavailable rather than being displayed as zero.
- No synthetic activation records are created for visual completeness.

## Validation evidence required

For each page, capture evidence of:

- Page title
- Connected governed data source
- Chart configuration
- Dimension and metric mapping
- Applied filters
- Sort order
- Visible disclaimers
- Empty-state behaviour
- Model and threshold labels
- Absence of member-level fields
- Absence of operational controls
- Refresh configuration
- Screenshot filename
- Reviewer result

## Completion criteria

The dashboard build is complete only when:

1. All six pages exist.
2. Only governed `dashboard_*` views are connected.
3. Forecast and observed-outcome metrics remain distinct.
4. The BigQuery comparison baseline is clearly labelled with threshold `0.467`.
5. Selected-for-review is clearly distinct from approved outreach.
6. The empty activation state is explicit.
7. No member-level data is exposed.
8. No operational control or action exists.
9. Synthetic and non-causal disclaimers are visible.
10. Quality and lineage information is available.
11. Screenshots and validation evidence are stored in the repository.
12. Reviewer instructions and known limitations are documented.
13. The README and project status are updated.
14. The full repository quality gate passes.
15. Changes are committed and pushed.
