// Server-side proxy for football-data.org group standings.

import { NextResponse } from "next/server"
import { normalizeTeamName } from "@/lib/live-normalize"
import type { LiveGroupStandings, LiveStanding } from "@/lib/live-types"

const API_BASE    = "https://api.football-data.org/v4"
const COMPETITION = "WC"
const CACHE_TTL   = 60_000

let cache: { data: LiveGroupStandings; ts: number } | null = null

export async function GET() {
  if (cache && Date.now() - cache.ts < CACHE_TTL) {
    return NextResponse.json({ standings: cache.data, cached: true })
  }

  const key = process.env.FOOTBALL_API_KEY
  if (!key) {
    return NextResponse.json({ standings: {}, configured: false })
  }

  try {
    const res = await fetch(
      `${API_BASE}/competitions/${COMPETITION}/standings`,
      {
        headers: { "X-Auth-Token": key },
        next: { revalidate: 60 },
      }
    )

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`API ${res.status}: ${text.slice(0, 120)}`)
    }

    const data = await res.json()
    const standings: LiveGroupStandings = {}

    for (const group of data.standings ?? []) {
      // Only use TOTAL type (not HOME/AWAY splits)
      if (group.type !== "TOTAL") continue

      // football-data.org: group = "GROUP_A" | "GROUP_B" | ...
      const groupId: string = (group.group as string)?.replace("GROUP_", "")
      if (!groupId) continue

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      standings[groupId] = (group.table ?? []).map((row: any): LiveStanding => ({
        position:        row.position,
        team:            normalizeTeamName(row.team?.name ?? row.team?.shortName ?? ""),
        played:          row.playedGames ?? 0,
        won:             row.won ?? 0,
        drawn:           row.draw ?? 0,
        lost:            row.lost ?? 0,
        goalsFor:        row.goalsFor ?? 0,
        goalsAgainst:    row.goalsAgainst ?? 0,
        goalDifference:  row.goalDifference ?? 0,
        points:          row.points ?? 0,
      }))
    }

    cache = { data: standings, ts: Date.now() }
    return NextResponse.json({ standings, cached: false })

  } catch (err) {
    if (cache) {
      return NextResponse.json({ standings: cache.data, cached: true, stale: true })
    }
    return NextResponse.json({ standings: {}, error: String(err) }, { status: 200 })
  }
}
