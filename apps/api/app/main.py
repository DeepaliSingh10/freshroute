"""FreshRoute FastAPI service (Owner B).

Run (from apps/api):
    uvicorn app.main:app --reload --port 8000

Endpoints:
    GET  /health
    GET  /scenarios
    GET  /inventory?scenario_id=...
    POST /plan        {scenario_id, include_clearance}
    POST /evaluate    {scenario_id, baseline}
    POST /replan      {scenario_id, blocked_origins, travel_delay_hours}
    GET  /explain?scenario_id=...
    POST /sensitivity {scenario_id, factor?}
"""

from __future__ import annotations

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

    def _guard(scenario_id: str) -> None:
        if service.get_spec(scenario_id) is None:
            raise HTTPException(status_code=404, detail=f"unknown scenario {scenario_id!r}")

    @app.get("/health", response_model=schemas.HealthResponse)
    def health() -> dict:
        return {
            "status": "ok",
            "version": service.VERSION,
            "cost_model_hash": service.get_cost_model().config_hash(),
        }

    @app.get("/scenarios", response_model=schemas.ScenarioList)
    def scenarios() -> dict:
        return {"scenarios": service.scenario_specs()}

    @app.get("/inventory", response_model=schemas.InventoryResponse)
    def inventory(scenario_id: str = Query(..., examples=["hidden_01"])) -> dict:
        _guard(scenario_id)
        return service.inventory_response(scenario_id)

    @app.post("/plan", response_model=schemas.PlanResponse)
    def plan(req: schemas.PlanRequest) -> dict:
        _guard(req.scenario_id)
        return service.plan_response(req.scenario_id, include_clearance=req.include_clearance)

    @app.post("/evaluate", response_model=schemas.EvaluateResponse)
    def evaluate(req: schemas.EvaluateRequest) -> dict:
        _guard(req.scenario_id)
        return service.evaluate_response(req.scenario_id, baseline=req.baseline)

    @app.post("/replan", response_model=schemas.ReplanResponse)
    def replan_ep(req: schemas.ReplanRequest) -> dict:
        _guard(req.scenario_id)
        return service.replan_response(
            req.scenario_id, req.blocked_origins, req.travel_delay_hours
        )

    @app.get("/explain", response_model=schemas.ExplainResponse)
    def explain(scenario_id: str = Query(..., examples=["hidden_01"])) -> dict:
        _guard(scenario_id)
        return service.explain_response(scenario_id)

    @app.post("/sensitivity", response_model=schemas.SensitivityResponse)
    def sensitivity_ep(req: schemas.SensitivityRequest) -> dict:
        _guard(req.scenario_id)
        return service.sensitivity_response(req.scenario_id, factor=req.factor)

    return app


app = create_app()
