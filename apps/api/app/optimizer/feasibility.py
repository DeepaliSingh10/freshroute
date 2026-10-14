"""Feasibility precomputation shared by the baseline and the LP optimizer.

A batch may only ship to a destination if its remaining shelf life covers:
    travel time + handling/inspection buffer + the buyer's minimum fresh days.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from ..data.constants import GRADE_PRICE_FACTOR
from ..data.cost_model import CostModel
from ..data.models import Instance


@dataclass(frozen=True)
class FeasiblePair:
    batch_id: str
    destination_id: str
    commodity_id: str
    origin_id: str
    lane_capacity_kg: float
    travel_time_hours: float
    travel_days: float
    transport_cost_per_kg: float
    handling_per_kg: float
    effective_price_per_kg: float
    margin_per_kg: float
    # Days of sellable shelf life left once the batch arrives and is handled.
    residual_shelf_life_days: float


def is_feasible(
    residual_shelf_life_days: float,
    travel_time_hours: float,
    min_days_fresh_on_shelf: float,
    cost_model: CostModel,
) -> bool:
    travel_days = travel_time_hours / 24.0
    required = travel_days + cost_model.shelf_life_buffer_days + min_days_fresh_on_shelf
    return residual_shelf_life_days >= required


def build_feasible_pairs(
    instance: Instance, cost_model: CostModel
) -> Dict[Tuple[str, str], FeasiblePair]:
    """Return feasible (batch_id, destination_id) -> FeasiblePair."""
    demand = instance.demand_lookup()
    pairs: Dict[Tuple[str, str], FeasiblePair] = {}

    for b in instance.batches.values():
        commodity = instance.commodities[b.commodity_id]
        for d in instance.destinations.values():
            dem = demand.get((d.destination_id, b.commodity_id))
            if dem is None or dem.demand_kg <= 0:
                continue
            lane = instance.lanes.get((b.origin_id, d.destination_id))
            if lane is None:
                continue
            if not is_feasible(
                b.remaining_shelf_life_days,
                lane.travel_time_hours,
                d.min_days_fresh_on_shelf,
                cost_model,
            ):
                continue
            travel_days = lane.travel_time_hours / 24.0
            eff_price = dem.price_per_kg * GRADE_PRICE_FACTOR.get(b.quality_grade, 1.0)
            transport = lane.cost_per_kg
            handling = commodity.handling_per_kg
            pairs[(b.batch_id, d.destination_id)] = FeasiblePair(
                batch_id=b.batch_id,
                destination_id=d.destination_id,
                commodity_id=b.commodity_id,
                origin_id=b.origin_id,
                lane_capacity_kg=lane.capacity_kg,
                travel_time_hours=lane.travel_time_hours,
                travel_days=travel_days,
                transport_cost_per_kg=transport,
                handling_per_kg=handling,
                effective_price_per_kg=eff_price,
                margin_per_kg=eff_price - transport - handling,
                residual_shelf_life_days=b.remaining_shelf_life_days
                - travel_days
                - cost_model.shelf_life_buffer_days,
            )
    return pairs
