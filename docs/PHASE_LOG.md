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

## Owner A — Phase 2 (next)
- [ ] Discount engine (M4) + at-risk clearance outlet → attack the stranded-stock spoilage.
- [ ] Demand forecasting (E1) feeding the allocator.
- [ ] Uncertainty ranges + Monte Carlo robustness (E4).
- [ ] Replan path on disruption (E3).

## Owner B / C
Not started in this repo yet (Phase 1 was Owner A only).
