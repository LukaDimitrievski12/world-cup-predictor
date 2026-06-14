"""
Data cleaning and preprocessing pipeline for the World Cup Predictor.

Transforms raw match results into a clean, labelled dataset ready
for feature engineering (Phase 3).

Pipeline steps (in order)
--------------------------
1.  Drop rows with missing scores.
2.  Standardise team names (historical → modern canonical).
3.  Flag matches involving defunct nations.
4.  Apply configurable year cutoff.
5.  Assign tournament importance weights (used as sample_weight in Phase 4).
6.  Create ordinal outcome label: 0 = away win, 1 = draw, 2 = home win.
7.  Derive goal_difference and total_goals columns.
8.  Sort chronologically and reset index.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from .team_names import DEFUNCT_TEAMS, TEAM_NAME_MAP

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = _PROJECT_ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# Outcome encoding
# ---------------------------------------------------------------------------
# Using named constants instead of magic integers prevents subtle bugs
# when comparing e.g. (outcome == 2) vs (outcome == "home_win").
OUTCOME_AWAY_WIN: int = 0
OUTCOME_DRAW: int = 1
OUTCOME_HOME_WIN: int = 2

OUTCOME_LABEL: dict[int, str] = {
    OUTCOME_HOME_WIN: "home_win",
    OUTCOME_DRAW: "draw",
    OUTCOME_AWAY_WIN: "away_win",
}

# ---------------------------------------------------------------------------
# Tournament importance weights
# ---------------------------------------------------------------------------
# Rationale: a team fielding its B-squad in a January friendly reveals far
# less about its true quality than a World Cup knockout match.
# These weights will be passed as ``sample_weight`` to scikit-learn models
# in Phase 4 so that high-stakes matches exert more influence on training.
#
# Tier structure:
#   1.00  →  FIFA World Cup knockout rounds (peak pressure / elite teams)
#   0.85  →  Continental championships
#   0.75  →  World Cup / major qualifiers
#   0.65  →  Minor qualifiers
#   0.30  →  Friendly internationals

TOURNAMENT_WEIGHTS: dict[str, float] = {
    # ── Tier 1 ────────────────────────────────────────────────────────────
    "FIFA World Cup": 1.00,
    # ── Tier 2 — continental championships ────────────────────────────────
    "UEFA Euro": 0.85,
    "Copa América": 0.85,
    "Africa Cup of Nations": 0.85,
    "AFC Asian Cup": 0.85,
    "CONCACAF Gold Cup": 0.80,
    "OFC Nations Cup": 0.75,
    "CONCACAF Championship": 0.75,
    "African Cup of Nations": 0.85,  # variant spelling
    # ── Tier 2.5 — prestige invitational ──────────────────────────────────
    "Confederations Cup": 0.80,
    "UEFA Nations League": 0.72,
    "Nations League": 0.70,
    # ── Tier 3 — qualification campaigns ──────────────────────────────────
    "FIFA World Cup qualification": 0.75,
    "UEFA Euro qualification": 0.70,
    "Copa América qualification": 0.65,
    "Africa Cup of Nations qualification": 0.65,
    "AFC Asian Cup qualification": 0.65,
    "CONCACAF Gold Cup qualification": 0.60,
    # ── Tier 4 — low-stakes ────────────────────────────────────────────────
    "Friendly": 0.30,
}

_DEFAULT_WEIGHT: float = 0.50  # fallback for unrecognised tournament strings


# ---------------------------------------------------------------------------
# Public pipeline
# ---------------------------------------------------------------------------


def preprocess_results(
    df: pd.DataFrame,
    year_cutoff: int = 1980,
    drop_defunct: bool = False,
) -> pd.DataFrame:
    """
    Run the full cleaning pipeline on raw match results.

    Parameters
    ----------
    df : pd.DataFrame
        Output of ``loader.load_match_results()``.
    year_cutoff : int
        Discard matches before this year.  Default 1980 strikes the
        right balance: enough data for robust rolling statistics while
        excluding the pre-modern era where tactics, fitness, and
        competition formats differed dramatically.

        Important: even if you set year_cutoff=1990, keep year_cutoff=1872
        when computing Elo ratings (Phase 3) — Elo needs the full history
        to converge on accurate starting values before the training window.
    drop_defunct : bool
        Drop matches involving defunct nations (e.g. Soviet Union).
        Default False keeps them (they contain real signal) but marks
        them with ``is_historical = True`` for optional later filtering.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with additional columns:
        ``outcome``, ``outcome_label``, ``tournament_weight``,
        ``is_historical``, ``goal_difference``, ``total_goals``.
    """
    df = df.copy()
    n_raw = len(df)

    # ── 1. Drop missing scores ─────────────────────────────────────────────
    df = df.dropna(subset=["home_score", "away_score"])
    _log_drop(n_raw, len(df), "missing scores")

    # Convert nullable Int64 → plain int now NaNs are gone.
    # Int64 (capitalised) is pandas' nullable integer; int is the standard
    # NumPy integer — required by sklearn and most downstream operations.
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)

    # ── 2. Standardise team names ──────────────────────────────────────────
    df["home_team"] = df["home_team"].map(lambda t: TEAM_NAME_MAP.get(str(t), str(t)))
    df["away_team"] = df["away_team"].map(lambda t: TEAM_NAME_MAP.get(str(t), str(t)))

    # ── 3. Flag defunct-nation matches ─────────────────────────────────────
    df["is_historical"] = (
        df["home_team"].isin(DEFUNCT_TEAMS) | df["away_team"].isin(DEFUNCT_TEAMS)
    )
    n_historical = int(df["is_historical"].sum())
    logger.info("Flagged %d matches involving defunct nations.", n_historical)

    if drop_defunct:
        n_before = len(df)
        df = df[~df["is_historical"]].copy()
        _log_drop(n_before, len(df), "defunct-nation matches")

    # ── 4. Year cutoff ─────────────────────────────────────────────────────
    n_before = len(df)
    df = df[df["date"].dt.year >= year_cutoff].copy()
    _log_drop(n_before, len(df), f"matches played before {year_cutoff}")

    # ── 5. Tournament weights ──────────────────────────────────────────────
    df["tournament_weight"] = df["tournament"].map(
        lambda t: _resolve_tournament_weight(str(t))
    )
    logger.info(
        "Tournament weights assigned — mean: %.3f, min: %.2f, max: %.2f.",
        df["tournament_weight"].mean(),
        df["tournament_weight"].min(),
        df["tournament_weight"].max(),
    )

    # ── 6. Outcome label ───────────────────────────────────────────────────
    # Using np.where (vectorised) rather than .apply for performance on
    # large DataFrames.
    df["outcome"] = np.where(
        df["home_score"] > df["away_score"],
        OUTCOME_HOME_WIN,
        np.where(
            df["home_score"] == df["away_score"],
            OUTCOME_DRAW,
            OUTCOME_AWAY_WIN,
        ),
    ).astype(int)
    df["outcome_label"] = df["outcome"].map(OUTCOME_LABEL)

    # ── 7. Derived columns ─────────────────────────────────────────────────
    df["goal_difference"] = df["home_score"] - df["away_score"]
    df["total_goals"] = df["home_score"] + df["away_score"]

    # ── 8. Sort and reset index ────────────────────────────────────────────
    df = df.sort_values("date").reset_index(drop=True)

    logger.info(
        "Preprocessing complete: %d → %d rows retained (%.1f%%).",
        n_raw,
        len(df),
        len(df) / n_raw * 100,
    )
    return df


def temporal_split(
    df: pd.DataFrame,
    val_start: str = "2018-01-01",
    test_start: str = "2022-01-01",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partition *df* into non-overlapping train / validation / test sets
    using match date as the split criterion.

    Why temporal split?
    -------------------
    Football is a time series: a team's 2022 form depends on its 2021
    form, which depends on 2020, and so on.  Random splitting allows
    future matches to leak into training — the model would effectively
    'know' results from after the test match date, producing
    optimistically biased metrics.  A hard temporal cut avoids this.

    Split rationale:
    - Train:      everything before 2018 (40+ years of modern football)
    - Validation: 2018–2021  (includes 2018 World Cup for tuning signal)
    - Test:       2022–present  (includes 2022 World Cup — held out
                                 until final model evaluation)

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned match results sorted by date.
    val_start : str
        ISO-format date string; first date of the validation window.
    test_start : str
        ISO-format date string; first date of the test window.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        (train, validation, test) — non-overlapping, exhaustive.
    """
    val_ts = pd.Timestamp(val_start)
    test_ts = pd.Timestamp(test_start)

    train = df[df["date"] < val_ts].copy()
    val = df[(df["date"] >= val_ts) & (df["date"] < test_ts)].copy()
    test = df[df["date"] >= test_ts].copy()

    assert len(train) + len(val) + len(test) == len(df), (
        "Split is not exhaustive — check for NaT values in 'date' column."
    )

    for name, split in [("Train", train), ("Validation", val), ("Test", test)]:
        if len(split):
            logger.info(
                "%-14s %6d rows   [%s  →  %s]",
                name + ":",
                len(split),
                split["date"].min().date(),
                split["date"].max().date(),
            )
        else:
            logger.warning("%s split is empty — check date parameters.", name)

    return train, val, test


def describe_splits(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return a concise comparison of class balance across all three splits.

    A large divergence in home_win_% between train and test would signal
    a structural shift in football outcomes over time — worth investigating
    before trusting model evaluation numbers.

    Parameters
    ----------
    train, val, test : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        One row per split; columns show match count and outcome percentages.
    """
    def _row(name: str, split: pd.DataFrame) -> dict:
        n = len(split)
        if n == 0:
            return {"split": name, "n_matches": 0}
        return {
            "split": name,
            "n_matches": n,
            "home_win_%": round((split["outcome"] == OUTCOME_HOME_WIN).mean() * 100, 1),
            "draw_%": round((split["outcome"] == OUTCOME_DRAW).mean() * 100, 1),
            "away_win_%": round((split["outcome"] == OUTCOME_AWAY_WIN).mean() * 100, 1),
            "avg_goals": round(split["total_goals"].mean(), 2),
            "date_min": str(split["date"].min().date()),
            "date_max": str(split["date"].max().date()),
        }

    return pd.DataFrame(
        [_row("train", train), _row("validation", val), _row("test", test)]
    ).set_index("split")


def save_processed(df: pd.DataFrame, filename: str = "matches_clean.csv") -> Path:
    """
    Persist the cleaned DataFrame to ``data/processed/<filename>``.

    Parameters
    ----------
    df : pd.DataFrame
    filename : str

    Returns
    -------
    Path
        Absolute path of the saved file.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / filename
    df.to_csv(out_path, index=False)
    logger.info("Saved → '%s'  (%d rows, %d cols).", out_path, *df.shape)
    return out_path


def get_outcome_distribution(df: pd.DataFrame) -> pd.Series:
    """
    Return outcome counts and percentages as a single formatted Series.

    Convenience function for quick sanity checks in notebooks.
    """
    counts = df["outcome_label"].value_counts()
    pcts = (df["outcome_label"].value_counts(normalize=True) * 100).round(1)
    return pd.concat(
        [counts.rename("count"), pcts.rename("pct_%")], axis=1
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_tournament_weight(tournament: str) -> float:
    """
    Look up the importance weight for *tournament*.

    Tries exact match first; falls back to substring search (e.g.
    'UEFA Euro 2020 qualification' matches 'UEFA Euro qualification').
    Longer keys are tested before shorter ones so more specific patterns
    win over general ones (prevents 'FIFA World Cup' matching before
    'FIFA World Cup qualification').
    """
    if tournament in TOURNAMENT_WEIGHTS:
        return TOURNAMENT_WEIGHTS[tournament]

    t_lower = tournament.lower()
    for key, weight in sorted(TOURNAMENT_WEIGHTS.items(), key=lambda x: -len(x[0])):
        if key.lower() in t_lower:
            return weight

    return _DEFAULT_WEIGHT


def _log_drop(before: int, after: int, reason: str) -> None:
    dropped = before - after
    if dropped > 0:
        logger.info("  Dropped %5d rows  (%s).", dropped, reason)
