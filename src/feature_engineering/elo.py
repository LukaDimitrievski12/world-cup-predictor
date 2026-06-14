"""
Elo rating system for international football teams.

Why Elo?
--------
Elo was designed for chess (Arpad Elo, 1960) and transfers cleanly to
football because:
  1. It self-corrects — over-performers eventually drift back toward
     their true strength as opponents accumulate wins against them.
  2. It summarises the entire history of a team into a single number,
     making it naturally suited to time-series feature engineering.
  3. The rating difference maps to a win probability via the logistic
     function, giving us a principled, interpretable baseline signal.

Key design decisions
--------------------
Home advantage offset (+65 points)
    On non-neutral venues the home team's EFFECTIVE rating is boosted
    by 65 Elo points when computing expected outcome — reflecting the
    documented ~6 pp home win advantage.  The stored rating itself is
    never inflated; only the probability calculation uses the offset.

K-factor scales with tournament importance
    Friendlies update ratings by ≤ 20 Elo points; World Cup matches
    by up to 60.  This prevents a string of January friendlies from
    swamping the signal from a World Cup qualification campaign.

Pre-match Elo as the feature (not post-match)
    Recording Elo BEFORE the match is a strict requirement to avoid
    data leakage: using the post-match rating would incorporate
    information about the result we're trying to predict.

Goal-difference multiplier (optional, off by default)
    Multiplying K by ln(|gd| + 1) rewards convincing wins more than
    narrow ones.  Improves Elo accuracy slightly but introduces an
    incentive to "run up the score" in unrealistic simulations.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level defaults (all configurable via function arguments)
# ---------------------------------------------------------------------------
INITIAL_ELO: float = 1500.0
HOME_ADVANTAGE: float = 65.0   # Elo offset for non-neutral venues
K_BASE: float = 20.0           # K-factor floor (friendlies)
K_MAX: float = 60.0            # K-factor ceiling (World Cup)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def compute_elo_ratings(
    df: pd.DataFrame,
    initial_elo: float = INITIAL_ELO,
    home_advantage: float = HOME_ADVANTAGE,
    k_base: float = K_BASE,
    k_max: float = K_MAX,
    use_goal_difference: bool = False,
) -> pd.DataFrame:
    """
    Process all matches chronologically and add pre-match Elo ratings.

    The input *df* MUST be sorted by date (ascending).
    ``preprocess_results()`` guarantees this via ``sort_values("date")``.
    Processing matches out of order would corrupt the rating chain.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned match results with columns: home_team, away_team,
        home_score, away_score, tournament_weight, neutral.
    initial_elo : float
        Rating assigned to any team on its first appearance (default 1500).
    home_advantage : float
        Elo points added to the home team's effective rating on non-neutral
        venues when computing expected outcome (default 65).
    k_base : float
        Minimum K-factor, applied to friendlies (default 20).
    k_max : float
        Maximum K-factor, applied to World Cup finals (default 60).
    use_goal_difference : bool
        Scale K by ln(|gd| + 1) so larger wins cause bigger updates
        (default False — keeps ratings stable for simulation in Phase 6).

    Returns
    -------
    pd.DataFrame
        Input df with four new columns:
        ``home_elo_pre``, ``away_elo_pre``   — features for modelling.
        ``home_elo_post``, ``away_elo_post`` — for audit / inspection.
        ``elo_diff``                          — home_elo_pre − away_elo_pre.
    """
    df = df.copy()

    # defaultdict means any unseen team starts at initial_elo automatically
    ratings: dict[str, float] = defaultdict(lambda: initial_elo)

    # Pre-allocate arrays — avoids repeated list.append() overhead
    n = len(df)
    home_pre = np.empty(n, dtype=np.float64)
    away_pre = np.empty(n, dtype=np.float64)
    home_post = np.empty(n, dtype=np.float64)
    away_post = np.empty(n, dtype=np.float64)

    # itertuples is ~10× faster than iterrows because it avoids boxing
    # each row into a Series; order matters here so we cannot vectorise.
    for i, row in enumerate(df.itertuples(index=False)):
        home_team: str = row.home_team
        away_team: str = row.away_team
        r_home: float = ratings[home_team]
        r_away: float = ratings[away_team]

        home_pre[i] = r_home
        away_pre[i] = r_away

        # Home venue boost: only applied to the probability calculation
        is_neutral = bool(getattr(row, "neutral", False))
        r_home_eff = r_home + (0.0 if is_neutral else home_advantage)

        # Logistic expected outcome for the home team
        expected_home = 1.0 / (1.0 + 10.0 ** ((r_away - r_home_eff) / 400.0))

        # Actual outcome: 1=win, 0.5=draw, 0=loss
        hs, gs = int(row.home_score), int(row.away_score)
        if hs > gs:
            actual_home = 1.0
        elif hs == gs:
            actual_home = 0.5
        else:
            actual_home = 0.0

        # K-factor: linearly interpolated between k_base and k_max
        # using tournament_weight (0.3 for friendlies → 1.0 for World Cup)
        weight = float(getattr(row, "tournament_weight", 0.5))
        k = k_base + (k_max - k_base) * weight

        if use_goal_difference:
            # np.log1p avoids log(0); minimum multiplier at gd=1 is ln(2) ≈ 0.69
            k *= np.log1p(abs(hs - gs))

        delta = k * (actual_home - expected_home)
        ratings[home_team] = r_home + delta
        ratings[away_team] = r_away - delta  # zero-sum: away's update is the negative

        home_post[i] = ratings[home_team]
        away_post[i] = ratings[away_team]

    df["home_elo_pre"] = home_pre
    df["away_elo_pre"] = away_pre
    df["home_elo_post"] = home_post
    df["away_elo_post"] = away_post
    df["elo_diff"] = home_pre - away_pre

    logger.info(
        "Elo computed for %d matches.  Final rating range: [%.0f – %.0f].",
        n,
        min(ratings.values()),
        max(ratings.values()),
    )
    return df


def get_current_ratings(df: pd.DataFrame) -> pd.Series:
    """
    Return the most recent Elo rating for every team in *df*.

    Uses the post-match rating from each team's last appearance
    (as home or away), so this reflects their rating after all
    matches in the dataset have been processed.

    Parameters
    ----------
    df : pd.DataFrame
        Output of ``compute_elo_ratings`` — must contain date,
        home_team, away_team, home_elo_post, away_elo_post.

    Returns
    -------
    pd.Series
        Index = team name; values = final Elo rating; sorted descending.
    """
    home = df[["date", "home_team", "home_elo_post"]].rename(
        columns={"home_team": "team", "home_elo_post": "elo"}
    )
    away = df[["date", "away_team", "away_elo_post"]].rename(
        columns={"away_team": "team", "away_elo_post": "elo"}
    )
    combined = pd.concat([home, away], ignore_index=True)
    return (
        combined.sort_values("date")
        .groupby("team")["elo"]
        .last()
        .sort_values(ascending=False)
        .rename("elo_rating")
    )


def elo_win_probability(
    home_elo: float,
    away_elo: float,
    home_advantage: float = HOME_ADVANTAGE,
    is_neutral: bool = False,
) -> float:
    """
    Return the expected probability of a home win given two Elo ratings.

    Used in Phase 6 (Monte Carlo simulation) to convert Elo ratings
    into match outcome probabilities.

    Parameters
    ----------
    home_elo, away_elo : float
    home_advantage : float
    is_neutral : bool

    Returns
    -------
    float
        Probability in [0, 1] that the home team wins in 90 minutes.
        Note: this is a raw Elo probability, not a three-way probability
        (home win / draw / away win) — calibration is handled in Phase 5.
    """
    offset = 0.0 if is_neutral else home_advantage
    return 1.0 / (1.0 + 10.0 ** ((away_elo - home_elo - offset) / 400.0))
