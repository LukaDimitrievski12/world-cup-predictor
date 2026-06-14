"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import ModeToggle from "@/components/ModeToggle"

const links = [
  { href: "/",         label: "Tournament" },
  { href: "/groups",   label: "🏟️ Groups" },
  { href: "/bracket",  label: "⚡ Bracket" },
  { href: "/match",    label: "Match Predictor" },
  { href: "/rankings", label: "Rankings" },
  { href: "/model",    label: "Model" },
]

export default function Nav() {
  const path = usePathname()

  return (
    <header
      className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-slate-200/80"
      style={{ boxShadow: "0 1px 16px rgba(37,99,235,0.07)" }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3.5">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center w-9 h-9 rounded-xl"
            style={{
              background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
              boxShadow: "0 4px 12px rgba(37,99,235,0.35)",
            }}
          >
            <span className="text-base leading-none">🏆</span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-extrabold text-slate-900 text-sm tracking-tight">WC 2026</span>
            <span className="text-slate-300 text-xs">·</span>
            <span className="text-slate-500 text-xs font-medium">Predictor</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-1">
          {links.map((l) => {
            const active = path === l.href
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-150 ${
                  active
                    ? "text-white shadow-md"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
                style={active ? {
                  background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
                  boxShadow: "0 2px 10px rgba(37,99,235,0.3)",
                } : {}}
              >
                {l.label}
              </Link>
            )
          })}
        </nav>

        {/* Live / Simulation mode toggle */}
        <ModeToggle />

      </div>
    </header>
  )
}
