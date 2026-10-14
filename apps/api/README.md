# apps/api — FreshRoute backend

Python 3.11+ · OR-Tools (GLOP) · numpy/pandas. Owner A (data + optimizer) Phase 1 is **done**.

## Layout
```
app/
  data/
    models.py         # domain model (frozen schema — docs/DATA_SPEC.md)
    constants.py      # commodity catalog, locations, grade factors
    cost_model.yaml   # single source of truth for the economic cost model
    cost_model.py     # loader (config hash for reproducibility)
    generator.py      # deterministic synthetic generator + perturbation profiles
  optimizer/
    feasibility.py    # shelf-life feasibility precompute (shared)
    baseline.py       # baseline strategies (fefo / margin / naive)
    allocator.py      # LP: maximize net revenue subject to hard constraints
    types.py          # Plan / Dispatch
  eval/
    metrics.py        # spoilage / fulfillment / net revenue / expired-on-arrival
    checker.py        # INDEPENDENT hard-constraint checker (0 violations)
scripts/
  run_phase1.py       # generate -> baseline -> optimize -> evaluate
```

## Setup
```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
```

## Run (Owner A Phase 1)
```
python scripts/run_phase1.py --write-csv --write-results
```
- `--write-csv` materializes the generated dataset to `../../data/generated/`.
- `--write-results` writes `../../results/phase1_summary.json` (timing stripped → deterministic).

## What Phase 1 delivers
- Deterministic synthetic dataset (batches, demand, lanes, cost model) with train/test/hidden scenarios.
- Shelf-life feasibility engine (MVP M3).
- LP allocator maximizing net revenue under hard constraints: stock, demand cap, lane capacity, shelf-life.
- Two baselines: **FEFO** (strong, urgency-aware) and **naive** (price-first, shelf-life-blind).
- Independent feasibility checker proving **0 hard violations**.
- Metric module: spoilage, fulfillment, net revenue, expired-on-arrival.

## Phase 1 results (see ../../results/phase1_summary.json)
| Comparison | Spoilage | Fulfillment | Net revenue |
|------------|----------|-------------|-------------|
| vs strong FEFO baseline | ≈ parity (+0–3%) | +0–1 pt | **+2.6% to +6.9%** |
| vs naive shelf-life-blind | **−22% to −32%** | **+9 to +11 pts** | large gain |

> The modest spoilage gain vs FEFO is expected: FEFO is already urgency-aware. The big
> spoilage lever — clearing at-risk / stranded stock — lands in **Phase 2** (discount engine
> + at-risk clearance), which is MVP item M4.

## Next (Owner A Phase 2)
Discount engine (M4), demand forecasting (E1), uncertainty/Monte Carlo (E4), replan path (E3).
