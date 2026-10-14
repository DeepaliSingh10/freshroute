"""API smoke tests (Owner B): frozen B<->C contract + determinism."""

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
    assert len(body["config_hash"]) >= 8
    assert body["config_hash"] == body["cost_model_hash"]


def test_scenarios_is_bare_array(client):
    body = client.get("/scenarios").json()
    assert isinstance(body, list)
    ids = {s["scenario_id"] for s in body}
    assert {"train_01", "test_01", "hidden_01"} <= ids
    assert all("seed" in s and "split" in s for s in body)


def test_inventory_has_commodities_and_batches(client):
    body = client.get("/inventory", params={"scenario_id": "hidden_01"}).json()
    assert body["n_batches"] == len(body["batches"])
    assert body["total_inventory_kg"] > 0
    assert len(body["commodities"]) > 0
    c = body["commodities"][0]
    assert {"commodity_id", "name", "perishability_class", "default_shelf_life_days",
            "cost_basis_per_kg"} <= set(c)
    b = body["batches"][0]
    assert {"batch_id", "commodity_id", "quantity_kg", "remaining_shelf_life_days"} <= set(b)


def test_inventory_defaults_without_scenario(client):
    body = client.get("/inventory").json()
    assert body["n_batches"] > 0
    assert body["scenario_id"]


def test_plan_contract_and_deterministic(client):
    a = client.post("/plan", json={"scenario_id": "hidden_01"}).json()
    b = client.post("/plan", json={"scenario_id": "hidden_01"}).json()
    # frozen contract fields
    assert {"scenario_id", "config_hash", "now_ts", "dispatches", "discounts",
            "leftover", "validation", "metrics"} <= set(a)
    assert a["validation"]["violations"] == []
    assert a["validation"]["degraded"] is False
    assert a["metrics"]["net_revenue"] == b["metrics"]["net_revenue"]
    assert len(a["dispatches"]) > 0
    d = a["dispatches"][0]
    assert {"batch_id", "commodity_id", "destination_id", "quantity_kg", "price_per_kg",
            "effective_price_per_kg", "travel_time_hours", "transport_cost", "margin",
            "priority_rank", "urgency_days", "feasible", "reason"} <= set(d)
    assert all(x["reason"] for x in a["dispatches"])
    assert a["dispatches"][0]["priority_rank"] == 1  # most urgent first


def test_evaluate_multi_scenario_contract(client):
    body = client.post(
        "/evaluate", json={"scenario_ids": ["hidden_01", "test_01"], "baseline": "fefo"}
    ).json()
    assert {"per_scenario", "aggregate"} <= set(body)
    assert len(body["per_scenario"]) == 2
    ps = body["per_scenario"][0]
    assert {"scenario_id", "split", "proposed", "baseline"} <= set(ps)
    agg = body["aggregate"]
    assert {"spoilage_pct_reduction", "fulfillment_delta", "net_revenue_delta",
            "net_revenue_delta_pct", "violations_total"} <= set(agg)
    assert agg["spoilage_pct_reduction"] > 0
    assert agg["net_revenue_delta"] > 0
    assert agg["violations_total"] == 0


def test_replan_event_contract(client):
    body = client.post(
        "/replan", json={"scenario_id": "hidden_01",
                         "event": {"type": "traffic_delay", "payload": {"hours": 6}}}
    ).json()
    assert {"scenario_id", "plan", "diff"} <= set(body)
    assert isinstance(body["diff"], list)
    assert body["plan"]["validation"]["violations"] == []
    assert body["recovery"]["spoilage_pct_reduction"] > 0


def test_replan_temp_spike_and_capacity(client):
    for ev in ("temp_spike", "capacity_change", "new_order"):
        body = client.post(
            "/replan", json={"scenario_id": "hidden_01", "event": {"type": ev, "payload": {}}}
        ).json()
        assert body["plan"]["validation"]["violations"] == []
        assert body["event_type"] == ev


def test_explain_post_contract(client):
    plan = client.post("/plan", json={"scenario_id": "hidden_01"}).json()
    d = plan["dispatches"][0]
    ex = client.post(
        "/explain", json={"batch_id": d["batch_id"], "destination_id": d["destination_id"]}
    ).json()
    assert ex["batch_id"] == d["batch_id"]
    assert ex["destination_id"] == d["destination_id"]
    assert ex["recommendation"] in {"dispatch", "clearance", "hold"}
    assert len(ex["factors"]) > 0
    assert all({"factor", "value"} <= set(f) for f in ex["factors"])


def test_sensitivity(client):
    sens = client.post(
        "/sensitivity", json={"scenario_id": "hidden_01", "factor": "demand_multiplier"}
    ).json()
    assert len(sens["curves"]["demand_multiplier"]["points"]) >= 3


def test_unknown_scenario_404(client):
    assert client.get("/inventory", params={"scenario_id": "nope"}).status_code == 404
    assert client.post("/plan", json={"scenario_id": "nope"}).status_code == 404
