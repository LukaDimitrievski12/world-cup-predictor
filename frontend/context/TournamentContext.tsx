"use client"

import {
  createContext, useContext, useState, useEffect,
  useCallback, useRef, type ReactNode,
} from "react"
import { fetchTournamentData } from "@/lib/live-api"
import type {
  LiveMatch, LiveGroupStandings, TournamentMode, TournamentContextValue,
} from "@/lib/live-types"

// ── Polling intervals ────────────────────────────────────────────
const POLL_LIVE    = 30_000   // 30 s when a match is in progress
const POLL_IDLE    = 60_000   // 60 s otherwise

// ── Context ─────────────────────────────────────────────────────

const TournamentContext = createContext<TournamentContextValue>({
  mode:               "simulation",
  setMode:            () => {},
  matches:            [],
  groupStandings:     {},
  lastUpdated:        null,
  isLoading:          false,
  error:              null,
  hasLiveData:        false,
  isLiveMatchActive:  false,
  getLiveGroupMatch:  () => undefined,
  getLiveKnockoutMatch: () => undefined,
  refresh:            () => {},
})

// ── Provider ─────────────────────────────────────────────────────

export function TournamentProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState]           = useState<TournamentMode>("simulation")
  const [matches, setMatches]          = useState<LiveMatch[]>([])
  const [groupStandings, setStandings] = useState<LiveGroupStandings>({})
  const [lastUpdated, setLastUpdated]  = useState<Date | null>(null)
  const [isLoading, setIsLoading]      = useState(false)
  const [error, setError]              = useState<string | null>(null)
  const [isConfigured, setIsConfigured]= useState(true)

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const modeRef  = useRef(mode)
  modeRef.current = mode

  // Persist mode in localStorage
  function setMode(m: TournamentMode) {
    setModeState(m)
    try { localStorage.setItem("wc2026_mode", m) } catch {}
  }

  // Core fetch function — called on mount and on each poll tick
  const fetchData = useCallback(async () => {
    if (modeRef.current !== "live") return
    setIsLoading(true)
    try {
      const data = await fetchTournamentData()
      setIsConfigured(data.isConfigured)
      if (data.matches.length > 0) setMatches(data.matches)
      if (Object.keys(data.standings).length > 0) setStandings(data.standings)
      setLastUpdated(new Date())
      setError(data.error)
    } catch (e) {
      setError(String(e))
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Self-adjusting poll: faster when a match is live
  const schedulePoll = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    if (modeRef.current !== "live") return
    const hasLive = matches.some(m => m.status === "live")
    timerRef.current = setTimeout(async () => {
      await fetchData()
      schedulePoll()   // reschedule after each fetch
    }, hasLive ? POLL_LIVE : POLL_IDLE)
  }, [fetchData, matches])

  // Load saved mode on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("wc2026_mode")
      if (saved === "live" || saved === "simulation") setModeState(saved)
    } catch {}
  }, [])

  // Start / stop polling when mode changes
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    if (mode !== "live") return
    fetchData()         // immediate fetch when switching to live
    schedulePoll()
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [mode])   // intentionally only mode as dep — fetchData/schedulePoll are stable

  // Re-schedule after match data changes (so interval adjusts to live/idle)
  useEffect(() => {
    if (mode === "live") schedulePoll()
  }, [matches, mode])   // eslint-disable-line react-hooks/exhaustive-deps

  // ── Helpers ─────────────────────────────────────────────────

  const getLiveGroupMatch = useCallback(
    (group: string, home: string, away: string): LiveMatch | undefined =>
      matches.find(m =>
        m.group === group &&
        ((m.homeTeam === home && m.awayTeam === away) ||
         (m.homeTeam === away && m.awayTeam === home))
      ),
    [matches]
  )

  const getLiveKnockoutMatch = useCallback(
    (team1: string | null, team2: string | null): LiveMatch | undefined => {
      if (!team1 || !team2) return undefined
      return matches.find(m =>
        m.stage !== "group" &&
        ((m.homeTeam === team1 && m.awayTeam === team2) ||
         (m.homeTeam === team2 && m.awayTeam === team1))
      )
    },
    [matches]
  )

  const hasLiveData        = isConfigured && matches.length > 0
  const isLiveMatchActive  = matches.some(m => m.status === "live")

  return (
    <TournamentContext.Provider value={{
      mode, setMode,
      matches, groupStandings,
      lastUpdated, isLoading, error,
      hasLiveData, isLiveMatchActive,
      getLiveGroupMatch, getLiveKnockoutMatch,
      refresh: fetchData,
    }}>
      {children}
    </TournamentContext.Provider>
  )
}

export function useTournament(): TournamentContextValue {
  return useContext(TournamentContext)
}
