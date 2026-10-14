# apps/api — FreshRoute backend

Python 3.11+ · OR-Tools (GLOP) · numpy/pandas. Owner A (data + optimizer) Phases 1 and 2
(part 1) are **done**.

## Layout
```
app/
  data/
    models.py         # domain model (frozen schema — docs/DATA_SPEC.md)
    constants.py      # commodity catalog, locations, grade factors
    cost_model.yaml   # single source of truth for the economic cost model
    cost_model.py     # loader (config hash for reproducibility)
    generator.py      # deterministic synthetic generator + clearance outlets + perturbations
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
scripts/
  run_phase1.py       # generate -> baseline -> optimize -> evaluate -> discounts
  run_forecast.py     # E1: forecast backtest + predict-then-optimize
  run_robustness.py   # E4: Monte Carlo robustness (mean/P10)
  run_replan.py       # E3: disruption replan demo
  run_discount_policy.py # E2: optimized markdown vs fixed rule
  run_telemetry.py    # E5: cold-chain telemetry + market-price feed
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

## Next
- Owner B (FastAPI service + tests) and Owner C (React/TS dashboard).
