# Stage 6 Dashboard Metric Inventory

## Status

This inventory defines the approved metrics, dimensions, terminology, and source boundaries for the Stage 6 governed Looker Studio dashboard.

Looker Studio must not connect directly to raw, staging, scoring, activation-decision, or local artifact sources. Dashboard metrics must be supplied by governed aggregate BigQuery views.

## Metric classes

Every dashboard metric must belong to exactly one class:

| Metric class | Meaning |
| --- | --- |
| Synthetic descriptive | Aggregate properties of synthetic historical data |
| Forecast | Predictive model output for a future seven-day risk window |
| Observed outcome | Completed future-window labels |
| Activation audit | Governed activation decision and capacity counts |
| Lineage | Model, policy, source, and timestamp provenance |
| Data quality | Completeness, uniqueness, reconciliation, and freshness |

Forecasts and observed outcomes must never be combined under an ambiguous label.

## Approved upstream sources

| Source | Approved purpose | Direct Looker access |
| --- | --- | --- |
| `engagement_features_28d` | Historical features and completed outcome labels | Prohibited |
| `engagement_logistic_scoring_predictions` | Stage 3 BigQuery baseline comparison | Prohibited |
| `activation_runs` | Run summaries, capacity, reconciliation, and lineage | Prohibited |
| `activation_decisions` | Aggregated outcomes and reason-code distributions | Prohibited |

The selected Stage 4 Python scoring artifact remains local. It must not be uploaded or recreated merely to populate the dashboard.

The local human-review queue is not an approved dashboard source.

## Required view fields

Every governed dashboard view must include:

| Field | Definition |
| --- | --- |
| `synthetic_data` | Constant Boolean `TRUE` |
| `data_classification` | Constant string `fully_synthetic` |
| `metric_class` | One approved metric class |
| `source_name` | Governed upstream source |
| `source_as_of` | Latest relevant source date or timestamp |
| `view_refreshed_at` | View evaluation timestamp |
| `is_valid` | Whether required quality checks pass |
| `invalid_reason` | Null when valid; otherwise a safe aggregate message |

A view without a valid synthetic-data marker is invalid.

## Planned governed views

| View | Grain |
| --- | --- |
| `dashboard_scoring_daily_summary` | Model and prediction date |
| `dashboard_risk_distribution` | Model, prediction date, and risk band |
| `dashboard_observed_outcome_summary` | Prediction or outcome date |
| `dashboard_activation_run_summary` | Activation run |
| `dashboard_activation_outcome_summary` | Run and decision outcome |
| `dashboard_activation_reason_summary` | Run, outcome, and reason code |
| `dashboard_review_summary` | Run and intervention category |
| `dashboard_lineage_freshness` | Governed source |
| `dashboard_quality_status` | Validation check |

## Forecast metrics

### Forecast row count

- Metric: `forecast_row_count`
- Formula: count of valid governed scoring rows
- Label: Forecast rows
- Prohibited label: Confirmed outcomes

### Forecast member count

- Metric: `forecast_member_count`
- Formula: distinct synthetic member count calculated before identifiers are removed
- Member identifiers must not appear in the view output

### Mean forecast risk

- Metric: `mean_forecast_risk`
- Formula: average risk probability
- Valid range: `0.0` through `1.0`
- Display: percentage
- Prohibited label: Miss rate

### High-risk forecast count

- Metric: `high_risk_forecast_count`
- Formula: count where probability meets the model-specific frozen threshold
- Required dimensions: model name, threshold, and prediction date
- Label: High-risk forecasts
- Prohibited label: Members who will miss their goal

### High-risk forecast rate

- Metric: `high_risk_forecast_rate`
- Formula: high-risk forecast count divided by forecast row count
- Numerator and denominator must use the same model, date, and valid population

## Approved risk bands

| Risk band | Rule |
| --- | --- |
| `0.00_to_0.20` | Probability below `0.20` |
| `0.20_to_0.40` | Probability from `0.20` to below `0.40` |
| `0.40_to_0.60` | Probability from `0.40` to below `0.60` |
| `0.60_to_0.80` | Probability from `0.60` to below `0.80` |
| `0.80_to_1.00` | Probability from `0.80` through `1.00` |

Risk bands are forecast groupings. They are not severity, diagnosis, or treatment categories.

## Approved model labels

| Model | Threshold | Status |
| --- | ---: | --- |
| `python_logistic_baseline` | `0.431` | Selected Stage 4 model |
| `bigquery_logistic_baseline` | `0.467` | Stage 3 comparison baseline |

The BigQuery baseline must not be labelled selected, operational, or activation-driving.

Any model comparison must display both model name and threshold.

## Observed-outcome metrics

Observed outcomes may use only rows where `label_will_miss_goal_next_7_days` is non-null.

### Completed outcome windows

- Metric: `observed_labelled_row_count`
- Formula: count of rows with a complete future outcome window

### Observed missed-goal count

- Metric: `observed_missed_goal_count`
- Formula: count where the completed future label is true
- Null future labels must be excluded

### Observed missed-goal rate

- Metric: `observed_missed_goal_rate`
- Formula: observed missed-goal count divided by completed outcome windows
- Required label: Synthetic observed missed-goal rate

Observed outcomes must not be joined to intervention history in a way that implies intervention effectiveness.

## Synthetic descriptive metrics

Approved historical aggregate metrics include:

- `avg_goal_completion_percentage_28d`
- `avg_active_minutes_28d`
- `avg_daily_steps_28d`
- `avg_app_sessions_28d`
- `avg_sleep_hours_28d`
- `active_day_count_28d_avg`
- `reward_redemption_rate_28d`
- `intervention_open_rate_28d`
- `intervention_click_rate_28d`
- `unavailable_day_count_28d_avg`
- `sleep_missing_day_count_28d_avg`
- `app_sessions_missing_day_count_28d_avg`

Intervention open and click rates are synthetic descriptive measures. They must not be labelled effectiveness, impact, uplift, or causal response.

## Activation run metrics

Activation metrics are available only when legitimate governed activation runs exist.

Approved metrics:

| Metric | Definition |
| --- | --- |
| `source_row_count` | Number of scoring rows audited |
| `source_member_count` | Number of non-superseded synthetic members |
| `capacity_limit` | Maximum records selectable for human review |
| `eligible_count` | Eligible records before capacity selection |
| `selected_for_review_count` | Records selected for authorised human review |
| `capacity_not_selected_count` | Eligible records not selected because capacity was reached |
| `capacity_utilisation_rate` | Selected count divided by capacity limit |

Required reconciliation rules:

- All six decision outcomes must sum to `source_row_count`.
- `source_member_count` must equal `source_row_count - superseded_count`.
- `eligible_count` must equal selected count plus capacity-not-selected count.
- Selected count must not exceed capacity limit.
- Capacity utilisation must not exceed `100%`.

Capacity and selection do not authorise outreach.

## Activation outcomes

| Outcome | Dashboard label |
| --- | --- |
| `selected_for_review` | Selected for human review |
| `no_contact_superseded` | No contact — superseded prediction |
| `no_contact_below_threshold` | No contact — below frozen threshold |
| `no_contact_excluded` | No contact — excluded |
| `no_contact_suppressed` | No contact — temporarily suppressed |
| `no_contact_capacity` | No contact — capacity limit |

All six outcomes must remain distinct.

## Activation reason codes

Approved final reason-code dimensions include:

- `superseded_by_latest_prediction`
- `below_frozen_threshold`
- `prediction_too_old`
- `missing_activation_context`
- `contact_not_permitted`
- `member_opted_out`
- `active_case_open`
- `contact_cooldown_active`
- `prior_intervention_limit_reached`
- `capacity_limit_reached`
- `selected_for_human_review`

Reason-code charts must use safe descriptive labels and aggregate counts only.

## Human-review summary

The dashboard may show aggregate summaries derived only from `selected_for_review` decisions.

Approved intervention categories:

- `supportive_check_in`
- `goal_planning`
- `activity_reminder`
- `rewards_education`

Approved metric:

- `pending_human_review_count`

Required label:

- Pending authorised human review

The dashboard must not expose member identifiers, exact probabilities, priority ranks, message templates, or a row-level review queue.

## Lineage fields

Approved lineage fields include:

- Run ID
- Policy version
- Policy fingerprint
- Model name
- Frozen threshold
- Decision timestamp
- Contact-context snapshot timestamp
- Warehouse ingestion timestamp
- Source as-of timestamp
- View refresh timestamp

Artifact paths, snapshot references, query digests, and SHA-256 values may appear only on the data-quality and lineage page. They must not become clickable operational links.

## Freshness status

Approved values:

| Status | Meaning |
| --- | --- |
| `current` | Source is within its expected freshness window |
| `stale` | Source is older than expected |
| `missing` | Required timestamp is unavailable |
| `empty` | Governed source contains no rows |
| `invalid` | Source fails quality or reconciliation checks |

Source-specific freshness windows will be defined with the Stage 6.2 view contracts.

## Data-quality checks

Approved checks include:

- Expected columns
- Required non-null fields
- Unique governed grain
- Probability bounds
- Model and threshold consistency
- Null outcome handling
- Activation decision reconciliation
- Eligible-count reconciliation
- Member-count reconciliation
- Capacity reconciliation
- Synthetic-data marker
- Minimum-cell suppression
- Source freshness

Every check must expose:

- Check name
- Pass or fail status
- Safe aggregate observed value
- Safe aggregate expected value
- Validation timestamp
- Source name

Failed checks must not expose member-level examples.

## Approved dimensions

Approved dimensions include:

- Prediction date
- Outcome observation date
- Model name
- Frozen threshold
- Governed risk band
- Activation decision date
- Activation outcome
- Activation reason code
- Intervention category
- Policy version
- Freshness status
- Validation check name
- Synthetic age band
- Synthetic activity level
- Synthetic reward profile

Subgroup dimensions require minimum-cell suppression.

Prohibited dimensions include:

- Member ID
- Exact member-level risk probability
- Priority rank
- Contact permission
- Opt-out status
- Active-case status
- Last-contact timestamp
- Individual intervention count

## Minimum-cell suppression

For subgroup views, a contributing count below `10` must produce:

- `is_suppressed = TRUE`
- Null metric values
- Label: `Suppressed — minimum cell count not met`

Suppressed values must not appear as zero, remain recoverable through filters, or appear in downloadable data.

Run-level governance totals are not subgroup cells and are not subject to this rule.

## Empty activation state

When no governed activation runs exist, the dashboard must display:

No governed activation runs are available.

No activation run, contact-context artifact, or review record may be fabricated for demonstration.

## Looker Studio calculated fields

Looker Studio calculated fields may be used only for:

- Display formatting
- Approved labels
- Approved percentages using numerator and denominator from the same governed view
- Safe date grouping

Thresholds, suppression, model selection, outcome classification, reconciliation, and business logic must be implemented in governed SQL views.

## Change control

Adding or changing a metric requires:

1. Updating this inventory
2. Updating the code contract where applicable
3. Updating governed SQL views
4. Updating validation tests
5. Reviewing terminology and disclaimers
6. Running the full repository quality gate
7. Recording the change in Stage 6 documentation
