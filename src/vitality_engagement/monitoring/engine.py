"""Deterministic Stage 7 monitoring evaluation over verified local inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Final

import pandas as pd
from sklearn.pipeline import Pipeline

from vitality_engagement.data.generate_members import AGE_BANDS
from vitality_engagement.data.schema import ActivityLevel, ResponseProfile
from vitality_engagement.models.load_data import ChronologicalModelingData
from vitality_engagement.models.persistence import (
    ModelArtifactMetadata,
    calculate_schema_fingerprint,
)
from vitality_engagement.models.predict import (
    RISK_PROBABILITY_COLUMN,
    PredictionBatch,
    predict_with_pipeline,
)
from vitality_engagement.models.schema import (
    CATEGORICAL_FEATURE_COLUMNS,
    MODEL_FEATURE_COLUMNS,
    NUMERIC_FEATURE_COLUMNS,
)
from vitality_engagement.models.scoring_artifact import VerifiedScoringArtifact
from vitality_engagement.monitoring.drift import (
    calculate_categorical_psi,
    calculate_numeric_psi,
)
from vitality_engagement.monitoring.policy import (
    MonitoringPolicy,
    calculate_monitoring_policy_fingerprint,
)
from vitality_engagement.monitoring.schema import (
    MonitoringCheckResult,
    MonitoringCheckType,
    MonitoringSeverity,
    classify_upper_threshold,
    maximum_severity,
)


class MonitoringEngineError(RuntimeError):
    """Raised when verified monitoring inputs cannot be reconciled safely."""


APPROVED_CATEGORICAL_DOMAINS: Final = MappingProxyType(
    {
        "age_band_as_of": frozenset(AGE_BANDS),
        "activity_level_as_of": frozenset(level.value for level in ActivityLevel),
        "reward_profile_as_of": frozenset(profile.value for profile in ResponseProfile),
    }
)


@dataclass(frozen=True)
class MonitoringRunResult:
    """Complete deterministic result for one governed monitoring run."""

    policy_version: str
    policy_fingerprint: str
    model_name: str
    threshold: float
    scoring_artifact_sha256: str
    reference_row_count: int
    current_row_count: int
    overall_severity: MonitoringSeverity
    checks: tuple[MonitoringCheckResult, ...]

    def __post_init__(self) -> None:
        """Validate aggregate monitoring-result consistency."""
        if not self.policy_version.strip():
            raise MonitoringEngineError("policy_version must not be empty.")

        if len(self.policy_fingerprint) != 64:
            raise MonitoringEngineError("policy_fingerprint must be a SHA-256 digest.")

        if not self.model_name.strip():
            raise MonitoringEngineError("model_name must not be empty.")

        if self.threshold < 0.0 or self.threshold > 1.0:
            raise MonitoringEngineError("threshold must fall between zero and one.")

        if len(self.scoring_artifact_sha256) != 64:
            raise MonitoringEngineError("scoring_artifact_sha256 must be a SHA-256 digest.")

        if self.reference_row_count < 1 or self.current_row_count < 1:
            raise MonitoringEngineError("Monitoring row counts must be positive.")

        if not self.checks:
            raise MonitoringEngineError("A monitoring run must contain at least one check.")

        expected_overall = maximum_severity(*(check.severity for check in self.checks))

        if self.overall_severity is not expected_overall:
            raise MonitoringEngineError("overall_severity does not match the monitoring checks.")


def _identifier_pairs(
    identifiers: pd.DataFrame,
) -> set[tuple[str, date]]:
    """Return governed member and prediction-date identifier pairs."""
    try:
        parsed_dates = pd.to_datetime(
            identifiers["prediction_date"],
            errors="raise",
        )
    except (KeyError, TypeError, ValueError) as error:
        raise MonitoringEngineError(
            "Monitoring identifiers contain invalid prediction dates."
        ) from error

    member_ids = identifiers["member_id"].astype(str).tolist()
    prediction_dates = [pd.Timestamp(value).date() for value in parsed_dates.tolist()]

    return set(
        zip(
            member_ids,
            prediction_dates,
            strict=True,
        )
    )


def _validate_scoring_feature_alignment(
    data: ChronologicalModelingData,
    scoring_artifact: VerifiedScoringArtifact,
) -> None:
    """Require scoring features and persisted predictions to describe one batch."""
    feature_identifiers = _identifier_pairs(data.scoring.identifiers)
    prediction_identifiers = {
        (
            prediction.member_id,
            prediction.prediction_date,
        )
        for prediction in scoring_artifact.predictions
    }

    if feature_identifiers != prediction_identifiers:
        raise MonitoringEngineError(
            "Scoring features and prediction artifacts contain different identifiers."
        )


def _exact_check(
    *,
    check_name: str,
    check_type: MonitoringCheckType,
    observed_value: float,
    expected_value: float,
    details: str,
) -> MonitoringCheckResult:
    """Build an exact-match check with critical failure severity."""
    severity = (
        MonitoringSeverity.PASS if observed_value == expected_value else MonitoringSeverity.CRITICAL
    )

    return MonitoringCheckResult(
        check_name=check_name,
        check_type=check_type,
        severity=severity,
        observed_value=observed_value,
        expected_value=expected_value,
        details=details,
    )


def _identity_check(
    *,
    check_name: str,
    check_type: MonitoringCheckType,
    matches: bool,
    details: str,
) -> MonitoringCheckResult:
    """Build a Boolean identity check using numeric persisted values."""
    return _exact_check(
        check_name=check_name,
        check_type=check_type,
        observed_value=1.0 if matches else 0.0,
        expected_value=1.0,
        details=details,
    )


def _unexpected_category_rate(
    values: pd.Series,
    *,
    allowed_categories: frozenset[str],
) -> float:
    """Return the rate of non-null categories outside the approved domain."""
    non_missing = values.dropna().astype(str)
    unexpected_mask = ~non_missing.isin(allowed_categories)
    return float(unexpected_mask.sum() / len(values))


def evaluate_monitoring_run(
    *,
    data: ChronologicalModelingData,
    pipeline: Pipeline,
    model_metadata: ModelArtifactMetadata,
    scoring_artifact: VerifiedScoringArtifact,
    policy: MonitoringPolicy | None = None,
) -> MonitoringRunResult:
    """Evaluate volume, identity, probability, and feature-distribution checks."""
    active_policy = policy or MonitoringPolicy()

    if tuple(str(column) for column in data.train.features.columns) != (MODEL_FEATURE_COLUMNS):
        raise MonitoringEngineError("Training features do not match the governed model schema.")

    if tuple(str(column) for column in data.scoring.features.columns) != (MODEL_FEATURE_COLUMNS):
        raise MonitoringEngineError("Scoring features do not match the governed model schema.")

    _validate_scoring_feature_alignment(
        data,
        scoring_artifact,
    )

    checks: list[MonitoringCheckResult] = []
    scoring_metadata = scoring_artifact.metadata

    prediction_days = {prediction.prediction_date for prediction in scoring_artifact.predictions}

    checks.extend(
        [
            _exact_check(
                check_name="scoring_row_count",
                check_type=MonitoringCheckType.SCORING_VOLUME,
                observed_value=float(scoring_metadata.row_count),
                expected_value=float(active_policy.expected_scoring_row_count),
                details=(
                    "Persisted scoring rows are compared with the governed expected batch size."
                ),
            ),
            _exact_check(
                check_name="scoring_member_count",
                check_type=MonitoringCheckType.SCORING_VOLUME,
                observed_value=float(scoring_metadata.member_count),
                expected_value=float(active_policy.expected_scoring_member_count),
                details=(
                    "Distinct scoring members are compared with the governed expected member count."
                ),
            ),
            _exact_check(
                check_name="scoring_prediction_day_count",
                check_type=MonitoringCheckType.SCORING_VOLUME,
                observed_value=float(len(prediction_days)),
                expected_value=float(active_policy.expected_scoring_prediction_day_count),
                details=(
                    "Distinct prediction dates are compared with the governed "
                    "expected scoring window."
                ),
            ),
        ]
    )

    model_identity_matches = scoring_metadata.model_name == model_metadata.model_name
    threshold_identity_matches = scoring_metadata.threshold == model_metadata.selected_threshold
    schema_identity_matches = model_metadata.schema_fingerprint == calculate_schema_fingerprint()

    checks.extend(
        [
            _identity_check(
                check_name="model_identity",
                check_type=MonitoringCheckType.MODEL_IDENTITY,
                matches=model_identity_matches,
                details=(
                    "The scoring artifact model name must match the trusted "
                    "persisted-model metadata."
                ),
            ),
            _identity_check(
                check_name="threshold_identity",
                check_type=MonitoringCheckType.THRESHOLD_IDENTITY,
                matches=threshold_identity_matches,
                details=(
                    "The scoring artifact threshold must match the frozen "
                    "persisted-model threshold."
                ),
            ),
            _identity_check(
                check_name="schema_identity",
                check_type=MonitoringCheckType.SCHEMA_IDENTITY,
                matches=schema_identity_matches,
                details=(
                    "The persisted model schema fingerprint must match the "
                    "current governed predictor contract."
                ),
            ),
        ]
    )

    if model_identity_matches and threshold_identity_matches:
        reference_batch = PredictionBatch(
            identifiers=data.train.identifiers,
            features=data.train.features,
        )
        reference_predictions = predict_with_pipeline(
            pipeline,
            reference_batch,
            model_name=model_metadata.model_name,
            threshold=model_metadata.selected_threshold,
        )
        probability_drift = calculate_numeric_psi(
            reference_predictions.predictions[RISK_PROBABILITY_COLUMN],
            scoring_artifact.result.predictions[RISK_PROBABILITY_COLUMN],
            bin_count=active_policy.probability_bin_count,
        )
        probability_severity = classify_upper_threshold(
            probability_drift.psi,
            warning_threshold=active_policy.psi_warning_threshold,
            critical_threshold=active_policy.psi_critical_threshold,
        )
        probability_details = (
            "Population stability index compares frozen-model training "
            "probabilities with the verified scoring distribution."
        )
        probability_value = probability_drift.psi
    else:
        probability_severity = MonitoringSeverity.CRITICAL
        probability_details = (
            "Probability drift was not comparable because model or threshold identity failed."
        )
        probability_value = active_policy.psi_critical_threshold

    checks.append(
        MonitoringCheckResult(
            check_name="probability_population_stability_index",
            check_type=MonitoringCheckType.PROBABILITY_DRIFT,
            severity=probability_severity,
            observed_value=probability_value,
            expected_value=0.0,
            warning_threshold=active_policy.psi_warning_threshold,
            critical_threshold=active_policy.psi_critical_threshold,
            reference_row_count=len(data.train.features),
            current_row_count=len(data.scoring.features),
            details=probability_details,
        )
    )

    for feature_name in NUMERIC_FEATURE_COLUMNS:
        drift = calculate_numeric_psi(
            data.train.features[feature_name],
            data.scoring.features[feature_name],
            bin_count=active_policy.numeric_feature_bin_count,
        )
        severity = classify_upper_threshold(
            drift.psi,
            warning_threshold=active_policy.psi_warning_threshold,
            critical_threshold=active_policy.psi_critical_threshold,
        )
        checks.append(
            MonitoringCheckResult(
                check_name=f"numeric_feature_psi__{feature_name}",
                check_type=MonitoringCheckType.NUMERIC_FEATURE_DRIFT,
                severity=severity,
                observed_value=drift.psi,
                expected_value=0.0,
                warning_threshold=active_policy.psi_warning_threshold,
                critical_threshold=active_policy.psi_critical_threshold,
                reference_row_count=len(data.train.features),
                current_row_count=len(data.scoring.features),
                feature_name=feature_name,
                details=(
                    "Numeric feature PSI compares the training reference "
                    "distribution with the current scoring split."
                ),
            )
        )

    for feature_name in CATEGORICAL_FEATURE_COLUMNS:
        categorical_drift = calculate_categorical_psi(
            data.train.features[feature_name],
            data.scoring.features[feature_name],
        )
        drift_severity = classify_upper_threshold(
            categorical_drift.psi,
            warning_threshold=active_policy.psi_warning_threshold,
            critical_threshold=active_policy.psi_critical_threshold,
        )
        checks.append(
            MonitoringCheckResult(
                check_name=f"categorical_feature_psi__{feature_name}",
                check_type=MonitoringCheckType.CATEGORICAL_FEATURE_DRIFT,
                severity=drift_severity,
                observed_value=categorical_drift.psi,
                expected_value=0.0,
                warning_threshold=active_policy.psi_warning_threshold,
                critical_threshold=active_policy.psi_critical_threshold,
                reference_row_count=len(data.train.features),
                current_row_count=len(data.scoring.features),
                feature_name=feature_name,
                details=(
                    "Categorical feature PSI compares aligned training and "
                    "scoring category distributions."
                ),
            )
        )

        unexpected_rate = _unexpected_category_rate(
            data.scoring.features[feature_name],
            allowed_categories=APPROVED_CATEGORICAL_DOMAINS[feature_name],
        )
        unexpected_severity = classify_upper_threshold(
            unexpected_rate,
            warning_threshold=(active_policy.unseen_category_warning_rate),
            critical_threshold=(active_policy.unseen_category_critical_rate),
        )
        checks.append(
            MonitoringCheckResult(
                check_name=f"unexpected_category_rate__{feature_name}",
                check_type=MonitoringCheckType.UNSEEN_CATEGORY_RATE,
                severity=unexpected_severity,
                observed_value=unexpected_rate,
                expected_value=0.0,
                warning_threshold=(active_policy.unseen_category_warning_rate),
                critical_threshold=(active_policy.unseen_category_critical_rate),
                reference_row_count=len(data.train.features),
                current_row_count=len(data.scoring.features),
                feature_name=feature_name,
                details=(
                    "Unexpected-category rate uses the approved synthetic "
                    "domain, not merely categories observed during training."
                ),
            )
        )

    check_tuple = tuple(checks)

    return MonitoringRunResult(
        policy_version=active_policy.policy_version,
        policy_fingerprint=calculate_monitoring_policy_fingerprint(active_policy),
        model_name=model_metadata.model_name,
        threshold=model_metadata.selected_threshold,
        scoring_artifact_sha256=(scoring_artifact.prediction_artifact_sha256),
        reference_row_count=len(data.train.features),
        current_row_count=len(data.scoring.features),
        overall_severity=maximum_severity(*(check.severity for check in check_tuple)),
        checks=check_tuple,
    )
