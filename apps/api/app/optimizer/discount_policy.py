"""E2 — optimized markdown timing & price under uncertainty.

The Phase-2/M4 discount engine is *rule-based* (fixed ladder). E2 instead **optimizes**
the markdown for each at-risk batch: choose (discount depth × days-to-hold) to maximize the
expected recovered value under uncertainty in remaining shelf life and demand.

Disclosed model (all parameters in `cost_model.yaml::discount_policy`):
  - price-elastic clearance: clearable_qty scales by (1/(1−d))^elasticity with depth d;
  - full-price selling before the markdown at `full_price_rate`/day;
  - days held at full price = hold; discounted window = remaining_life − hold;
  - leftover after selling spoils and is charged `cost_basis × spoilage_fraction`;
  - value(draw) = full_sold·p0 + disc_sold·p0·(1−d) − spoilage_cost(leftover).

We report the mean and P10 (worst-case) of the chosen option, and compare to doing nothing
and to the fixed 30%-off rule from M4.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass(frozen=True)
class MarkdownDecision:
    batch_id: str
    commodity_name: str
    quantity_kg: float
    remaining_shelf_life_days: float
    discount_pct: float
    hold_days: float
    expected_value: float
    p10_value: float
    no_discount_value: float
    rule_30_value: float
    uplift_vs_rule: float
    reason: str


def _value_draws(
    quantity: float,
    base_price: float,
    cost_basis: float,
    spoilage_fraction: float,
    rsl: float,
    discount: float,
    hold: float,
    policy: dict,
    rng: np.random.Generator,
    n_draws: int,
) -> np.ndarray:
    elasticity = float(policy.get("elasticity", 1.5))
    full_rate = float(policy.get("full_price_rate", 0.10))
    clear_rate = float(policy.get("clear_rate", 0.55))
    rsl_noise = float(policy.get("rsl_noise", 0.15))
    dem_noise = float(policy.get("demand_noise", 0.25))

    R = np.clip(rsl * (1.0 + rng.uniform(-rsl_noise, rsl_noise, n_draws)), 0.05, None)
    shock = np.exp(rng.normal(0.0, dem_noise, n_draws))

    hold_eff = np.minimum(hold, R)
    disc_window = np.maximum(0.0, R - hold_eff)

    price = base_price * (1.0 - discount)
    full_sold = np.minimum(quantity, full_rate * hold_eff * quantity * shock)
    clear_cap = clear_rate * (1.0 / (1.0 - discount)) ** elasticity * disc_window * quantity * shock
    disc_sold = np.minimum(quantity - full_sold, np.maximum(0.0, clear_cap))

    revenue = full_sold * base_price + disc_sold * price
    leftover = np.maximum(0.0, quantity - full_sold - disc_sold)
    spoilage_cost = leftover * cost_basis * spoilage_fraction
    return revenue - spoilage_cost


def optimize_batch_markdown(
    batch_id: str,
    commodity_name: str,
    quantity: float,
    base_price: float,
    cost_basis: float,
    spoilage_fraction: float,
    rsl: float,
    policy: dict,
    seed: int = 0,
) -> MarkdownDecision:
    levels: List[float] = list(policy.get("levels", [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]))
    hold_fracs: List[float] = list(policy.get("hold_fractions", [0.0, 0.25, 0.5]))
    n_draws = int(policy.get("n_draws", 400))

    best = None  # (mean_value, discount, hold, p10)
    no_disc = -1e18
    rule30 = -1e18

    for d in levels:
        for hf in hold_fracs:
            hold = hf * rsl
            vals = _value_draws(
                quantity, base_price, cost_basis, spoilage_fraction, rsl, d, hold,
                policy, np.random.default_rng(seed + int(d * 1000) + int(hf * 100)), n_draws,
            )
            mean_v = float(np.mean(vals))
            if d == 0.0 and mean_v > no_disc:
                no_disc = mean_v
            if abs(d - 0.30) < 1e-9 and hf == 0.0:
                rule30 = mean_v
            if best is None or mean_v > best[0]:
                best = (mean_v, d, hold, float(np.percentile(vals, 10)))

    assert best is not None
    mean_v, d, hold, p10 = best
    uplift = mean_v - (rule30 if rule30 > -1e17 else no_disc)

    if d <= 1e-9:
        reason = (
            f"{commodity_name} batch {batch_id}: hold at full price (no markdown) — "
            f"remaining life {rsl:.1f}d still supports full-price selling; "
            f"expected value {mean_v:,.0f}."
        )
    else:
        reason = (
            f"{commodity_name} batch {batch_id}: mark down {d:.0%} after holding {hold:.1f}d "
            f"(price-elastic clearance), vs fixed 30% rule -> uplift {uplift:+,.0f}; "
            f"expected {mean_v:,.0f} (P10 {p10:,.0f}) on {quantity:.0f}kg at {rsl:.1f}d life."
        )

    return MarkdownDecision(
        batch_id=batch_id,
        commodity_name=commodity_name,
        quantity_kg=round(quantity, 2),
        remaining_shelf_life_days=round(rsl, 2),
        discount_pct=round(d, 3),
        hold_days=round(hold, 2),
        expected_value=round(mean_v, 2),
        p10_value=round(p10, 2),
        no_discount_value=round(no_disc, 2),
        rule_30_value=round(rule30, 2),
        uplift_vs_rule=round(uplift, 2),
        reason=reason,
    )
