"""Sensitivity runner — one-factor sweeps for the UI sliders.

Usage (from apps/api):
    python scripts/run_sensitivity.py --write-results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.cost_model import CostModel  # noqa: E402
from app.data.generator import generate_instance  # noqa: E402
from app.eval.sensitivity import FACTORS, sweep  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="FreshRoute - sensitivity sweeps")
    ap.add_argument("--seed", type=int, default=303)
    ap.add_argument("--write-results", action="store_true")
    ap.add_argument(
        "--results",
        default=str(Path(__file__).resolve().parents[3] / "results" / "sensitivity_summary.json"),
    )
    args = ap.parse_args()

    cm = CostModel.load()
    base = generate_instance(seed=args.seed, cost_model=cm, split="hidden", with_clearance=True)

    curves = {}
    print(f"FreshRoute - sensitivity sweeps  | hash={cm.config_hash()}")
    for factor, meta in FACTORS.items():
        pts = sweep(base, cm, factor, meta["default_range"], seed=args.seed)
        curves[factor] = {"label": meta["label"], "range": meta["default_range"], "points": pts}
        red = [p["spoilage_reduction_pct"] for p in pts]
        print(f"  {meta['label']:<18} spoilage reduction vs FEFO: {min(red):+.1f}% .. {max(red):+.1f}%")

    if args.write_results:
        payload = {"phase": "owner_A_sensitivity", "cost_model_hash": cm.config_hash(), "curves": curves}
        p = Path(args.results)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  results written to: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
