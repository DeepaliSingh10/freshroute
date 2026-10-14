"""Independent post-hoc feasibility checker (defense in depth).

Re-derives every hard constraint directly from a plan and the instance, WITHOUT
trusting the solver. Any non-empty result means a hard-constraint violation.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..data.cost_model import CostModel
from ..data.models import Instance
from ..optimizer.feasibility import is_feasible
from ..optimizer.types import Plan

TOL = 1e-3


def check_plan(instance: Instance, cost_model: CostModel, plan: Plan) -> List[str]:
    violations: List[str] = []
    demand = instance.demand_lookup()

    shipped_by_batch: Dict[str, float] = {}
    served_by_demand: Dict[Tuple[str, str], float] = {}
    lane_load: Dict[Tuple[str, str], float] = {}

    for disp in plan.dispatches:
        b = instance.batches.get(disp.batch_id)
        if b is None:
            violations.append(f"unknown batch {disp.batch_id}")
            continue
        d = instance.destinations.get(disp.destination_id)
        if d is None:
            violations.append(f"unknown destination {disp.destination_id}")
            continue
        lane = instance.lanes.get((b.origin_id, disp.destination_id))
        if lane is None:
            violations.append(f"no lane {b.origin_id}->{disp.destination_id}")
            continue

        if disp.quantity_kg <= 0:
            violations.append(f"non-positive dispatch {disp.batch_id}->{disp.destination_id}")
            continue

        # Shelf-life feasibility
        if not is_feasible(
            b.remaining_shelf_life_days,
            lane.travel_time_hours,
            d.min_days_fresh_on_shelf,
            cost_model,
        ):
            violations.append(
                f"infeasible pair {disp.batch_id}->{disp.destination_id} (shelf life)"
            )

        shipped_by_batch[disp.batch_id] = shipped_by_batch.get(disp.batch_id, 0.0) + disp.quantity_kg
        served_by_demand[(disp.destination_id, b.commodity_id)] = (
            served_by_demand.get((disp.destination_id, b.commodity_id), 0.0) + disp.quantity_kg
        )
        lane_load[(b.origin_id, disp.destination_id)] = (
            lane_load.get((b.origin_id, disp.destination_id), 0.0) + disp.quantity_kg
        )

    # (1) stock availability
    for b in instance.batches.values():
        if shipped_by_batch.get(b.batch_id, 0.0) > b.quantity_kg + TOL:
            violations.append(
                f"over-ship batch {b.batch_id}: {shipped_by_batch[b.batch_id]:.2f} > {b.quantity_kg:.2f}"
            )

    # (2) demand upper bound
    for (did, cid), served in served_by_demand.items():
        dem = demand.get((did, cid))
        if dem is not None and served > dem.demand_kg + TOL:
            violations.append(f"over-serve {did}/{cid}: {served:.2f} > {dem.demand_kg:.2f}")

    # (3) lane capacity
    for (oid, did), load in lane_load.items():
        cap = instance.lane(oid, did).capacity_kg
        if load > cap + TOL:
            violations.append(f"lane {oid}->{did} over capacity: {load:.2f} > {cap:.2f}")

    return violations
