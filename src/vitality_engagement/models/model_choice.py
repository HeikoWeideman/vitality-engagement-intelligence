"""Frozen Stage 4 model choice based on validation-only evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

ModelName = Literal[
    "python_logistic_baseline",
    "hist_gradient_boosting",
]


class ModelChoiceError(ValueError):
    """Raised when a frozen model-choice record is invalid."""


@dataclass(frozen=True)
class ValidationModelMetrics:
    """Validation metrics used for model comparison."""

    model_name: ModelName
    roc_auc: float
    pr_auc: float
    log_loss: float
    brier_score: float
    positive_f1: float
    top_decile_lift: float
    expected_calibration_error: float

    def __post_init__(self) -> None:
        """Validate model-comparison metrics."""
        bounded_metrics = {
            "roc_auc": self.roc_auc,
            "pr_auc": self.pr_auc,
            "brier_score": self.brier_score,
            "positive_f1": self.positive_f1,
            "expected_calibration_error": self.expected_calibration_error,
        }

        for metric_name, metric_value in bounded_metrics.items():
            if metric_value < 0.0 or metric_value > 1.0:
                raise ModelChoiceError(f"{metric_name} must fall between zero and one.")

        if self.log_loss < 0.0:
            raise ModelChoiceError("Log loss must not be negative.")

        if self.top_decile_lift <= 0.0:
            raise ModelChoiceError("Top-decile lift must be positive.")


@dataclass(frozen=True)
class FrozenModelChoice:
    """Final Stage 4 model selected using validation data only."""

    selected_model: ModelName
    rejected_model: ModelName
    selection_split: Literal["validation"]
    rationale: str
    selected_metrics: ValidationModelMetrics
    rejected_metrics: ValidationModelMetrics

    def __post_init__(self) -> None:
        """Validate the frozen model choice."""
        if self.selected_model == self.rejected_model:
            raise ModelChoiceError("Selected and rejected models must differ.")

        if self.selection_split != "validation":
            raise ModelChoiceError("Model choice must be based on validation data.")

        if not self.rationale.strip():
            raise ModelChoiceError("Model-choice rationale must not be empty.")

        if self.selected_metrics.model_name != self.selected_model:
            raise ModelChoiceError("Selected metrics do not match the selected model.")

        if self.rejected_metrics.model_name != self.rejected_model:
            raise ModelChoiceError("Rejected metrics do not match the rejected model.")


LOGISTIC_VALIDATION_METRICS: Final = ValidationModelMetrics(
    model_name="python_logistic_baseline",
    roc_auc=0.9475771070325816,
    pr_auc=0.8705389454062007,
    log_loss=0.2376839513110581,
    brier_score=0.0732845711910035,
    positive_f1=0.7720781113378025,
    top_decile_lift=4.139457664637521,
    expected_calibration_error=0.013603559204041552,
)

HIST_GRADIENT_BOOSTING_VALIDATION_METRICS: Final = ValidationModelMetrics(
    model_name="hist_gradient_boosting",
    roc_auc=0.9404143248520043,
    pr_auc=0.85084915337156,
    log_loss=0.2548536313320763,
    brier_score=0.0791749035251201,
    positive_f1=0.749862258953168,
    top_decile_lift=4.061981184283343,
    expected_calibration_error=0.017235174926046107,
)

STAGE4_MODEL_CHOICE: Final = FrozenModelChoice(
    selected_model="python_logistic_baseline",
    rejected_model="hist_gradient_boosting",
    selection_split="validation",
    rationale=(
        "The logistic model achieved stronger validation ROC-AUC, "
        "PR-AUC, F1, log loss, Brier score, calibration error and "
        "top-decile lift. The nonlinear model did not earn its "
        "additional complexity."
    ),
    selected_metrics=LOGISTIC_VALIDATION_METRICS,
    rejected_metrics=HIST_GRADIENT_BOOSTING_VALIDATION_METRICS,
)
