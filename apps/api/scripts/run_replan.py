"""Extension E3 runner — disruption replanning demo.

Builds a morning plan, knocks out one origin hub (+6h delay everywhere), then compares
"frozen" (no replan) against "replan" (re-optimize remaining stock).

Usage (from apps/api):
    python scripts/run_replan.py --write-results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.cost_model import CostModel  # noqa: E402
from app.data.generator import generate_instance  # noqa: E402
from app.eval.checker import check_plan  # noqa: E402
from app.eval.metrics import compare, compute_metrics  # noqa: E402
from app.optimizer.allocator import solve_optimizer  # noqa: E402
from app.optimizer.replan import Disruption, apply_disruption, replan  # noqa: E402


def _clean(metrics) -> dict:
    d = metrics.to_dict()
    d.pop("runtime_ms", None)  # timing is not part of the reproducible result
    return d


def _origin_stock(instance) -> dict:
    acc: dict = {}
    for b in instance.batches.values():
        acc[b.origin_id] = acc.get(b.origin_id, 0.0) + b.quantity_kg
    return acc


def main() -> int:
    parser = argparse.ArgumentParser(description="FreshRoute E3 — disruption replan")
    parser.add_argument("--seed", type=int, default=303)
    parser.add_argument("--split", default="hidden")
    parser.add_argument("--delay-hours", type=float, default=6.0)
    parser.add_argument("--write-results", action="store_true")
    parser.add_argument(
        "--results",
        default=str(Path(__file__).resolve().parents[3] / "results" / "replan_summary.json"),
    )
    args = parser.parse_args()

    cost_model = CostModel.load()
    base = generate_instance(
        seed=args.seed, cost_model=cost_model, scenario_id=f"{args.split}_01", split=args.split
    )

    plan0 = solve_optimizer(base, cost_model)
    m0 = compute_metrics(base, cost_model, plan0)

    stock = _origin_stock(base)
    blocked = max(stock, key=stock.get)
    disruption = Disruption(
        blocked_origins=(blocked,),
        travel_delay_hours=args.delay_hours,
        description=f"{blocked} hub outbound lanes closed + {args.delay_hours}h delay network-wide",
    )
    inst_dis = apply_disruption(base, disruption)

    frozen, combined = replan(inst_dis, plan0, cost_model)
    m_frozen = compute_metrics(inst_dis, cost_model, frozen)
    m_replan = compute_metrics(inst_dis, cost_model, combined)
    violations = len(check_plan(inst_dis, cost_model, combined))
    delta = compare(m_replan, m_frozen)

    print(f"FreshRoute E3 — Disruption replan  | hash={cost_model.config_hash()}")
    print(f"  morning plan (pre-disruption): spoilage {m0.spoilage_kg:,.0f}kg  net_rev {m0.net_revenue:,.0f}")
    print(f"  disruption: {disruption.description}  (hub stock {stock[blocked]:,.0f}kg)")
    print(f"  {'':<14}{'spoilage(kg)':>14}{'clearance(kg)':>15}{'fulfilled(kg)':>15}{'net_rev':>14}")
    print(
        f"  {'no replan':<14}{m_frozen.spoilage_kg:>14,.0f}{m_frozen.clearance_kg:>15,.0f}"
        f"{m_frozen.fulfilled_kg:>15,.0f}{m_frozen.net_revenue:>14,.0f}"
    )
    print(
        f"  {'replan':<14}{m_replan.spoilage_kg:>14,.0f}{m_replan.clearance_kg:>15,.0f}"
        f"{m_replan.fulfilled_kg:>15,.0f}{m_replan.net_revenue:>14,.0f}"
    )
    print(
        f"  recovery: spoilage {delta['spoilage_pct_reduction'] * 100:+.1f}%  "
        f"net_rev {delta['net_revenue_delta']:+,.0f} ({delta['net_revenue_delta_pct'] * 100:+.1f}%)  "
        f"hard violations {violations}"
    )

    if args.write_results:
        payload = {
            "phase": "owner_A_phase2_e3_replan",
            "cost_model_hash": cost_model.config_hash(),
            "disruption": {
                "blocked_origins": list(disruption.blocked_origins),
                "travel_delay_hours": disruption.travel_delay_hours,
                "description": disruption.description,
                "hub_stock_kg": round(stock[blocked], 1),
            },
            "morning_plan": _clean(m0),
            "no_replan": _clean(m_frozen),
            "replan": _clean(m_replan),
            "recovery": delta,
            "hard_violations": violations,
        }
        p = Path(args.results)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  results written to: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
