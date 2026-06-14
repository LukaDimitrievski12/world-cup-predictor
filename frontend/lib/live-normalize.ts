// Team name + status normalization shared by API route handlers and client code.
// Maps football-data.org names → our internal names (from lib/groups.ts).

import type { MatchStatus, MatchStage, LiveMatch } from "@/lib/live-types"

// football-data.org stage codes → our internal round keys
export const STAGE_MAP: Record<string, MatchStage> = {
  GROUP_STAGE:     "group",
  ROUND_OF_32:     "r32",
  ROUND_OF_16:     "r16",
  QUARTER_FINALS:  "qf",
  SEMI_FINALS:     "sf",
  FINAL:           "final",
  // Some APIs use these variants
  "3RD_PLACE":     "sf",   // treat 3rd-place play-off as SF slot
}

// football-data.org status → our internal status
export function normalizeStatus(apiStatus: string): MatchStatus {
  if (["FINISHED", "AWARDED"].includes(apiStatus))                        return "finished"
  if (["IN_PLAY", "PAUSED", "HALFTIME", "EXTRA_TIME", "PENALTY"].includes(apiStatus)) return "live"
  if (["CANCELLED", "POSTPONED", "SUSPENDED", "ABANDONED"].includes(apiStatus))       return "cancelled"
  return "scheduled"
}

// Maps every possible football-data.org team name → our groups.ts name.
// Direction: API name → internal name.
export const TEAM_NAME_MAP: Record<string, string> = {
  // Name differences between API and our groups.ts
  "México":                     "Mexico",
  "Korea Republic":             "South Korea",
  "Republic of Korea":          "South Korea",
  "DR Congo":                   "DR Congo",
  "Congo DR":                   "DR Congo",
  "Democratic Republic of Congo": "DR Congo",
  "Bosnia-Herzegovina":         "Bosnia and Herzegovina",
  "Bosnia & Herzegovina":       "Bosnia and Herzegovina",
  "Ivory Coast":                "Côte d'Ivoire",
  "Cote d'Ivoire":              "Côte d'Ivoire",
  "Cape Verde Islands":         "Cape Verde",
  "Uzbekistan":                 "Uzbekistan",
  "Curacao":                    "Curaçao",
  "USA":                        "United States",
  "United States of America":   "United States",
  "Czech Republic":             "Czech Republic",
  "Czechia":                    "Czech Republic",
  // Names that are correct as-is (listed for documentation)
  "Argentina": "Argentina",
  "Brazil": "Brazil",
  "France": "France",
  "Germany": "Germany",
  "England": "England",
  "Spain": "Spain",
  "Netherlands": "Netherlands",
  "Portugal": "Portugal",
  "Belgium": "Belgium",
  "Uruguay": "Uruguay",
  "Colombia": "Colombia",
  "Switzerland": "Switzerland",
  "Morocco": "Morocco",
  "Senegal": "Senegal",
  "Japan": "Japan",
  "South Korea": "South Korea",
  "Australia": "Australia",
  "Canada": "Canada",
  "Mexico": "Mexico",
  "Ecuador": "Ecuador",
  "Paraguay": "Paraguay",
  "Turkey": "Turkey",
  "Croatia": "Croatia",
  "Austria": "Austria",
  "Sweden": "Sweden",
  "Norway": "Norway",
  "Scotland": "Scotland",
  "Algeria": "Algeria",
  "Tunisia": "Tunisia",
  "Egypt": "Egypt",
  "Ghana": "Ghana",
  "South Africa": "South Africa",
  "Saudi Arabia": "Saudi Arabia",
  "Iran": "Iran",
  "Iraq": "Iraq",
  "Jordan": "Jordan",
  "Qatar": "Qatar",
  "Haiti": "Haiti",
  "Panama": "Panama",
  "New Zealand": "New Zealand",
}

export function normalizeTeamName(name: string): string {
  return TEAM_NAME_MAP[name] ?? name
}

// Normalize a raw football-data.org match object into our LiveMatch shape
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeMatch(m: any): LiveMatch {
  const status = normalizeStatus(m.status ?? "SCHEDULED")
  const apiStage: string = m.stage ?? "GROUP_STAGE"
  const stage = STAGE_MAP[apiStage] ?? "group"
  const group = m.group ? (m.group as string).replace("GROUP_", "") : null

  // Scores: prefer fullTime, fall back to regularTime
  const ft = m.score?.fullTime ?? m.score?.regularTime
  const homeScore = status === "finished" || status === "live" ? (ft?.home ?? null) : null
  const awayScore = status === "finished" || status === "live" ? (ft?.away ?? null) : null

  return {
    id: m.id,
    homeTeam: normalizeTeamName(m.homeTeam?.name ?? m.homeTeam?.shortName ?? ""),
    awayTeam: normalizeTeamName(m.awayTeam?.name ?? m.awayTeam?.shortName ?? ""),
    homeScore,
    awayScore,
    status,
    group,
    stage,
    kickoff: m.utcDate ?? "",
    minute: m.minute ?? undefined,
  }
}
