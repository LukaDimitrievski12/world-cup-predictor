// Server-side proxy for football-data.org match data.
// The API key never leaves the server. All users share one server-side cache.

import { NextResponse } from "next/server"
import { normalizeMatch } from "@/lib/live-normalize"
import type { LiveMatch } from "@/lib/live-types"

const API_BASE   = "https://api.football-data.org/v4"
const COMPETITION = "WC"   // FIFA World Cup code on football-data.org
const CACHE_TTL  = 60_000  // 1 minute — respects free-tier rate limit (10 req/min)

// Module-level cache: all Next.js requests share it within a server process
let cache: { data: LiveMatch[]; ts: number } | null = null

export async function GET() {
  // Serve from cache if still fresh
  if (cache && Date.now() - cache.ts < CACHE_TTL) {
    return NextResponse.json({ matches: cache.data, cached: true })
  }

  const key = process.env.FOOTBALL_API_KEY
  if (!key) {
    // No API key configured — return empty payload; client falls back gracefully
    return NextResponse.json({ matches: [], configured: false })
  }

  try {
    const res = await fetch(
      `${API_BASE}/competitions/${COMPETITION}/matches`,
      {
        headers: { "X-Auth-Token": key },
        // Next.js fetch cache: revalidate every 60 s at the HTTP level too
        next: { revalidate: 60 },
      }
    )

    if (!res.ok) {
      // football-data.org 429 = rate limited, 403 = bad key
      const text = await res.text()
      throw new Error(`API ${res.status}: ${text.slice(0, 120)}`)
    }

    const data = await res.json()
    const matches: LiveMatch[] = (data.matches ?? []).map(normalizeMatch)

    cache = { data: matches, ts: Date.now() }
    return NextResponse.json({ matches, cached: false })

  } catch (err) {
    // Serve stale cache rather than breaking the UI
    if (cache) {
      return NextResponse.json({ matches: cache.data, cached: true, stale: true })
    }
    return NextResponse.json(
      { matches: [], error: String(err) },
      { status: 200 }   // always 200 so the client doesn't crash
    )
  }
}
