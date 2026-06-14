"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { getTeams, TeamProfile } from "@/lib/api"
import Flag from "@/components/Flag"

const EASE = [0.23, 1, 0.32, 1] as const
const MEDAL = ["🥇", "🥈", "🥉"]

function eloBarColor(i: number): string {
  if (i === 0) return "linear-gradient(90deg, #f59e0b, #fcd34d, #f59e0b)"
  if (i === 1) return "linear-gradient(90deg, #94a3b8, #cbd5e1)"
  if (i === 2) return "linear-gradient(90deg, #b45309, #d97706)"
  if (i < 10) return "linear-gradient(90deg, #2563eb, #60a5fa)"
  return "linear-gradient(90deg, #cbd5e1, #e2e8f0)"
}

export default function RankingsPage() {
  const [teams, setTeams] = useState<TeamProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")

  useEffect(() => {
    getTeams().then(setTeams).catch(console.error).finally(() => setLoading(false))
  }, [])

  const filtered = teams.filter(t => t.team.toLowerCase().includes(search.toLowerCase()))
  const maxElo = teams[0]?.elo ?? 2100
  const minElo = 1100

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-7 h-7 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin" />
    </div>
  )

  return (
    <div className="space-y-8">

      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: EASE }}>
        <p className="text-blue-600 text-[11px] font-black tracking-[0.25em] uppercase mb-3">📊 Strength Index</p>
        <h1 className="text-4xl font-black tracking-tight text-slate-900 mb-2">Team Rankings</h1>
        <p className="text-slate-500 text-sm">Elo ratings computed from 150+ years of international football (1872–2026)</p>
        <div className="gradient-divider mt-6" />
      </motion.div>

      {/* Search */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.35, ease: EASE }}>
        <input
          type="text"
          placeholder="Search nation…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-56 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800
            placeholder:text-slate-400 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
        />
      </motion.div>

      {/* List */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.45, ease: EASE }}
        className="card rounded-2xl overflow-hidden"
      >
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <h2 className="text-base font-bold text-slate-900">
            {search ? `${filtered.length} results` : `${teams.length} nations ranked`}
          </h2>
          <span className="text-xs text-slate-600">Elo rating</span>
        </div>

        <div className="divide-y divide-slate-50">
          {filtered.slice(0, 80).map((team, i) => {
            const globalRank = teams.findIndex(t => t.team === team.team) + 1
            const barPct = Math.max(2, ((team.elo - minElo) / (maxElo - minElo)) * 100)
            const isTop3 = globalRank <= 3

            return (
              <motion.div
                key={team.team}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.01, duration: 0.25, ease: EASE }}
                className={`px-6 py-3 flex items-center gap-4 group transition-colors duration-100 ${
                  isTop3 ? "hover:bg-amber-50" : "hover:bg-blue-50/40"
                }`}
              >
                {/* Rank */}
                <div className="w-8 text-right shrink-0">
                  {isTop3
                    ? <span className="text-base">{MEDAL[globalRank - 1]}</span>
                    : <span className="text-xs font-mono text-slate-400 tabular-nums">{globalRank}</span>
                  }
                </div>

                {/* Flag + Name */}
                <div className="flex items-center gap-2 w-44 shrink-0">
                  <Flag team={team.team} size="sm" />
                  <span className={`text-sm truncate ${isTop3 ? "text-slate-900 font-bold" : "text-slate-700 font-medium"}`}>
                    {team.team}
                  </span>
                </div>

                {/* Bar */}
                <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: eloBarColor(globalRank - 1) }}
                    initial={{ width: 0 }}
                    animate={{ width: `${barPct}%` }}
                    transition={{ delay: 0.2 + i * 0.01, duration: 0.7, ease: EASE }}
                  />
                </div>

                {/* Elo */}
                <span className={`text-sm font-black tabular-nums w-14 text-right shrink-0 ${
                  globalRank === 1 ? "text-amber-500" :
                  globalRank === 2 ? "text-slate-500" :
                  globalRank === 3 ? "text-amber-700" :
                  "text-slate-500"
                }`}>
                  {Math.round(team.elo)}
                </span>

                {/* FIFA rank */}
                <span className="text-[10px] text-slate-300 w-16 text-right shrink-0 tabular-nums">
                  {team.rank ? `#${Math.round(team.rank)} FIFA` : ""}
                </span>

                {/* W5 — on hover */}
                <span className="text-[10px] text-slate-300 w-14 text-right shrink-0 tabular-nums opacity-0 group-hover:opacity-100 transition-opacity">
                  {team.last5_win != null ? `${(team.last5_win * 100).toFixed(0)}% W5` : ""}
                </span>
              </motion.div>
            )
          })}
        </div>
      </motion.div>
    </div>
  )
}
