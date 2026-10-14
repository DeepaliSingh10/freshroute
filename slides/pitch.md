# FreshRoute — Pitch Deck

> 7 slides. Speaker notes in blockquotes. Numbers from the demo fixture are labelled as such;
> replace with `results/hidden_summary.md` values once the backend evaluation (Workstream B) lands.

---

## Slide 1 — The problem

**A third of fresh produce is lost between farm and market** — a shared global estimate, and the
post-harvest loss that MFPI-style cold-chain and food-processing programmes are built to attack.

- Perishables decay on a clock; today's routing ignores it.
- Distributors decide by habit: nearest first, or first-expiry-first-out with no re-planning.
- Loss shows up twice: spoiled stock **and** unmet demand at the same time.

> "Post-harvest loss is not a storage problem alone — it is a *decision* problem, made every
> morning, across every batch and every lane."

---

## Slide 2 — What FreshRoute decides

**Dispatch-where-discount: one decision per batch, every day.**

- **Ship** a batch to a destination, or
- **Discount** it to recover value before it spoils.
- Subject to shelf life, demand, transport and capacity — simultaneously.

Why existing tools fall short: ERPs track inventory; route optimizers ignore spoilage; neither
prices the cost of a decision made an hour too late.

---

## Slide 3 — Architecture

```
scenarios ──▶ API (FastAPI) ──▶ optimizer ──▶ plan + metrics
                   │                                 │
                   ▼                                 ▼
              inventory                         dashboard
            (commodities,                    (KPIs, plan, charts,
             batches)                         explain, what-if)
```

- **B (API):** `/scenarios`, `/plan`, `/evaluate`, `/inventory`, optional `/explain`, `/replan`.
- **C (frontend):** this dashboard — React + TypeScript, contract-frozen against B.
- Shared contracts in `apps/web/src/api/types.ts` mirror `docs/ARCHITECTURE.md § 8`.

> Current build state: the API endpoints are not implemented yet, so the dashboard runs on
> deterministic, clearly-labelled demo data in `apps/web/src/api/mockData.ts`.

---

## Slide 4 — The optimization (one formula)

**Maximize net revenue subject to hard freshness constraints.**

```
maximize   Σ  x(b,d) · price(b) · (1 − discount(b))
           −  transport(b,d) − handling(b) − spoilage(b)

subject to  arrival(b,d) ≥ min_fresh_on_shelf(b)      # shelf life
            Σ_d x(b,d) ≤ stock(b)                     # stock availability
            Σ_b x(b,d) ≤ demand(d)                    # demand upper bound
            Σ_b x(b,d) ≤ lane_capacity(d)             # vehicle / lane capacity
            departure / delivery windows respected     # timing windows
```

- Feasibility is checked **before** dispatch; infeasible batches fall to discount / leftover.
- Discounts are rule-based (thresholds t1 / t2) and disclosed in the plan response.

---

## Slide 5 — Results vs baseline

**Same cost model, both sides — FEFO + nearest-first greedy vs FreshRoute.**

| Metric | Baseline | FreshRoute | Delta |
|--------|---------:|-----------:|------:|
| Spoilage | — | ↓ | [[from eval]] |
| Demand fulfillment | — | ↑ | [[from eval]] |
| Net revenue | — | ↑ | [[from eval]] |
| Constraint violations | — | — | 0 |

> Fill the blanks from `results/hidden_summary.md` on judging day. Until the backend evaluation
> runs, the in-app numbers are **demo fixtures** and must be presented as such — the dashboard
> badges them "Demo data" and omits any confidence-interval-like statistics.

---

## Slide 6 — Robustness, uncertainty & replanning

- **Sensitivity:** move demand / travel time / price and watch the plan respond (disclosed
  local model, labelled "Simulated" — illustrative range, not a statistical CI).
- **Uncertainty:** spoilage and net revenue shown as ranges as inputs move to their bounds.
- **Replanning (E3):** fire a disruption (traffic delay, temp spike, capacity change) → a plan
  diff with per-batch reasons, so the operator sees *what changed and why*.

> Design principle: never fabricate optimizer reasoning. Where the backend does not expose a
> factor, the UI says "enforced server-side" rather than inventing it.

---

## Slide 7 — Commercial model & workflow

**Who pays, and for what.**

- **SaaS subscription** for distributors, cold-storage operators and 3PLs — priced per lane or
  per tonne planned.
- **Value story:** points of spoilage removed × cost basis + recovered value on discounts.
- **Workflow:** morning plan → operator inspects & explains → fires disruptions → ships.

> Close: "Ship where it survives, discount where it won't — and show your work."
