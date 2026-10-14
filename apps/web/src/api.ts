import type {
  EvaluateResponse,
  ExplainResponse,
  PlanResponse,
  ReplanResponse,
  ScenarioInfo,
  SensitivityResponse,
} from './types'

const BASE = (import.meta.env.VITE_API_BASE as string) ?? '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`)
  return (await res.json()) as T
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`)
  return (await res.json()) as T
}

export const api = {
  health: () => get<{ status: string; version: string; cost_model_hash: string }>('/health'),
  scenarios: () =>
    get<{ scenarios: ScenarioInfo[] }>('/scenarios').then((r) => r.scenarios),
  inventory: (scenarioId: string) =>
    get<{ scenario_id: string; n_batches: number; total_inventory_kg: number }>(
      `/inventory?scenario_id=${encodeURIComponent(scenarioId)}`,
    ),
  plan: (scenarioId: string, includeClearance = true) =>
    post<PlanResponse>('/plan', { scenario_id: scenarioId, include_clearance: includeClearance }),
  evaluate: (scenarioId: string, baseline = 'fefo') =>
    post<EvaluateResponse>('/evaluate', { scenario_id: scenarioId, baseline }),
  replan: (scenarioId: string, travelDelayHours = 6.0) =>
    post<ReplanResponse>('/replan', {
      scenario_id: scenarioId,
      blocked_origins: [],
      travel_delay_hours: travelDelayHours,
    }),
  explain: (scenarioId: string) =>
    get<ExplainResponse>(`/explain?scenario_id=${encodeURIComponent(scenarioId)}`),
  sensitivity: (scenarioId: string, factor?: string) =>
    post<SensitivityResponse>('/sensitivity', { scenario_id: scenarioId, factor }),
}
