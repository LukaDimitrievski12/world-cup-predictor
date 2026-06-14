import { flagUrl } from "@/lib/flags"

type Size = "sm" | "md" | "lg"

const DIMS: Record<Size, { w: number; h: number; cls: string }> = {
  sm: { w: 16, h: 12, cls: "w-4 h-3" },
  md: { w: 24, h: 18, cls: "w-6 h-[18px]" },
  lg: { w: 32, h: 24, cls: "w-8 h-6" },
}

export default function Flag({ team, size = "md" }: { team: string; size?: Size }) {
  const dim = DIMS[size]
  const url = flagUrl(team, `${dim.w}x${dim.h}` as "16x12" | "24x18" | "32x24")
  if (!url) return <span className="text-slate-700 text-xs">—</span>
  return (
    <img
      src={url}
      alt={team}
      width={dim.w}
      height={dim.h}
      className={`${dim.cls} object-cover rounded-[2px] shrink-0`}
    />
  )
}
