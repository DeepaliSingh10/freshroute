"""Discount recommendation engine (MVP M4).

Rule-based and fully disclosed. Uses the discount ladder in the cost model and a
reference price (base market price). Each recommendation carries a human-readable reason.

Rules:
  R1 clearance_recovery : batch was cleared locally because no full-price lane could
                          deliver it before expiry. Discount = 1 - clearance_price / base.
  R2 spoil_no_buyer     : batch still spoiled (no feasible regular OR clearance buyer).
                          Recommend a pre-emptive deep discount / donation; recovery = 0.
  R3 at_risk_upsell     : batch is at risk (RSL <= t1) but was sold at full price; recommend
                          monitoring no discount needed. (Informational.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..data.cost_model import CostModel
from ..data.models import Instance
from ..optimizer.types import Plan

EPS = 1e-6


@dataclass(frozen=True)
class Discount:
    batch_id: str
    commodity_name: str
    rule_id: str
    discount_pct: float
    quantity_kg: float
    expected_recovered_value: float
    reason: str


def recommend_discounts(instance: Instance, cost_model: CostModel, plan: Plan) -> List[Discount]:
    ladder = cost_model.discount_ladder or {}
    t1 = float(ladder.get("t1_days", 3.0))
    d1 = float(ladder.get("d1", 0.15))
    d2 = float(ladder.get("d2", 0.30))

    demand = instance.demand_lookup()

    # Quantities dispatched to the clearance channel, per batch.
    clearance_qty: Dict[str, float] = {}
    for disp in plan.dispatches:
        d = instance.destinations[disp.destination_id]
        if d.is_clearance:
            clearance_qty[disp.batch_id] = clearance_qty.get(disp.batch_id, 0.0) + disp.quantity_kg

    shipped = plan.shipped_by_batch()
    out: List[Discount] = []

    for b in instance.batches.values():
        commodity = instance.commodities[b.commodity_id]
        base_price = commodity.base_price_per_kg
        clr_qty = clearance_qty.get(b.batch_id, 0.0)
        leftover = plan.leftover.get(b.batch_id, max(0.0, b.quantity_kg - shipped.get(b.batch_id, 0.0)))

        if clr_qty > EPS:
            # Find the clearance price for this batch's commodity (from any clearance outlet).
            clr_price = base_price * cost_model.clearance_price_fraction
            for (did, cid), dem in demand.items():
                if cid == b.commodity_id and instance.destinations[did].is_clearance:
                    clr_price = dem.price_per_kg
                    break
            disc = max(0.0, 1.0 - (clr_price / base_price)) if base_price else 0.0
            out.append(
                Discount(
                    batch_id=b.batch_id,
                    commodity_name=commodity.name,
                    rule_id="clearance_recovery",
                    discount_pct=round(disc, 3),
                    quantity_kg=round(clr_qty, 2),
                    expected_recovered_value=round(clr_qty * clr_price, 2),
                    reason=(
                        f"{commodity.name} batch {b.batch_id} has {b.remaining_shelf_life_days:.1f}d "
                        f"shelf life; no full-price lane can deliver it in time. Clear {clr_qty:.0f}kg "
                        f"locally at Rs{clr_price:.2f}/kg ({disc:.0%} off base Rs{base_price:.2f}) to "
                        f"recover value instead of spoiling."
                    ),
                )
            )
        elif leftover > EPS and b.remaining_shelf_life_days <= t1 + cost_model.shelf_life_buffer_days:
            out.append(
                Discount(
                    batch_id=b.batch_id,
                    commodity_name=commodity.name,
                    rule_id="spoil_no_buyer",
                    discount_pct=round(d2, 3),
                    quantity_kg=round(leftover, 2),
                    expected_recovered_value=0.0,
                    reason=(
                        f"{commodity.name} batch {b.batch_id} will expire in "
                        f"{b.remaining_shelf_life_days:.1f}d with no feasible buyer (regular or "
                        f"clearance). Recommend pre-emptive {d2:.0%} discount / donation drive; "
                        f"no recoverable value modeled."
                    ),
                )
            )
        elif b.remaining_shelf_life_days <= t1:
            out.append(
                Discount(
                    batch_id=b.batch_id,
                    commodity_name=commodity.name,
                    rule_id="at_risk_monitor",
                    discount_pct=round(d1, 3),
                    quantity_kg=round(b.quantity_kg, 2),
                    expected_recovered_value=0.0,
                    reason=(
                        f"{commodity.name} batch {b.batch_id} is at risk ({b.remaining_shelf_life_days:.1f}d "
                        f"left) but was placed at full price; monitor and hold {d1:.0%} discount ready."
                    ),
                )
            )

    return out
