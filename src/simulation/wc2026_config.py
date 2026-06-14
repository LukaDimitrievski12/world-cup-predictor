"""
FIFA World Cup 2026 configuration.

UPDATE THIS FILE once the actual draw results are confirmed.
The groups below are a reasonable placeholder based on likely qualifiers
and geographic distribution rules.  Team names must exactly match the
canonical names used in the feature matrix (from team_names.py).

Format:  WC2026 uses 48 teams in 12 groups of 4.
         Top 2 from each group + 8 best 3rd-place teams advance to R32.

Host nations: United States, Mexico, Canada (in CONCACAF allocation).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Group assignments
# IMPORTANT: Update with the actual draw (held December 2025).
# Team names must match canonical names in src/data_processing/team_names.py
# ---------------------------------------------------------------------------
WC2026_GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Korea", "Czech Republic", "South Africa"],
    "B": ["Switzerland", "Canada", "Qatar", "Bosnia and Herzegovina"],
    "C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "D": ["United States", "Turkey", "Australia", "Paraguay"],
    "E": ["Germany", "Curaçao", "Côte d'Ivoire", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# All 48 teams in tournament order
WC2026_TEAMS: list[str] = [t for group in WC2026_GROUPS.values() for t in group]

# Knockout round names in order (rounds that involve playing a match).
# "winner" is tracked separately after the final — it is not a round.
KNOCKOUT_ROUNDS: list[str] = [
    "round_of_32",
    "round_of_16",
    "quarterfinal",
    "semifinal",
    "final",
]

# Default Elo for teams missing from the feature matrix (new qualifiers,
# playoff winners with no historical data in our dataset)
DEFAULT_ELO: float = 1350.0
DEFAULT_FORM_WIN: float = 0.40
DEFAULT_FORM_GF: float = 1.4
DEFAULT_FORM_GA: float = 1.4
