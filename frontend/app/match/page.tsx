"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence, animate, useMotionValue, useTransform } from "framer-motion"
import { getTeams, predictMatch, PredictResult } from "@/lib/api"
import Flag from "@/components/Flag"

const EASE = [0.23, 1, 0.32, 1] as const

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
}: {
  label: string; team?: string; value: number; gradient: string; isWinner?: boolean; delay?: number
}) {
  return (
    <div className={`rounded-xl border p-4 transition-all duration-200 ${
      isWinner
        ? "border-blue-300 bg-blue-50 shadow-md shadow-blue-100"
        : "border-slate-200 bg-white"
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

export default function MatchPage() {
  const [teamNames, setTeamNames] = useState<string[]>([])
  const [home, setHome] = useState("Argentina")
  const [away, setAway] = useState("France")
  const [neutral, setNeutral] = useState(true)
  const [weight, setWeight] = useState(1.0)
  const [result, setResult] = useState<PredictResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(true)

  useEffect(() => {
    getTeams().then(t => setTeamNames(t.map(x => x.team))).catch(console.error).finally(() => setFetching(false))
  }, [])

  async function predict() {
    if (home === away) return
    setLoading(true); setResult(null)
    try { setResult(await predictMatch(home, away, neutral, weight)) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
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
          {([
            { label: "Home Nation", value: home, set: (v: string) => { setHome(v); setResult(null) } },
            { label: "Away Nation", value: away, set: (v: string) => { setAway(v); setResult(null) } },
          ] as const).map(({ label, value, set }) => (
            <div key={label} className="space-y-2">
              <label className="text-xs font-black text-slate-600 uppercase tracking-[0.15em]">{label}</label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
                  <Flag team={value} size="sm" />
                </div>
                <select
                  value={value}
                  onChange={e => set(e.target.value)}
                  className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-800
                    focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 cursor-pointer transition-all"
                >
                  {teamNames.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
          ))}
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

        <button
          onClick={predict}
          disabled={loading || home === away}
          className="btn-primary w-full py-3"
        >
          {loading ? "Calculating…" : "Predict Match"}
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

            <div className="text-center text-xs text-slate-600 mt-3">
              Elo — {result.home_team}: {result.home_elo} · {result.away_team}: {result.away_elo}
              <span className="ml-2">
                (Δ {result.home_elo > result.away_elo ? "+" : ""}{result.home_elo - result.away_elo})
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}
