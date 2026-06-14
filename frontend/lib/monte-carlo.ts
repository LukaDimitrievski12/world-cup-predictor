import { WC2026_GROUPS, groupFixtures, BRACKET_SEEDING, type GroupId } from "@/lib/groups"
import type { LiveMatch } from "@/lib/live-types"
import type { SimulationRow } from "@/lib/api"

const SIMS = 1_000
const GROUP_IDS = ["A","B","C","D","E","F","G","H","I","J","K","L"] as const

function eloP(a: number, b: number) {
  return 1 / (1 + Math.pow(10, (b - a) / 400))
}

function simGroupMatch(eloH: number, eloA: number): [number, number] {
  const ph   = eloP(eloH, eloA)
  const draw = Math.max(0.08, 0.28 - Math.abs(eloH - eloA) * 0.00035)
  const r    = Math.random()
  if (r < ph - draw * 0.5)             return [1, 0]
  if (r < ph - draw * 0.5 + draw)      return [0, 0]
  return [0, 1]
}

function simKnockout(t1: string, t2: string, elo: Record<string, number>): string {
  return Math.random() < eloP(elo[t1] ?? 1350, elo[t2] ?? 1350) ? t1 : t2
}

export function runMonteCarlo(
  liveMatches: LiveMatch[],
  eloMap: Record<string, number>
): SimulationRow[] {
  const allTeams = Object.values(WC2026_GROUPS).flat()
  const counts: Record<string, { r32:number; r16:number; qf:number; sf:number; final:number; winner:number }> = {}
  for (const t of allTeams) counts[t] = { r32:0, r16:0, qf:0, sf:0, final:0, winner:0 }

  const finishedGroup = liveMatches.filter(m => m.group && m.status === "finished")

  for (let s = 0; s < SIMS; s++) {
    // ── Group stage ────────────────────────────────────────────────
    const qualified: Record<string, string> = {}
    const thirds: { team: string; pts: number; gd: number; gf: number }[] = []

    for (const gid of GROUP_IDS) {
      const teams = WC2026_GROUPS[gid as GroupId]
      const st: Record<string, { pts:number; gd:number; gf:number }> = {}
      for (const t of teams) st[t] = { pts:0, gd:0, gf:0 }

      for (const [ht, at] of groupFixtures(teams)) {
        const played = finishedGroup.find(m =>
          m.group === gid &&
          ((m.homeTeam === ht && m.awayTeam === at) ||
           (m.homeTeam === at && m.awayTeam === ht))
        )

        let hg: number, ag: number
        if (played && played.homeScore != null && played.awayScore != null) {
          hg = played.homeTeam === ht ? played.homeScore : played.awayScore
          ag = played.homeTeam === ht ? played.awayScore : played.homeScore
        } else {
          ;[hg, ag] = simGroupMatch(eloMap[ht] ?? 1350, eloMap[at] ?? 1350)
        }

        st[ht].gf += hg; st[ht].gd += hg - ag
        st[at].gf += ag; st[at].gd += ag - hg
        if      (hg > ag) { st[ht].pts += 3 }
        else if (hg < ag) { st[at].pts += 3 }
        else              { st[ht].pts += 1; st[at].pts += 1 }
      }

      const ranked = [...teams].sort((a, b) =>
        (st[b].pts - st[a].pts) || (st[b].gd - st[a].gd) || (st[b].gf - st[a].gf)
      )
      qualified[`${gid}1`] = ranked[0]
      qualified[`${gid}2`] = ranked[1]
      thirds.push({ team: ranked[2], ...st[ranked[2]] })
    }

    thirds.sort((a, b) => (b.pts - a.pts) || (b.gd - a.gd) || (b.gf - a.gf))
    thirds.slice(0, 8).forEach((t, i) => { qualified[`3rd${i + 1}`] = t.team })

    for (const t of Object.values(qualified)) { if (counts[t]) counts[t].r32++ }

    // ── Knockout rounds ────────────────────────────────────────────
    const r32Pairs = BRACKET_SEEDING.map(([s1, s2]) =>
      [qualified[s1] ?? "", qualified[s2] ?? ""] as [string, string]
    )

    const r16: string[] = []
    for (const [t1, t2] of r32Pairs) {
      if (!t1 || !t2) continue
      const w = simKnockout(t1, t2, eloMap)
      r16.push(w)
      if (counts[w]) counts[w].r16++
    }

    const qf: string[] = []
    for (let i = 0; i < r16.length - 1; i += 2) {
      const w = simKnockout(r16[i], r16[i + 1], eloMap)
      qf.push(w)
      if (counts[w]) counts[w].qf++
    }

    const sf: string[] = []
    for (let i = 0; i < qf.length - 1; i += 2) {
      const w = simKnockout(qf[i], qf[i + 1], eloMap)
      sf.push(w)
      if (counts[w]) counts[w].sf++
    }

    const finalists: string[] = []
    for (let i = 0; i < sf.length - 1; i += 2) {
      const w = simKnockout(sf[i], sf[i + 1], eloMap)
      finalists.push(w)
      if (counts[w]) counts[w].final++
    }

    if (finalists.length >= 2) {
      const champ = simKnockout(finalists[0], finalists[1], eloMap)
      if (counts[champ]) counts[champ].winner++
    }
  }

  return allTeams.map(t => ({
    team:         t,
    group_stage:  1,
    round_of_32:  counts[t].r32    / SIMS,
    round_of_16:  counts[t].r16    / SIMS,
    quarterfinal: counts[t].qf     / SIMS,
    semifinal:    counts[t].sf     / SIMS,
    final:        counts[t].final  / SIMS,
    winner:       counts[t].winner / SIMS,
  }))
}
