# FreshRoute — Evaluation & Winning-the-Rubric Strategy

This is the document that maps each **judging criterion** to a concrete metric, where it's
computed, and the tactic to maximize it. Every number must be reproducible from `results/`.

---

## Rubric → Our metric → Owner

| Criterion | Weight | Our metric | Computed in | Owner |
|-----------|:------:|-----------|-------------|:-----:|
| Spoilage reduction | 20 | `spoilage_pct_reduction = 1 − spoilage_opt/spoilage_base` | eval module | A/B |
| Demand fulfillment | 15 | `fulfillment = fulfilled_kg / demand_kg` (+ unmet, balance) | eval module | B |
| Net economic outcome | 20 | `net_revenue = revenue − transport − handling − spoilage − discount_effect` | eval module | A/B |
| Allocation feasibility | 15 | hard-violation count (**must be 0**) | constraint checker | B |
| Robustness & sensitivity | 10 | metric distribution over perturbed scenarios (mean, P10) | scenario runner | A |
| Engineering & reproducibility | 10 | seed+config ⇒ identical results; tests green | reproducibility harness | B |
| Explainability & commercial | 10 | % recommendations with reason; workflow clarity | explain module + UI | C |

---

## 1. Spoilage reduction (20)

**Metric:** spoiled kg and spoiled % of inventory, proposed vs baseline.
`spoilage_pct_reduction = 1 − (spoiled_kg_opt / spoiled_kg_base)`

**How we win:**
- Perishability-first prioritization removes near-expiry stock before it dies.
- Explicit shelf-life feasibility stops us shipping produce that would expire in transit.
- Discount engine recovers value on would-be-spoiled batches via the local clearance channel
  instead of letting them rot.
- Report an absolute number: *"X% less spoiled inventory than baseline on hidden scenarios."*

## 2. Demand fulfillment (15)

**Metric:** `fulfilled_kg / total_demand_kg`; also per-commodity and per-destination balance,
and `unmet_kg`. **Clearance demand is excluded** from the denominator (it is an optional salvage
sink, not market demand), so the metric measures real service level.

**How we win:**
- Optimizer maximizes served demand subject to feasibility (penalized unmet demand).
- Show we don't just dump stock at the nearest market — report destination balance to prove
  allocation isn't lopsided.
- Prefer feasibility-respecting fulfillment; never inflate by ignoring constraints.

## 3. Net economic outcome (20)

**Metric (one shared cost model — see `DATA_SPEC.md` §2):**
```
revenue          = Σ x[b,d] · price[c,d] · grade_factor(b)         # includes clearance salvage
transport_cost   = Σ x[b,d] · cost_per_kg(lane)
handling_cost    = Σ x[b,d] · handling_per_kg(c)
spoilage_cost    = Σ leftover[b] · cost_basis_per_kg(c) · spoilage_fraction(c)
net_revenue      = revenue − transport_cost − handling_cost − spoilage_cost
```
where clearance sales (`Destination.is_clearance`) contribute to `revenue` at
`base_price × clearance.price_fraction`. The internal `unmet_demand_penalty_per_kg` is **not**
a real cost and is excluded from reported `net_revenue`.
**How we win:** the LP directly maximizes this. Report `Δnet_revenue` vs baseline in absolute
currency **and** %. Break the delta into its drivers (less spoilage, better allocation, fewer
wasted trips) so judges see *why*.

## 4. Allocation feasibility (15)

**Metric:** count of hard-constraint violations (stock, demand upper bound, lane capacity,
delivery window, shelf-life). **Target = 0**, asserted by an independent post-hoc checker.

**How we win:**
- Hard constraints modeled exactly; shelf-life feasibility precomputed per pair.
- A second checker re-validates the solver output (defense in depth) and the UI shows a green
  **"0 constraint violations"** badge — makes the 15 points visible to judges instantly.

## 5. Robustness & sensitivity (10)

**Metric:** distribution of (spoilage, fulfillment, net revenue) over N perturbed scenarios;
report **mean** and **worst-case (P10)**; show plan *stability* under input ranges.

**How we win:**
- Monte Carlo over shelf-life/travel-time/demand/price/capacity perturbations (E4) —
  `scripts/run_robustness.py` → `results/robustness.json` (30 draws × 3 scenarios, seeded).
  The same seeded engine is exposed live at `POST /robustness` and rendered as the dashboard
  uncertainty band, so the jury sees the distribution, not just a point estimate.
- Replan on disruption (E3) — `scripts/run_replan.py` → `results/replan_summary.json`: keeps
  still-valid committed shipments and re-optimizes the residual stock on the disrupted network.
- Optimized markdown (E2) — `scripts/run_discount_policy.py` → `results/discount_policy_summary.json`:
  depth × timing chosen to maximize expected recovered value under uncertainty.
- Cold-chain telemetry + price feed (E5) — `scripts/run_telemetry.py` → `results/telemetry_summary.json`:
  temperature-driven shelf-life loss (and the infeasibility of ignoring it) plus a market-price walk.
- Demand forecasting (E1) — `scripts/run_forecast.py` → `results/forecast_summary.json`:
  holdout MAPE + a predict-then-optimize robustness check.
- Sensitivity sliders in the UI: drag travel time/demand, watch the plan adapt.

## 6. Engineering & reproducibility (10)

**Metric:** `same (seed, config) ⇒ identical results`; test suite green; documented setup.

**How we win:**
- Config hash on every artifact; one-command reproduce.
- Ingestion handles missing/noisy data with documented rules and explicit `warnings[]`.
- Clean README quickstart + architecture doc for judges.

## 7. Explainability & commercial relevance (10)

**Metric:** share of dispatches/discounts with a reason string (target 100%) + a plausible
operator workflow.

**How we win:**
- Every recommendation shows: urgency, feasibility check, margin, and the chosen destination
  with the **reason** (e.g., *"Batch B12 expires in 1.2d; lane to Pune removes 0.4d transit,
  leaving 0.8d — discounted 30% to clear 400kg that would otherwise spoil"*).
- `/explain` returns a factor breakdown for any single decision.
- Commercial workflow slide: distributor ops team runs the plan each morning, receives
  discount approvals, replans on disruption.

---

## Final report format (write to `results/`)

```
results/
  phase1_summary.json         # Phase 1: baseline-vs-optimizer, no clearance channel
  phase2_summary.json         # Phase 2: with clearance channel (+ discount recommendations)
  robustness.json             # E4: mean/P10 across perturbed scenarios
  forecast_summary.json       # E1: forecast backtest (MAPE) + predict-then-optimize
  replan_summary.json         # E3: disruption replan recovery
  discount_policy_summary.json # E2: optimized markdown vs fixed 30% rule
  telemetry_summary.json      # E5: cold-chain effect + market-price feed
  figures/                    # charts used in the deck
```

**Headline table for judges:**

| Metric | Baseline | FreshRoute | Improvement |
|--------|:--------:|:----------:|:-----------:|
| Spoilage (kg / %) | | | |
| Demand fulfillment (%) | | | |
| Net revenue (₹) | | | |
| Hard-constraint violations | | **0** | ✅ |
| Robustness (P10 net rev) | | | |
| Explainability coverage | | **100%** | ✅ |

> State explicitly: *results are on hidden scenarios not used for tuning.*
