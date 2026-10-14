"""Shared result types returned by baseline and optimizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Dispatch:
    batch_id: str
    destination_id: str
    quantity_kg: float


@dataclass
class Plan:
    method: str
    dispatches: List[Dispatch] = field(default_factory=list)
    # Not-dispatched quantity per batch (kg); leftover spoils or is salvaged per class.
    leftover: Dict[str, float] = field(default_factory=dict)
    status: str = "OK"
    objective_value: float = 0.0
    solver: str = ""
    runtime_ms: float = 0.0

    def shipped_by_batch(self) -> Dict[str, float]:
        acc: Dict[str, float] = {}
        for d in self.dispatches:
            acc[d.batch_id] = acc.get(d.batch_id, 0.0) + d.quantity_kg
        return acc
