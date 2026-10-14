"""Load and represent the FreshRoute economic cost model (single source of truth)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import yaml

DEFAULT_COST_MODEL_PATH = Path(__file__).with_name("cost_model.yaml")


@dataclass(frozen=True)
class CostModel:
    transport_cost_per_kg_km: float
    handling_per_kg_default: float
    spoilage_cost_fraction: Dict[str, float]
    unmet_demand_penalty_per_kg: float
    discount_ladder: dict
    shelf_life_buffer_days: float
    clearance: dict
    raw: dict

    @classmethod
    def load(cls, path: str | Path = DEFAULT_COST_MODEL_PATH) -> "CostModel":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            transport_cost_per_kg_km=float(data["transport_cost_per_kg_km"]),
            handling_per_kg_default=float(data["handling_per_kg_default"]),
            spoilage_cost_fraction={
                k: float(v) for k, v in data["spoilage_cost_fraction"].items()
            },
            unmet_demand_penalty_per_kg=float(data["unmet_demand_penalty_per_kg"]),
            discount_ladder=data.get("discount_ladder", {}),
            shelf_life_buffer_days=float(data["shelf_life_buffer_days"]),
            clearance=data.get("clearance", {}),
            raw=data,
        )

    def spoilage_fraction(self, perishability_class: str) -> float:
        return float(self.spoilage_cost_fraction.get(perishability_class, 1.0))

    # --- E2 discount-policy params (with defaults) ---
    @property
    def discount_policy(self) -> dict:
        return self.raw.get("discount_policy", {})

    # --- E5 cold-chain / price-feed params ---
    @property
    def cold_chain(self) -> dict:
        return self.raw.get("cold_chain", {})

    @property
    def price_feed(self) -> dict:
        return self.raw.get("price_feed", {})

    # --- clearance channel helpers ---
    @property
    def clearance_price_fraction(self) -> float:
        return float(self.clearance.get("price_fraction", 0.45))

    @property
    def clearance_demand_fraction(self) -> float:
        return float(self.clearance.get("demand_fraction", 0.35))

    @property
    def clearance_travel_hours(self) -> float:
        return float(self.clearance.get("travel_hours", 0.75))

    @property
    def clearance_transport_cost_per_kg(self) -> float:
        return float(self.clearance.get("transport_cost_per_kg", 0.5))

    @property
    def clearance_lane_capacity_kg(self) -> float:
        return float(self.clearance.get("lane_capacity_kg", 1_000_000))

    @property
    def clearance_min_days_fresh(self) -> float:
        return float(self.clearance.get("min_days_fresh", 0.0))

    def config_hash(self) -> str:
        import hashlib
        import json

        blob = json.dumps(self.raw, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:12]
