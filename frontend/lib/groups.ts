export const GROUP_IDS = ["A","B","C","D","E","F","G","H","I","J","K","L"] as const
export type GroupId = typeof GROUP_IDS[number]

export const WC2026_GROUPS: Record<GroupId, string[]> = {
  A: ["Mexico",       "South Korea",            "Czech Republic",    "South Africa"],
  B: ["Switzerland",  "Canada",                 "Qatar",             "Bosnia and Herzegovina"],
  C: ["Brazil",       "Morocco",                "Scotland",          "Haiti"],
  D: ["United States","Turkey",                 "Australia",         "Paraguay"],
  E: ["Germany",      "Curaçao",                "Côte d'Ivoire",     "Ecuador"],
  F: ["Netherlands",  "Japan",                  "Sweden",            "Tunisia"],
  G: ["Belgium",      "Egypt",                  "Iran",              "New Zealand"],
  H: ["Spain",        "Cape Verde",             "Saudi Arabia",      "Uruguay"],
  I: ["France",       "Senegal",                "Iraq",              "Norway"],
  J: ["Argentina",    "Algeria",                "Austria",           "Jordan"],
  K: ["Portugal",     "DR Congo",               "Uzbekistan",        "Colombia"],
  L: ["England",      "Croatia",                "Ghana",             "Panama"],
}

// All 6 round-robin pairs for a 4-team group
export function groupFixtures(teams: string[]): [string, string][] {
  const f: [string, string][] = []
  for (let i = 0; i < teams.length; i++)
    for (let j = i + 1; j < teams.length; j++)
      f.push([teams[i], teams[j]])
  return f
}

export type Score = { h: number; a: number }

export type TeamStats = {
  team: string; p: number; w: number; d: number; l: number
  gf: number; ga: number; gd: number; pts: number
}

export function calcStandings(
  teams: string[],
  fixtures: [string, string][],
  scores: (Score | null)[]
): TeamStats[] {
  const s: Record<string, TeamStats> = Object.fromEntries(
    teams.map(t => [t, { team: t, p:0, w:0, d:0, l:0, gf:0, ga:0, gd:0, pts:0 }])
  )
  fixtures.forEach(([home, away], i) => {
    const sc = scores[i]
    if (!sc) return
    const { h: hg, a: ag } = sc
    s[home].p++; s[away].p++
    s[home].gf += hg; s[home].ga += ag; s[home].gd = s[home].gf - s[home].ga
    s[away].gf += ag; s[away].ga += hg; s[away].gd = s[away].gf - s[away].ga
    if      (hg > ag) { s[home].w++; s[home].pts += 3; s[away].l++ }
    else if (hg < ag) { s[away].w++; s[away].pts += 3; s[home].l++ }
    else              { s[home].d++; s[home].pts++;    s[away].d++; s[away].pts++ }
  })
  return Object.values(s).sort((a, b) =>
    (b.pts - a.pts) || (b.gd - a.gd) || (b.gf - a.gf) || a.team.localeCompare(b.team)
  )
}

// Map slot codes ("A1", "A2", "3rd1"…) → actual team names
export type QualifiedMap = Record<string, string>

export function getQualified(allScores: Record<GroupId, (Score | null)[]>): QualifiedMap {
  const qualified: QualifiedMap = {}
  const thirds: (TeamStats & { group: GroupId })[] = []
  for (const gid of GROUP_IDS) {
    const teams  = WC2026_GROUPS[gid]
    const scores = allScores[gid] ?? Array<Score | null>(6).fill(null)
    const st     = calcStandings(teams, groupFixtures(teams), scores)
    qualified[`${gid}1`] = st[0].team
    qualified[`${gid}2`] = st[1].team
    thirds.push({ ...st[2], group: gid })
  }
  // Top 8 best 3rd-place teams (by pts → gd → gf)
  thirds.sort((a, b) => (b.pts - a.pts) || (b.gd - a.gd) || (b.gf - a.gf))
  thirds.slice(0, 8).forEach((t, i) => { qualified[`3rd${i + 1}`] = t.team })
  return qualified
}

// Which slots fill which R32 match (left half 0-7, right half 8-15)
export const BRACKET_SEEDING: [string, string][] = [
  ["A1","C2"], ["B1","D2"], ["A2","C1"], ["B2","D1"],
  ["E1","G2"], ["F1","H2"], ["E2","G1"], ["F2","H1"],
  ["I1","K2"], ["J1","L2"], ["I2","K1"], ["J2","L1"],
  ["3rd1","3rd5"], ["3rd2","3rd6"], ["3rd3","3rd7"], ["3rd4","3rd8"],
]

export type BracketMatch = { team1: string | null; team2: string | null; winner: string | null }

export function seededBracket(qualified: QualifiedMap): BracketMatch[] {
  return BRACKET_SEEDING.map(([s1, s2]) => ({
    team1: qualified[s1] ?? null,
    team2: qualified[s2] ?? null,
    winner: null,
  }))
}

// localStorage helpers
const LS_GROUPS    = "wc2026_groups"
const LS_QUALIFIED = "wc2026_qualified"

export function saveGroupScores(scores: Record<GroupId, (Score | null)[]>) {
  try { localStorage.setItem(LS_GROUPS, JSON.stringify(scores)) } catch {}
}

export function loadGroupScores(): Record<GroupId, (Score | null)[]> | null {
  try {
    const raw = localStorage.getItem(LS_GROUPS)
    if (raw) return JSON.parse(raw)
  } catch {}
  return null
}

export function saveQualified(qualified: QualifiedMap) {
  try { localStorage.setItem(LS_QUALIFIED, JSON.stringify(qualified)) } catch {}
}

export function loadQualified(): QualifiedMap | null {
  try {
    const raw = localStorage.getItem(LS_QUALIFIED)
    if (raw) return JSON.parse(raw)
  } catch {}
  return null
}
