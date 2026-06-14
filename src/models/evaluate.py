"""
Evaluation metrics for multiclass match outcome prediction.

Why these six metrics?
----------------------
accuracy         : Intuitive fraction correct; misleads when classes
                   are imbalanced (home wins ~44% of data).
log_loss         : Measures probability quality, not just prediction
                   direction.  A model that says 99% when truth is 50%
                   is punished far more than one that says 60%.
brier_score      : Mean squared error in probability space.  Lower = better
                   calibrated.  Ranges from 0 (perfect) to 2 (maximally wrong).
f1_macro         : Unweighted average F1 across the three classes.
                   Critical for detecting if the model ignores draws.
precision_w      : Weighted precision — measures false positive rate,
                   weighted by class frequency.
recall_w         : Weighted recall — measures coverage of each class.

Log Loss and Brier Score are the most important for this project
because the Monte Carlo simulation (Phase 6) uses predicted probabilities
directly — a well-calibrated model is more important than a highly
accurate one.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import label_binarize

logger = logging.getLogger(__name__)


def evaluate_model(
    pipeline: Any,
    X: pd.DataFrame,
    y: pd.Series,
    model_name: str = "model",
) -> dict[str, Any]:
    """
    Compute all evaluation metrics for *pipeline* on (X, y).

    Parameters
    ----------
    pipeline : fitted sklearn Pipeline or CalibratedClassifierCV
    X : pd.DataFrame
    y : pd.Series
        True labels (0, 1, 2).
    model_name : str

    Returns
    -------
    dict  with keys: model, accuracy, log_loss, brier_score,
                     f1_macro, precision_weighted, recall_weighted.
    """
    y_pred = pipeline.predict(X)
    y_proba = pipeline.predict_proba(X)
    y_onehot = label_binarize(y, classes=[0, 1, 2])

    # Multiclass Brier Score: mean of sum of squared probability errors per sample
    brier = float(np.mean(np.sum((y_proba - y_onehot) ** 2, axis=1)))

    metrics = {
        "model": model_name,
        "accuracy": round(accuracy_score(y, y_pred), 4),
        "log_loss": round(log_loss(y, y_proba), 4),
        "brier_score": round(brier, 4),
        "f1_macro": round(f1_score(y, y_pred, average="macro"), 4),
        "precision_weighted": round(
            precision_score(y, y_pred, average="weighted", zero_division=0), 4
        ),
        "recall_weighted": round(
            recall_score(y, y_pred, average="weighted", zero_division=0), 4
        ),
    }

    logger.info(
        "%-28s  acc=%.3f  ll=%.3f  brier=%.3f  f1=%.3f",
        model_name,
        metrics["accuracy"],
        metrics["log_loss"],
        metrics["brier_score"],
        metrics["f1_macro"],
    )
    return metrics


def compare_models(results: list[dict]) -> pd.DataFrame:
    """
    Format a list of metric dicts into a sorted comparison DataFrame.

    Sorted by log_loss ascending (lower = better).
    """
    return pd.DataFrame(results).set_index("model").sort_values("log_loss")


def get_confusion_matrix(
    pipeline: Any, X: pd.DataFrame, y: pd.Series
) -> pd.DataFrame:
    """
    Return a labelled confusion matrix as a DataFrame.

    Rows = actual outcome, Columns = predicted outcome.
    """
    y_pred = pipeline.predict(X)
    labels = ["away_win", "draw", "home_win"]
    cm = confusion_matrix(y, y_pred, labels=[0, 1, 2])
    return pd.DataFrame(
        cm,
        index=[f"actual_{l}" for l in labels],
        columns=[f"pred_{l}" for l in labels],
    )


def print_evaluation_report(
    results: list[dict],
    split_name: str = "validation",
) -> None:
    """Print a formatted evaluation table to stdout."""
    df = compare_models(results)
    sep = "=" * 72
    print(f"\n{sep}\n  MODEL COMPARISON — {split_name.upper()} SET\n{sep}")
    print(df.to_string())
    best = df.index[0]
    print(f"\n  Best model by log_loss: {best}")
    print(sep)
