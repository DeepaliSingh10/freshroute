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

- Each stochastic input (`RSL`, `travel_time`, `demand`, `price`) gets a **range** (low/point/high).
- **Monte Carlo**: sample `N=200` scenarios → distribution of net revenue, spoilage, fulfillment.
- Report **mean and worst-case (P10)**; optionally optimize a **risk-adjusted** objective
  (mean − λ·downside) to avoid plans that look good only on average.
- Sensitivity UI: sliders for the ranges; the plan recomputes and shows impact.

## 7. Replanning (E3)

`POST /replan` accepts an event — `{type: traffic_delay|capacity_change|new_order|temp_spike,
payload}` — and returns a **new plan + diff** (added/removed/changed dispatches) with a reason
per change. Internally: mutate scenario, re-solve, emit `PlanDiff`.

## 8. API surface

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/health` | GET | status, version, config hash |
| `/scenarios` | GET | list of scenarios with `split` |
| `/inventory` | GET | batches + commodities (M1) |
| `/plan` | POST `{scenario_id}` | dispatch plan + discounts + reasons (M2, M3, M4) |
| `/evaluate` | POST `{scenario_ids[]}` | proposed vs baseline metrics (M5) |
| `/replan` | POST `{scenario_id, event}` | new plan + diff (E3) |
| `/explain` | POST `{batch_id, destination_id}` | factor breakdown for one recommendation |

All responses are deterministic given `scenario_id` (seeded). Contract types live in
`apps/web/src/api/types.ts` and are the frozen interface between B and C.

## 9. Reproducibility

- Every run writes `results/<scenario>__<config_hash>.json` (metrics + plan + baseline).
- `config_hash` = SHA256 of the cost model + solver config + seed.
- Tests assert: same seed+config ⇒ byte-identical results; 0 constraint violations.

## 10. Failure handling (rubric "Engineering")

- Missing samples → forward-fill with a documented rule + flag on the plan.
- Noisy readings (E5 simulated temperature) → clamped/denoised, degradation noted.
- Infeasible LP → relax with slack variables, mark `degraded=true`, explain which constraint bound.
- Unavailable data feed → return partial plan with explicit `warnings[]`, never a 500.
