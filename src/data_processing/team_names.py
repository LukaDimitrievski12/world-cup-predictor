"""
Canonical team name mapping for the World Cup Predictor project.

Without this mapping, "West Germany" and "Germany" appear as two
unrelated teams, silently fragmenting 25+ years of training signal.
We map every known historical variant to its modern FIFA-registered name.

Design decision: West Germany → Germany
---------------------------------------
The DFB (Deutscher Fußball-Bund) is the same organisation before and
after 1990 reunification — unlike Yugoslavia, which dissolved into
entirely separate FAs. Mapping West Germany to Germany is therefore
defensible. East Germany is also mapped to Germany, but flagged via
the DEFUNCT_TEAMS set so analysts can easily exclude them.

See preprocessor.py for how DEFUNCT_TEAMS interacts with the pipeline.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Historical / variant name  →  modern FIFA-registered name
# ---------------------------------------------------------------------------
TEAM_NAME_MAP: dict[str, str] = {
    # ── German reunification (1990) ────────────────────────────────────────
    "West Germany": "Germany",
    "East Germany": "Germany",
    # ── Soviet Union & successor states ───────────────────────────────────
    "Soviet Union": "Russia",
    # ── Yugoslav succession ────────────────────────────────────────────────
    "Yugoslavia": "Serbia",
    "Serbia and Montenegro": "Serbia",
    "Federal Republic of Yugoslavia": "Serbia",
    # ── Czechoslovakia ─────────────────────────────────────────────────────
    "Czechoslovakia": "Czech Republic",
    # ── African name changes ───────────────────────────────────────────────
    "Zaire": "DR Congo",
    "Congo DR": "DR Congo",
    "Swaziland": "Eswatini",
    "Cape Verde Islands": "Cape Verde",
    # ── Asian naming conventions (Kaggle / FIFA style) ─────────────────────
    "Korea Republic": "South Korea",
    "Korea DPR": "North Korea",
    "China PR": "China",
    "IR Iran": "Iran",
    "UAE": "United Arab Emirates",
    "Kyrgyz Republic": "Kyrgyzstan",
    "Timor-Leste": "East Timor",
    # ── Americas ───────────────────────────────────────────────────────────
    "USA": "United States",
    "Trinidad & Tobago": "Trinidad and Tobago",
    "Antigua & Barbuda": "Antigua and Barbuda",
    "St. Kitts and Nevis": "Saint Kitts and Nevis",
    "St. Vincent and the Grenadines": "Saint Vincent and the Grenadines",
    "St. Lucia": "Saint Lucia",
    # ── Europe ─────────────────────────────────────────────────────────────
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Macedonia": "North Macedonia",
    "Republic of Ireland": "Ireland",
    # ── Ivory Coast (both spellings appear in various datasets) ───────────
    "Ivory Coast": "Côte d'Ivoire",
    # ── Other ──────────────────────────────────────────────────────────────
    "Brunei Darussalam": "Brunei",
}

# ---------------------------------------------------------------------------
# Defunct nations — no clear modern successor or ambiguous mapping.
# Rows involving these teams are flagged with ``is_historical = True``
# rather than silently included or dropped.
# ---------------------------------------------------------------------------
DEFUNCT_TEAMS: frozenset[str] = frozenset(
    {
        "East Germany",
        "Soviet Union",
        "Yugoslavia",
        "Czechoslovakia",
        "Zaire",
        "Serbia and Montenegro",
        "Federal Republic of Yugoslavia",
        "Netherlands Antilles",
        "Saarland",
    }
)
