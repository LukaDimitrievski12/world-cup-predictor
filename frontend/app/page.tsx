"use client"

import { useEffect, useState } from "react"
import { motion, animate, useMotionValue, useTransform } from "framer-motion"
import { getSimulation, SimulationRow } from "@/lib/api"
import Flag from "@/components/Flag"

const STAGES = ["group_stage", "round_of_32", "round_of_16", "quarterfinal", "semifinal", "final", "winner"] as const
const LABELS: Record<string, string> = {
  group_stage: "Groups", round_of_32: "R32", round_of_16: "R16",
  quarterfinal: "QF", semifinal: "SF", final: "Final", winner: "🏆",
}

const EASE = [0.23, 1, 0.32, 1] as const

function AnimatedPct({ value, delay = 0 }: { value: number; delay?: number }) {
  const mv = useMotionValue(0)
  const display = useTransform(mv, (v) => `${(v * 100).toFixed(1)}%`)
  useEffect(() => {
    let ctrl: { stop: () => void } | null = null
    const t = setTimeout(() => { ctrl = animate(mv, value, { duration: 1.3, ease: [0.23, 1, 0.32, 1] }) }, delay * 1000)
    return () => { clearTimeout(t); ctrl?.stop() }
  }, [value, delay, mv])
  return <motion.span>{display}</motion.span>
}

function pct(v: number) { return `${(v * 100).toFixed(1)}%` }

function cellColor(v: number): string {
  if (v >= 0.35) return "text-blue-700 font-bold"
  if (v >= 0.18) return "text-blue-500 font-semibold"
  if (v >= 0.08) return "text-slate-600"
  if (v >= 0.03) return "text-slate-400"
  return "text-slate-300"
}

function Spinner() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="w-7 h-7 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin" />
    </div>
  )
}

export default function TournamentPage() {
  const [data, setData] = useState<SimulationRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    getSimulation().then(setData).catch(() => setError(true)).finally(() => setLoading(false))
  }, [])

  const sorted = [...data].sort((a, b) => b.winner - a.winner)
  const top5 = sorted.slice(0, 5)

  if (loading) return <Spinner />
  if (error) return (
    <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
      Could not connect to API — run: <code className="ml-2 text-blue-600 bg-blue-50 px-2 py-0.5 rounded">uvicorn api.main:app --port 8000</code>
    </div>
  )

  return (
    <div className="space-y-12">

      {/* ── Hero ── */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: EASE }}
        className="relative pt-2"
      >
        <div
          className="absolute -top-10 -left-6 w-72 h-32 pointer-events-none"
          style={{ background: "radial-gradient(ellipse at left, rgba(37,99,235,0.1) 0%, transparent 70%)" }}
        />
        <p className="text-blue-600 text-[11px] font-black tracking-[0.28em] uppercase mb-4">
          ⚽ &nbsp;USA · Mexico · Canada &nbsp;·&nbsp; June 2026
        </p>
        <h1 className="text-[3.25rem] font-black tracking-tight leading-none text-slate-900 mb-4">
          Who Will Lift<br />
          <span className="shimmer-text">The Trophy?</span>
        </h1>
        <p className="text-slate-500 text-sm max-w-md">
          10,000 Monte Carlo simulations · Calibrated XGBoost + Logistic Regression · 48 nations competing
        </p>
        <div className="gradient-divider mt-8" />
      </motion.section>

      {/* ── Top 5 cards ── */}
      <section className="grid grid-cols-5 gap-3">
        {top5.map((team, i) => {
          const isTop = i === 0
          return (
            <motion.div
              key={team.team}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.08, duration: 0.45, ease: EASE }}
              className={`relative rounded-2xl p-4 cursor-default transition-all duration-300 hover:-translate-y-1 ${
                isTop ? "card-gold" : "card"
              }`}
            >
              {isTop && (
                <div className="absolute top-3 right-3 text-xl" style={{ animation: "float 2.5s ease-in-out infinite" }}>
                  🏆
                </div>
              )}

              <div className={`text-[10px] font-black uppercase tracking-[0.2em] mb-2 ${
                isTop ? "text-amber-600" : "text-slate-500"
              }`}>
                #{i + 1} Favourite
              </div>

              <div className="flex items-center gap-1.5 mb-3 pr-6">
                <Flag team={team.team} size="sm" />
                <span className={`font-bold text-sm leading-tight truncate ${isTop ? "text-slate-900" : "text-slate-800"}`}>
                  {team.team}
                </span>
              </div>

              <div className={`text-[1.75rem] font-black tabular-nums leading-none mb-0.5 ${
                isTop ? "text-amber-600" : "text-blue-600"
              }`}>
                <AnimatedPct value={team.winner} delay={0.3 + i * 0.08} />
              </div>
              <div className={`text-[10px] mb-3 ${isTop ? "text-amber-500" : "text-slate-500"}`}>win probability</div>

              <div className={`border-t pt-3 space-y-1.5 ${isTop ? "border-amber-200" : "border-slate-100"}`}>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">→ Final</span>
                  <span className={`tabular-nums font-semibold ${isTop ? "text-amber-600" : "text-slate-600"}`}>{pct(team.final)}</span>
                </div>
                <div className="prob-bar">
                  <motion.div
                    className={isTop ? "prob-fill-amber" : "prob-fill-blue"}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(team.final * 200, 100)}%` }}
                    transition={{ delay: 0.6 + i * 0.08, duration: 1, ease: EASE }}
                  />
                </div>
              </div>
            </motion.div>
          )
        })}
      </section>

      {/* ── Full table ── */}
      <motion.section
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.5, ease: EASE }}
        className="card rounded-2xl overflow-hidden"
      >
        <div className="px-6 py-5 border-b border-slate-100">
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">Advancement Probabilities</h2>
          <p className="text-xs text-slate-600 mt-0.5">All 48 nations · Sorted by championship probability</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/60">
                <th className="text-left px-6 py-3 text-xs font-bold text-slate-600 uppercase tracking-[0.15em]">Nation</th>
                {STAGES.map((s) => (
                  <th key={s} className={`px-3 py-3 text-xs font-bold text-center uppercase tracking-[0.15em] ${
                    s === "winner" ? "text-amber-600" : "text-slate-600"
                  }`}>
                    {LABELS[s]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row, i) => (
                <motion.tr
                  key={row.team}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.6 + i * 0.005, duration: 0.2 }}
                  className="border-b border-slate-50 transition-colors duration-100 hover:bg-blue-50/40 group"
                >
                  <td className="px-6 py-2.5">
                    <div className="flex items-center gap-2.5">
                      <span className="w-5 text-[10px] text-slate-300 font-mono text-right shrink-0 tabular-nums">{i + 1}</span>
                      <Flag team={row.team} size="sm" />
                      <span className="font-semibold text-slate-800 text-sm">{row.team}</span>
                    </div>
                  </td>
                  {STAGES.map((s) => {
                    const v = row[s] as number
                    return (
                      <td key={s} className={`px-3 py-2.5 text-center text-xs font-mono tabular-nums ${cellColor(v)}`}>
                        {s === "group_stage" ? <span className="text-slate-300">✓</span> : pct(v)}
                      </td>
                    )
                  })}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.section>

    </div>
  )
}
