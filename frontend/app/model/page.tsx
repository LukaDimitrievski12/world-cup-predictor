"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { getMetrics, ModelMetrics } from "@/lib/api"

const EASE = [0.23, 1, 0.32, 1] as const

const METRIC_META: Record<string, { label: string; desc: string; good: "high" | "low" }> = {
  accuracy:           { label: "Accuracy",    desc: "Fraction of correct outcome predictions",    good: "high" },
  log_loss:           { label: "Log Loss",    desc: "Probability quality — cross-entropy",         good: "low"  },
  brier_score:        { label: "Brier Score", desc: "Mean squared probability error",              good: "low"  },
  f1_macro:           { label: "F1 Macro",    desc: "Balanced F1 across home/draw/away classes",  good: "high" },
  precision_weighted: { label: "Precision",   desc: "Weighted precision across all classes",      good: "high" },
  recall_weighted:    { label: "Recall",      desc: "Weighted recall across all classes",         good: "high" },
}
const METRIC_KEYS = Object.keys(METRIC_META)

export default function ModelPage() {
  const [metrics, setMetrics] = useState<ModelMetrics[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMetrics().then(setMetrics).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-7 h-7 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin" />
    </div>
  )

  const best: Record<string, number> = {}
  METRIC_KEYS.forEach(k => {
    const vals = metrics.map(r => r[k as keyof ModelMetrics] as number).filter(Number.isFinite)
    if (vals.length) best[k] = METRIC_META[k].good === "high" ? Math.max(...vals) : Math.min(...vals)
  })

  return (
    <div className="space-y-8">

      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: EASE }}>
        <p className="text-blue-600 text-[11px] font-black tracking-[0.25em] uppercase mb-3">🤖 ML Pipeline</p>
        <h1 className="text-4xl font-black tracking-tight text-slate-900 mb-2">Model Performance</h1>
        <p className="text-slate-500 text-sm">Evaluated on a held-out validation set (2018–2021) — test set never seen during training</p>
        <div className="gradient-divider mt-6" />
      </motion.div>

      {/* Metrics table */}
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4, ease: EASE }}
        className="card rounded-2xl overflow-hidden"
      >
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/60">
          <h2 className="text-base font-bold text-slate-900">Validation Set Comparison</h2>
          <p className="text-xs text-slate-600 mt-0.5">Best value per column highlighted in blue</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-6 py-3 text-xs font-bold text-slate-600 uppercase tracking-wide">Model</th>
                {METRIC_KEYS.map(k => (
                  <th key={k} className="px-4 py-3 text-xs font-bold text-slate-600 text-center uppercase tracking-wide">
                    {METRIC_META[k].label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {metrics.map((row, i) => (
                <motion.tr
                  key={row.model}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 + i * 0.06, duration: 0.3, ease: EASE }}
                  className="border-b border-slate-50 hover:bg-blue-50/30 transition-colors"
                >
                  <td className="px-6 py-3 font-semibold text-slate-800">{row.model}</td>
                  {METRIC_KEYS.map(k => {
                    const v = row[k as keyof ModelMetrics] as number
                    const isBest = Number.isFinite(v) && v === best[k]
                    return (
                      <td key={k} className={`px-4 py-3 text-center font-mono text-sm ${isBest ? "text-blue-600 font-bold" : "text-slate-500"}`}>
                        {Number.isFinite(v) ? v.toFixed(4) : "—"}
                      </td>
                    )
                  })}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Glossary */}
      <div className="grid grid-cols-3 gap-3">
        {METRIC_KEYS.map((k, i) => (
          <motion.div
            key={k}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.05, duration: 0.3, ease: EASE }}
            className="card rounded-xl p-4"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-slate-800">{METRIC_META[k].label}</span>
              <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                METRIC_META[k].good === "high"
                  ? "bg-green-50 text-green-600 border border-green-100"
                  : "bg-red-50 text-red-500 border border-red-100"
              }`}>
                {METRIC_META[k].good === "high" ? "↑ higher" : "↓ lower"}
              </span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">{METRIC_META[k].desc}</p>
          </motion.div>
        ))}
      </div>

      {/* Key insight */}
      <motion.div
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.3, ease: EASE }}
        className="card-blue rounded-xl p-4"
      >
        <p className="text-sm text-blue-800 leading-relaxed">
          <span className="font-bold">Key insight:</span>{" "}
          Log Loss and Brier Score matter most here — the Monte Carlo simulation uses raw predicted probabilities.
          A model with good accuracy but poor calibration will generate misleading tournament winner estimates.
        </p>
      </motion.div>

    </div>
  )
}
