/**
 * Frozen API contract between Workstream B (API) and Workstream C (frontend).
 * Mirrors docs/WORKSTREAMS.md § "Frozen interfaces" and docs/ARCHITECTURE.md § 8.
 * Do not change these shapes without consensus between owners B and C.
 */

export type Split = 'train' | 'test' | 'hidden';

export interface Scenario {
  scenario_id: string;
  seed?: number;
  now_ts?: string;
  split: Split | string;
  perturbation_profile?: string;
}

export interface Dispatch {
  batch_id: string;
  commodity_id: string;
  destination_id: string;
  quantity_kg: number;
  price_per_kg: number;
  effective_price_per_kg: number;
  travel_time_hours: number;
  transport_cost: number;
  margin: number;
  priority_rank: number;
  urgency_days: number;
  feasible: boolean;
  reason: string;
}

export interface Discount {
  batch_id: string;
  rule_id: string;
  discount_pct: number;
  expected_recovered_value: number;
  reason: string;
}

export interface Leftover {
  batch_id: string;
  quantity_kg: number;
  spoilage_cost: number;
}

export interface Validation {
  violations: string[];
  degraded: boolean;
  warnings: string[];
}

export interface Metrics {
  spoilage_kg: number;
  spoilage_pct: number;
  fulfilled_kg: number;
  fulfillment_pct: number;
  unmet_kg: number;
  revenue: number;
  transport_cost: number;
  handling_cost: number;
  spoilage_cost: number;
  net_revenue: number;
}

export interface PlanResponse {
  scenario_id: string;
  config_hash: string;
  now_ts: string;
  dispatches: Dispatch[];
  discounts: Discount[];
  leftover: Leftover[];
  validation: Validation;
  metrics: Metrics;
}

export interface PerScenarioEval {
  scenario_id: string;
  split: string;
  proposed: Metrics;
  baseline: Metrics;
}

export interface EvalAggregate {
  spoilage_pct_reduction: number;
  fulfillment_delta: number;
  net_revenue_delta: number;
  net_revenue_delta_pct: number;
  violations_total: number;
}

export interface Robustness {
  net_revenue_mean: number;
  net_revenue_p10: number;
}

export interface EvalResponse {
  per_scenario: PerScenarioEval[];
  aggregate: EvalAggregate;
  robustness?: Robustness;
}

export interface HealthResponse {
  status: string;
  version?: string;
  config_hash?: string;
}

/* ------------------------------------------------------------------ *
 * Documented endpoint shapes beyond the frozen core contract.
 * These mirror docs/ARCHITECTURE.md § 8 and docs/DATA_SPEC.md § 2.
 * They are additive: the frozen PlanResponse/EvalResponse contracts above
 * are unchanged (Owner B ↔ C agreement preserved).
 * ------------------------------------------------------------------ */

/** `GET /inventory` — commodities + batches (DATA_SPEC §2, M1). */
export interface Commodity {
  commodity_id: string;
  name: string;
  perishability_class: string;
  default_shelf_life_days: number;
  cost_basis_per_kg: number;
  handling_per_kg?: number;
}

export interface Batch {
  batch_id: string;
  commodity_id: string;
  quantity_kg: number;
  harvest_ts?: string;
  remaining_shelf_life_days: number;
  origin_id?: string;
  quality_grade?: string;
}

export interface InventoryResponse {
  commodities: Commodity[];
  batches: Batch[];
}

/** `POST /explain` — factor breakdown for one recommendation (ARCHITECTURE §8). */
export interface ExplainFactor {
  factor: string;
  value: string | number;
  contribution?: number;
  note?: string;
}

export interface ExplainConstraint {
  name: string;
  satisfied: boolean;
  detail?: string;
}

export interface ExplainResponse {
  batch_id: string;
  destination_id: string;
  recommendation: string;
  reason: string;
  urgency_days?: number;
  factors: ExplainFactor[];
  constraints?: ExplainConstraint[];
}

/** `POST /replan` — event → new plan + diff (ARCHITECTURE §7, E3). */
export type ReplanEventType = 'traffic_delay' | 'capacity_change' | 'new_order' | 'temp_spike';

export interface ReplanEvent {
  type: ReplanEventType;
  payload?: Record<string, unknown>;
}

export interface PlanDiffEntry {
  batch_id: string;
  destination_id?: string;
  change: 'added' | 'removed' | 'changed';
  reason: string;
}

export interface ReplanResponse {
  scenario_id: string;
  plan: PlanResponse;
  diff: PlanDiffEntry[];
}

/**
 * Result of *attempting* the optional `/explain` endpoint.
 * `available: false` means the endpoint is not connected; the UI must then fall
 * back to data already present in the plan response and say so — never invent
 * optimizer reasoning.
 */
export interface ExplainResult {
  available: boolean;
  data: ExplainResponse | null;
  error?: string;
}

/** Result of attempting the optional `/replan` endpoint (E3). */
export interface ReplanResult {
  available: boolean;
  data: ReplanResponse | null;
  error?: string;
}

/** Where a response came from — the UI labels demo data explicitly. */
export type DataSource = 'live' | 'demo';

export interface Sourced<T> {
  data: T;
  source: DataSource;
  /** Populated when a live request failed and demo data was substituted. */
  error?: string;
}
