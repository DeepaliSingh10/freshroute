"""Monte Carlo robustness engine (Extension E4).

For each base scenario, draws N random perturbation vectors (shelf-life noise, demand,
travel delay, price shock, missing demand, capacity), solves the optimizer and the FEFO
baseline, and reports the distribution (mean, std, P10/P50/P90, min/max) of the key
metrics. Reproducible: every draw is seeded.

Shared by `scripts/run_robustness.py` (writes `results/robustness.json`) and the API
(`POST /robustness`) so the dashboard shows the same statistics the results file holds.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from ..data.cost_model import CostModel
from ..data.generator import apply_perturbations, generate_instance
from ..optimizer.allocator import solve_optimizer
from ..optimizer.baseline import solve_baseline
from .checker import check_plan
from .metrics import compare, compute_metrics

SCENARIOS: List[dict] = [
    {"id": "train_01", "seed": 101, "split": "train"},
    {"id": "test_01", "seed": 202, "split": "test"},
    {"id": "hidden_01", "seed": 303, "split": "hidden"},
]

DEFAULT_DRAWS = 20


def sample_perturbation(rng: np.random.Generator) -> dict:
    return {
        "rsl_noise_pct": float(rng.uniform(0.0, 0.15)),
        "demand_multiplier": float(np.clip(rng.normal(1.0, 0.12), 0.70, 1.45)),
        "travel_delay_hours": float(rng.uniform(0.0, 8.0)),
        "price_shock_pct": float(np.clip(rng.normal(0.0, 0.07), -0.20, 0.20)),
        "missing_demand_pct": float(rng.uniform(0.0, 0.05)),
        "lane_capacity_multiplier": float(np.clip(rng.normal(1.0, 0.10), 0.70, 1.30)),
    }


def _stats(vals: list) -> dict:
    a = np.array(vals, dtype=float)
    if a.size == 0:
        return {}
    return {
        "mean": round(float(np.mean(a)), 4),
        "std": round(float(np.std(a)), 4),
        "min": round(float(np.min(a)), 4),
        "p10": round(float(np.percentile(a, 10)), 4),
        "p50": round(float(np.percentile(a, 50)), 4),
        "p90": round(float(np.percentile(a, 90)), 4),
        "max": round(float(np.max(a)), 4),
    }


def run(cost_model: CostModel, draws: int, scenario_ids: Optional[List[str]] = None) -> dict:
    wanted = set(scenario_ids) if scenario_ids else None
    specs = [s for s in SCENARIOS if wanted is None or s["id"] in wanted]

    per_scenario = []
    agg = {"spoilage_reduction": [], "fulfillment_delta": [], "net_revenue_delta": [],
           "net_revenue_opt": [], "spoilage_pct_opt": []}
    total_violations = 0

    for spec in specs:
        base = generate_instance(
            seed=spec["seed"], cost_model=cost_model,
            scenario_id=spec["id"], split=spec["split"],
        )
        records = {"spoilage_reduction": [], "fulfillment_delta": [], "net_revenue_delta": [],
                   "net_revenue_opt": [], "spoilage_pct_opt": []}

        for i in range(draws):
            rng = np.random.default_rng(spec["seed"] * 100_000 + i)
            perturb = sample_perturbation(rng)
            inst = apply_perturbations(base, perturb, seed=spec["seed"] * 100_000 + i)

            plan_opt = solve_optimizer(inst, cost_model)
            m_opt = compute_metrics(inst, cost_model, plan_opt)
            m_base = compute_metrics(inst, cost_model, solve_baseline(inst, cost_model, "fefo"))
            d = compare(m_opt, m_base)

            total_violations += len(check_plan(inst, cost_model, plan_opt))

            records["spoilage_reduction"].append(d["spoilage_pct_reduction"])
            records["fulfillment_delta"].append(d["fulfillment_delta"])
            records["net_revenue_delta"].append(d["net_revenue_delta"])
            records["net_revenue_opt"].append(m_opt.net_revenue)
            records["spoilage_pct_opt"].append(m_opt.spoilage_pct)

        entry = {"scenario_id": spec["id"], "seed": spec["seed"], "split": spec["split"],
                 "draws": draws, "metrics": {k: _stats(v) for k, v in records.items()}}
        per_scenario.append(entry)
        for k in agg:
            agg[k].extend(records[k])

    return {
        "draws": draws,
        "scenarios": per_scenario,
        "overall": {k: _stats(v) for k, v in agg.items()},
        "total_hard_violations": total_violations,
    }


def band(report: dict, scenario_id: Optional[str] = None) -> Dict[str, float]:
    """Compact net-revenue uncertainty band for one scenario (or the overall draw)."""
    metrics: Dict[str, dict]
    chosen = scenario_id
    if scenario_id is not None:
        match = next((s for s in report["scenarios"] if s["scenario_id"] == scenario_id), None)
        if match is not None:
            metrics = match["metrics"]
        else:
            chosen = None
            metrics = report["overall"]
    else:
        metrics = report["overall"]

    if chosen is None:
        chosen = report["scenarios"][0]["scenario_id"] if report["scenarios"] else "overall"

    nrev = metrics.get("net_revenue_opt", {})
    delta = metrics.get("net_revenue_delta", {})
    spoil = metrics.get("spoilage_reduction", {})
    return {
        "scenario_id": chosen,
        "draws": int(report["draws"]),
        "net_revenue_mean": float(nrev.get("mean", 0.0)),
        "net_revenue_p10": float(nrev.get("p10", 0.0)),
        "net_revenue_p90": float(nrev.get("p90", 0.0)),
        "net_revenue_delta_mean": float(delta.get("mean", 0.0)),
        "net_revenue_delta_p10": float(delta.get("p10", 0.0)),
        "spoilage_reduction_mean": float(spoil.get("mean", 0.0)),
        "spoilage_reduction_p10": float(spoil.get("p10", 0.0)),
    }
