"""Demand forecasting (Extension E1).

A transparent, explainable forecaster — no black boxes. Each prediction decomposes into:

    forecast(d, c, day) = level(d, c) · dow[d, c, weekday] · event_uplift[d, c]

- `level`       : robust per-(destination, commodity) baseline level.
- `dow`         : per-weekday multiplicative index (fresh-produce weekly rhythm).
- `event_uplift`: multiplier learned from festival/event days (applied when a known
                  upcoming event is flagged). Defaults to 1.0 with no event data.

Trained on a synthetic daily demand *history* and backtested against naive baselines.
The generator emits a single-day snapshot; `generate_demand_history` produces the
multi-day series a forecaster needs so E1 has real signal to learn.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from ..data.constants import AVG_SPEED_KMH  # noqa: F401  (kept for parity with generator)
from ..data.models import Commodity, Destination, Instance, Demand

Key = Tuple[str, str]  # (destination_id, commodity_id)
DOW = 7

# Weekly shape for fresh produce (Mon..Sun), mean ~= 1.0 (weekend peak).
DEFAULT_DOW_FACTORS = (0.95, 0.93, 0.97, 1.02, 1.10, 1.15, 0.88)


def generate_demand_history(
    seed: int,
    commodities: Dict[str, Commodity],
    destinations: Dict[str, Destination],
    base_date: date,
    days: int = 90,
    event_rate: float = 0.08,
    noise: float = 0.18,
    scale: float = 900.0,
) -> List[dict]:
    """Deterministic daily demand history (excludes clearance outlets).

    Returns rows: {date, destination_id, commodity_id, demand_kg, event_flag}.
    """
    rng = np.random.default_rng(seed)
    rows: List[dict] = []
    for d in destinations.values():
        if d.is_clearance:
            continue
        for c in commodities.values():
            level = scale * c.popularity * d.size_factor
            tilt = rng.uniform(0.9, 1.1, size=DOW)
            tilt = tilt / tilt.mean()
            for i in range(days):
                day = base_date + timedelta(days=i)
                dow = day.weekday()
                f = DEFAULT_DOW_FACTORS[dow] * float(tilt[dow])
                event_flag = ""
                if rng.random() < event_rate:
                    event_flag = "festival"
                    f *= float(rng.uniform(1.3, 1.7))
                qty = max(0.0, level * f * float(rng.normal(1.0, noise)))
                rows.append(
                    {
                        "date": day.isoformat(),
                        "destination_id": d.destination_id,
                        "commodity_id": c.commodity_id,
                        "demand_kg": round(qty, 1),
                        "event_flag": event_flag,
                    }
                )
    return rows


@dataclass
class ForecastModel:
    levels: Dict[Key, float]
    dow_index: Dict[Key, List[float]]
    event_uplift: Dict[Key, float]

    def predict(self, destination_id: str, commodity_id: str, day: date, is_event: bool = False) -> float:
        k = (destination_id, commodity_id)
        level = self.levels.get(k, 0.0)
        idx = self.dow_index.get(k)
        dow = idx[day.weekday()] if idx else 1.0
        ev = self.event_uplift.get(k, 1.0) if is_event else 1.0
        return max(0.0, level * dow * ev)


def fit(history: Iterable[dict], event_uplift_cap: float = 2.0) -> ForecastModel:
    """Fit level + day-of-week index + event uplift from history rows."""
    by_key: Dict[Key, List[dict]] = {}
    for r in history:
        by_key.setdefault((r["destination_id"], r["commodity_id"]), []).append(r)

    levels: Dict[Key, float] = {}
    dow_index: Dict[Key, List[float]] = {}
    event_uplift: Dict[Key, float] = {}

    for k, rows in by_key.items():
        vals = np.array([r["demand_kg"] for r in rows], dtype=float)
        level = float(np.mean(vals)) if len(vals) else 0.0
        levels[k] = level

        idx = [1.0] * DOW
        if level > 0:
            numer = np.zeros(DOW)
            denom = np.zeros(DOW)
            for r in rows:
                dow = date.fromisoformat(r["date"]).weekday()
                numer[dow] += r["demand_kg"]
                denom[dow] += 1.0
            raw = np.where(denom > 0, numer / np.maximum(denom, 1e-9), level)
            raw = raw / np.mean(raw)
            idx = [float(x) for x in raw]
        dow_index[k] = idx

        # event uplift = mean(value / (level·dow)) on event days
        if level > 0:
            ratios = []
            for r in rows:
                if r["event_flag"]:
                    dow = date.fromisoformat(r["date"]).weekday()
                    ratios.append(r["demand_kg"] / max(1e-9, level * idx[dow]))
            event_uplift[k] = (
                float(min(event_uplift_cap, np.mean(ratios))) if ratios else 1.0
            )
        else:
            event_uplift[k] = 1.0

    return ForecastModel(levels=levels, dow_index=dow_index, event_uplift=event_uplift)


def backtest(
    history: Iterable[dict], holdout_days: int = 14
) -> dict:
    """Time-series holdout: train on all but the last `holdout_days`, evaluate on those.

    Compares our model to naive baselines: yesterday's value, and the seasonal-naive
    (same weekday last week). Reports MAE / MAPE / bias per method.
    """
    rows = list(history)
    if not rows:
        return {}
    d0 = min(date.fromisoformat(r["date"]) for r in rows)
    dmax = max(date.fromisoformat(r["date"]) for r in rows)
    cutoff = dmax - timedelta(days=holdout_days - 1)

    train = [r for r in rows if date.fromisoformat(r["date"]) < cutoff]
    test = [r for r in rows if date.fromisoformat(r["date"]) >= cutoff]

    model = fit(train)

    # index history by (dest,commodity,date) for naive baselines
    lut: Dict[Tuple[str, str, str], dict] = {
        (r["destination_id"], r["commodity_id"], r["date"]): r for r in rows
    }

    preds: Dict[str, List[float]] = {"model": [], "naive_last": [], "seasonal_naive": []}
    actuals: List[float] = []

    for r in test:
        d = date.fromisoformat(r["date"])
        k = (r["destination_id"], r["commodity_id"])
        actual = r["demand_kg"]
        actuals.append(actual)

        preds["model"].append(
            model.predict(r["destination_id"], r["commodity_id"], d, is_event=bool(r["event_flag"]))
        )

        y = lut.get((r["destination_id"], r["commodity_id"], (d - timedelta(days=1)).isoformat()))
        preds["naive_last"].append(y["demand_kg"] if y else model.levels.get(k, 0.0))

        s = lut.get((r["destination_id"], r["commodity_id"], (d - timedelta(days=7)).isoformat()))
        preds["seasonal_naive"].append(s["demand_kg"] if s else model.levels.get(k, 0.0))

    a = np.array(actuals, dtype=float)
    out: dict = {
        "train_days": (cutoff - d0).days,
        "holdout_days": holdout_days,
        "n_series": len({(r["destination_id"], r["commodity_id"]) for r in rows}),
        "n_test_points": len(test),
        "methods": {},
    }
    for name, p in preds.items():
        pv = np.array(p, dtype=float)
        mae = float(np.mean(np.abs(pv - a)))
        mask = a > 1e-6
        mape = float(np.mean(np.abs(pv[mask] - a[mask]) / a[mask])) if mask.any() else 0.0
        bias = float(np.mean(pv - a) / (np.mean(a) if np.mean(a) else 1.0))
        out["methods"][name] = {
            "mae": round(mae, 2),
            "mape": round(mape, 4),
            "bias": round(bias, 4),
        }
    return out


def forecast_next_day(
    model: ForecastModel,
    instance: Instance,
    target_date: date,
    events: Optional[Dict[Key, bool]] = None,
) -> List[Demand]:
    """Turn a next-day forecast into `Demand` rows (market destinations only).

    Prices are carried over from the instance's current demand (price is set by the
    market, not forecast by this model).
    """
    events = events or {}
    out: List[Demand] = []
    seen: set = set()
    for d in instance.demands:
        dest = instance.destinations[d.destination_id]
        if dest.is_clearance:
            out.append(d)
            continue
        k = (d.destination_id, d.commodity_id)
        seen.add(k)
        out.append(
            Demand(
                destination_id=d.destination_id,
                commodity_id=d.commodity_id,
                date=target_date.isoformat(),
                demand_kg=round(model.predict(d.destination_id, d.commodity_id, target_date, events.get(k, False)), 1),
                price_per_kg=d.price_per_kg,
                event_flag="festival" if events.get(k, False) else "",
            )
        )
    return out
