"""
Phase 3 runner — Feature Engineering.

Builds the full model-ready feature matrix and saves it to
data/processed/features.csv.

Key design choice: features are computed on ALL historical matches
(year_cutoff=1872 in preprocess_results) before filtering to the
training window.  This ensures Elo ratings and rolling form statistics
are accurate even for matches at the start of the training window —
a team's 1982 Elo is only meaningful if computed using all pre-1982
matches.

Usage
-----
    python run_phase3_features.py
    python run_phase3_features.py --train-cutoff 1990
    python run_phase3_features.py --elo-gd            # enable goal-diff multiplier
    python run_phase3_features.py --no-rankings       # skip ranking features
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing.loader import load_match_results, load_fifa_rankings
from src.data_processing.preprocessor import preprocess_results
from src.feature_engineering.builder import (
    build_feature_matrix,
    get_feature_columns,
    save_features,
)
from src.feature_engineering.elo import get_current_ratings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "results" / "phase3"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 3: Feature Engineering")
    p.add_argument(
        "--train-cutoff",
        type=int,
        default=1980,
        metavar="YEAR",
        help=(
            "Keep only matches from this year onwards in the saved "
            "feature matrix (default: 1980).  Features are still "
            "computed on ALL historical data for accuracy."
        ),
    )
    p.add_argument(
        "--no-rankings",
        action="store_true",
        help="Skip FIFA ranking features (useful if rankings file is absent).",
    )
    p.add_argument(
        "--elo-gd",
        action="store_true",
        help="Enable goal-difference multiplier in Elo computation.",
    )
    p.add_argument(
        "--plot-elo",
        action="store_true",
        help="Save Elo rating trajectory plots for top teams.",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Load full raw data ─────────────────────────────────────────────
    logger.info("Loading raw match results …")
    raw = load_match_results()
    logger.info("Raw records: %d", len(raw))

    # ── 2. Preprocess — NO year cutoff so Elo/form see full history ───────
    logger.info("Preprocessing (full history, year_cutoff=1872) …")
    full_df = preprocess_results(raw, year_cutoff=1872, drop_defunct=False)
    logger.info("Full preprocessed dataset: %d matches.", len(full_df))

    # ── 3. Load FIFA rankings (optional) ─────────────────────────────────
    rankings = None
    if not args.no_rankings:
        try:
            rankings = load_fifa_rankings()
        except FileNotFoundError as exc:
            logger.warning("%s\nContinuing without ranking features.", exc)

    # ── 4. Build feature matrix on full dataset ───────────────────────────
    elo_kwargs = {"use_goal_difference": args.elo_gd}
    features_full, feat_cols = build_feature_matrix(
        full_df,
        rankings=rankings,
        form_windows=(5, 10),
        elo_kwargs=elo_kwargs,
    )

    # ── 5. Optional: visualise Elo rating trajectories ───────────────────
    if args.plot_elo:
        _plot_elo_trajectories(features_full, OUTPUT_DIR)

    # ── 6. Filter to training window and save ────────────────────────────
    features_training = features_full[
        features_full["date"].dt.year >= args.train_cutoff
    ].copy()
    logger.info(
        "Filtered to post-%d: %d → %d matches.",
        args.train_cutoff,
        len(features_full),
        len(features_training),
    )
    out_path = save_features(features_training)

    # ── 7. Summary report ────────────────────────────────────────────────
    sep = "=" * 64
    print(f"\n{sep}\n  TOP 20 TEAMS BY CURRENT ELO RATING\n{sep}")
    current_elos = get_current_ratings(features_full)
    print(current_elos.head(20).to_string())

    print(f"\n{sep}\n  FEATURE COLUMNS ({len(feat_cols)} features)\n{sep}")
    for i, col in enumerate(feat_cols, 1):
        print(f"  {i:>2}. {col}")

    print(f"\n{sep}\n  FEATURE NULL RATES (training window)\n{sep}")
    null_rates = (features_training[feat_cols].isna().mean() * 100).round(2)
    nonzero_nulls = null_rates[null_rates > 0]
    if nonzero_nulls.empty:
        print("  All features fully populated — no nulls.")
    else:
        print(nonzero_nulls.to_string())
        print(
            "\n  Note: ranking features are NaN for pre-1993 matches.\n"
            "  Phase 4 will handle these via an imputation step."
        )

    print(f"\nFeature matrix saved → {out_path}")
    print(f"Phase 3 complete.  Ready for Phase 4 (Model Training).")


def _plot_elo_trajectories(
    df: pd.DataFrame,
    output_dir: Path,
    teams: tuple[str, ...] = (
        "Brazil", "Germany", "France", "Argentina",
        "Spain", "Italy", "England", "Netherlands",
    ),
) -> None:
    """
    Plot how Elo ratings evolve over time for a selection of top teams.

    This is not a feature used in the model — it's a diagnostic that
    confirms Elo is behaving as expected (e.g. Germany's rating dropping
    sharply after the 2018 World Cup group-stage exit).
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    for team in teams:
        home_hist = df[df["home_team"] == team][["date", "home_elo_pre"]].rename(
            columns={"home_elo_pre": "elo"}
        )
        away_hist = df[df["away_team"] == team][["date", "away_elo_pre"]].rename(
            columns={"away_elo_pre": "elo"}
        )
        hist = pd.concat([home_hist, away_hist]).sort_values("date")
        if not hist.empty:
            ax.plot(hist["date"], hist["elo"], label=team, linewidth=1.5, alpha=0.85)

    ax.set_title("Elo Rating Trajectories — Top Teams", fontsize=13, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Elo Rating")
    ax.legend(ncol=2, fontsize=9)
    ax.grid(alpha=0.3)
    ax.axhline(1500, color="black", linestyle=":", linewidth=0.8, label="Global average")
    fig.tight_layout()

    save_path = output_dir / "elo_trajectories.png"
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Elo trajectory plot saved → %s", save_path)


if __name__ == "__main__":
    main()
