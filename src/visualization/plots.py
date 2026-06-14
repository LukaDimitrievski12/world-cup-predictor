"""
Results visualisation for the World Cup Predictor project.

All functions follow the same contract as Phase 1 inspector.py:
  - Pure (no side effects beyond optional save_path).
  - Accept save_path: str | None — save or display interactively.
  - Call plt.close(fig) at the end to prevent memory leaks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_C = {
    "gold": "#FFD700",
    "silver": "#C0C0C0",
    "bronze": "#CD7F32",
    "blue": "#2196F3",
    "green": "#4CAF50",
    "red": "#F44336",
    "grey": "#9E9E9E",
    "bg": "#F5F5F5",
}


# ---------------------------------------------------------------------------
# 1. Tournament win probability bar chart
# ---------------------------------------------------------------------------


def plot_win_probabilities(
    results: pd.DataFrame,
    top_n: int = 20,
    save_path: Optional[str] = None,
) -> None:
    """
    Horizontal bar chart of WC 2026 win probabilities for top N teams.

    Parameters
    ----------
    results : pd.DataFrame
        Output of ``run_monte_carlo`` — must contain 'team' and 'winner'.
    top_n : int
    save_path : str, optional
    """
    top = results.nlargest(top_n, "winner").sort_values("winner")
    colours = [_C["gold"] if i == len(top) - 1
               else _C["silver"] if i == len(top) - 2
               else _C["blue"] for i in range(len(top))]

    fig, ax = plt.subplots(figsize=(10, 8))
    bars = ax.barh(top["team"], top["winner"] * 100, color=colours,
                   edgecolor="white", alpha=0.9)

    for bar, val in zip(bars, top["winner"] * 100):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=9)

    ax.set_title("FIFA World Cup 2026 — Win Probabilities",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Win Probability (%)")
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 2. Advancement probability heatmap
# ---------------------------------------------------------------------------


def plot_advancement_heatmap(
    results: pd.DataFrame,
    top_n: int = 32,
    save_path: Optional[str] = None,
) -> None:
    """
    Heatmap: team (rows) × tournament stage (columns), values = probability.

    Shows at a glance which teams are expected to go deep and which face
    tough groups / strong opponents in the bracket.
    """
    stage_cols = [c for c in results.columns if c != "team"]
    top = results.nlargest(top_n, "winner").set_index("team")[stage_cols]

    # Sort by winner probability descending (already sorted, but be explicit)
    top = top.sort_values("winner", ascending=False)

    fig, ax = plt.subplots(figsize=(len(stage_cols) * 1.6 + 2, top_n * 0.38 + 2))
    im = ax.imshow(top.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(range(len(stage_cols)))
    ax.set_xticklabels(
        [c.replace("_", "\n") for c in stage_cols], fontsize=9
    )
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top.index, fontsize=8)

    # Annotate cells
    for i in range(len(top)):
        for j in range(len(stage_cols)):
            val = top.values[i, j]
            text_col = "white" if val > 0.55 else "black"
            ax.text(j, i, f"{val:.0%}", ha="center", va="center",
                    fontsize=7, color=text_col)

    plt.colorbar(im, ax=ax, label="Probability", shrink=0.6)
    ax.set_title(
        f"FIFA World Cup 2026 — Advancement Probabilities (Top {top_n})",
        fontsize=13, fontweight="bold", pad=12,
    )
    fig.tight_layout()
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 3. ELO rating comparison
# ---------------------------------------------------------------------------


def plot_elo_rankings(
    profiles: pd.DataFrame,
    top_n: int = 30,
    save_path: Optional[str] = None,
) -> None:
    """
    Horizontal bar chart of current ELO ratings for top N teams.

    Parameters
    ----------
    profiles : pd.DataFrame
        Output of ``build_team_profiles`` saved as CSV — columns: team, elo.
    """
    top = profiles.nlargest(top_n, "elo").sort_values("elo")

    fig, ax = plt.subplots(figsize=(10, 9))
    ax.barh(top["team"], top["elo"], color=_C["blue"], edgecolor="white", alpha=0.88)
    ax.axvline(1500, color="black", linestyle=":", linewidth=1.2, label="Average (1500)")
    ax.set_title(f"Top {top_n} Teams by Elo Rating",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Elo Rating")
    ax.legend(fontsize=9)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 4. Feature importance (XGBoost / Random Forest)
# ---------------------------------------------------------------------------


def plot_feature_importance(
    model: Any,
    feature_cols: list[str],
    top_n: int = 20,
    save_path: Optional[str] = None,
) -> None:
    """
    Bar chart of feature importance from a tree-based model.

    Works with RandomForest (feature_importances_) and XGBoost.
    Automatically unwraps sklearn Pipeline and CalibratedClassifierCV.

    Parameters
    ----------
    model : fitted sklearn Pipeline / CalibratedClassifierCV
    feature_cols : list[str]
    top_n : int
    save_path : str, optional
    """
    estimator = _unwrap_model(model)
    if not hasattr(estimator, "feature_importances_"):
        logger.warning("Model does not expose feature_importances_ — skipping.")
        return

    importances = estimator.feature_importances_
    if len(importances) != len(feature_cols):
        logger.warning("Importance length mismatch (%d vs %d) — skipping.",
                       len(importances), len(feature_cols))
        return

    imp_df = (
        pd.Series(importances, index=feature_cols)
        .sort_values(ascending=False)
        .head(top_n)
        .sort_values()
    )

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(imp_df.index, imp_df.values, color=_C["green"], edgecolor="white", alpha=0.88)
    ax.set_title(f"Feature Importance — Top {top_n}", fontsize=13, fontweight="bold")
    ax.set_xlabel("Importance Score")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 5. Model metrics comparison table (saved as styled PNG)
# ---------------------------------------------------------------------------


def plot_model_comparison(
    metrics_df: pd.DataFrame,
    save_path: Optional[str] = None,
) -> None:
    """
    Render the model comparison table as a matplotlib figure.

    Parameters
    ----------
    metrics_df : pd.DataFrame
        Output of ``compare_models`` with models as index.
    save_path : str, optional
    """
    display_cols = ["accuracy", "log_loss", "brier_score", "f1_macro"]
    df = metrics_df[[c for c in display_cols if c in metrics_df.columns]]

    fig, ax = plt.subplots(figsize=(len(df.columns) * 2.5 + 1, len(df) * 0.6 + 1.5))
    ax.axis("off")

    table = ax.table(
        cellText=df.round(4).values,
        rowLabels=df.index,
        colLabels=df.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)

    # Highlight header
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#37474F")
            cell.set_text_props(color="white", fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#ECEFF1")

    ax.set_title("Model Comparison", fontsize=13, fontweight="bold", pad=20)
    fig.tight_layout()
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 6. Group-stage expected points bubble chart
# ---------------------------------------------------------------------------


def plot_group_strength(
    profiles: pd.DataFrame,
    groups: dict[str, list[str]],
    save_path: Optional[str] = None,
) -> None:
    """
    Scatter plot showing group-average Elo vs. variance (group difficulty).

    Each bubble is one group; size = max Elo in group (strongest team).
    Groups with high average AND high variance are "group of death".
    """
    rows = []
    for gname, teams in groups.items():
        elos = [
            float(profiles.loc[profiles["team"] == t, "elo"].values[0])
            if t in profiles["team"].values else 1350.0
            for t in teams
        ]
        rows.append({
            "group": gname,
            "mean_elo": np.mean(elos),
            "std_elo": np.std(elos),
            "max_elo": max(elos),
        })

    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(10, 7))
    sc = ax.scatter(
        df["mean_elo"], df["std_elo"],
        s=df["max_elo"] / 4,
        c=df["mean_elo"],
        cmap="YlOrRd",
        edgecolors="black",
        linewidths=0.5,
        alpha=0.85,
    )
    for _, row in df.iterrows():
        ax.annotate(
            f"Group {row['group']}",
            (row["mean_elo"], row["std_elo"]),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=9,
        )

    ax.set_title("Group Strength Analysis", fontsize=13, fontweight="bold")
    ax.set_xlabel("Average Group Elo (higher = stronger group)")
    ax.set_ylabel("Elo Std Dev (higher = more uneven / predictable group)")
    plt.colorbar(sc, ax=ax, label="Mean Elo")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _save_or_show(fig: plt.Figure, save_path: Optional[str]) -> None:
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Saved → '%s'.", save_path)
    else:
        plt.show()
    plt.close(fig)


def _unwrap_model(model: Any) -> Any:
    """Unwrap CalibratedClassifierCV → Pipeline → final estimator."""
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.pipeline import Pipeline

    if isinstance(model, CalibratedClassifierCV):
        # CalibratedClassifierCV stores the base estimator
        model = model.estimator

    if isinstance(model, Pipeline):
        model = model.named_steps.get("model", model[-1])

    return model
