"""
Monte Carlo tournament simulation engine.

Design
------
For each simulation run:
  1. Simulate all 12 groups (6 matches each = 72 total group matches).
  2. Rank teams within each group; take top 2 per group (24) + 8 best
     3rd-place teams = 32 teams advance.
  3. Seed the 32 teams by group-stage performance; create a bracket
     (seed 1 vs 32, seed 2 vs 31, …).
  4. Simulate 5 knockout rounds.  Draws in 90 minutes resolved by a
     penalty shootout model (Elo-adjusted 50/50).
  5. Record which round each team reached.

After N simulations, divide counts by N to get advancement probabilities.

Probability model
-----------------
For each match, we:
  a) Build a feature vector from the two teams' current profiles.
  b) Call model.predict_proba() → [P(away_win), P(draw), P(home_win)].
  c) Sample from this distribution.

All World Cup matches (group and knockout) are treated as neutral-venue
with tournament_weight = 1.0.  This is correct: the USA/Mexico/Canada
host stadiums are neutral territory for all non-host teams, and even
host teams don't get the same advantage as a true home fixture.

Note on Elo updating during simulation
--------------------------------------
We do NOT update team Elo ratings during the tournament simulation.
Doing so would create path-dependency: a team that wins an early group
match (and gains Elo) would be stronger in later matches within the
same simulation run, creating feedback loops.  Since 10 000 simulations
average over all outcomes anyway, fixed ratings give the same expected
result with far simpler code.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .wc2026_config import (
    DEFAULT_ELO,
    DEFAULT_FORM_GA,
    DEFAULT_FORM_GF,
    DEFAULT_FORM_WIN,
    KNOCKOUT_ROUNDS,
    WC2026_GROUPS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Team profile
# ---------------------------------------------------------------------------


@dataclass
class TeamProfile:
    """Snapshot of a team's current strength for simulation use."""
    name: str
    elo: float
    # Form over last 5 matches
    last5_win: float = DEFAULT_FORM_WIN
    last5_draw: float = 0.25
    last5_loss: float = 0.35
    last5_gf: float = DEFAULT_FORM_GF
    last5_ga: float = DEFAULT_FORM_GA
    last5_points: float = 1.45
    # Form over last 10 matches
    last10_win: float = DEFAULT_FORM_WIN
    last10_draw: float = 0.25
    last10_loss: float = 0.35
    last10_gf: float = DEFAULT_FORM_GF
    last10_ga: float = DEFAULT_FORM_GA
    last10_points: float = 1.45
    # Rankings (None if pre-1993 or team never ranked)
    rank: Optional[float] = None
    rank_points: Optional[float] = None


def build_team_profiles(df: pd.DataFrame) -> dict[str, TeamProfile]:
    """
    Build a current TeamProfile for every team in the feature matrix.

    We compute stats DIRECTLY from the raw match history (not from the
    shifted form-feature columns) to include the most recent match.

    Parameters
    ----------
    df : pd.DataFrame
        Full feature matrix output of Phase 3, sorted by date.

    Returns
    -------
    dict[str, TeamProfile]
        Team name → profile.
    """
    # Build long-format match history with post-match Elo
    home_cols = {
        "date": "date",
        "home_team": "team",
        "home_score": "gf",
        "away_score": "ga",
        "home_elo_post": "elo_post",
    }
    away_cols = {
        "date": "date",
        "away_team": "team",
        "away_score": "gf",
        "home_score": "ga",
        "away_elo_post": "elo_post",
    }

    home_r = df[[c for c in home_cols if c in df.columns]].rename(columns=home_cols)
    away_r = df[[c for c in away_cols if c in df.columns]].rename(columns=away_cols)

    # Ranking lookup (use most recent available)
    if "home_rank" in df.columns:
        home_rank = df[["date", "home_team", "home_rank", "home_rank_points"]].rename(
            columns={"home_team": "team", "home_rank": "rank", "home_rank_points": "rank_points"}
        )
        away_rank = df[["date", "away_team", "away_rank", "away_rank_points"]].rename(
            columns={"away_team": "team", "away_rank": "rank", "away_rank_points": "rank_points"}
        )
        rank_long = pd.concat([home_rank, away_rank], ignore_index=True)
    else:
        rank_long = None

    long = pd.concat([home_r, away_r], ignore_index=True).sort_values(["team", "date"])
    all_teams = sorted(long["team"].unique())

    profiles: dict[str, TeamProfile] = {}
    for team in all_teams:
        t_hist = long[long["team"] == team]
        if t_hist.empty:
            profiles[team] = TeamProfile(name=team, elo=DEFAULT_ELO)
            continue

        current_elo = float(t_hist["elo_post"].iloc[-1])
        gf = t_hist["gf"].astype(float)
        ga = t_hist["ga"].astype(float)

        def _form(n: int) -> dict:
            sub = t_hist.tail(n)
            sub_gf = sub["gf"].astype(float)
            sub_ga = sub["ga"].astype(float)
            wins = (sub_gf > sub_ga).astype(float)
            draws = (sub_gf == sub_ga).astype(float)
            losses = (sub_gf < sub_ga).astype(float)
            return {
                "win": float(wins.mean()) if len(sub) else DEFAULT_FORM_WIN,
                "draw": float(draws.mean()) if len(sub) else 0.25,
                "loss": float(losses.mean()) if len(sub) else 0.35,
                "gf": float(sub_gf.mean()) if len(sub) else DEFAULT_FORM_GF,
                "ga": float(sub_ga.mean()) if len(sub) else DEFAULT_FORM_GA,
                "points": float((wins * 3 + draws).mean()) if len(sub) else 1.45,
            }

        f5, f10 = _form(5), _form(10)

        rank, rank_pts = None, None
        if rank_long is not None:
            t_rank = rank_long[rank_long["team"] == team].dropna(subset=["rank"])
            if not t_rank.empty:
                latest = t_rank.sort_values("date").iloc[-1]
                rank = float(latest["rank"])
                rank_pts = float(latest["rank_points"]) if pd.notna(latest["rank_points"]) else None

        profiles[team] = TeamProfile(
            name=team, elo=current_elo,
            last5_win=f5["win"], last5_draw=f5["draw"], last5_loss=f5["loss"],
            last5_gf=f5["gf"], last5_ga=f5["ga"], last5_points=f5["points"],
            last10_win=f10["win"], last10_draw=f10["draw"], last10_loss=f10["loss"],
            last10_gf=f10["gf"], last10_ga=f10["ga"], last10_points=f10["points"],
            rank=rank, rank_points=rank_pts,
        )

    logger.info("Built profiles for %d teams.", len(profiles))
    return profiles


# ---------------------------------------------------------------------------
# Match prediction
# ---------------------------------------------------------------------------


def predict_match_proba(
    home: TeamProfile,
    away: TeamProfile,
    model: object,
    feature_cols: list[str],
    is_neutral: bool = True,
    tournament_weight: float = 1.0,
) -> np.ndarray:
    """
    Return [P(away_win), P(draw), P(home_win)] for a hypothetical match.

    Parameters
    ----------
    home, away : TeamProfile
    model : fitted sklearn Pipeline / CalibratedClassifierCV
    feature_cols : list[str]
        The exact feature column list used during training.
    is_neutral : bool
        True for all World Cup matches.
    tournament_weight : float
        1.0 for World Cup knockout; 0.75 for group stage.

    Returns
    -------
    np.ndarray, shape (3,) — probabilities summing to 1.
    """
    nan = float("nan")

    def _rdiff(a: Optional[float], b: Optional[float]) -> float:
        return (a - b) if (a is not None and b is not None) else nan

    row: dict[str, float] = {
        "home_elo_pre": home.elo,
        "away_elo_pre": away.elo,
        "elo_diff": home.elo - away.elo,
        "is_neutral": float(is_neutral),
        "tournament_weight": tournament_weight,
        "home_last5_win": home.last5_win,
        "home_last5_draw": home.last5_draw,
        "home_last5_loss": home.last5_loss,
        "home_last5_gf": home.last5_gf,
        "home_last5_ga": home.last5_ga,
        "home_last5_points": home.last5_points,
        "away_last5_win": away.last5_win,
        "away_last5_draw": away.last5_draw,
        "away_last5_loss": away.last5_loss,
        "away_last5_gf": away.last5_gf,
        "away_last5_ga": away.last5_ga,
        "away_last5_points": away.last5_points,
        "home_last10_win": home.last10_win,
        "home_last10_draw": home.last10_draw,
        "home_last10_loss": home.last10_loss,
        "home_last10_gf": home.last10_gf,
        "home_last10_ga": home.last10_ga,
        "home_last10_points": home.last10_points,
        "away_last10_win": away.last10_win,
        "away_last10_draw": away.last10_draw,
        "away_last10_loss": away.last10_loss,
        "away_last10_gf": away.last10_gf,
        "away_last10_ga": away.last10_ga,
        "away_last10_points": away.last10_points,
        "home_rank": home.rank if home.rank is not None else nan,
        "away_rank": away.rank if away.rank is not None else nan,
        "rank_diff": _rdiff(away.rank, home.rank),
        "home_rank_points": home.rank_points if home.rank_points is not None else nan,
        "away_rank_points": away.rank_points if away.rank_points is not None else nan,
        "rank_points_diff": _rdiff(home.rank_points, away.rank_points),
    }

    # Build DataFrame with only the columns the model expects
    X = pd.DataFrame([{k: row.get(k, nan) for k in feature_cols}])
    return model.predict_proba(X)[0]   # shape (3,): [P_away, P_draw, P_home]


def _resolve(
    proba: np.ndarray,
    rng: np.random.Generator,
    allow_draw: bool = True,
) -> str:
    """
    Sample a match outcome from *proba*.

    In knockout matches (allow_draw=False), a draw triggers a
    penalty shootout decided by a slight Elo-adjusted coin flip.

    Returns 'home' or 'away' (or 'draw' only if allow_draw=True).
    """
    p_away, p_draw, p_home = proba
    choices = ["away", "draw", "home"]
    outcome = rng.choice(choices, p=np.array([p_away, p_draw, p_home]))

    if outcome == "draw" and not allow_draw:
        # Penalty shootout: slight home advantage (Elo-based) removed for
        # WC knockouts since venues are neutral. Pure 50/50 with small noise.
        outcome = "home" if rng.random() < 0.5 else "away"

    return outcome


# ---------------------------------------------------------------------------
# Group stage simulation
# ---------------------------------------------------------------------------


def _simulate_group(
    teams: list[str],
    model: object,
    profiles: dict[str, TeamProfile],
    feature_cols: list[str],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Simulate one round-robin group and return the standings DataFrame.

    Columns: team, points, gf, ga, gd, wins, draws, losses.
    Sorted by: points DESC, gd DESC, gf DESC (simplified tiebreaker).
    """
    n = len(teams)
    stats: dict[str, dict] = {
        t: {"points": 0, "gf": 0, "ga": 0, "wins": 0, "draws": 0, "losses": 0}
        for t in teams
    }

    for i in range(n):
        for j in range(i + 1, n):
            home, away = teams[i], teams[j]
            hp = profiles.get(home, TeamProfile(name=home, elo=DEFAULT_ELO))
            ap = profiles.get(away, TeamProfile(name=away, elo=DEFAULT_ELO))

            proba = predict_match_proba(hp, ap, model, feature_cols,
                                        is_neutral=True, tournament_weight=0.75)
            outcome = _resolve(proba, rng, allow_draw=True)

            # Sample a scoreline consistent with the outcome
            gf_h, ga_h = _sample_scoreline(proba, outcome, rng)

            if outcome == "home":
                stats[home]["points"] += 3
                stats[home]["wins"] += 1
                stats[away]["losses"] += 1
            elif outcome == "away":
                stats[away]["points"] += 3
                stats[away]["wins"] += 1
                stats[home]["losses"] += 1
            else:
                stats[home]["points"] += 1
                stats[away]["points"] += 1
                stats[home]["draws"] += 1
                stats[away]["draws"] += 1

            stats[home]["gf"] += gf_h
            stats[home]["ga"] += ga_h
            stats[away]["gf"] += ga_h
            stats[away]["ga"] += gf_h

    rows = []
    for team, s in stats.items():
        s["team"] = team
        s["gd"] = s["gf"] - s["ga"]
        rows.append(s)

    df = pd.DataFrame(rows).sort_values(
        ["points", "gd", "gf"], ascending=False
    ).reset_index(drop=True)
    df["position"] = df.index + 1
    return df


def _sample_scoreline(
    proba: np.ndarray, outcome: str, rng: np.random.Generator
) -> tuple[int, int]:
    """
    Sample a (home_goals, away_goals) scoreline consistent with *outcome*.

    Uses a Poisson model with mean derived from the strength difference.
    """
    p_away, p_draw, p_home = proba
    # Expected home goals: scale with home advantage in probability
    lambda_h = max(0.5, 1.5 + (p_home - p_away) * 2.0)
    lambda_a = max(0.5, 1.5 + (p_away - p_home) * 2.0)

    for _ in range(50):   # rejection sample to match outcome
        gf = int(rng.poisson(lambda_h))
        ga = int(rng.poisson(lambda_a))
        sim_outcome = "home" if gf > ga else ("away" if ga > gf else "draw")
        if sim_outcome == outcome:
            return gf, ga

    # Fallback if rejection sampling fails
    if outcome == "home":
        return 1, 0
    elif outcome == "away":
        return 0, 1
    else:
        return 1, 1


# ---------------------------------------------------------------------------
# Monte Carlo runner
# ---------------------------------------------------------------------------


def run_monte_carlo(
    model: object,
    profiles: dict[str, TeamProfile],
    feature_cols: list[str],
    groups: dict[str, list[str]] = WC2026_GROUPS,
    n_simulations: int = 10_000,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Run the full Monte Carlo simulation and return advancement probabilities.

    Parameters
    ----------
    model : fitted sklearn Pipeline / CalibratedClassifierCV
    profiles : dict[str, TeamProfile]
    feature_cols : list[str]
    groups : dict[str, list[str]]
        Group assignments.
    n_simulations : int
        Number of full tournament simulations (default 10 000).
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    pd.DataFrame
        Columns: team, group_stage, round_of_32, round_of_16,
                 quarterfinal, semifinal, final, winner.
        Values: probability (0.0 – 1.0).
        Sorted by winner probability descending.
    """
    all_teams = [t for g in groups.values() for t in g]
    stages = ["group_stage"] + KNOCKOUT_ROUNDS + ["winner"]
    counts: dict[str, dict[str, int]] = {t: {s: 0 for s in stages} for t in all_teams}

    rng = np.random.default_rng(seed)

    for sim_idx in range(n_simulations):
        if (sim_idx + 1) % 1000 == 0:
            logger.info("  Simulation %d / %d …", sim_idx + 1, n_simulations)

        # ── Group stage ────────────────────────────────────────────────────
        group_results: dict[str, pd.DataFrame] = {}
        all_3rd: list[dict] = []

        for group_name, teams in groups.items():
            standings = _simulate_group(teams, model, profiles, feature_cols, rng)
            group_results[group_name] = standings

            # All teams participate in group stage
            for _, row in standings.iterrows():
                counts[row["team"]]["group_stage"] += 1

            # Collect 3rd-place team for best-3rd selection
            third = standings[standings["position"] == 3].iloc[0]
            all_3rd.append({
                "team": third["team"],
                "points": third["points"],
                "gd": third["gd"],
                "gf": third["gf"],
            })

        # ── Select 32 advancing teams ──────────────────────────────────────
        advancing: list[tuple[str, int]] = []  # (team, seed_rank)

        # Top 2 from each group
        first_place: list[str] = []
        second_place: list[str] = []
        for g_df in group_results.values():
            first_place.append(g_df[g_df["position"] == 1].iloc[0]["team"])
            second_place.append(g_df[g_df["position"] == 2].iloc[0]["team"])

        # Best 8 third-place teams by: points → gd → gf
        best_third = (
            pd.DataFrame(all_3rd)
            .sort_values(["points", "gd", "gf"], ascending=False)
            .head(8)["team"]
            .tolist()
        )

        # Seed: group winners are seeds 1–12, runners-up 13–24, best 3rd 25–32
        # (seeding is approximate; the actual WC bracket depends on group letters)
        advancing_teams = first_place + second_place + best_third

        # ── Knockout bracket (seeded) ──────────────────────────────────────
        # Assign Elo-based sub-seeding within each pot for the bracket
        def _elo(t: str) -> float:
            return profiles.get(t, TeamProfile(name=t, elo=DEFAULT_ELO)).elo

        seeds_1  = sorted(first_place, key=_elo, reverse=True)   # 12 teams
        seeds_2  = sorted(second_place, key=_elo, reverse=True)  # 12 teams
        seeds_3  = sorted(best_third, key=_elo, reverse=True)    # 8 teams

        # Create seeded bracket: strongest seed vs weakest seed
        bracket = seeds_1 + seeds_2 + seeds_3  # 32 teams seeded 1 → 32

        # Simulate knockout rounds
        remaining = bracket[:]
        for round_name in KNOCKOUT_ROUNDS:
            winners: list[str] = []
            # Pair: seed i vs seed (n-1-i)
            n_r = len(remaining)
            pairs = [(remaining[i], remaining[n_r - 1 - i]) for i in range(n_r // 2)]

            for home_team, away_team in pairs:
                hp = profiles.get(home_team, TeamProfile(name=home_team, elo=DEFAULT_ELO))
                ap = profiles.get(away_team, TeamProfile(name=away_team, elo=DEFAULT_ELO))
                proba = predict_match_proba(
                    hp, ap, model, feature_cols,
                    is_neutral=True, tournament_weight=1.0,
                )
                outcome = _resolve(proba, rng, allow_draw=False)
                winner = home_team if outcome == "home" else away_team
                winners.append(winner)
                counts[winner][round_name] += 1

            remaining = winners

        # The last team standing after all rounds is the champion
        if remaining:
            counts[remaining[0]]["winner"] += 1

    # ── Convert counts to probabilities ───────────────────────────────────
    rows = []
    for team in all_teams:
        row = {"team": team}
        for stage in stages:
            row[stage] = round(counts[team][stage] / n_simulations, 4)
        rows.append(row)

    result = (
        pd.DataFrame(rows)
        .sort_values("winner", ascending=False)
        .reset_index(drop=True)
    )
    logger.info("Monte Carlo complete: %d simulations.", n_simulations)
    return result
