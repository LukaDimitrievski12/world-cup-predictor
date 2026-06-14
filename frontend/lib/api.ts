const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface SimulationRow {
  team: string
  group_stage: number
  round_of_32: number
  round_of_16: number
  quarterfinal: number
  semifinal: number
  final: number
  winner: number
}

export interface TeamProfile {
  team: string
  elo: number
  last5_win: number | null
  last5_gf: number | null
  last5_ga: number | null
  rank: number | null
}

export interface ModelMetrics {
  model: string
  accuracy: number
  log_loss: number
  brier_score: number
  f1_macro: number
  precision_weighted: number
  recall_weighted: number
}

export interface PredictResult {
  home_team: string
  away_team: string
  home_win: number
  draw: number
  away_win: number
  home_elo: number
  away_elo: number
}

export async function getSimulation(): Promise<SimulationRow[]> {
  const res = await fetch(`${API}/api/simulation`)
  if (!res.ok) throw new Error("Failed to fetch simulation")
  return res.json()
}

export async function getTeams(): Promise<TeamProfile[]> {
  const res = await fetch(`${API}/api/teams`)
  if (!res.ok) throw new Error("Failed to fetch teams")
  return res.json()
}

export async function getMetrics(): Promise<ModelMetrics[]> {
  const res = await fetch(`${API}/api/metrics`)
  if (!res.ok) throw new Error("Failed to fetch metrics")
  return res.json()
}

export async function predictMatch(
  home: string,
  away: string,
  isNeutral: boolean,
  weight: number,
): Promise<PredictResult> {
  const res = await fetch(`${API}/api/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      home_team: home,
      away_team: away,
      is_neutral: isNeutral,
      tournament_weight: weight,
    }),
  })
  if (!res.ok) throw new Error("Prediction failed")
  return res.json()
}
