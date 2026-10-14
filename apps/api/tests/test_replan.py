"""Disruption replan (E3): committed shipments stay valid; replan improves on frozen."""

from __future__ import annotations

from app.data.cost_model import CostModel
from app.data.scenarios import build_instance
from app.eval.checker import check_plan
from app.eval.metrics import compute_metrics
from app.optimizer.allocator import solve_optimizer
from app.optimizer.replan import Disruption, apply_disruption, replan


def test_apply_disruption_closes_blocked_origin_lanes():
    cm = CostModel.load()
    base = build_instance("hidden_01", cm)
    origin = next(iter(base.origins))
    disrupted = apply_disruption(base, Disruption(blocked_origins=(origin,)))
    for (o, d), _lane in disrupted.lanes.items():
        if o == origin:
            assert disrupted.destinations[d].is_clearance  # only clearance may remain


def test_replan_has_no_violations_and_beats_frozen():
    cm = CostModel.load()
    base = build_instance("hidden_01", cm)
    plan0 = solve_optimizer(base, cm)

    stock = {}
    for b in base.batches.values():
        stock[b.origin_id] = stock.get(b.origin_id, 0.0) + b.quantity_kg
    blocked = max(stock, key=stock.get)

    disrupted = apply_disruption(base, Disruption(blocked_origins=(blocked,), travel_delay_hours=6.0))
    frozen, combined = replan(disrupted, plan0, cm)

    assert check_plan(disrupted, cm, combined) == []
    m_frozen = compute_metrics(disrupted, cm, frozen)
    m_replan = compute_metrics(disrupted, cm, combined)
    assert m_replan.spoilage_kg <= m_frozen.spoilage_kg + 1e-6
    assert m_replan.net_revenue >= m_frozen.net_revenue - 1e-6
