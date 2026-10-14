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

> Finalized to match the shipped implementation in `apps/api/app/api/schemas.py`
> (server) and `apps/web/src/api/types.ts` (client).

### `PlanResponse` (B ↔ C)
```ts
interface PlanResponse {
  scenario_id: string;
  status: string;            // "OPTIMAL" | "INFEASIBLE" | "DEGRADED"
  metrics: Metrics;
  dispatches: Dispatch[];
  discounts: Discount[];
  violations: number;        // independent checker output; 0 when feasible
}
interface Dispatch {
  batch_id: string; commodity_name: string; destination_id: string;
  destination_name: string; quantity_kg: number; price_per_kg: number;
  margin_per_kg: number; travel_hours: number; is_clearance: boolean;
  reason: string;
}
interface Discount {
  batch_id: string; commodity_name: string; rule_id: string;
  discount_pct: number; quantity_kg: number;
  expected_recovered_value: number; reason: string;
}
interface Metrics {
  method: string; status: string;
  spoilage_kg: number; spoilage_pct: number; expired_kg: number;
  clearance_kg: number; clearance_revenue: number;
  fulfilled_kg: number; demand_kg: number; fulfillment_pct: number;
  revenue: number; transport_cost: number; handling_cost: number;
  spoilage_cost: number; net_revenue: number; violations: number;
}
```

### `EvaluateResponse`, `ReplanResponse`, `ExplainResponse`, `SensitivityResponse` (B ↔ C)
```ts
interface EvaluateResponse {
  scenario_id: string; baseline: string;
  optimizer: Metrics; baseline_metrics: Metrics;
  compare: Record<string, number>;   // spoilage_pct_reduction, net_revenue_delta, ...
  violations_optimizer: number;
}
interface ReplanResponse {
  scenario_id: string; blocked_origins: string[]; travel_delay_hours: number;
  morning_plan: Metrics; no_replan: Metrics; replan: Metrics;
  recovery: Record<string, number>; violations_replan: number;
}
interface ExplainResponse {
  scenario_id: string;
  reasons: { kind: string; ref: string; reason: string }[];
}
interface SensitivityResponse {
  scenario_id: string;
  curves: Record<string, { label: string; range: number[]; points: SensPoint[] }>;
}
```

> C can develop against these types with a static mock; swap to the live API with one flag.

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
