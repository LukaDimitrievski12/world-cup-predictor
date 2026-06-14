"""
Exploratory data analysis utilities for the World Cup Predictor project.

All public functions are pure:
  - No file I/O except optional ``save_path`` arguments.
  - No mutation of input DataFrames (internal copies are made where needed).
  - Safe to call in Jupyter notebooks or headless scripts alike.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Consistent colour palette — change once here, propagates to all plots.
# ---------------------------------------------------------------------------
_C = {
    "home": "#2196F3",   # blue
    "draw": "#9E9E9E",   # grey
    "away": "#F44336",   # red
    "positive": "#4CAF50",  # green
    "accent": "#FF9800",    # orange
}

_OUTCOME_ORDER = ["Home Win", "Draw", "Away Win"]
_OUTCOME_COLOURS = [_C["home"], _C["draw"], _C["away"]]


# ---------------------------------------------------------------------------
# 1. Structural overview
# ---------------------------------------------------------------------------


def summarize_dataframe(df: pd.DataFrame, name: str = "DataFrame") -> None:
    """
    Print a structured console overview of *df*.

    Reports: shape, per-column dtype / null count / unique count,
    and the first five rows.

    Parameters
    ----------
    df : pd.DataFrame
    name : str
        Label shown in the section header.
    """
    sep = "=" * 64
    print(f"\n{sep}\n  {name}\n{sep}")
    print(f"  Rows : {len(df):>10,}")
    print(f"  Cols : {df.shape[1]:>10,}\n")

    info = pd.DataFrame(
        {
            "dtype": df.dtypes,
            "non_null": df.notna().sum(),
            "null": df.isna().sum(),
            "null_%": (df.isna().mean() * 100).round(2),
            "unique": df.nunique(),
        }
    )
    print(info.to_string())
    print(f"\n{'─' * 64}\nFirst 5 rows:\n")
    print(df.head().to_string())
    print(sep)


# ---------------------------------------------------------------------------
# 2. High-level statistics
# ---------------------------------------------------------------------------


def describe_match_results(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a one-row summary DataFrame of match-level statistics.

    Only rows with both scores present are included in the computation;
    the function does NOT drop NaN rows from the original DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw match results (output of ``loader.load_match_results``).

    Returns
    -------
    pd.DataFrame
        Single-row summary — transpose for display (``summary.T``).
    """
    scored = df.dropna(subset=["home_score", "away_score"]).copy()
    total = len(scored)

    home_wins = int((scored["home_score"] > scored["away_score"]).sum())
    draws = int((scored["home_score"] == scored["away_score"]).sum())
    away_wins = int((scored["home_score"] < scored["away_score"]).sum())

    scored["total_goals"] = scored["home_score"] + scored["away_score"]
    all_teams = pd.concat([scored["home_team"], scored["away_team"]])

    return pd.DataFrame(
        {
            "total_matches": [total],
            "home_wins": [home_wins],
            "draws": [draws],
            "away_wins": [away_wins],
            "home_win_%": [round(home_wins / total * 100, 2)],
            "draw_%": [round(draws / total * 100, 2)],
            "away_win_%": [round(away_wins / total * 100, 2)],
            "avg_home_goals": [round(float(scored["home_score"].mean()), 3)],
            "avg_away_goals": [round(float(scored["away_score"].mean()), 3)],
            "avg_total_goals": [round(float(scored["total_goals"].mean()), 3)],
            "date_min": [scored["date"].min()],
            "date_max": [scored["date"].max()],
            "unique_teams": [all_teams.nunique()],
            "unique_tournaments": [scored["tournament"].nunique()],
            "pct_neutral_venue": [
                round(scored["neutral"].mean() * 100, 2)
                if "neutral" in scored.columns
                else None
            ],
        }
    )


# ---------------------------------------------------------------------------
# 3. Plots
# ---------------------------------------------------------------------------


def plot_matches_per_year(
    df: pd.DataFrame,
    save_path: Optional[str] = None,
) -> None:
    """
    Bar chart of total international matches played per calendar year.

    Useful for spotting data gaps (e.g. WWI/WWII) and the post-1990
    explosion in fixture count.

    Parameters
    ----------
    df : pd.DataFrame
    save_path : str, optional
        File path to save the figure (PNG/SVG/PDF). Shows interactively
        when *None*.
    """
    df = df.dropna(subset=["date"]).copy()
    counts = df.groupby(df["date"].dt.year).size().rename("matches")

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.bar(counts.index, counts.values, color=_C["positive"], edgecolor="none", alpha=0.85)
    ax.set_title("International Matches Played per Year", fontsize=13, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Matches")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _save_or_show(fig, save_path)


def plot_outcomes_over_time(
    df: pd.DataFrame,
    freq: str = "10YE",
    save_path: Optional[str] = None,
) -> None:
    """
    Line chart of match outcome proportions (home win / draw / away win)
    grouped by calendar period.

    Parameters
    ----------
    df : pd.DataFrame
    freq : str
        Pandas offset alias for grouping.  ``"10YE"`` = 10-year buckets
        ending at year-end (default).  Use ``"YE"`` for annual resolution.
    save_path : str, optional
    """
    df = df.dropna(subset=["home_score", "away_score", "date"]).copy()
    df["outcome"] = _outcome_label(df)

    grouped = (
        df.set_index("date")
        .groupby(pd.Grouper(freq=freq))["outcome"]
        .value_counts(normalize=True)
        .mul(100)
        .unstack(fill_value=0)
        .rename_axis("period")
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(13, 5))
    for col, colour, label in zip(
        ["Home Win", "Draw", "Away Win"],
        _OUTCOME_COLOURS,
        _OUTCOME_ORDER,
    ):
        if col in grouped.columns:
            ax.plot(
                grouped["period"],
                grouped[col],
                marker="o",
                markersize=5,
                color=colour,
                label=label,
                linewidth=2.2,
            )

    ax.set_title("Match Outcome Proportions Over Time", fontsize=13, fontweight="bold")
    ax.set_xlabel("Period")
    ax.set_ylabel("Share of Matches (%)")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.legend(framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _save_or_show(fig, save_path)


def plot_goals_distribution(
    df: pd.DataFrame,
    max_goals: int = 12,
    save_path: Optional[str] = None,
) -> None:
    """
    Three-panel histogram: home goals, away goals, and total goals per match.

    Parameters
    ----------
    df : pd.DataFrame
    max_goals : int
        X-axis upper limit; caps outlier bars.
    save_path : str, optional
    """
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["total_goals"] = df["home_score"] + df["away_score"]

    columns = [
        ("home_score", "Home Goals / Match", _C["home"]),
        ("away_score", "Away Goals / Match", _C["away"]),
        ("total_goals", "Total Goals / Match", _C["positive"]),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (col, title, colour) in zip(axes, columns):
        clipped = df[col].clip(upper=max_goals)
        counts = clipped.value_counts().sort_index()
        ax.bar(counts.index, counts.values, color=colour, edgecolor="white", alpha=0.85)
        mean_val = float(df[col].mean())
        ax.axvline(mean_val, color="black", linestyle="--", linewidth=1.4,
                   label=f"mean={mean_val:.2f}")
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Goals")
        ax.set_ylabel("Matches")
        ax.legend(fontsize=9)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Goal Distributions — All International Matches", fontsize=14, fontweight="bold")
    fig.tight_layout()
    _save_or_show(fig, save_path)


def plot_home_advantage(
    df: pd.DataFrame,
    save_path: Optional[str] = None,
) -> None:
    """
    Side-by-side bars comparing outcome proportions at home venues
    vs. neutral venues.

    This directly quantifies the 'home advantage' effect — a key
    predictor we will include as a binary feature in Phase 3.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a ``neutral`` boolean column.
    save_path : str, optional
    """
    if "neutral" not in df.columns:
        logger.warning("'neutral' column missing — skipping home advantage plot.")
        return

    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["outcome"] = _outcome_label(df)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, (is_neutral, label) in zip(
        axes,
        [(False, "Home-Venue Matches"), (True, "Neutral-Venue Matches")],
    ):
        subset = df[df["neutral"] == is_neutral]
        props = (
            subset["outcome"]
            .value_counts(normalize=True)
            .reindex(_OUTCOME_ORDER, fill_value=0)
            .mul(100)
        )
        bars = ax.bar(props.index, props.values, color=_OUTCOME_COLOURS,
                      edgecolor="white", alpha=0.87)
        ax.set_title(f"{label}\n(n = {len(subset):,})", fontweight="bold")
        ax.set_ylabel("Share of Matches (%)")
        ax.set_ylim(0, 65)
        ax.grid(axis="y", alpha=0.3)
        for bar, val in zip(bars, props.values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.8,
                f"{val:.1f}%",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )

    fig.suptitle("Home Advantage Effect", fontsize=14, fontweight="bold")
    fig.tight_layout()
    _save_or_show(fig, save_path)


def plot_top_teams(
    df: pd.DataFrame,
    top_n: int = 20,
    metric: Literal["matches", "wins", "win_rate"] = "wins",
    save_path: Optional[str] = None,
) -> None:
    """
    Horizontal bar chart ranking teams by a chosen metric.

    Parameters
    ----------
    df : pd.DataFrame
    top_n : int
        Number of teams to show.
    metric : {"matches", "wins", "win_rate"}
    save_path : str, optional
    """
    df = df.dropna(subset=["home_score", "away_score"]).copy()

    # Reshape so each row is one team's single-match record
    home = df[["home_team", "home_score", "away_score"]].rename(
        columns={"home_team": "team", "home_score": "gf", "away_score": "ga"}
    )
    away = df[["away_team", "away_score", "home_score"]].rename(
        columns={"away_team": "team", "away_score": "gf", "home_score": "ga"}
    )
    all_games = pd.concat([home, away], ignore_index=True)
    all_games["win"] = (all_games["gf"] > all_games["ga"]).astype(int)

    stats = all_games.groupby("team").agg(matches=("win", "count"), wins=("win", "sum"))
    stats["win_rate"] = stats["wins"] / stats["matches"]

    if metric not in stats.columns:
        raise ValueError(f"metric must be one of {list(stats.columns)}, got '{metric}'.")

    top = stats.nlargest(top_n, metric).sort_values(metric)

    labels = {
        "matches": "Total Matches Played",
        "wins": "Total Wins",
        "win_rate": "Win Rate",
    }
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(top.index, top[metric], color=_C["home"], edgecolor="white", alpha=0.87)
    ax.set_title(
        f"Top {top_n} Teams — {labels[metric]}",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel(labels[metric])
    if metric == "win_rate":
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _save_or_show(fig, save_path)


def plot_tournament_distribution(
    df: pd.DataFrame,
    top_n: int = 15,
    save_path: Optional[str] = None,
) -> None:
    """
    Horizontal bar chart showing match counts per tournament type.

    Important for Phase 2 where we will assign importance weights
    to tournaments (World Cup > Continental Championship > Friendly).

    Parameters
    ----------
    df : pd.DataFrame
    top_n : int
    save_path : str, optional
    """
    counts = df["tournament"].value_counts().head(top_n).sort_values()

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(counts.index, counts.values, color=_C["accent"], edgecolor="white", alpha=0.87)
    ax.set_title(
        f"Top {top_n} Tournament Types by Match Count",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel("Number of Matches")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _save_or_show(fig, save_path)


def plot_score_heatmap(
    df: pd.DataFrame,
    max_goals: int = 8,
    save_path: Optional[str] = None,
) -> None:
    """
    Heatmap of scoreline frequencies (home goals × away goals).

    Reveals score correlations — e.g. whether high-scoring games
    cluster around balanced or one-sided results.

    Parameters
    ----------
    df : pd.DataFrame
    max_goals : int
        Caps both axes; high-scoring outliers are grouped into the
        max_goals cell.
    save_path : str, optional
    """
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["hs"] = df["home_score"].clip(upper=max_goals).astype(int)
    df["as_"] = df["away_score"].clip(upper=max_goals).astype(int)

    grid = (
        df.groupby(["hs", "as_"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=range(max_goals + 1), columns=range(max_goals + 1), fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(9, 7))
    im = ax.imshow(grid.values, origin="upper", cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(max_goals + 1))
    ax.set_yticks(range(max_goals + 1))
    labels = [str(i) if i < max_goals else f"{max_goals}+" for i in range(max_goals + 1)]
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Away Goals")
    ax.set_ylabel("Home Goals")
    ax.set_title("Scoreline Frequency Heatmap", fontsize=13, fontweight="bold")
    plt.colorbar(im, ax=ax, label="Number of Matches")
    fig.tight_layout()
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _outcome_label(df: pd.DataFrame) -> pd.Series:
    """Return a Series of 'Home Win' / 'Draw' / 'Away Win' strings."""
    return np.where(
        df["home_score"] > df["away_score"],
        "Home Win",
        np.where(df["home_score"] == df["away_score"], "Draw", "Away Win"),
    )


def _save_or_show(fig: plt.Figure, save_path: Optional[str]) -> None:
    """Save figure to *save_path* or display it interactively."""
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Saved plot → '%s'", save_path)
    else:
        plt.show()
    plt.close(fig)
