"""
Rolling form features for the World Cup Predictor project.

For each match we compute team-level statistics over their last N
matches (before the match date), for both the home and away sides.

Features produced per team per window
--------------------------------------
last{N}_win    : win rate over last N matches
last{N}_draw   : draw rate
last{N}_loss   : loss rate
last{N}_gf     : avg goals scored (goals for)
last{N}_ga     : avg goals conceded (goals against)
last{N}_points : avg points earned (3=win, 1=draw, 0=loss)

Implementation
--------------
We reshape the match DataFrame into "long format" (one row per team
per match) to exploit pandas' vectorised groupby + rolling operations.
This avoids a Python-level loop over rows and is ~100× faster than
df.apply() for the ~90 000 long-format rows produced from 45 000 matches.

The rolling window is shifted by 1 (.shift(1)) so that the feature at
match i uses only the PREVIOUS i−1 matches — never the current one.
min_periods=1 means teams with fewer than N prior matches still get a
valid (though noisier) feature rather than NaN.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_STAT_COLS = ["gf", "ga", "win", "draw", "loss", "points"]


def compute_form_features(
    df: pd.DataFrame,
    windows: tuple[int, ...] = (5, 10),
) -> pd.DataFrame:
    """
    Add rolling form statistics for home and away teams to each match row.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned match results sorted chronologically.  Must contain:
        home_team, away_team, home_score, away_score, date, outcome.
    windows : tuple[int, ...]
        Rolling window sizes (number of matches).  Default (5, 10)
        captures recent hot-streak and medium-term form separately.

    Returns
    -------
    pd.DataFrame
        Input df with 2 × len(windows) × 6 new columns:
        home_last{N}_{stat} and away_last{N}_{stat} for each window
        and stat in [gf, ga, win, draw, loss, points].

    Notes
    -----
    NaN values appear for a team's first match (no prior history).
    Fill these downstream — in Phase 4 preprocessing — with 0 or
    with the global training-set mean per feature.
    """
    df = df.copy().reset_index(drop=True)

    # Build long-format records
    long = _build_long_format(df)

    # Sort so each team's matches are processed in chronological order.
    # _match_idx is the secondary sort key to break date ties deterministically.
    long = long.sort_values(["team", "date", "_match_idx"]).reset_index(drop=True)

    # Compute rolling stats with a one-position shift (pre-match only)
    for window in windows:
        for col in _STAT_COLS:
            long[f"last{window}_{col}"] = (
                long.groupby("team")[col]
                .transform(
                    lambda x: x.rolling(window, min_periods=1).mean().shift(1)
                )
            )

    feat_cols = [f"last{w}_{c}" for w in windows for c in _STAT_COLS]

    # Separate home/away records and join back to df by original match index
    for side in ("home", "away"):
        side_df = (
            long[long["side"] == side][["_match_idx"] + feat_cols]
            .rename(columns={c: f"{side}_{c}" for c in feat_cols})
            .set_index("_match_idx")
        )
        df = df.join(side_df)  # df.index == _match_idx (both are 0..N-1)

    logger.info(
        "Form features added: %d columns  (windows=%s).",
        len(feat_cols) * 2,
        windows,
    )
    return df


def get_feature_names(windows: tuple[int, ...] = (5, 10)) -> list[str]:
    """
    Return the list of form feature column names for given windows.

    Useful for Phase 4 to identify which columns to pass to the model.
    """
    return [
        f"{side}_last{w}_{c}"
        for side in ("home", "away")
        for w in windows
        for c in _STAT_COLS
    ]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_long_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reshape match df into long format: one row per (team, match).

    For each match we create two rows — one for the home team and one
    for the away team — with all statistics expressed from that team's
    perspective (gf = goals scored, ga = goals conceded, win = did this
    team win?).
    """
    hs = df["home_score"].astype(float)
    gs = df["away_score"].astype(float)
    idx = np.arange(len(df))

    home_win = (hs > gs).astype(float)
    draw = (hs == gs).astype(float)
    away_win = (gs > hs).astype(float)

    home_recs = pd.DataFrame(
        {
            "_match_idx": idx,
            "date": df["date"].values,
            "team": df["home_team"].values,
            "side": "home",
            "gf": hs.values,
            "ga": gs.values,
            "win": home_win.values,
            "draw": draw.values,
            "loss": away_win.values,
            "points": (home_win * 3 + draw).values,
        }
    )
    away_recs = pd.DataFrame(
        {
            "_match_idx": idx,
            "date": df["date"].values,
            "team": df["away_team"].values,
            "side": "away",
            "gf": gs.values,
            "ga": hs.values,
            "win": away_win.values,
            "draw": draw.values,
            "loss": home_win.values,
            "points": (away_win * 3 + draw).values,
        }
    )
    return pd.concat([home_recs, away_recs], ignore_index=True)
