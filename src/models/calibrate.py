"""
Probability calibration for match outcome predictions.

Why calibration matters here more than in most ML projects
----------------------------------------------------------
In a standard classification task you care about rank order (which
class is most likely?).  In a Monte Carlo tournament simulation you
need the *absolute probability values* to be correct.  If our model
says 0.70 for home win but the true rate at that confidence level is
only 0.55, we will systematically over-seed strong teams through the
bracket — small errors compound across 5 knockout rounds into large
probability distortions.

Platt scaling (sigmoid calibration)
    Fits a logistic regression on the model's raw output scores.
    Works well when calibration error is roughly sigmoid-shaped and
    training data is moderate in size (~1 000–10 000 samples).

Isotonic regression
    Non-parametric: fits a monotone step function to the calibration
    data.  More flexible than Platt scaling but can overfit with small
    validation sets.  Preferred when validation set > 5 000 samples.

We use cv='prefit' because the model is already fitted on the training
set; we only apply calibration on the held-out validation set, which
the model has never seen.  Using the training set for calibration would
defeat the purpose.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import CalibrationDisplay
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression as _PlattScaling

logger = logging.getLogger(__name__)


class _ManualCalibrated:
    """
    Calibrates a pre-fitted pipeline on held-out validation data.

    Replaces cv='prefit' in CalibratedClassifierCV, which was removed
    in scikit-learn 1.6.  One isotonic/sigmoid calibrator is fitted per
    class; outputs are renormalized to sum to 1.0 row-wise.
    """

    def __init__(self, pipeline: Any, method: str = "isotonic") -> None:
        self.pipeline = pipeline
        self.method = method
        self._calibrators: list = []
        self.classes_ = np.array([0, 1, 2])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "_ManualCalibrated":
        raw = self.pipeline.predict_proba(X)
        y_arr = np.asarray(y)
        self._calibrators = []
        for k in range(raw.shape[1]):
            y_k = (y_arr == k).astype(float)
            if self.method == "isotonic":
                cal: Any = IsotonicRegression(out_of_bounds="clip")
                cal.fit(raw[:, k], y_k)
            else:
                cal = _PlattScaling(C=1.0, max_iter=1000)
                cal.fit(raw[:, k].reshape(-1, 1), y_k)
            self._calibrators.append(cal)
        logger.info(
            "Calibration (%s) fitted on %d validation samples.", self.method, len(y)
        )
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raw = self.pipeline.predict_proba(X)
        cols = []
        for k, cal in enumerate(self._calibrators):
            if self.method == "isotonic":
                cols.append(cal.predict(raw[:, k]))
            else:
                cols.append(cal.predict_proba(raw[:, k].reshape(-1, 1))[:, 1])
        proba = np.column_stack(cols).clip(1e-7, 1.0)
        return proba / proba.sum(axis=1, keepdims=True)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


def calibrate_pipeline(
    pipeline: Any,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    method: Literal["sigmoid", "isotonic"] = "isotonic",
) -> _ManualCalibrated:
    """
    Wrap *pipeline* in a calibrated classifier fitted on validation data.

    Parameters
    ----------
    pipeline : fitted sklearn Pipeline
    X_val, y_val : pd.DataFrame, pd.Series
        Held-out validation split (not used during model training).
    method : "sigmoid" or "isotonic"
        Calibration method.  Isotonic is preferred for larger datasets.

    Returns
    -------
    _ManualCalibrated
        The original pipeline wrapped in calibration.
        Call .predict_proba() to get calibrated probabilities.
    """
    return _ManualCalibrated(pipeline, method=method).fit(X_val, y_val)


def plot_calibration_curves(
    pipelines: dict[str, Any],
    X_val: pd.DataFrame,
    y_val: pd.Series,
    n_bins: int = 10,
    save_path: str | None = None,
) -> None:
    """
    Plot reliability diagrams for all models on the HOME WIN class.

    A perfectly calibrated model lies on the diagonal.
    Points above the diagonal = under-confident (model says 0.5 but
    actual win rate is 0.65).  Points below = over-confident.

    We focus on the HOME WIN class (label=2) because it has the
    highest base rate (~44%) and is the most policy-relevant outcome.

    Parameters
    ----------
    pipelines : dict[str, estimator]
    X_val, y_val : validation data
    n_bins : int
    save_path : str, optional
    """
    HOME_WIN = 2
    y_binary = (y_val == HOME_WIN).astype(int)

    colours = ["#2196F3", "#4CAF50", "#F44336", "#FF9800"]
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.plot([0, 1], [0, 1], "k--", linewidth=1.3, label="Perfect calibration", zorder=5)

    for (name, pipeline), colour in zip(pipelines.items(), colours):
        y_proba = pipeline.predict_proba(X_val)[:, HOME_WIN]
        CalibrationDisplay.from_predictions(
            y_binary, y_proba, n_bins=n_bins, ax=ax, name=name, color=colour
        )

    ax.set_title(
        "Calibration Curves — Home Win Probability",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel("Mean Predicted Probability")
    ax.set_ylabel("Fraction of Positives (Actual Home Win Rate)")
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Calibration plot → '%s'.", save_path)
    else:
        plt.show()
    plt.close(fig)


def expected_calibration_error(
    pipeline: Any,
    X: pd.DataFrame,
    y: pd.Series,
    n_bins: int = 10,
    outcome_class: int = 2,
) -> float:
    """
    Compute Expected Calibration Error (ECE) for one outcome class.

    ECE = weighted average of |predicted probability − actual fraction|
    across probability bins.  Lower is better; 0 = perfect.

    Parameters
    ----------
    pipeline : fitted estimator
    X, y : data
    n_bins : int
    outcome_class : int
        Which class to evaluate (0=away, 1=draw, 2=home_win).

    Returns
    -------
    float
    """
    y_proba = pipeline.predict_proba(X)[:, outcome_class]
    y_binary = (y == outcome_class).astype(float)

    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(y_binary)

    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (y_proba >= lo) & (y_proba < hi)
        if mask.sum() == 0:
            continue
        frac_positive = y_binary[mask].mean()
        mean_pred = y_proba[mask].mean()
        ece += mask.sum() / n * abs(frac_positive - mean_pred)

    return round(float(ece), 5)
