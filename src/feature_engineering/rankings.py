"""
FIFA ranking feature engineering for the World Cup Predictor project.

For each match we look up the most recent FIFA ranking for both teams
prior to the match date.  This gives us an official strength signal
that is independent of our self-computed Elo ratings and can serve as
a useful cross-validation feature or as a sanity check.

Implementation: pd.merge_asof
------------------------------
merge_asof performs an ordered, nearest-key merge — exactly what we
need to find "the last ranking before date X for team Y".  It is O(n)
after sorting, far more efficient than a per-row lookup loop.

Limitations
-----------
- FIFA rankings began in August 1993.  Pre-1993 matches will have NaN
  ranking features.
- Rankings are released roughly monthly; gaps between release dates
  mean a match may use a ranking that is several weeks old.
- Ranking points formulas changed in 2018.  Pre-2018 and post-2018
  points are not directly comparable — consider including a binary
  'uses_new_formula' flag in future iterations.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def merge_rankings(
    matches: pd.DataFrame,
    rankings: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add the most recent pre-match FIFA ranking to each row in *matches*.

    Adds six columns:
    - ``home_rank``         : FIFA rank of the home team (lower = better)
    - ``home_rank_points``  : FIFA rating points of the home team
    - ``away_rank``         : FIFA rank of the away team
    - ``away_rank_points``  : FIFA rating points of the away team
    - ``rank_diff``         : away_rank − home_rank
                              Positive → home team is ranked better (lower number).
    - ``rank_points_diff``  : home_rank_points − away_rank_points

    Missing values (NaN) appear when:
    - The match predates FIFA rankings (pre-August 1993).
    - The team has never appeared in the rankings (micro-nations).

    Parameters
    ----------
    matches : pd.DataFrame
        Cleaned match results (from Phase 2 or with Elo features added).
        Must contain columns: date, home_team, away_team.
    rankings : pd.DataFrame
        Output of ``loader.load_fifa_rankings()``.  Must contain:
        rank_date, country_full, rank, total_points.

    Returns
    -------
    pd.DataFrame
        *matches* with six ranking feature columns appended.
    """
    if "rank_date" not in rankings.columns or "country_full" not in rankings.columns:
        logger.warning(
            "Rankings DataFrame is missing expected columns — "
            "ranking features will be skipped."
        )
        return matches

    df = matches.copy().reset_index(drop=True)
    df["_orig_idx"] = np.arange(len(df))

    rankings_s = (
        rankings[["rank_date", "country_full", "rank", "total_points"]]
        .dropna(subset=["rank_date", "country_full"])
        .sort_values("rank_date")
        .reset_index(drop=True)
    )

    home_r = _lookup_ranking(df, "home_team", rankings_s)
    away_r = _lookup_ranking(df, "away_team", rankings_s)

    df["home_rank"] = home_r["rank"]
    df["home_rank_points"] = home_r["total_points"]
    df["away_rank"] = away_r["rank"]
    df["away_rank_points"] = away_r["total_points"]

    # Derived features
    df["rank_diff"] = df["away_rank"] - df["home_rank"]
    df["rank_points_diff"] = df["home_rank_points"] - df["away_rank_points"]

    df = df.drop(columns=["_orig_idx"])

    n_missing = df["home_rank"].isna().sum()
    logger.info(
        "Rankings merged.  %d / %d matches have ranking data (%.1f%%).",
        len(df) - n_missing,
        len(df),
        (len(df) - n_missing) / len(df) * 100,
    )
    return df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _lookup_ranking(
    df: pd.DataFrame,
    team_col: str,
    rankings_s: pd.DataFrame,
) -> pd.DataFrame:
    """
    Use merge_asof to find the most recent ranking for each team in *df*.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain '_orig_idx', 'date', and *team_col*.
    team_col : str
        Column name holding team names ('home_team' or 'away_team').
    rankings_s : pd.DataFrame
        FIFA rankings sorted ascending by rank_date.

    Returns
    -------
    pd.DataFrame
        Same length as df, sorted by _orig_idx, with columns
        'rank' and 'total_points'.
    """
    # Build a lookup table sorted by date (required by merge_asof).
    # Both 'country_full' columns must share the exact same dtype for
    # merge_asof to accept them — convert both to plain object (str) to
    # avoid the StringDtype(na_value=nan) vs StringDtype(na_value=<NA>) clash.
    side = (
        df[["_orig_idx", "date", team_col]]
        .rename(columns={team_col: "country_full"})
        .sort_values("date")
        .reset_index(drop=True)
    )
    side["country_full"] = side["country_full"].astype(object)
    rankings_s = rankings_s.copy()
    rankings_s["country_full"] = rankings_s["country_full"].astype(object)

    merged = pd.merge_asof(
        side,
        rankings_s,
        left_on="date",
        right_on="rank_date",
        by="country_full",          # only match same-team rows
        direction="backward",       # last ranking BEFORE match date
        suffixes=("", "_ranking"),
    )

    # Restore original row order before returning
    return (
        merged[["_orig_idx", "rank", "total_points"]]
        .sort_values("_orig_idx")
        .reset_index(drop=True)
    )
