"""Python logistic-regression baseline fitted on the chronological training split."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from vitality_engagement.models.load_data import ChronologicalModelingData
from vitality_engagement.models.schema import (
    CATEGORICAL_FEATURE_COLUMNS,
    NUMERIC_FEATURE_COLUMNS,
)

RANDOM_SEED: Final = 42
MAX_ITERATIONS: Final = 1_000


class LogisticBaselineError(RuntimeError):
    """Raised when the Python logistic baseline produces invalid output."""


@dataclass(frozen=True)
class LogisticBaselineValidationResult:
    """Fitted logistic pipeline and its validation probabilities."""

    pipeline: Pipeline
    validation_probabilities: npt.NDArray[np.float64]
    validation_row_count: int

    def __post_init__(self) -> None:
        """Validate probability shape, completeness, and range."""
        probabilities = self.validation_probabilities

        if probabilities.ndim != 1:
            raise LogisticBaselineError("Validation probabilities must be one-dimensional.")

        if len(probabilities) != self.validation_row_count:
            raise LogisticBaselineError(
                "Validation probability count does not match validation rows."
            )

        if not bool(np.isfinite(probabilities).all()):
            raise LogisticBaselineError("Validation probabilities contain non-finite values.")

        if bool(((probabilities < 0.0) | (probabilities > 1.0)).any()):
            raise LogisticBaselineError("Validation probabilities fall outside zero to one.")


def build_logistic_baseline_pipeline() -> Pipeline:
    """Build the leakage-safe Python logistic-regression pipeline."""
    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent"),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                categorical_pipeline,
                list(CATEGORICAL_FEATURE_COLUMNS),
            ),
            (
                "numeric",
                numeric_pipeline,
                list(NUMERIC_FEATURE_COLUMNS),
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    classifier = LogisticRegression(
        C=1.0,
        solver="lbfgs",
        max_iter=MAX_ITERATIONS,
        random_state=RANDOM_SEED,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def fit_logistic_baseline(
    data: ChronologicalModelingData,
) -> LogisticBaselineValidationResult:
    """Fit on training rows and predict probabilities for validation only."""
    pipeline = build_logistic_baseline_pipeline()

    pipeline.fit(
        data.train.features,
        data.train.target,
    )

    probability_matrix = np.asarray(
        pipeline.predict_proba(data.validation.features),
        dtype=np.float64,
    )

    if probability_matrix.ndim != 2:
        raise LogisticBaselineError("Classifier probability output must be two-dimensional.")

    classes = np.asarray(pipeline.classes_)
    positive_matches = np.flatnonzero(np.equal(classes, np.bool_(True)))

    if len(positive_matches) != 1:
        raise LogisticBaselineError(
            "Classifier does not expose exactly one positive Boolean class."
        )

    positive_class_index = int(positive_matches[0])

    if probability_matrix.shape != (
        len(data.validation.features),
        len(classes),
    ):
        raise LogisticBaselineError("Classifier probability dimensions are inconsistent.")

    validation_probabilities = probability_matrix[
        :,
        positive_class_index,
    ].copy()

    return LogisticBaselineValidationResult(
        pipeline=pipeline,
        validation_probabilities=validation_probabilities,
        validation_row_count=len(data.validation.features),
    )
