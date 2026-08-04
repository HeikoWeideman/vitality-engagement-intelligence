# Stage 6 Looker Studio Validation Checklist

## Status

Use this checklist while constructing and reviewing the Stage 6 governed Looker Studio dashboard.

Do not mark an item complete without direct Looker Studio evidence. Do not invent screenshots, data-source settings, access controls, reviewer approvals, or activation records.

## Evidence notation

For each completed item, record:

- Result: Pass, Fail, Not applicable, or Blocked
- Evidence: Screenshot filename, report page, configuration panel, or repository reference
- Reviewer: Name or role of the person who performed the check
- Date: Review date
- Notes: Any limitation, defect, or follow-up action

## 1. Report identity and access

- [ ] Report title is `Vitality Engagement Intelligence - Governed Dashboard`.
- [ ] Report is located in the approved Looker Studio workspace.
- [ ] Report access is read-only for dashboard viewers.
- [ ] Edit access is limited to authorised builders or reviewers.
- [ ] Viewer credentials do not provide broader BigQuery access than required.
- [ ] No public-link sharing is enabled.
- [ ] No anonymous access is enabled.
- [ ] No embedded operational application is present.
- [ ] No viewer can trigger scoring, activation, review, approval, messaging, or case activity.
- [ ] The report contains no member search.
- [ ] The report contains no member drill-through.
- [ ] The report contains no row-level export.
- [ ] The report contains no write-back control.
- [ ] The report contains no webhook or external action control.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 2. Global governance language

Confirm every report page visibly displays the required synthetic-data banner.

- [ ] Every page states that all dashboard data is fully synthetic.
- [ ] Every page states that the dashboard is for technical demonstration only.
- [ ] Forecast pages state that predictions are forecasts, not confirmed outcomes.
- [ ] Activation and review pages state that selected for review is pending human review.
- [ ] Activation and review pages state that selected for review is not approved outreach.
- [ ] Every page states or links prominently to the descriptive, non-causal limitation.
- [ ] Every page states or links prominently to the non-authorisation limitation.
- [ ] Governance text is readable without opening edit mode.
- [ ] Governance text is not hidden behind a chart interaction.
- [ ] Governance text remains visible when filters are applied.

Required statements:

```text
All dashboard data is fully synthetic and is shown for technical demonstration only.

Predictions are forecasts, not confirmed missed-goal outcomes.

Selected for review means pending authorised human review, not approved outreach.

Dashboard content is descriptive and does not establish causal intervention effects.

Dashboard visibility does not authorise contact, messaging, case changes, eligibility changes, penalties, treatment, or clinical conclusions.
```

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 3. Governed data-source boundary

Confirm that Looker Studio connects only to the approved governed views.

Approved views:

- [ ] `dashboard_scoring_daily_summary`
- [ ] `dashboard_risk_distribution`
- [ ] `dashboard_observed_outcome_summary`
- [ ] `dashboard_activation_run_summary`
- [ ] `dashboard_activation_outcome_summary`
- [ ] `dashboard_activation_reason_summary`
- [ ] `dashboard_review_selection_summary`
- [ ] `dashboard_lineage_freshness_summary`
- [ ] `dashboard_quality_status`

For every connected source:

- [ ] Project is `vitality-engagement-43999`.
- [ ] Dataset is `vitality_engagement_dev`.
- [ ] BigQuery location is `asia-southeast1`.
- [ ] Source name begins with `dashboard_`.
- [ ] No custom query bypasses the governed view.
- [ ] No wildcard dataset source is connected.
- [ ] No extracted data source contains prohibited row-level fields.
- [ ] Schema refresh preserves the governed field contract.
- [ ] Data-source owner is documented.
- [ ] Credential mode is documented.
- [ ] Data-source refresh behaviour is documented.

Prohibited direct sources:

- [ ] `engagement_raw` is not connected.
- [ ] `engagement_staging` is not connected.
- [ ] `engagement_features_28d` is not connected.
- [ ] `engagement_logistic_scoring_predictions` is not connected.
- [ ] `activation_runs` is not connected.
- [ ] `activation_decisions` is not connected.
- [ ] No local Parquet artifact is uploaded.
- [ ] No local human-review queue is uploaded.
- [ ] No member-level custom source is connected.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 4. Field configuration

Use `dashboards/looker_studio_field_mapping.md` as the authoritative field contract.

For every data source:

- [ ] Date fields use the correct date type.
- [ ] Timestamp fields use the correct timestamp type.
- [ ] Timestamp timezone is documented.
- [ ] Count fields use the approved aggregation.
- [ ] Rate fields do not use `SUM`.
- [ ] Daily distinct-member counts are not summed across dates.
- [ ] Display-order fields use no aggregation.
- [ ] Threshold fields display three decimal places.
- [ ] Probability and rate fields display as percentages.
- [ ] Null governed rates display as unavailable.
- [ ] Validation-only fields are hidden from normal report pages where practical.
- [ ] Governance Boolean fields are not exposed as action controls.
- [ ] Invalid reasons remain available for quality review.
- [ ] No threshold logic is recreated in Looker Studio.
- [ ] No outcome classification is recreated in Looker Studio.
- [ ] No activation reason mapping is recreated in Looker Studio.
- [ ] No suppression logic is recreated in Looker Studio.
- [ ] No reconciliation logic is recreated in Looker Studio.
- [ ] No model-selection logic is recreated in Looker Studio.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 5. Prohibited fields and privacy

Confirm that none of the following fields or equivalents are exposed:

- [ ] No `member_id`.
- [ ] No member-level risk probability.
- [ ] No member-level predicted class.
- [ ] No exact priority rank.
- [ ] No contact permission.
- [ ] No opt-out status.
- [ ] No active-case status.
- [ ] No last-contact timestamp.
- [ ] No individual intervention history.
- [ ] No message template.
- [ ] No contact-context record.
- [ ] No row-level activation decision.
- [ ] No row-level review record.
- [ ] No member-level downloadable data.
- [ ] No URL containing member identifiers.
- [ ] No chart drill-down exposes prohibited fields.

Subgroup controls:

- [ ] No subgroup field is enabled unless a governed suppressed view exists.
- [ ] Counts below the minimum cell count of 10 are not exposed.
- [ ] Suppressed values are not converted to zero.
- [ ] Suppressed values cannot be recovered through filters or downloads.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 6. Page 1 - Executive overview

Required sources:

- `dashboard_quality_status`
- `dashboard_lineage_freshness_summary`
- `dashboard_scoring_daily_summary`
- `dashboard_observed_outcome_summary`
- `dashboard_activation_run_summary`

Checks:

- [ ] Page title is present.
- [ ] Synthetic-data banner is visible.
- [ ] Governed asset health scorecard is present.
- [ ] Asset availability table is present.
- [ ] Asset table uses `dashboard_label`.
- [ ] Asset table is sorted by `display_order`.
- [ ] Availability status remains distinct from quality status.
- [ ] Valid empty activation assets are not shown as failures.
- [ ] Latest business date is present.
- [ ] Forecast volume is present.
- [ ] Observed labelled volume is present.
- [ ] Activation state is present.
- [ ] Current activation state displays no governed activation runs.
- [ ] Historical snapshots are not labelled live or current production data.
- [ ] Forecast and observed metrics are visually distinct.
- [ ] Limitations panel is visible.
- [ ] No operational control exists.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 7. Page 2 - Model scoring overview

Required sources:

- `dashboard_scoring_daily_summary`
- `dashboard_risk_distribution`

Checks:

- [ ] Page title is present.
- [ ] Synthetic-data banner is visible.
- [ ] Warning states that forecasts are not confirmed outcomes.
- [ ] Model label is `BigQuery comparison baseline`.
- [ ] Model name is `bigquery_logistic_baseline`.
- [ ] Threshold is displayed as `0.467`.
- [ ] Threshold `0.431` is not substituted into these views.
- [ ] Forecast-row scorecard uses `SUM(forecast_row_count)`.
- [ ] Daily forecast-member scorecard requires one selected prediction date.
- [ ] Daily forecast-member count is not summed across dates.
- [ ] Mean forecast-risk scorecard uses the approved weighted formula.
- [ ] High-risk count uses `SUM(high_risk_forecast_count)`.
- [ ] High-risk rate uses the approved numerator and denominator.
- [ ] Forecast count by date uses `prediction_date`.
- [ ] Mean forecast risk by date does not use a summed rate.
- [ ] Risk distribution uses `risk_band`.
- [ ] Risk distribution is sorted by `risk_band_order`.
- [ ] Risk distribution uses `forecast_row_count` or `risk_band_forecast_rate`.
- [ ] Zero-count risk bands remain visible.
- [ ] Risk bands are not labelled severity, diagnosis, or treatment categories.
- [ ] No chart is labelled confirmed missed goals.
- [ ] Date controls affect only approved aggregate charts.
- [ ] No member-level drill-through exists.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 8. Page 3 - Activation governance

Required sources:

- `dashboard_activation_run_summary`
- `dashboard_activation_outcome_summary`
- `dashboard_activation_reason_summary`

Checks:

- [ ] Page title is present.
- [ ] Synthetic-data banner is visible.
- [ ] Pending-human-review warning is visible.
- [ ] Not-approved-outreach warning is visible.
- [ ] Non-authorisation warning is visible.
- [ ] Run-count metric uses `COUNT(run_id)`.
- [ ] Current empty-state run count is zero.
- [ ] Source-row count is zero in the governed empty state.
- [ ] Source-member count is zero in the governed empty state.
- [ ] Eligible count is zero in the governed empty state.
- [ ] Selected count is zero in the governed empty state.
- [ ] Capacity utilisation remains unavailable when capacity is absent.
- [ ] Outcome chart uses `outcome_label`.
- [ ] Outcome metric is `decision_count`.
- [ ] Outcome chart is sorted by `display_order`.
- [ ] All six authoritative outcomes remain visible.
- [ ] No-contact outcomes remain distinct.
- [ ] Reason chart uses `reason_label`.
- [ ] Reason metric is `reason_count`.
- [ ] Reason chart is sorted by `display_order`.
- [ ] All 11 final decision reasons remain visible.
- [ ] Intermediate reason values are absent.
- [ ] Null decision and reason rates remain unavailable.
- [ ] Page states `No governed activation runs are available`.
- [ ] Page states `Valid governed empty state`.
- [ ] No activation data was fabricated.
- [ ] No approval or outreach control exists.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 9. Page 4 - Human-review summary

Required source:

- `dashboard_review_selection_summary`

Checks:

- [ ] Page title is present.
- [ ] Synthetic-data banner is visible.
- [ ] Page states pending authorised human review.
- [ ] Page states not approved outreach.
- [ ] Page states dashboard visibility does not authorise contact.
- [ ] Total uses `SUM(selection_count)`.
- [ ] Primary dimension is `intervention_label`.
- [ ] Category chart is sorted by `display_order`.
- [ ] All four supportive intervention categories remain visible.
- [ ] `selection_share` is unavailable when the denominator is zero.
- [ ] `review_state` displays `pending_human_review`.
- [ ] `outreach_approval_state` displays `not_approved_outreach`.
- [ ] `operational_action_authorised` remains `FALSE`.
- [ ] No message content is shown.
- [ ] No member record is shown.
- [ ] No row-level review queue is shown.
- [ ] No approval or contact control exists.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 10. Page 5 - Data quality and lineage

Required sources:

- `dashboard_lineage_freshness_summary`
- `dashboard_quality_status`

Checks:

- [ ] Page title is present.
- [ ] Synthetic-data banner is visible.
- [ ] Governed asset inventory uses `dashboard_label`.
- [ ] Asset inventory is sorted by `display_order`.
- [ ] Quality status and availability status remain distinct.
- [ ] Quality-pass count uses `COUNT_DISTINCT(dashboard_view_name)`.
- [ ] Quality-pass scorecard filters `quality_status = pass`.
- [ ] Availability chart uses `availability_status`.
- [ ] Availability chart distinguishes `available`, `empty`, and `unavailable`.
- [ ] Lineage table uses `dashboard_view_name`.
- [ ] Lineage table shows `source_table_names`.
- [ ] Lineage table shows `source_table_count`.
- [ ] Lineage table shows `lineage_status`.
- [ ] Source-row counts are not summed across views.
- [ ] Latest business dates remain unavailable for empty activation sources.
- [ ] Freshness status is shown with `freshness_interpretation`.
- [ ] `historical_snapshot` is explained as valid historical synthetic data.
- [ ] `available` is distinct from `historical_snapshot`.
- [ ] `empty` is explained as a valid governed source state.
- [ ] `missing` and `missing_data` are not hidden.
- [ ] Invalid reasons are visible when present.
- [ ] No member-level validation examples appear.
- [ ] Quality pass does not imply operational authorisation.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 11. Page 6 - Methodology and limitations

Checks:

- [ ] Page title is present.
- [ ] Dashboard purpose is documented.
- [ ] Fully synthetic data limitation is documented.
- [ ] Approved audiences are documented.
- [ ] Approved source boundary is documented.
- [ ] Metric classes are documented.
- [ ] Forecast and observed-outcome distinction is documented.
- [ ] Stage 3 and Stage 4 model distinction is documented.
- [ ] Stage 3 threshold `0.467` is documented.
- [ ] Stage 4 threshold `0.431` is documented as separate.
- [ ] Stage 4 local artifact is not represented as connected to Looker Studio.
- [ ] Selected-for-review terminology is documented.
- [ ] Not-approved-outreach terminology is documented.
- [ ] Minimum-cell count of 10 is documented as an engineering default.
- [ ] Empty activation-state policy is documented.
- [ ] Refresh behaviour is documented.
- [ ] Prohibited uses are documented.
- [ ] Known limitations are documented.
- [ ] Repository documentation references are present.
- [ ] No causal or production-evidence claim is present.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 12. Filter and interaction testing

- [ ] Date filter changes forecast charts correctly.
- [ ] Date filter changes observed-outcome charts correctly.
- [ ] Forecast and observed date controls do not create ambiguous combined metrics.
- [ ] Model filter contains only governed model values.
- [ ] Policy-version filter is absent or empty when no activation runs exist.
- [ ] Outcome filter retains all six governed outcome categories.
- [ ] Reason filter retains all 11 final reason categories.
- [ ] Intervention filter retains all four supportive categories.
- [ ] Empty-state rows remain visible after valid filters.
- [ ] No filter exposes member-level data.
- [ ] No filter bypasses suppression.
- [ ] No chart interaction exposes prohibited hidden fields.
- [ ] Page navigation works.
- [ ] Informational repository links contain no member identifiers.
- [ ] No interaction initiates an external workflow.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 13. Empty-state validation

Current governed activation source state:

```text
activation_runs: 0 rows
activation_decisions: 0 rows
```

Confirm:

- [ ] Activation-run summary returns one valid empty-state row.
- [ ] Activation-outcome summary returns six valid empty-state rows.
- [ ] Activation-reason summary returns 11 valid empty-state rows.
- [ ] Review-selection summary returns four valid empty-state rows.
- [ ] All empty-state counts remain zero.
- [ ] All empty-state rates remain null or unavailable.
- [ ] Empty states are labelled explicitly.
- [ ] Empty states are not hidden by chart settings.
- [ ] Empty states are not converted into fabricated records.
- [ ] Empty states are not presented as failures.
- [ ] Empty states do not imply that outreach occurred.
- [ ] Empty states do not imply that review was approved.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 14. Refresh testing

- [ ] Report refresh is read-only.
- [ ] Refresh reevaluates only governed BigQuery views.
- [ ] Refresh does not trigger scoring.
- [ ] Refresh does not create activation runs.
- [ ] Refresh does not upload local artifacts.
- [ ] Refresh does not create review records.
- [ ] Refresh does not approve outreach.
- [ ] Refresh does not initiate messaging.
- [ ] Refresh does not change cases or eligibility.
- [ ] Refresh timestamp is visible where required.
- [ ] Source business dates remain distinct from refresh timestamps.
- [ ] Historical snapshots remain labelled historical after refresh.
- [ ] Empty activation sources remain explicit after refresh.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 15. Export and sharing restrictions

- [ ] Download-data controls are disabled where possible.
- [ ] No row-level export is available.
- [ ] No scheduled delivery exposes prohibited data.
- [ ] No emailed report contains member-level data.
- [ ] No public embed is enabled.
- [ ] No report link grants edit access unintentionally.
- [ ] No connected source grants access to upstream tables.
- [ ] No chart exposes hidden validation fields through export.
- [ ] No repository link points to a member-level artifact.

Evidence:

```text
Result:
Evidence:
Reviewer:
Date:
Notes:
```

## 16. Screenshot evidence

Create screenshots only after the report is actually built.

Required evidence:

- [ ] Executive overview page.
- [ ] Model scoring overview page.
- [ ] Activation governance page.
- [ ] Human-review summary page.
- [ ] Data quality and lineage page.
- [ ] Methodology and limitations page.
- [ ] Global synthetic-data banner.
- [ ] Forecast-not-outcome warning.
- [ ] Pending-review-not-approved-outreach warning.
- [ ] Valid governed activation empty state.
- [ ] Six zero-count activation outcomes.
- [ ] Eleven zero-count activation reasons.
- [ ] Four zero-count review-selection categories.
- [ ] Data-source connection list.
- [ ] Field aggregation configuration.
- [ ] Filter behaviour.
- [ ] Refresh configuration.
- [ ] Sharing and access configuration.
- [ ] Absence of operational controls.

Screenshot directory:

```text
dashboards/screenshots/
```

Do not commit placeholder or fabricated screenshots.

## 17. Reviewer sign-off

### Technical review

- [ ] View connections match repository SQL.
- [ ] Chart dimensions and metrics match the build specification.
- [ ] Calculated fields match approved formulas.
- [ ] Filters and sorting work correctly.
- [ ] Screenshots match the implemented report.

```text
Result:
Reviewer:
Date:
Notes:
```

### Model-governance review

- [ ] Forecast terminology is correct.
- [ ] Model labels and thresholds are correct.
- [ ] Forecasts and observed outcomes remain distinct.
- [ ] No causal or operational claim is present.

```text
Result:
Reviewer:
Date:
Notes:
```

### Data-governance review

- [ ] Only governed aggregate views are connected.
- [ ] No member-level data is exposed.
- [ ] Empty states and invalid states are explicit.
- [ ] Sharing and export restrictions are appropriate.
- [ ] Synthetic-data classification is visible.

```text
Result:
Reviewer:
Date:
Notes:
```

### Authorised human-review review

- [ ] Pending-review terminology is understandable.
- [ ] Selected for review is not presented as outreach approval.
- [ ] No operational action is possible.
- [ ] Human-review page remains aggregate-only.

```text
Result:
Reviewer:
Date:
Notes:
```

## 18. Final Stage 6 dashboard acceptance

Do not mark Stage 6 complete until all applicable items below pass.

- [ ] All six dashboard pages exist.
- [ ] Only governed `dashboard_*` views are connected.
- [ ] Forecast and observed metrics remain distinct.
- [ ] BigQuery comparison baseline is labelled correctly.
- [ ] Threshold `0.467` is displayed correctly.
- [ ] Threshold `0.431` remains separate.
- [ ] Selected-for-review remains distinct from approved outreach.
- [ ] Empty activation state is explicit.
- [ ] No member-level data is exposed.
- [ ] No operational action exists.
- [ ] Synthetic and non-causal disclaimers are visible.
- [ ] Quality and lineage information is visible.
- [ ] Screenshots are genuine and committed.
- [ ] Reviewer guidance is complete.
- [ ] Known limitations are documented.
- [ ] README and project status are updated.
- [ ] Targeted checks pass.
- [ ] Full repository quality gate passes.
- [ ] Changes are committed and pushed.
- [ ] Local and remote hashes match.
- [ ] `git status --short` is blank.

Final result:

```text
Stage 6 dashboard status:
Reviewer:
Review date:
Open defects:
Evidence location:
Notes:
```
