"""Degraded/noisy data handling: perturbations and telemetry do not break the pipeline."""

from __future__ import annotations

from app.data.cost_model import CostModel
from app.data.generator import apply_perturbations, generate_instance
from app.data.telemetry import apply_temperature_effect, simulate_temperatures
from app.eval.checker import check_plan
from app.eval.metrics import compute_metrics
from app.optimizer.allocator import solve_optimizer


def test_missing_demand_drops_rows():
    cm = CostModel.load()
    base = generate_instance(seed=303, cost_model=cm, split="hidden", with_clearance=True)
    degraded = apply_perturbations(base, {"missing_demand_pct": 0.25}, seed=1)
    assert len(degraded.demands) < len(base.demands)


def test_lane_capacity_perturbation_reduces_capacity():
    cm = CostModel.load()
    base = generate_instance(seed=303, cost_model=cm, split="hidden", with_clearance=True)
    degraded = apply_perturbations(base, {"lane_capacity_multiplier": 0.5}, seed=1)
    assert sum(l.capacity_kg for l in degraded.lanes.values()) < sum(
        l.capacity_kg for l in base.lanes.values()
    )


def test_solver_survives_noisy_instance():
    cm = CostModel.load()
    base = generate_instance(seed=202, cost_model=cm, split="test", with_clearance=True)
    noisy = apply_perturbations(
        base,
        {"rsl_noise_pct": 0.2, "demand_multiplier": 1.3, "travel_delay_hours": 5.0},
        seed=7,
    )
    plan = solve_optimizer(noisy, cm)
    assert plan.status in ("OPTIMAL", "FEASIBLE")
    assert check_plan(noisy, cm, plan) == []


def test_temperature_excursion_reduces_shelf_life_and_stays_feasible():
    cm = CostModel.load()
    base = generate_instance(seed=303, cost_model=cm, split="hidden", with_clearance=True)
    telem = simulate_temperatures(base, cm, seed=1)
    assert len(telem.readings) > 0
    degraded = apply_temperature_effect(base, telem, cm)
    # every batch's shelf life is non-increasing after cold-chain exposure
    for bid, b in base.batches.items():
        assert degraded.batches[bid].remaining_shelf_life_days <= b.remaining_shelf_life_days + 1e-9
    plan = solve_optimizer(degraded, cm)
    assert check_plan(degraded, cm, plan) == []
    assert compute_metrics(degraded, cm, plan).status in ("OPTIMAL", "FEASIBLE")
