 Vitality Engagement Intelligence Engine Reproducibility Guide

## Purpose

This guide describes how to reproduce the governed technical workflow using synthetic data, local Python components, version-controlled SQL, verified artifacts, dashboard assets, and monitoring controls.

It distinguishes:

- safe local commands;
- commands that modify BigQuery;
- commands requiring legitimate approved contact context;
- commands that must not be run merely for demonstration.

All data and outputs are for technical demonstration only.

Forecasts are not confirmed outcomes. Observed outcomes are descriptive, not causal. No command, dashboard, or monitoring result authorises operational action.

## Supported environment

| Requirement | Supported value |
| --- | --- |
| Operating workflow | Windows PowerShell |
| Python | `>=3.12,<3.15` |
| Packaging | `hatchling` through `pyproject.toml` |
| Google Cloud tools | `gcloud` and `bq` for BigQuery steps |
| BigQuery project | `vitality-engagement-43999` |
| BigQuery dataset | `vitality_engagement_dev` |
| BigQuery location | `asia-southeast1` |

Python 3.12, 3.13, and 3.14 satisfy the repository version contract.

## Command safety classes

| Class | Meaning |
| --- | --- |
| Local validation | Reads or verifies repository files without modifying BigQuery |
| Local artifact creation | Creates ignored outputs under `data/`, `models/`, or `artifacts/` |
| BigQuery dry run | Validates SQL without changing warehouse objects |
| BigQuery write | Creates, replaces, trains, or evaluates BigQuery objects |
| Restricted activation | Requires legitimate approved external contact context |
| Prohibited demonstration action | Must not populate empty states or upload records merely to demonstrate functionality |

## Repository preparation

Clone the repository and enter its root directory.

```powershell
git clone https://github.com/HeikoWeideman/vitality-engagement-intelligence.git
Set-Location .\vitality-engagement-intelligence
```

Confirm the branch and working-tree state.

```powershell
git branch --show-current
git status --short
```

Review unexpected working-tree changes before continuing.

## Python environment setup

Create and activate a virtual environment using a supported Python version.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project and development dependencies.

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Verify the interpreter and package import.

```powershell
python --version
python -c "import vitality_engagement; print(vitality_engagement.__name__)"
```

## Google Cloud prerequisites

BigQuery steps require:

- an authenticated Google Cloud CLI session;
- access to project `vitality-engagement-43999`;
- dataset `vitality_engagement_dev` in `asia-southeast1`;
- the BigQuery API;
- the `gcloud` and `bq` commands on `PATH`.

Confirm the authenticated account and active project.

```powershell
gcloud auth list
gcloud config get project
```

Set the project only after confirming the intended development environment.

```powershell
gcloud config set project vitality-engagement-43999
```

The governed SQL runner is:

- `scripts/run_bigquery_sql.ps1`

Its defaults are dataset `vitality_engagement_dev`, location `asia-southeast1`, and maximum bytes billed `100000000`.

Use -DryRun before SQL that creates, replaces, trains, or evaluates BigQuery objects.

## Safe execution order

Run the workflow in dependency order. Do not skip assertions merely because an earlier command completed.

### 1. Generate the synthetic dataset

This is a local artifact-creation step. Generated data is excluded from Git.

```powershell
python -m vitality_engagement.data.export_dataset
```

Optional parameters are available for member count, day count, random seed, and output directory.

```powershell
python -m vitality_engagement.data.export_dataset --help
```

Do not substitute real member data.

### 2. Confirm BigQuery execution variables

These commands assign the governed development configuration used by the SQL runner.

```powershell
$projectId = "vitality-engagement-43999"
$datasetId = "vitality_engagement_dev"
$location = "asia-southeast1"
$maximumBytesBilled = 100000000
```

### 3. Run staging, feature, split, model, and evaluation SQL

The following list preserves the repository dependency order.

```powershell
$sqlSteps = @(
    ".\sql\staging\01_create_engagement_staging.sql"
    ".\sql\tests\01_assert_engagement_staging.sql"
    ".\sql\features\01_create_engagement_features_28d.sql"
    ".\sql\tests\02_assert_engagement_features_28d.sql"
    ".\sql\splits\01_create_chronological_modeling_split.sql"
    ".\sql\tests\03_assert_chronological_modeling_split.sql"
    ".\sql\models\01_create_logistic_baseline_input.sql"
    ".\sql\models\02_train_logistic_baseline.sql"
    ".\sql\evaluation\01_create_logistic_validation_predictions.sql"
    ".\sql\evaluation\02_create_logistic_validation_thresholds.sql"
    ".\sql\evaluation\03_create_logistic_validation_calibration.sql"
    ".\sql\evaluation\04_create_logistic_validation_summary.sql"
    ".\sql\evaluation\05_create_logistic_test_predictions.sql"
    ".\sql\evaluation\06_create_logistic_test_calibration.sql"
    ".\sql\evaluation\07_create_logistic_test_summary.sql"
    ".\sql\evaluation\08_create_logistic_scoring_predictions.sql"
    ".\sql\tests\04_assert_logistic_baseline_evaluation.sql"
    ".\sql\tests\05_assert_logistic_scoring_predictions.sql"
)
```

For each SQL file, run a dry run first.

```powershell
foreach ($sqlFile in $sqlSteps) {
    .\scripts\run_bigquery_sql.ps1 `
        -SqlFile $sqlFile `
        -ProjectId $projectId `
        -DatasetId $datasetId `
        -Location $location `
        -MaximumBytesBilled $maximumBytesBilled `
        -DryRun
}
```

A dry run validates SQL and billing limits but does not create the required dependency objects.

After reviewing every dry-run result, execute the files sequentially in the same order.

```powershell
foreach ($sqlFile in $sqlSteps) {
    .\scripts\run_bigquery_sql.ps1 `
        -SqlFile $sqlFile `
        -ProjectId $projectId `
        -DatasetId $datasetId `
        -Location $location `
        -MaximumBytesBilled $maximumBytesBilled
}
```

These commands modify BigQuery. Run them only against the confirmed development project and dataset.

The Stage 3 BigQuery model remains the comparison baseline `bigquery_logistic_baseline` with threshold `0.467`.

It must not be described as the selected Stage 4 model.

### 4. Export the chronological modelling dataset

This step reads the governed BigQuery modelling split and creates a local ignored Parquet artifact.

Application Default Credentials are required.

```powershell
gcloud auth application-default login
```

Export the default governed feature table.

```powershell
python -m vitality_engagement.models.export_features
```

Review the available project, dataset, table, location, and output-path overrides before changing defaults.

```powershell
python -m vitality_engagement.models.export_features --help
```

Expected default output:

- `data/modeling/engagement_modeling_split.parquet`

The validated artifact contains 76,000 rows, 51 columns, 500 synthetic members, and the chronological train, validation, test, and unlabelled scoring splits.

The scoring labels must remain null.

### 5. Persist the selected Python model

This local artifact-creation command loads the validated chronological dataset, trains the selected model on the governed training split, and persists the trusted model and metadata.

```powershell
python -c "from vitality_engagement.models.load_data import load_chronological_modeling_data; from vitality_engagement.models.persistence import save_selected_model; save_selected_model(load_chronological_modeling_data())"
```

Expected default outputs:

- `models/python_logistic_baseline.pkl`
- `models/python_logistic_baseline.metadata.json`

The selected model identity is `python_logistic_baseline` and its frozen threshold is `0.431`.

Only load trusted pickle artifacts created by this repository. Pickle deserialisation can execute arbitrary code.

### 6. Generate the verified scoring artifact

This local command verifies the modelling data, selected model, and model metadata before scoring the unlabelled chronological split.

```powershell
python -m vitality_engagement.models.scoring_artifact
```

Review optional input and output overrides when reproducing artifacts outside their default paths.

```powershell
python -m vitality_engagement.models.scoring_artifact --help
```

Expected default outputs:

- `artifacts/scoring/python_logistic_scoring_predictions.parquet`
- `artifacts/scoring/python_logistic_scoring_predictions.metadata.json`

The verified scoring artifact contains 3,500 forecasts across 500 synthetic members for prediction dates from 2025-06-23 through 2025-06-29.

Forecasts are not confirmed missed-goal outcomes.

The scoring metadata must preserve the selected Python model identity, frozen threshold, schema, row counts, and source lineage.

Do not apply the BigQuery comparison threshold of `0.467` to these Python predictions.

### 7. Run activation only with approved context

Activation is a restricted local workflow. Do not run it unless legitimate approved contact-context files exist and authorised human review is available.

The repository intentionally provides no default production contact-context artifact.

Do not fabricate contact context merely to make this command run or to populate the valid governed empty state.

The following help command is safe because it does not execute activation.

```powershell
python -m vitality_engagement.activation.cli --help
```

A legitimate run requires:

- a verified contact-context Parquet artifact;
- its matching metadata JSON;
- a timezone-aware decision timestamp;
- the verified Stage 4 scoring artifact and metadata;
- authorised human review for any selected records.

The context snapshot must not be later than the decision timestamp.

The command structure is:

```powershell
python -m vitality_engagement.activation.cli `
    --context-path "C:\approved-inputs\member_contact_context.parquet" `
    --context-metadata-path "C:\approved-inputs\member_contact_context.metadata.json" `
    --decision-timestamp "YYYY-MM-DDTHH:MM:SS+HH:MM"
```

The paths and timestamp above are placeholders. Do not execute the example unchanged.

Expected default local outputs are:

- `artifacts/activation/activation_decisions.parquet`
- `artifacts/activation/activation_decisions.metadata.json`
- `artifacts/activation/human_review_queue.parquet`
- `artifacts/activation/human_review_queue.metadata.json`

The command verifies scoring and contact-context artifacts, applies deterministic policy rules, and creates local review artifacts.

Every scoring row receives one auditable activation outcome.

Selected review-queue rows remain `pending_human_review`.

Selected for review does not mean approved outreach.

The local activation command does not:

- upload records to BigQuery;
- contact members;
- send messages;
- dispatch interventions;
- approve outreach;
- change eligibility;
- create a production operational action.

BigQuery activation persistence is a separate guarded workflow.

Do not upload an activation run merely to demonstrate that the uploader works.

An empty activation state is valid when legitimate approved context is unavailable.

### 8. Reproduce the governed dashboard views

The Looker Studio report consumes governed BigQuery views rather than raw, staging, feature, scoring, activation, contact-context, or member-level sources.

The dashboard layer is:

- fully synthetic;
- aggregate-only;
- read-only;
- descriptive and non-causal;
- explicit about valid empty activation states;
- non-operational;
- protected by the governed subgroup minimum of 10.

Dashboard visibility does not authorise operational action.

The dashboard SQL and matching assertions must be executed in dependency order.

```powershell
$dashboardSqlSteps = @(
    @(
        ".\sql\dashboard\01_create_scoring_daily_summary.sql",
        ".\sql\tests\06_assert_dashboard_scoring_daily_summary.sql"
    )
    @(
        ".\sql\dashboard\02_create_risk_distribution.sql",
        ".\sql\tests\07_assert_dashboard_risk_distribution.sql"
    )
    @(
        ".\sql\dashboard\03_create_observed_outcome_summary.sql",
        ".\sql\tests\08_assert_dashboard_observed_outcome_summary.sql"
    )
    @(
        ".\sql\dashboard\04_create_activation_run_summary.sql",
        ".\sql\tests\09_assert_dashboard_activation_run_summary.sql"
    )
    @(
        ".\sql\dashboard\05_create_activation_outcome_summary.sql",
        ".\sql\tests\10_assert_dashboard_activation_outcome_summary.sql"
    )
    @(
        ".\sql\dashboard\06_create_activation_reason_summary.sql",
        ".\sql\tests\11_assert_dashboard_activation_reason_summary.sql"
    )
    @(
        ".\sql\dashboard\07_create_review_selection_summary.sql",
        ".\sql\tests\12_assert_dashboard_review_selection_summary.sql"
    )
    @(
        ".\sql\dashboard\08_create_lineage_freshness_summary.sql",
        ".\sql\tests\13_assert_dashboard_lineage_freshness_summary.sql"
    )
    @(
        ".\sql\dashboard\09_create_dashboard_quality_status.sql",
        ".\sql\tests\14_assert_dashboard_quality_status.sql"
    )
)
```

For each view and assertion, perform a dry run and then execute it before advancing to the next dependency pair.

```powershell
foreach ($step in $dashboardSqlSteps) {
    foreach ($sqlFile in $step) {
        .\scripts\run_bigquery_sql.ps1 `
            -SqlFile $sqlFile `
            -ProjectId $projectId `
            -DatasetId $datasetId `
            -Location $location `
            -MaximumBytesBilled $maximumBytesBilled `
            -DryRun

        .\scripts\run_bigquery_sql.ps1 `
            -SqlFile $sqlFile `
            -ProjectId $projectId `
            -DatasetId $datasetId `
            -Location $location `
            -MaximumBytesBilled $maximumBytesBilled
    }
}
```

These commands create or replace BigQuery views and therefore modify the confirmed development dataset.

Do not run them merely to inspect existing dashboard evidence.

The governed views are:

- `dashboard_scoring_daily_summary`;
- `dashboard_risk_distribution`;
- `dashboard_observed_outcome_summary`;
- `dashboard_activation_run_summary`;
- `dashboard_activation_outcome_summary`;
- `dashboard_activation_reason_summary`;
- `dashboard_review_selection_summary`;
- `dashboard_lineage_freshness_summary`;
- `dashboard_quality_status`.

The forecast views use `bigquery_logistic_baseline` with threshold `0.467`.

They do not use the selected Python threshold of `0.431`.

Observed outcomes must remain separate from forecasts and are descriptive, not causal.

Activation views must preserve the valid governed empty state when no legitimate activation runs exist.

Looker Studio construction is a manual reporting step. Connect it only to the governed dashboard views.

Do not expose member identifiers, member-level probabilities, contact context, review-queue records, or operational controls.

The validated report contains five pages. Its retained evidence is documented in docs/stage_6_dashboard_evidence.md.

### 9. Reproduce governed monitoring

Monitoring is a technical, local, and read-only governance workflow. It does not contact members, send alerts externally, change thresholds, retrain models, replace models, or authorise operational action.

#### Local Python monitoring

Review the command interface without writing artifacts:

```powershell
python -m vitality_engagement.monitoring.cli --help
```

A monitoring run requires an explicit timezone-aware ISO-8601 timestamp:

```powershell
python -m vitality_engagement.monitoring.cli `
    --monitoring-timestamp "YYYY-MM-DDTHH:MM:SS+HH:MM"
```

The timestamp above is a placeholder. Replace it with the actual monitoring time and timezone offset.

Before running monitoring:

- confirm that the Stage 4 modelling, model, and scoring artifacts exist;
- confirm that model and scoring metadata match their artifacts;
- preserve existing monitoring evidence when replacement is not intended;
- confirm that input and output paths do not overlap;
- ensure no external alert or operational action is connected to the command.

The default local inputs are:

- `data/modeling/engagement_modeling_split.parquet`;
- the persisted selected Python model;
- the persisted selected-model metadata;
- `artifacts/scoring/python_logistic_scoring_predictions.parquet`;
- `artifacts/scoring/python_logistic_scoring_predictions.metadata.json`.

The default outputs are:

- `artifacts/monitoring/monitoring_checks.parquet`;
- `artifacts/monitoring/monitoring_checks.metada.json`.

The command verifies artifact identity, metadata, schemas, SHA-256 lineage, model identity, threshold, scoring volume, probabilities, and monitored feature distributions before writing final outputs.

Local exit codes have governed meanings:

| Exit code | Meaning |
| ---: | --- |
| `0` | Monitoring completed with overall pass or warning severity |
| `2` | Monitoring completed and found at least one governed critical condition |
| Other non-zero | Argument, verification, or execution failure |

Exit code `2` is not an unhandled execution failure.

The retained Stage 7 evidence run evaluated 57 checks:

| Severity | Count |
| --- | ---: |
| Pass | 53 |
| Warning | 2 |
| Critical | 2 |

The retained non-passing findings are:

| Check | Observed value | Severity |
| --- | ---: | --- |
| Probability PSI | `0.155921` | Warning |
| `previous_goal_streak_as_of` PSI | `1.559510` | Critical |
| `previous_failed_goals_as_of` PSI | `0.290255` | Critical |
| `avg_goal_completion_percentage_28d` PSI | `0.109969` | Warning |

Do not weaken monitoring thresholds merely to obtain a passing result.

Monitoring detects these concerns; it does not resolve them.

#### BigQuery model monitoring

The BigQuery model-monitoring view evaluates the separate Stage 3 comparison baseline:

- model: `bigquery_logistic_baseline`;
- threshold: `0.467`;
- view: `vitality_engagement_dev.model_monitoring_status`;
- SQL: `sql/monitoring/01_create_model_monitoring_status.sql`;
- assertion: `sql/tests/15_assert_model_monitoring_status.sql`.

Dry-run the view SQL:

```powershell
.\scripts\run_bigquery_sql.ps1 `
    -SqlFile .\sql\monitoring\01_create_model_monitoring_status.sql `
    -ProjectId $projectId `
    -DatasetId $datasetId `
    -Location $location `
    -MaximumBytesBilled $maximumBytesBilled `
    -DryRun
```

After reviewing the dry run, create or replace the view:

```powershell
.\scripts\run_bigquery_sql.ps1 `
    -SqlFile .\sql\monitoring\01_create_model_monitoring_status.sql `
    -ProjectId $projectId `
    -DatasetId $datasetId `
    -Location $location `
    -MaximumBytesBilled $maximumBytesBilled
```

Dry-run and then execute the assertion:

```powershell
.\scripts\run_bigquery_sql.ps1 `
    -SqlFile .\sql\tests\15_assert_model_monitoring_status.sql `
    -ProjectId $projectId `
    -DatasetId $datasetId `
    -Location $location `
    -MaximumBytesBilled $maximumBytesBilled `
    -DryRun

.\scripts\run_bigquery_sql.ps1 `
    -SqlFile .\sql\tests\15_assert_model_monitoring_status.sql `
    -ProjectId $projectId `
    -DatasetId $datasetId `
    -Location $location `
    -MaximumBytesBilled $maximumBytesBilled
```

The retained BigQuery result contained nine passing checks and two critical training-support breaches:

| Check | Observed | Expected | Severity |
| --- | ---: | ---: | --- |
| `previous_goal_streak_training_support_breach_count` | 1,708 | 0 | Critical |
| `previous_failed_goals_training_support_breach_count` | 268 | 0 | Critical |

This view does not evaluate or replace the selected Python model and must not use the Python threshold of `0.431`.

Creating or replacing this view modifies the confirmed development dataset. The resulting monitoring view is read-only and does not authorise operational action.


#### BigQuery governance monitoring

The governance-monitoring view evaluates activation empty-state validity, dashboard quality, and dashboard lineage and freshness:

- view: `vitality_engagement_dev.governance_monitoring_status`;
- SQL: `sql/monitoring/02_create_governance_monitoring_status.sql`;
- assertion: `sql/tests/16_assert_governance_monitoring_status.sql`.

Dry-run the view SQL:

```powershell
.\scripts\run_bigquery_sql.ps1 `
    -SqlFile .\sql\monitoring\02_create_governance_monitoring_status.sql `
    -ProjectId $projectId `
    -DatasetId $datasetId `
    -Location $location `
    -MaximumBytesBilled $maximumBytesBilled `
    -DryRun
```

After reviewing the dry run, create or replace the view:

```powershell
.\scripts\run_bigquery_sql.ps1 `
    -SqlFile .\sql\monitoring\02_create_governance_monitoring_status.sql `
    -ProjectId $projectId `
    -DatasetId $datasetId `
    -Location $location `
    -MaximumBytesBilled $maximumBytesBilled
```

Dry-run and then execute its assertion:

```powershell
.\scripts\run_bigquery_sql.ps1 `
    -SqlFile .\sql\tests\16_assert_governance_monitoring_status.sql `
    -ProjectId $projectId `
    -DatasetId $datasetId `
    -Location $location `
    -MaximumBytesBilled $maximumBytesBilled `
    -DryRun

.\scripts\run_bigquery_sql.ps1 `
    -SqlFile .\sql\tests\16_assert_governance_monitoring_status.sql `
    -ProjectId $projectId `
    -DatasetId $datasetId `
    -Location $location `
    -MaximumBytesBilled $maximumBytesBilled
```

The retained governance result contained three passing checks and no warning or critical checks.

The checks cover:

- activation empty-state validity;
- dashboard quality;
- dashboard lineage and freshness.

Both BigQuery monitoring views set `operational_action_authorised` to `FALSE`.

Creating or replacing this view modifies the confirmed development dataset. The resulting monitoring view is read-only and does not grant operational authority.

#### Monitoring response boundary

Warnings and critical findings require documented human review.

Monitoring must not automatically:

- contact members;
- dispatch interventions;
- alter eligibility;
- impose penalties;
- change a model threshold;
- retrain, promote, or replace a model;
- suppress or delete an adverse result;
- reinterpret forecasts as confirmed outcomes.

The retained Stage 7 evidence is documented in `docs/stage_7_monitoring_evidence.md`.

## Expected artifacts and evidence

Generated datasets, models, and runtime artifacts are excluded from Git. Reproduction should create or verify them locally without committing sensitive or environment-specific outputs.

| Stage | Expected local artifact or retained evidence | Git treatment |
| --- | --- | --- |
| Synthetic data | Generated files under `data/` | Ignored |
| Chronological modelling export | `data/modeling/engagement_modeling_split.parquet` | Ignored |
| Selected Python model | `models/python_logistic_baseline.pkl` | Ignored |
| Selected-model metadata | `models/python_logistic_baseline.metadata.json` | Ignored |
| Scoring predictions | `artifacts/scoring/python_logistic_scoring_predictions.parquet` | Ignored |
| Scoring metadata | `artifacts/scoring/python_logistic_scoring_predictions.metadata.json` | Ignored |
| Activation decisions | `artifacts/activation/activation_decisions.parquet` | Ignored |
| Activation metadata | `artifacts/activation/activation_decisions.metadata.json` | Ignored |
| Human-review queue | `artifacts/activation/human_review_queue.parquet` | Ignored |
| Human-review metadata | `artifacts/activation/human_review_queue.metadata.json` | Ignored |
| Monitoring checks | `artifacts/monitoring/monitoring_checks.parquet` | Ignored |
| Monitoring metadata | `artifacts/monitoring/monitoring_checks.metadata.json` | Ignored |
| Dashboard evidence | `docs/stage_6_dashboard_evidence.md` and retained screenshots | Tracked evidence |
| Monitoring evidence | `docs/stage_7_monitoring_evidence.md` | Tracked evidence |

Do not commit generated data, trained-model binaries, credentials, contact-context artifacts, member-level review queues, or environment-specific runtime outputs.

## Repository quality gate

Run the repository quality gate from the activated virtual environment after documentation or code changes.

```powershell
ruff format --check .
```

```powershell
ruff check .
```

```powershell
mypy
```

```powershell
pytest -q
```

Run whitespace validation:

```powershell
git diff --check
```

Before staging, inspect the complete working tree and diff summary:

```powershell
git status --short
git diff --stat
```

After staging only the intended files, run:

```powershell
git diff --cached --check
git diff --cached --stat
```

Do not commit unless the targeted checks and full quality gate pass.

## Reproducibility boundaries

Reproducing the technical workflow does not establish:

- clinical validity;
- causal intervention effectiveness;
- production fairness;
- production privacy compliance;
- legal or regulatory compliance;
- member-contact authorisation;
- safe automated decision-making;
- production deployment readiness.

The project uses fully synthetic data and has not been validated with real members or live operational workflows.

The selected Python threshold of `0.431` was chosen using validation positive-class F1. It was not selected using clinical value, intervention cost, member harm, financial optimisation, or treatment effectiveness.

The BigQuery comparison threshold of `0.467` belongs only to `bigquery_logistic_baseline`.

Monitoring warnings and critical findings must remain visible. Reproduction must not weaken thresholds, suppress adverse results, or relabel forecasts as confirmed outcomes.

## Commands not to run merely for demonstration

Do not:

- fabricate contact context to force a non-empty activation result;
- upload activation artifacts merely to prove persistence works;
- execute BigQuery write commands against an unconfirmed project or dataset;
- overwrite retained evidence without an explicit replacement decision;
- load untrusted pickle files;
- connect monitoring output to automatic outreach or intervention dispatch;
- commit credentials, contact context, member-level artifacts, or generated data;
- interpret a passing technical check as proof of production suitability.

## Related documentation

- [Project architecture](project_architecture.md)
- [Repository README](../README.md)
- [Synthetic dataset card](data_card.md)
- [Dataset distribution review](data_distribution_review.md)
- [BigQuery and SQL architecture](bigquery_architecture.md)
- [BigQuery ML baseline results](bigquery_baseline_results.md)
- [Python model results](python_logistic_baseline_results.md)
- [Model card](model_card.md)
- [Activation policy](activation_policy.md)
- [Activation runbook](activation_runbook.md)
- [Dashboard requirements](dashboard_requirements.md)
- [Dashboard metric inventory](dashboard_metric_inventory.md)
- [Stage 6 dashboard evidence](stage_6_dashboard_evidence.md)
- [Monitoring policy](monitoring_policy.md)
- [Monitoring runbook](monitoring_runbook.md)
- [Stage 7 monitoring evidence](stage_7_monitoring_evidence.md)

## Completion checklist

A reproducible review is complete only when:

- the intended environment and branch are confirmed;
- local dependencies are installed;
- synthetic data and governed artifacts are generated or verified;
- BigQuery writes, when required, are dry-run before execution;
- model identities and thresholds remain separated;
- activation is not run without legitimate approved context;
- dashboard sources remain aggregate-only and governed;
- monitoring warnings and critical findings remain visible;
- the full quality gate passes;
- no generated, sensitive, or environment-specific artifacts are staged.
