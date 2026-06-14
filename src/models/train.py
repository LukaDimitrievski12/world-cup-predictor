"""
Model training pipelines for the World Cup Predictor.

Three models are trained on an identical sklearn Pipeline so that
preprocessing never touches validation or test data (no leakage),
and the full pipeline (imputer + scaler + model) can be saved as a
single artefact for deployment.

Model choice rationale
----------------------
Logistic Regression  — interpretable baseline; coefficients reveal
    direction of each feature's effect (positive elo_diff → more
    likely home win); sensitive to scale so StandardScaler is critical.

Random Forest        — handles non-linear interactions (e.g. Elo only
    matters a lot when it's very large); invariant to scale; gives
    Gini-based feature importance.

XGBoost              — consistently strongest on tabular data; handles
    residual NaN values (ranking features for pre-1993 matches) that
    slip through the imputer via its own internal missing-value logic;
    SHAP values give the best feature attribution in Phase 7.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = _PROJECT_ROOT / "results" / "models"


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------


def get_model_configs() -> dict[str, dict]:
    """
    Return {model_name: {"description": str, "pipeline": Pipeline}}.

    All pipelines share the same preprocessing prefix so comparison
    is fair.  Scaling is included even for tree models — it has no
    effect on their predictions but keeps the pipeline identical,
    which simplifies the calibration and deployment code.
    """
    return {
        "logistic_regression": {
            "description": "Logistic Regression (L2, multinomial)",
            "pipeline": Pipeline([
                ("imputer", SimpleImputer(strategy="mean")),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(
                    C=1.0,
                    max_iter=2000,
                    solver="lbfgs",
                    random_state=42,
                )),
            ]),
        },
        "random_forest": {
            "description": "Random Forest (300 trees)",
            "pipeline": Pipeline([
                ("imputer", SimpleImputer(strategy="mean")),
                ("scaler", StandardScaler()),
                ("model", RandomForestClassifier(
                    n_estimators=300,
                    max_depth=10,
                    min_samples_leaf=5,
                    n_jobs=-1,
                    random_state=42,
                )),
            ]),
        },
        "xgboost": {
            "description": "XGBoost (gradient boosted trees)",
            "pipeline": Pipeline([
                ("imputer", SimpleImputer(strategy="mean")),
                ("scaler", StandardScaler()),
                ("model", XGBClassifier(
                    n_estimators=300,
                    max_depth=5,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    eval_metric="mlogloss",
                    verbosity=0,
                    random_state=42,
                    n_jobs=-1,
                )),
            ]),
        },
    }


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_all_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    sample_weight: Optional[pd.Series] = None,
) -> dict[str, Pipeline]:
    """
    Fit all model pipelines on (X_train, y_train).

    Parameters
    ----------
    X_train : pd.DataFrame
        Feature matrix — training split only.
    y_train : pd.Series
        Outcome labels: 0 = away win, 1 = draw, 2 = home win.
    sample_weight : pd.Series, optional
        Per-sample importance weights.  Passed to the final Pipeline
        step via ``model__sample_weight`` so the imputer and scaler
        are not affected.

    Returns
    -------
    dict[str, Pipeline]
        Fitted pipelines keyed by model name.
    """
    configs = get_model_configs()
    trained: dict[str, Pipeline] = {}

    for name, cfg in configs.items():
        logger.info("Training %s …", cfg["description"])
        pipeline = cfg["pipeline"]
        fit_params: dict = {}
        if sample_weight is not None:
            fit_params["model__sample_weight"] = sample_weight.values

        pipeline.fit(X_train, y_train, **fit_params)
        trained[name] = pipeline
        logger.info("  %s fitted on %d samples.", name, len(X_train))

    return trained


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_model(pipeline: object, name: str) -> Path:
    """Persist *pipeline* to ``results/models/<name>.joblib``."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / f"{name}.joblib"
    joblib.dump(pipeline, path)
    logger.info("Saved → '%s'.", path)
    return path


def load_model(name: str = "best_model") -> object:
    """Load a previously saved model by file stem."""
    path = MODELS_DIR / f"{name}.joblib"
    if not path.exists():
        raise FileNotFoundError(
            f"Model not found at '{path}'.\nRun: python run_phase4_models.py"
        )
    logger.info("Loaded model from '%s'.", path)
    return joblib.load(path)
