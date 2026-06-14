"use client"

import { useEffect, useRef, useState } from "react"
import { motion, AnimatePresence, animate, useMotionValue, useTransform } from "framer-motion"
import { getTeams, predictMatch, PredictResult } from "@/lib/api"
import Flag from "@/components/Flag"

const EASE = [0.23, 1, 0.32, 1] as const

// ── Searchable country combobox ──────────────────────────────────────────────

function TeamSearch({
  label, value, teams, onChange,
}: { label: string; value: string; teams: string[]; onChange: (t: string) => void }) {
  const [query, setQuery] = useState("")
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handle)
    return () => document.removeEventListener("mousedown", handle)
  }, [])

  const filtered = query.trim()
    ? teams.filter(t => t.toLowerCase().includes(query.toLowerCase()))
    : teams

  function select(t: string) {
    onChange(t)
    setQuery("")
    setOpen(false)
    inputRef.current?.blur()
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Escape") { setOpen(false); setQuery("") }
    if (e.key === "Enter" && filtered.length > 0) select(filtered[0])
  }

  return (
    <div ref={ref} className="relative space-y-2">
      <label className="text-xs font-black text-slate-600 uppercase tracking-[0.15em] block">{label}</label>
      <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none z-10">
          <Flag team={value} size="sm" />
        </div>
        <input
          ref={inputRef}
          type="text"
          value={open ? query : value}
          placeholder={open ? "Type to search…" : value}
          onFocus={() => { setQuery(""); setOpen(true) }}
          onChange={e => { setQuery(e.target.value); setOpen(true) }}
          onKeyDown={handleKey}
          className="w-full pl-9 pr-8 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-800
            focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all cursor-pointer"
          autoComplete="off"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 text-xs">
          {open ? "▲" : "▼"}
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scaleY: 0.95 }}
            animate={{ opacity: 1, y: 0, scaleY: 1 }}
            exit={{ opacity: 0, y: -4, scaleY: 0.95 }}
            transition={{ duration: 0.12 }}
            style={{ transformOrigin: "top" }}
            className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden"
          >
            <div className="max-h-52 overflow-y-auto overscroll-contain">
              {filtered.length === 0 ? (
                <div className="px-4 py-3 text-xs text-slate-400 text-center">No country found</div>
              ) : filtered.map(t => (
                <button
                  key={t}
                  onMouseDown={e => { e.preventDefault(); select(t) }}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left transition-colors
                    ${t === value ? "bg-blue-50 text-blue-700 font-semibold" : "text-slate-700 hover:bg-slate-50"}`}
                >
                  <Flag team={t} size="sm" />
                  {t}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Animated percentage bar ──────────────────────────────────────────────────

function AnimatedPct({ value, delay = 0 }: { value: number; delay?: number }) {
  const mv = useMotionValue(0)
  const display = useTransform(mv, (v) => `${(v * 100).toFixed(1)}%`)
  useEffect(() => {
    let ctrl: { stop: () => void } | null = null
    const t = setTimeout(() => { ctrl = animate(mv, value, { duration: 1, ease: [0.23, 1, 0.32, 1] }) }, delay * 1000)
    return () => { clearTimeout(t); ctrl?.stop() }
  }, [value, delay, mv])
  return <motion.span>{display}</motion.span>
}

function ProbBar({
  label, team, value, gradient, isWinner = false, delay = 0,
}: { label: string; team?: string; value: number; gradient: string; isWinner?: boolean; delay?: number }) {
  return (
    <div className={`rounded-xl border p-4 transition-all duration-200 ${
      isWinner ? "border-blue-300 bg-blue-50 shadow-md shadow-blue-100" : "border-slate-200 bg-white"
    }`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {team && <Flag team={team} size="md" />}
          <span className={`text-sm font-semibold ${isWinner ? "text-blue-900" : "text-slate-700"}`}>{label}</span>
          {isWinner && <span className="text-blue-500 text-sm">✦</span>}
        </div>
        <div className={`text-2xl font-black tabular-nums ${isWinner ? "text-blue-600" : "text-slate-500"}`}>
          <AnimatedPct value={value} delay={delay} />
        </div>
      </div>
      <div className="prob-bar">
        <motion.div
          style={{ background: gradient, height: "100%", borderRadius: 999 }}
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 0.7, delay, ease: EASE }}
        />
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function MatchPage() {
  const [teamNames, setTeamNames] = useState<string[]>([])
  const [home, setHome] = useState("Argentina")
  const [away, setAway] = useState("France")
  const [neutral, setNeutral] = useState(true)
  const [weight, setWeight] = useState(1.0)
  const [result, setResult] = useState<PredictResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fetching, setFetching] = useState(true)

  useEffect(() => {
    getTeams()
      .then(t => setTeamNames(t.map(x => x.team)))
      .catch(() => setError("Could not load team list — is the API running?"))
      .finally(() => setFetching(false))
  }, [])

  function handleHomeChange(v: string) { setHome(v); setResult(null); setError(null) }
  function handleAwayChange(v: string) { setAway(v); setResult(null); setError(null) }

  async function predict() {
    if (home === away) return
    setLoading(true); setResult(null); setError(null)
    try {
      setResult(await predictMatch(home, away, neutral, weight))
    } catch (e) {
      setError("Prediction failed — the API may be starting up, try again in a moment.")
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (fetching) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-7 h-7 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin" />
    </div>
  )

  const winner = result
    ? result.home_win > result.away_win && result.home_win > result.draw ? "home"
      : result.away_win > result.home_win && result.away_win > result.draw ? "away"
      : "draw"
    : null

  return (
    <div className="max-w-xl mx-auto space-y-8">

      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: EASE }}>
        <p className="text-blue-600 text-[11px] font-black tracking-[0.25em] uppercase mb-3">⚽ Head-to-head</p>
        <h1 className="text-4xl font-black tracking-tight text-slate-900 mb-2">Match Predictor</h1>
        <p className="text-slate-500 text-sm">Select two nations to get ML-powered win probabilities</p>
        <div className="gradient-divider mt-6" />
      </motion.div>

      {/* Selector card */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.45, ease: EASE }}
        className="card rounded-2xl p-6 space-y-5"
      >
        <div className="grid grid-cols-2 gap-4">
          <TeamSearch label="Home Nation" value={home} teams={teamNames} onChange={handleHomeChange} />
          <TeamSearch label="Away Nation" value={away} teams={teamNames} onChange={handleAwayChange} />
        </div>

        {home !== away ? (
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-slate-100" />
            <span className="text-xs text-slate-500 font-black tracking-widest">VS</span>
            <div className="flex-1 h-px bg-slate-100" />
          </div>
        ) : (
          <p className="text-xs text-red-500 text-center">Select two different teams</p>
        )}

        <div className="flex items-center gap-5 flex-wrap">
          <button onClick={() => setNeutral(!neutral)} className="flex items-center gap-2.5 cursor-pointer group">
            <div className={`w-9 h-5 rounded-full relative transition-colors duration-200 ${neutral ? "bg-blue-600" : "bg-slate-200"}`}>
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${neutral ? "translate-x-[18px]" : "translate-x-0.5"}`} />
            </div>
            <span className="text-xs text-slate-500 group-hover:text-slate-800 transition-colors">Neutral venue</span>
          </button>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-600 uppercase tracking-wide">Weight</span>
            <input type="range" min="0.3" max="1" step="0.05" value={weight}
              onChange={e => setWeight(parseFloat(e.target.value))}
              className="w-20 accent-blue-600"
            />
            <span className="text-xs text-blue-600 tabular-nums w-8">{weight.toFixed(2)}</span>
          </div>
        </div>

        {error && (
          <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-center">
            {error}
          </div>
        )}

        <button
          onClick={predict}
          disabled={loading || home === away}
          className="btn-primary w-full py-3"
        >
          {loading
            ? <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                Calculating…
              </span>
            : "Predict Match"
          }
        </button>
      </motion.div>

      {/* Result */}
      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            key={`${result.home_team}-${result.away_team}-${weight}`}
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={{ duration: 0.4, ease: EASE }}
            className="space-y-3"
          >
            <div className="flex items-center justify-center gap-3 text-sm mb-5">
              <Flag team={result.home_team} size="md" />
              <span className="text-slate-800 font-semibold">{result.home_team}</span>
              <span className="text-slate-300 text-xs font-black tracking-widest">VS</span>
              <span className="text-slate-800 font-semibold">{result.away_team}</span>
              <Flag team={result.away_team} size="md" />
            </div>

            <ProbBar label={`${result.home_team} Win`} team={result.home_team} value={result.home_win}
              gradient="linear-gradient(90deg, #2563eb, #60a5fa)" isWinner={winner === "home"} delay={0.05} />
            <ProbBar label="Draw" value={result.draw}
              gradient="linear-gradient(90deg, #94a3b8, #cbd5e1)" isWinner={winner === "draw"} delay={0.12} />
            <ProbBar label={`${result.away_team} Win`} team={result.away_team} value={result.away_win}
              gradient="linear-gradient(90deg, #10b981, #34d399)" isWinner={winner === "away"} delay={0.19} />

            <div className="text-center text-xs text-slate-500 mt-3 space-x-3">
              <span>Elo — {result.home_team}: {result.home_elo} · {result.away_team}: {result.away_elo}</span>
              <span className="text-slate-300">|</span>
              <span>(Δ {result.home_elo > result.away_elo ? "+" : ""}{result.home_elo - result.away_elo})</span>
              {result.method === "elo" && (
                <span className="ml-2 text-amber-600 font-semibold">· Elo estimate</span>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}
