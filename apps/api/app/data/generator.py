"""Synthetic dataset generator for FreshRoute (deterministic given a seed).

Produces an `Instance` and can materialize it to CSV. See docs/DATA_SPEC.md.
"""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .constants import (
    AVG_SPEED_KMH,
    COMMODITY_CATALOG,
    DELIVERY_WINDOWS,
    DESTINATION_CATALOG,
    GRADE_PRICE_FACTOR,
    ORIGIN_CATALOG,
    TRAVEL_OVERHEAD_HOURS,
)
from .cost_model import CostModel
from .models import Batch, Commodity, Demand, Destination, Instance, Lane, Origin

DEFAULT_NOW = datetime(2026, 3, 15, 7, 0, tzinfo=timezone.utc)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _build_commodities() -> Dict[str, Commodity]:
    out: Dict[str, Commodity] = {}
    for c in COMMODITY_CATALOG:
        price = float(c["price"])
        out[c["id"]] = Commodity(
            commodity_id=c["id"],
            name=c["name"],
            perishability_class=c["cls"],
            default_shelf_life_days=float(c["shelf"]),
            cost_basis_per_kg=round(price * 0.6, 2),
            handling_per_kg=1.2,
            base_price_per_kg=price,
            popularity=float(c["pop"]),
        )
    return out


def _build_origins(rng: np.random.Generator, n: int) -> Dict[str, Origin]:
    chosen = rng.choice(len(ORIGIN_CATALOG), size=n, replace=False)
    out: Dict[str, Origin] = {}
    for i in chosen:
        oid, name, lat, lon = ORIGIN_CATALOG[int(i)]
        out[oid] = Origin(origin_id=oid, name=name, lat=lat, lon=lon)
    return out


def _build_destinations(rng: np.random.Generator, n: int) -> Dict[str, Destination]:
    chosen = rng.choice(len(DESTINATION_CATALOG), size=n, replace=False)
    out: Dict[str, Destination] = {}
    for idx, i in enumerate(chosen):
        did, name, region, lat, lon = DESTINATION_CATALOG[int(i)]
        w0, w1 = DELIVERY_WINDOWS[idx % len(DELIVERY_WINDOWS)]
        out[did] = Destination(
            destination_id=did,
            name=name,
            region=region,
            lat=lat,
            lon=lon,
            min_days_fresh_on_shelf=float(rng.choice([0.5, 1.0, 1.5])),
            delivery_window_start=w0,
            delivery_window_end=w1,
            size_factor=float(rng.uniform(0.5, 2.0)),
            price_factor=float(rng.uniform(0.85, 1.25)),
        )
    return out


def _build_lanes(
    rng: np.random.Generator,
    origins: Dict[str, Origin],
    destinations: Dict[str, Destination],
    cost_model: CostModel,
) -> Dict[Tuple[str, str], Lane]:
    lanes: Dict[Tuple[str, str], Lane] = {}
    for o in origins.values():
        for d in destinations.values():
            dist = haversine_km(o.lat, o.lon, d.lat, d.lon)
            travel_h = dist / AVG_SPEED_KMH + TRAVEL_OVERHEAD_HOURS
            cost = dist * cost_model.transport_cost_per_kg_km
            lanes[(o.origin_id, d.destination_id)] = Lane(
                lane_id=f"LANE-{o.origin_id}-{d.destination_id}",
                origin_id=o.origin_id,
                destination_id=d.destination_id,
                travel_time_hours=round(travel_h, 2),
                cost_per_kg=round(cost, 3),
                capacity_kg=round(float(rng.uniform(800, 4000)), 1),
                departure_window_start="04:00",
                departure_window_end="09:00",
            )
    return lanes


def _build_batches(
    rng: np.random.Generator,
    commodities: Dict[str, Commodity],
    origins: Dict[str, Origin],
    now: datetime,
) -> Dict[str, Batch]:
    batches: Dict[str, Batch] = {}
    origin_ids = list(origins.keys())
    bid = 0
    for c in commodities.values():
        n_batches = int(rng.integers(3, 8))
        for _ in range(n_batches):
            qty = float(np.clip(rng.lognormal(mean=6.0, sigma=0.7), 50, 5000))
            rsl = float(c.default_shelf_life_days * rng.uniform(0.12, 1.0))
            grade = str(rng.choice(["A", "B", "C"], p=[0.5, 0.35, 0.15]))
            batches[f"B{bid:04d}"] = Batch(
                batch_id=f"B{bid:04d}",
                commodity_id=c.commodity_id,
                quantity_kg=round(qty, 1),
                harvest_ts=now.isoformat(),
                remaining_shelf_life_days=round(rsl, 2),
                origin_id=str(rng.choice(origin_ids)),
                quality_grade=grade,
            )
            bid += 1
    return batches


def _build_demands(
    rng: np.random.Generator,
    commodities: Dict[str, Commodity],
    destinations: Dict[str, Destination],
    batches: Dict[str, Batch],
    now: datetime,
    target_ratio: float = 0.85,
) -> List[Demand]:
    total_supply = sum(b.quantity_kg for b in batches.values())
    weight = sum(
        c.popularity * d.size_factor for c in commodities.values() for d in destinations.values()
    )
    scale = (total_supply * target_ratio) / max(weight, 1e-9)

    demands: List[Demand] = []
    for d in destinations.values():
        for c in commodities.values():
            base = c.popularity * d.size_factor * scale
            noise = float(rng.normal(1.0, 0.30))
            qty = max(0.0, base * noise)
            event = ""
            if rng.random() < 0.10:
                event = "festival"
                qty *= 1.5
            price = c.base_price_per_kg * d.price_factor * float(rng.uniform(0.95, 1.05))
            demands.append(
                Demand(
                    destination_id=d.destination_id,
                    commodity_id=c.commodity_id,
                    date=now.date().isoformat(),
                    demand_kg=round(qty, 1),
                    price_per_kg=round(price, 2),
                    event_flag=event,
                )
            )
    return demands


def generate_instance(
    seed: int,
    cost_model: CostModel,
    scenario_id: str = "scenario",
    split: str = "train",
    now: datetime = DEFAULT_NOW,
    n_origins: int = 4,
    n_destinations: int = 7,
) -> Instance:
    """Build a single reproducible instance from a seed."""
    rng = np.random.default_rng(seed)
    commodities = _build_commodities()
    origins = _build_origins(rng, n_origins)
    destinations = _build_destinations(rng, n_destinations)
    lanes = _build_lanes(rng, origins, destinations, cost_model)
    batches = _build_batches(rng, commodities, origins, now)
    demands = _build_demands(rng, commodities, destinations, batches, now)
    return Instance(
        scenario_id=scenario_id,
        split=split,
        now_ts=now.isoformat(),
        seed=seed,
        commodities=commodities,
        origins=origins,
        destinations=destinations,
        batches=batches,
        demands=demands,
        lanes=lanes,
    )


def apply_perturbations(
    instance: Instance, perturb: Optional[dict], seed: Optional[int] = None
) -> Instance:
    """Return a new Instance with perturbation profile applied (E4 / robustness)."""
    if not perturb:
        return instance
    rng = np.random.default_rng(instance.seed if seed is None else seed)

    batches = instance.batches
    rsl_noise = float(perturb.get("rsl_noise_pct", 0.0))
    if rsl_noise:
        batches = {
            bid: replace(
                b,
                remaining_shelf_life_days=max(
                    0.05, b.remaining_shelf_life_days * (1.0 + rng.uniform(-rsl_noise, rsl_noise))
                ),
            )
            for bid, b in batches.items()
        }

    demand_mult = float(perturb.get("demand_multiplier", 1.0))
    price_shock = float(perturb.get("price_shock_pct", 0.0))
    demand_mult_by_class = perturb.get("demand_multiplier_by_class", {})
    demands = []
    for d in instance.demands:
        cls = instance.commodities[d.commodity_id].perishability_class
        m = demand_mult * float(demand_mult_by_class.get(cls, 1.0))
        demands.append(
            replace(
                d,
                demand_kg=max(0.0, round(d.demand_kg * m, 1)),
                price_per_kg=round(d.price_per_kg * (1.0 + price_shock), 2),
            )
        )

    missing_pct = float(perturb.get("missing_demand_pct", 0.0))
    if missing_pct:
        keep = rng.random(len(demands)) >= missing_pct
        demands = [d for d, k in zip(demands, keep) if k]

    delay = float(perturb.get("travel_delay_hours", 0.0))
    cap_mult = float(perturb.get("lane_capacity_multiplier", 1.0))
    lanes = instance.lanes
    if delay or cap_mult != 1.0:
        lanes = {
            k: replace(
                l,
                travel_time_hours=round(l.travel_time_hours + delay, 2),
                capacity_kg=round(l.capacity_kg * cap_mult, 1),
            )
            for k, l in instance.lanes.items()
        }

    return replace(
        instance,
        batches=batches,
        demands=demands,
        lanes=lanes,
        split=instance.split,
    )


def write_instance_csv(instance: Instance, out_dir: str | Path) -> Path:
    """Materialize the instance to CSV files under `out_dir`."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    pd.DataFrame([c.__dict__ for c in instance.commodities.values()]).to_csv(
        out / "commodities.csv", index=False
    )
    pd.DataFrame([o.__dict__ for o in instance.origins.values()]).to_csv(
        out / "origins.csv", index=False
    )
    pd.DataFrame([d.__dict__ for d in instance.destinations.values()]).to_csv(
        out / "destinations.csv", index=False
    )
    pd.DataFrame([b.__dict__ for b in instance.batches.values()]).to_csv(
        out / "batches.csv", index=False
    )
    pd.DataFrame([d.__dict__ for d in instance.demands]).to_csv(
        out / "demand.csv", index=False
    )
    pd.DataFrame([l.__dict__ for l in instance.lanes.values()]).to_csv(
        out / "lanes.csv", index=False
    )
    return out
