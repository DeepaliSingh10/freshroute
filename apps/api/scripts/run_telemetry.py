"""E5 runner — simulated cold-chain telemetry and live market-price feed.

Usage (from apps/api):
    python scripts/run_telemetry.py --write-results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.cost_model import CostModel  # noqa: E402
from app.data.generator import generate_instance  # noqa: E402
from app.data.telemetry import (  # noqa: E402
    apply_price_feed,
    apply_temperature_effect,
    price_factors_at,
    simulate_price_feed,
    simulate_temperatures,
)
from app.eval.checker import check_plan  # noqa: E402
from app.eval.metrics import compute_metrics  # noqa: E402
from app.optimizer.allocator import solve_optimizer  # noqa: E402


def _clean(metrics) -> dict:
    d = metrics.to_dict()
    d.pop("runtime_ms", None)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description="FreshRoute E5 - telemetry & market feed")
    ap.add_argument("--seed", type=int, default=303)
    ap.add_argument("--write-results", action="store_true")
    ap.add_argument(
        "--results",
        default=str(Path(__file__).resolve().parents[3] / "results" / "telemetry_summary.json"),
    )
    args = ap.parse_args()

    cm = CostModel.load()
    base = generate_instance(seed=args.seed, cost_model=cm, split="hidden", with_clearance=True)

    plan0 = solve_optimizer(base, cm)
    m0 = compute_metrics(base, cm, plan0)

    # --- cold chain ---
    telem = simulate_temperatures(base, cm, seed=args.seed + 1)
    degraded = apply_temperature_effect(base, telem, cm)
    m_ignore = compute_metrics(degraded, cm, plan0)
    v_ignore = check_plan(degraded, cm, plan0)

    plan_temp = solve_optimizer(degraded, cm)
    m_temp = compute_metrics(degraded, cm, plan_temp)
    v_temp = check_plan(degraded, cm, plan_temp)

    exc = telem.batches_with_excursion()
    total_dh = sum(telem.degree_hours_above.values())
    total_lost = sum(telem.life_lost_days.values())

    # --- market price feed ---
    ticks = simulate_price_feed(base, cm, seed=args.seed + 2)
    n_ticks = max((t.tick for t in ticks), default=0)
    feed_series = []
    for k in range(n_ticks + 1):
        factors = price_factors_at(ticks, k)
        inst_k = apply_price_feed(base, factors, cm)
        plan_k = solve_optimizer(inst_k, cm)
        m_k = compute_metrics(inst_k, cm, plan_k)
        mean_factor = sum(factors.values()) / len(factors) if factors else 1.0
        feed_series.append(
            {
                "tick": k,
                "mean_price_factor": round(mean_factor, 4),
                "spoilage_kg": round(m_k.spoilage_kg, 1),
                "fulfilled_kg": round(m_k.fulfilled_kg, 1),
                "net_revenue": round(m_k.net_revenue, 1),
            }
        )

    print(f"FreshRoute E5 - telemetry & market feed  | hash={cm.config_hash()}")
    print("  COLD CHAIN")
    print(f"    excursions: {len(exc)}/{len(base.batches)} batches  threshold {telem.threshold_c:.1f}C")
    print(f"    total degree-hours {total_dh:,.0f}  ->  life lost {total_lost:,.2f} batch-days")
    print(f"    {'plan':<16}{'spoilage(kg)':>14}{'fulfilled(kg)':>15}{'net_rev':>14}{'violations':>12}")
    print(f"    {'nominal':<16}{m0.spoilage_kg:>14,.0f}{m0.fulfilled_kg:>15,.0f}{m0.net_revenue:>14,.0f}{0:>12}")
    print(f"    {'ignore telem.':<16}{m_ignore.spoilage_kg:>14,.0f}{m_ignore.fulfilled_kg:>15,.0f}{m_ignore.net_revenue:>14,.0f}{len(v_ignore):>12}")
    print(f"    {'temp-aware':<16}{m_temp.spoilage_kg:>14,.0f}{m_temp.fulfilled_kg:>15,.0f}{m_temp.net_revenue:>14,.0f}{len(v_temp):>12}")
    print("  MARKET PRICE FEED")
    for row in feed_series:
        print(f"    tick {row['tick']}  factor {row['mean_price_factor']:.3f}  net_rev {row['net_revenue']:,.0f}")

    if args.write_results:
        payload = {
            "phase": "owner_A_phase2_e5_telemetry",
            "cost_model_hash": cm.config_hash(),
            "cold_chain": {
                "threshold_c": telem.threshold_c,
                "n_readings": len(telem.readings),
                "n_excursion_batches": len(exc),
                "total_degree_hours": round(total_dh, 2),
                "total_life_lost_batch_days": round(total_lost, 3),
                "nominal": _clean(m0),
                "ignore_telemetry": {**_clean(m_ignore), "hard_violations": len(v_ignore)},
                "temp_aware_replan": {**_clean(m_temp), "hard_violations": len(v_temp)},
            },
            "price_feed": {"ticks": feed_series},
        }
        p = Path(args.results)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  results written to: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
