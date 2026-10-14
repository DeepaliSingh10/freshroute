"""Sensitivity engine (Owner A) — one-factor sweeps that feed the UI sliders.

Given a base instance and a single factor, perturb it across a list of values, re-solve the
optimizer and the strong baseline, and return a *curve* of metrics so the dashboard can show
"drag travel time / demand, watch the plan adapt". Deterministic (seeded).
"""

from __future__ import annotations

from typing import Dict, List

from ..data.cost_model import CostModel
from ..data.generator import apply_perturbations
from ..data.models import Instance
from ..optimizer.allocator import solve_optimizer
from ..optimizer.baseline import solve_baseline
from .metrics import compute_metrics

# Supported knobs (must match keys understood by generator.apply_perturbations).
FACTORS: Dict[str, dict] = {
    "demand_multiplier": {"default_range": [0.8, 0.9, 1.0, 1.1, 1.2], "label": "Demand multiplier"},
    "travel_delay_hours": {"default_range": [0.0, 2.0, 4.0, 6.0, 8.0], "label": "Travel delay (h)"},
    "price_shock_pct": {"default_range": [-0.10, -0.05, 0.0, 0.05, 0.10], "label": "Price shock"},
    "lane_capacity_multiplier": {"default_range": [0.3, 0.5, 0.7, 1.0, 1.5], "label": "Lane capacity x"},
    "rsl_noise_pct": {"default_range": [0.0, 0.05, 0.10, 0.15, 0.20], "label": "Shelf-life noise"},
}


def sweep(
    instance: Instance,
    cost_model: CostModel,
    factor: str,
    values: List[float],
    baseline: str = "fefo",
    seed: int = 0,
) -> List[dict]:
    if factor not in FACTORS:
        raise ValueError(f"unknown factor {factor!r}; expected one of {sorted(FACTORS)}")

    points: List[dict] = []
    for i, v in enumerate(values):
        inst = apply_perturbations(instance, {factor: v}, seed=seed + i)
        m_opt = compute_metrics(inst, cost_model, solve_optimizer(inst, cost_model))
        m_base = compute_metrics(inst, cost_model, solve_baseline(inst, cost_model, baseline))
        pct = (
            (m_base.spoilage_kg - m_opt.spoilage_kg) / m_base.spoilage_kg * 100.0
            if m_base.spoilage_kg > 1e-9
            else 0.0
        )
        points.append(
            {
                "factor": factor,
                "value": v,
                "optimizer": {
                    "spoilage_kg": round(m_opt.spoilage_kg, 1),
                    "fulfilled_kg": round(m_opt.fulfilled_kg, 1),
                    "net_revenue": round(m_opt.net_revenue, 1),
                },
                "baseline": {
                    "spoilage_kg": round(m_base.spoilage_kg, 1),
                    "fulfilled_kg": round(m_base.fulfilled_kg, 1),
                    "net_revenue": round(m_base.net_revenue, 1),
                },
                "spoilage_reduction_pct": round(pct, 2),
                "net_revenue_delta": round(m_opt.net_revenue - m_base.net_revenue, 1),
            }
        )
    return points
