# FreshRoute — Architecture

## 1. Components

```
┌──────────────────────────── apps/web (React + TS + Vite) ───────────────────────────┐
│  Scenario picker │ KPI cards │ Dispatch plan table │ Discount cards │ Compare charts │
│  Sensitivity sliders │ Replan event feed │ Explainability drawer                    │
└───────────────────────────────────▲─────────────────────────────────────────────────┘
                                    │ REST/JSON (typed contracts in web/src/api/types.ts)
┌───────────────────────────────────┴────────────────────── apps/api (FastAPI) ───────┐
│  /scenarios  /inventory  /plan  /evaluate  /replan  /explain  /health               │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │
│  │ data loader  │→ │  optimizer   │→ │ evaluation      │→ │ explainability       │  │
│  │ (schemas)    │  │ (OR-Tools LP)│  │ (metrics)       │  │ (reason generator)   │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  └──────────────────────┘  │
│  scenario runner · reproducibility (seed+config hash) · results writer              │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                    data/  (generated synthetic dataset + scenarios)
```

**Stack:** Python 3.11 + FastAPI + OR-Tools (GLOP/CBC) + Pandas; React 18 + TypeScript +
Vite + Recharts. Reproducibility via fixed seeds and a config hash.

---

## 2. Domain model

| Entity | Key fields |
|--------|-----------|
| **Commodity** | `commodity_id`, `name`, `perishability_class` (leafy/berry/root/…), `default_shelf_life_days`, `cost_basis_per_kg` |
| **Batch** | `batch_id`, `commodity_id`, `quantity_kg`, `harvest_ts`, `remaining_shelf_life_days`, `origin_id`, `quality_grade` |
| **Destination** | `destination_id`, `name`, `region`, `lat`, `lon`, `delivery_window` |
| **Demand** | `destination_id`, `commodity_id`, `window`, `demand_kg`, `price_per_kg`, `min_days_fresh_on_shelf` |
| **Lane** | `lane_id`, `origin_id`, `destination_id`, `travel_time_hours`, `cost_per_kg`, `capacity_kg`, `departure_window` |
| **CostModel** | `transport_per_kg_km` (or per lane), `handling_per_kg`, `spoilage_cost_basis`, `unmet_demand_penalty`, `discount_ladder` |
| **Scenario** | `scenario_id`, `seed`, `now_ts`, `perturbations[]`, `split` (train/test/hidden) |

Full column spec: `DATA_SPEC.md`.

---

## 3. Decision variables

For each feasible (batch, destination) pair:

- `x[b,d] ≥ 0` — kg of batch `b` shipped to destination `d`
- `disc[b] ∈ [0, 0.5]` — discount applied to batch `b`'s proceeds (rule-driven or optimized)
- `leftover[b] ≥ 0` — kg of batch `b` not dispatched (may spoil → cost)

Feasible pairs are precomputed: a pair `(b,d)` is allowed only if shelf life covers travel +
handling + minimum fresh-shelf-on-arrival.

---

## 4. Optimization model (MVP)

**Objective — maximize net revenue:**

```
maximize  Σ_{b,d} x[b,d] · price[c(b),d] · (1 − disc[b])
        − Σ_{b,d} x[b,d] · transport_cost(b,d)
        − Σ_{b,d} x[b,d] · handling_per_kg(c(b))
        − Σ_b      leftover[b] · spoilage_cost_basis(c(b))
        − Σ_{c,d}  unmet[c,d] · unmet_penalty
```

**Hard constraints (feasibility — the 15-pt criterion):**

```
(1) Stock:        Σ_d x[b,d] + leftover[b] = quantity_kg[b]
(2) Demand:       Σ_b x[b,d] ≤ demand_kg[c,d]                       (never over-serve)
(3) Lane cap:     Σ_b x[b,d] ≤ capacity_kg[lane(b,d)]               (per lane/vehicle)
(4) Shelf life:    pair (b,d) only if travel_days + handling_days + min_fresh ≤ RSL[b]
(5) Windows:       x[b,d] = 0 outside departure/delivery windows
(6) Non-negativity
```

`unmet[c,d] = demand_kg[c,d] − Σ_b x[b,d]` is a reporting/soft variable (penalized, not hard,
so demand fulfillment is *maximized* rather than forcing infeasibility).

**Priority key (M3, perishability-first):** sort candidate dispatches by
`urgency = RSL_remaining_after_transit` ascending, then `margin_per_kg` descending.
This order is surfaced in the UI as the dispatch priority list even though the LP jointly
optimizes quantities.

**Solver:** OR-Tools `pywraplp.Solver` with GLOP (LP) for speed; switch to CBC (MILP) only if
we need binary lane-activation. Time limit + gap tolerance to guarantee it always returns.

---

## 5. Discount engine (M4, E2)

Rule-based, fully disclosed, and **explainable** (never a black box):

| Condition | Discount |
|-----------|----------|
| `RSL ≤ discount_ladder.t1` and expected unsold > 0 | `d1` (e.g., 15%) |
| `RSL ≤ t2` (more perishable) | `d2` (e.g., 30%) |
| Demand shortfall at destination but batch movable | prefer reallocation before discount |
| No feasible lane for a batch | discount at origin / local sale, or accept spoilage |

Discounts enter the objective so the optimizer trades margin for recovered value.
**E2** upgrades the rule to an optimization of *timing* (when to cut price as RSL shrinks)
under demand/inventory uncertainty (Monte Carlo).

Every discount output includes: `batch_id`, `rule_id`, `discount_pct`, `expected_recovered_value`,
`reason` (human string).

---

## 6. Uncertainty & robustness (E4, rubric "Robustness")

- Each stochastic input (`RSL`, `travel_time`, `demand`, `price`, lane capacity, missing demand)
  has a range; the harness samples them **jointly** per draw.
- **Monte Carlo**: `app/eval/robustness.py` draws seeded perturbation vectors and re-solves the
  optimizer **and** the FEFO baseline per draw → distribution of net revenue, spoilage,
  fulfillment. Every draw is seeded, so results are reproducible.
- Report **mean and worst-case (P10)** per scenario and overall. `scripts/run_robustness.py
  --draws 30` writes `results/robustness.json` (30 draws × 3 scenarios = 90 solves, 0 violations).
- The **same engine** backs `POST /robustness` (default 20 draws), returning a compact
  net-revenue band (P10 / mean / P90) that the dashboard renders directly — the UI never
  fabricates statistics (see §8 and `apps/web/README.md`).
- Sensitivity UI: sliders for demand/travel/price; one-factor curves from `/sensitivity`.

## 7. Replanning (E3)

`POST /replan` is **event-driven**, matching the dashboard: it accepts
`{scenario_id, event: {type, payload?}}` and returns `{scenario_id, plan, diff[]}` — the new
optimized `PlanResponse` under the disruption plus a per-shipment diff (`added` / `removed` /
`changed`) with reasons. Event types: `traffic_delay` (`{hours}`), `temp_spike`
(`{rsl_penalty_days}`), `capacity_change` (`{factor}`), `new_order` (`{}`).

Internally the event is materialized into a disrupted instance (block the largest origin's
outbound lanes + add `travel_delay_hours` via `apply_disruption`, or shrink shelf life / lane
capacity / bump demand), then the network is re-optimized under the same hard constraints. For
the recovery comparison, `replan` keeps only still-valid committed shipments (reduced stock,
demand and lane capacity) and re-optimizes the residual. The additive `recovery`,
`morning_plan`, `no_replan` and `violations_replan` fields are retained for tooling.

## 8. API surface

| Endpoint | Method | Request | Returns |
|----------|--------|---------|---------|
| `/health` | GET | — | status, version, `config_hash` (= `cost_model_hash`) |
| `/scenarios` | GET | — | **bare array** of scenarios with `split` + seed |
| `/inventory` | GET | `?scenario_id=` (optional) | commodities + batches + destinations (M1) |
| `/plan` | POST | `{scenario_id, include_clearance?}` | `{config_hash, now_ts, dispatches, discounts, leftover, validation, metrics}` (M2, M3, M4) |
| `/evaluate` | POST | `{scenario_ids:[...], baseline?}` | `{per_scenario[], aggregate, robustness?}` (M5) |
| `/robustness` | POST | `{scenario_ids?, draws?}` | E4 Monte Carlo: per-scenario + overall mean/P10/P50/P90 stats and a compact `band` for the dashboard |
| `/replan` | POST | `{scenario_id, event:{type, payload?}}` | `{scenario_id, plan, diff[]}` (E3) |
| `/explain` | POST | `{batch_id, destination_id}` | factor breakdown for one recommendation |
| `/sensitivity` | POST | `{scenario_id, factor?}` | one-factor net-revenue curves (E4) |

Unknown `scenario_id` → **404**. All responses are deterministic given `scenario_id` (seeded).
The contract types live in `apps/api/app/api/schemas.py` (server) and
`apps/web/src/api/types.ts` (client) — they are the frozen interface between B and C. The API
was adapted to the client contract the dashboard was built against (see `WORKSTREAMS.md`).

## 9. Reproducibility

- Every run writes deterministic JSON artifacts under `results/` (phase summaries, forecast,
  robustness, replan, discount policy, telemetry, sensitivity) plus `results/manifest.json`.
- `manifest.json` records the `config_hash` (SHA256 of `cost_model.yaml`) and a SHA-256 per
  artifact; `scripts/run_all.py` regenerates everything, `tests/test_reproducibility.py`
  fails on any drift.
- Tests assert: same seed+config ⇒ byte-identical results; 0 constraint violations.

## 10. Failure handling (rubric "Engineering")

- Missing samples → forward-fill with a documented rule + flag on the plan.
- Noisy readings (E5 simulated temperature) → clamped/denoised, degradation noted.
- Infeasible LP → relax with slack variables, mark `degraded=true`, explain which constraint bound.
- Unavailable data feed → return partial plan with explicit `warnings[]`, never a 500.
