"""
Phase 1 runner — Data Loading & Exploratory Data Analysis.

Loads raw datasets, prints a structured console report, and saves
all Phase 1 plots to results/phase1/.

Usage
-----
    python run_phase1_eda.py

Dependencies
------------
    pip install -r requirements.txt
    # Then download data:
    python -m src.data_processing.downloader
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make the project root importable without pip-installing the package
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing.loader import load_match_results, load_fifa_rankings, load_shootouts
from src.data_processing.inspector import (
    describe_match_results,
    plot_goals_distribution,
    plot_home_advantage,
    plot_matches_per_year,
    plot_outcomes_over_time,
    plot_score_heatmap,
    plot_top_teams,
    plot_tournament_distribution,
    summarize_dataframe,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "results" / "phase1"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Step 1 — Load datasets
    # ------------------------------------------------------------------
    logger.info("Loading datasets …")
    results = load_match_results()

    # Rankings and shootouts are optional for EDA; skip cleanly if absent
    try:
        rankings = load_fifa_rankings()
    except FileNotFoundError as exc:
        logger.warning("%s", exc)
        rankings = None

    shootouts = load_shootouts()  # returns empty DF if missing — never raises

    # ------------------------------------------------------------------
    # Step 2 — Structural overview
    # ------------------------------------------------------------------
    summarize_dataframe(results, "Match Results")
    if rankings is not None:
        summarize_dataframe(rankings, "FIFA Rankings")
    if not shootouts.empty:
        summarize_dataframe(shootouts, "Penalty Shootouts")

    # ------------------------------------------------------------------
    # Step 3 — High-level statistics
    # ------------------------------------------------------------------
    summary = describe_match_results(results)
    print("\n" + "=" * 64)
    print("  HIGH-LEVEL MATCH STATISTICS")
    print("=" * 64)
    print(summary.T.to_string(header=False))

    # ------------------------------------------------------------------
    # Step 4 — Plots (saved to results/phase1/)
    # ------------------------------------------------------------------
    logger.info("Generating plots → %s", OUTPUT_DIR)

    plot_matches_per_year(
        results,
        save_path=str(OUTPUT_DIR / "01_matches_per_year.png"),
    )
    plot_outcomes_over_time(
        results,
        save_path=str(OUTPUT_DIR / "02_outcomes_over_time.png"),
    )
    plot_goals_distribution(
        results,
        save_path=str(OUTPUT_DIR / "03_goals_distribution.png"),
    )
    plot_home_advantage(
        results,
        save_path=str(OUTPUT_DIR / "04_home_advantage.png"),
    )
    plot_top_teams(
        results,
        metric="wins",
        save_path=str(OUTPUT_DIR / "05_top_teams_wins.png"),
    )
    plot_top_teams(
        results,
        metric="win_rate",
        save_path=str(OUTPUT_DIR / "06_top_teams_win_rate.png"),
    )
    plot_tournament_distribution(
        results,
        save_path=str(OUTPUT_DIR / "07_tournament_distribution.png"),
    )
    plot_score_heatmap(
        results,
        save_path=str(OUTPUT_DIR / "08_score_heatmap.png"),
    )

    logger.info("Phase 1 complete.  %d plots saved to %s/", 8, OUTPUT_DIR)


if __name__ == "__main__":
    main()
