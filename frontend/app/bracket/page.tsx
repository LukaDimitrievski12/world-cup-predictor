"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { getTeams, TeamProfile } from "@/lib/api"
import Flag from "@/components/Flag"
import MatchStatusBadge from "@/components/MatchStatusBadge"
import { loadQualified, seededBracket } from "@/lib/groups"
import { useTournament } from "@/context/TournamentContext"
import type { LiveMatch } from "@/lib/live-types"
import type { QualifiedMap } from "@/lib/groups"
import type { LiveGroupStandings } from "@/lib/live-types"

const EASE = [0.23, 1, 0.32, 1] as const

/* ── Types ───────────────────────────────────────────────────────*/

type Match = { team1: string | null; team2: string | null; winner: string | null }
type Round = "r32" | "r16" | "qf" | "sf" | "final"

const NEXT: Partial<Record<Round, Round>> = { r32: "r16", r16: "qf", qf: "sf", sf: "final" }
const ROUND_LABELS: Record<Round, string> = {
  r32: "R32", r16: "R16", qf: "QF", sf: "SF", final: "Final",
}

/* ── Default bracket seeds ───────────────────────────────────────*/

const SEEDED_R32: [string, string][] = [
  ["Brazil","Turkey"],           ["Morocco","United States"],
  ["France","Austria"],          ["Argentina","Senegal"],
  ["Germany","Japan"],           ["Netherlands","Ecuador"],
  ["Spain","Uruguay"],           ["England","Colombia"],
  ["Portugal","Croatia"],        ["Belgium","South Korea"],
  ["Mexico","Canada"],           ["Switzerland","Australia"],
  ["Egypt","Sweden"],            ["Côte d'Ivoire","Norway"],
  ["Czech Republic","Iran"],     ["Scotland","Algeria"],
]

function makeInitialBracket(): Record<Round, Match[]> {
  return {
    r32:   SEEDED_R32.map(([t1, t2]) => ({ team1: t1, team2: t2, winner: null })),
    r16:   Array.from({ length: 8 }, () => ({ team1: null, team2: null, winner: null })),
    qf:    Array.from({ length: 4 }, () => ({ team1: null, team2: null, winner: null })),
    sf:    Array.from({ length: 2 }, () => ({ team1: null, team2: null, winner: null })),
    final: [{ team1: null, team2: null, winner: null }],
  }
}

/* ── Build QualifiedMap from API group standings ─────────────────*/

function qualifiedFromStandings(gs: LiveGroupStandings): QualifiedMap {
  const qualified: QualifiedMap = {}
  const thirds: { team: string; pts: number; gd: number; gf: number }[] = []
  for (const [gid, table] of Object.entries(gs)) {
    if (table.length < 3) continue
    qualified[`${gid}1`] = table[0].team
    qualified[`${gid}2`] = table[1].team
    thirds.push({ team: table[2].team, pts: table[2].points, gd: table[2].goalDifference, gf: table[2].goalsFor })
  }
  thirds.sort((a, b) => (b.pts - a.pts) || (b.gd - a.gd) || (b.gf - a.gf))
  thirds.slice(0, 8).forEach((t, i) => { qualified[`3rd${i + 1}`] = t.team })
  return qualified
}

/* ── Elo helpers ─────────────────────────────────────────────────*/

function eloWinProb(a: number, b: number) { return 1 / (1 + Math.pow(10, (b - a) / 400)) }
function crowdProb(a: number, b: number) {
  const base = eloWinProb(a, b)
  const biased = (base * 1.2) / (base * 1.2 + (1 - base))
  return Math.max(0.05, Math.min(0.95, biased))
}
function popularityLabel(p: number): { label: string; color: string } {
  if (p >= 0.65) return { label: "Popular pick", color: "text-blue-600" }
  if (p >= 0.45) return { label: "Balanced",     color: "text-slate-500" }
  if (p >= 0.25) return { label: "Underdog",     color: "text-amber-600" }
  return               { label: "Rare pick",     color: "text-rose-600" }
}

/* ── MatchCard ───────────────────────────────────────────────────*/

function MatchCard({
  match, eloMap, onPick, isFinal = false, liveMatch,
}: {
  match: Match
  eloMap: Record<string, number>
  onPick: (team: string) => void
  isFinal?: boolean
  liveMatch?: LiveMatch    // if present, match has a real result
}) {
  const { team1, team2, winner } = match

  // In Live mode, real finished result takes precedence
  const isLocked  = !!liveMatch && liveMatch.status === "finished"
  const isLiveFeed = !!liveMatch && liveMatch.status === "live"
  const effectiveWinner = isLocked
    ? liveMatch!.homeScore! > liveMatch!.awayScore!
      ? liveMatch!.homeTeam
      : liveMatch!.awayTeam
    : winner

  const elo1   = team1 ? (eloMap[team1] ?? 1500) : 1500
  const elo2   = team2 ? (eloMap[team2] ?? 1500) : 1500
  const prob1  = team1 && team2 ? eloWinProb(elo1, elo2) : 0.5
  const crowd1 = team1 && team2 ? crowdProb(elo1, elo2)  : 0.5

  const teams = [
    { team: team1, prob: prob1,     crowd: crowd1 },
    { team: team2, prob: 1 - prob1, crowd: 1 - crowd1 },
  ]

  // Real scores for display (if live/finished)
  function realScoreFor(i: number) {
    if (!liveMatch || liveMatch.homeScore == null) return null
    const isHome = i === 0 ? liveMatch.homeTeam === team1 : liveMatch.homeTeam === team2
    return isHome ? liveMatch.homeScore : liveMatch.awayScore
  }

  return (
    <div className={`w-full overflow-hidden rounded-xl border bg-white transition-all duration-150 ${
      isFinal
        ? "border-amber-300 shadow-[0_4px_24px_rgba(245,158,11,0.2)]"
        : isLocked
        ? "border-slate-300 shadow-sm"
        : isLiveFeed
        ? "border-red-300 shadow-[0_0_12px_rgba(239,68,68,0.15)]"
        : "border-slate-200 shadow-sm hover:shadow-md hover:border-blue-200"
    }`}>
      {/* Live / locked header strip */}
      {(isLocked || isLiveFeed) && (
        <div className={`flex items-center justify-center gap-1.5 px-2 py-1 text-[10px] font-bold ${
          isLiveFeed ? "bg-red-500 text-white" : "bg-slate-100 text-slate-600"
        }`}>
          {isLiveFeed && <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />}
          {isLiveFeed ? (liveMatch!.minute ? `${liveMatch!.minute}'` : "LIVE") : "FT · Real result"}
        </div>
      )}

      {teams.map(({ team, crowd }, i) => {
        const isWinner = effectiveWinner === team
        const isLoser  = !!effectiveWinner && effectiveWinner !== team
        const { label: popLabel } = team && team2 && team1
          ? popularityLabel(i === 0 ? crowd : 1 - crowd1)
          : { label: "" }
        const score = realScoreFor(i)

        return (
          <button
            key={i}
            onClick={() => !isLocked && team && onPick(team)}
            disabled={!team || !team1 || !team2 || isLocked}
            title={team && team1 && team2
              ? `Model: ${((i === 0 ? prob1 : 1-prob1)*100).toFixed(0)}%  |  ${popLabel}`
              : undefined}
            className={`w-full flex items-center gap-2 px-2.5 py-2 text-left transition-all duration-150
              ${i === 0 ? "border-b" : ""}
              ${isWinner
                ? isFinal
                  ? "bg-gradient-to-r from-amber-50 to-yellow-50 border-amber-200"
                  : isLocked
                  ? "bg-gradient-to-r from-green-50 to-emerald-50"
                  : "bg-gradient-to-r from-blue-600 to-blue-700"
                : ""}
              ${isLoser ? "opacity-35 bg-slate-50" : ""}
              ${!effectiveWinner && team && team1 && team2 && !isLocked ? "hover:bg-blue-50 cursor-pointer" : "cursor-default"}
              ${i === 0 ? "border-slate-100" : ""}
            `}
          >
            {team ? (
              <>
                <Flag team={team} size="sm" />
                <span className={`flex-1 text-[11px] font-semibold truncate leading-tight ${
                  isWinner
                    ? isFinal ? "text-amber-800"
                      : isLocked ? "text-green-800"
                      : "text-white"
                    : "text-slate-800"
                }`}>
                  {team}
                </span>
                {/* Real score if available */}
                {score != null && (
                  <span className={`text-sm font-black tabular-nums shrink-0 ${
                    isWinner ? isLocked ? "text-green-700" : "text-blue-100" : "text-slate-600"
                  }`}>{score}</span>
                )}
                {/* Elo probability when no score */}
                {score == null && team1 && team2 && (
                  <span className={`text-[10px] font-mono tabular-nums shrink-0 ${
                    isWinner ? isFinal ? "text-amber-600" : "text-blue-100" : "text-slate-400"
                  }`}>
                    {((i === 0 ? prob1 : 1 - prob1) * 100).toFixed(0)}%
                  </span>
                )}
              </>
            ) : (
              <span className="text-[10px] text-slate-300 italic">TBD</span>
            )}
          </button>
        )
      })}
    </div>
  )
}

/* ── BracketColumn ───────────────────────────────────────────────*/

const SLOT_H = 64

function BracketColumn({
  round, matches, matchOffset, eloMap, onPick, roundIdx, liveMatches,
}: {
  round: Round
  matches: Match[]
  matchOffset: number
  eloMap: Record<string, number>
  onPick: (round: Round, idx: number, team: string) => void
  roundIdx: number
  liveMatches: LiveMatch[]
}) {
  const slotH = SLOT_H * Math.pow(2, roundIdx)

  return (
    <div className="flex flex-col shrink-0" style={{ width: 148 }}>
      <div className="text-center mb-2">
        <span className={`text-[10px] font-black uppercase tracking-[0.2em] ${
          round === "final" ? "text-amber-600" : "text-slate-500"
        }`}>
          {ROUND_LABELS[round]}
        </span>
      </div>
      {matches.map((match, localIdx) => {
        const lm = liveMatches.find(m =>
          m.stage === round &&
          match.team1 && match.team2 &&
          ((m.homeTeam === match.team1 && m.awayTeam === match.team2) ||
           (m.homeTeam === match.team2 && m.awayTeam === match.team1))
        )
        return (
          <div key={localIdx} style={{ height: slotH }} className="flex items-center">
            <MatchCard
              match={match}
              eloMap={eloMap}
              onPick={(team) => onPick(round, matchOffset + localIdx, team)}
              isFinal={round === "final"}
              liveMatch={lm}
            />
          </div>
        )
      })}
    </div>
  )
}

/* ── Sidebar ─────────────────────────────────────────────────────*/

function Sidebar({ bracket, eloMap }: { bracket: Record<Round, Match[]>; eloMap: Record<string, number> }) {
  const champion = bracket.final[0].winner
  const picks: { team: string; modelPct: number; crowdPct: number }[] = []

  for (const round of ["r32","r16","qf","sf","final"] as Round[]) {
    for (const match of bracket[round]) {
      if (!match.winner || !match.team1 || !match.team2) continue
      const isTeam1 = match.winner === match.team1
      const elo1 = eloMap[match.team1] ?? 1500
      const elo2 = eloMap[match.team2] ?? 1500
      picks.push({
        team: match.winner,
        modelPct: isTeam1 ? eloWinProb(elo1, elo2) : 1 - eloWinProb(elo1, elo2),
        crowdPct: isTeam1 ? crowdProb(elo1, elo2)  : 1 - crowdProb(elo1, elo2),
      })
    }
  }

  const totalPicks     = picks.length
  const underdogPicks  = picks.filter(p => p.modelPct < 0.45).length
  const avgCrowdPct    = totalPicks > 0 ? picks.reduce((a, p) => a + p.crowdPct, 0) / totalPicks : 0.5
  const uniqueness     = Math.round((1 - avgCrowdPct) * 100)
  const champElo       = champion ? (eloMap[champion] ?? 1500) : null

  const riskLabel =
    underdogPicks === 0 ? { label: "Safe",     color: "text-green-600", bg: "bg-green-50 border-green-200", desc: "You're backing the favourites." }
    : underdogPicks <= 2 ? { label: "Balanced", color: "text-blue-600",  bg: "bg-blue-50 border-blue-200",   desc: "Smart mix of safe and bold picks." }
    : underdogPicks <= 5 ? { label: "Bold",     color: "text-amber-600", bg: "bg-amber-50 border-amber-200", desc: "High risk, high upside bracket." }
    : { label: "Wild", color: "text-rose-600", bg: "bg-rose-50 border-rose-200", desc: "You're backing the dark horses!" }

  return (
    <div className="w-56 shrink-0 space-y-3">
      <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Your Bracket</h3>

      <AnimatePresence mode="wait">
        {champion ? (
          <motion.div
            key={champion}
            initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="card-gold rounded-2xl p-4 text-center"
          >
            <div className="text-2xl mb-2" style={{ animation: "float 2.5s ease-in-out infinite" }}>🏆</div>
            <div className="flex justify-center mb-2"><Flag team={champion} size="lg" /></div>
            <div className="font-black text-slate-900 text-sm">{champion}</div>
            {champElo && <div className="text-[10px] text-amber-700 mt-0.5">Elo {Math.round(champElo)}</div>}
          </motion.div>
        ) : (
          <div className="card rounded-2xl p-4 text-center border-dashed border-2 border-slate-200 bg-slate-50">
            <div className="text-2xl mb-1 opacity-30">🏆</div>
            <div className="text-xs text-slate-500">Pick your winner</div>
          </div>
        )}
      </AnimatePresence>

      {totalPicks > 0 && (
        <div className="space-y-2">
          <div className={`rounded-xl border p-3 ${riskLabel.bg}`}>
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-[10px] font-bold text-slate-600">Risk Level</span>
              <span className={`text-xs font-black ${riskLabel.color}`}>{riskLabel.label}</span>
            </div>
            <p className="text-xs text-slate-600">{riskLabel.desc}</p>
          </div>
          <div className="card rounded-xl p-3">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold text-slate-600">Uniqueness</span>
              <span className="text-xs font-black text-blue-600">{uniqueness}%</span>
            </div>
            <div className="prob-bar">
              <div className="prob-fill-blue" style={{ width: `${uniqueness}%`, transition: "width 0.6s ease" }} />
            </div>
            <p className="text-xs text-slate-500 mt-1">More unique than {uniqueness}% of fans</p>
          </div>
          <div className="card rounded-xl p-3 space-y-1.5">
            <span className="text-[10px] font-bold text-slate-600 block">Your Picks ({totalPicks})</span>
            <div className="flex justify-between text-xs">
              <span className="text-slate-600">Favourites</span>
              <span className="font-semibold text-green-600">{totalPicks - underdogPicks}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-600">Underdogs</span>
              <span className={`font-semibold ${underdogPicks > 0 ? "text-amber-600" : "text-slate-500"}`}>{underdogPicks}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Main page ───────────────────────────────────────────────────*/

export default function BracketPage() {
  const { mode, matches, groupStandings, hasLiveData, isLoading } = useTournament()
  const isLiveMode = mode === "live"

  const [bracket, setBracket]     = useState<Record<Round, Match[]>>(makeInitialBracket)
  const [eloMap, setEloMap]       = useState<Record<string, number>>({})
  const [fromGroups, setFromGroups] = useState(false)
  const [fromLive, setFromLive]   = useState(false)

  // Seed R32 from user's group-stage predictions (localStorage)
  useEffect(() => {
    const qualified = loadQualified()
    if (qualified && Object.keys(qualified).length > 0) {
      setBracket(prev => ({
        ...prev,
        r32:   seededBracket(qualified),
        r16:   Array.from({ length: 8 }, () => ({ team1: null, team2: null, winner: null })),
        qf:    Array.from({ length: 4 }, () => ({ team1: null, team2: null, winner: null })),
        sf:    Array.from({ length: 2 }, () => ({ team1: null, team2: null, winner: null })),
        final: [{ team1: null, team2: null, winner: null }],
      }))
      setFromGroups(true)
    }
  }, [])

  // In Live mode, auto-seed from real standings when all 12 groups have data
  useEffect(() => {
    if (!isLiveMode || !hasLiveData) return
    const groupsComplete = Object.keys(groupStandings).length === 12
    if (!groupsComplete) return
    const qualified = qualifiedFromStandings(groupStandings)
    if (Object.keys(qualified).length < 32) return  // incomplete — not all groups settled yet
    setBracket(prev => ({
      ...prev,
      r32:   seededBracket(qualified),
      r16:   Array.from({ length: 8 }, () => ({ team1: null, team2: null, winner: null })),
      qf:    Array.from({ length: 4 }, () => ({ team1: null, team2: null, winner: null })),
      sf:    Array.from({ length: 2 }, () => ({ team1: null, team2: null, winner: null })),
      final: [{ team1: null, team2: null, winner: null }],
    }))
    setFromLive(true)
    setFromGroups(false)
  }, [isLiveMode, hasLiveData, groupStandings])

  useEffect(() => {
    getTeams().then((teams: TeamProfile[]) => {
      const map: Record<string, number> = {}
      teams.forEach(t => { map[t.team] = t.elo })
      setEloMap(map)
    }).catch(() => {})
  }, [])

  const clearDownstream = useCallback((
    draft: Record<Round, Match[]>, round: Round, matchIdx: number, oldTeam: string
  ) => {
    const m = draft[round][matchIdx]
    if (!m) return
    if (m.team1 === oldTeam) m.team1 = null
    if (m.team2 === oldTeam) m.team2 = null
    if (m.winner === oldTeam) {
      m.winner = null
      const nxt = NEXT[round]
      if (nxt) clearDownstream(draft, nxt, Math.floor(matchIdx / 2), oldTeam)
    }
  }, [])

  const pickWinner = useCallback((round: Round, matchIdx: number, team: string) => {
    setBracket(prev => {
      const next: Record<Round, Match[]> = JSON.parse(JSON.stringify(prev))
      const old = next[round][matchIdx].winner
      if (old && old !== team) {
        const nxt = NEXT[round]
        if (nxt) clearDownstream(next, nxt, Math.floor(matchIdx / 2), old)
      }
      next[round][matchIdx].winner = team
      const nxt = NEXT[round]
      if (nxt) {
        const slot = matchIdx % 2 === 0 ? "team1" : "team2"
        next[nxt][Math.floor(matchIdx / 2)][slot] = team
      }
      return next
    })
  }, [clearDownstream])

  const resetBracket = () => { setBracket(makeInitialBracket()); setFromGroups(false); setFromLive(false) }

  function resetToGroups() {
    const qualified = loadQualified()
    if (!qualified) return
    setBracket({
      r32:   seededBracket(qualified),
      r16:   Array.from({ length: 8 }, () => ({ team1: null, team2: null, winner: null })),
      qf:    Array.from({ length: 4 }, () => ({ team1: null, team2: null, winner: null })),
      sf:    Array.from({ length: 2 }, () => ({ team1: null, team2: null, winner: null })),
      final: [{ team1: null, team2: null, winner: null }],
    })
    setFromGroups(true)
    setFromLive(false)
  }

  // Knockout live matches from context
  const knockoutMatches = useMemo(
    () => matches.filter(m => m.stage !== "group"),
    [matches]
  )

  const leftR32  = bracket.r32.slice(0, 8)
  const rightR32 = bracket.r32.slice(8)
  const leftR16  = bracket.r16.slice(0, 4)
  const rightR16 = bracket.r16.slice(4)
  const leftQF   = bracket.qf.slice(0, 2)
  const rightQF  = bracket.qf.slice(2)

  return (
    <div className="space-y-6">

      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="flex items-end justify-between"
      >
        <div>
          <p className="text-blue-600 text-[11px] font-black uppercase tracking-[0.25em] mb-2">⚡ Bracket Predictor</p>
          <h1 className="text-4xl font-black tracking-tight text-slate-900 mb-1">
            Build Your <span className="shimmer-text">Bracket</span>
          </h1>
          <p className="text-slate-600 text-sm">
            {isLiveMode
              ? "Live mode: real results shown in green. Predict the remaining rounds."
              : "Click a team to advance them. Win probabilities from our ML model."}
          </p>
        </div>
        <button onClick={resetBracket} className="text-xs font-semibold text-slate-500 hover:text-slate-700 transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-100">
          Reset ↺
        </button>
      </motion.div>

      <div className="gradient-divider" />

      {/* Source banners */}
      <AnimatePresence>
        {fromLive && isLiveMode && (
          <motion.div
            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="flex items-center gap-3 px-4 py-2.5 bg-green-50 border border-green-200 rounded-xl"
          >
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse shrink-0" />
            <span className="text-green-700 text-xs font-medium">
              Bracket auto-seeded from real group standings
              {knockoutMatches.filter(m => m.status === "finished").length > 0
                ? ` · ${knockoutMatches.filter(m => m.status === "finished").length} knockout results locked`
                : ""}
            </span>
            <button onClick={resetBracket} className="ml-auto text-xs text-green-500 hover:text-green-700 font-semibold transition-colors">
              Use defaults
            </button>
          </motion.div>
        )}
        {fromGroups && !fromLive && (
          <motion.div
            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-xl"
          >
            <span className="text-blue-600 font-bold text-sm">✓</span>
            <span className="text-blue-700 text-xs font-medium">Bracket seeded from your group stage predictions</span>
            <button onClick={resetToGroups} className="ml-auto text-xs text-blue-500 hover:text-blue-700 font-semibold transition-colors">
              Re-seed
            </button>
            <button onClick={resetBracket} className="text-xs text-slate-400 hover:text-slate-600 font-semibold transition-colors">
              Defaults
            </button>
          </motion.div>
        )}
        {isLiveMode && isLoading && !fromLive && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2 px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-500"
          >
            <svg className="w-3 h-3 animate-spin shrink-0" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            Loading live standings to auto-seed bracket…
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bracket + Sidebar */}
      <div className="flex gap-5 items-start">
        <div className="flex-1 overflow-x-auto pb-3">
          <div className="flex items-start gap-2 min-w-max">

            {[
              { round: "r32" as Round, matches: leftR32,  offset: 0, idx: 0 },
              { round: "r16" as Round, matches: leftR16,  offset: 0, idx: 1 },
              { round: "qf"  as Round, matches: leftQF,   offset: 0, idx: 2 },
              { round: "sf"  as Round, matches: [bracket.sf[0]], offset: 0, idx: 3 },
            ].map(({ round, matches: ms, offset, idx }) => (
              <BracketColumn
                key={`left-${round}`}
                round={round} matches={ms} matchOffset={offset}
                eloMap={eloMap} onPick={pickWinner} roundIdx={idx}
                liveMatches={knockoutMatches}
              />
            ))}

            {/* Final */}
            <div className="shrink-0 flex flex-col" style={{ width: 160 }}>
              <div className="text-center mb-2">
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-amber-600">Final</span>
              </div>
              <div style={{ height: SLOT_H * 8 }} className="flex items-center">
                <MatchCard
                  match={bracket.final[0]}
                  eloMap={eloMap}
                  onPick={(team) => pickWinner("final", 0, team)}
                  isFinal
                  liveMatch={knockoutMatches.find(m => m.stage === "final")}
                />
              </div>
            </div>

            {[
              { round: "sf"  as Round, matches: [bracket.sf[1]], offset: 1, idx: 3 },
              { round: "qf"  as Round, matches: rightQF,  offset: 2, idx: 2 },
              { round: "r16" as Round, matches: rightR16, offset: 4, idx: 1 },
              { round: "r32" as Round, matches: rightR32, offset: 8, idx: 0 },
            ].map(({ round, matches: ms, offset, idx }) => (
              <BracketColumn
                key={`right-${round}`}
                round={round} matches={ms} matchOffset={offset}
                eloMap={eloMap} onPick={pickWinner} roundIdx={idx}
                liveMatches={knockoutMatches}
              />
            ))}

          </div>
        </div>

        <Sidebar bracket={bracket} eloMap={eloMap} />
      </div>

      {/* Legend */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5, duration: 0.3 }}
        className="flex items-center gap-4 pt-2 border-t border-slate-200 flex-wrap"
      >
        <span className="text-xs text-slate-600 font-semibold uppercase tracking-widest">Model %</span>
        {[
          { range: "≥ 65%",  color: "bg-blue-100 text-blue-700",   label: "Popular pick" },
          { range: "45–65%", color: "bg-slate-100 text-slate-600", label: "Balanced" },
          { range: "25–45%", color: "bg-amber-100 text-amber-700", label: "Underdog" },
          { range: "< 25%",  color: "bg-rose-100 text-rose-700",   label: "Rare pick" },
        ].map(({ range, color, label }) => (
          <span key={label} className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}>
            {label} <span className="opacity-60">{range}</span>
          </span>
        ))}
        {isLiveMode && (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-700 ml-2">
            Green border = real result locked
          </span>
        )}
      </motion.div>

    </div>
  )
}
