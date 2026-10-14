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
            raw=data,
        )

    def spoilage_fraction(self, perishability_class: str) -> float:
        return float(self.spoilage_cost_fraction.get(perishability_class, 1.0))

    def config_hash(self) -> str:
        import hashlib
        import json

        blob = json.dumps(self.raw, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:12]
