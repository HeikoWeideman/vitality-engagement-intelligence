"""Tests for the frozen Stage 4 validation model choice."""

import pytest

from vitality_engagement.models.model_choice import (
    HIST_GRADIENT_BOOSTING_VALIDATION_METRICS,
    LOGISTIC_VALIDATION_METRICS,
    STAGE4_MODEL_CHOICE,
    FrozenModelChoice,
    ModelChoiceError,
)


def test_logistic_model_is_selected() -> None:
    choice = STAGE4_MODEL_CHOICE

    assert choice.selected_model == "python_logistic_baseline"
    assert choice.rejected_model == "hist_gradient_boosting"
    assert choice.selection_split == "validation"


def test_selected_model_has_stronger_validation_metrics() -> None:
    logistic = LOGISTIC_VALIDATION_METRICS
    nonlinear = HIST_GRADIENT_BOOSTING_VALIDATION_METRICS

    assert logistic.roc_auc > nonlinear.roc_auc
    assert logistic.pr_auc > nonlinear.pr_auc
    assert logistic.positive_f1 > nonlinear.positive_f1
    assert logistic.log_loss < nonlinear.log_loss
    assert logistic.brier_score < nonlinear.brier_score
    assert logistic.expected_calibration_error < nonlinear.expected_calibration_error
    assert logistic.top_decile_lift > nonlinear.top_decile_lift


def test_model_choice_contains_explicit_complexity_rationale() -> None:
    assert "did not earn" in STAGE4_MODEL_CHOICE.rationale


def test_selected_and_rejected_models_must_differ() -> None:
    with pytest.raises(
        ModelChoiceError,
        match="must differ",
    ):
        FrozenModelChoice(
            selected_model="python_logistic_baseline",
            rejected_model="python_logistic_baseline",
            selection_split="validation",
            rationale="Invalid duplicate choice.",
            selected_metrics=LOGISTIC_VALIDATION_METRICS,
            rejected_metrics=LOGISTIC_VALIDATION_METRICS,
        )
