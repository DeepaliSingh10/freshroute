/**
 * Single source of truth for metric definitions and baseline-vs-optimized deltas.
 *
 * Formulas follow docs/EVALUATION.md §1–3 and docs/ARCHITECTURE.md §4:
 *   revenue        = Σ x·price·(1−disc)
 *   transport_cost, handling_cost, spoilage_cost as reported by the API
 *   net_revenue    = revenue − transport_cost − handling_cost − spoilage_cost
 *   spoilage_pct   = spoilage_kg / inventory_kg
 *   fulfillment    = fulfilled_kg / demand_kg
 *
 * Components must use these helpers so improvements and regressions are
 * represented consistently (a metric going the wrong way is shown as a
 * regression, not silently treated as an improvement).
 */
import type { Metrics } from '../api/types';

export type Tone = 'good' | 'bad' | 'neutral';

export interface Direction {
  improved: boolean;
  regressed: boolean;
  tone: Tone;
}

const EPSILON = 1e-9;

/** Documented net-revenue formula, recomputed from components for consistency. */
export function netRevenueOf(metrics: Metrics): number {
  return metrics.revenue - metrics.transport_cost - metrics.handling_cost - metrics.spoilage_cost;
}

export function totalCostOf(metrics: Metrics): number {
  return metrics.transport_cost + metrics.handling_cost + metrics.spoilage_cost;
}

/**
 * Classify a signed delta. `higherIsBetter` captures whether an increase is an
 * improvement (net revenue, fulfillment) or a regression (spoilage, cost).
 */
export function evaluateDelta(delta: number, higherIsBetter: boolean): Direction {
  if (Math.abs(delta) <= EPSILON) {
    return { improved: false, regressed: false, tone: 'neutral' };
  }
  const improved = higherIsBetter ? delta > 0 : delta < 0;
  return improved
    ? { improved: true, regressed: false, tone: 'good' }
    : { improved: false, regressed: true, tone: 'bad' };
}

export interface MetricDelta {
  baseline: number;
  proposed: number;
  delta: number;
  deltaPct: number | null;
  higherIsBetter: boolean;
  direction: Direction;
}

function buildDelta(
  baseline: number,
  proposed: number,
  higherIsBetter: boolean,
  pctBase = baseline,
): MetricDelta {
  const delta = proposed - baseline;
  const deltaPct = Math.abs(pctBase) > EPSILON ? delta / Math.abs(pctBase) : null;
  return { baseline, proposed, delta, deltaPct, higherIsBetter, direction: evaluateDelta(delta, higherIsBetter) };
}

export interface ComparisonSummary {
  netRevenue: MetricDelta;
  spoilage: MetricDelta;
  spoilageReductionPct: number | null;
  fulfillment: MetricDelta;
  totalCost: MetricDelta;
  revenue: MetricDelta;
}

export function compareToBaseline(proposed: Metrics, baseline: Metrics): ComparisonSummary {
  const spoilageReductionPct =
    baseline.spoilage_kg > EPSILON ? 1 - proposed.spoilage_kg / baseline.spoilage_kg : null;

  return {
    netRevenue: buildDelta(baseline.net_revenue, proposed.net_revenue, true),
    spoilage: buildDelta(baseline.spoilage_kg, proposed.spoilage_kg, false),
    spoilageReductionPct,
    fulfillment: buildDelta(baseline.fulfillment_pct, proposed.fulfillment_pct, true),
    totalCost: buildDelta(totalCostOf(baseline), totalCostOf(proposed), false),
    revenue: buildDelta(baseline.revenue, proposed.revenue, true),
  };
}
