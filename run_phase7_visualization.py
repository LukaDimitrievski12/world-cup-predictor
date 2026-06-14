"""
Phase 7 runner — Results Visualisation.

Generates all final output plots from the model and simulation results.
Run this after Phase 4 (models) and Phase 6 (simulation) are complete.

Usage
-----
    python run_phase7_visualization.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_engineering.builder import get_feature_columns, load_features
from src.models.train import load_model
from src.simulation.wc2026_config import WC2026_GROUPS
from src.visualization.plots import (
    plot_advancement_heatmap,
    plot_elo_rankings,
    plot_feature_importance,
    plot_group_strength,
    plot_model_comparison,
    plot_win_probabilities,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUT = PROJECT_ROOT / "results" / "phase7"
SIM_DIR = PROJECT_ROOT / "results" / "simulation"
MODELS_DIR = PROJECT_ROOT / "results" / "models"
PROC_DIR = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # ── Load simulation results ───────────────────────────────────────────
    sim_path = SIM_DIR / "probabilities.csv"
    if not sim_path.exists():
        logger.error("Simulation results not found at '%s'.  Run Phase 6 first.", sim_path)
        sys.exit(1)
    results = pd.read_csv(sim_path)
    logger.info("Loaded simulation results: %d teams.", len(results))

    # ── Load team profiles ────────────────────────────────────────────────
    profiles_path = PROC_DIR / "team_profiles.csv"
    if profiles_path.exists():
        profiles = pd.read_csv(profiles_path)
    else:
        logger.warning("Team profiles not found — skipping Elo/group plots.")
        profiles = None

    # ── Load model & features ─────────────────────────────────────────────
    model = None
    feat_cols = []
    try:
        model = load_model("best_model")
        df = load_features()
        has_rankings = "home_rank" in df.columns
        feat_cols = get_feature_columns(df, include_rankings=has_rankings)
    except FileNotFoundError as exc:
        logger.warning("%s — feature importance plot will be skipped.", exc)

    # ── Load metrics ──────────────────────────────────────────────────────
    metrics_path = MODELS_DIR / "metrics.csv"
    metrics_df = pd.read_csv(metrics_path, index_col=0) if metrics_path.exists() else None

    # ── Generate plots ────────────────────────────────────────────────────
    logger.info("Generating Phase 7 visualisations …")

    plot_win_probabilities(
        results,
        top_n=20,
        save_path=str(OUT / "01_win_probabilities.png"),
    )
    logger.info("  1/6  Win probabilities chart saved.")

    plot_advancement_heatmap(
        results,
        top_n=32,
        save_path=str(OUT / "02_advancement_heatmap.png"),
    )
    logger.info("  2/6  Advancement heatmap saved.")

    if profiles is not None:
        plot_elo_rankings(
            profiles,
            top_n=30,
            save_path=str(OUT / "03_elo_rankings.png"),
        )
        logger.info("  3/6  Elo rankings chart saved.")

        plot_group_strength(
            profiles,
            WC2026_GROUPS,
            save_path=str(OUT / "04_group_strength.png"),
        )
        logger.info("  4/6  Group strength chart saved.")
    else:
        logger.info("  3–4/6  Skipped (no team profiles).")

    if model is not None and feat_cols:
        plot_feature_importance(
            model,
            feat_cols,
            top_n=20,
            save_path=str(OUT / "05_feature_importance.png"),
        )
        logger.info("  5/6  Feature importance chart saved.")
    else:
        logger.info("  5/6  Skipped (no model).")

    if metrics_df is not None:
        plot_model_comparison(
            metrics_df,
            save_path=str(OUT / "06_model_comparison.png"),
        )
        logger.info("  6/6  Model comparison table saved.")
    else:
        logger.info("  6/6  Skipped (no metrics file).")

    logger.info("Phase 7 complete.  All plots saved to %s/", OUT)


if __name__ == "__main__":
    main()
