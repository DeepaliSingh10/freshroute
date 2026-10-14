"""Extension E1 runner — demand forecasting backtest + predict-then-optimize demo.

Usage (from apps/api):
    python scripts/run_forecast.py --write-results
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.cost_model import CostModel  # noqa: E402
from app.data.generator import DEFAULT_NOW, generate_instance  # noqa: E402
from app.data.models import Demand  # noqa: E402
from app.eval.metrics import compute_metrics, compare  # noqa: E402
from app.forecast.forecaster import backtest, fit, generate_demand_history  # noqa: E402
from app.optimizer.allocator import solve_optimizer  # noqa: E402
from app.optimizer.baseline import solve_baseline  # noqa: E402


def _scale_for(instance, target_ratio: float = 0.85) -> float:
    total_supply = sum(b.quantity_kg for b in instance.batches.values())
    weight = sum(
        c.popularity * d.size_factor
        for c in instance.commodities.values()
        for d in instance.destinations.values()
        if not d.is_clearance
    )
    return total_supply * target_ratio / max(weight, 1e-9)


def _clean(metrics) -> dict:
    d = metrics.to_dict()
    d.pop("runtime_ms", None)  # timing is not part of the reproducible result
    return d


def _demands_from_rows(instance, rows, target_date):
    """Replace non-clearance demand with given rows; keep clearance + prices."""
    price = {(d.destination_id, d.commodity_id): d.price_per_kg for d in instance.demands}
    demands = []
    for d in instance.demands:
        if instance.destinations[d.destination_id].is_clearance:
            demands.append(d)
    for r in rows:
        key = (r["destination_id"], r["commodity_id"])
        if instance.destinations[r["destination_id"]].is_clearance:
            continue
        demands.append(
            Demand(
                destination_id=r["destination_id"],
                commodity_id=r["commodity_id"],
                date=target_date.isoformat(),
                demand_kg=float(r["demand_kg"]),
                price_per_kg=price.get(key, 0.0),
                event_flag=r.get("event_flag", ""),
            )
        )
    return replace(instance, demands=demands)


def main() -> int:
    parser = argparse.ArgumentParser(description="FreshRoute E1 — demand forecasting")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--days", type=int, default=91)
    parser.add_argument("--holdout", type=int, default=14)
    parser.add_argument("--write-results", action="store_true")
    parser.add_argument(
        "--results",
        default=str(Path(__file__).resolve().parents[3] / "results" / "forecast_summary.json"),
    )
    args = parser.parse_args()

    cost_model = CostModel.load()
    base = generate_instance(
        seed=args.seed, cost_model=cost_model, scenario_id="forecast", split="train"
    )

    history = generate_demand_history(
        seed=args.seed + 7,
        commodities=base.commodities,
        destinations=base.destinations,
        base_date=date(2026, 1, 5),
        days=args.days,
        scale=_scale_for(base),
    )

    report = backtest(history, holdout_days=args.holdout)

    print(f"FreshRoute E1 — Demand forecasting  | cost_model hash={cost_model.config_hash()}")
    print(
        f"  history: {report['train_days']} train days, {report['holdout_days']} holdout days, "
        f"{report['n_series']} series, {report['n_test_points']} test points"
    )
    print(f"  {'method':<16}{'MAE':>10}{'MAPE':>10}{'bias':>10}")
    for name, m in report["methods"].items():
        print(f"  {name:<16}{m['mae']:>10.2f}{m['mape'] * 100:>9.1f}%{m['bias'] * 100:>9.1f}%")
    best = min(report["methods"].items(), key=lambda kv: kv[1]["mape"])[0]
    print(f"  best method by MAPE: {best}")

    # --- predict-then-optimize: does the plan stay sound under forecast error? ---
    dmax = max(date.fromisoformat(r["date"]) for r in history)
    true_rows = [r for r in history if r["date"] == dmax.isoformat()]
    train_rows = [r for r in history if r["date"] != dmax.isoformat()]
    model = fit(train_rows)
    fc_rows = [
        {
            "destination_id": r["destination_id"],
            "commodity_id": r["commodity_id"],
            "demand_kg": model.predict(
                r["destination_id"], r["commodity_id"], dmax, is_event=bool(r["event_flag"])
            ),
            "event_flag": r["event_flag"],
        }
        for r in true_rows
    ]

    inst_true = _demands_from_rows(base, true_rows, dmax)
    inst_fc = _demands_from_rows(base, fc_rows, dmax)

    plan_true = solve_optimizer(inst_true, cost_model)
    plan_fc = solve_optimizer(inst_fc, cost_model)
    m_true = compute_metrics(inst_true, cost_model, plan_true)
    m_fc = compute_metrics(inst_fc, cost_model, plan_fc)

    # Evaluate the forecast-based plan against the TRUE demand it actually faces.
    plan_fc_on_true = compute_metrics(inst_true, cost_model, plan_fc)
    delta = compare(m_fc, m_true)

    print("\n  predict-then-optimize (next day):")
    print(f"    {'':<22}{'demand_kg':>12}{'fulfill%':>10}{'net_rev':>14}{'spoilage(kg)':>14}")
    print(
        f"    {'with TRUE demand':<22}{m_true.demand_kg:>12,.0f}{m_true.fulfillment_pct * 100:>9.1f}%"
        f"{m_true.net_revenue:>14,.0f}{m_true.spoilage_kg:>14,.0f}"
    )
    print(
        f"    {'with FORECAST':<22}{m_fc.demand_kg:>12,.0f}{m_fc.fulfillment_pct * 100:>9.1f}%"
        f"{m_fc.net_revenue:>14,.0f}{m_fc.spoilage_kg:>14,.0f}"
    )
    print(
        f"    forecast-plan evaluated on TRUE demand: fulfill {plan_fc_on_true.fulfillment_pct * 100:.1f}%  "
        f"net_rev {plan_fc_on_true.net_revenue:,.0f}"
    )

    integration = {
        "target_date": dmax.isoformat(),
        "true": _clean(m_true),
        "forecast": _clean(m_fc),
        "forecast_plan_on_true_demand": _clean(plan_fc_on_true),
        "delta_forecast_vs_true": delta,
    }

    if args.write_results:
        payload = {
            "phase": "owner_A_phase2_e1_forecast",
            "cost_model_hash": cost_model.config_hash(),
            "backtest": report,
            "integration": integration,
        }
        p = Path(args.results)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\n  results written to: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
