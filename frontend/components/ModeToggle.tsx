"use client"

import { useTournament } from "@/context/TournamentContext"

export default function ModeToggle() {
  const { mode, setMode, isLiveMatchActive, lastUpdated, isLoading } = useTournament()

  const isLive = mode === "live"

  function fmt(d: Date) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  }

  return (
    <div className="flex items-center gap-2">
      {/* Live indicator dot */}
      {isLive && isLiveMatchActive && (
        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse shrink-0" />
      )}

      {/* Last updated timestamp */}
      {isLive && lastUpdated && !isLoading && (
        <span className="text-[10px] text-slate-400 tabular-nums hidden md:block">
          {fmt(lastUpdated)}
        </span>
      )}

      {/* Loading spinner */}
      {isLive && isLoading && (
        <svg className="w-3 h-3 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
        </svg>
      )}

      {/* Toggle button */}
      <button
        onClick={() => setMode(isLive ? "simulation" : "live")}
        className={`relative inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-all duration-200 ${
          isLive
            ? "bg-red-50 border-red-200 text-red-600 hover:bg-red-100"
            : "bg-slate-100 border-slate-200 text-slate-600 hover:bg-slate-200"
        }`}
      >
        {isLive ? (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
            Live
          </>
        ) : (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            Simulation
          </>
        )}
      </button>
    </div>
  )
}
