"""Cost-model correctness and stability."""

from __future__ import annotations

from app.data.cost_model import CostModel


def test_config_hash_is_stable_and_nonempty():
    cm = CostModel.load()
    h = cm.config_hash()
    assert isinstance(h, str) and len(h) >= 8
    assert CostModel.load().config_hash() == h


def test_spoilage_fractions_match_spec():
    cm = CostModel.load()
    assert cm.spoilage_fraction("leafy") == 1.0
    assert cm.spoilage_fraction("berry") == 1.0
    assert cm.spoilage_fraction("soft_fruit") == 0.9
    assert cm.spoilage_fraction("root") == 0.6
    assert cm.spoilage_fraction("tuber") == 0.6
    # unknown class defaults to full loss
    assert cm.spoilage_fraction("unknown") == 1.0


def test_clearance_and_penalty_params():
    cm = CostModel.load()
    assert cm.unmet_demand_penalty_per_kg == 10.0
    assert 0.0 < cm.clearance_price_fraction < 1.0
    assert cm.clearance_demand_fraction > 0.0
    assert cm.shelf_life_buffer_days > 0.0
