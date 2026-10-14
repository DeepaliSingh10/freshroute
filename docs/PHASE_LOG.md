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

### Phase 2 · Part 2 — Extensions E1–E5 ✅ (done)
- **E1 Demand forecasting** (`app/forecast/forecaster.py`, `scripts/run_forecast.py`): transparent
  level × day-of-week × event-uplift model over a synthetic daily history. Backtest holdout:
  **MAPE 17.4%** vs naive-last 28.7% / seasonal-naive 24.7% (bias 2.0%). Predict-then-optimize
  demo shows the plan is robust to forecast error (fulfillment/net-rev within ~1%).
  → `results/forecast_summary.json`
- **E2 Optimized markdown timing/price** (`app/optimizer/discount_policy.py`,
  `scripts/run_discount_policy.py`): per at-risk batch we search (discount depth × days-to-hold)
  to maximize expected recovered value under shelf-life & demand uncertainty, with a disclosed
  price-elastic clearance response. On hidden scenario: 18 at-risk batches, 9 marked down;
  expected value **666,985** vs fixed-30% rule 466,062 (**+200,923**, ~+43%) and vs no discount
  **+149,267**. Short-life batches get deep discounts (40–50%), long-life batches sell at full price.
  → `results/discount_policy_summary.json`
- **E3 Disruption replan** (`app/optimizer/replan.py`, `scripts/run_replan.py`): keeps only
  still-valid committed shipments, then re-optimizes the residual stock (reduced stock, demand
  and lane capacity) on the disrupted network. On a hub outage + 6h delay: spoilage
  **−20.4%**, net revenue **+213,504**, **0 hard violations**. → `results/replan_summary.json`
- **E4 Monte Carlo robustness** (`scripts/run_robustness.py`): 30 draws × 3 scenarios (90 solves)
  over shelf-life/demand/travel/price/capacity perturbations. Mean spoilage reduction
  **−57.7%** (P10 −46.3%), net-revenue delta mean **+331,772** (P10 **+271,309**), fulfillment
  delta +0.20 pts, **0 violations**. → `results/robustness.json`
- **E5 Cold-chain telemetry + live price feed** (`app/data/telemetry.py`,
  `scripts/run_telemetry.py`): simulated per-batch temperature readings; degree-hours above
  threshold reduce remaining shelf life (16/46 batches hit, 10.4 batch-days lost). Ignoring
  telemetry yields **5 infeasible shipments**; a temperature-aware replan restores
  **0 violations**. A lognormal market-price walk moves net revenue 626,512 → **648,001** as the
  plan re-solves on each tick. → `results/telemetry_summary.json`

### Owner A completeness
- **Frozen baseline definition** `app/data/baseline_definition.yaml` now materializes the baseline
  (strategies `fefo` / `margin` / `nearest` / `naive`, all shelf-life-feasible except `naive`).
- Added the **nearest-first greedy** baseline strategy (`baseline.py::solve_baseline(..., "nearest")`).
- **Sensitivity engine** (`app/eval/sensitivity.py`, `scripts/run_sensitivity.py`): one-factor sweeps
  (demand, travel delay, price shock, lane capacity, shelf-life noise) → curves for the UI sliders.
  → `results/sensitivity_summary.json`. Every Owner A deliverable in `WORKSTREAMS.md` is now present.

### Owner B — FastAPI service + tests ✅ (done)
- **HTTP layer**: `app/main.py` (app factory, CORS, 404 guard) + `app/api/schemas.py`
  (Pydantic v2 contract) + `app/api/service.py` (assembles plan/evaluate/replan/explain/sensitivity).
  Endpoints: `GET /health`, `GET /scenarios`, `GET /inventory`, `POST /plan`, `POST /evaluate`,
  `POST /replan`, `GET /explain`, `POST /sensitivity`. Run: `uvicorn app.main:app --reload`.
- **Shared scenario registry** `app/data/scenarios.py` (single source for API + scripts);
  `scripts/run_phase1.py` now imports it (identical results).
- **pytest suite** `apps/api/tests/` — **38 tests, all passing**: cost model, LP optimizer,
  all four baselines, determinism, degraded/perturbed data, disruption replan, forecast backtest,
  the reproducibility manifest, and every HTTP endpoint (incl. unknown-scenario 404 and
  `/plan` determinism).
- **Reproducibility harness** `app/repro.py` + `scripts/run_all.py`: regenerates every
  `results/` artifact and writes `results/manifest.json` (cost-model hash + environment +
  SHA-256 per artifact); `tests/test_reproducibility.py` fails on drift. `results/README.md`
  documents each file. (Regeneration also fixed a stale `cost_model_hash` in `phase1_summary.json`.)
- Smoke check: `/health` hash `cef90379ab1f`; `hidden_01` = 46 batches / 25,350.9 kg;
  `/plan` OPTIMAL, 87 dispatches, 20 discounts, **0 violations**, net revenue 572,204.63.

### Owner C — React + TypeScript dashboard ✅ (done)
- Vite + React 18 + TS in `apps/web`; `npm run typecheck` and `npm run build` both clean.
- Pages/panels: scenario picker, KPI cards (spoilage / fulfillment / net revenue / recovered /
  violations), FreshRoute-vs-FEFO comparison charts, sortable dispatch table, discount cards,
  sensitivity factor chart, disruption replan panel, and a "why this plan?" explainability drawer.
- Talks to the FastAPI service (dev proxy `/api` → `:8000`); see `apps/web/README.md`.

## Integration — Owner C frontend wired to Owner B API ✅ (done)
- Merged `feature/workstream-c-frontend` into `main`, taking the teammate's authoritative
  `apps/web` dashboard (the client types in `apps/web/src/api/types.ts` are the source of truth).
- **Adapted the backend to the frontend's frozen contract**:
  `/health` exposes `config_hash`; `/scenarios` returns a bare array; `/inventory` returns
  `commodities` + `batches` (+ destinations) with `scenario_id` optional; `/plan` returns
  `{config_hash, now_ts, dispatches, discounts, leftover, validation, metrics}` with enriched
  dispatches (`commodity_id`, `effective_price_per_kg`, `travel_time_hours`, `transport_cost`,
  `margin`, `priority_rank`, `urgency_days`, `feasible`); `/evaluate` takes `{scenario_ids[]}`
  and returns `{per_scenario, aggregate, robustness?}`; `/replan` is event-driven
  (`{scenario_id, event}` → `{scenario_id, plan, diff[]}`) for `traffic_delay` / `temp_spike` /
  `capacity_change` / `new_order`; `/explain` is `POST {batch_id, destination_id}` with a
  factor/constraint breakdown.
- Updated `apps/api/tests/test_api.py` to the new contract; suite is now **41 tests, passing**.
- Verified end-to-end: `pytest` green; `npm run typecheck` + `npm run build` clean; live smoke
  against `uvicorn` returned 46 batches / 87 dispatches / 20 discounts / **0 violations** /
  net revenue 572,204.63; `/evaluate` spoilage reduction 0.67 with 0 violations; and all four
  `/replan` events produced valid plans + diffs.
- Docs reconciled to the single frozen contract: `WORKSTREAMS.md`, `ARCHITECTURE.md`,
  `README.md`, `apps/api/README.md`, `apps/web/README.md`, `docs/DEMO.md`.

## E4 robustness exposure — API + dashboard ✅ (done)
- Extracted the Monte Carlo engine into `app/eval/robustness.py` (shared by the harness and the
  API); `scripts/run_robustness.py` is now a thin CLI over it and still writes a **byte-identical**
  `results/robustness.json` (30 draws × 3 scenarios, verified against the committed artifact), so
  `tests/test_reproducibility.py` stays green.
- Added `POST /robustness` (`{scenario_ids?, draws?}`, default 20 draws, capped at 200) →
  per-scenario + overall mean/std/P10/P50/P90/min/max stats plus a compact `band`
  (P10 / mean / P90 net revenue, net-revenue delta, spoilage reduction). Suite is now
  **42 tests, passing**.
- Wired the dashboard to real statistics: `getRobustness()` client call (live-only, no demo
  fallback) feeds `UncertaintyBand` and the `CompareCharts` note with the seeded Monte-Carlo
  band; the illustrative local band remains only when the endpoint is unavailable. Copy updated
  from "illustrative" to "verified Monte-Carlo result".
- Verified live: `/robustness` for `hidden_01` at 20 draws → P10 ₹417,483 / mean ₹515,665 /
  P90 ₹597,092, net-revenue delta mean +₹317,324 (P10 +₹248,059), 0 violations;
  `npm run typecheck` + `npm run build` clean.

> Remaining after integration: demo rehearsal against the live stack.
