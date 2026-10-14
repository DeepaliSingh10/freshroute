"""Reproducibility: same (seed, config) => identical instances and results."""

from __future__ import annotations

from app.data.cost_model import CostModel
from app.data.generator import generate_instance
from app.eval.metrics import compute_metrics
from app.optimizer.allocator import solve_optimizer
from app.optimizer.baseline import solve_baseline


def _metrics(inst, cm):
    d = compute_metrics(inst, cm, solve_optimizer(inst, cm)).to_dict()
    d.pop("runtime_ms", None)
    return d


def test_same_seed_same_instance_and_metrics():
    cm = CostModel.load()
    a = generate_instance(seed=303, cost_model=cm, split="hidden", with_clearance=True)
    b = generate_instance(seed=303, cost_model=cm, split="hidden", with_clearance=True)
    assert len(a.batches) == len(b.batches)
    assert sum(x.quantity_kg for x in a.batches.values()) == sum(
        x.quantity_kg for x in b.batches.values()
    )
    assert _metrics(a, cm) == _metrics(b, cm)


def test_different_seed_changes_instance():
    cm = CostModel.load()
    a = generate_instance(seed=303, cost_model=cm, split="hidden", with_clearance=True)
    b = generate_instance(seed=999, cost_model=cm, split="hidden", with_clearance=True)
    assert sum(x.quantity_kg for x in a.batches.values()) != sum(
        x.quantity_kg for x in b.batches.values()
    )


def test_baseline_deterministic():
    cm = CostModel.load()
    inst = generate_instance(seed=101, cost_model=cm, split="train", with_clearance=False)
    p1 = compute_metrics(inst, cm, solve_baseline(inst, cm, "fefo")).to_dict()
    p2 = compute_metrics(inst, cm, solve_baseline(inst, cm, "fefo")).to_dict()
    p1.pop("runtime_ms", None)
    p2.pop("runtime_ms", None)
    assert p1 == p2
