# FreshRoute — Intelligent Decision Support for Perishable Produce Distribution

> PS 03 solution plan and repository for a 15-hour, 3-person build.

FreshRoute is a decision-support platform for fresh-produce distributors. It decides
**which batches to dispatch first, where to allocate them, and when to discount**, while
respecting remaining shelf life, destination demand, transport time/cost, market prices,
and capacity. Every plan is **explainable** and compared against a **documented baseline**.

## Repo contents

| File | Purpose |
|------|---------|
| `docs/PLAN.md` | 15h phased plan, 3 workstreams, MVP + extension checklist, milestones |
| `docs/ARCHITECTURE.md` | Components, data model, optimization formulation, cost model, APIs |
| `docs/DATA_SPEC.md` | Synthetic dataset schema, generator spec, baseline, scenarios |
| `docs/EVALUATION.md` | Rubric-by-rubric winning strategy and exact metrics |
| `docs/WORKSTREAMS.md` | Owner matrix, interfaces/contracts, handoff points |
| `docs/DEMO.md` | Demo script, pitch, judging-day runbook |

## TL;DR of the strategy

1. **Generate a rigorous synthetic dataset** with a documented cost model, a fixed
   train/hidden-test split, and perturbation scenarios (noise, missing data, demand spikes).
2. **Optimize allocations with an LP/MILP** (OR-Tools) that maximizes net revenue subject
   to hard feasibility constraints (stock, demand, capacity, windows, shelf-life).
3. **Beat a documented baseline** (FEFO + nearest-first greedy) on spoilage, fulfillment,
   and net revenue — reported on **held-out hidden scenarios**.
4. **Make it explainable**: every dispatch and discount carries a human-readable reason.
5. **Prove robustness** with Monte Carlo over shelf-life/travel-time/demand uncertainty and
   a live replan path.

## Current status

- **Web dashboard (`apps/web/`)** — implemented and runnable now, frontend-only. It runs on
  clearly-labelled **demo data** by default and auto-switches to live data if the API is up.
  See `apps/web/README.md`.
- **API (`apps/api/`)** — a placeholder; no endpoints are implemented yet. Because of this the
  dashboard badges every value as demo data and labels the `/explain` and `/replan` paths as
  simulated. No simulated number is presented as a verified result.

## Quickstart

```
# Web (works standalone on demo data — default when no API is running)
cd apps/web
npm install
npm run dev            # http://localhost:5173   (add ?demo=1 to force demo mode)

# API (not implemented yet — placeholder only)
cd apps/api
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Team

- **Owner A** — Data & Optimization Core
- **Owner B** — API, Evaluation & Reproducibility
- **Owner C** — Frontend, Explainability & Pitch

See `docs/WORKSTREAMS.md`.
