"""API smoke tests (Owner B): every endpoint responds and is deterministic."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert len(body["cost_model_hash"]) >= 8


def test_scenarios(client):
    body = client.get("/scenarios").json()
    ids = {s["scenario_id"] for s in body["scenarios"]}
    assert {"train_01", "test_01", "hidden_01"} <= ids


def test_inventory(client):
    body = client.get("/inventory", params={"scenario_id": "hidden_01"}).json()
    assert body["n_batches"] == len(body["batches"])
    assert body["total_inventory_kg"] > 0


def test_plan_zero_violations_and_deterministic(client):
    a = client.post("/plan", json={"scenario_id": "hidden_01"}).json()
    b = client.post("/plan", json={"scenario_id": "hidden_01"}).json()
    assert a["violations"] == 0
    assert a["metrics"]["net_revenue"] == b["metrics"]["net_revenue"]
    assert len(a["dispatches"]) > 0
    # every dispatch carries a human-readable reason
    assert all(d["reason"] for d in a["dispatches"])


def test_evaluate_beats_baseline(client):
    body = client.post(
        "/evaluate", json={"scenario_id": "hidden_01", "baseline": "fefo"}
    ).json()
    assert body["violations_optimizer"] == 0
    assert body["compare"]["spoilage_pct_reduction"] > 0
    assert body["compare"]["net_revenue_delta"] > 0


def test_replan(client):
    body = client.post(
        "/replan", json={"scenario_id": "hidden_01", "travel_delay_hours": 6.0}
    ).json()
    assert body["violations_replan"] == 0
    assert body["recovery"]["spoilage_pct_reduction"] > 0


def test_explain_and_sensitivity(client):
    ex = client.get("/explain", params={"scenario_id": "hidden_01"}).json()
    assert len(ex["reasons"]) > 0
    sens = client.post(
        "/sensitivity", json={"scenario_id": "hidden_01", "factor": "demand_multiplier"}
    ).json()
    assert len(sens["curves"]["demand_multiplier"]["points"]) >= 3


def test_unknown_scenario_404(client):
    assert client.get("/inventory", params={"scenario_id": "nope"}).status_code == 404
    assert client.post("/plan", json={"scenario_id": "nope"}).status_code == 404
