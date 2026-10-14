# FreshRoute — Intelligent Decision Support for Perishable Produce Distribution

> PS 03 solution for a 15-hour, 3-person build. All three workstreams are **implemented and
> integrated**: the optimizer + API (`apps/api`) now serves the live React dashboard
> (`apps/web`) over the frozen contract in `docs/WORKSTREAMS.md`.

FreshRoute is a decision-support platform for fresh-produce distributors. It decides
**which batches to dispatch first, where to allocate them, and when to discount**, while
respecting remaining shelf life, destination demand, transport time/cost, market prices,
and capacity. Every plan is **explainable** and compared against a **documented baseline**.

## Repo contents

| Path | Purpose |
|------|---------|
| `apps/api/` | Python backend: synthetic data generator, LP optimizer, baselines, evaluator, FastAPI service + pytest suite + reproducibility harness |
| `apps/web/` | React + TypeScript + Vite dashboard (Owner C) — consumes the live API, with labelled demo fallback |
| `results/` | Deterministic, hash-pinned evaluation artifacts + `manifest.json` |
| `docs/PLAN.md` | 15h phased plan, 3 workstreams, MVP + extension checklist, milestones |
| `docs/ARCHITECTURE.md` | Components, data model, optimization formulation, cost model, APIs |
| `docs/DATA_SPEC.md` | Synthetic dataset schema, generator spec, baseline, scenarios |
| `docs/EVALUATION.md` | Rubric-by-rubric winning strategy and exact metrics |
| `docs/WORKSTREAMS.md` | Owner matrix, **frozen interfaces/contract**, handoff points |
| `docs/DEMO.md` | Demo script, pitch, judging-day runbook, verified numbers |
| `docs/PHASE_LOG.md` | Build log across the three phases |

## TL;DR of the strategy

1. **Rigorous synthetic dataset** with a documented cost model, a fixed train/hidden-test split,
   and perturbation scenarios (noise, missing data, demand spikes).
2. **LP/MILP optimizer** (OR-Tools) maximizing net revenue subject to hard feasibility
   constraints (stock, demand, capacity, windows, shelf-life), plus a local **clearance channel**
   that rescues at-risk stock instead of spoiling it.
3. **Beat a documented baseline** (FEFO + nearest-first greedy) on spoilage, fulfillment, and
   net revenue — reported on **held-out hidden scenarios**.
4. **Explainable**: every dispatch and discount carries a human-readable reason; the API exposes
   a factor breakdown via `/explain`.
5. **Robust**: Monte Carlo over shelf-life/travel-time/demand uncertainty, an E2 markdown policy,
   an E5 cold-chain/price-feed layer, and a live event-driven replan path (`/replan`).

## Current status

- **API (`apps/api/`)** — complete. FastAPI service exposing `/health`, `/scenarios`,
  `/inventory`, `/plan`, `/evaluate`, `/robustness`, `/replan`, `/explain`, `/sensitivity`;
  42 passing tests; deterministic results under `results/`.
- **Dashboard (`apps/web/`)** — complete. Scenario picker, KPI cards, dispatch table, discount
  cards, baseline-vs-optimized charts, explainability drawer, sensitivity panel, replan feed.
  It calls the live API and falls back to clearly-labelled **demo** data only when the API is
  unreachable (it never presents a demo number as a result).

## Quickstart

Terminal 1 — API:
```
cd apps/api
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Terminal 2 — dashboard:
```
cd apps/web
npm install
npm run dev            # http://localhost:5173   (add ?demo=1 to force demo mode)
```
The dashboard proxies `/api` to `http://localhost:8000` in dev (override with
`VITE_API_PROXY_TARGET`).

Reproduce every result artifact and run the tests:
```
cd apps/api
python scripts/run_all.py     # regenerates results/ + results/manifest.json
pytest                        # 41 tests
```

## Team

- **Owner A** — Data & Optimization Core
- **Owner B** — API, Evaluation & Reproducibility
- **Owner C** — Frontend, Explainability & Pitch

See `docs/WORKSTREAMS.md`.
