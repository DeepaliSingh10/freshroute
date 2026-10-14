"""Domain model for FreshRoute (frozen data schema — see docs/DATA_SPEC.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Commodity:
    commodity_id: str
    name: str
    perishability_class: str  # leafy | berry | soft_fruit | root | tuber
    default_shelf_life_days: float
    cost_basis_per_kg: float
    handling_per_kg: float
    base_price_per_kg: float
    popularity: float


@dataclass(frozen=True)
class Origin:
    origin_id: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Destination:
    destination_id: str
    name: str
    region: str
    lat: float
    lon: float
    min_days_fresh_on_shelf: float
    delivery_window_start: str
    delivery_window_end: str
    size_factor: float
    price_factor: float


@dataclass(frozen=True)
class Batch:
    batch_id: str
    commodity_id: str
    quantity_kg: float
    harvest_ts: str
    remaining_shelf_life_days: float
    origin_id: str
    quality_grade: str  # A | B | C


@dataclass(frozen=True)
class Demand:
    destination_id: str
    commodity_id: str
    date: str
    demand_kg: float
    price_per_kg: float
    event_flag: str


@dataclass(frozen=True)
class Lane:
    lane_id: str
    origin_id: str
    destination_id: str
    travel_time_hours: float
    cost_per_kg: float
    capacity_kg: float
    departure_window_start: str
    departure_window_end: str


@dataclass
class Instance:
    """A single decision-support instance (one scenario snapshot)."""

    scenario_id: str
    split: str
    now_ts: str
    seed: int
    commodities: Dict[str, Commodity] = field(default_factory=dict)
    origins: Dict[str, Origin] = field(default_factory=dict)
    destinations: Dict[str, Destination] = field(default_factory=dict)
    batches: Dict[str, Batch] = field(default_factory=dict)
    demands: List[Demand] = field(default_factory=list)
    lanes: Dict[Tuple[str, str], Lane] = field(default_factory=dict)

    def demand_lookup(self) -> Dict[Tuple[str, str], Demand]:
        return {(d.destination_id, d.commodity_id): d for d in self.demands}

    def lane(self, origin_id: str, destination_id: str) -> Lane:
        return self.lanes[(origin_id, destination_id)]
