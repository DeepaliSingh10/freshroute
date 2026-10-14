"""Documented baseline strategies (greedy, no joint optimization).

Strategies:
  - "fefo"  : FEFO (first-expired-first-out) + best-margin feasible market. Urgency-aware
              and shelf-life-feasible. The STRONG baseline we must still beat.
  - "margin": urgency-blind; ships the most profitable stock first (still feasibility-checked).
  - "naive" : price-first and SHELF-LIFE-BLIND. Ships to the highest-price market without
              checking whether it can arrive before the produce expires. Doomed cargo is
              surfaced by the metrics layer as "expired on arrival" (lost revenue + wasted
              transport). This is the common real-world failure FreshRoute fixes (MVP item M3).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..data.constants import GRADE_PRICE_FACTOR
from ..data.cost_model import CostModel
from ..data.models import Instance
from .feasibility import build_feasible_pairs
from .types import Dispatch, Plan

EPS = 1e-6


def solve_baseline(instance: Instance, cost_model: CostModel, strategy: str = "fefo") -> Plan:
    if strategy == "naive":
        return _solve_shelf_life_blind(instance, cost_model)
    return _solve_feasible_greedy(instance, cost_model, strategy)


def _solve_feasible_greedy(instance: Instance, cost_model: CostModel, strategy: str) -> Plan:
    pairs = build_feasible_pairs(instance, cost_model, include_clearance=False)

    remaining_demand: Dict[Tuple[str, str], float] = {
        (d.destination_id, d.commodity_id): d.demand_kg for d in instance.demands
    }
    remaining_lane: Dict[Tuple[str, str], float] = {
        (l.origin_id, l.destination_id): l.capacity_kg for l in instance.lanes.values()
    }

    dispatches: List[Dispatch] = []
    leftover: Dict[str, float] = {}

    if strategy == "margin":
        def best_margin(b) -> float:
            return max(
                (p.margin_per_kg for (bid, _), p in pairs.items() if bid == b.batch_id),
                default=float("-inf"),
            )

        ordered = sorted(instance.batches.values(), key=lambda b: -best_margin(b))
    else:  # fefo
        ordered = sorted(instance.batches.values(), key=lambda b: b.remaining_shelf_life_days)

    for b in ordered:
        candidates = [
            p
            for (bid, did), p in pairs.items()
            if bid == b.batch_id
            and remaining_demand.get((did, b.commodity_id), 0.0) > EPS
            and remaining_lane.get((p.origin_id, did), 0.0) > EPS
        ]
        candidates.sort(key=lambda p: (-p.margin_per_kg, p.travel_time_hours))

        remaining = b.quantity_kg
        for p in candidates:
            if remaining <= EPS:
                break
            dem_left = remaining_demand[(p.destination_id, b.commodity_id)]
            cap_left = remaining_lane[(p.origin_id, p.destination_id)]
            take = min(remaining, dem_left, cap_left)
            if take <= EPS:
                continue
            dispatches.append(Dispatch(b.batch_id, p.destination_id, round(take, 4)))
            remaining_demand[(p.destination_id, b.commodity_id)] = dem_left - take
            remaining_lane[(p.origin_id, p.destination_id)] = cap_left - take
            remaining -= take

        leftover[b.batch_id] = round(max(0.0, remaining), 4)

    return Plan(method=f"baseline_{strategy}", dispatches=dispatches, leftover=leftover)


def _solve_shelf_life_blind(instance: Instance, cost_model: CostModel) -> Plan:
    """Price-first greedy that ignores shelf-life feasibility. Doomed shipments expected."""
    demand = instance.demand_lookup()

    remaining_demand: Dict[Tuple[str, str], float] = {
        (d.destination_id, d.commodity_id): d.demand_kg for d in instance.demands
    }
    remaining_lane: Dict[Tuple[str, str], float] = {
        (l.origin_id, l.destination_id): l.capacity_kg for l in instance.lanes.values()
    }

    dispatches: List[Dispatch] = []
    leftover: Dict[str, float] = {}

    # Highest unit price achievable first, then shortest travel.
    def price_of(b, dest_id) -> float:
        dem = demand.get((dest_id, b.commodity_id))
        if dem is None:
            return float("-inf")
        return dem.price_per_kg * GRADE_PRICE_FACTOR.get(b.quality_grade, 1.0)

    for b in instance.batches.values():
        candidates = []
        for d in instance.destinations.values():
            if d.is_clearance:
                continue
            lane = instance.lanes.get((b.origin_id, d.destination_id))
            if lane is None:
                continue
            if remaining_demand.get((d.destination_id, b.commodity_id), 0.0) <= EPS:
                continue
            if remaining_lane.get((b.origin_id, d.destination_id), 0.0) <= EPS:
                continue
            candidates.append((price_of(b, d.destination_id), lane.travel_time_hours, d))

        candidates.sort(key=lambda t: (-t[0], t[1]))

        remaining = b.quantity_kg
        for _price, _travel, d in candidates:
            if remaining <= EPS:
                break
            dem_left = remaining_demand[(d.destination_id, b.commodity_id)]
            cap_left = remaining_lane[(b.origin_id, d.destination_id)]
            take = min(remaining, dem_left, cap_left)
            if take <= EPS:
                continue
            dispatches.append(Dispatch(b.batch_id, d.destination_id, round(take, 4)))
            remaining_demand[(d.destination_id, b.commodity_id)] = dem_left - take
            remaining_lane[(b.origin_id, d.destination_id)] = cap_left - take
            remaining -= take

        leftover[b.batch_id] = round(max(0.0, remaining), 4)

    return Plan(method="baseline_naive", dispatches=dispatches, leftover=leftover)
