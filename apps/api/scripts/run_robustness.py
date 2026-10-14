"""Extension E4 runner — Monte Carlo robustness & sensitivity.

Thin CLI wrapper over `app.eval.robustness` (the engine shared with the API). Writes
`results/robustness.json`. Reproducible: every draw is seeded.

Usage (from apps/api):
    python scripts/run_robustness.py --draws 30 --write-results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.cost_model import CostModel  # noqa: E402
from app.eval.robustness import run  # noqa: E402


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
