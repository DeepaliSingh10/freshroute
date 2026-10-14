"""FreshRoute FastAPI service (Owner B).

Run (from apps/api):
    uvicorn app.main:app --reload --port 8000

Endpoints (frozen B<->C contract; see docs/WORKSTREAMS.md):
    GET  /health                                -> {status, version, config_hash}
    GET  /scenarios                             -> [ {scenario_id, seed, split, ...} ]
    GET  /inventory?scenario_id=...             -> {commodities, batches, ...}
    POST /plan        {scenario_id}             -> PlanResponse
    POST /evaluate    {scenario_ids:[...]}      -> {per_scenario, aggregate, robustness?}
    POST /replan      {scenario_id, event}      -> {scenario_id, plan, diff}
    POST /explain     {batch_id, destination_id}-> ExplainResponse
    POST /sensitivity {scenario_id, factor?}    -> {scenario_id, curves}  (additive tooling)
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .api import schemas, service


def create_app() -> FastAPI:
    app = FastAPI(title="FreshRoute API", version=service.VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _guard(scenario_id: Optional[str]) -> None:
        if scenario_id is not None and service.get_spec(scenario_id) is None:
            raise HTTPException(status_code=404, detail=f"unknown scenario {scenario_id!r}")

    @app.get("/health", response_model=schemas.HealthResponse)
    def health() -> dict:
        h = service.get_cost_model().config_hash()
        return {"status": "ok", "version": service.VERSION, "config_hash": h, "cost_model_hash": h}

    @app.get("/scenarios", response_model=List[schemas.ScenarioInfo])
    def scenarios() -> list:
        return service.scenario_specs()

    @app.get("/inventory", response_model=schemas.InventoryResponse)
    def inventory(scenario_id: Optional[str] = Query(None, examples=["hidden_01"])) -> dict:
        sid = scenario_id or service.default_scenario_id()
        _guard(sid)
        return service.inventory_response(sid)

    @app.post("/plan", response_model=schemas.PlanResponse)
    def plan(req: schemas.PlanRequest) -> dict:
        _guard(req.scenario_id)
        return service.plan_response(req.scenario_id, include_clearance=req.include_clearance)

    @app.post("/evaluate", response_model=schemas.EvaluateResponse)
    def evaluate(req: schemas.EvaluateRequest) -> dict:
        ids = list(req.scenario_ids or [])
        if req.scenario_id:
            ids.append(req.scenario_id)
        for sid in ids:
            _guard(sid)
        return service.evaluate_response(ids, baseline=req.baseline)

    @app.post("/replan", response_model=schemas.ReplanResponse)
    def replan_ep(req: schemas.ReplanRequest) -> dict:
        _guard(req.scenario_id)
        event = req.event
        return service.replan_response(
            req.scenario_id,
            event_type=(event.type if event else ""),
            payload=(event.payload if event else None),
            blocked_origins=req.blocked_origins,
            travel_delay_hours=req.travel_delay_hours,
        )

    @app.post("/explain", response_model=schemas.ExplainResponse)
    def explain(req: schemas.ExplainRequest) -> dict:
        return service.explain_response(req.batch_id, req.destination_id)

    @app.post("/sensitivity", response_model=schemas.SensitivityResponse)
    def sensitivity_ep(req: schemas.SensitivityRequest) -> dict:
        _guard(req.scenario_id)
        return service.sensitivity_response(req.scenario_id, factor=req.factor)

    return app


app = create_app()
