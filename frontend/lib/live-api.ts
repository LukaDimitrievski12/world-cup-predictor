// Client-side fetchers that call our Next.js API routes (never the external API directly).

import type { LiveMatch, LiveGroupStandings } from "@/lib/live-types"

export interface MatchesResponse {
  matches: LiveMatch[]
  cached?: boolean
  stale?: boolean
  configured?: boolean
  error?: string
}

export interface StandingsResponse {
  standings: LiveGroupStandings
  cached?: boolean
  stale?: boolean
  configured?: boolean
  error?: string
}

export async function fetchLiveMatches(): Promise<MatchesResponse> {
  const res = await fetch("/api/tournament/matches", { cache: "no-store" })
  if (!res.ok) return { matches: [], error: `HTTP ${res.status}` }
  return res.json()
}

export async function fetchLiveStandings(): Promise<StandingsResponse> {
  const res = await fetch("/api/tournament/standings", { cache: "no-store" })
  if (!res.ok) return { standings: {}, error: `HTTP ${res.status}` }
  return res.json()
}

// Fetches both in parallel — used by the context provider on each poll cycle
export async function fetchTournamentData(): Promise<{
  matches: LiveMatch[]
  standings: LiveGroupStandings
  isConfigured: boolean
  error: string | null
}> {
  const [mr, sr] = await Promise.all([
    fetchLiveMatches().catch((): MatchesResponse => ({ matches: [], error: "network" })),
    fetchLiveStandings().catch((): StandingsResponse => ({ standings: {}, error: "network" })),
  ])

  const isConfigured = mr.configured !== false && sr.configured !== false
  const error = mr.error ?? sr.error ?? null

  return {
    matches:      mr.matches,
    standings:    sr.standings,
    isConfigured,
    error,
  }
}
