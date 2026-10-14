"""Demand forecasting (E1): the model beats the naive baselines on holdout."""

from __future__ import annotations

from datetime import date

from app.data.cost_model import CostModel
from app.data.generator import generate_instance
from app.forecast.forecaster import backtest, fit, generate_demand_history


def test_backtest_beats_naive():
    cm = CostModel.load()
    inst = generate_instance(seed=303, cost_model=cm, split="hidden", with_clearance=True)
    history = generate_demand_history(
        seed=303, commodities=inst.commodities, destinations=inst.destinations,
        base_date=date(2026, 1, 1), days=60,
    )
    result = backtest(history, holdout_days=10)
    model_mape = result["methods"]["model"]["mape"]
    assert model_mape < result["methods"]["naive_last"]["mape"]
    assert model_mape < result["methods"]["seasonal_naive"]["mape"]


def test_fit_produces_positive_levels():
    cm = CostModel.load()
    inst = generate_instance(seed=101, cost_model=cm, split="train", with_clearance=True)
    history = generate_demand_history(
        seed=101, commodities=inst.commodities, destinations=inst.destinations,
        base_date=date(2026, 1, 1), days=30,
    )
    model = fit(history)
    assert len(model.levels) > 0
    assert all(v >= 0 for v in model.levels.values())
