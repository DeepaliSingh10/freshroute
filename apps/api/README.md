# apps/api — FastAPI service (Owner B, with Owner A's optimizer)

## Structure (target)
```
app/
  main.py            # FastAPI app + endpoints
  schemas.py         # Pydantic models (frozen contract)
  data/              # loader + synthetic generator (Owner A)
  optimizer/         # LP/MILP + baseline (Owner A)
  uncertainty/       # Monte Carlo / sensitivity (Owner A)
  eval/              # metrics + constraint checker (Owner B)
  explain/           # reason generator (B/C)
tests/               # determinism, 0-violation, degraded data, cost model
results/             # generated evaluation artifacts
```

## Run
```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

> Scaffold placeholder — implement per `docs/PLAN.md` Phase 1.
