import type { MatchStatus } from "@/lib/live-types"

interface Props {
  status: MatchStatus
  minute?: number
  compact?: boolean   // true = just the pill, no extra margin
}

export default function MatchStatusBadge({ status, minute, compact = false }: Props) {
  const cls = compact ? "" : "ml-1"

  if (status === "live") {
    return (
      <span className={`${cls} inline-flex items-center gap-1 text-[10px] font-black bg-red-500 text-white px-1.5 py-0.5 rounded-md shrink-0`}>
        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse shrink-0" />
        {minute != null ? `${minute}'` : "LIVE"}
      </span>
    )
  }

  if (status === "finished") {
    return (
      <span className={`${cls} inline-flex items-center text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200 px-1.5 py-0.5 rounded-md shrink-0`}>
        FT
      </span>
    )
  }

  // scheduled / cancelled — render nothing
  return null
}
