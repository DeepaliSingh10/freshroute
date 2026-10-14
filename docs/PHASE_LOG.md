# Phase Log

## Owner A — Data & Optimization Core

### Phase 1 — Foundations ✅ (done)
**Deliverables shipped**
- `app/data/models.py` — frozen domain schema.
- `app/data/constants.py` — commodity catalog, origins/destinations, grade factors.
- `app/data/cost_model.yaml` + `cost_model.py` — single-source cost model with config hash.
- `app/data/generator.py` — deterministic synthetic generator + perturbation profiles.
- `app/optimizer/feasibility.py` — shelf-life feasibility engine (MVP M3).
- `app/optimizer/baseline.py` — `fefo` (strong), `margin`, `naive` (shelf-life-blind) baselines.
- `app/optimizer/allocator.py` — LP maximizing net revenue under hard constraints.
- `app/eval/metrics.py` — spoilage / fulfillment / net revenue / expired-on-arrival.
- `app/eval/checker.py` — independent hard-constraint checker.
- `scripts/run_phase1.py` — end-to-end CLI + `results/phase1_summary.json`.

**Verified**
- Solver status OPTIMAL, runtime ~1–2 ms on all scenarios.
- Independent checker reports **0 hard-constraint violations**.
- **Deterministic**: identical results JSON across runs (timing stripped).

**Results (mean over train/test/hidden)**
| Comparison | Spoilage | Fulfillment | Net revenue |
|------------|----------|-------------|-------------|
| vs `fefo` (strong) | +0.9% | +0.29 pts | **+16,912 (~+5%)** |
| vs `naive` (shelf-life-blind) | **−28.1%** | **+~10 pts** | large gain |

**Known limitation / hand-off to Phase 2**
- Spoilage vs the strong FEFO baseline is near-parity because FEFO is already urgency-aware and
  a large share of spoilage is *structurally stranded* stock (can't reach any destination in
  time). The spoilage lever is **clearing at-risk/stranded stock via discounts** (MVP M4) plus
  price-elastic demand — implemented in Phase 2.

## Owner A — Phase 2 (in progress)

### Phase 2 · Part 1 — Local clearance channel + discount engine (M4) ✅ (done)
The Phase 1 spoilage gain vs the strong FEFO baseline was near-parity because a large share of
spoilage is **structurally stranded** stock (no full-price destination is reachable before
expiry). Phase 2 part 1 adds a **local clearance channel** the baseline does NOT have, plus a
rule-based **discount recommendation engine**.

**What changed**
- `app/data/generator.py` — `_build_clearance_outlets()` creates one clearance destination +
  lane + commodity demand per origin (`CLR-<origin>`), sized from local supply.
  `generate_instance(..., with_clearance=True)`.
- `app/data/models.py` — `Destination.is_clearance: bool`.
- `app/data/cost_model.yaml`/`.py` — `clearance:` block + typed helpers.
- `app/optimizer/feasibility.py` — `build_feasible_pairs(..., include_clearance=True)`.
- `app/optimizer/baseline.py` — baselines run with `include_clearance=False` (no recovery
  capability); the `naive` shelf-life-blind strategy also skips clearance outlets.
- `app/optimizer/allocator.py` — clearance is an **optional salvage sink** (upper bound, not
  penalized unmet demand), so recovery never comes at the cost of market fulfillment.
- `app/optimizer/discounts.py` — NEW rule-based engine (`clearance_recovery`,
  `spoil_no_buyer`, `at_risk_monitor`) with a human-readable reason per recommendation.
- `app/eval/metrics.py` — clearance excluded from the demand/fulfillment denominator; adds
  `clearance_kg`, `clearance_revenue`; salvage revenue flows into net revenue.
- `scripts/run_phase1.py` — `--no-clearance` reproduces the Phase 1 artifact; default now writes
  `results/phase2_summary.json` and embeds discount recommendations.

**Verified**
- Solver OPTIMAL, runtime ~1–3 ms; **0 hard-constraint violations**; deterministic (identical
  JSON across runs, timing stripped).
- Phase 1 still reproduces exactly via `--no-clearance` (mean spoilage +0.9%, net +16,912 vs FEFO).

**Results (mean over train/test/hidden, with clearance)**
| Comparison | Spoilage | Fulfillment | Net revenue |
|------------|----------|-------------|-------------|
| vs `fefo` (strong) | **−65.8%** | +0.29 pts | **+311,076 (+~92%)** |
| vs `naive` (shelf-life-blind) | **−74.9%** | **+~10 pts** | large gain |

Per scenario, spoilage falls **58.8%–76.3%** vs FEFO while fulfillment stays on par
(+0.0 to +0.9 pts) — recovery is added value, not a trade against service.

### Phase 2 · Part 2 — Extensions E1 / E3 / E4 ✅ (done)
- **E1 Demand forecasting** (`app/forecast/forecaster.py`, `scripts/run_forecast.py`): transparent
  level × day-of-week × event-uplift model over a synthetic daily history. Backtest holdout:
  **MAPE 17.4%** vs naive-last 28.7% / seasonal-naive 24.7% (bias 2.0%). Predict-then-optimize
  demo shows the plan is robust to forecast error (fulfillment/net-rev within ~1%).
  → `results/forecast_summary.json`
- **E3 Disruption replan** (`app/optimizer/replan.py`, `scripts/run_replan.py`): keeps only
  still-valid committed shipments, then re-optimizes the residual stock (reduced stock, demand
  and lane capacity) on the disrupted network. On a hub outage + 6h delay: spoilage
  **−20.4%**, net revenue **+213,504**, **0 hard violations**. → `results/replan_summary.json`
- **E4 Monte Carlo robustness** (`scripts/run_robustness.py`): 30 draws × 3 scenarios (90 solves)
  over shelf-life/demand/travel/price/capacity perturbations. Mean spoilage reduction
  **−57.7%** (P10 −46.3%), net-revenue delta mean **+331,772** (P10 **+271,309**), fulfillment
  delta +0.20 pts, **0 violations**. → `results/robustness.json`

### Phase 2 — remaining
- [ ] E2 discount timing/price under uncertainty.
- [ ] E5 simulated temperature / live market-price feed.
- [ ] Owner B (API + tests) and Owner C (React dashboard) integration.

## Owner B / C
Not started in this repo yet (Owner A phases only).
