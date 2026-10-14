# apps/web — React + TypeScript + Vite dashboard (Owner C)

Decision-support dashboard for FreshRoute: pick a scenario, run the optimizer, and read the
dispatch plan, discount recommendations, KPI cards, baseline-vs-optimized charts, per-dispatch
explainability, a sensitivity panel, and a replan event feed — with loading, empty, and error
states everywhere.

## Structure

```
src/
  api/
    types.ts        # frozen API contract + additive endpoint shapes (inventory/explain/replan)
    client.ts       # fetch wrapper with live → demo fallback and strict mode
    mockData.ts     # deterministic, schema-compatible DEMO fixtures (clearly labelled)
  components/
    ScenarioSelector.tsx   # scenario picker + Optimize action + source badge
    ApiStatusBanner.tsx    # /health check → connected / unavailable banner
    KpiCards.tsx           # revenue / spoilage / fulfillment / feasibility KPI cards
    ViolationBadge.tsx     # "0 constraint violations" badge (degraded-input aware)
    DispatchTable.tsx      # sortable, filterable plan table + per-row Explain action
    DiscountSection.tsx    # discount cards with batch detail + Explain action
    CompareCharts.tsx      # baseline-vs-optimized charts (Recharts)
    ExplainDrawer.tsx      # accessible explainability drawer (dialog, Esc to close)
    SensitivityPanel.tsx   # demand / delay / price sliders + illustrative uncertainty range
    UncertaintyBand.tsx    # net-revenue range track (labelled: not a confidence interval)
    ReplanFeed.tsx         # disruption buttons → labelled plan diff (live or simulated)
    SourceBadge.tsx        # shared "Live API" / "Demo data" badge
    StateViews.tsx         # loading / empty / error views + skeleton
    Spinner.tsx
  pages/Dashboard.tsx      # orchestration + state machine
  utils/
    format.ts              # currency / number / percent formatting (en-IN, ₹)
    metrics.ts             # single source of truth for metric formulas + delta tones
    explain.ts             # builds explainability models from plan-response fields only
    simulate.ts            # disclosed local models for sensitivity + replan (illustrative)
  App.tsx  main.tsx  index.css
```

## Run

```
npm install
npm run dev        # http://localhost:5173
```

Scripts: `npm run dev`, `npm run build` (type-check + production build), `npm run preview`,
`npm run typecheck`.

## Demonstration

The dashboard is designed to run against the live backend (`apps/api`, frozen contract in
`docs/WORKSTREAMS.md`), and is also fully demonstrable **without it**: on start it checks
`/health`; if the API is not reachable it shows the orange "Live API not connected" banner and
falls back to the labelled **demo** fixtures. To see it immediately:

```
npm install
npm run dev            # then open http://localhost:5173/?demo=1
```

`?demo=1` (or `VITE_USE_DEMO=true`) forces demo mode with no network attempt. Then:
pick **`demo-hidden-stress`** → **Optimize** → inspect KPI cards and the baseline charts →
**Explain** a dispatch row or discount card → drag the **Sensitivity** sliders → fire a
**Replan** event. The full 90-second script lives in `docs/DEMO.md`.

> The backend lives in `apps/api/` and serves this exact contract. When it is running the
> dashboard shows **Live API** badges and real results; only when it is unreachable does it fall
> back to synthetic demo data (badged as such, never presented as a result).

## Checks

There is no test suite in this package; the checks are type-checking and a production build:

```
npm run typecheck      # tsc --noEmit (strict, noUnusedLocals/Parameters)
npm run build          # tsc --noEmit && vite build
```

## Data source: live API or labelled demo

`src/api/client.ts` calls the FastAPI service first (`/scenarios`, `/plan`, `/evaluate`,
`/inventory`, `/health`, and the optional `/explain`, `/replan`). If the API is unreachable it
falls back to deterministic **demo data** in `src/api/mockData.ts` that matches the documented
schemas. Demo responses always render a **"Demo data"** badge, an inline notice, and a footer
disclaimer — demo numbers are synthetic and are **not** evaluation results.

Two endpoints deliberately have **no demo fallback**:

- `/explain` — if not connected, the drawer shows only fields already present in the plan
  response and states that unexposed constraints are "enforced server-side". It never invents
  optimizer reasoning.
- `/replan` — if not connected, the event feed runs a **clearly-labelled local simulation**
  instead of pretending the optimizer produced a diff.

Environment: the repo `.gitignore` ignores `.env.*`, so there is no committed `.env.example` —
set these in your shell or Vite `.env.local`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `/api` | API base path (dev uses the Vite proxy). |
| `VITE_API_PROXY_TARGET` | `http://localhost:8000` | Dev proxy target for `/api`. |
| `VITE_USE_DEMO` | unset | `true` forces demo data (also `?demo=1` in the URL). |
| `VITE_STRICT_API` | unset | `true` surfaces live-API errors instead of falling back, for exercising the error states. |

## Scope (this phase)

Implemented: scenario selector + Optimize, KPI cards, sortable/filterable dispatch table,
discount recommendations, baseline-vs-optimized charts, per-dispatch/discount **explainability
drawer**, **sensitivity** sliders, a net-revenue **uncertainty band** backed by the live E4
Monte-Carlo endpoint (`POST /robustness`), **replan** event feed, API status banner, and
loading/empty/error states. Demo data is deterministic and labelled.

Deferred to later Workstream C phases: map view and any backend-dependent results.

## Honesty rules (enforced in code)

- Demo/illustrative values are never presented as verified results (badges + notices + footer).
- No statistical confidence intervals are fabricated. When the live E4 endpoint is available the
  band shows the **real** seeded Monte-Carlo P10–P90 (labelled as such); otherwise it falls back
  to the disclosed local model's input-bound spread, clearly marked illustrative. `robustness`
  is never fabricated in demo evaluation data.
- Optimizer reasoning is never invented; the explain drawer restates plan-response fields.
