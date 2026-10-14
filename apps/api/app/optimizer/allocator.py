"""LP allocator (Owner A core): maximize net revenue subject to hard feasibility.

Decision variables
    x[b,d]   >= 0   kg of batch b shipped to destination d   (feasible pairs only)
    left[b]  >= 0   kg of batch b not dispatched (may spoil)
    unmet[d,c]>=0   kg of demand at destination d for commodity c not served

Objective (maximize)
    sum x * effective_price
  - sum x * transport_cost
  - sum x * handling_cost
  - sum left * spoilage_cost_per_kg
  - sum unmet * unmet_penalty

Hard constraints
    (1) stock     : sum_d x[b,d] + left[b] = qty[b]
    (2) demand    : sum_b x[b,d] + unmet[d,c] = demand[d,c]
    (3) lane cap  : sum_b x[b,d] <= lane.capacity_kg          (grouped by origin->dest)
    (4) shelf life: enforced by only creating feasible pairs (see feasibility.py)
"""

from __future__ import annotations

import time
from typing import Dict, Tuple

from ortools.linear_solver import pywraplp

from ..data.cost_model import CostModel
from ..data.models import Instance
from .feasibility import build_feasible_pairs
from .types import Dispatch, Plan

EPS = 1e-6


def solve_optimizer(
    instance: Instance, cost_model: CostModel, time_limit_ms: int = 10000
) -> Plan:
    pairs = build_feasible_pairs(instance, cost_model)

    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:  # pragma: no cover - GLOP always available with ortools
        raise RuntimeError("GLOP solver unavailable")

    # --- variables ---
    x: Dict[Tuple[str, str], object] = {}
    for key in pairs:
        x[key] = solver.NumVar(0.0, solver.infinity(), f"x_{key[0]}_{key[1]}")

    left = {
        b.batch_id: solver.NumVar(0.0, b.quantity_kg, f"left_{b.batch_id}")
        for b in instance.batches.values()
    }

    unmet: Dict[Tuple[str, str], object] = {}
    for dem in instance.demands:
        k = (dem.destination_id, dem.commodity_id)
        unmet[k] = solver.NumVar(0.0, max(0.0, dem.demand_kg), f"unmet_{k[0]}_{k[1]}")

    # --- constraints ---
    # (1) stock balance per batch
    for b in instance.batches.values():
        ct = solver.Constraint(b.quantity_kg, b.quantity_kg, f"stock_{b.batch_id}")
        for (bid, did), var in x.items():
            if bid == b.batch_id:
                ct.SetCoefficient(var, 1.0)
        ct.SetCoefficient(left[b.batch_id], 1.0)

    # (2) demand balance per (destination, commodity)
    for dem in instance.demands:
        k = (dem.destination_id, dem.commodity_id)
        ct = solver.Constraint(dem.demand_kg, dem.demand_kg, f"demand_{k[0]}_{k[1]}")
        for (bid, did), var in x.items():
            if did == dem.destination_id and pairs[(bid, did)].commodity_id == dem.commodity_id:
                ct.SetCoefficient(var, 1.0)
        ct.SetCoefficient(unmet[k], 1.0)

    # (3) lane capacity per (origin, destination)
    for lane in instance.lanes.values():
        ct = solver.Constraint(-solver.infinity(), lane.capacity_kg, f"lane_{lane.lane_id}")
        for (bid, did), var in x.items():
            if did == lane.destination_id and pairs[(bid, did)].origin_id == lane.origin_id:
                ct.SetCoefficient(var, 1.0)

    # --- objective ---
    objective = solver.Objective()
    for key, var in x.items():
        p = pairs[key]
        objective.SetCoefficient(var, p.margin_per_kg)
    for b in instance.batches.values():
        commodity = instance.commodities[b.commodity_id]
        spoilage_cost_per_kg = (
            commodity.cost_basis_per_kg * cost_model.spoilage_fraction(commodity.perishability_class)
        )
        objective.SetCoefficient(left[b.batch_id], -spoilage_cost_per_kg)
    for k, var in unmet.items():
        objective.SetCoefficient(var, -cost_model.unmet_demand_penalty_per_kg)
    objective.SetMaximization()

    solver.SetTimeLimit(int(time_limit_ms))
    t0 = time.perf_counter()
    status = solver.Solve()
    runtime_ms = (time.perf_counter() - t0) * 1000.0

    status_name = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
        pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
        pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
        pywraplp.Solver.ABNORMAL: "ABNORMAL",
        pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
    }.get(status, "UNKNOWN")

    dispatches = []
    leftover: Dict[str, float] = {}
    if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        for (bid, did), var in x.items():
            qty = var.solution_value()
            if qty > EPS:
                dispatches.append(
                    Dispatch(batch_id=bid, destination_id=did, quantity_kg=round(qty, 4))
                )
        for bid, var in left.items():
            leftover[bid] = round(max(0.0, var.solution_value()), 4)
        obj_val = objective.Value()
    else:
        for b in instance.batches.values():
            leftover[b.batch_id] = b.quantity_kg
        obj_val = float("nan")

    return Plan(
        method="lp_optimizer",
        dispatches=dispatches,
        leftover=leftover,
        status=status_name,
        objective_value=obj_val,
        solver="GLOP",
        runtime_ms=round(runtime_ms, 2),
    )
