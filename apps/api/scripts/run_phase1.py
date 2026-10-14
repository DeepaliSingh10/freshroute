"""Owner A Phase 1 runner.

Generate synthetic scenarios, run the FEFO baseline and the LP optimizer, and print
the metric deltas (spoilage, fulfillment, net revenue). Optionally materialize CSVs.

Usage (from apps/api):
    python scripts/run_phase1.py
    python scripts/run_phase1.py --write-csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.cost_model import CostModel  # noqa: E402
from app.data.generator import generate_instance, apply_perturbations, write_instance_csv  # noqa: E402
from app.optimizer.allocator import solve_optimizer  # noqa: E402
from app.optimizer.baseline import solve_baseline  # noqa: E402
from app.optimizer.discounts import recommend_discounts  # noqa: E402
from app.eval.metrics import compute_metrics, compare  # noqa: E402
from app.eval.checker import check_plan  # noqa: E402

SCENARIOS = [
    {
        "id": "train_01",
        "seed": 101,
        "split": "train",
        "perturb": {"rsl_noise_pct": 0.05},
    },
    {
        "id": "test_01",
        "seed": 202,
        "split": "test",
        "perturb": {"demand_multiplier": 1.2, "travel_delay_hours": 4.0},
    },
    {
        "id": "hidden_01",
        "seed": 303,
        "split": "hidden",
        "perturb": {
            "rsl_noise_pct": 0.10,
            "demand_multiplier": 1.4,
            "travel_delay_hours": 6.0,
            "price_shock_pct": -0.08,
            "missing_demand_pct": 0.03,
        },
    },
]


def run_scenario(
    spec: dict, cost_model: CostModel, write_csv: bool, out_dir: Path, with_clearance: bool = True
) -> dict:
    base = generate_instance(
        seed=spec["seed"],
        cost_model=cost_model,
        scenario_id=spec["id"],
        split=spec["split"],
        with_clearance=with_clearance,
    )
    instance = apply_perturbations(base, spec.get("perturb"), seed=spec["seed"] + 1)

    if write_csv:
        write_instance_csv(instance, out_dir / spec["id"])

    plan_base = solve_baseline(instance, cost_model, strategy="fefo")
    plan_naive = solve_baseline(instance, cost_model, strategy="naive")
    plan_opt = solve_optimizer(instance, cost_model)

    m_base = compute_metrics(instance, cost_model, plan_base)
    m_naive = compute_metrics(instance, cost_model, plan_naive)
    m_opt = compute_metrics(instance, cost_model, plan_opt)

    # Independent feasibility check applies to feasible-by-design plans only.
    m_base.violations = len(check_plan(instance, cost_model, plan_base))
    m_opt.violations = len(check_plan(instance, cost_model, plan_opt))

    discounts = recommend_discounts(instance, cost_model, plan_opt)

    delta = compare(m_opt, m_base)
    delta_naive = compare(m_opt, m_naive)

    return {
        "instance": instance,
        "base": m_base,
        "naive": m_naive,
        "opt": m_opt,
        "delta": delta,
        "delta_naive": delta_naive,
        "discounts": discounts,
    }


def _fmt(x: float, nd: int = 2) -> str:
    return f"{x:,.{nd}f}"


def _feasibility_coverage(instance, cost_model) -> tuple:
    """How many batches can reach at least one destination; structural spoilage floor."""
    from app.optimizer.feasibility import build_feasible_pairs

    pairs = build_feasible_pairs(instance, cost_model, include_clearance=False)
    reachable = {bid for (bid, _) in pairs}
    total = len(instance.batches)
    stranded_kg = sum(
        b.quantity_kg for b in instance.batches.values() if b.batch_id not in reachable
    )
    return len(reachable), total, stranded_kg


def _print_scenario(result: dict, cost_model: CostModel) -> None:
    inst = result["instance"]
    b, nv, o, d = result["base"], result["naive"], result["opt"], result["delta"]
    dn = result["delta_naive"]
    reach, total, stranded = _feasibility_coverage(inst, cost_model)
    print(f"\n=== Scenario: {inst.scenario_id}  [{inst.split}]  seed={inst.seed} ===")
    print(
        f"  batches={total} (reachable={reach}, stranded={stranded:,.0f}kg)  "
        f"destinations={len(inst.destinations)}  demand_rows={len(inst.demands)}  "
        f"lanes={len(inst.lanes)}  solver={o.status}  runtime={o.runtime_ms:.1f} ms"
    )
    rows = [
        ("Spoilage (kg)", b.spoilage_kg, nv.spoilage_kg, o.spoilage_kg),
        ("Spoilage (%)", b.spoilage_pct * 100, nv.spoilage_pct * 100, o.spoilage_pct * 100),
        ("Expired (kg)", b.expired_kg, nv.expired_kg, o.expired_kg),
        ("Clearance (kg)", b.clearance_kg, nv.clearance_kg, o.clearance_kg),
        ("Fulfillment (%)", b.fulfillment_pct * 100, nv.fulfillment_pct * 100, o.fulfillment_pct * 100),
        ("Net revenue", b.net_revenue, nv.net_revenue, o.net_revenue),
        ("Transport cost", b.transport_cost, nv.transport_cost, o.transport_cost),
        ("Spoilage cost", b.spoilage_cost, nv.spoilage_cost, o.spoilage_cost),
        ("Violations", b.violations, nv.violations, o.violations),
    ]
    print(f"  {'metric':<16}{'FEFO base':>15}{'naive':>15}{'optimized':>15}")
    for name, bv, nvv, ov in rows:
        print(f"  {name:<16}{_fmt(bv):>15}{_fmt(nvv):>15}{_fmt(ov):>15}")
    print(
        f"  vs FEFO  : spoilage {d['spoilage_pct_reduction'] * 100:+.1f}%  "
        f"fulfill {d['fulfillment_delta'] * 100:+.1f}pts  "
        f"net rev {_fmt(d['net_revenue_delta'])} ({d['net_revenue_delta_pct'] * 100:+.1f}%)"
    )
    print(
        f"  vs naive : spoilage {dn['spoilage_pct_reduction'] * 100:+.1f}%  "
        f"fulfill {dn['fulfillment_delta'] * 100:+.1f}pts  "
        f"net rev {_fmt(dn['net_revenue_delta'])} ({dn['net_revenue_delta_pct'] * 100:+.1f}%)"
    )

    disc = result["discounts"]
    recovered = sum(x.expected_recovered_value for x in disc)
    cleared = [x for x in disc if x.rule_id == "clearance_recovery"]
    print(
        f"  discounts: {len(disc)} recommendations  "
        f"(clearance_recovery={len(cleared)}, recovered=Rs{_fmt(recovered)})"
    )
    for x in disc[:2]:
        print(f"    - [{x.rule_id}] {x.reason}")




def main() -> int:
    parser = argparse.ArgumentParser(description="FreshRoute Owner A Phase 1 runner")
    parser.add_argument("--write-csv", action="store_true", help="materialize instance CSVs")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parents[3] / "data" / "generated"),
        help="CSV output directory",
    )
    parser.add_argument("--write-results", action="store_true", help="write results JSON")
    parser.add_argument(
        "--no-clearance",
        action="store_true",
        help="disable the local clearance channel (reproduces the Phase 1 artifact)",
    )
    parser.add_argument(
        "--results",
        default=None,
        help="results JSON path (default: results/phase{1,2}_summary.json)",
    )
    args = parser.parse_args()

    with_clearance = not args.no_clearance
    phase = "owner_A_phase2" if with_clearance else "owner_A_phase1"
    if args.results is None:
        fname = "phase2_summary.json" if with_clearance else "phase1_summary.json"
        args.results = str(Path(__file__).resolve().parents[3] / "results" / fname)

    cost_model = CostModel.load()
    print(f"FreshRoute Owner A — {phase}  | cost_model hash={cost_model.config_hash()}")
    out_dir = Path(args.out)

    results = []
    for spec in SCENARIOS:
        res = run_scenario(spec, cost_model, args.write_csv, out_dir, with_clearance)
        _print_scenario(res, cost_model)
        results.append(res)

    print("\n================ SUMMARY (mean over scenarios) ================")
    n = len(results)
    mean_sr = sum(r["delta"]["spoilage_pct_reduction"] for r in results) / n
    mean_fd = sum(r["delta"]["fulfillment_delta"] for r in results) / n
    mean_nd = sum(r["delta"]["net_revenue_delta"] for r in results) / n
    mean_sr_n = sum(r["delta_naive"]["spoilage_pct_reduction"] for r in results) / n
    mean_nd_n = sum(r["delta_naive"]["net_revenue_delta"] for r in results) / n
    total_viol = sum(r["opt"].violations for r in results)
    print(f"  vs FEFO  : spoilage {mean_sr * 100:+.1f}%   net revenue {_fmt(mean_nd)}")
    print(f"  vs naive : spoilage {mean_sr_n * 100:+.1f}%   net revenue {_fmt(mean_nd_n)}")
    print(f"  mean fulfillment delta : {mean_fd * 100:+.2f} pts")
    print(f"  total hard violations   : {total_viol}")
    if args.write_csv:
        print(f"  CSVs written under      : {out_dir}")

    if args.write_results:
        import json
        from dataclasses import asdict

        def _clean(metrics) -> dict:
            d = metrics.to_dict()
            d.pop("runtime_ms", None)  # timing is not part of the reproducible result
            return d

        payload = {
            "phase": phase,
            "cost_model_hash": cost_model.config_hash(),
            "scenarios": [
                {
                    "scenario_id": r["instance"].scenario_id,
                    "split": r["instance"].split,
                    "seed": r["instance"].seed,
                    "baseline_fefo": _clean(r["base"]),
                    "baseline_naive": _clean(r["naive"]),
                    "optimized": _clean(r["opt"]),
                    "delta_vs_fefo": r["delta"],
                    "delta_vs_naive": r["delta_naive"],
                    "discounts": {
                        "count": len(r["discounts"]),
                        "clearance_recovery": sum(
                            1 for x in r["discounts"] if x.rule_id == "clearance_recovery"
                        ),
                        "expected_recovered_value": round(
                            sum(x.expected_recovered_value for x in r["discounts"]), 2
                        ),
                        "recommendations": [asdict(x) for x in r["discounts"]],
                    },
                }
                for r in results
            ],
        }
        res_path = Path(args.results)
        res_path.parent.mkdir(parents=True, exist_ok=True)
        res_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  results written to      : {res_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
