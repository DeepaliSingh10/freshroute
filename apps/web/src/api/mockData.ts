/**
 * DEMO DATA — synthetic, deterministic, and schema-compatible only.
 *
 * This is NOT a performance result. It exists so the dashboard is fully usable
 * before Workstream B's live API is running. Every consumer marks responses built
 * from these fixtures with `source: 'demo'`, and the UI renders an explicit
 * "Demo data" badge. Shapes match docs/WORKSTREAMS.md frozen interfaces exactly.
 */
import type {
  Batch,
  Commodity,
  Discount,
  Dispatch,
  EvalAggregate,
  EvalResponse,
  InventoryResponse,
  Leftover,
  Metrics,
  PlanResponse,
  Scenario,
} from './types';

interface CommodityMeta {
  handling_per_kg: number;
  cost_basis_per_kg: number;
}

const COMMODITIES: Record<string, CommodityMeta> = {
  TOM: { handling_per_kg: 0.9, cost_basis_per_kg: 18 },
  SPN: { handling_per_kg: 1.4, cost_basis_per_kg: 42 },
  STR: { handling_per_kg: 1.6, cost_basis_per_kg: 120 },
  MNG: { handling_per_kg: 1.1, cost_basis_per_kg: 46 },
  POT: { handling_per_kg: 0.7, cost_basis_per_kg: 11 },
  ONN: { handling_per_kg: 0.6, cost_basis_per_kg: 9 },
};

/** Descriptive attributes from DATA_SPEC §2 commodities.csv, for demo inventory. */
const COMMODITY_INFO: Record<
  string,
  { name: string; perishability_class: string; default_shelf_life_days: number }
> = {
  TOM: { name: 'Tomato', perishability_class: 'soft_fruit', default_shelf_life_days: 7 },
  SPN: { name: 'Spinach', perishability_class: 'leafy', default_shelf_life_days: 3 },
  STR: { name: 'Strawberry', perishability_class: 'berry', default_shelf_life_days: 2.5 },
  MNG: { name: 'Mango', perishability_class: 'soft_fruit', default_shelf_life_days: 6 },
  POT: { name: 'Potato', perishability_class: 'tuber', default_shelf_life_days: 25 },
  ONN: { name: 'Onion', perishability_class: 'root', default_shelf_life_days: 30 },
};

/** Illustrative quality grades per commodity for demo inventory only. */
const QUALITY_GRADE: Record<string, string> = {
  STR: 'A',
  MNG: 'A',
  TOM: 'B',
  SPN: 'B',
  POT: 'C',
  ONN: 'C',
};

const ORIGIN_BY_COMMODITY: Record<string, string> = {
  STR: 'O-MAH',
  MNG: 'O-KON',
  TOM: 'O-NAS',
  SPN: 'O-PUN',
  POT: 'O-AGR',
  ONN: 'O-IND',
};

interface DispatchSeed {
  batch_id: string;
  commodity_id: string;
  destination_id: string;
  quantity_kg: number;
  price_per_kg: number;
  travel_time_hours: number;
  transport_per_kg: number;
  urgency_days: number;
  discount_pct: number;
  feasible: boolean;
  reason: string;
}

interface ScenarioSeed {
  scenario: Scenario;
  demand_kg: number;
  inventory_kg: number;
  handling_days: number;
  /** Baseline (FEFO + nearest-first greedy) multipliers vs the optimized plan. */
  baseline: {
    fulfilledFactor: number;
    revenueFactor: number;
    spoilageFactor: number;
    transportFactor: number;
    handlingFactor: number;
  };
  dispatches: DispatchSeed[];
}

const SCENARIO_SEEDS: ScenarioSeed[] = [
  {
    scenario: {
      scenario_id: 'demo-train-clear-day',
      split: 'train',
      seed: 1001,
      now_ts: '2026-03-02T06:00:00Z',
      perturbation_profile: 'none',
    },
    demand_kg: 9000,
    inventory_kg: 11000,
    handling_days: 0.15,
    baseline: {
      fulfilledFactor: 0.84,
      revenueFactor: 0.9,
      spoilageFactor: 1.42,
      transportFactor: 1.06,
      handlingFactor: 1.0,
    },
    dispatches: [
      seed('B-1001', 'STR', 'D-MUM', 380, 210, 1.4, 3.1, 0.4, 0.3, true,
        'Strawberry batch expires in 0.9d; Mumbai lane removes only 1.4h transit, leaving 0.84d on arrival — feasible under the 0.25d buffer. 30% discount clears stock that would otherwise spoil.'),
      seed('B-1002', 'SPN', 'D-PUN', 520, 68, 0.8, 1.9, 0.6, 0.15, true,
        'Spinach is the most perishable class; Pune demand is open and the lane is the shortest, so it is dispatched first at a 15% recovery discount.'),
      seed('B-1003', 'TOM', 'D-NAS', 1400, 34, 2.2, 2.4, 1.9, 0, true,
        'Tomato has ample remaining shelf life (3.4d); Nashik offers the best net margin after transport, so it takes the largest allocation.'),
      seed('B-1004', 'MNG', 'D-DEL', 900, 96, 9.5, 6.8, 2.6, 0, true,
        'Mango grade A: high price at Delhi outweighs the longer 9.5h transit; arrival shelf life still exceeds the 2d minimum.'),
      seed('B-1005', 'ONN', 'D-PUN', 1100, 26, 0.8, 1.1, 4.1, 0, true,
        'Onion is a root/tuber class with long shelf life; short lane and steady demand make it a low-risk filler.'),
      seed('B-1006', 'POT', 'D-NAS', 950, 22, 2.2, 1.3, 5.0, 0, true,
        'Potato has the longest shelf life; allocated to Nashik to absorb residual demand after higher-margin commodities.'),
      seed('B-1007', 'STR', 'D-BLR', 260, 222, 13.0, 8.4, 0.4, 0.3, false,
        'EXCLUDED: 13h transit plus handling exceeds the 0.9d remaining shelf life — arrival would breach the minimum fresh-on-shelf requirement.'),
      seed('B-1008', 'SPN', 'D-DEL', 300, 74, 9.5, 6.1, 0.6, 0.15, false,
        'EXCLUDED: Delhi lane cannot deliver spinach before its shelf life ends; retained for discount/local sale instead.'),
      seed('B-1009', 'TOM', 'D-MUM', 700, 38, 1.4, 2.0, 1.9, 0, true,
        'Tomato surplus reallocated to Mumbai where price is slightly higher than Nashik after transport.'),
    ],
  },
  {
    scenario: {
      scenario_id: 'demo-test-demand-spike',
      split: 'test',
      seed: 2002,
      now_ts: '2026-03-09T06:00:00Z',
      perturbation_profile: 'demand_multiplier=1.4,event_spike=festival',
    },
    demand_kg: 12600,
    inventory_kg: 13200,
    handling_days: 0.15,
    baseline: {
      fulfilledFactor: 0.79,
      revenueFactor: 0.88,
      spoilageFactor: 1.55,
      transportFactor: 1.09,
      handlingFactor: 1.0,
    },
    dispatches: [
      seed('B-2001', 'STR', 'D-MUM', 420, 228, 1.4, 3.1, 0.5, 0.3, true,
        'Festival demand spike: strawberry clears at peak price; 30% discount still beats spoilage given 0.9d shelf life.'),
      seed('B-2002', 'MNG', 'D-DEL', 1150, 104, 9.5, 6.8, 2.8, 0, true,
        'Mango demand is up 40% at Delhi; allocation increased to capture the higher festival price.'),
      seed('B-2003', 'SPN', 'D-PUN', 610, 72, 0.8, 1.9, 0.6, 0.15, true,
        'Spinach prioritized by perishability; Pune absorbs the short-shelf-life volume first.'),
      seed('B-2004', 'TOM', 'D-NAS', 1550, 37, 2.2, 2.4, 2.0, 0, true,
        'Tomato takes the largest balance: strong demand and safe shelf life.'),
      seed('B-2005', 'ONN', 'D-MUM', 1250, 28, 1.4, 1.4, 4.3, 0, true,
        'Onion fills Mumbai residual demand at a stable price.'),
      seed('B-2006', 'POT', 'D-NAS', 1050, 23, 2.2, 1.3, 5.1, 0, true,
        'Potato absorbs remaining Nashik demand.'),
      seed('B-2007', 'STR', 'D-BLR', 240, 240, 13.0, 8.4, 0.5, 0.3, false,
        'EXCLUDED: transit exceeds remaining shelf life under the spike-adjusted plan.'),
      seed('B-2008', 'TOM', 'D-MUM', 820, 41, 1.4, 2.0, 2.0, 0, true,
        'Tomato reallocated to Mumbai to serve the spike without exceeding lane capacity.'),
    ],
  },
  {
    scenario: {
      scenario_id: 'demo-hidden-stress',
      split: 'hidden',
      seed: 3003,
      now_ts: '2026-03-16T06:00:00Z',
      perturbation_profile: 'demand_multiplier=1.4,travel_delay=6h,temp_spike=0.5d,noise=5%',
    },
    demand_kg: 13100,
    inventory_kg: 13800,
    handling_days: 0.25,
    baseline: {
      fulfilledFactor: 0.74,
      revenueFactor: 0.85,
      spoilageFactor: 1.68,
      transportFactor: 1.12,
      handlingFactor: 1.0,
    },
    dispatches: [
      seed('B-3001', 'STR', 'D-MUM', 300, 226, 1.4, 3.1, 0.3, 0.3, true,
        'Temperature spike cut shelf life by 0.5d; only the nearest lane keeps strawberry feasible. Dispatched first.'),
      seed('B-3002', 'SPN', 'D-PUN', 480, 71, 0.8, 1.9, 0.4, 0.15, true,
        'Spinach prioritized; stress-adjusted feasibility leaves a thin but positive margin.'),
      seed('B-3003', 'MNG', 'D-DEL', 980, 101, 15.5, 6.8, 2.4, 0, true,
        'Mango absorbs a 6h travel delay; still feasible because remaining shelf life is long enough.'),
      seed('B-3004', 'TOM', 'D-NAS', 1300, 36, 8.2, 2.4, 1.7, 0, true,
        'Tomato reallocated given the delayed Mumbai lane; Nashik is now the higher net-margin option.'),
      seed('B-3005', 'ONN', 'D-MUM', 1050, 27, 7.4, 1.4, 3.9, 0, true,
        'Onion tolerates the delay; fills Mumbai demand.'),
      seed('B-3006', 'POT', 'D-NAS', 900, 22, 8.2, 1.3, 4.8, 0, true,
        'Potato remains a safe long-shelf-life filler.'),
      seed('B-3007', 'STR', 'D-BLR', 180, 238, 19.0, 8.4, 0.3, 0.3, false,
        'EXCLUDED: delay + temp spike make the Bengaluru lane infeasible by a wide margin.'),
      seed('B-3008', 'SPN', 'D-DEL', 260, 76, 15.5, 6.1, 0.4, 0.15, false,
        'EXCLUDED: lettuce/spinach cannot survive the delayed Delhi lane under stress.'),
      seed('B-3009', 'MNG', 'D-MUM', 520, 92, 7.4, 5.0, 2.4, 0, true,
        'Mango split across Mumbai to hedge the long Delhi lane under uncertainty.'),
    ],
  },
];

function seed(
  batch_id: string,
  commodity_id: string,
  destination_id: string,
  quantity_kg: number,
  price_per_kg: number,
  travel_time_hours: number,
  transport_per_kg: number,
  urgency_days: number,
  discount_pct: number,
  feasible: boolean,
  reason: string,
): DispatchSeed {
  return {
    batch_id,
    commodity_id,
    destination_id,
    quantity_kg,
    price_per_kg,
    travel_time_hours,
    transport_per_kg,
    urgency_days,
    discount_pct,
    feasible,
    reason,
  };
}

function buildDispatches(seedData: ScenarioSeed): Dispatch[] {
  const ordered = [...seedData.dispatches].sort((a, b) => {
    if (a.feasible !== b.feasible) return a.feasible ? -1 : 1;
    return a.urgency_days - b.urgency_days;
  });

  return ordered.map((d, index) => {
    const meta = COMMODITIES[d.commodity_id] ?? { handling_per_kg: 1, cost_basis_per_kg: 10 };
    const effective_price_per_kg = round2(d.price_per_kg * (1 - d.discount_pct));
    const transport_cost = round2(d.quantity_kg * d.transport_per_kg);
    const margin = round2(
      d.quantity_kg * (effective_price_per_kg - d.transport_per_kg - meta.handling_per_kg),
    );
    return {
      batch_id: d.batch_id,
      commodity_id: d.commodity_id,
      destination_id: d.destination_id,
      quantity_kg: d.quantity_kg,
      price_per_kg: d.price_per_kg,
      effective_price_per_kg,
      travel_time_hours: d.travel_time_hours,
      transport_cost,
      margin,
      priority_rank: index + 1,
      urgency_days: d.urgency_days,
      feasible: d.feasible,
      reason: d.reason,
    };
  });
}

function buildDiscounts(seedData: ScenarioSeed): Discount[] {
  return seedData.dispatches
    .filter((d) => d.discount_pct > 0)
    .map((d) => {
      const effective = d.price_per_kg * (1 - d.discount_pct);
      const recovered = round2(d.quantity_kg * effective * 0.5);
      const rule_id =
        d.discount_pct >= 0.3 ? 'DISCOUNT_T2_RSL_LE_1.5D' : 'DISCOUNT_T1_RSL_LE_3D';
      return {
        batch_id: d.batch_id,
        rule_id,
        discount_pct: d.discount_pct,
        expected_recovered_value: recovered,
        reason: d.feasible
          ? `Rule ${rule_id}: remaining shelf life below threshold — a ${Math.round(
              d.discount_pct * 100,
            )}% price cut recovers value on ${d.quantity_kg}kg that would otherwise go unsold.`
          : `Rule ${rule_id}: no feasible lane for ${d.batch_id} to ${d.destination_id}; discounted at origin to recover ${Math.round(
              d.discount_pct * 100,
            )}% off rather than accept full spoilage.`,
      };
    });
}

function buildMetrics(seedData: ScenarioSeed, dispatches: Dispatch[]): Metrics {
  const shipped = dispatches.filter((d) => d.feasible);
  const fulfilled_kg = round2(shipped.reduce((sum, d) => sum + d.quantity_kg, 0));
  const revenue = round2(shipped.reduce((sum, d) => sum + d.quantity_kg * d.effective_price_per_kg, 0));
  const transport_cost = round2(shipped.reduce((sum, d) => sum + d.transport_cost, 0));
  const handling_cost = round2(
    shipped.reduce(
      (sum, d) => sum + d.quantity_kg * (COMMODITIES[d.commodity_id]?.handling_per_kg ?? 1),
      0,
    ),
  );
  const spoilage_kg = round2(Math.max(0, seedData.inventory_kg - fulfilled_kg));
  const spoilage_cost = round2(
    spoilage_kg * averageCostBasis(seedData.dispatches.map((d) => d.commodity_id)),
  );
  const unmet_kg = round2(Math.max(0, seedData.demand_kg - fulfilled_kg));
  const net_revenue = round2(revenue - transport_cost - handling_cost - spoilage_cost);

  return {
    spoilage_kg,
    spoilage_pct: round4(spoilage_kg / seedData.inventory_kg),
    fulfilled_kg,
    fulfillment_pct: round4(fulfilled_kg / seedData.demand_kg),
    unmet_kg,
    revenue,
    transport_cost,
    handling_cost,
    spoilage_cost,
    net_revenue,
  };
}

function baselineMetrics(seedData: ScenarioSeed, proposed: Metrics): Metrics {
  const b = seedData.baseline;
  const fulfilled_kg = round2(proposed.fulfilled_kg * b.fulfilledFactor);
  const revenue = round2(proposed.revenue * b.revenueFactor);
  const transport_cost = round2(proposed.transport_cost * b.transportFactor);
  const handling_cost = round2(proposed.handling_cost * b.handlingFactor);
  const spoilage_kg = round2(proposed.spoilage_kg * b.spoilageFactor);
  const spoilage_cost = round2(proposed.spoilage_cost * b.spoilageFactor);
  const unmet_kg = round2(Math.max(0, seedData.demand_kg - fulfilled_kg));
  const net_revenue = round2(revenue - transport_cost - handling_cost - spoilage_cost);

  return {
    spoilage_kg,
    spoilage_pct: round4(spoilage_kg / seedData.inventory_kg),
    fulfilled_kg,
    fulfillment_pct: round4(fulfilled_kg / seedData.demand_kg),
    unmet_kg,
    revenue,
    transport_cost,
    handling_cost,
    spoilage_cost,
    net_revenue,
  };
}

function buildLeftover(seedData: ScenarioSeed, proposed: Metrics): Leftover[] {
  const infeasible = seedData.dispatches.filter((d) => !d.feasible);
  const rows: Leftover[] = infeasible.map((d) => ({
    batch_id: d.batch_id,
    quantity_kg: d.quantity_kg,
    spoilage_cost: round2(d.quantity_kg * (COMMODITIES[d.commodity_id]?.cost_basis_per_kg ?? 10)),
  }));
  const flagged = rows.reduce((sum, r) => sum + r.quantity_kg, 0);
  const remainder = round2(Math.max(0, proposed.spoilage_kg - flagged));
  if (remainder > 0) {
    rows.push({
      batch_id: 'B-UNALLOCATED',
      quantity_kg: remainder,
      spoilage_cost: round2(remainder * averageCostBasis(seedData.dispatches.map((d) => d.commodity_id))),
    });
  }
  return rows;
}

function aggregateEval(proposed: Metrics, baseline: Metrics): EvalAggregate {
  return {
    spoilage_pct_reduction: round4(1 - proposed.spoilage_kg / Math.max(1, baseline.spoilage_kg)),
    fulfillment_delta: round4(proposed.fulfillment_pct - baseline.fulfillment_pct),
    net_revenue_delta: round2(proposed.net_revenue - baseline.net_revenue),
    net_revenue_delta_pct: round4(
      (proposed.net_revenue - baseline.net_revenue) / Math.max(1, Math.abs(baseline.net_revenue)),
    ),
    violations_total: 0,
  };
}

function averageCostBasis(commodityIds: string[]): number {
  if (commodityIds.length === 0) return 10;
  const total = commodityIds.reduce(
    (sum, id) => sum + (COMMODITIES[id]?.cost_basis_per_kg ?? 10),
    0,
  );
  return total / commodityIds.length;
}

function hashSeed(seedData: ScenarioSeed): string {
  const base = `${seedData.scenario.scenario_id}:${seedData.scenario.seed}`;
  let h = 0x811c9dc5;
  for (let i = 0; i < base.length; i += 1) {
    h ^= base.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}

export const DEMO_SCENARIOS: Scenario[] = SCENARIO_SEEDS.map((s) => s.scenario);

export function getDemoPlan(scenarioId: string): PlanResponse {
  const seedData = findSeed(scenarioId);
  const dispatches = buildDispatches(seedData);
  const metrics = buildMetrics(seedData, dispatches);
  const discounts = buildDiscounts(seedData);
  const leftover = buildLeftover(seedData, metrics);
  const degraded = seedData.scenario.perturbation_profile?.includes('noise') ?? false;

  return {
    scenario_id: seedData.scenario.scenario_id,
    config_hash: hashSeed(seedData),
    now_ts: seedData.scenario.now_ts ?? new Date().toISOString(),
    dispatches,
    discounts,
    leftover,
    validation: {
      violations: [],
      degraded,
      warnings: degraded
        ? ['Synthetic sensor noise (±5%) applied to shelf-life readings; values clamped before feasibility checks.']
        : [],
    },
    metrics,
  };
}

export function getDemoEval(scenarioIds: string[]): EvalResponse {
  const per_scenario = scenarioIds.map((id) => {
    const seedData = findSeed(id);
    const dispatches = buildDispatches(seedData);
    const proposed = buildMetrics(seedData, dispatches);
    const baseline = baselineMetrics(seedData, proposed);
    return {
      scenario_id: seedData.scenario.scenario_id,
      split: seedData.scenario.split,
      proposed,
      baseline,
    };
  });

  const n = Math.max(1, per_scenario.length);
  const aggregate = per_scenario.reduce(
    (acc, row) => {
      const a = aggregateEval(row.proposed, row.baseline);
      acc.spoilage_pct_reduction += a.spoilage_pct_reduction;
      acc.fulfillment_delta += a.fulfillment_delta;
      acc.net_revenue_delta += a.net_revenue_delta;
      acc.net_revenue_delta_pct += a.net_revenue_delta_pct;
      acc.violations_total += a.violations_total;
      return acc;
    },
    {
      spoilage_pct_reduction: 0,
      fulfillment_delta: 0,
      net_revenue_delta: 0,
      net_revenue_delta_pct: 0,
      violations_total: 0,
    } as EvalAggregate,
  );

  aggregate.spoilage_pct_reduction = round4(aggregate.spoilage_pct_reduction / n);
  aggregate.fulfillment_delta = round4(aggregate.fulfillment_delta / n);
  aggregate.net_revenue_delta_pct = round4(aggregate.net_revenue_delta_pct / n);

  // NOTE: no `robustness` block is fabricated here. Confidence-interval-like
  // statistics require the Monte Carlo harness (E4, backend); inventing them in
  // demo data would present illustrative numbers as verified results.
  return {
    per_scenario,
    aggregate,
  };
}

export function findDemoScenario(scenarioId: string): Scenario | undefined {
  return DEMO_SCENARIOS.find((s) => s.scenario_id === scenarioId);
}

/**
 * Demo `/inventory` payload (DATA_SPEC §2, M1): commodities + batches.
 * Batches are derived from the demo scenario seeds so batch details line up with
 * the dispatch rows. Deterministic; clearly labelled as demo data by the client.
 */
export function getDemoInventory(): InventoryResponse {
  const commodities: Commodity[] = Object.entries(COMMODITY_INFO).map(([id, info]) => ({
    commodity_id: id,
    name: info.name,
    perishability_class: info.perishability_class,
    default_shelf_life_days: info.default_shelf_life_days,
    cost_basis_per_kg: COMMODITIES[id]?.cost_basis_per_kg ?? 10,
    handling_per_kg: COMMODITIES[id]?.handling_per_kg,
  }));

  const seen = new Set<string>();
  const batches: Batch[] = [];
  for (const scenario of SCENARIO_SEEDS) {
    for (const d of scenario.dispatches) {
      if (seen.has(d.batch_id)) continue;
      seen.add(d.batch_id);
      batches.push({
        batch_id: d.batch_id,
        commodity_id: d.commodity_id,
        quantity_kg: d.quantity_kg,
        harvest_ts: scenario.scenario.now_ts,
        remaining_shelf_life_days: d.urgency_days,
        origin_id: ORIGIN_BY_COMMODITY[d.commodity_id] ?? 'O-UNK',
        quality_grade: QUALITY_GRADE[d.commodity_id] ?? 'B',
      });
    }
  }

  return { commodities, batches };
}

function findSeed(scenarioId: string): ScenarioSeed {
  const found = SCENARIO_SEEDS.find((s) => s.scenario.scenario_id === scenarioId);
  if (found) return found;
  const fallback = SCENARIO_SEEDS[0];
  return { ...fallback, scenario: { ...fallback.scenario, scenario_id: scenarioId } };
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}
function round4(value: number): number {
  return Math.round(value * 10000) / 10000;
}
