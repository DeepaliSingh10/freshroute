"""Pydantic schemas for the FreshRoute API (mirror docs/DATA_SPEC.md)."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------- system ----------
class HealthResponse(BaseModel):
    status: str
    version: str
    cost_model_hash: str


class ScenarioInfo(BaseModel):
    scenario_id: str
    seed: int
    split: str


class ScenarioList(BaseModel):
    scenarios: List[ScenarioInfo]


# ---------- inventory ----------
class BatchOut(BaseModel):
    batch_id: str
    commodity_id: str
    commodity_name: str
    quantity_kg: float
    remaining_shelf_life_days: float
    origin_id: str
    quality_grade: str


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
    batches: List[BatchOut]
    destinations: List[DestinationOut]


# ---------- plan ----------
class PlanRequest(BaseModel):
    scenario_id: str = Field(..., examples=["hidden_01"])
    include_clearance: bool = True


class DispatchOut(BaseModel):
    batch_id: str
    commodity_name: str
    destination_id: str
    destination_name: str
    quantity_kg: float
    price_per_kg: float
    margin_per_kg: float
    travel_hours: float
    is_clearance: bool
    reason: str


class DiscountOut(BaseModel):
    batch_id: str
    commodity_name: str
    rule_id: str
    discount_pct: float
    quantity_kg: float
    expected_recovered_value: float
    reason: str


class MetricsOut(BaseModel):
    method: str
    status: str
    spoilage_kg: float
    spoilage_pct: float
    expired_kg: float
    clearance_kg: float
    clearance_revenue: float
    fulfilled_kg: float
    demand_kg: float
    fulfillment_pct: float
    revenue: float
    transport_cost: float
    handling_cost: float
    spoilage_cost: float
    net_revenue: float
    violations: int = 0


class PlanResponse(BaseModel):
    scenario_id: str
    status: str
    metrics: MetricsOut
    dispatches: List[DispatchOut]
    discounts: List[DiscountOut]
    violations: int


# ---------- evaluate ----------
class EvaluateRequest(BaseModel):
    scenario_id: str
    baseline: str = "fefo"


class EvaluateResponse(BaseModel):
    scenario_id: str
    baseline: str
    optimizer: MetricsOut
    baseline_metrics: MetricsOut
    compare: Dict[str, float]
    violations_optimizer: int


# ---------- replan ----------
class ReplanRequest(BaseModel):
    scenario_id: str
    blocked_origins: List[str] = Field(default_factory=list)
    travel_delay_hours: float = 6.0


class ReplanResponse(BaseModel):
    scenario_id: str
    blocked_origins: List[str]
    travel_delay_hours: float
    morning_plan: MetricsOut
    no_replan: MetricsOut
    replan: MetricsOut
    recovery: Dict[str, float]
    violations_replan: int


# ---------- explain ----------
class ReasonOut(BaseModel):
    kind: str
    ref: str
    reason: str


class ExplainResponse(BaseModel):
    scenario_id: str
    reasons: List[ReasonOut]


# ---------- sensitivity ----------
class SensitivityRequest(BaseModel):
    scenario_id: str
    factor: Optional[str] = None


class SensitivityResponse(BaseModel):
    scenario_id: str
    curves: Dict[str, dict]
