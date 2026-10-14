"""E2 runner — optimized markdown timing/price for every at-risk batch.

Pipeline: generate hidden instance -> LP optimizer plan -> collect at-risk batches
(leftover, or routed to the clearance channel) -> optimize the markdown for each and
compare against the fixed 30%-off rule (M4) and doing nothing.

Usage:
    python scripts/run_discount_policy.py [--seed 303] [--write-results]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.cost_model import CostModel
from app.data.generator import generate_instance
from app.optimizer.allocator import solve_optimizer
from app.optimizer.discount_policy import optimize_batch_markdown

REPO_ROOT = Path(__file__).resolve().parents[3]
EPS = 1e-6


def run(seed: int) -> dict:
    cost_model = CostModel.load()
    policy = cost_model.discount_policy
    instance = generate_instance(seed=seed, cost_model=cost_model, split="hidden", with_clearance=True)
    plan = solve_optimizer(instance, cost_model)

    at_risk = set(bid for bid, kg in plan.leftover.items() if kg > EPS)
    for d in plan.dispatches:
        if instance.destinations[d.destination_id].is_clearance:
            at_risk.add(d.batch_id)

    decisions = []
    for i, bid in enumerate(sorted(at_risk)):
        b = instance.batches[bid]
        c = instance.commodities[b.commodity_id]
        decisions.append(
            optimize_batch_markdown(
                batch_id=bid,
                commodity_name=c.name,
                quantity=b.quantity_kg,
                base_price=c.base_price_per_kg,
                cost_basis=c.cost_basis_per_kg,
                spoilage_fraction=cost_model.spoilage_fraction(c.perishability_class),
                rsl=b.remaining_shelf_life_days,
                policy=policy,
                seed=seed * 1000 + i,
            )
        )

    total_exp = sum(d.expected_value for d in decisions)
    total_rule = sum(d.rule_30_value for d in decisions)
    total_none = sum(d.no_discount_value for d in decisions)
    marked = [d for d in decisions if d.discount_pct > 0]

    return {
        "scenario": {"seed": seed, "split": instance.split},
        "n_at_risk_batches": len(decisions),
        "n_marked_down": len(marked),
        "totals": {
            "expected_value": round(total_exp, 2),
            "rule_30_value": round(total_rule, 2),
            "no_discount_value": round(total_none, 2),
            "uplift_vs_rule_30": round(total_exp - total_rule, 2),
            "uplift_vs_no_discount": round(total_exp - total_none, 2),
        },
        "decisions": [
            {
                "batch_id": d.batch_id,
                "commodity": d.commodity_name,
                "quantity_kg": d.quantity_kg,
                "remaining_shelf_life_days": d.remaining_shelf_life_days,
                "discount_pct": d.discount_pct,
                "hold_days": d.hold_days,
                "expected_value": d.expected_value,
                "p10_value": d.p10_value,
                "rule_30_value": d.rule_30_value,
                "reason": d.reason,
            }
            for d in decisions
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=303)
    ap.add_argument("--write-results", action="store_true")
    args = ap.parse_args()

    out = run(args.seed)
    t = out["totals"]
    print("=" * 64)
    print("E2 — OPTIMIZED MARKDOWN (at-risk batches)")
    print("=" * 64)
    print(f"  at-risk batches        : {out['n_at_risk_batches']} ({out['n_marked_down']} marked down)")
    print(f"  expected value         : {t['expected_value']:,.0f}")
    print(f"  fixed 30% rule         : {t['rule_30_value']:,.0f}")
    print(f"  no discount            : {t['no_discount_value']:,.0f}")
    print(f"  uplift vs 30% rule     : {t['uplift_vs_rule_30']:+,.0f}")
    print(f"  uplift vs no discount  : {t['uplift_vs_no_discount']:+,.0f}")
    for d in out["decisions"][:4]:
        print(f"    - {d['reason']}")

    if args.write_results:
        (REPO_ROOT / "results").mkdir(parents=True, exist_ok=True)
        dest = REPO_ROOT / "results" / "discount_policy_summary.json"
        dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"  results written to     : {dest}")


if __name__ == "__main__":
    main()
