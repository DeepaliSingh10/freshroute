"""Extension E4 runner — Monte Carlo robustness & sensitivity.

For each base scenario, draws N random perturbation vectors (shelf-life noise, demand,
travel delay, price shock, missing demand, capacity), solves the optimizer and the FEFO
baseline, and reports the distribution (mean, std, P10/P50/P90, min/max) of the key
metrics. Reproducible: every draw is seeded.

Usage (from apps/api):
    python scripts/run_robustness.py --draws 30 --write-results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.cost_model import CostModel  # noqa: E402
from app.data.generator import apply_perturbations, generate_instance  # noqa: E402
from app.eval.checker import check_plan  # noqa: E402
from app.eval.metrics import compare, compute_metrics  # noqa: E402
from app.optimizer.allocator import solve_optimizer  # noqa: E402
from app.optimizer.baseline import solve_baseline  # noqa: E402

SCENARIOS = [
    {"id": "train_01", "seed": 101, "split": "train"},
    {"id": "test_01", "seed": 202, "split": "test"},
    {"id": "hidden_01", "seed": 303, "split": "hidden"},
]


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


def run(cost_model: CostModel, draws: int) -> dict:
    per_scenario = []
    agg = {"spoilage_reduction": [], "fulfillment_delta": [], "net_revenue_delta": [],
           "net_revenue_opt": [], "spoilage_pct_opt": []}
    total_violations = 0

    for spec in SCENARIOS:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="FreshRoute E4 — Monte Carlo robustness")
    parser.add_argument("--draws", type=int, default=30)
    parser.add_argument("--write-results", action="store_true")
    parser.add_argument(
        "--results",
        default=str(Path(__file__).resolve().parents[3] / "results" / "robustness.json"),
    )
    args = parser.parse_args()

    cost_model = CostModel.load()
    report = run(cost_model, args.draws)

    print(f"FreshRoute E4 — Robustness  | draws={args.draws}  hash={cost_model.config_hash()}")
    hdr = f"  {'scenario':<12}{'spoil_d mean':>13}{'spoil_d P10':>12}{'fulfill_d mean':>15}{'netRev_d mean':>15}{'netRev_d P10':>13}"
    print(hdr)
    for s in report["scenarios"]:
        m = s["metrics"]
        print(
            f"  {s['scenario_id']:<12}"
            f"{m['spoilage_reduction']['mean'] * 100:>12.1f}%"
            f"{m['spoilage_reduction']['p10'] * 100:>11.1f}%"
            f"{m['fulfillment_delta']['mean'] * 100:>14.2f}p"
            f"{m['net_revenue_delta']['mean']:>15,.0f}"
            f"{m['net_revenue_delta']['p10']:>13,.0f}"
        )
    o = report["overall"]
    print(
        f"  {'OVERALL':<12}"
        f"{o['spoilage_reduction']['mean'] * 100:>12.1f}%"
        f"{o['spoilage_reduction']['p10'] * 100:>11.1f}%"
        f"{o['fulfillment_delta']['mean'] * 100:>14.2f}p"
        f"{o['net_revenue_delta']['mean']:>15,.0f}"
        f"{o['net_revenue_delta']['p10']:>13,.0f}"
    )
    print(f"  worst-case (P10) net-revenue delta overall: {o['net_revenue_delta']['p10']:,.0f}")
    print(f"  total hard violations across all draws    : {report['total_hard_violations']}")

    if args.write_results:
        payload = {"phase": "owner_A_phase2_e4_robustness",
                   "cost_model_hash": cost_model.config_hash(), **report}
        p = Path(args.results)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  results written to: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
