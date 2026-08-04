# Stage 6 Looker Studio Field Mapping

## Status

This document maps the governed Stage 6 BigQuery fields to their approved Looker Studio roles, aggregations, labels, and restrictions.

Use it together with:

- `docs/dashboard_requirements.md`
- `docs/dashboard_metric_inventory.md`
- `dashboards/looker_studio_build_spec.md`

The dashboard remains read-only, aggregate-only, fully synthetic, descriptive, and non-operational.

## Connection boundary

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

Direct access to raw, staging, feature, scoring, activation-decision, local artifact, or review-queue sources is prohibited.

## Global aggregation rules

- Do not sum rates.
- Do not sum daily distinct-member counts across dates.
- Recalculate selected-range rates from governed numerators and denominators.
- Keep null rates unavailable; do not convert them to zero.
- Use display-order fields only for sorting.
- Do not recreate thresholds, classifications, reconciliation logic, suppression, or activation policy in Looker Studio.
- Do not expose member identifiers, member-level probabilities, priority ranks, contact context, or row-level review records.

## Formatting

| Field type | Format |
| --- | --- |
| Date | `YYYY-MM-DD` |
| Timestamp | `YYYY-MM-DD HH:MM:SS`, with timezone documented |
| Rate or probability | Percentage with one or two decimal places |
| Threshold | Decimal with three places |
| Count | Whole number with thousands separator |
| Null rate | `Unavailable` |

## 1. Daily scoring summary

Source:

`dashboard_scoring_daily_summary`

Grain:

One row per `prediction_date`.

Model contract:

- Model: `bigquery_logistic_baseline`
- Display label: BigQuery comparison baseline
- Threshold: `0.467`
- Forecasts are not confirmed outcomes.

| Field | Role | Aggregation | Display label | Restriction |
| --- | --- | --- | --- | --- |
| `prediction_date` | Dimension | None | Prediction date | Approved date control |
| `model_name` | Dimension | None | Model | Label as BigQuery comparison baseline |
| `threshold` | Governance | None | Frozen threshold | Must remain `0.467` |
| `forecast_row_count` | Metric | SUM | Forecast rows | May be summed across dates |
| `forecast_member_count` | Metric | None | Daily forecast members | Require one selected date; never sum across dates |
| `mean_forecast_risk` | Metric | None | Mean forecast risk | Do not sum or use an unweighted multi-date average |
| `high_risk_forecast_count` | Metric | SUM | High-risk forecasts | Never label as confirmed missed goals |
| `high_risk_forecast_rate` | Metric | None | High-risk forecast rate | Do not sum |
| `source_as_of` | Governance | MAX | Source as of | Historical business date |
| `view_refreshed_at` | Governance | MAX | View refreshed at | Refresh does not trigger scoring |
| `is_valid` | Governance | None | Valid | Invalid data must be visibly blocked |
| `invalid_reason` | Validation | None | Invalid reason | Display only when non-null |

Approved selected-range mean forecast risk:

`SUM(mean_forecast_risk * forecast_row_count) / SUM(forecast_row_count)`

Approved selected-range high-risk forecast rate:

`SUM(high_risk_forecast_count) / SUM(forecast_row_count)`

## 2. Risk distribution

Source:

`dashboard_risk_distribution`

Grain:

One row per `prediction_date` and `risk_band`.

| Field | Role | Aggregation | Display label | Restriction |
| --- | --- | --- | --- | --- |
| `prediction_date` | Dimension | None | Prediction date | Approved date control |
| `model_name` | Dimension | None | Model | BigQuery comparison baseline |
| `threshold` | Governance | None | Frozen threshold | Must remain `0.467` |
| `risk_band_order` | Sort | None | Risk-band order | Hide from normal viewers |
| `risk_band` | Dimension | None | Forecast risk band | Do not reinterpret as severity |
| `forecast_row_count` | Metric | SUM | Forecast rows | May be summed across dates and bands |
| `forecast_member_count` | Metric | SUM within one date | Forecast members in band | Do not claim multi-date unique members |
| `risk_band_forecast_rate` | Metric | None | Forecast share | Do not sum |
| `is_valid` | Governance | None | Valid | Invalid data must not be silently charted |
| `invalid_reason` | Validation | None | Invalid reason | Safe aggregate message only |

Governed sort order:

1. `0.00_to_0.20`
2. `0.20_to_0.40`
3. `0.40_to_0.60`
4. `0.60_to_0.80`
5. `0.80_to_1.00`

## 3. Observed outcome summary

Source:

`dashboard_observed_outcome_summary`

Grain:

One row per completed `prediction_date` outcome window.

| Field | Role | Aggregation | Display label | Restriction |
| --- | --- | --- | --- | --- |
| `prediction_date` | Dimension | None | Prediction date | Historical outcome cohort |
| `outcome_window_end` | Dimension | None | Outcome window end | Completed seven-day window |
| `observed_labelled_row_count` | Metric | SUM | Completed outcome windows | May be summed across dates |
| `observed_missed_goal_count` | Metric | SUM | Observed missed goals | Not a forecast |
| `observed_goal_met_count` | Metric | SUM | Observed goals met | Descriptive only |
| `observed_missed_goal_rate` | Metric | None | Synthetic observed missed-goal rate | Do not sum |
| `source_as_of` | Governance | MAX | Source as of | Latest completed labelled date |
| `is_valid` | Governance | None | Valid | Invalid data must be visibly blocked |
| `invalid_reason` | Validation | None | Invalid reason | Safe aggregate message only |

Approved selected-range observed missed-goal rate:

`SUM(observed_missed_goal_count) / SUM(observed_labelled_row_count)`

Observed outcomes are descriptive and do not establish intervention effects or causality.

## 4. Activation run summary

Source:

`dashboard_activation_run_summary`

Grain:

One row per governed activation run, or one explicit empty-state row.

| Field | Role | Aggregation | Display label | Restriction |
| --- | --- | --- | --- | --- |
| `run_id` | Dimension | None | Run ID | Technical audit context only |
| `policy_version` | Dimension | None | Policy version | Approved filter |
| `model_name` | Dimension | None | Model | Audit context |
| `threshold` | Governance | None | Frozen threshold | Do not recalculate |
| `decision_timestamp` | Dimension | None | Decision timestamp | Latest-run sorting |
| `capacity_limit` | Metric | None | Capacity limit | Selected run only |
| `source_row_count` | Metric | None | Source rows | Selected run only |
| `source_member_count` | Metric | None | Source members | Selected run only |
| `superseded_count` | Metric | None | Superseded | Selected run only |
| `below_threshold_count` | Metric | None | Below threshold | Selected run only |
| `excluded_count` | Metric | None | Excluded | Selected run only |
| `suppressed_count` | Metric | None | Suppressed | Selected run only |
| `eligible_count` | Metric | None | Eligible before capacity | Does not authorise outreach |
| `capacity_not_selected_count` | Metric | None | Not selected due to capacity | Selected run only |
| `selected_count` | Metric | None | Pending authorised human review | Never label as approved outreach |
| `capacity_utilisation_rate` | Metric | None | Capacity utilisation | Use governed SQL value |
| `reconciled_decision_count` | Validation | None | Reconciled decisions | Technical evidence only |
| `freshness_status` | Dimension | None | Activation state | Values: `current`, `empty` |
| `is_valid` | Governance | None | Valid | Empty state may be valid |
| `invalid_reason` | Validation | None | Invalid reason | Display only when non-null |

Approved run count:

`COUNT(run_id)`

The empty-state row has `run_id = NULL`, so it produces zero governed runs.

## 5. Activation outcome summary

Source:

`dashboard_activation_outcome_summary`

Grain:

One row per run and authoritative outcome. Six rows remain present in the empty state.

| Field | Role | Aggregation | Display label | Restriction |
| --- | --- | --- | --- | --- |
| `display_order` | Sort | None | Display order | Hide from normal viewers |
| `outcome` | Dimension | None | Outcome code | Technical context |
| `outcome_label` | Dimension | None | Activation outcome | Primary chart label |
| `is_selected_for_review` | Governance | None | Selected for review | Never use as an approval control |
| `outcome_semantics` | Governance | None | Outcome semantics | Preserve no-contact and pending-review meaning |
| `decision_count` | Metric | SUM within one run | Decisions | Primary chart metric |
| `expected_decision_count` | Validation | None | Expected decisions | Reconciliation only |
| `total_decision_count` | Validation | None | Total decisions | Repeated value; do not sum |
| `decision_rate` | Metric | None | Decision share | Null remains unavailable |
| `unexpected_decision_count` | Validation | None | Unexpected decisions | Must remain zero |
| `orphan_decision_count` | Validation | None | Orphan decisions | Must remain zero |
| `freshness_status` | Dimension | None | Freshness status | Values: `current`, `empty` |
| `is_valid` | Governance | None | Valid | Empty rows may be valid |
| `invalid_reason` | Validation | None | Invalid reason | Safe aggregate message only |

Required order:

1. Selected for review
2. No contact - superseded
3. No contact - below threshold
4. No contact - excluded
5. No contact - suppressed
6. No contact - capacity

## 6. Activation reason summary

Source:

`dashboard_activation_reason_summary`

Grain:

One row per run and authoritative final decision reason. Eleven rows remain in the empty state.

| Field | Role | Aggregation | Display label | Restriction |
| --- | --- | --- | --- | --- |
| `display_order` | Sort | None | Display order | Hide from normal viewers |
| `reason_code` | Dimension | None | Reason code | Technical table field |
| `reason_label` | Dimension | None | Decision reason | Primary chart label |
| `outcome_label` | Dimension | None | Outcome | Optional chart grouping |
| `reason_group` | Dimension | None | Reason group | Approved aggregate filter |
| `reason_semantics` | Governance | None | Reason semantics | Preserve explicit no-contact meaning |
| `reason_count` | Metric | SUM within one run | Decisions | Primary chart metric |
| `reason_rate` | Metric | None | Share of all decisions | Null remains unavailable |
| `within_outcome_rate` | Metric | None | Share within outcome | Null remains unavailable |
| `unexpected_reason_count` | Validation | None | Unexpected reasons | Must remain zero |
| `invalid_outcome_reason_count` | Validation | None | Invalid mappings | Must remain zero |
| `orphan_decision_count` | Validation | None | Orphan decisions | Must remain zero |
| `freshness_status` | Dimension | None | Freshness status | Values: `current`, `empty` |
| `is_valid` | Governance | None | Valid | Empty rows may be valid |
| `invalid_reason` | Validation | None | Invalid reason | Safe aggregate message only |

Intermediate values such as `eligible_high_risk` and `default_supportive_intervention` are prohibited.

## 7. Review selection summary

Source:

`dashboard_review_selection_summary`

Grain:

One row per run and governed supportive intervention category. Four rows remain in the empty state.

| Field | Role | Aggregation | Display label | Restriction |
| --- | --- | --- | --- | --- |
| `display_order` | Sort | None | Display order | Hide from normal viewers |
| `intervention_category` | Dimension | None | Category code | Technical table field |
| `intervention_label` | Dimension | None | Supportive intervention category | Primary chart label |
| `selection_count` | Metric | SUM within one run | Pending authorised human review | Never label as approved outreach |
| `selection_share` | Metric | None | Selection share | Null remains unavailable |
| `review_state` | Governance | None | Review state | Must remain `pending_human_review` |
| `outreach_approval_state` | Governance | None | Outreach approval state | Must remain `not_approved_outreach` |
| `operational_action_authorised` | Governance | None | Operational action authorised | Must remain `FALSE` |
| `freshness_status` | Dimension | None | Freshness status | Values: `current`, `empty` |
| `is_valid` | Governance | None | Valid | Empty rows may be valid |
| `invalid_reason` | Validation | None | Invalid reason | Safe aggregate message only |

Approved category order:

1. Supportive check-in
2. Goal planning
3. Activity reminder
4. Rewards education

## 8. Lineage and freshness summary

Source:

`dashboard_lineage_freshness_summary`

Grain:

One row per governed analytical dashboard view.

| Field | Role | Aggregation | Display label | Restriction |
| --- | --- | --- | --- | --- |
| `display_order` | Sort | None | Display order | Hide from normal viewers |
| `dashboard_view_name` | Dimension | None | Governed view | Primary table dimension |
| `metric_class` | Dimension | None | Metric class | Governed semantic class |
| `source_table_names` | Governance | None | Source tables | May contain multiple source names |
| `source_table_count` | Validation | None | Source table count | Do not sum |
| `source_row_count` | Metric | None | Source rows | Do not sum across views sharing a source |
| `storage_row_count` | Validation | None | Storage rows | Technical metadata |
| `latest_business_date` | Governance | None | Latest business date | Null is valid for empty activation sources |
| `latest_source_timestamp` | Governance | None | Latest source timestamp | Technical metadata |
| `latest_ingested_at` | Governance | None | Latest ingested at | May be null |
| `lineage_type` | Dimension | None | Lineage type | Technical classification |
| `lineage_status` | Dimension | None | Lineage status | Expected valid value: `complete` |
| `freshness_status` | Dimension | None | Freshness status | Preserve exactly |
| `freshness_interpretation` | Governance | None | Freshness interpretation | Display with status |
| `metadata_source` | Governance | None | Metadata source | Technical lineage context |
| `is_valid` | Governance | None | Valid | Invalid lineage must remain visible |
| `invalid_reason` | Validation | None | Invalid reason | Safe aggregate message only |

Possible freshness values:

- `historical_snapshot`
- `available`
- `empty`
- `missing`
- `missing_data`

Historical snapshots must not be presented as current production feeds.

## 9. Dashboard quality status

Source:

`dashboard_quality_status`

Grain:

One row per governed dashboard asset.

| Field | Role | Aggregation | Display label | Restriction |
| --- | --- | --- | --- | --- |
| `display_order` | Sort | None | Display order | Hide from normal viewers |
| `dashboard_view_name` | Dimension | None | Governed view | Technical identifier |
| `dashboard_label` | Dimension | None | Governed asset | Primary viewer-facing label |
| `metric_class` | Dimension | None | Metric class | Governed semantic class |
| `view_row_count` | Metric | None | View rows | Per-asset value |
| `invalid_row_count` | Validation | None | Invalid rows | Must be zero for pass |
| `invalid_reason_count` | Validation | None | Invalid reasons | Must be zero for pass |
| `invalid_governance_metadata_count` | Validation | None | Invalid governance metadata | Must be zero for pass |
| `lineage_status` | Dimension | None | Lineage status | Expected `complete` |
| `freshness_status` | Dimension | None | Freshness status | Preserve exactly |
| `availability_status` | Dimension | None | Availability | Values: `available`, `empty`, `unavailable` |
| `latest_business_date` | Governance | None | Latest business date | Null may be valid |
| `freshness_interpretation` | Governance | None | Freshness interpretation | Display with status |
| `quality_status` | Dimension | None | Quality status | Values: `pass`, `fail` |
| `quality_failure_reason` | Validation | None | Quality failure reason | Null for pass |
| `quality_summary` | Governance | None | Quality summary | Preserve valid-empty-state wording |
| `operational_action_authorised` | Governance | None | Operational action authorised | Must remain `FALSE` |
| `is_valid` | Governance | None | Valid | Equivalent to quality pass |
| `invalid_reason` | Validation | None | Invalid reason | Null for pass |

Approved quality-pass scorecard:

`COUNT_DISTINCT(dashboard_view_name)`

Chart filter:

`quality_status = pass`

Approved availability distribution:

- Dimension: `availability_status`
- Metric: `COUNT_DISTINCT(dashboard_view_name)`
- Keep `available`, `empty`, and `unavailable` distinct.

## Data-source validation checklist

For every Looker Studio data source:

- Confirm project `vitality-engagement-43999`.
- Confirm dataset `vitality_engagement_dev`.
- Confirm location `asia-southeast1`.
- Confirm the source name begins with `dashboard_`.
- Confirm no custom SQL bypasses the governed view.
- Confirm no member identifier is present.
- Confirm no member-level probability is present.
- Confirm no exact priority rank is present.
- Confirm no row-level activation or review record is present.
- Set identifiers, labels, statuses, and codes as dimensions.
- Set rates to no default summation.
- Set display-order fields to no aggregation.
- Set thresholds to three decimal places.
- Document the timestamp timezone.
- Hide validation-only fields from normal pages where practical.
- Do not create controls from governance booleans.
- Do not enable write-back, operational actions, member drill-through, or row-level export.
- Preserve null rates as unavailable.
- Preserve governed zero-count empty-state rows.
- Display all required synthetic, forecast, review, non-causal, and non-authorisation warnings.

## Validation evidence

For each source, record:

- Looker Studio data-source name
- Governed BigQuery view
- Credential mode
- Schema verification
- Field-type verification
- Default-aggregation verification
- Hidden-field verification
- Calculated-field verification
- Filter-control verification
- Export restriction verification
- Reviewer result
- Screenshot filename

No field mapping is complete until the connected Looker Studio source has been checked against this repository contract.
