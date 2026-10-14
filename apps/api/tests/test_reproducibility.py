"""Reproducibility (Owner B): the results manifest is complete and matches disk."""

from __future__ import annotations

import json

from app.data.cost_model import CostModel
from app.repro import ARTIFACTS, MANIFEST_NAME, RESULTS_DIR, build_manifest, sha256_file


def _load_manifest() -> dict:
    path = RESULTS_DIR / MANIFEST_NAME
    assert path.exists(), f"missing {path}; run `python scripts/run_all.py`"
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_pins_config_hash():
    manifest = _load_manifest()
    assert manifest["cost_model_hash"] == CostModel.load().config_hash()


def test_all_artifacts_present():
    manifest = _load_manifest()
    for name, _argv in ARTIFACTS:
        entry = manifest["artifacts"][name]
        assert entry["present"], f"{name} not recorded as present"
        assert entry["sha256"], f"{name} has no recorded hash"


def test_manifest_matches_disk():
    manifest = _load_manifest()
    for name, _argv in ARTIFACTS:
        recorded = manifest["artifacts"][name]["sha256"]
        on_disk = sha256_file(RESULTS_DIR / name)
        assert recorded == on_disk, f"{name} changed since manifest was written"


def test_build_manifest_is_deterministic():
    a = build_manifest()
    b = build_manifest()
    assert a["cost_model_hash"] == b["cost_model_hash"]
    assert a["artifacts"] == b["artifacts"]
    assert a["environment"]["python"]


def test_commands_are_documented():
    manifest = _load_manifest()
    for name, argv in ARTIFACTS:
        assert manifest["artifacts"][name]["command"].endswith(" ".join(argv[1:]))
