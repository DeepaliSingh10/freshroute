# apps/api — FreshRoute backend

Python 3.11+ · OR-Tools (GLOP) · numpy/pandas · FastAPI.
Owner A (data + optimizer), Owner B (HTTP service + tests) and Owner C (dashboard, see
`../web`) are **done**. The API serves the dashboard's frozen contract.

## Layout
```
app/
  data/
    models.py         # domain model (frozen schema — docs/DATA_SPEC.md)
    constants.py      # commodity catalog, locations, grade factors
    cost_model.yaml   # single source of truth for the economic cost model
    cost_model.py     # loader (config hash for reproducibility)
    generator.py      # deterministic synthetic generator + clearance outlets + perturbations
    telemetry.py      # E5: cold-chain temperatures + market-price feed
    scenarios.py      # shared scenario registry (train/test/hidden) for API + scripts
    baseline_definition.yaml # frozen baseline strategy spec
  optimizer/
    feasibility.py    # shelf-life feasibility precompute (shared; include_clearance flag)
    baseline.py       # baseline strategies (fefo / margin / naive) — no clearance
    allocator.py      # LP: maximize net revenue subject to hard constraints
    discounts.py      # rule-based discount recommendation engine (M4)
    discount_policy.py # E2: optimized markdown depth x timing under uncertainty
    replan.py         # disruption replan: committed + residual re-optimization (E3)
    types.py          # Plan / Dispatch
  forecast/
    forecaster.py     # transparent demand forecasting + backtest (E1)
  eval/
    metrics.py        # spoilage / fulfillment / net revenue / expired / clearance
    checker.py        # INDEPENDENT hard-constraint checker (0 violations)
    sensitivity.py    # one-factor sweeps feeding the UI sliders
  api/
    schemas.py        # Pydantic v2 response models (frozen HTTP contract)
    service.py        # assembles responses from the optimizer/eval layers
  main.py             # FastAPI app factory + CORS + endpoints
  repro.py            # reproducibility harness (env stamp + artifact manifest)
tests/                # pytest suite (cost model, optimizer, baselines, API, ...)
scripts/
  run_phase1.py       # generate -> baseline -> optimize -> evaluate -> discounts
  run_forecast.py     # E1: forecast backtest + predict-then-optimize
  run_robustness.py   # E4: Monte Carlo robustness (mean/P10)
  run_replan.py       # E3: disruption replan demo
  run_discount_policy.py # E2: optimized markdown vs fixed rule
  run_telemetry.py    # E5: cold-chain telemetry + market-price feed
  run_sensitivity.py  # one-factor sensitivity curves for the UI
  run_all.py          # regenerate every artifact + write results/manifest.json
```

## Setup
```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```
python scripts/run_phase1.py --write-csv --write-results
```
- `--write-csv` materializes the generated dataset to `../../data/generated/`.
- `--write-results` writes `../../results/phase2_summary.json` (timing stripped → deterministic).
- `--no-clearance` disables the local clearance channel and writes
  `../../results/phase1_summary.json` (reproduces the Phase 1 artifact).

## What Phase 1 delivers
- Deterministic synthetic dataset (batches, demand, lanes, cost model) with train/test/hidden scenarios.
- Shelf-life feasibility engine (MVP M3).
- LP allocator maximizing net revenue under hard constraints: stock, demand cap, lane capacity, shelf-life.
- Two baselines: **FEFO** (strong, urgency-aware) and **naive** (price-first, shelf-life-blind).
- Independent feasibility checker proving **0 hard violations**.
- Metric module: spoilage, fulfillment, net revenue, expired-on-arrival.

## What Phase 2 (part 1) adds
- **Local clearance channel** (per-origin `CLR-*` outlets) that baselines do NOT have —
  recovers value on at-risk / stranded stock instead of spoiling it (MVP M4).
- **Discount recommendation engine** (`optimizer/discounts.py`) with rules
  `clearance_recovery`, `spoil_no_buyer`, `at_risk_monitor` and a reason per recommendation.
- Clearance modeled as an optional salvage sink (never penalized), so recovery is pure upside.
- Clearance excluded from the demand/fulfillment denominator; salvage revenue counted in net revenue.

## What Phase 2 (part 2) adds — extensions
- **E1 Demand forecasting** (`run_forecast.py`): transparent level × day-of-week × event model;
  holdout MAPE **17.4%** vs naive 24.7–28.7%; predict-then-optimize stays within ~1%.
- **E2 Optimized markdown** (`run_discount_policy.py`): per at-risk batch, search depth × timing to
  maximize expected recovered value under uncertainty; **+200,923** vs the fixed 30% rule.
- **E3 Disruption replan** (`run_replan.py`): keep committed shipments, re-optimize the residual
  stock on the disrupted network; hub outage + 6h delay → spoilage −20.4%, net rev +213,504, 0 violations.
- **E4 Monte Carlo robustness** (`run_robustness.py`): 30 draws × 3 scenarios; mean spoilage
  reduction −57.7% (P10 −46.3%), net-rev delta mean +331,772 (P10 +271,309), 0 violations.
- **E5 Cold-chain telemetry + price feed** (`run_telemetry.py`): temperature excursions cost
  10.4 batch-days of life; ignoring them gives 5 infeasible shipments (temp-aware replan: 0).
  A market-price walk lifts net revenue 626,512 → 648,001.

```
python scripts/run_forecast.py --write-results
python scripts/run_robustness.py --draws 30 --write-results
python scripts/run_replan.py --write-results
python scripts/run_discount_policy.py --write-results
python scripts/run_telemetry.py --write-results
```

## Results (see `../../results/`)
**Phase 2 (with clearance)** — mean over train/test/hidden:
| Comparison | Spoilage | Fulfillment | Net revenue |
|------------|----------|-------------|-------------|
| vs strong FEFO baseline | **−58.8% to −76.3%** | +0.0 to +0.9 pts | **+46% to +131%** |
| vs naive shelf-life-blind | **−70.8% to −84.0%** | +4.8 to +10.8 pts | large gain |

**Phase 1 (no clearance)** — reproduced via `--no-clearance`:
| Comparison | Spoilage | Fulfillment | Net revenue |
|------------|----------|-------------|-------------|
| vs strong FEFO baseline | +0.9% | +0.29 pts | +16,912 |
| vs naive shelf-life-blind | **−28.1%** | **+~10 pts** | large gain |

> Phase 1 was near-parity vs FEFO because much spoilage is *structurally stranded*. Phase 2's
> clearance channel converts that stranded stock into recovered revenue with no fulfillment loss.

## HTTP API (Owner B)

```
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

| Method | Path | Body / query | Returns |
|--------|------|--------------|---------|
| GET  | `/health` | — | status, version, `config_hash` (= `cost_model_hash`) |
| GET  | `/scenarios` | — | **bare array** of scenarios (id, seed, split, perturbation_profile) |
| GET  | `/inventory` | `?scenario_id=` (optional) | `{commodities, batches, destinations, ...}` |
| POST | `/plan` | `{scenario_id, include_clearance?}` | `{config_hash, now_ts, dispatches, discounts, leftover, validation, metrics}` |
| POST | `/evaluate` | `{scenario_ids:[...], baseline?}` | `{per_scenario[], aggregate, robustness?}` |
| POST | `/replan` | `{scenario_id, event:{type, payload?}}` | `{scenario_id, plan, diff[]}` (E3 event-driven) |
| POST | `/explain` | `{batch_id, destination_id}` | factor breakdown for one recommendation |
| POST | `/sensitivity` | `{scenario_id, factor?}` | one-factor net-revenue curves |

Unknown scenario ids return **404**. CORS is open (`*`) so the Vite dev server or any static
build can call it directly. The React dashboard (`apps/web`) consumes exactly these endpoints;
this service was adapted to the dashboard's frozen contract (see `docs/WORKSTREAMS.md`
§ "Frozen interfaces"). `/replan` event types: `traffic_delay` (`{hours}`),
`temp_spike` (`{rsl_penalty_days}`), `capacity_change` (`{factor}`), `new_order` (`{}`).

## Tests

```
pip install -r requirements.txt
pytest                        # 41 tests
```

Covers the cost-model loader, LP optimizer, all baseline strategies, deterministic output,
degraded/perturbed data, disruption replanning, the forecast backtest, the reproducibility
manifest, and every HTTP endpoint against the frozen contract (including the bare-array
`/scenarios`, multi-scenario `/evaluate`, event-driven `/replan`, POST `/explain`, 404s, and
`/plan` determinism).

## Reproducibility

```
python scripts/run_all.py     # regenerates every results/ artifact + manifest.json
pytest tests/test_reproducibility.py -q
```

`results/manifest.json` pins the cost-model hash, the environment and a SHA-256 per artifact;
the test fails if any result drifts. See `../../results/README.md`.

## Next
- Owner C (React/TS dashboard) is built in `apps/web` (see its README).
