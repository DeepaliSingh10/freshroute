"""Baseline behaviour: feasible strategies never expire cargo; naive is shelf-life-blind."""

from __future__ import annotations

import pytest

from app.data.cost_model import CostModel
from app.data.scenarios import build_instance
from app.eval.checker import check_plan
from app.eval.metrics import compute_metrics
from app.optimizer.baseline import solve_baseline


@pytest.fixture(scope="module")
def cm() -> CostModel:
    return CostModel.load()


@pytest.mark.parametrize("strategy", ["fefo", "margin", "nearest"])
def test_feasible_baselines_have_no_violations(cm, strategy):
    inst = build_instance("hidden_01", cm)
    plan = solve_baseline(inst, cm, strategy)
    assert check_plan(inst, cm, plan) == []
    m = compute_metrics(inst, cm, plan)
    assert m.expired_kg == 0.0


def test_naive_is_shelf_life_blind(cm):
    """The naive baseline ignores feasibility and should ship some doomed cargo."""
    inst = build_instance("hidden_01", cm)
    m_naive = compute_metrics(inst, cm, solve_baseline(inst, cm, "naive"))
    m_fefo = compute_metrics(inst, cm, solve_baseline(inst, cm, "fefo"))
    assert m_naive.expired_kg >= m_fefo.expired_kg
    assert m_naive.expired_kg > 0.0
