"""Disruption replanning (Extension E3).

A morning plan is built from the *expected* instance. Mid-day a disruption hits:
origin hubs go offline (outbound lanes closed) and/or all travel is delayed. We compare:

  - **no_replan / frozen** : shipments already on open lanes proceed; anything planned on
    a now-closed lane is stranded, and nothing further is optimized.
  - **replan**             : keep the shipments already dispatched on open lanes, then
    re-optimize the *remaining* stock on the disrupted network (this is where the local
    clearance channel earns its keep — it rescues stock that can no longer reach a market).

Both outcomes are scored on the *same* disrupted instance with the shared cost model.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Tuple

from ..data.cost_model import CostModel
from ..data.models import Instance
from .allocator import solve_optimizer
from .feasibility import is_feasible
from .types import Dispatch, Plan


@dataclass(frozen=True)
class Disruption:
    blocked_origins: Tuple[str, ...] = ()
    travel_delay_hours: float = 0.0
    description: str = ""


def apply_disruption(instance: Instance, disruption: Disruption) -> Instance:
    """Close outbound non-clearance lanes from blocked origins; delay all remaining lanes."""
    lanes = {}
    for (o, d), lane in instance.lanes.items():
        dest = instance.destinations[d]
        if o in disruption.blocked_origins and not dest.is_clearance:
            continue
        lanes[(o, d)] = replace(
            lane,
            travel_time_hours=round(lane.travel_time_hours + disruption.travel_delay_hours, 2),
        )
    return replace(instance, lanes=lanes)


def _shipped_by_batch(dispatches) -> Dict[str, float]:
    acc: Dict[str, float] = {}
    for d in dispatches:
        acc[d.batch_id] = acc.get(d.batch_id, 0.0) + d.quantity_kg
    return acc


def keep_dispatched(
    instance_after: Instance, plan_before: Plan, cost_model: CostModel
) -> Plan:
    """Committed response: keep only shipments that are STILL valid after the disruption.

    A shipment is committed if its lane is open AND the (possibly delayed) network still
    lets it reach the buyer before expiry. Anything else is treated as not-yet-departed
    stock, to be re-planned on the disrupted network.
    """
    kept = []
    for disp in plan_before.dispatches:
        b = instance_after.batches[disp.batch_id]
        lane = instance_after.lanes.get((b.origin_id, disp.destination_id))
        if lane is None:
            continue
        dest = instance_after.destinations[disp.destination_id]
        if is_feasible(
            b.remaining_shelf_life_days, lane.travel_time_hours, dest.min_days_fresh_on_shelf, cost_model
        ):
            kept.append(disp)
    return Plan(method="no_replan", dispatches=kept, leftover={}, status="FROZEN")


def _residual_instance(
    instance_after: Instance,
    shipped: Dict[str, float],
    served: Dict[Tuple[str, str], float],
    lane_load: Dict[Tuple[str, str], float],
) -> Instance:
    """Instance with stock, demand and lane capacity reduced by already-committed shipments."""
    batches = {
        bid: replace(b, quantity_kg=round(max(0.0, b.quantity_kg - shipped.get(bid, 0.0)), 4))
        for bid, b in instance_after.batches.items()
    }
    demands = [
        replace(d, demand_kg=round(max(0.0, d.demand_kg - served.get((d.destination_id, d.commodity_id), 0.0)), 1))
        for d in instance_after.demands
    ]
    lanes = {
        k: replace(l, capacity_kg=round(max(0.0, l.capacity_kg - lane_load.get(k, 0.0)), 1))
        for k, l in instance_after.lanes.items()
    }
    return replace(instance_after, batches=batches, demands=demands, lanes=lanes)


def replan(instance_after: Instance, plan_before: Plan, cost_model: CostModel) -> Tuple[Plan, Plan]:
    """Return (frozen_plan, combined_replan_plan) both valid on `instance_after`."""
    frozen = keep_dispatched(instance_after, plan_before, cost_model)

    served: Dict[Tuple[str, str], float] = {}
    lane_load: Dict[Tuple[str, str], float] = {}
    for disp in frozen.dispatches:
        b = instance_after.batches[disp.batch_id]
        served[(disp.destination_id, b.commodity_id)] = (
            served.get((disp.destination_id, b.commodity_id), 0.0) + disp.quantity_kg
        )
        lane_load[(b.origin_id, disp.destination_id)] = (
            lane_load.get((b.origin_id, disp.destination_id), 0.0) + disp.quantity_kg
        )

    residual = _residual_instance(
        instance_after, _shipped_by_batch(frozen.dispatches), served, lane_load
    )
    residual_plan = solve_optimizer(residual, cost_model)

    combined_dispatches = list(frozen.dispatches) + list(residual_plan.dispatches)
    combined = Plan(
        method="replan",
        dispatches=combined_dispatches,
        leftover=residual_plan.leftover,
        status=residual_plan.status,
        solver=residual_plan.solver,
        runtime_ms=residual_plan.runtime_ms,
    )
    return frozen, combined
