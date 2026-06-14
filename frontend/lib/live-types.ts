// Shared types for live tournament data (used by API routes, context, and pages)

export type MatchStatus = "scheduled" | "live" | "finished" | "cancelled"
export type TournamentMode = "live" | "simulation"
export type KnockoutRound = "r32" | "r16" | "qf" | "sf" | "final"
export type MatchStage = "group" | KnockoutRound

export interface LiveMatch {
  id: number
  homeTeam: string
  awayTeam: string
  homeScore: number | null
  awayScore: number | null
  status: MatchStatus
  group: string | null      // "A"–"L" for group stage, null for knockout
  stage: MatchStage
  kickoff: string           // ISO 8601
  minute?: number           // current match minute when live
}

export interface LiveStanding {
  position: number
  team: string
  played: number
  won: number
  drawn: number
  lost: number
  goalsFor: number
  goalsAgainst: number
  goalDifference: number
  points: number
}

export type LiveGroupStandings = Record<string, LiveStanding[]>   // "A" → sorted table

export interface TournamentContextValue {
  mode: TournamentMode
  setMode: (mode: TournamentMode) => void
  matches: LiveMatch[]
  groupStandings: LiveGroupStandings
  lastUpdated: Date | null
  isLoading: boolean
  error: string | null
  hasLiveData: boolean            // true if API returned any data
  isLiveMatchActive: boolean      // true if any match is currently in play
  // Helpers used by pages
  getLiveGroupMatch: (group: string, home: string, away: string) => LiveMatch | undefined
  getLiveKnockoutMatch: (team1: string | null, team2: string | null) => LiveMatch | undefined
  refresh: () => void
}
