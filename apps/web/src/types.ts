// API response types — mirror apps/api/app/api/schemas.py

export interface ScenarioInfo {
  scenario_id: string
  seed: number
  split: string
}

export interface Metrics {
  method: string
  status: string
  spoilage_kg: number
  spoilage_pct: number
  expired_kg: number
  clearance_kg: number
  clearance_revenue: number
  fulfilled_kg: number
  demand_kg: number
  fulfillment_pct: number
  revenue: number
  transport_cost: number
  handling_cost: number
  spoilage_cost: number
  net_revenue: number
  violations: number
}

export interface Dispatch {
  batch_id: string
  commodity_name: string
  destination_id: string
  destination_name: string
  quantity_kg: number
  price_per_kg: number
  margin_per_kg: number
  travel_hours: number
  is_clearance: boolean
  reason: string
}

export interface Discount {
  batch_id: string
  commodity_name: string
  rule_id: string
  discount_pct: number
  quantity_kg: number
  expected_recovered_value: number
  reason: string
}

export interface PlanResponse {
  scenario_id: string
  status: string
  metrics: Metrics
  dispatches: Dispatch[]
  discounts: Discount[]
  violations: number
}

export interface EvaluateResponse {
  scenario_id: string
  baseline: string
  optimizer: Metrics
  baseline_metrics: Metrics
  compare: Record<string, number>
  violations_optimizer: number
}

export interface ReplanResponse {
  scenario_id: string
  blocked_origins: string[]
  travel_delay_hours: number
  morning_plan: Metrics
  no_replan: Metrics
  replan: Metrics
  recovery: Record<string, number>
  violations_replan: number
}

export interface Reason {
  kind: string
  ref: string
  reason: string
}

export interface ExplainResponse {
  scenario_id: string
  reasons: Reason[]
}

export interface SensPoint {
  value: number
  optimizer: { spoilage_kg: number; fulfilled_kg: number; net_revenue: number }
  baseline: { spoilage_kg: number; fulfilled_kg: number; net_revenue: number }
  spoilage_reduction_pct: number
  net_revenue_delta: number
}

export interface SensCurve {
  label: string
  range: number[]
  points: SensPoint[]
}

export interface SensitivityResponse {
  scenario_id: string
  curves: Record<string, SensCurve>
}
