# Vitality Engagement Intelligence Engine

An end-to-end machine-learning product for predicting near-term wellness-programme disengagement, selecting an appropriate behavioural intervention, and generating a safe personalised message.

## Current status

Stages 1â€“6 are complete. The latest closed milestone is **Stage 6 â€” Governed Looker Studio dashboard**, which was validated in View mode, evidenced with genuine screenshots, reviewer-approved, committed, pushed, and verified with matching local and remote hashes.

Stage 7 is complete. Local Python monitoring, verified atomic artifacts, read-only BigQuery monitoring views, governance checks, runbooks, and evidence are in place. The governed historical scoring snapshot has two warnings and two critical drift findings, which are preserved for human review rather than suppressed.

### Project delivery status

| Stage                                                | Status      |
| ---------------------------------------------------- | ----------- |
| Stage 1 â€” Repository and development foundation      | Complete    |
| Stage 2 â€” Synthetic data and BigQuery ingestion      | Complete    |
| Stage 3 â€” Governed features and BigQuery ML baseline | Complete    |
| Stage 4 â€” Python modelling and operational scoring   | Complete    |
| Stage 5 â€” Activation pipeline                        | Complete    |
| Stage 6 â€” Looker Studio dashboard                    | Complete    |
| Stage 7 â€” Monitoring and governance                  | Closure pending |
| Stage 8 â€” Final documentation and portfolio polish   | Not started |

All modelling results use synthetic data and must not be interpreted as evidence about real member behaviour, health, eligibility, or intervention effectiveness.

## Stage 7 â€” Monitoring and governance

Stage 7 adds deterministic, fail-closed monitoring for the selected Stage 4 Python model, the separate Stage 3 BigQuery comparison baseline, dashboard quality, lineage freshness, and valid activation empty states.

The local command is:

`python -m vitality_engagement.monitoring.cli --monitoring-timestamp "<timezone-aware ISO-8601 timestamp>"`

Default local outputs are:

- `artifacts/monitoring/monitoring_checks.parquet`
- `artifacts/monitoring/monitoring_checks.metadata.json`

The local workflow evaluates 57 checks covering scoring volume, model identity, threshold identity, schema identity, probability drift, all 47 model features, and unexpected categorical values. It records SHA-256 lineage for the modelling data, persisted model, model metadata, scoring predictions, and scoring metadata.

The governed Stage 7 evidence run produced:

| Result | Value |
| --- | ---: |
| Monitoring checks | 57 |
| Passing checks | 53 |
| Warning checks | 2 |
| Critical checks | 2 |
| Overall severity | Critical |
| CLI exit code | 2 |

The non-passing findings are:

| Check | Observed value | Severity |
| --- | ---: | --- |
| Probability PSI | `0.155921` | Warning |
| `previous_goal_streak_as_of` PSI | `1.559510` | Critical |
| `previous_failed_goals_as_of` PSI | `0.290255` | Critical |
| `avg_goal_completion_percentage_28d` PSI | `0.109969` | Warning |

The critical findings are retained as genuine temporal-shift and model-extrapolation concerns. Monitoring thresholds were not weakened merely to obtain a passing result.

The BigQuery monitoring layer keeps the two model identities separate:

| Model | Threshold | Role |
| --- | ---: | --- |
| `python_logistic_baseline` | `0.431` | Selected Stage 4 Python model |
| `bigquery_logistic_baseline` | `0.467` | Stage 3 comparison baseline |

Read-only BigQuery monitoring views are:

- `vitality_engagement_dev.model_monitoring_status`
- `vitality_engagement_dev.governance_monitoring_status`

The model-monitoring view has nine passing checks and two expected critical training-support findings. The governance-monitoring view has three passing checks covering valid activation empty states, all eight governed dashboard assets, and all seven dashboard lineage rows.

Monitoring is descriptive and non-operational. It does not authorise member contact, outreach, intervention delivery, case creation, eligibility changes, penalties, treatment assignment, model promotion, retraining, or threshold changes.

See:

- `docs/monitoring_policy.md`
- `docs/monitoring_runbook.md`
- `docs/stage_7_monitoring_evidence.md`
## Stage 5 â€” Governed activation workflow

Stage 5 converts verified scoring forecasts and an independently verified contact-context snapshot into deterministic, capacity-aware recommendations for mandatory human review.

The workflow audits every scoring row, applies permission and suppression rules, preserves scoring and contact-context lineage, enforces a maximum of 100 selected records per run, and writes verified local Parquet and metadata artifacts.

A legitimate approved contact-context artifact is required. The repository does not fabricate or provide one.

The local command is available through:

`python -m vitality_engagement.activation.cli`

Do not run it until approved contact-context files exist. The default local outputs are:

- `artifacts/activation/activation_decisions.parquet`
- `artifacts/activation/activation_decisions.metadata.json`
- `artifacts/activation/human_review_queue.parquet`
- `artifacts/activation/human_review_queue.metadata.json`

The human-review queue contains only records already marked `selected_for_review`, ordered by deterministic priority rank, with a fixed `pending_human_review` status. Its metadata preserves SHA-256 lineage to both source activation artifacts.

The CLI prints the activation artifact paths, review-queue paths, source rows audited, selected count, and `Mode: local artifacts only`.

A selected record is a recommendation for authorised human review only. It is not automatically approved for contact.

See `docs/activation_policy.md` and `docs/activation_runbook.md`.

## Stage 4 â€” Python modelling

Stage 4 implements a leakage-safe Python modelling workflow on top of the governed BigQuery feature layer.

### Modelling dataset

The feature export contains:

| Item                    |  Value |
| ----------------------- | -----: |
| Total rows              | 76,000 |
| Synthetic members       |    500 |
| Approved predictors     |     47 |
| Categorical predictors  |      3 |
| Numeric predictors      |     44 |
| Train rows              | 46,000 |
| Validation rows         | 15,500 |
| Test rows               | 11,000 |
| Unlabelled scoring rows |  3,500 |

The data is split chronologically rather than randomly. Member identifiers, prediction dates, targets, split labels, and prohibited future-derived fields are excluded from the predictor matrix.

### Selected model

The selected Python model is a regularised logistic-regression pipeline with:

* Most-frequent categorical imputation
* One-hot categorical encoding
* Median numeric imputation
* Numeric standardisation
* Logistic regression using `C=1.0`
* `lbfgs` solver
* Maximum 1,000 iterations
* Random state `42`

The decision threshold was selected on validation data only by maximising positive-class F1. The frozen threshold is:

```text
0.431
```

### Validation model comparison

| Metric                     | Logistic regression | Histogram gradient boosting |
| -------------------------- | ------------------: | --------------------------: |
| ROC-AUC                    |              0.9476 |                      0.9404 |
| PR-AUC                     |              0.8705 |                      0.8508 |
| Log loss                   |              0.2377 |                      0.2549 |
| Brier score                |              0.0733 |                      0.0792 |
| Positive-class F1          |              0.7721 |                      0.7499 |
| Top-decile lift            |              4.1395 |                      4.0620 |
| Expected calibration error |              0.0136 |                      0.0172 |

The nonlinear candidate did not improve validation performance enough to justify its additional complexity. Logistic regression therefore remains the frozen Stage 4 model.

### Frozen logistic test audit

| Metric                     | Result |
| -------------------------- | -----: |
| ROC-AUC                    | 0.9565 |
| PR-AUC                     | 0.9114 |
| Log loss                   | 0.2259 |
| Brier score                | 0.0690 |
| Precision                  | 0.8400 |
| Recall                     | 0.7920 |
| Positive-class F1          | 0.8153 |
| Specificity                | 0.9444 |
| Accuracy                   | 0.9034 |
| Top-decile lift            | 3.6833 |
| Expected calibration error | 0.0095 |

The logistic specification and threshold were frozen before this test evaluation. However, the test result had already been viewed before nonlinear-model development began. It is therefore a valid frozen-logistic audit, but not a completely untouched cross-model holdout for all Stage 4 experimentation.

The nonlinear candidate was developed and rejected using train and validation data only and was not evaluated on the test split.

### Stage 4 components

| Component             | Purpose                                             |
| --------------------- | --------------------------------------------------- |
| `schema.py`           | Approved predictor and export contracts             |
| `export_features.py`  | Deterministic BigQuery-to-Parquet export            |
| `load_data.py`        | Chronological split loading and validation          |
| `baseline.py`         | Logistic pipeline construction and fitting          |
| `nonlinear.py`        | Validation-only nonlinear challenger                |
| `evaluation.py`       | Metrics, threshold selection, calibration, and lift |
| `selection.py`        | Frozen logistic threshold record                    |
| `model_choice.py`     | Frozen validation-based model decision              |
| `test_evaluation.py`  | Frozen-threshold test evaluation                    |
| `explain.py`          | Logistic coefficients and odds ratios               |
| `persistence.py`      | Trusted model persistence and loading               |
| `predict.py`          | Typed persisted-model prediction interface          |
| `scoring_artifact.py` | Verified operational scoring artifacts              |

### Export the governed modelling dataset

```powershell
python -m vitality_engagement.models.export_features
```

The default output is:

```text
data/modeling/engagement_modeling_split.parquet
```

### Persist the selected model

```powershell
python -c "from vitality_engagement.models.load_data import load_chronological_modeling_data; from vitality_engagement.models.persistence import save_selected_model; save_selected_model(load_chronological_modeling_data())"
```

The local ignored artifacts are:

```text
models/python_logistic_baseline.pkl
models/python_logistic_baseline.metadata.json
```

Only trusted model artifacts created by this project should be loaded. Pickle artifacts can execute code during deserialisation.

### Generate operational predictions

```powershell
python -m vitality_engagement.models.scoring_artifact
```

The command scores the 3,500 unlabelled operational rows and creates:

```text
artifacts/scoring/python_logistic_scoring_predictions.parquet
artifacts/scoring/python_logistic_scoring_predictions.metadata.json
```

The prediction output contains:

| Column             | Meaning                                 |
| ------------------ | --------------------------------------- |
| `member_id`        | Synthetic member identifier             |
| `prediction_date`  | Prediction date                         |
| `risk_probability` | Estimated positive-class probability    |
| `is_high_risk`     | Whether probability is at least `0.431` |
| `model_name`       | Frozen model name                       |
| `threshold`        | Frozen threshold                        |

These rows are forecasts, not confirmed missed-goal outcomes.

## Quality gate

```powershell
ruff format --check .
ruff check .
mypy
pytest -q
pre-commit run --all-files
```

## Documentation

The full model card includes data lineage, preprocessing, evaluation results, explainability, persistence, intended use, limitations, and the test-holdout qualification:

```text
docs/model_card.md
```
