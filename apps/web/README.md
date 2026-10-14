# apps/web — React + TypeScript + Vite dashboard (Owner C)

Single-page decision-support dashboard for the FreshRoute optimizer. It talks to the
FastAPI service in `apps/api` and renders the allocation plan, the baseline comparison,
discount recommendations, sensitivity curves, disruption replanning and the
explainability feed.

## Structure
```
src/
  api.ts              # typed fetch wrapper (GET/POST) against the API
  types.ts            # response types mirroring apps/api/app/api/schemas.py
  App.tsx             # scenario picker + orchestration
  main.tsx            # React entrypoint
  styles.css          # dark dashboard theme
  components/
    KpiCards.tsx        # spoilage / fulfillment / net revenue / recovered / violations
    DispatchTable.tsx   # sortable allocation table (clearance toggle, reason tooltips)
    DiscountCards.tsx   # M4 discount recommendations with plain-language reasons
    ComparisonChart.tsx # FreshRoute vs FEFO spoilage + net revenue (Recharts)
    SensitivitySliders.tsx # factor picker + net-revenue curves (E4)
    ReplanPanel.tsx     # simulate disruption and compare do-nothing vs replan (E3)
    ExplainDrawer.tsx   # "why this plan?" side drawer (~100% reason coverage)
```

## Run

Start the API first (from `apps/api`):
```
uvicorn app.main:app --reload --port 8000
```

Then the dashboard:
```
npm install
npm run dev          # http://localhost:5173, proxies /api -> :8000
```

Other scripts: `npm run typecheck`, `npm run build` (emits `dist/`, git-ignored).

## Configuration

The client reads `VITE_API_BASE` (default `/api`, which the Vite dev proxy rewrites to
`http://localhost:8000`). For a production build served from a different origin, set
`VITE_API_BASE=https://<api-host>` before `npm run build`.
