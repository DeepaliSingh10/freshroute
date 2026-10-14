# results/ — reproducibility artifacts

Every number quoted in the docs and the UI is produced by a runner script and frozen
here as JSON. All artifacts are **deterministic** (timing is stripped) and are pinned to
the cost-model config hash.

## Regenerate everything

```
cd apps/api
python scripts/run_all.py         # runs every runner, then writes manifest.json
```

## Verify

```
cd apps/api
pytest tests/test_reproducibility.py -q
```

The manifest test fails if any artifact drifts from what is recorded (e.g. after an
unintended change to the data generator, optimizer or `cost_model.yaml`).

## Files

| File | Produced by | Contents |
|------|-------------|----------|
| `phase1_summary.json` | `run_phase1.py --no-clearance` | Phase 1, no clearance channel |
| `phase2_summary.json` | `run_phase1.py` | Phase 2, clearance + discounts; FEFO/naive/optimized per scenario |
| `forecast_summary.json` | `run_forecast.py` | E1 demand-forecast backtest (MAPE) + predict-then-optimize |
| `robustness.json` | `run_robustness.py --draws 30` | E4 Monte Carlo (mean / P10 spoilage & net revenue) |
| `replan_summary.json` | `run_replan.py` | E3 disruption replan (morning / no-replan / replan) |
| `discount_policy_summary.json` | `run_discount_policy.py` | E2 optimized markdown vs fixed 30% rule |
| `telemetry_summary.json` | `run_telemetry.py` | E5 cold-chain excursions + market price feed |
| `sensitivity_summary.json` | `run_sensitivity.py` | One-factor sweeps feeding the UI sliders |
| `manifest.json` | `scripts/run_all.py` | cost-model hash + environment + SHA-256 per artifact |

> `results/` is owned by Owner B (API, evaluation & reproducibility). The API
> (`apps/api`) reads none of these at request time — they exist to prove the claims.
