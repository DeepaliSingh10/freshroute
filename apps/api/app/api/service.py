"""Service layer: assemble API responses from the Owner-A core modules.

Shapes follow the frozen B<->C contract (docs/WORKSTREAMS.md) consumed by
`apps/web/src/api/types.ts`. Additive fields are included for richer tooling/tests.
"""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from ..data.cost_model import CostModel
from ..data.models import Instance
from ..data.scenarios import build_instance, get_spec, list_scenarios
from ..optimizer.allocator import solve_optimizer
from ..optimizer.baseline import solve_baseline
from ..optimizer.discounts import recommend_discounts
from ..optimizer.feasibility import build_feasible_pairs, is_feasible
from ..optimizer.replan import Disruption, apply_disruption, keep_dispatched, replan
from ..optimizer.types import Plan
from ..eval.checker import check_plan
from ..eval.metrics import compare, compute_metrics
from ..eval import sensitivity

VERSION = "0.2.0"


@lru_cache(maxsize=1)
def get_cost_model() -> CostModel:
    return CostModel.load()


def scenario_specs() -> List[dict]:
    out = []
    for s in list_scenarios():
        spec = get_spec(s["scenario_id"]) or {}
        profile = ",".join(sorted((spec.get("perturb") or {}).keys())) or None
        out.append({**s, "perturbation_profile": profile})
    return out


def default_scenario_id() -> str:
    specs = list_scenarios()
    for s in specs:
        if s["split"] == "hidden":
            return s["scenario_id"]
    return specs[-1]["scenario_id"]


def instance_for(scenario_id: str, include_clearance: bool = True) -> Instance:
    return build_instance(scenario_id, get_cost_model(), with_clearance=include_clearance)


def _metrics_out(m) -> dict:
    d = m.to_dict()
    d.pop("runtime_ms", None)
    return d


# --------------------------------------------------------------------------- #
# Inventory
# --------------------------------------------------------------------------- #
def inventory_response(scenario_id: str) -> dict:
    inst = instance_for(scenario_id)
    return {
        "scenario_id": inst.scenario_id,
        "split": inst.split,
        "now_ts": inst.now_ts,
        "n_batches": len(inst.batches),
        "total_inventory_kg": round(sum(b.quantity_kg for b in inst.batches.values()), 1),
        "commodities": [
            {
                "commodity_id": c.commodity_id,
                "name": c.name,
                "perishability_class": c.perishability_class,
                "default_shelf_life_days": c.default_shelf_life_days,
                "cost_basis_per_kg": c.cost_basis_per_kg,
                "handling_per_kg": c.handling_per_kg,
            }
            for c in inst.commodities.values()
        ],
        "batches": [
            {
                "batch_id": b.batch_id,
                "commodity_id": b.commodity_id,
                "quantity_kg": round(b.quantity_kg, 1),
                "remaining_shelf_life_days": round(b.remaining_shelf_life_days, 2),
                "origin_id": b.origin_id,
                "quality_grade": b.quality_grade,
                "harvest_ts": b.harvest_ts,
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


# --------------------------------------------------------------------------- #
# Plan
# --------------------------------------------------------------------------- #
def _dispatch_rows(inst: Instance, cm: CostModel, plan: Plan, pairs) -> List[dict]:
    demand = inst.demand_lookup()
    rows: List[dict] = []
    for disp in plan.dispatches:
        pair = pairs.get((disp.batch_id, disp.destination_id))
        if pair is None:
            continue
        b = inst.batches[disp.batch_id]
        c = inst.commodities[b.commodity_id]
        d = inst.destinations[disp.destination_id]
        dem = demand.get((disp.destination_id, b.commodity_id))
        base_price = dem.price_per_kg if dem is not None else pair.effective_price_per_kg
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
        rows.append(
            {
                "batch_id": disp.batch_id,
                "commodity_id": b.commodity_id,
                "destination_id": disp.destination_id,
                "quantity_kg": round(disp.quantity_kg, 2),
                "price_per_kg": round(base_price, 2),
                "effective_price_per_kg": round(pair.effective_price_per_kg, 2),
                "travel_time_hours": round(pair.travel_time_hours, 2),
                "transport_cost": round(disp.quantity_kg * pair.transport_cost_per_kg, 2),
                "margin": round(disp.quantity_kg * pair.margin_per_kg, 2),
                "priority_rank": 0,
                "urgency_days": round(b.remaining_shelf_life_days, 2),
                "feasible": is_feasible(
                    b.remaining_shelf_life_days,
                    pair.travel_time_hours,
                    d.min_days_fresh_on_shelf,
                    cm,
                ),
                "reason": reason,
                "commodity_name": c.name,
                "destination_name": d.name,
                "margin_per_kg": round(pair.margin_per_kg, 2),
                "is_clearance": bool(d.is_clearance),
            }
        )

    # Perishability-first priority: most urgent (least remaining shelf life) ranks first.
    rows.sort(key=lambda r: (r["is_clearance"], r["urgency_days"]))
    for i, r in enumerate(rows, start=1):
        r["priority_rank"] = i
    return rows


def _leftover_rows(inst: Instance, cm: CostModel, plan: Plan) -> List[dict]:
    shipped = plan.shipped_by_batch()
    out = []
    for b in inst.batches.values():
        qty = plan.leftover.get(b.batch_id, max(0.0, b.quantity_kg - shipped.get(b.batch_id, 0.0)))
        if qty <= 0:
            continue
        commodity = inst.commodities[b.commodity_id]
        frac = cm.spoilage_fraction(commodity.perishability_class)
        out.append(
            {
                "batch_id": b.batch_id,
                "quantity_kg": round(qty, 2),
                "spoilage_cost": round(qty * commodity.cost_basis_per_kg * frac, 2),
            }
        )
    return out


def _plan_payload(inst: Instance, plan: Plan, cm: CostModel) -> dict:
    pairs = build_feasible_pairs(inst, cm, include_clearance=True)
    m = compute_metrics(inst, cm, plan)
    violations = check_plan(inst, cm, plan)
    m.violations = len(violations)
    discounts = recommend_discounts(inst, cm, plan)
    return {
        "scenario_id": inst.scenario_id,
        "config_hash": cm.config_hash(),
        "now_ts": inst.now_ts,
        "status": plan.status,
        "dispatches": _dispatch_rows(inst, cm, plan, pairs),
        "discounts": [
            {
                "batch_id": x.batch_id,
                "rule_id": x.rule_id,
                "discount_pct": x.discount_pct,
                "expected_recovered_value": x.expected_recovered_value,
                "reason": x.reason,
                "commodity_name": x.commodity_name,
                "quantity_kg": x.quantity_kg,
            }
            for x in discounts
        ],
        "leftover": _leftover_rows(inst, cm, plan),
        "validation": {
            "violations": violations,
            "degraded": plan.status not in ("OK", "OPTIMAL"),
            "warnings": [],
        },
        "metrics": _metrics_out(m),
    }


def plan_response(scenario_id: str, include_clearance: bool = True) -> dict:
    cm = get_cost_model()
    inst = instance_for(scenario_id, include_clearance=include_clearance)
    plan = solve_optimizer(inst, cm)
    return _plan_payload(inst, plan, cm)


# --------------------------------------------------------------------------- #
# Evaluate
# --------------------------------------------------------------------------- #
def evaluate_response(scenario_ids: Optional[List[str]] = None,
                      baseline: str = "fefo",
                      scenario_id: Optional[str] = None) -> dict:
    ids = list(scenario_ids or [])
    if scenario_id and scenario_id not in ids:
        ids.append(scenario_id)
    if not ids:
        ids = [default_scenario_id()]

    cm = get_cost_model()
    per_scenario = []
    total_opt_spoil = total_base_spoil = 0.0
    total_opt_rev = total_base_rev = 0.0
    fulfillment_deltas: List[float] = []
    violations_total = 0

    for sid in ids:
        inst = instance_for(sid)
        plan_opt = solve_optimizer(inst, cm)
        plan_base = solve_baseline(inst, cm, strategy=baseline)
        m_opt = compute_metrics(inst, cm, plan_opt)
        m_base = compute_metrics(inst, cm, plan_base)
        v_opt = len(check_plan(inst, cm, plan_opt))
        v_base = len(check_plan(inst, cm, plan_base))
        m_opt.violations = v_opt
        m_base.violations = v_base
        per_scenario.append(
            {
                "scenario_id": inst.scenario_id,
                "split": inst.split,
                "proposed": _metrics_out(m_opt),
                "baseline": _metrics_out(m_base),
            }
        )
        total_opt_spoil += m_opt.spoilage_kg
        total_base_spoil += m_base.spoilage_kg
        total_opt_rev += m_opt.net_revenue
        total_base_rev += m_base.net_revenue
        fulfillment_deltas.append(m_opt.fulfillment_pct - m_base.fulfillment_pct)
        violations_total += v_opt + v_base

    n = len(per_scenario)
    aggregate = {
        "spoilage_pct_reduction": round(
            1.0 - (total_opt_spoil / total_base_spoil) if total_base_spoil else 0.0, 4
        ),
        "fulfillment_delta": round(sum(fulfillment_deltas) / n, 4),
        "net_revenue_delta": round(total_opt_rev - total_base_rev, 2),
        "net_revenue_delta_pct": round(
            ((total_opt_rev - total_base_rev) / total_base_rev) if total_base_rev else 0.0, 4
        ),
        "violations_total": violations_total,
    }
    return {"per_scenario": per_scenario, "aggregate": aggregate, "robustness": None}


# --------------------------------------------------------------------------- #
# Replan (event -> new plan + diff)
# --------------------------------------------------------------------------- #
def _mutate_for_event(base: Instance, event_type: str, payload: dict, cm: CostModel) -> Instance:
    if event_type == "traffic_delay":
        delay = float(payload.get("hours", payload.get("travel_delay_hours", 6.0)))
        stock: Dict[str, float] = {}
        for b in base.batches.values():
            stock[b.origin_id] = stock.get(b.origin_id, 0.0) + b.quantity_kg
        blocked = (max(stock, key=stock.get),) if stock else ()
        return apply_disruption(base, Disruption(blocked_origins=blocked, travel_delay_hours=delay))
    if event_type == "temp_spike":
        penalty = float(payload.get("rsl_penalty_days", 0.5))
        batches = {
            bid: replace(b, remaining_shelf_life_days=round(max(0.0, b.remaining_shelf_life_days - penalty), 3))
            for bid, b in base.batches.items()
        }
        return replace(base, batches=batches)
    if event_type == "capacity_change":
        factor = float(payload.get("factor", 0.8))
        lanes = {k: replace(l, capacity_kg=round(l.capacity_kg * factor, 1)) for k, l in base.lanes.items()}
        return replace(base, lanes=lanes)
    if event_type == "new_order":
        factor = float(payload.get("demand_multiplier", 1.15))
        demands = [replace(d, demand_kg=round(d.demand_kg * factor, 1)) for d in base.demands]
        return replace(base, demands=demands)
    # Unknown event: return unchanged network (re-optimize everything).
    return base


def _diff_plans(before: Plan, after: Plan, inst_after: Instance) -> List[dict]:
    def key(disp):
        return (disp.batch_id, disp.destination_id)

    before_q = {key(d): d.quantity_kg for d in before.dispatches}
    after_q = {key(d): d.quantity_kg for d in after.dispatches}
    diff: List[dict] = []
    for k in after_q:
        if k not in before_q:
            diff.append({"batch_id": k[0], "destination_id": k[1], "change": "added",
                         "reason": f"new shipment of {after_q[k]:.1f}kg added on the disrupted network."})
        elif abs(after_q[k] - before_q[k]) > 1e-6:
            diff.append({"batch_id": k[0], "destination_id": k[1], "change": "changed",
                         "reason": f"quantity changed {before_q[k]:.1f}kg -> {after_q[k]:.1f}kg."})
    for k in before_q:
        if k not in after_q:
            diff.append({"batch_id": k[0], "destination_id": k[1], "change": "removed",
                         "reason": f"{before_q[k]:.1f}kg shipment dropped (no longer feasible)."})
    return diff


def replan_response(scenario_id: str, event_type: str = "", payload: Optional[dict] = None,
                    blocked_origins: Optional[List[str]] = None,
                    travel_delay_hours: float = 6.0) -> dict:
    payload = payload or {}
    cm = get_cost_model()
    base = instance_for(scenario_id)
    plan0 = solve_optimizer(base, cm)
    m0 = compute_metrics(base, cm, plan0)
    m0.violations = len(check_plan(base, cm, plan0))

    if event_type:
        inst2 = _mutate_for_event(base, event_type, payload, cm)
    else:
        blocked = tuple(blocked_origins or ())
        if not blocked:
            stock: Dict[str, float] = {}
            for b in base.batches.values():
                stock[b.origin_id] = stock.get(b.origin_id, 0.0) + b.quantity_kg
            blocked = (max(stock, key=stock.get),) if stock else ()
        inst2 = apply_disruption(base, Disruption(blocked_origins=blocked, travel_delay_hours=travel_delay_hours))

    new_plan = solve_optimizer(inst2, cm)
    m_new = compute_metrics(inst2, cm, new_plan)
    v_new = len(check_plan(inst2, cm, new_plan))
    m_new.violations = v_new

    frozen = keep_dispatched(inst2, plan0, cm)
    m_frozen = compute_metrics(inst2, cm, frozen)
    m_frozen.violations = 0

    plan_payload = _plan_payload(inst2, new_plan, cm)
    return {
        "scenario_id": base.scenario_id,
        "plan": plan_payload,
        "diff": _diff_plans(plan0, new_plan, inst2),
        "event_type": event_type or "disruption",
        "morning_plan": _metrics_out(m0),
        "no_replan": _metrics_out(m_frozen),
        "recovery": compare(m_new, m_frozen),
        "violations_replan": v_new,
    }


# --------------------------------------------------------------------------- #
# Explain (single recommendation breakdown)
# --------------------------------------------------------------------------- #
def _ordered_scenario_ids() -> List[str]:
    ids = [s["scenario_id"] for s in list_scenarios()]
    default = default_scenario_id()
    return [default] + [i for i in ids if i != default]


def _resolve_explain_context(batch_id: str, destination_id: str):
    """Batch ids repeat across scenarios; prefer the scenario where (batch, dest) is feasible.

    The `/explain` contract carries only batch+destination (no scenario_id), so we search
    deterministically: default scenario first, then the rest, stepping past a candidate only
    when a later scenario can actually place the requested pair.
    """
    cm = get_cost_model()
    fallback = None
    for sid in _ordered_scenario_ids():
        inst = instance_for(sid)
        if batch_id not in inst.batches:
            continue
        plan = solve_optimizer(inst, cm)
        pairs = build_feasible_pairs(inst, cm, include_clearance=True)
        if fallback is None:
            fallback = (inst, plan, pairs)
        if destination_id and (batch_id, destination_id) in pairs:
            return inst, plan, pairs
    return fallback


def explain_response(batch_id: str, destination_id: str = "") -> dict:
    cm = get_cost_model()
    ctx = _resolve_explain_context(batch_id, destination_id)
    if ctx is None:
        return {
            "batch_id": batch_id,
            "destination_id": destination_id,
            "recommendation": "unknown",
            "reason": f"batch {batch_id} not found in any scenario",
            "urgency_days": None,
            "factors": [],
            "constraints": [],
        }

    inst, plan, pairs = ctx
    b = inst.batches[batch_id]
    c = inst.commodities[b.commodity_id]

    if not destination_id:
        dests = [d.destination_id for d in plan.dispatches if d.batch_id == batch_id]
        destination_id = dests[0] if dests else ""

    pair = pairs.get((batch_id, destination_id))
    d = inst.destinations.get(destination_id)

    factors = [
        {"factor": "perishability_class", "value": c.perishability_class, "note": "spoilage sensitivity"},
        {"factor": "remaining_shelf_life_days", "value": round(b.remaining_shelf_life_days, 2)},
        {"factor": "quality_grade", "value": b.quality_grade},
        {"factor": "cost_basis_per_kg", "value": round(c.cost_basis_per_kg, 2)},
    ]
    constraints = []
    recommendation = "hold"
    reason = f"{c.name} batch {batch_id}: no feasible market; monitor for discount."

    if pair is not None and d is not None:
        factors += [
            {"factor": "effective_price_per_kg", "value": round(pair.effective_price_per_kg, 2)},
            {"factor": "transport_cost_per_kg", "value": round(pair.transport_cost_per_kg, 2)},
            {"factor": "handling_per_kg", "value": round(pair.handling_per_kg, 2)},
            {"factor": "margin_per_kg", "value": round(pair.margin_per_kg, 2), "contribution": round(pair.margin_per_kg, 2)},
            {"factor": "travel_time_hours", "value": round(pair.travel_time_hours, 2)},
            {"factor": "residual_shelf_life_days", "value": round(pair.residual_shelf_life_days, 2)},
        ]
        feasible = is_feasible(
            b.remaining_shelf_life_days, pair.travel_time_hours, d.min_days_fresh_on_shelf, cm
        )
        constraints = [
            {"name": "shelf_life", "satisfied": feasible,
             "detail": f"{b.remaining_shelf_life_days:.1f}d RSL >= {pair.travel_time_hours/24 + cm.shelf_life_buffer_days + d.min_days_fresh_on_shelf:.1f}d required"},
            {"name": "lane_exists", "satisfied": True, "detail": f"{b.origin_id} -> {destination_id}"},
        ]
        if d.is_clearance:
            recommendation = "clearance"
            reason = (
                f"{c.name} batch {batch_id} routed to local clearance outlet {d.name} at "
                f"Rs{pair.effective_price_per_kg:.2f}/kg to recover value before spoilage."
            )
        else:
            recommendation = "dispatch"
            reason = (
                f"{c.name} batch {batch_id} -> {d.name}: margin Rs{pair.margin_per_kg:.2f}/kg with "
                f"{pair.residual_shelf_life_days:.1f}d shelf life remaining on arrival."
            )
    else:
        constraints = [{"name": "feasible_market", "satisfied": False,
                        "detail": "no feasible destination for this batch's remaining shelf life"}]

    return {
        "batch_id": batch_id,
        "destination_id": destination_id,
        "recommendation": recommendation,
        "reason": reason,
        "urgency_days": round(b.remaining_shelf_life_days, 2),
        "factors": factors,
        "constraints": constraints,
    }


# --------------------------------------------------------------------------- #
# Sensitivity (additive tooling endpoint)
# --------------------------------------------------------------------------- #
def sensitivity_response(scenario_id: str, factor: Optional[str] = None) -> dict:
    cm = get_cost_model()
    base = instance_for(scenario_id)
    factors = [factor] if factor else list(sensitivity.FACTORS)
    curves = {}
    for f in factors:
        meta = sensitivity.FACTORS[f]
        curves[f] = {
            "label": meta["label"],
            "range": meta["default_range"],
            "points": sensitivity.sweep(base, cm, f, meta["default_range"]),
        }
    return {"scenario_id": base.scenario_id, "curves": curves}
