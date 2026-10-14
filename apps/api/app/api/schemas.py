"""Pydantic schemas for the FreshRoute API.

These mirror the **frozen B<->C contract** documented in docs/WORKSTREAMS.md (section
"Frozen interfaces") and consumed by the React dashboard in
`apps/web/src/api/types.ts`.

Response models include a few additive convenience fields (names, clearance flags,
internal metric components). TypeScript clients ignore unknown fields, so extras are safe
and keep the same response usable by both the contract fields and richer tooling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ---------- system ----------
class HealthResponse(BaseModel):
    status: str
    version: str
    # `config_hash` is the frozen-contract name; `cost_model_hash` is kept for tooling.
    config_hash: str
    cost_model_hash: str


class ScenarioInfo(BaseModel):
    scenario_id: str
    seed: int
    split: str
    perturbation_profile: Optional[str] = None


# ---------- inventory ----------
class CommodityOut(BaseModel):
    commodity_id: str
    name: str
    perishability_class: str
    default_shelf_life_days: float
    cost_basis_per_kg: float
    handling_per_kg: Optional[float] = None


class BatchOut(BaseModel):
    batch_id: str
    commodity_id: str
    quantity_kg: float
    remaining_shelf_life_days: float
    origin_id: Optional[str] = None
    quality_grade: Optional[str] = None
    harvest_ts: Optional[str] = None


class DestinationOut(BaseModel):
    destination_id: str
    name: str
    region: str
    min_days_fresh_on_shelf: float
    price_factor: float
    is_clearance: bool


class InventoryResponse(BaseModel):
    scenario_id: str
    split: str
    now_ts: str
    n_batches: int
    total_inventory_kg: float
    commodities: List[CommodityOut]
    batches: List[BatchOut]
    destinations: List[DestinationOut]


# ---------- plan ----------
class PlanRequest(BaseModel):
    scenario_id: str = Field(..., examples=["hidden_01"])
    include_clearance: bool = True


class DispatchOut(BaseModel):
    # frozen contract
    batch_id: str
    commodity_id: str
    destination_id: str
    quantity_kg: float
    price_per_kg: float
    effective_price_per_kg: float
    travel_time_hours: float
    transport_cost: float
    margin: float
    priority_rank: int
    urgency_days: float
    feasible: bool
    reason: str
    # additive convenience
    commodity_name: str
    destination_name: str
    margin_per_kg: float
    is_clearance: bool


class DiscountOut(BaseModel):
    # frozen contract
    batch_id: str
    rule_id: str
    discount_pct: float
    expected_recovered_value: float
    reason: str
    # additive convenience
    commodity_name: str
    quantity_kg: float


class LeftoverOut(BaseModel):
    batch_id: str
    quantity_kg: float
    spoilage_cost: float


class ValidationOut(BaseModel):
    violations: List[str]
    degraded: bool
    warnings: List[str]


class MetricsOut(BaseModel):
    # frozen contract
    spoilage_kg: float
    spoilage_pct: float
    fulfilled_kg: float
    fulfillment_pct: float
    unmet_kg: float
    revenue: float
    transport_cost: float
    handling_cost: float
    spoilage_cost: float
    net_revenue: float
    # additive tooling fields
    method: str
    status: str
    expired_kg: float
    clearance_kg: float
    clearance_revenue: float
    demand_kg: float
    violations: int


class PlanResponse(BaseModel):
    scenario_id: str
    config_hash: str
    now_ts: str
    status: str
    dispatches: List[DispatchOut]
    discounts: List[DiscountOut]
    leftover: List[LeftoverOut]
    validation: ValidationOut
    metrics: MetricsOut


# ---------- evaluate ----------
class EvaluateRequest(BaseModel):
    # Frozen contract accepts a list; `scenario_id` is accepted as a convenience.
    scenario_ids: Optional[List[str]] = None
    scenario_id: Optional[str] = None
    baseline: str = "fefo"


class PerScenarioEval(BaseModel):
    scenario_id: str
    split: str
    proposed: MetricsOut
    baseline: MetricsOut


class EvalAggregate(BaseModel):
    spoilage_pct_reduction: float
    fulfillment_delta: float
    net_revenue_delta: float
    net_revenue_delta_pct: float
    violations_total: int


class RobustnessOut(BaseModel):
    net_revenue_mean: float
    net_revenue_p10: float


class EvaluateResponse(BaseModel):
    per_scenario: List[PerScenarioEval]
    aggregate: EvalAggregate
    robustness: Optional[RobustnessOut] = None


# ---------- replan ----------
class ReplanEvent(BaseModel):
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class ReplanRequest(BaseModel):
    scenario_id: str
    event: Optional[ReplanEvent] = None
    # Optional direct disruption parameters (kept for tooling / tests).
    blocked_origins: List[str] = Field(default_factory=list)
    travel_delay_hours: float = 6.0


class PlanDiffEntry(BaseModel):
    batch_id: str
    destination_id: Optional[str] = None
    change: str  # added | removed | changed
    reason: str


class ReplanResponse(BaseModel):
    scenario_id: str
    plan: PlanResponse
    diff: List[PlanDiffEntry]
    # additive tooling fields
    event_type: str
    morning_plan: MetricsOut
    no_replan: MetricsOut
    recovery: Dict[str, float]
    violations_replan: int


# ---------- explain ----------
class ExplainRequest(BaseModel):
    batch_id: str
    destination_id: str = ""


class ExplainFactor(BaseModel):
    factor: str
    value: Union[str, float]
    contribution: Optional[float] = None
    note: Optional[str] = None


class ExplainConstraint(BaseModel):
    name: str
    satisfied: bool
    detail: Optional[str] = None


class ExplainResponse(BaseModel):
    batch_id: str
    destination_id: str
    recommendation: str
    reason: str
    urgency_days: Optional[float] = None
    factors: List[ExplainFactor]
    constraints: List[ExplainConstraint]


# ---------- sensitivity (additive tooling endpoint) ----------
class SensitivityRequest(BaseModel):
    scenario_id: str
    factor: Optional[str] = None


class SensitivityResponse(BaseModel):
    scenario_id: str
    curves: Dict[str, dict]


# ---------- robustness (E4 Monte Carlo) ----------
class RobustnessStats(BaseModel):
    mean: float
    std: float
    min: float
    p10: float
    p50: float
    p90: float
    max: float


class RobustnessScenario(BaseModel):
    scenario_id: str
    split: str
    draws: int
    metrics: Dict[str, RobustnessStats]


class RobustnessBand(BaseModel):
    """Compact net-revenue uncertainty band for one scenario (drives the dashboard band)."""

    scenario_id: str
    draws: int
    net_revenue_mean: float
    net_revenue_p10: float
    net_revenue_p90: float
    net_revenue_delta_mean: float
    net_revenue_delta_p10: float
    spoilage_reduction_mean: float
    spoilage_reduction_p10: float


class RobustnessRequest(BaseModel):
    scenario_ids: Optional[List[str]] = None
    draws: int = 20


class RobustnessResponse(BaseModel):
    draws: int
    scenarios: List[RobustnessScenario]
    overall: Dict[str, RobustnessStats]
    total_hard_violations: int
    band: RobustnessBand
