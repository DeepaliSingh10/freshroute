"""Named scenarios shared by the runners and the API.

A scenario = (seed, split, perturbation profile). The base instance is generated from the
seed; the perturbation profile is applied on top (`generator.apply_perturbations`).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .cost_model import CostModel
from .generator import apply_perturbations, generate_instance
from .models import Instance

SCENARIOS: List[dict] = [
    {"id": "train_01", "seed": 101, "split": "train", "perturb": {"rsl_noise_pct": 0.05}},
    {
        "id": "test_01",
        "seed": 202,
        "split": "test",
        "perturb": {"demand_multiplier": 1.2, "travel_delay_hours": 4.0},
    },
    {
        "id": "hidden_01",
        "seed": 303,
        "split": "hidden",
        "perturb": {
            "rsl_noise_pct": 0.10,
            "demand_multiplier": 1.4,
            "travel_delay_hours": 6.0,
            "price_shock_pct": -0.08,
            "missing_demand_pct": 0.03,
        },
    },
]

_BY_ID: Dict[str, dict] = {s["id"]: s for s in SCENARIOS}


def list_scenarios() -> List[dict]:
    return [{"scenario_id": s["id"], "seed": s["seed"], "split": s["split"]} for s in SCENARIOS]


def get_spec(scenario_id: str) -> Optional[dict]:
    return _BY_ID.get(scenario_id)


def build_instance(
    scenario_id: str, cost_model: CostModel, with_clearance: bool = True
) -> Instance:
    """Materialize a scenario, applying its perturbation profile deterministically."""
    spec = get_spec(scenario_id)
    if spec is None:
        raise KeyError(f"unknown scenario {scenario_id!r}")
    base = generate_instance(
        seed=spec["seed"],
        cost_model=cost_model,
        scenario_id=spec["id"],
        split=spec["split"],
        with_clearance=with_clearance,
    )
    return apply_perturbations(base, spec.get("perturb"), seed=spec["seed"] + 1)
