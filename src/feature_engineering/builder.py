"""
Feature matrix builder for the World Cup Predictor project.

Orchestrates the three Phase 3 modules (Elo, form, rankings) into a
single pipeline that transforms cleaned match data into a model-ready
feature matrix.

Why build features on the FULL historical dataset?
--------------------------------------------------
A team's 1982 Elo rating is only meaningful if computed using all
matches since 1872.  Similarly, a team's 5-match form in January 1980
requires November/December 1979 results.  If we filtered to post-1980
BEFORE computing features, early-1980 features would be wrong.

The correct sequence:
  1. Load ALL cleaned matches (year_cutoff=1872 in preprocess_results).
  2. Compute Elo + form on the full dataset.
  3. Merge rankings (available from 1993).
  4. Save the feature matrix for all matches.
  5. In Phase 4, filter to the training window (e.g. post-1980).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .elo import compute_elo_ratings
from .form import compute_form_features, get_feature_names
from .rankings import merge_rankings

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = _PROJECT_ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# Feature column groups (referenced in Phase 4)
# ---------------------------------------------------------------------------

ELO_FEATURES: list[str] = [
    "home_elo_pre",
    "away_elo_pre",
    "elo_diff",
]

MATCH_CONTEXT_FEATURES: list[str] = [
    "is_neutral",
    "tournament_weight",
]

RANKING_FEATURES: list[str] = [
    "home_rank",
    "away_rank",
    "rank_diff",
    "home_rank_points",
    "away_rank_points",
    "rank_points_diff",
]


def build_feature_matrix(
    df: pd.DataFrame,
    rankings: Optional[pd.DataFrame] = None,
    form_windows: tuple[int, ...] = (5, 10),
    elo_kwargs: Optional[dict] = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Run the full Phase 3 feature engineering pipeline.

    Parameters
    ----------
    df : pd.DataFrame
        FULL cleaned match history sorted by date.  Should be the output
        of ``preprocess_results(raw, year_cutoff=1872)`` — no year filter —
        so Elo and form features are accurate for the earliest matches
        in the eventual training window.
    rankings : pd.DataFrame, optional
        Output of ``loader.load_fifa_rankings()``.  When provided, six
        FIFA ranking columns are added.  When absent, ranking features
        are omitted (pre-1993 data will train without them).
    form_windows : tuple[int, ...]
        Rolling window sizes for form features (default: 5 and 10 matches).
    elo_kwargs : dict, optional
        Override any ``compute_elo_ratings`` keyword arguments.
        Example: ``{"use_goal_difference": True, "home_advantage": 80}``.

    Returns
    -------
    df_features : pd.DataFrame
        Full dataset with all engineered columns.  Filter this by date
        in Phase 4 before splitting into train/val/test.
    feature_cols : list[str]
        Ordered list of column names to use as model input features X.
        All other columns are metadata (team names, date, outcome, etc.).
    """
    elo_kwargs = elo_kwargs or {}

    # ── Step 1: Elo ratings ────────────────────────────────────────────────
    logger.info("Step 1/3  Computing Elo ratings …")
    df = compute_elo_ratings(df, **elo_kwargs)

    # ── Step 2: Rolling form features ─────────────────────────────────────
    logger.info("Step 2/3  Computing rolling form features (windows=%s) …", form_windows)
    df = compute_form_features(df, windows=form_windows)

    # ── Step 3: FIFA rankings ──────────────────────────────────────────────
    if rankings is not None:
        logger.info("Step 3/3  Merging FIFA rankings …")
        df = merge_rankings(df, rankings)
    else:
        logger.info("Step 3/3  No rankings provided — skipping.")

    # ── Identify final feature columns ────────────────────────────────────
    feature_cols = get_feature_columns(df, include_rankings=rankings is not None)

    # Fill NaN form features with 0 — teams with no prior history get
    # neutral statistics.  Phase 4 can override this with mean imputation.
    form_feat_names = get_feature_names(form_windows)
    for col in form_feat_names:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)

    logger.info(
        "Feature matrix built: %d rows × %d features.",
        len(df),
        len(feature_cols),
    )
    _log_feature_summary(df, feature_cols)
    return df, feature_cols


def get_feature_columns(
    df: pd.DataFrame,
    include_rankings: bool = True,
) -> list[str]:
    """
    Return the ordered list of feature column names present in *df*.

    Parameters
    ----------
    df : pd.DataFrame
        Output of ``build_feature_matrix``.
    include_rankings : bool
        Whether to include FIFA ranking columns (they may be absent if
        rankings were not provided or the match predates 1993).

    Returns
    -------
    list[str]
    """
    candidates = (
        ELO_FEATURES
        + MATCH_CONTEXT_FEATURES
        + (RANKING_FEATURES if include_rankings else [])
        + [c for c in df.columns if c.startswith(("home_last", "away_last"))]
    )
    # Keep only columns that actually exist and have non-null data
    return [c for c in candidates if c in df.columns]


def save_features(df: pd.DataFrame, filename: str = "features.csv") -> Path:
    """
    Save the feature matrix to ``data/processed/<filename>``.

    Parameters
    ----------
    df : pd.DataFrame
    filename : str

    Returns
    -------
    Path
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / filename
    df.to_csv(path, index=False)
    logger.info("Saved feature matrix → '%s'  (%d rows, %d cols).", path, *df.shape)
    return path


def load_features(filename: str = "features.csv") -> pd.DataFrame:
    """
    Load the feature matrix saved by ``save_features``.

    Parameters
    ----------
    filename : str

    Returns
    -------
    pd.DataFrame
    """
    path = PROCESSED_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Feature matrix not found at '{path}'.\n"
            "Run: python run_phase3_features.py"
        )
    df = pd.read_csv(path, parse_dates=["date"])
    logger.info("Loaded feature matrix from '%s'  (%d rows).", path, len(df))
    return df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _log_feature_summary(df: pd.DataFrame, feature_cols: list[str]) -> None:
    """Print null counts and value ranges for all feature columns."""
    info = pd.DataFrame(
        {
            "null_%": (df[feature_cols].isna().mean() * 100).round(1),
            "mean": df[feature_cols].mean().round(3),
            "std": df[feature_cols].std().round(3),
            "min": df[feature_cols].min().round(3),
            "max": df[feature_cols].max().round(3),
        }
    )
    logger.info("\nFeature summary:\n%s", info.to_string())
