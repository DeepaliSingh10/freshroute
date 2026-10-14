# FreshRoute — Workstreams, Owners & Interfaces

Three parallel workstreams. The **interfaces are frozen at hour 0:45** so everyone can build
against them without blocking. If an interface must change, it changes **once, by consensus,
and is announced in the team chat immediately.**

---

## Owner A — Data & Optimization Core

**Owns:** `data/`, `apps/api/app/data/`, `apps/api/app/optimizer/`, `apps/api/app/uncertainty/`

Deliverables:
- Synthetic data generator (deterministic by seed) + cost model + baseline definition.
- Baseline strategy (FEFO + nearest-first greedy).
- LP/MILP optimizer (OR-Tools) with hard constraints + net-revenue objective.
- Perishability priority key and discount engine.
- Demand forecast (E1), uncertainty/Monte Carlo (E4), replan solver path (E3).
- Sensitivity engine feeding the UI.

**Critical path.** If A slips, B and C mock A's JSON and keep moving.

## Owner B — API, Evaluation & Reproducibility

**Owns:** `apps/api/app/main.py`, `apps/api/app/eval/`, `apps/api/tests/`, `results/`

Deliverables:
- FastAPI service + Pydantic schemas matching `DATA_SPEC.md`.
- Endpoints: `/health /scenarios /inventory /plan /evaluate /replan /explain`.
- Independent hard-constraint checker (defense in depth).
- Metric computation (spoilage, fulfillment, net revenue, feasibility).
- Scenario runner + reproducibility harness (seed + config hash) + results writer.
- Tests: determinism, 0-violation, degraded-data handling, cost-model correctness.

## Owner C — Frontend, Explainability & Pitch

**Owns:** `apps/web/`, `docs/DEMO.md`, `slides/`

Deliverables:
- React+TS dashboard: scenario picker, KPI cards, dispatch plan table, discount cards,
  baseline-vs-proposed charts, sensitivity sliders, replan event feed, explainability drawer.
- The **"0 constraint violations"** badge and the reason strings surfacing.
- Pitch deck + 90s recorded backup demo + live demo script.

---

## Frozen interfaces (contract)

> Single source of truth, mirrored byte-for-byte by the server models
> (`apps/api/app/api/schemas.py`) and the client types (`apps/web/src/api/types.ts`).
> The React dashboard was built against this contract **first**; the API was adapted to it.
> Additive convenience fields exist on the server but are ignored by the client (TS ignores
> unknown fields), so both stay compatible.

### `PlanResponse` (B ↔ C)
```ts
interface PlanResponse {
  scenario_id: string;
  config_hash: string;       // cost-model hash for reproducibility
  now_ts: string;
  dispatches: Dispatch[];
  discounts: Discount[];
  leftover: Leftover[];
  validation: Validation;    // independent checker output
  metrics: Metrics;
}
interface Dispatch {
  batch_id: string; commodity_id: string; destination_id: string;
  quantity_kg: number; price_per_kg: number; effective_price_per_kg: number;
  travel_time_hours: number; transport_cost: number; margin: number;
  priority_rank: number; urgency_days: number; feasible: boolean; reason: string;
}
interface Discount {
  batch_id: string; rule_id: string; discount_pct: number;
  expected_recovered_value: number; reason: string;
}
interface Leftover { batch_id: string; quantity_kg: number; spoilage_cost: number; }
interface Validation { violations: string[]; degraded: boolean; warnings: string[]; }
interface Metrics {
  spoilage_kg: number; spoilage_pct: number; fulfilled_kg: number; fulfillment_pct: number;
  unmet_kg: number; revenue: number; transport_cost: number; handling_cost: number;
  spoilage_cost: number; net_revenue: number;
}
```

### `EvaluateResponse`, `ReplanResponse`, `ExplainResponse`, `SensitivityResponse` (B ↔ C)
```ts
interface EvaluateResponse {
  per_scenario: { scenario_id: string; split: string; proposed: Metrics; baseline: Metrics }[];
  aggregate: {
    spoilage_pct_reduction: number; fulfillment_delta: number;
    net_revenue_delta: number; net_revenue_delta_pct: number; violations_total: number;
  };
  robustness?: { net_revenue_mean: number; net_revenue_p10: number };
}
interface ReplanResponse {
  scenario_id: string; plan: PlanResponse;
  diff: { batch_id: string; destination_id?: string; change: 'added'|'removed'|'changed'; reason: string }[];
}
interface ExplainResponse {
  batch_id: string; destination_id: string; recommendation: string; reason: string;
  urgency_days?: number;
  factors: { factor: string; value: string | number; contribution?: number; note?: string }[];
  constraints?: { name: string; satisfied: boolean; detail?: string }[];
}
interface SensitivityResponse {
  scenario_id: string;
  curves: Record<string, { label: string; range: number[]; points: SensPoint[] }>;
}
```

### Other endpoints
```ts
GET  /health     -> { status, version, config_hash }         // client reads config_hash
GET  /scenarios  -> Scenario[]                               // bare array
GET  /inventory  -> { commodities: Commodity[], batches: Batch[] }
POST /replan      body { scenario_id, event: { type, payload? } }   // event-driven (E3)
POST /explain     body { batch_id, destination_id }                 // factor breakdown
```
`/replan` event types: `traffic_delay` (`{hours}`), `temp_spike` (`{rsl_penalty_days}`),
`capacity_change` (`{factor}`), `new_order` (`{}`).

> C develops against these types with a static mock; swap to the live API with one flag
> (`VITE_USE_DEMO` / `?demo=1`). `/plan`, `/evaluate`, `/scenarios`, `/inventory`, `/health`
> have demo fallbacks; `/explain` and `/replan` deliberately do not — the UI labels local
> simulations instead of inventing optimizer output.

---

## Handoff checkpoints

| Hour | Handoff | Gate |
|:----:|---------|------|
| 0:45 | A publishes `DATA_SPEC.md` schema + cost model | all 3 agree |
| 3:00 | A optimizer v1 + B metric module | feasible plan exists |
| 5:00 | A baseline + B `/plan` + C table | end-to-end delta visible |
| 8:00 | MVP complete + ≥2 extensions | checklist §5 green |
| 11:00 | Feature freeze | only hardening after |
| 12:30 | B freezes `results/` | hidden eval done |
| 13:30 | All | demo rehearsed twice |
| 14:30 | All | submitted |

## Communication rules

- 3-minute sync every 90 min; one shared chat channel.
- Any red blocker called out immediately; owner re-plans around it.
- **No merging to `main` without the interface still compiling.**
- Commit small and often: `feat(optimizer): shelf-life feasibility`, `feat(web): kpi cards`.
