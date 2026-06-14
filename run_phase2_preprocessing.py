"""
Phase 2 runner — Data Cleaning & Preprocessing.

Loads the raw match results, runs the full preprocessing pipeline,
saves the cleaned dataset, and prints a split quality report.

Usage
-----
    python run_phase2_preprocessing.py
    python run_phase2_preprocessing.py --year-cutoff 1990
    python run_phase2_preprocessing.py --drop-defunct
    python run_phase2_preprocessing.py --year-cutoff 1990 --val-start 2019-01-01
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing.loader import load_match_results
from src.data_processing.preprocessor import (
    describe_splits,
    get_outcome_distribution,
    preprocess_results,
    save_processed,
    temporal_split,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 2: Data Cleaning & Preprocessing")
    p.add_argument(
        "--year-cutoff",
        type=int,
        default=1980,
        metavar="YEAR",
        help="Drop matches before this year (default: 1980).",
    )
    p.add_argument(
        "--drop-defunct",
        action="store_true",
        help="Exclude matches involving defunct nations (Soviet Union etc.).",
    )
    p.add_argument(
        "--val-start",
        default="2018-01-01",
        metavar="DATE",
        help="Start of validation window, ISO format (default: 2018-01-01).",
    )
    p.add_argument(
        "--test-start",
        default="2022-01-01",
        metavar="DATE",
        help="Start of test window, ISO format (default: 2022-01-01).",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    # ── 1. Load ───────────────────────────────────────────────────────────
    logger.info("Loading raw match results …")
    raw = load_match_results()
    logger.info("Raw dataset: %d rows.", len(raw))

    # ── 2. Preprocess ─────────────────────────────────────────────────────
    logger.info("Running preprocessing pipeline …")
    clean = preprocess_results(
        raw,
        year_cutoff=args.year_cutoff,
        drop_defunct=args.drop_defunct,
    )

    # ── 3. Outcome distribution (full cleaned set) ────────────────────────
    sep = "=" * 64
    print(f"\n{sep}\n  OUTCOME DISTRIBUTION (full cleaned dataset)\n{sep}")
    print(get_outcome_distribution(clean).to_string())

    # ── 4. Temporal split ─────────────────────────────────────────────────
    logger.info("Creating temporal splits …")
    train, val, test = temporal_split(
        clean,
        val_start=args.val_start,
        test_start=args.test_start,
    )

    # ── 5. Split quality report ───────────────────────────────────────────
    print(f"\n{sep}\n  SPLIT QUALITY REPORT\n{sep}")
    print(describe_splits(train, val, test).to_string())
    print()

    # Warn if home win rate deviates from historical norms
    for name, split in [("train", train), ("validation", val), ("test", test)]:
        if len(split) == 0:
            continue
        hw_pct = (split["outcome"] == 2).mean() * 100
        if hw_pct > 52 or hw_pct < 30:
            logger.warning(
                "%s set home win rate = %.1f%% — outside expected range [30%%–52%%]. "
                "Check date parameters or data integrity.",
                name,
                hw_pct,
            )

    # ── 6. Save ───────────────────────────────────────────────────────────
    out = save_processed(clean)

    print(f"\nCleaned dataset saved → {out}")
    print(f"  Total rows : {len(clean):,}")
    print(f"  Columns    : {list(clean.columns)}")
    print(f"\nPhase 2 complete.  Run Phase 3 to build features.")


if __name__ == "__main__":
    main()
