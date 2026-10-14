"""E5 — simulated cold-chain telemetry and live market-price feed.

Two capability stubs that make FreshRoute responsive to a changing world:

1. Temperature telemetry (IoT sensor simulation). Per-batch temperature readings are
   generated; degree-hours above the safe threshold accelerate spoilage, reducing each
   batch's remaining shelf life. Feeding the degraded instance back through the planner
   shows why ignoring cold-chain data produces infeasible shipments.

2. Market-price feed. A simulated lognormal price walk updates destination prices over
   several ticks; re-solving on the updated feed moves the plan toward higher-value markets.

All parameters live in `cost_model.yaml` (`cold_chain`, `price_feed`) and are disclosed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List

import numpy as np

from .cost_model import CostModel
from .models import Instance


@dataclass(frozen=True)
class TemperatureReading:
    batch_id: str
    hour: float
    temp_c: float


@dataclass
class Telemetry:
    readings: List[TemperatureReading]
    degree_hours_above: Dict[str, float]
    life_lost_days: Dict[str, float]
    threshold_c: float

    def batches_with_excursion(self) -> List[str]:
        return [bid for bid, dh in self.degree_hours_above.items() if dh > 1e-9]


def simulate_temperatures(
    instance: Instance, cost_model: CostModel, seed: int = 0
) -> Telemetry:
    cfg = cost_model.cold_chain
    ideal = float(cfg.get("ideal_temp_c", 4.0))
    thr = float(cfg.get("threshold_temp_c", 8.0))
    p_exc = float(cfg.get("excursion_prob", 0.25))
    rise = float(cfg.get("excursion_rise_c", 7.0))
    per_day = float(cfg.get("degree_hours_per_day_lost", 24.0))
    interval = float(cfg.get("sample_interval_hours", 4.0))
    horizon = float(cfg.get("horizon_hours", 24.0))

    rng = np.random.default_rng(seed)
    times = np.arange(0.0, horizon + 1e-9, interval)
    readings: List[TemperatureReading] = []
    degree_hours: Dict[str, float] = {}

    for b in instance.batches.values():
        base = ideal + rng.normal(0.0, 0.6)
        has_excursion = rng.random() < p_exc
        start_idx = 0
        if has_excursion and len(times) > 2:
            start_idx = 1 + int(rng.integers(0, len(times) - 2))
        temps = []
        for i, t in enumerate(times):
            temp = base + rng.normal(0.0, 0.5)
            if has_excursion and i >= start_idx:
                temp += rise * (0.6 + 0.4 * rng.random())
            temps.append(temp)
            readings.append(TemperatureReading(b.batch_id, float(t), round(float(temp), 2)))

        over = np.maximum(0.0, np.array(temps) - thr)
        dh = 0.0
        for i in range(len(times) - 1):
            dh += 0.5 * (over[i] + over[i + 1]) * (times[i + 1] - times[i])
        degree_hours[b.batch_id] = float(dh)

    life_lost = {bid: dh / per_day if per_day > 0 else 0.0 for bid, dh in degree_hours.items()}
    return Telemetry(readings, degree_hours, life_lost, thr)


def apply_temperature_effect(
    instance: Instance, telemetry: Telemetry, cost_model: CostModel
) -> Instance:
    """Return a copy of the instance with shelf life reduced by cold-chain exposure."""
    new_batches = {}
    for bid, b in instance.batches.items():
        lost = telemetry.life_lost_days.get(bid, 0.0)
        new_rsl = max(0.05, b.remaining_shelf_life_days - lost)
        new_batches[bid] = replace(b, remaining_shelf_life_days=round(new_rsl, 3))
    return replace(instance, batches=new_batches)


@dataclass(frozen=True)
class PriceTick:
    tick: int
    commodity_id: str
    price_factor: float


def simulate_price_feed(
    instance: Instance, cost_model: CostModel, seed: int = 0
) -> List[PriceTick]:
    cfg = cost_model.price_feed
    n_ticks = int(cfg.get("n_ticks", 3))
    vol = float(cfg.get("volatility", 0.06))

    rng = np.random.default_rng(seed)
    cids = sorted(instance.commodities.keys())
    factors = {c: 1.0 for c in cids}
    ticks: List[PriceTick] = []
    for k in range(1, n_ticks + 1):
        for c in cids:
            factors[c] *= float(np.exp(rng.normal(0.0, vol)))
            ticks.append(PriceTick(k, c, round(factors[c], 4)))
    return ticks


def price_factors_at(ticks: List[PriceTick], tick: int) -> Dict[str, float]:
    factors: Dict[str, float] = {}
    for t in ticks:
        if t.tick <= tick:
            factors[t.commodity_id] = t.price_factor
    return factors


def apply_price_feed(
    instance: Instance, factors: Dict[str, float], cost_model: CostModel
) -> Instance:
    """Return a copy with market demand prices scaled by the latest feed factors."""
    new_demands = []
    for dem in instance.demands:
        if instance.destinations[dem.destination_id].is_clearance:
            new_demands.append(dem)
            continue
        f = factors.get(dem.commodity_id, 1.0)
        new_demands.append(replace(dem, price_per_kg=round(dem.price_per_kg * f, 2)))
    return replace(instance, demands=new_demands)
