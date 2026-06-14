from .loader import load_match_results, load_fifa_rankings, load_shootouts
from .inspector import (
    summarize_dataframe,
    describe_match_results,
    plot_outcomes_over_time,
    plot_goals_distribution,
    plot_home_advantage,
    plot_top_teams,
    plot_tournament_distribution,
    plot_matches_per_year,
    plot_score_heatmap,
)
from .preprocessor import (
    preprocess_results,
    temporal_split,
    save_processed,
    describe_splits,
    get_outcome_distribution,
    OUTCOME_HOME_WIN,
    OUTCOME_DRAW,
    OUTCOME_AWAY_WIN,
    OUTCOME_LABEL,
    TOURNAMENT_WEIGHTS,
)
from .team_names import TEAM_NAME_MAP, DEFUNCT_TEAMS

__all__ = [
    # loaders
    "load_match_results",
    "load_fifa_rankings",
    "load_shootouts",
    # inspector
    "summarize_dataframe",
    "describe_match_results",
    "plot_outcomes_over_time",
    "plot_goals_distribution",
    "plot_home_advantage",
    "plot_top_teams",
    "plot_tournament_distribution",
    "plot_matches_per_year",
    "plot_score_heatmap",
    # preprocessor
    "preprocess_results",
    "temporal_split",
    "save_processed",
    "describe_splits",
    "get_outcome_distribution",
    "OUTCOME_HOME_WIN",
    "OUTCOME_DRAW",
    "OUTCOME_AWAY_WIN",
    "OUTCOME_LABEL",
    "TOURNAMENT_WEIGHTS",
    # team names
    "TEAM_NAME_MAP",
    "DEFUNCT_TEAMS",
]
