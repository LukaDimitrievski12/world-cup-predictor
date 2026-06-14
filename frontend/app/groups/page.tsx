"use client"

import { useState, useMemo, useEffect } from "react"
import { useRouter } from "next/navigation"
import { motion, LayoutGroup } from "framer-motion"
import {
  GROUP_IDS, GroupId, WC2026_GROUPS, groupFixtures,
  Score, TeamStats, calcStandings, getQualified,
  saveGroupScores, loadGroupScores, saveQualified,
} from "@/lib/groups"
import { useTournament } from "@/context/TournamentContext"
import type { LiveMatch, LiveStanding } from "@/lib/live-types"
import Flag from "@/components/Flag"
import MatchStatusBadge from "@/components/MatchStatusBadge"

const EASE = [0.23, 1, 0.32, 1] as const

/* ── Helpers ─────────────────────────────────────────────────────*/

// Convert API LiveStanding → our TeamStats shape
function liveToStats(ls: LiveStanding): TeamStats {
  return {
    team: ls.team,
    p: ls.played,
    w: ls.won,
    d: ls.drawn,
    l: ls.lost,
    gf: ls.goalsFor,
    ga: ls.goalsAgainst,
    gd: ls.goalDifference,
    pts: ls.points,
  }
}

/* ── MatchRow — editable OR locked (real result) ─────────────────*/

function MatchRow({
  home, away, score, onChange, liveMatch, isLiveMode,
}: {
  home: string
  away: string
  score: Score | null
  onChange: (s: Score | null) => void
  liveMatch?: LiveMatch
  isLiveMode: boolean
}) {
  const locked = isLiveMode && !!liveMatch &&
    (liveMatch.status === "finished" || liveMatch.status === "live")

  // Real score in home/away perspective (API may have teams swapped)
  const realScore: Score | null = locked && liveMatch
    ? liveMatch.homeTeam === home
      ? { h: liveMatch.homeScore ?? 0, a: liveMatch.awayScore ?? 0 }
      : { h: liveMatch.awayScore ?? 0, a: liveMatch.homeScore ?? 0 }
    : null

  const displayScore = realScore ?? score
  const outcome = displayScore == null ? null
    : displayScore.h > displayScore.a ? "H"
    : displayScore.h < displayScore.a ? "A" : "D"

  function handleChange(field: "h" | "a", raw: string) {
    const n = Math.max(0, Math.min(20, parseInt(raw.replace(/\D/, "")) || 0))
    const cur = score ?? { h: 0, a: 0 }
    onChange(field === "h" ? { ...cur, h: n } : { ...cur, a: n })
  }

  // ── Locked / real result display ──
  if (locked && realScore && liveMatch) {
    return (
      <div className={`flex items-center gap-1.5 py-1.5 border-b border-slate-100 last:border-0 ${
        liveMatch.status === "live" ? "bg-red-50/40" : ""
      }`}>
        {/* Home */}
        <div className="flex items-center gap-1 flex-1 min-w-0 justify-end">
          <span className={`text-xs truncate font-semibold ${
            outcome === "H" ? "text-blue-700" : "text-slate-600"
          }`}>{home}</span>
          <Flag team={home} size="sm" />
        </div>

        {/* Score */}
        <div className="flex items-center gap-1 shrink-0">
          <span className={`w-7 h-6 flex items-center justify-center text-sm font-black rounded ${
            outcome === "H" ? "bg-blue-100 text-blue-800" : "bg-slate-100 text-slate-700"
          }`}>{realScore.h}</span>
          <span className="text-slate-400 text-xs font-bold">–</span>
          <span className={`w-7 h-6 flex items-center justify-center text-sm font-black rounded ${
            outcome === "A" ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-700"
          }`}>{realScore.a}</span>
        </div>

        {/* Away */}
        <div className="flex items-center gap-1 flex-1 min-w-0">
          <Flag team={away} size="sm" />
          <span className={`text-xs truncate font-semibold ${
            outcome === "A" ? "text-green-700" : "text-slate-600"
          }`}>{away}</span>
        </div>

        {/* Status badge */}
        <MatchStatusBadge status={liveMatch.status} minute={liveMatch.minute} />
      </div>
    )
  }

  // ── Editable input row (unchanged from before) ──
  return (
    <div className="flex items-center gap-1 py-1.5 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-1 flex-1 min-w-0 justify-end">
        <span className={`text-xs truncate ${outcome === "H" ? "font-bold text-blue-700" : "text-slate-600"}`}>
          {home}
        </span>
        <Flag team={home} size="sm" />
      </div>

      <div className="flex items-center gap-0.5 shrink-0">
        <input
          type="text" inputMode="numeric" maxLength={2}
          value={score?.h ?? ""}
          placeholder="–"
          onFocus={() => { if (!score) onChange({ h: 0, a: 0 }) }}
          onChange={e => handleChange("h", e.target.value)}
          className={`w-7 h-6 text-center text-xs font-bold rounded focus:outline-none transition-colors ${
            score != null
              ? "border border-blue-300 bg-white text-slate-800"
              : "border border-slate-200 bg-slate-50 text-slate-400"
          }`}
        />
        <span className="text-slate-400 text-xs px-0.5 font-bold">–</span>
        <input
          type="text" inputMode="numeric" maxLength={2}
          value={score?.a ?? ""}
          placeholder="–"
          onFocus={() => { if (!score) onChange({ h: 0, a: 0 }) }}
          onChange={e => handleChange("a", e.target.value)}
          className={`w-7 h-6 text-center text-xs font-bold rounded focus:outline-none transition-colors ${
            score != null
              ? "border border-blue-300 bg-white text-slate-800"
              : "border border-slate-200 bg-slate-50 text-slate-400"
          }`}
        />
      </div>

      <div className="flex items-center gap-1 flex-1 min-w-0">
        <Flag team={away} size="sm" />
        <span className={`text-xs truncate ${outcome === "A" ? "font-bold text-green-700" : "text-slate-600"}`}>
          {away}
        </span>
      </div>

      <div className="flex gap-0.5 shrink-0">
        {(["H","D","A"] as const).map(o => (
          <button
            key={o}
            onClick={() => onChange(o === "H" ? {h:1,a:0} : o === "D" ? {h:0,a:0} : {h:0,a:1})}
            className={`w-5 h-5 rounded text-[10px] font-black transition-all ${
              outcome === o
                ? o === "H" ? "bg-blue-500 text-white"
                  : o === "D" ? "bg-slate-500 text-white"
                  : "bg-green-500 text-white"
                : "bg-slate-100 text-slate-500 hover:bg-slate-200"
            }`}
          >{o}</button>
        ))}
        {score != null && (
          <button
            onClick={() => onChange(null)}
            className="w-5 h-5 rounded text-xs text-slate-400 hover:text-red-400 hover:bg-red-50 transition-all"
          >×</button>
        )}
      </div>
    </div>
  )
}

/* ── Group card ───────────────────────────────────────────────── */

const GROUP_COLORS: Record<GroupId, string> = {
  A:"from-blue-50",   B:"from-indigo-50", C:"from-green-50",
  D:"from-sky-50",    E:"from-orange-50", F:"from-violet-50",
  G:"from-red-50",    H:"from-amber-50",  I:"from-cyan-50",
  J:"from-emerald-50",K:"from-rose-50",   L:"from-purple-50",
}

function GroupCard({
  groupId, standings, fixtures, scores, bestThirds, onScore,
  liveMatches, isLiveMode,
}: {
  groupId: GroupId
  standings: TeamStats[]
  fixtures: [string, string][]
  scores: (Score | null)[]
  bestThirds: Set<string>
  onScore: (idx: number, score: Score | null) => void
  liveMatches: LiveMatch[]
  isLiveMode: boolean
}) {
  const [open, setOpen] = useState(true)
  const matchesPlayed = scores.filter(Boolean).length

  // Count locked (real) matches in live mode
  const lockedCount = isLiveMode
    ? liveMatches.filter(m => m.status === "finished" || m.status === "live").length
    : 0

  return (
    <div className="card rounded-2xl overflow-hidden">
      {/* Header */}
      <div className={`px-3 py-2.5 border-b border-slate-100 bg-gradient-to-r ${GROUP_COLORS[groupId]} to-white flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-blue-600 flex items-center justify-center shadow-sm">
            <span className="text-white text-[11px] font-black">{groupId}</span>
          </div>
          <span className="text-xs font-bold text-slate-700">Group {groupId}</span>
          {isLiveMode && lockedCount > 0 && (
            <span className="text-[9px] font-bold bg-green-100 text-green-700 px-1.5 py-0.5 rounded-md">
              {lockedCount} real
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium">
            {isLiveMode ? `${lockedCount}/6` : `${matchesPlayed}/6`}
          </span>
          <button
            onClick={() => setOpen(v => !v)}
            className="text-xs text-slate-500 hover:text-slate-700 font-semibold px-1.5 py-0.5 rounded hover:bg-white/60 transition-all"
          >
            {open ? "▲" : "▼"}
          </button>
        </div>
      </div>

      <div className="px-3 pt-2 pb-3">
        {/* Standings table */}
        <div className="mb-2">
          <div className="flex items-center gap-1 pb-1 text-[10px] text-slate-500 font-bold uppercase tracking-wide">
            <div className="w-4" />
            <div className="flex-1">Team</div>
            <div className="w-4 text-center">P</div>
            <div className="w-4 text-center">W</div>
            <div className="w-4 text-center">D</div>
            <div className="w-4 text-center">L</div>
            <div className="w-6 text-center">GD</div>
            <div className="w-6 text-center text-blue-600">Pts</div>
          </div>

          <LayoutGroup id={`group-${groupId}`}>
            {standings.map((row, i) => {
              const qualifies = i < 2
              const isBest3   = i === 2 && bestThirds.has(row.team)
              return (
                <motion.div
                  key={row.team}
                  layoutId={`${groupId}-${row.team}`}
                  layout="position"
                  transition={{ duration: 0.32, ease: EASE }}
                  className={`flex items-center gap-1 rounded-md py-1 px-0.5 transition-colors ${
                    qualifies ? "bg-blue-50" : isBest3 ? "bg-amber-50/70" : ""
                  }`}
                >
                  <div className="w-4 shrink-0">
                    <span className={`inline-flex w-3.5 h-3.5 rounded-full items-center justify-center text-[7px] font-black ${
                      qualifies ? "bg-blue-500 text-white"
                      : isBest3 ? "bg-amber-400 text-white"
                      : "text-slate-400"
                    }`}>{i + 1}</span>
                  </div>
                  <div className="flex-1 flex items-center gap-1 min-w-0">
                    <Flag team={row.team} size="sm" />
                    <span className={`text-xs truncate leading-tight ${qualifies ? "font-bold text-slate-800" : "text-slate-700"}`}>
                      {row.team}
                    </span>
                  </div>
                  <div className="w-4 text-center text-xs text-slate-600">{row.p}</div>
                  <div className="w-4 text-center text-xs text-slate-600">{row.w}</div>
                  <div className="w-4 text-center text-xs text-slate-600">{row.d}</div>
                  <div className="w-4 text-center text-xs text-slate-600">{row.l}</div>
                  <div className={`w-6 text-center text-xs font-semibold ${row.gd > 0 ? "text-green-600" : row.gd < 0 ? "text-red-500" : "text-slate-500"}`}>
                    {row.gd > 0 ? `+${row.gd}` : row.gd}
                  </div>
                  <div className={`w-6 text-center text-sm font-black ${qualifies ? "text-blue-700" : "text-slate-700"}`}>
                    {row.pts}
                  </div>
                </motion.div>
              )
            })}
          </LayoutGroup>
        </div>

        {/* Fixtures */}
        {open && (
          <div className="border-t border-slate-100 pt-2">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Fixtures</div>
            {fixtures.map(([home, away], idx) => {
              const lm = liveMatches.find(m =>
                (m.homeTeam === home && m.awayTeam === away) ||
                (m.homeTeam === away && m.awayTeam === home)
              )
              return (
                <MatchRow
                  key={idx}
                  home={home}
                  away={away}
                  score={scores[idx]}
                  onChange={s => onScore(idx, s)}
                  liveMatch={lm}
                  isLiveMode={isLiveMode}
                />
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Main page ───────────────────────────────────────────────────*/

const EMPTY_SCORES = () =>
  Object.fromEntries(GROUP_IDS.map(g => [g, Array<Score | null>(6).fill(null)])) as Record<GroupId, (Score | null)[]>

export default function GroupsPage() {
  const router = useRouter()
  const { mode, matches, groupStandings, lastUpdated, isLoading, error, hasLiveData } = useTournament()
  const isLiveMode = mode === "live"

  const [scores, setScores] = useState<Record<GroupId, (Score | null)[]>>(EMPTY_SCORES)

  useEffect(() => {
    const saved = loadGroupScores()
    if (saved) setScores(saved)
  }, [])

  useEffect(() => { saveGroupScores(scores) }, [scores])

  const allFixtures = useMemo(
    () => Object.fromEntries(GROUP_IDS.map(g => [g, groupFixtures(WC2026_GROUPS[g])])) as Record<GroupId, [string, string][]>,
    []
  )

  // Get effective score: real data (locked) takes precedence over user input in Live mode
  const getEffectiveScore = useMemo(() => {
    return (gid: GroupId, idx: number): Score | null => {
      if (isLiveMode) {
        const [home, away] = allFixtures[gid][idx]
        const lm = matches.find(m =>
          m.group === gid &&
          ((m.homeTeam === home && m.awayTeam === away) ||
           (m.homeTeam === away && m.awayTeam === home))
        )
        if (lm && (lm.status === "finished" || lm.status === "live")) {
          const isSwapped = lm.homeTeam === away
          return {
            h: isSwapped ? (lm.awayScore ?? 0) : (lm.homeScore ?? 0),
            a: isSwapped ? (lm.homeScore ?? 0) : (lm.awayScore ?? 0),
          }
        }
      }
      return scores[gid][idx]
    }
  }, [isLiveMode, matches, scores, allFixtures])

  // Standings: prefer API standings in Live mode, fall back to calculated
  const standings = useMemo(() => {
    return Object.fromEntries(
      GROUP_IDS.map(gid => {
        if (isLiveMode && groupStandings[gid]?.length > 0) {
          return [gid, groupStandings[gid].map(liveToStats)]
        }
        const effectiveScores = allFixtures[gid].map((_, idx) => getEffectiveScore(gid, idx))
        return [gid, calcStandings(WC2026_GROUPS[gid], allFixtures[gid], effectiveScores)]
      })
    ) as Record<GroupId, TeamStats[]>
  }, [isLiveMode, groupStandings, allFixtures, getEffectiveScore])

  const bestThirds = useMemo(() => {
    const thirds = GROUP_IDS.map(g => standings[g][2])
    thirds.sort((a, b) => (b.pts - a.pts) || (b.gd - a.gd) || (b.gf - a.gf))
    return new Set(thirds.slice(0, 8).map(t => t.team))
  }, [standings])

  // In Live mode, count real finished matches; in sim mode, count user entries
  const matchesPlayed = useMemo(() => {
    if (isLiveMode) {
      return matches.filter(m => m.group !== null && m.status === "finished").length
    }
    return GROUP_IDS.reduce((n, g) => n + scores[g].filter(Boolean).length, 0)
  }, [isLiveMode, matches, scores])

  function setScore(gid: GroupId, idx: number, score: Score | null) {
    setScores(prev => ({ ...prev, [gid]: prev[gid].map((s, i) => i === idx ? score : s) }))
  }

  function advanceToBracket() {
    // In Live mode, build qualified map from real/effective standings
    const effectiveAllScores = Object.fromEntries(
      GROUP_IDS.map(gid => [
        gid,
        allFixtures[gid].map((_, idx) => getEffectiveScore(gid, idx))
      ])
    ) as Record<GroupId, (Score | null)[]>
    const qualified = getQualified(effectiveAllScores)
    saveQualified(qualified)
    router.push("/bracket")
  }

  function resetAll() { setScores(EMPTY_SCORES()) }

  return (
    <div className="space-y-7">

      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: EASE }}>
        <p className="text-blue-600 text-[11px] font-black tracking-[0.25em] uppercase mb-3">🏟️ Group Stage</p>
        <h1 className="text-4xl font-black tracking-tight text-slate-900 mb-2">
          Predict the <span className="shimmer-text">Groups</span>
        </h1>
        <p className="text-slate-600 text-sm max-w-xl">
          {isLiveMode
            ? "Live mode: real results are locked in. You can still predict unplayed matches."
            : "Fill in match scores (or use H / D / A quick picks). Standings update live."}
        </p>
        <div className="gradient-divider mt-6" />
      </motion.div>

      {/* Live data status banner */}
      {isLiveMode && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-xs font-medium border ${
            hasLiveData
              ? "bg-green-50 border-green-200 text-green-700"
              : error
              ? "bg-red-50 border-red-200 text-red-700"
              : "bg-blue-50 border-blue-200 text-blue-700"
          }`}
        >
          {isLoading
            ? <><svg className="w-3 h-3 animate-spin shrink-0" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" /></svg> Fetching live data…</>
            : hasLiveData
            ? <><span className="w-2 h-2 rounded-full bg-green-500 shrink-0" /> Live data connected · {matchesPlayed} matches played{lastUpdated ? ` · updated ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : ""}</>
            : error
            ? <><span className="w-2 h-2 rounded-full bg-red-500 shrink-0" /> Live data unavailable · {error.includes("configured") ? "add FOOTBALL_API_KEY to .env.local" : "check connection"}</>
            : <><span className="w-2 h-2 rounded-full bg-blue-500 shrink-0 animate-pulse" /> Connecting to live data…</>
          }
        </motion.div>
      )}

      {/* Progress + controls */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs text-slate-700">
          <span className="font-semibold tabular-nums">{matchesPlayed}/72</span>
          <div className="w-36 bg-slate-200 rounded-full h-1.5 overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-green-500"
              animate={{ width: `${(matchesPlayed / 72) * 100}%` }}
              transition={{ duration: 0.4, ease: EASE }}
            />
          </div>
          <span>{isLiveMode ? "real results" : "matches predicted"}</span>
        </div>
        <div className="ml-auto flex gap-2">
          {!isLiveMode && (
            <button onClick={resetAll} className="text-xs text-slate-500 hover:text-slate-700 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors">
              Reset all ↺
            </button>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="inline-flex w-4 h-4 rounded-full bg-blue-500 items-center justify-center text-white text-[9px] font-black">Q</span>
          <span className="text-slate-600">Qualified (top 2)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-flex w-4 h-4 rounded-full bg-amber-400 items-center justify-center text-white text-[9px] font-black">Q</span>
          <span className="text-slate-600">Best 3rd place (8 of 12)</span>
        </div>
        {isLiveMode && (
          <>
            <div className="flex items-center gap-1.5">
              <span className="inline-flex items-center gap-1 text-[10px] font-black bg-red-500 text-white px-1.5 py-0.5 rounded-md">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />LIVE
              </span>
              <span className="text-slate-600">In progress</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-flex text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200 px-1.5 py-0.5 rounded-md">FT</span>
              <span className="text-slate-600">Locked result</span>
            </div>
          </>
        )}
        {!isLiveMode && (
          <div className="flex items-center gap-2 ml-2">
            <span className="inline-flex items-center gap-0.5 bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-[10px] font-bold">H</span>
            <span className="text-slate-600">Home win</span>
            <span className="inline-flex items-center gap-0.5 bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px] font-bold ml-1">D</span>
            <span className="text-slate-600">Draw</span>
            <span className="inline-flex items-center gap-0.5 bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-[10px] font-bold ml-1">A</span>
            <span className="text-slate-600">Away win</span>
          </div>
        )}
      </div>

      {/* Group cards grid */}
      <div className="grid grid-cols-3 gap-4">
        {GROUP_IDS.map((gid, i) => {
          const groupLiveMatches = matches.filter(m => m.group === gid)
          return (
            <motion.div
              key={gid}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03, duration: 0.38, ease: EASE }}
            >
              <GroupCard
                groupId={gid}
                standings={standings[gid]}
                fixtures={allFixtures[gid]}
                scores={scores[gid]}
                bestThirds={bestThirds}
                onScore={(idx, s) => setScore(gid, idx, s)}
                liveMatches={groupLiveMatches}
                isLiveMode={isLiveMode}
              />
            </motion.div>
          )
        })}
      </div>

      {/* Advance to bracket */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.4, ease: EASE }}
        className="card rounded-2xl p-5 flex items-center justify-between"
      >
        <div className="space-y-0.5">
          <div className="text-sm font-bold text-slate-800">Ready to build your bracket?</div>
          <div className="text-xs text-slate-600">
            {isLiveMode
              ? hasLiveData
                ? `${matchesPlayed} real results locked in. Bracket will seed from official standings.`
                : "Connect live data to auto-seed the bracket from real standings."
              : matchesPlayed === 72
              ? "All 72 matches predicted — bracket fully personalised!"
              : `${72 - matchesPlayed} matches left. Bracket uses predicted standings so far.`}
          </div>
        </div>
        <button onClick={advanceToBracket} className="btn-primary px-6 py-3 shrink-0">
          Generate Knockout Bracket →
        </button>
      </motion.div>

    </div>
  )
}
