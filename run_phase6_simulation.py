"""
Phase 6 runner — Monte Carlo Tournament Simulation.

Runs 10 000 complete World Cup 2026 simulations and outputs
per-team stage advancement probabilities.

Usage
-----
    python run_phase6_simulation.py
    python run_phase6_simulation.py --n-sims 50000
    python run_phase6_simulation.py --n-sims 1000   # fast test run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_engineering.builder import load_features, get_feature_columns
from src.models.train import load_model
from src.simulation.monte_carlo import build_team_profiles, run_monte_carlo
from src.simulation.wc2026_config import WC2026_GROUPS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SIM_DIR = PROJECT_ROOT / "results" / "simulation"
PROC_DIR = PROJECT_ROOT / "data" / "processed"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 6: Monte Carlo Simulation")
    p.add_argument("--n-sims", type=int, default=10_000, metavar="N",
                   help="Number of full tournament simulations (default: 10 000).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--model", default="best_model",
                   help="Model file stem to load (default: best_model).")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    SIM_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Load model and features ────────────────────────────────────────
    logger.info("Loading model '%s' …", args.model)
    model = load_model(args.model)

    logger.info("Loading feature matrix …")
    df = load_features()

    has_rankings = "home_rank" in df.columns
    feature_cols = get_feature_columns(df, include_rankings=has_rankings)
    logger.info("Using %d features.", len(feature_cols))

    # ── 2. Build team profiles ────────────────────────────────────────────
    logger.info("Building team profiles …")
    profiles = build_team_profiles(df)

    # Persist team profiles for the dashboard
    profile_rows = []
    for t, p in profiles.items():
        profile_rows.append({
            "team": t, "elo": p.elo,
            "last5_win": p.last5_win, "last5_gf": p.last5_gf, "last5_ga": p.last5_ga,
            "last10_win": p.last10_win, "last10_gf": p.last10_gf, "last10_ga": p.last10_ga,
            "rank": p.rank, "rank_points": p.rank_points,
        })
    pd.DataFrame(profile_rows).to_csv(PROC_DIR / "team_profiles.csv", index=False)
    logger.info("Team profiles saved → data/processed/team_profiles.csv")

    # Check for WC teams missing from profiles
    all_wc_teams = [t for g in WC2026_GROUPS.values() for t in g]
    missing = [t for t in all_wc_teams if t not in profiles]
    if missing:
        logger.warning(
            "%d WC teams have no historical data → using default Elo 1350: %s",
            len(missing),
            missing,
        )

    # ── 3. Run Monte Carlo simulation ─────────────────────────────────────
    logger.info("Running %d simulations …", args.n_sims)
    results = run_monte_carlo(
        model=model,
        profiles=profiles,
        feature_cols=feature_cols,
        groups=WC2026_GROUPS,
        n_simulations=args.n_sims,
        seed=args.seed,
    )

    # ── 4. Save results ───────────────────────────────────────────────────
    out_path = SIM_DIR / "probabilities.csv"
    results.to_csv(out_path, index=False)
    logger.info("Probabilities saved → '%s'.", out_path)

    # Also save feature_cols list for the dashboard
    (PROJECT_ROOT / "results" / "models" / "feature_columns.txt").write_text(
        "\n".join(feature_cols)
    )

    # ── 5. Print top results ──────────────────────────────────────────────
    sep = "=" * 72
    print(f"\n{sep}")
    print(f"  WORLD CUP 2026 — MONTE CARLO RESULTS  ({args.n_sims:,} simulations)")
    print(sep)
    pd.set_option("display.float_format", lambda x: f"{x:.1%}")
    pd.set_option("display.max_rows", 48)
    print(results.to_string(index=False))
    pd.reset_option("display.float_format")
    print(f"\nPhase 6 complete.  Results saved to {SIM_DIR}/")


if __name__ == "__main__":
    main()
