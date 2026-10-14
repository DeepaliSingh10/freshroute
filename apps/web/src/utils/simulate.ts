/**
 * Local, disclosed simulations for the sensitivity panel and the demo replan
 * feed. These run entirely in the browser and are clearly labelled in the UI.
 *
 * They are NOT the optimizer. Every function returns the `assumptions` it used so
 * the UI can show exactly how a number was produced, and results are always
 * marked "illustrative". No statistical confidence intervals are produced.
 */
import type { Dispatch, PlanDiffEntry, PlanResponse, ReplanEvent } from '../api/types';

export interface SensitivityInputs {
  demandMultiplier: number;
  travelDelayHours: number;
  priceShockPct: number;
}

export interface SimulatedMetrics {
  fulfilled_kg: number;
  fulfillment_pct: number;
  unmet_kg: number;
  spoilage_kg: number;
  spoilage_pct: number;
  revenue: number;
  transport_cost: number;
  handling_cost: number;
  spoilage_cost: number;
  net_revenue: number;
}

export interface AffectedDispatch {
  batch_id: string;
  destination_id: string;
  reason: string;
}

export interface SimulationResult {
  metrics: SimulatedMetrics;
  affected: AffectedDispatch[];
  assumptions: string[];
}

const HANDLING_BUFFER_DAYS = 0.25;

function isFeasibleUnderDelay(dispatch: Dispatch, travelDelayHours: number): boolean {
  const transitDays = (dispatch.travel_time_hours + travelDelayHours) / 24;
  return dispatch.feasible && transitDays + HANDLING_BUFFER_DAYS <= dispatch.urgency_days;
}

export function simulatePlan(plan: PlanResponse, inputs: SensitivityInputs): SimulationResult {
  const { metrics } = plan;
  const inventoryProxy = metrics.fulfilled_kg + metrics.spoilage_kg;
  const demandProxy = Math.max(1, metrics.fulfilled_kg + metrics.unmet_kg);

  const usable = plan.dispatches.filter((d) => isFeasibleUnderDelay(d, inputs.travelDelayHours));
  const affected: AffectedDispatch[] = plan.dispatches
    .filter((d) => d.feasible && !isFeasibleUnderDelay(d, inputs.travelDelayHours))
    .map((d) => ({
      batch_id: d.batch_id,
      destination_id: d.destination_id,
      reason: `Transit becomes ${(d.travel_time_hours + inputs.travelDelayHours).toFixed(1)} h, exceeding ${d.urgency_days.toFixed(
        1,
      )} d of remaining shelf life.`,
    }));

  const fulfilled = usable.reduce((sum, d) => sum + d.quantity_kg, 0);
  const demand = demandProxy * inputs.demandMultiplier;

  const handlingPerKg = metrics.fulfilled_kg > 0 ? metrics.handling_cost / metrics.fulfilled_kg : 0;
  const transportPerKg = metrics.fulfilled_kg > 0 ? metrics.transport_cost / metrics.fulfilled_kg : 0;
  const spoilageCostPerKg = metrics.spoilage_kg > 0 ? metrics.spoilage_cost / metrics.spoilage_kg : 0;

  const revenue =
    usable.reduce((sum, d) => sum + d.quantity_kg * d.effective_price_per_kg, 0) *
    (1 + inputs.priceShockPct);
  const transport_cost = transportPerKg * fulfilled;
  const handling_cost = handlingPerKg * fulfilled;
  const spoilage_kg = Math.max(0, inventoryProxy - fulfilled);
  const spoilage_cost = spoilageCostPerKg * spoilage_kg;
  const unmet_kg = Math.max(0, demand - fulfilled);

  const simulated: SimulatedMetrics = {
    fulfilled_kg: round2(fulfilled),
    fulfillment_pct: round4(Math.min(fulfilled, demand) / demand),
    unmet_kg: round2(unmet_kg),
    spoilage_kg: round2(spoilage_kg),
    spoilage_pct: round4(inventoryProxy > 0 ? spoilage_kg / inventoryProxy : 0),
    revenue: round2(revenue),
    transport_cost: round2(transport_cost),
    handling_cost: round2(handling_cost),
    spoilage_cost: round2(spoilage_cost),
    net_revenue: round2(revenue - transport_cost - handling_cost - spoilage_cost),
  };

  return {
    metrics: simulated,
    affected,
    assumptions: [
      'Dispatches remain feasible only if transit + the simulated delay + a 0.25 d handling buffer fit within remaining shelf life.',
      'Demand is scaled by the multiplier; fulfilment is capped by the quantity actually dispatched.',
      'Revenue is scaled by the price shock; handling/transport are priced per kg from the current plan.',
      `Spoilage uses the inventory proxy ${Math.round(inventoryProxy)} kg from the current plan.`,
    ],
  };
}

/** Low and high illustrative net-revenue outcomes across the sensitivity bounds. */
export function sensitivityRange(plan: PlanResponse): { low: number; point: number; high: number } {
  const lowInputs: SensitivityInputs = { demandMultiplier: 1.5, travelDelayHours: 12, priceShockPct: -0.2 };
  const highInputs: SensitivityInputs = { demandMultiplier: 0.7, travelDelayHours: 0, priceShockPct: 0.15 };
  const low = simulatePlan(plan, lowInputs).metrics.net_revenue;
  const high = simulatePlan(plan, highInputs).metrics.net_revenue;
  return {
    low: Math.min(low, high),
    high: Math.max(low, high),
    point: plan.metrics.net_revenue,
  };
}

export interface ReplanSimulation {
  entries: PlanDiffEntry[];
  summary: string;
  assumptions: string[];
  /** True when the event cannot be evaluated without the real optimizer. */
  requiresOptimizer: boolean;
}

export function simulateReplan(plan: PlanResponse, event: ReplanEvent): ReplanSimulation {
  const feasible = plan.dispatches.filter((d) => d.feasible);

  switch (event.type) {
    case 'traffic_delay': {
      const hours = Number(event.payload?.hours ?? 6);
      const removed = feasible.filter((d) => (d.travel_time_hours + hours) / 24 > d.urgency_days - HANDLING_BUFFER_DAYS);
      return {
        entries: removed.map((d) => ({
          batch_id: d.batch_id,
          destination_id: d.destination_id,
          change: 'removed' as const,
          reason: `Illustrative rule: transit ${(d.travel_time_hours + hours).toFixed(1)} h no longer fits ${d.urgency_days.toFixed(
            1,
          )} d shelf life.`,
        })),
        summary: `${hours} h travel delay would make ${removed.length} dispatch${
          removed.length === 1 ? '' : 'es'
        } infeasible.`,
        assumptions: [`A flat +${hours} h is applied to every lane.`],
        requiresOptimizer: false,
      };
    }
    case 'temp_spike': {
      const penalty = Number(event.payload?.rsl_penalty_days ?? 0.5);
      const removed = feasible.filter((d) => d.urgency_days - penalty <= HANDLING_BUFFER_DAYS);
      return {
        entries: removed.map((d) => ({
          batch_id: d.batch_id,
          destination_id: d.destination_id,
          change: 'removed' as const,
          reason: `Illustrative rule: −${penalty} d shelf life leaves ${(d.urgency_days - penalty).toFixed(2)} d.`,
        })),
        summary: `A −${penalty} d shelf-life penalty would make ${removed.length} dispatch${
          removed.length === 1 ? '' : 'es'
        } infeasible.`,
        assumptions: [`A flat −${penalty} d is applied to every batch's remaining shelf life.`],
        requiresOptimizer: false,
      };
    }
    case 'capacity_change': {
      if (feasible.length === 0) {
        return { entries: [], summary: 'No feasible dispatches to replan.', assumptions: [], requiresOptimizer: false };
      }
      const lowest = [...feasible].sort((a, b) => a.margin - b.margin)[0];
      return {
        entries: [
          {
            batch_id: lowest.batch_id,
            destination_id: lowest.destination_id,
            change: 'removed' as const,
            reason: 'Illustrative rule: the lowest-margin dispatch is dropped first when capacity is reduced.',
          },
        ],
        summary: `A capacity reduction would first drop the lowest-margin dispatch (${lowest.batch_id}).`,
        assumptions: ['Capacity is reduced by at least one vehicle; only the single lowest-margin dispatch is shown.'],
        requiresOptimizer: false,
      };
    }
    case 'new_order':
    default:
      return {
        entries: [],
        summary:
          'A new order cannot be allocated in the demo — optimising new demand requires the /replan endpoint. The event is recorded only.',
        assumptions: [],
        requiresOptimizer: true,
      };
  }
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}
function round4(value: number): number {
  return Math.round(value * 10000) / 10000;
}
