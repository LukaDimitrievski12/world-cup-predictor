"""
Phase 4 runner — Model Training & Evaluation (+ Phase 5 Calibration).

Pipeline
--------
1. Load feature matrix from data/processed/features.csv.
2. Filter to the training window (default: post-1980).
3. Apply temporal train / validation / test split.
4. Train Logistic Regression, Random Forest, XGBoost.
5. Evaluate all three on the validation set.
6. Calibrate each model on the validation set.
7. Re-evaluate calibrated models; pick the best by log_loss.
8. Save all models + the best calibrated model as best_model.joblib.
9. Save metrics CSV + confusion matrices + calibration plot.

Usage
-----
    python run_phase4_models.py
    python run_phase4_models.py --train-cutoff 1993 --val-start 2019-01-01
    python run_phase4_models.py --no-sample-weight
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # non-interactive backend for saving plots

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing.preprocessor import temporal_split
from src.feature_engineering.builder import load_features, get_feature_columns
from src.models.calibrate import calibrate_pipeline, plot_calibration_curves, expected_calibration_error
from src.models.evaluate import compare_models, evaluate_model, get_confusion_matrix, print_evaluation_report
from src.models.train import save_model, train_all_models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "results" / "phase4"
MODELS_DIR = PROJECT_ROOT / "results" / "models"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 4 + 5: Model Training & Calibration")
    p.add_argument("--train-cutoff", type=int, default=1980, metavar="YEAR")
    p.add_argument("--val-start", default="2018-01-01", metavar="DATE")
    p.add_argument("--test-start", default="2022-01-01", metavar="DATE")
    p.add_argument("--no-sample-weight", action="store_true",
                   help="Train without tournament importance weights.")
    p.add_argument("--calibration-method", default="isotonic",
                   choices=["sigmoid", "isotonic"])
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Load & filter feature matrix ──────────────────────────────────
    logger.info("Loading feature matrix …")
    df = load_features()
    df = df[df["date"].dt.year >= args.train_cutoff].copy()
    logger.info("Dataset after year filter: %d rows.", len(df))

    # ── 2. Temporal split ─────────────────────────────────────────────────
    train, val, test = temporal_split(df, args.val_start, args.test_start)

    # ── 3. Assemble X and y ───────────────────────────────────────────────
    has_rankings = "home_rank" in df.columns
    feat_cols = get_feature_columns(df, include_rankings=has_rankings)
    logger.info("Feature columns (%d): %s", len(feat_cols), feat_cols)

    X_train, y_train = train[feat_cols], train["outcome"]
    X_val,   y_val   = val[feat_cols],   val["outcome"]
    X_test,  y_test  = test[feat_cols],  test["outcome"]

    sample_weight = None
    if not args.no_sample_weight and "tournament_weight" in train.columns:
        sample_weight = train["tournament_weight"]
        logger.info("Using tournament importance weights for training.")

    # ── 4. Train ──────────────────────────────────────────────────────────
    logger.info("Training models …")
    trained = train_all_models(X_train, y_train, sample_weight=sample_weight)

    # Save each raw model
    for name, pipeline in trained.items():
        save_model(pipeline, name)

    # ── 5. Evaluate on validation set ─────────────────────────────────────
    logger.info("Evaluating on validation set …")
    val_results = [
        evaluate_model(pipe, X_val, y_val, model_name=name)
        for name, pipe in trained.items()
    ]
    print_evaluation_report(val_results, split_name="validation")

    # ── 6. Calibrate all models ───────────────────────────────────────────
    logger.info("Calibrating models (%s) …", args.calibration_method)
    calibrated: dict[str, object] = {}
    cal_results: list[dict] = []
    for name, pipeline in trained.items():
        cal = calibrate_pipeline(pipeline, X_val, y_val, method=args.calibration_method)
        calibrated[f"{name}_calibrated"] = cal
        cal_results.append(
            evaluate_model(cal, X_val, y_val, model_name=f"{name}_cal")
        )

    print_evaluation_report(cal_results, split_name="validation (calibrated)")

    # ── 7. Select best calibrated model ───────────────────────────────────
    best_cal_name = min(cal_results, key=lambda r: r["log_loss"])["model"]
    raw_name = best_cal_name.replace("_cal", "")
    best_pipeline = calibrated[f"{raw_name}_calibrated"]
    save_model(best_pipeline, "best_model")
    logger.info("Best model: %s → saved as best_model.joblib.", best_cal_name)

    # ── 8. Final evaluation on held-out test set ──────────────────────────
    logger.info("Final evaluation on TEST set (held out until now) …")
    test_result = evaluate_model(best_pipeline, X_test, y_test, model_name=best_cal_name)
    sep = "=" * 64
    print(f"\n{sep}\n  FINAL TEST SET METRICS\n{sep}")
    for k, v in test_result.items():
        if k != "model":
            print(f"  {k:<25} {v}")

    # ── 9. Save metrics and confusion matrix ──────────────────────────────
    all_results = val_results + cal_results + [test_result]
    metrics_df = compare_models([r for r in all_results])
    metrics_path = MODELS_DIR / "metrics.csv"
    metrics_df.to_csv(metrics_path)
    logger.info("Metrics saved → '%s'.", metrics_path)

    cm = get_confusion_matrix(best_pipeline, X_val, y_val)
    print(f"\n  Confusion Matrix (validation, best model):\n{cm.to_string()}")
    cm.to_csv(MODELS_DIR / "confusion_matrix.csv")

    # ── 10. Calibration curves plot ───────────────────────────────────────
    all_pipelines = {**trained, **calibrated}
    plot_calibration_curves(
        all_pipelines,
        X_val,
        y_val,
        save_path=str(OUTPUT_DIR / "calibration_curves.png"),
    )

    # ECE for best model
    ece = expected_calibration_error(best_pipeline, X_val, y_val)
    print(f"\n  ECE (home win, best model): {ece:.5f}")

    # ── 11. Feature column list for downstream phases ─────────────────────
    feat_path = MODELS_DIR / "feature_columns.txt"
    feat_path.write_text("\n".join(feat_cols))
    logger.info("Feature columns saved → '%s'.", feat_path)

    print(f"\nPhase 4 + 5 complete.  Models saved to {MODELS_DIR}/")


if __name__ == "__main__":
    main()
