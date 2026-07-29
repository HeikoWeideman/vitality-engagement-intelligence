# Stage 6 Dashboard Requirements

## Status

This document defines the governed requirements for the Stage 6 Looker Studio dashboard.

The dashboard is a read-only technical demonstration using fully synthetic data. It is not an operational dispatch, outreach, approval, clinical, eligibility, or case-management system.

The governed metric inventory in `docs/dashboard_metric_inventory.md` must be approved before dashboard views or Looker Studio pages are built.

## Intended audience

Access is limited to:

- Technical reviewers assessing data, SQL, modelling, and dashboard implementation
- Model-governance reviewers assessing model boundaries, terminology, and limitations
- Data-governance reviewers assessing aggregation, lineage, freshness, and privacy controls
- Authorised human reviewers viewing aggregate activation-governance summaries

Dashboard access does not grant authority to contact members, approve outreach, change cases, or take any operational action.

## Approved decisions

The dashboard may support only descriptive and governance-oriented decisions, including:

- Assess whether synthetic scoring volumes and risk distributions are internally consistent
- Review trends in synthetic forecast outputs
- Compare clearly labelled model-development results
- Assess whether activation decision counts reconcile to governed run metadata
- Review capacity utilisation and no-contact outcome distributions
- Confirm source freshness, ingestion timestamps, model name, threshold, policy version, and lineage availability
- Identify missing, stale, empty, or inconsistent dashboard source data
- Review methodology, assumptions, and known limitations

The dashboard must not recommend or authorise outreach to an individual.

## Prohibited uses

The dashboard must not be used to:

- Send or trigger email, SMS, notifications, or any other outreach
- Approve a member for contact
- Open, close, assign, or change a case
- Change benefits, eligibility, access, or programme status
- Apply penalties or punitive treatment
- Assign experimental, behavioural, or clinical treatment
- Make medical, psychological, diagnostic, or clinical conclusions
- Claim that an intervention caused an observed result
- Infer real-world wellness behaviour from synthetic results
- Export or expose member-level dashboard data
- Treat `selected_for_review` as approved outreach
- Treat forecasts as confirmed missed-goal outcomes

No dashboard button, link, community visual, embedded application, or external action may initiate an operational workflow.

## Approved source boundary

Looker Studio may connect only to explicit governed BigQuery views created for Stage 6.

It must not connect directly to:

- Raw or staging tables
- `engagement_features_28d`
- `engagement_modeling_split`
- Member-level scoring tables
- `activation_decisions`
- Local Parquet artifacts
- Local human-review queue artifacts
- Broad dataset-level wildcard sources

Potential governed upstream sources are:

- `engagement_features_28d`
- `engagement_logistic_scoring_predictions`
- `activation_runs`
- `activation_decisions`

These are upstream inputs only. Stage 6 views must aggregate, rename, constrain, and validate fields before Looker Studio access is allowed.

The local human-review queue is not a warehouse table. Stage 6 must not fabricate, upload, or reconstruct unauthorised review data merely to populate a dashboard.

## Model boundaries

The selected Stage 4 operational model is:

- Model: Python logistic baseline
- Frozen threshold: `0.431`

Its predictions are forecasts, not confirmed outcomes.

The Stage 3 BigQuery ML baseline uses a separate threshold of `0.467`. Any dashboard comparison must label the two models explicitly. The BigQuery baseline must not be presented as the selected activation model.

The threshold `0.431` was selected using validation positive-class F1. It was not selected using capacity, financial cost, clinical value, or intervention effectiveness.

## Metric semantic boundaries

Every dashboard metric must belong to one governed class:

- Synthetic descriptive
- Forecast
- Observed outcome
- Activation audit
- Lineage
- Data quality

Forecasts and observed outcomes must never be combined under one label or denominator.

Observed outcome metrics must:

- Use only rows with a complete future outcome window
- Exclude null future labels
- State the observation period
- Avoid causal or intervention-effect language

Activation metrics must:

- Use `selected_for_review`, never `approved`, `contacted`, or `activated`
- Keep exclusions, suppressions, below-threshold records, superseded records, and capacity non-selections distinct
- Reconcile all decision outcomes to the source row count
- Reconcile eligible rows to selected plus capacity-not-selected rows
- Confirm selected count does not exceed capacity

## Aggregation and privacy

The Stage 6 dashboard is aggregate-only.

Member identifiers, member-level probabilities, exact priority ranks, contact permissions, opt-out status, active-case status, contact timestamps, and individual intervention histories must not be exposed to Looker Studio.

Subgroup metrics must be suppressed when the contributing row or member count is below `10`.

The minimum cell count of `10` is a conservative engineering default for this synthetic portfolio project. It is not represented as a legal, regulatory, clinical, or production privacy standard.

Suppressed cells must be shown as suppressed or unavailable. They must not be converted to zero.

## Synthetic-data labelling

Every dashboard page must visibly state:

> All dashboard data is fully synthetic and is shown for technical demonstration only.

The dashboard must not imply that it contains real member, clinical, wearable-device, disability, socioeconomic, geographic, or personally identifiable information.

Synthetic subgroup differences must not be presented as evidence of real demographic or behavioural differences.

## Required disclaimers

Every dashboard page must display or link prominently to all of the following:

- All dashboard data is fully synthetic and is shown for technical demonstration only.
- Predictions are forecasts, not confirmed missed-goal outcomes.
- Selected for review means pending authorised human review, not approved outreach.
- Dashboard content is descriptive and does not establish causal intervention effects.
- Dashboard visibility does not authorise contact, messaging, case changes, eligibility changes, penalties, treatment, or clinical conclusions.

## Read-only interaction boundary

Allowed interactions are limited to:

- Date filters
- Governed model labels
- Governed policy-version filters
- Aggregate outcome filters
- Aggregate intervention-category filters
- Approved synthetic subgroup filters that preserve suppression rules
- Navigation between dashboard pages
- Informational links to repository documentation

Prohibited interactions include:

- Member search
- Member drill-through
- Row-level downloads
- Write-back
- Approval controls
- Status changes
- Messaging controls
- Case controls
- Webhooks
- Embedded operational applications
- Links that contain member identifiers or pre-filled outreach actions

## Freshness and empty states

Every governed view must expose a source freshness or ingestion timestamp appropriate to its grain.

The dashboard must display an explicit empty state when:

- No governed activation runs exist
- A source view contains no rows
- A source is stale
- A source fails reconciliation
- A synthetic-data marker is missing

Empty warehouse activation tables are valid. Stage 6 must not fabricate governed runs or contact context to make charts non-empty.

## Data-quality requirements

Governed dashboard sources must validate:

- Expected columns
- Expected data types
- Required non-null fields
- Unique view keys
- Date ranges
- Probability bounds
- Threshold consistency
- Model-name consistency
- Synthetic-data markers
- Metric denominators
- Null outcome handling
- Activation outcome reconciliation
- Capacity reconciliation
- Source freshness
- Minimum-cell suppression

A validation failure must block or clearly invalidate the affected dashboard view.

## Dashboard page requirements

The planned dashboard pages are:

1. Executive overview
2. Model scoring overview
3. Activation governance
4. Human-review summary
5. Data quality and lineage
6. Methodology and limitations

The human-review page is aggregate-only. It must not reproduce the member-level local review queue.

## Refresh behaviour

Refresh behaviour must be documented for every governed view and Looker Studio data source.

Refresh must remain read-only. Refreshing the dashboard must not trigger scoring, activation, upload, review, approval, outreach, or any downstream operation.

## Evidence and review

Stage 6 completion evidence must include:

- Governed view definitions
- Metric formulas
- Validation results
- Dashboard page screenshots
- Filter behaviour
- Refresh behaviour
- Empty-state evidence
- Synthetic-data warning evidence
- Confirmation that no operational action controls exist
- Metric reconciliation evidence
- Reviewer instructions
- Known limitations

## Change control

Changes to dashboard audiences, sources, metrics, suppression rules, disclaimers, action boundaries, or model labels require code review, updated tests, and documentation review.

The default code contract is defined in:

- `src/vitality_engagement/dashboard/governance.py`
- `tests/unit/test_dashboard_governance.py`
