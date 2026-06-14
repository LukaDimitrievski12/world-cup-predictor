"""
Data loading utilities for the World Cup Predictor project.

Handles reading raw CSVs from disk, enforcing expected dtypes,
and raising informative errors when files are missing or malformed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directory constants — resolved relative to this file so the project can
# be opened from any working directory.
# ---------------------------------------------------------------------------
_PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
RAW_DIR: Path = _PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR: Path = _PROJECT_ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# Download URLs (for error messages)
# ---------------------------------------------------------------------------
_RESULTS_URL = (
    "https://www.kaggle.com/datasets/martj42/"
    "international-football-results-from-1872-to-2024"
)
_RANKINGS_URL = "https://www.kaggle.com/datasets/cashncarry/fifaworldranking"


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------


def load_match_results(filepath: Optional[Path] = None) -> pd.DataFrame:
    """
    Load international football match results from CSV.

    Source dataset (Kaggle – Mart Jürisoo):
        ``data/raw/results.csv``

    Expected columns
    ----------------
    date : datetime64
        Match date.
    home_team, away_team : str
        Team names as strings.
    home_score, away_score : Int64 (nullable integer)
        Goals scored; nullable to preserve NaN rows for later inspection.
    tournament : str
        Competition name (e.g. "FIFA World Cup", "Friendly").
    city, country : str
        Venue location.
    neutral : bool
        True when the match was played at a neutral venue.

    Parameters
    ----------
    filepath : Path, optional
        Override the default ``data/raw/results.csv`` path.

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    FileNotFoundError
        If the CSV does not exist at the resolved path.
    ValueError
        If required columns are absent or scores contain invalid values.
    """
    path = filepath or RAW_DIR / "results.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Match results not found at '{path}'.\n"
            f"Download from: {_RESULTS_URL}\n"
            "Or run:  python -m src.data_processing.downloader"
        )

    df = pd.read_csv(
        path,
        parse_dates=["date"],
        dtype={
            "home_team": "string",
            "away_team": "string",
            "tournament": "string",
            "city": "string",
            "country": "string",
        },
    )

    # neutral can arrive as bool or 0/1 int; coerce to Python bool cleanly
    if "neutral" in df.columns:
        df["neutral"] = df["neutral"].astype(bool)

    # Use nullable integer so that rows with missing scores are preserved
    # rather than silently dropped or converted to float.
    for col in ("home_score", "away_score"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    _validate_results(df)
    logger.info("Loaded %d match records from '%s'.", len(df), path.name)
    return df


def load_fifa_rankings(filepath: Optional[Path] = None) -> pd.DataFrame:
    """
    Load FIFA World Rankings from CSV.

    Source dataset (Kaggle – cashncarry):
        ``data/raw/fifa_ranking-2023-07-20.csv``

    The ranking file name varies slightly between dataset versions.
    This loader tries the default name first, then falls back to any
    ``fifa_ranking*.csv`` file found in the raw directory.

    Expected columns (subset kept)
    --------------------------------
    rank_date : datetime64
    country_full : str
    rank : int
    total_points : float

    Parameters
    ----------
    filepath : Path, optional
        Override the default path.

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    FileNotFoundError
        If no FIFA ranking file is found.
    """
    # Try explicit path → default name → glob fallback
    if filepath:
        path = filepath
    else:
        default = RAW_DIR / "fifa_ranking-2023-07-20.csv"
        if default.exists():
            path = default
        else:
            candidates = sorted(RAW_DIR.glob("fifa_ranking*.csv"))
            if not candidates:
                raise FileNotFoundError(
                    f"No FIFA ranking CSV found in '{RAW_DIR}'.\n"
                    f"Download from: {_RANKINGS_URL}\n"
                    "Or run:  python -m src.data_processing.downloader"
                )
            path = candidates[-1]  # latest file by filename sort
            logger.info("Using ranking file '%s' (fallback).", path.name)

    df = pd.read_csv(path, parse_dates=["rank_date"])

    # Standardise the team-name column: datasets use country_full or team
    if "country_full" not in df.columns and "team" in df.columns:
        df = df.rename(columns={"team": "country_full"})

    df["country_full"] = df["country_full"].astype("string")

    # Keep only the columns needed for feature engineering
    keep = [c for c in ("rank_date", "country_full", "rank", "total_points") if c in df.columns]
    df = df[keep].copy()

    logger.info("Loaded %d FIFA ranking records from '%s'.", len(df), path.name)
    return df


def load_shootouts(filepath: Optional[Path] = None) -> pd.DataFrame:
    """
    Load penalty shootout outcomes from CSV.

    Used in Phase 6 to determine knockout-stage tiebreakers.
    Returns an empty DataFrame (not an error) when the file is absent,
    because shootout data is optional for early phases.

    Parameters
    ----------
    filepath : Path, optional
        Override the default ``data/raw/shootouts.csv`` path.

    Returns
    -------
    pd.DataFrame
        Columns: date, home_team, away_team, winner, first_shooter.
        Empty DataFrame if file not found.
    """
    path = filepath or RAW_DIR / "shootouts.csv"

    if not path.exists():
        logger.warning("Shootouts file not found at '%s' — skipping.", path)
        return pd.DataFrame(
            columns=["date", "home_team", "away_team", "winner", "first_shooter"]
        )

    df = pd.read_csv(
        path,
        parse_dates=["date"],
        dtype={
            "home_team": "string",
            "away_team": "string",
            "winner": "string",
            "first_shooter": "string",
        },
    )
    logger.info("Loaded %d shootout records from '%s'.", len(df), path.name)
    return df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_results(df: pd.DataFrame) -> None:
    """Raise if critical columns are missing or scores are logically invalid."""
    required = {"date", "home_team", "away_team", "home_score", "away_score", "tournament"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"results.csv is missing required columns: {sorted(missing)}.\n"
            "Re-download the dataset or check the file path."
        )

    # Scores below zero are data errors, not missing values
    valid_rows = df["home_score"].notna() & df["away_score"].notna()
    if valid_rows.any():
        negative = (df.loc[valid_rows, "home_score"] < 0) | (
            df.loc[valid_rows, "away_score"] < 0
        )
        if negative.any():
            raise ValueError(
                f"Found {negative.sum()} rows with negative scores. "
                "Check data integrity."
            )
