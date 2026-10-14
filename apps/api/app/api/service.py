"""Service layer: assemble API responses from the Owner-A core modules."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

from ..data.cost_model import CostModel
from ..data.models import Instance
from ..data.scenarios import build_instance, get_spec, list_scenarios
from ..optimizer.allocator import solve_optimizer
from ..optimizer.baseline import solve_baseline
from ..optimizer.discounts import recommend_discounts
from ..optimizer.feasibility import build_feasible_pairs
from ..optimizer.replan import Disruption, apply_disruption, replan
from ..optimizer.types import Plan
from ..eval.checker import check_plan
from ..eval.metrics import compare, compute_metrics
from ..eval import sensitivity

VERSION = "0.1.0"


@lru_cache(maxsize=1)
def get_cost_model() -> CostModel:
    return CostModel.load()


def scenario_specs() -> List[dict]:
    return list_scenarios()


def instance_for(scenario_id: str, include_clearance: bool = True) -> Instance:
    return build_instance(scenario_id, get_cost_model(), with_clearance=include_clearance)


def _metrics_out(m) -> dict:
    d = m.to_dict()
    d.pop("runtime_ms", None)
    return d


def _dispatch_row(instance: Instance, pair, disp) -> dict:
    b = instance.batches[disp.batch_id]
    c = instance.commodities[b.commodity_id]
    d = instance.destinations[disp.destination_id]
    if d.is_clearance:
        reason = (
            f"{c.name} batch {disp.batch_id} ({b.remaining_shelf_life_days:.1f}d) cleared locally "
            f"at Rs{pair.effective_price_per_kg:.2f}/kg to recover value before it spoils."
        )
    else:
        reason = (
            f"{c.name} batch {disp.batch_id} ({b.remaining_shelf_life_days:.1f}d, grade "
            f"{b.quality_grade}) -> {d.name}: margin Rs{pair.margin_per_kg:.2f}/kg, "
            f"{pair.travel_time_hours:.1f}h transit, {pair.residual_shelf_life_days:.1f}d shelf life left."
        )
    return {
        "batch_id": disp.batch_id,
        "commodity_name": c.name,
        "destination_id": disp.destination_id,
        "destination_name": d.name,
        "quantity_kg": round(disp.quantity_kg, 2),
        "price_per_kg": round(pair.effective_price_per_kg, 2),
        "margin_per_kg": round(pair.margin_per_kg, 2),
        "travel_hours": round(pair.travel_time_hours, 2),
        "is_clearance": bool(d.is_clearance),
        "reason": reason,
    }


def inventory_response(scenario_id: str) -> dict:
    inst = instance_for(scenario_id)
    return {
        "scenario_id": inst.scenario_id,
        "split": inst.split,
        "now_ts": inst.now_ts,
        "n_batches": len(inst.batches),
        "total_inventory_kg": round(sum(b.quantity_kg for b in inst.batches.values()), 1),
        "batches": [
            {
                "batch_id": b.batch_id,
                "commodity_id": b.commodity_id,
                "commodity_name": inst.commodities[b.commodity_id].name,
                "quantity_kg": round(b.quantity_kg, 1),
                "remaining_shelf_life_days": round(b.remaining_shelf_life_days, 2),
                "origin_id": b.origin_id,
                "quality_grade": b.quality_grade,
            }
            for b in inst.batches.values()
        ],
        "destinations": [
            {
                "destination_id": d.destination_id,
                "name": d.name,
                "region": d.region,
                "min_days_fresh_on_shelf": d.min_days_fresh_on_shelf,
                "price_factor": d.price_factor,
                "is_clearance": bool(d.is_clearance),
            }
            for d in inst.destinations.values()
        ],
    }


def _solve(instance: Instance, cost_model: CostModel) -> Plan:
    return solve_optimizer(instance, cost_model)


def plan_response(scenario_id: str, include_clearance: bool = True) -> dict:
    cost_model = get_cost_model()
    inst = instance_for(scenario_id, include_clearance=include_clearance)
    plan = _solve(inst, cost_model)
    pairs = build_feasible_pairs(inst, cost_model, include_clearance=include_clearance)
    m = compute_metrics(inst, cost_model, plan)
    m.violations = len(check_plan(inst, cost_model, plan))
    discounts = recommend_discounts(inst, cost_model, plan)

    dispatches = [
        _dispatch_row(inst, pairs[(disp.batch_id, disp.destination_id)], disp)
        for disp in plan.dispatches
        if (disp.batch_id, disp.destination_id) in pairs
    ]
    return {
        "scenario_id": inst.scenario_id,
        "status": plan.status,
        "metrics": _metrics_out(m),
        "dispatches": dispatches,
        "discounts": [
            {
                "batch_id": x.batch_id,
                "commodity_name": x.commodity_name,
                "rule_id": x.rule_id,
                "discount_pct": x.discount_pct,
                "quantity_kg": x.quantity_kg,
                "expected_recovered_value": x.expected_recovered_value,
                "reason": x.reason,
            }
            for x in discounts
        ],
        "violations": m.violations,
    }


def evaluate_response(scenario_id: str, baseline: str = "fefo") -> dict:
    cost_model = get_cost_model()
    inst = instance_for(scenario_id)
    plan_opt = _solve(inst, cost_model)
    plan_base = solve_baseline(inst, cost_model, strategy=baseline)
    m_opt = compute_metrics(inst, cost_model, plan_opt)
    m_base = compute_metrics(inst, cost_model, plan_base)
    v_opt = len(check_plan(inst, cost_model, plan_opt))
    m_opt.violations = v_opt
    return {
        "scenario_id": inst.scenario_id,
        "baseline": baseline,
        "optimizer": _metrics_out(m_opt),
        "baseline_metrics": _metrics_out(m_base),
        "compare": compare(m_opt, m_base),
        "violations_optimizer": v_opt,
    }


def replan_response(
    scenario_id: str, blocked_origins: List[str], travel_delay_hours: float
) -> dict:
    cost_model = get_cost_model()
    base = instance_for(scenario_id)
    plan0 = _solve(base, cost_model)
    m0 = compute_metrics(base, cost_model, plan0)

    if not blocked_origins:
        stock: Dict[str, float] = {}
        for b in base.batches.values():
            stock[b.origin_id] = stock.get(b.origin_id, 0.0) + b.quantity_kg
        if stock:
            blocked_origins = [max(stock, key=stock.get)]

    disruption = Disruption(
        blocked_origins=tuple(blocked_origins),
        travel_delay_hours=travel_delay_hours,
        description=f"blocked={blocked_origins} delay={travel_delay_hours}h",
    )
    inst_dis = apply_disruption(base, disruption)
    frozen, combined = replan(inst_dis, plan0, cost_model)
    m_frozen = compute_metrics(inst_dis, cost_model, frozen)
    m_replan = compute_metrics(inst_dis, cost_model, combined)
    v_replan = len(check_plan(inst_dis, cost_model, combined))
    m_replan.violations = v_replan
    return {
        "scenario_id": base.scenario_id,
        "blocked_origins": list(disruption.blocked_origins),
        "travel_delay_hours": travel_delay_hours,
        "morning_plan": _metrics_out(m0),
        "no_replan": _metrics_out(m_frozen),
        "replan": _metrics_out(m_replan),
        "recovery": compare(m_replan, m_frozen),
        "violations_replan": v_replan,
    }


def explain_response(scenario_id: str) -> dict:
    cost_model = get_cost_model()
    inst = instance_for(scenario_id)
    plan = _solve(inst, cost_model)
    pairs = build_feasible_pairs(inst, cost_model, include_clearance=True)
    reasons: List[dict] = []
    for disp in plan.dispatches:
        key = (disp.batch_id, disp.destination_id)
        if key in pairs:
            row = _dispatch_row(inst, pairs[key], disp)
            reasons.append(
                {"kind": "dispatch", "ref": f"{disp.batch_id}->{disp.destination_id}", "reason": row["reason"]}
            )
    for x in recommend_discounts(inst, cost_model, plan):
        reasons.append({"kind": f"discount:{x.rule_id}", "ref": x.batch_id, "reason": x.reason})
    return {"scenario_id": inst.scenario_id, "reasons": reasons}


def sensitivity_response(scenario_id: str, factor: str | None = None) -> dict:
    cost_model = get_cost_model()
    base = instance_for(scenario_id)
    factors = [factor] if factor else list(sensitivity.FACTORS)
    curves = {}
    for f in factors:
        meta = sensitivity.FACTORS[f]
        curves[f] = {
            "label": meta["label"],
            "range": meta["default_range"],
            "points": sensitivity.sweep(base, cost_model, f, meta["default_range"]),
        }
    return {"scenario_id": base.scenario_id, "curves": curves}
