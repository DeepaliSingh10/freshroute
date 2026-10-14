"""Metric computation for a plan, using the shared cost model.

Reported net_revenue EXCLUDES the optimizer's internal unmet-demand penalty
(that penalty only steers the objective; it is not a real economic cost).

Two special quantities:
  - `expired_kg`: shelf-life-blind cargo that arrives after expiry (zero revenue,
    transport/handling still paid) — the naive-baseline failure mode (MVP M3).
  - `clearance_kg` / `clearance_revenue`: at-risk stock recovered through the local
    clearance channel (MVP M4). Clearance is a salvage channel, NOT market demand, so it
    is excluded from the demand/fulfillment denominator.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict

from ..data.constants import GRADE_PRICE_FACTOR
from ..data.cost_model import CostModel
from ..data.models import Instance
from ..optimizer.feasibility import is_feasible
from ..optimizer.types import Plan


@dataclass
class Metrics:
    method: str
    status: str
    spoilage_kg: float
    spoilage_pct: float
    expired_kg: float
    clearance_kg: float
    clearance_revenue: float
    fulfilled_kg: float
    demand_kg: float
    unmet_kg: float
    fulfillment_pct: float
    revenue: float
    transport_cost: float
    handling_cost: float
    spoilage_cost: float
    net_revenue: float
    violations: int = 0
    runtime_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def compute_metrics(instance: Instance, cost_model: CostModel, plan: Plan) -> Metrics:
    demand = instance.demand_lookup()
    total_inventory = sum(b.quantity_kg for b in instance.batches.values())

    revenue = 0.0
    transport = 0.0
    handling = 0.0
    fulfilled = 0.0
    expired = 0.0
    clearance_kg = 0.0
    clearance_revenue = 0.0

    for disp in plan.dispatches:
        b = instance.batches[disp.batch_id]
        commodity = instance.commodities[b.commodity_id]
        dem = demand.get((disp.destination_id, b.commodity_id))
        if dem is None:
            continue
        d = instance.destinations[disp.destination_id]
        lane = instance.lane(b.origin_id, disp.destination_id)
        eff_price = dem.price_per_kg * GRADE_PRICE_FACTOR.get(b.quality_grade, 1.0)

        transport += disp.quantity_kg * lane.cost_per_kg
        handling += disp.quantity_kg * commodity.handling_per_kg

        if d.is_clearance:
            clearance_kg += disp.quantity_kg
            clearance_revenue += disp.quantity_kg * eff_price
            revenue += disp.quantity_kg * eff_price
        elif is_feasible(
            b.remaining_shelf_life_days,
            lane.travel_time_hours,
            d.min_days_fresh_on_shelf,
            cost_model,
        ):
            revenue += disp.quantity_kg * eff_price
            fulfilled += disp.quantity_kg
        else:
            expired += disp.quantity_kg

    # Leftover per batch (stock minus everything dispatched).
    shipped = plan.shipped_by_batch()
    leftover: Dict[str, float] = {}
    for b in instance.batches.values():
        leftover[b.batch_id] = plan.leftover.get(
            b.batch_id, max(0.0, b.quantity_kg - shipped.get(b.batch_id, 0.0))
        )

    spoilage_kg = 0.0
    spoilage_cost = 0.0

    # Expired on arrival (non-clearance infeasible shipments).
    for disp in plan.dispatches:
        b = instance.batches[disp.batch_id]
        d = instance.destinations[disp.destination_id]
        if d.is_clearance:
            continue
        lane = instance.lane(b.origin_id, disp.destination_id)
        commodity = instance.commodities[b.commodity_id]
        if not is_feasible(
            b.remaining_shelf_life_days,
            lane.travel_time_hours,
            d.min_days_fresh_on_shelf,
            cost_model,
        ):
            frac = cost_model.spoilage_fraction(commodity.perishability_class)
            spoilage_kg += disp.quantity_kg * frac
            spoilage_cost += disp.quantity_kg * commodity.cost_basis_per_kg * frac

    # Spoiled at origin (leftover).
    for bid, qty in leftover.items():
        b = instance.batches[bid]
        commodity = instance.commodities[b.commodity_id]
        frac = cost_model.spoilage_fraction(commodity.perishability_class)
        spoilage_kg += qty * frac
        spoilage_cost += qty * commodity.cost_basis_per_kg * frac

    # Demand denominator excludes clearance (it is salvage, not market demand).
    demand_kg = sum(
        d.demand_kg
        for d in instance.demands
        if not instance.destinations[d.destination_id].is_clearance
    )
    unmet = max(0.0, demand_kg - fulfilled)

    return Metrics(
        method=plan.method,
        status=plan.status,
        spoilage_kg=round(spoilage_kg, 2),
        spoilage_pct=round((spoilage_kg / total_inventory) if total_inventory else 0.0, 4),
        expired_kg=round(expired, 2),
        clearance_kg=round(clearance_kg, 2),
        clearance_revenue=round(clearance_revenue, 2),
        fulfilled_kg=round(fulfilled, 2),
        demand_kg=round(demand_kg, 2),
        unmet_kg=round(unmet, 2),
        fulfillment_pct=round((fulfilled / demand_kg) if demand_kg else 0.0, 4),
        revenue=round(revenue, 2),
        transport_cost=round(transport, 2),
        handling_cost=round(handling, 2),
        spoilage_cost=round(spoilage_cost, 2),
        net_revenue=round(revenue - transport - handling - spoilage_cost, 2),
        violations=0,
        runtime_ms=plan.runtime_ms,
    )


def compare(proposed: Metrics, baseline: Metrics) -> dict:
    """Proposed-vs-baseline deltas used by the runner and evaluation harness."""

    def pct_reduction(base: float, new: float) -> float:
        return (1.0 - (new / base)) if base else 0.0

    return {
        "spoilage_pct_reduction": round(pct_reduction(baseline.spoilage_kg, proposed.spoilage_kg), 4),
        "fulfillment_delta": round(proposed.fulfillment_pct - baseline.fulfillment_pct, 4),
        "net_revenue_delta": round(proposed.net_revenue - baseline.net_revenue, 2),
        "net_revenue_delta_pct": round(
            ((proposed.net_revenue - baseline.net_revenue) / baseline.net_revenue)
            if baseline.net_revenue
            else 0.0,
            4,
        ),
        "violations_total": proposed.violations + baseline.violations,
    }
