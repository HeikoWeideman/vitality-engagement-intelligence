 Vitality Engagement Intelligence Engine Evidence Index

## Purpose

This index maps each project stage to the tracked documentation, configuration, retained evidence, and governed review artifacts that support it.

It does not treat source code, configuration, or narrative documentation as experimental evidence unless the repository retains a specific evidence record for that stage.

All project data is synthetic. Forecasts are not confirmed outcomes. Observed outcomes are descriptive, not causal. No listed artifact authorises operational action.

## Evidence classification

| Classification | Meaning |
| --- | --- |
| Foundation | Repository, packaging, quality, or governance material that defines how the project is structured |
| Technical documentation | Architecture, policy, runbook, metric definition, or model documentation |
| Retained evidence | A tracked record of validated results, screenshots, checks, findings, or reviewer sign-off |
| Runtime artifact | Generated data, model, prediction, activation, or monitoring output that is normally excluded from Git |

Generated runtime artifacts are described for lineage but are not presented as tracked evidence unless a retained evidence document explicitly records their validated results.

## Stage-by-stage index

### Stage 1 — Repository foundation and engineering controls

**Classification:** Foundation, not experimental evidence.

- [Repository README](../README.md)
- [Project configuration](../pyproject.toml)
- [Pre-commit configuration](../.pre-commit-config.yaml)

These files establish scope, package metadata, development dependencies, quality controls, and repository-level governance. They do not by themselves prove model performance, dashboard validity, or monitoring success.

### Stage 2 — Synthetic data generation and review

**Classification:** Technical documentation and retained review evidence.

- [Synthetic dataset card](data_card.md)
- [Dataset distribution review](data_distribution_review.md)

These documents record the synthetic-data design, dimensions, distributions, leakage controls, limitations, and review findings.

### Stage 3 — BigQuery feature pipeline and comparison baseline

**Classification:** Technical documentation and retained model evidence.

- [BigQuery and SQL architecture](bigquery_architecture.md)
- [BigQuery ML baseline results](bigquery_baseline_results.md)

The retained Stage 3 model is `bigquery_logistic_baseline` with threshold `0.467`. It is the BigQuery comparison baseline, not the selected Stage 4 activation-driving model.

### Stage 4 — Selected Python model and verified scoring

**Classification:** Technical documentation and retained model evidence.

- [Python logistic baseline results](python_logistic_baseline_results.md)
- [Model card](model_card.md)

The selected model is `python_logistic_baseline` with threshold `0.431`.

Generated local runtime artifacts include:

- `data/modeling/engagement_modeling_split.parquet`;
- the persisted selected Python model and metadata;
- `artifacts/scoring/python_logistic_scoring_predictions.parquet`;
- `artifacts/scoring/python_logistic_scoring_predictions.metadata.json`.

These generated files are normally excluded from Git. Their model identity, threshold, schema, row counts, and SHA-256 lineage are described in the retained Stage 4 documentation.

### Stage 5 — Governed activation and mandatory human review

**Classification:** Technical policy and runbook documentation.

- [Activation policy](activation_policy.md)
- [Activation runbook](activation_runbook.md)

Activation requires legitimate approved contact context and a timezone-aware decision timestamp.

The repository intentionally permits a valid governed empty state when approved contact context is unavailable. Selected for review does not mean approved outreach.

Generated activation decisions and review-queue artifacts are runtime outputs and are normally excluded from Git.

### Stage 6 — Aggregate dashboard and reporting evidence

**Classification:** Technical documentation and retained dashboard evidence.

- [Dashboard requirements](dashboard_requirements.md)
- [Dashboard metric inventory](dashboard_metric_inventory.md)
- [Stage 6 dashboard evidence](stage_6_dashboard_evidence.md)
- [Retained dashboard assets](../dashboards/)

The dashboard evidence records the validated five-page Looker Studio report, governed BigQuery views, screenshots, lineage, quality checks, aggregate-only design, and subgroup suppression minimum of 10.

Dashboard visibility does not grant operational authority.

### Stage 7 — Drift, data-quality, and governance monitoring

**Classification:** Technical policy, runbook documentation, and retained monitoring evidence.

- [Monitoring policy](monitoring_policy.md)
- [Monitoring runbook](monitoring_runbook.md)
- [Stage 7 monitoring evidence](stage_7_monitoring_evidence.md)

The retained local monitoring run evaluated 57 checks:

| Severity | Count |
| --- | ---: |
| Pass | 53 |
| Warning | 2 |
| Critical | 2 |

The retained critical findings are:

- `previous_goal_streak_as_of` PSI: `1.559510`;
- `previous_failed_goals_as_of` PSI: `0.290255`.

The retained warnings are:

- probability PSI: `0.155921`;
- `avg_goal_completion_percentage_28d` PSI: `0.109969`.

The critical and warning findings remain visible. Monitoring detects temporal-shift and training-support concerns; it does not resolve them.

Both BigQuery monitoring views set `operational_action_authorised` to `FALSE`.

### Stage 8 — Portfolio architecture, reproducibility, and evidence navigation

**Classification:** Final technical documentation and portfolio navigation.

- [Project architecture](project_architecture.md)
- [Reproducibility guide](reproducibility_guide.md)
- [Evidence index](evidence_index.md)
- [Repository README](../README.md)

These documents consolidate the end-to-end architecture, execution order, command safety classes, artifact lineage, model boundaries, monitoring findings, limitations, and evidence locations.

Stage 8 does not replace or reinterpret the retained evidence from Stages 2–7.

## Model identity boundary

| Model | Threshold | Evidence role |
| --- | ---: | --- |
| `python_logistic_baseline` | `0.431` | Selected Stage 4 Python model used for verified scoring |
| `bigquery_logistic_baseline` | `0.467` | Stage 3 BigQuery ML comparison baseline and BigQuery forecast-view model |

The two model names and thresholds must remain together. Neither threshold may be transferred to the other model.

## Evidence interpretation boundary

The evidence indexed here supports a synthetic technical portfolio only.

It does not establish:

- clinical validity;
- causal intervention effectiveness;
- real-world fairness;
- production privacy compliance;
- legal or regulatory compliance;
- member-contact authorisation;
- production deployment readiness;
- safe automated decision-making.

A passing technical check does not prove operational suitability. A warning or critical result does not itself authorise corrective operational action.

## Primary navigation

- [Project architecture](project_architecture.md)
- [Reproducibility guide](reproducibility_guide.md)
- [Repository README](../README.md)
