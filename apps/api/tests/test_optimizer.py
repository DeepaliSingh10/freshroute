"""Optimizer guarantees: feasibility, determinism, and dominance over the baseline."""

from __future__ import annotations

import pytest

from app.data.cost_model import CostModel
from app.data.scenarios import SCENARIOS, build_instance
from app.eval.checker import check_plan
from app.eval.metrics import compute_metrics
from app.optimizer.allocator import solve_optimizer
from app.optimizer.baseline import solve_baseline

IDS = [s["id"] for s in SCENARIOS]


@pytest.fixture(scope="module")
def cm() -> CostModel:
    return CostModel.load()


@pytest.mark.parametrize("sid", IDS)
def test_optimizer_zero_hard_violations(cm, sid):
    inst = build_instance(sid, cm)
    plan = solve_optimizer(inst, cm)
    assert plan.status in ("OPTIMAL", "FEASIBLE")
    assert check_plan(inst, cm, plan) == []


@pytest.mark.parametrize("sid", IDS)
def test_optimizer_dominates_fefo(cm, sid):
    inst = build_instance(sid, cm)
    m_opt = compute_metrics(inst, cm, solve_optimizer(inst, cm))
    m_base = compute_metrics(inst, cm, solve_baseline(inst, cm, "fefo"))
    assert m_opt.spoilage_kg <= m_base.spoilage_kg + 1e-6
    assert m_opt.net_revenue >= m_base.net_revenue - 1e-6


def test_optimizer_is_deterministic(cm):
    inst = build_instance("hidden_01", cm)
    a = compute_metrics(inst, cm, solve_optimizer(inst, cm)).to_dict()
    b = compute_metrics(inst, cm, solve_optimizer(inst, cm)).to_dict()
    a.pop("runtime_ms", None)
    b.pop("runtime_ms", None)
    assert a == b
