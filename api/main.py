"""
FastAPI backend for the WC 2026 Predictor.

Run with:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

app = FastAPI(title="WC 2026 Predictor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow Vercel + localhost
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global state — loaded once at startup
# ---------------------------------------------------------------------------
_model = None
_sim_results: Optional[pd.DataFrame] = None
_profiles: Optional[pd.DataFrame] = None
_metrics: Optional[pd.DataFrame] = None
_feature_cols: list[str] = []


@app.on_event("startup")
async def load_data() -> None:
    global _model, _sim_results, _profiles, _metrics, _feature_cols

    try:
        from src.models.train import load_model
        _model = load_model("best_model")
    except FileNotFoundError:
        pass

    sim_path = PROJECT_ROOT / "results" / "simulation" / "probabilities.csv"
    if sim_path.exists():
        _sim_results = pd.read_csv(sim_path)

    profiles_path = PROJECT_ROOT / "data" / "processed" / "team_profiles.csv"
    if profiles_path.exists():
        _profiles = pd.read_csv(profiles_path)

    metrics_path = PROJECT_ROOT / "results" / "models" / "metrics.csv"
    if metrics_path.exists():
        _metrics = pd.read_csv(metrics_path, index_col=0)

    feat_path = PROJECT_ROOT / "results" / "models" / "feature_columns.txt"
    if feat_path.exists():
        _feature_cols = feat_path.read_text().strip().split("\n")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/simulation")
async def get_simulation() -> list[dict]:
    if _sim_results is None:
        raise HTTPException(status_code=404, detail="Run phase 6 first")
    df = _sim_results.copy()
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")


@app.get("/api/teams")
async def get_teams() -> list[dict]:
    if _profiles is None:
        raise HTTPException(status_code=404, detail="Run phase 6 first")
    cols = [c for c in ["team", "elo", "last5_win", "last5_gf", "last5_ga", "rank"] if c in _profiles.columns]
    df = _profiles[cols].copy().where(pd.notnull(_profiles[cols]), None)
    return df.sort_values("elo", ascending=False).to_dict(orient="records")


@app.get("/api/metrics")
async def get_metrics() -> list[dict]:
    if _metrics is None:
        raise HTTPException(status_code=404, detail="Run phase 4 first")
    return _metrics.reset_index().to_dict(orient="records")


class MatchRequest(BaseModel):
    home_team: str
    away_team: str
    is_neutral: bool = True
    tournament_weight: float = 1.0


def _get_elo(name: str) -> float:
    if _profiles is None:
        return 1350.0
    row = _profiles[_profiles["team"] == name]
    return float(row.iloc[0].get("elo", 1350)) if not row.empty else 1350.0


def _elo_predict(home: str, away: str, is_neutral: bool) -> dict:
    """Elo-based fallback when the ML model isn't available."""
    home_elo = _get_elo(home)
    away_elo = _get_elo(away)
    advantage = 0.0 if is_neutral else 50.0
    diff = (home_elo + advantage) - away_elo
    p_home = 1 / (1 + 10 ** (-diff / 400))
    p_away = 1 - p_home
    # Draw probability peaks near 0 elo diff (~28%), shrinks for big mismatches
    draw = max(0.08, 0.28 - abs(diff) * 0.00035)
    p_home -= draw * 0.5
    p_away -= draw * 0.5
    total = p_home + draw + p_away
    return {
        "home_team": home, "away_team": away,
        "home_win": round(p_home / total, 4),
        "draw":     round(draw   / total, 4),
        "away_win": round(p_away / total, 4),
        "home_elo": round(home_elo),
        "away_elo": round(away_elo),
        "method":   "elo",
    }


@app.post("/api/predict")
async def predict_match(body: MatchRequest) -> dict:
    if body.home_team == body.away_team:
        raise HTTPException(status_code=400, detail="Teams must be different")

    # Fall back to Elo prediction if ML model isn't loaded
    if _model is None or _profiles is None:
        return _elo_predict(body.home_team, body.away_team, body.is_neutral)

    from src.simulation.monte_carlo import TeamProfile, predict_match_proba

    def _profile(name: str) -> TeamProfile:
        row = _profiles[_profiles["team"] == name]
        if row.empty:
            return TeamProfile(name=name, elo=1350.0)
        r = row.iloc[0]
        return TeamProfile(
            name=name,
            elo=float(r.get("elo", 1350)),
            last5_win=float(r.get("last5_win", 0.4)),
            last5_gf=float(r.get("last5_gf", 1.4)),
            last5_ga=float(r.get("last5_ga", 1.4)),
            last10_win=float(r.get("last10_win", 0.4)),
            last10_gf=float(r.get("last10_gf", 1.4)),
            last10_ga=float(r.get("last10_ga", 1.4)),
            rank=float(r["rank"]) if pd.notna(r.get("rank")) else None,
            rank_points=float(r["rank_points"]) if pd.notna(r.get("rank_points")) else None,
        )

    hp, ap = _profile(body.home_team), _profile(body.away_team)
    proba = predict_match_proba(hp, ap, _model, _feature_cols, body.is_neutral, body.tournament_weight)
    p_away, p_draw, p_home = float(proba[0]), float(proba[1]), float(proba[2])

    return {
        "home_team": body.home_team, "away_team": body.away_team,
        "home_win": round(p_home, 4),
        "draw":     round(p_draw, 4),
        "away_win": round(p_away, 4),
        "home_elo": round(hp.elo),
        "away_elo": round(ap.elo),
        "method":   "ml",
    }
