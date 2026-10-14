# apps/web — React + TypeScript + Vite dashboard (Owner C)

## Structure (target)
```
src/
  api/types.ts        # frozen API contract (PlanResponse, EvalResponse, ...)
  api/client.ts       # fetch wrapper, mock toggle
  components/         # KpiCards, DispatchTable, DiscountCard, CompareChart,
                      # SensitivityPanel, ReplanFeed, ExplainDrawer, ViolationBadge
  pages/Dashboard.tsx
  App.tsx  main.tsx
```

## Run
```
npm install
npm run dev
```

> Scaffold placeholder — implement per `docs/PLAN.md` Phase 1.
