/**
 * Builds an explainability model from data already present in the documented
 * `PlanResponse` / `/inventory` payloads.
 *
 * Design rule: we only restate fields the API actually returns (the verbatim
 * `reason`, `urgency_days`, prices, feasibility) and we label every hard
 * constraint the plan response does NOT expose as "checked server-side". We never
 * synthesise new optimizer reasoning or infer values the schema does not carry.
 * If the optional `/explain` endpoint is connected, its server-provided factors
 * are shown in addition.
 */
import type {
  Batch,
  Commodity,
  DataSource,
  Dispatch,
  Discount,
  ExplainConstraint,
  ExplainFactor,
  ExplainResult,
} from '../api/types';
import { formatCurrency, formatHours, formatKg, formatPercent } from './format';

export interface ExplainModel {
  kind: 'dispatch' | 'discount';
  heading: string;
  recommendation: string;
  reason: string;
  urgencyDays?: number;
  constraints: ExplainConstraint[];
  facts: { label: string; value: string }[];
  batch?: Batch;
  commodity?: Commodity;
  source: DataSource;
  endpointAvailable: boolean;
  endpointNote: string;
  serverFactors: ExplainFactor[];
}

export interface ExplainRefs {
  batches: Map<string, Batch>;
  commodities: Map<string, Commodity>;
  /** Dispatch rows keyed by batch_id, used to enrich discount explanations. */
  dispatchesByBatch: Map<string, Dispatch>;
  source: DataSource;
  /** null = not attempted yet; { available: false } = endpoint not connected. */
  endpoint: ExplainResult | null;
}

const inr1 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 });

function commodityLabel(commodity: Commodity | undefined, fallbackId: string): string {
  if (!commodity) return fallbackId;
  return `${commodity.name} (${commodity.perishability_class})`;
}

/**
 * The five hard constraints from docs/ARCHITECTURE.md §4. Only shelf-life
 * feasibility is exposed per dispatch (via the `feasible` flag + shelf life/travel
 * fields); the others are stated as server-side checks.
 */
export function knownConstraints(dispatch: Dispatch): ExplainConstraint[] {
  return [
    {
      name: 'Shelf-life feasibility (arrival ≥ min fresh on shelf)',
      satisfied: dispatch.feasible,
      detail: `Remaining shelf life ${inr1.format(dispatch.urgency_days)} d; transit ${inr1.format(
        dispatch.travel_time_hours,
      )} h plus handling. Feasibility is computed server-side.`,
    },
    {
      name: 'Stock availability',
      satisfied: false,
      detail: 'Not exposed per dispatch in the plan response — enforced server-side.',
    },
    {
      name: 'Destination demand upper bound',
      satisfied: false,
      detail: 'Not exposed per dispatch in the plan response — enforced server-side.',
    },
    {
      name: 'Lane / vehicle capacity',
      satisfied: false,
      detail: 'Not exposed per dispatch in the plan response — enforced server-side.',
    },
    {
      name: 'Departure / delivery windows',
      satisfied: false,
      detail: 'Not exposed per dispatch in the plan response — enforced server-side.',
    },
  ];
}

function endpointContext(endpoint: ExplainResult | null): {
  available: boolean;
  note: string;
  factors: ExplainFactor[];
} {
  if (endpoint && endpoint.available && endpoint.data) {
    return {
      available: true,
      note: 'Factor breakdown returned by the /explain endpoint.',
      factors: endpoint.data.factors,
    };
  }
  const reason = endpoint?.error ? ` (${endpoint.error})` : '';
  return {
    available: false,
    note: `The /explain endpoint is not connected${reason}. The fields below are taken verbatim from the plan response.`,
    factors: [],
  };
}

export function buildDispatchExplain(dispatch: Dispatch, refs: ExplainRefs): ExplainModel {
  const batch = refs.batches.get(dispatch.batch_id);
  const commodity = refs.commodities.get(dispatch.commodity_id);
  const impliedDiscount =
    dispatch.price_per_kg > 0 ? 1 - dispatch.effective_price_per_kg / dispatch.price_per_kg : 0;
  const endpoint = endpointContext(refs.endpoint);

  const facts: { label: string; value: string }[] = [
    { label: 'Batch', value: dispatch.batch_id },
    { label: 'Commodity', value: commodityLabel(commodity, dispatch.commodity_id) },
    { label: 'Destination', value: dispatch.destination_id },
    { label: 'Quantity', value: formatKg(dispatch.quantity_kg) },
    { label: 'Priority rank', value: `#${dispatch.priority_rank}` },
    { label: 'Remaining shelf life', value: `${inr1.format(dispatch.urgency_days)} days` },
    { label: 'Transit time', value: formatHours(dispatch.travel_time_hours) },
    { label: 'List price', value: `₹${inr1.format(dispatch.price_per_kg)}/kg` },
    { label: 'Effective price', value: `₹${inr1.format(dispatch.effective_price_per_kg)}/kg` },
    { label: 'Implied discount', value: formatPercent(impliedDiscount, 0) },
    { label: 'Transport cost', value: formatCurrency(dispatch.transport_cost) },
    { label: 'Contribution margin', value: formatCurrency(dispatch.margin) },
    { label: 'Feasible', value: dispatch.feasible ? 'Yes' : 'No (excluded from dispatch)' },
  ];
  if (batch) {
    facts.push(
      { label: 'Origin', value: batch.origin_id ?? '—' },
      { label: 'Quality grade', value: batch.quality_grade ?? '—' },
      { label: 'Batch remaining shelf life', value: `${inr1.format(batch.remaining_shelf_life_days)} days` },
    );
  }

  return {
    kind: 'dispatch',
    heading: `Dispatch · ${dispatch.batch_id}`,
    recommendation: `Ship ${formatKg(dispatch.quantity_kg)} of ${
      commodity ? commodity.name : dispatch.commodity_id
    } from ${dispatch.batch_id} to ${dispatch.destination_id}.`,
    reason: dispatch.reason,
    urgencyDays: dispatch.urgency_days,
    constraints: knownConstraints(dispatch),
    facts,
    batch,
    commodity,
    source: refs.source,
    endpointAvailable: endpoint.available,
    endpointNote: endpoint.note,
    serverFactors: endpoint.factors,
  };
}

export function buildDiscountExplain(discount: Discount, refs: ExplainRefs): ExplainModel {
  const batch = refs.batches.get(discount.batch_id);
  const commodity = batch ? refs.commodities.get(batch.commodity_id) : undefined;
  const linked = refs.dispatchesByBatch.get(discount.batch_id);
  const endpoint = endpointContext(refs.endpoint);

  const facts: { label: string; value: string }[] = [
    { label: 'Batch', value: discount.batch_id },
    { label: 'Rule', value: discount.rule_id },
    { label: 'Discount', value: formatPercent(discount.discount_pct, 0) },
    { label: 'Expected recovered value', value: formatCurrency(discount.expected_recovered_value) },
  ];
  if (commodity) facts.push({ label: 'Commodity', value: commodityLabel(commodity, commodity.commodity_id) });
  if (batch) {
    facts.push(
      { label: 'Batch quantity', value: formatKg(batch.quantity_kg) },
      { label: 'Remaining shelf life', value: `${inr1.format(batch.remaining_shelf_life_days)} days` },
      { label: 'Quality grade', value: batch.quality_grade ?? '—' },
    );
  }
  if (linked) {
    facts.push(
      { label: 'Linked destination', value: linked.destination_id },
      { label: 'Linked dispatch feasibility', value: linked.feasible ? 'Feasible' : 'Infeasible' },
    );
  }

  const constraints: ExplainConstraint[] = [
    {
      name: `Discount rule trigger (${discount.rule_id})`,
      satisfied: true,
      detail:
        'The plan reports this rule fired for the batch. Threshold values (t1/t2) are configuration, not returned per discount.',
    },
    ...(linked ? knownConstraints(linked) : []),
  ];

  return {
    kind: 'discount',
    heading: `Discount · ${discount.batch_id}`,
    recommendation: `Apply a ${formatPercent(discount.discount_pct, 0)} price reduction to batch ${
      discount.batch_id
    }${commodity ? ` (${commodity.name})` : ''} under rule ${discount.rule_id}.`,
    reason: discount.reason,
    urgencyDays: linked?.urgency_days,
    constraints,
    facts,
    batch,
    commodity,
    source: refs.source,
    endpointAvailable: endpoint.available,
    endpointNote: endpoint.note,
    serverFactors: endpoint.factors,
  };
}
