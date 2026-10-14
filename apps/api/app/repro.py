"""Reproducibility harness (Owner B).

Stamps the environment + cost-model hash and records a SHA-256 of every generated
artifact, so `results/` is self-describing and can be verified/reproduced.

Usage:
    python scripts/run_all.py            # regenerate every artifact + write manifest
    from app.repro import build_manifest # inspect programmatically
"""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Dict, List, Tuple

from app.data.cost_model import CostModel

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "results"
MANIFEST_NAME = "manifest.json"

# (artifact file name, argv after the interpreter) — in regeneration order.
ARTIFACTS: List[Tuple[str, List[str]]] = [
    ("phase1_summary.json", ["run_phase1.py", "--no-clearance", "--write-results"]),
    ("phase2_summary.json", ["run_phase1.py", "--write-results"]),
    ("forecast_summary.json", ["run_forecast.py", "--write-results"]),
    ("robustness.json", ["run_robustness.py", "--draws", "30", "--write-results"]),
    ("replan_summary.json", ["run_replan.py", "--write-results"]),
    ("discount_policy_summary.json", ["run_discount_policy.py", "--write-results"]),
    ("telemetry_summary.json", ["run_telemetry.py", "--write-results"]),
    ("sensitivity_summary.json", ["run_sensitivity.py", "--write-results"]),
]

_PACKAGES = ("numpy", "pandas", "ortools", "yaml", "fastapi")


def command_str(argv: List[str]) -> str:
    return f"python scripts/{argv[0]} {' '.join(argv[1:])}".strip()


def environment() -> Dict[str, str]:
    env = {"python": platform.python_version(), "platform": platform.platform()}
    for name in _PACKAGES:
        try:
            mod = __import__(name)
            env[name] = str(getattr(mod, "__version__", "unknown"))
        except Exception:  # pragma: no cover - missing optional dep
            env[name] = "missing"
    return env


def sha256_file(path: Path) -> str:
    """Hash artifact bytes with newlines normalized, so the digest is identical on
    Windows (CRLF) and POSIX (LF) checkouts."""
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def build_manifest(results_dir: Path = RESULTS_DIR) -> Dict:
    results_dir = Path(results_dir)
    artifacts: Dict[str, dict] = {}
    for name, argv in ARTIFACTS:
        path = results_dir / name
        artifacts[name] = {
            "command": command_str(argv),
            "present": path.exists(),
            "sha256": sha256_file(path) if path.exists() else None,
        }
    return {
        "cost_model_hash": CostModel.load().config_hash(),
        "environment": environment(),
        "artifacts": artifacts,
    }


def write_manifest(results_dir: Path = RESULTS_DIR) -> Path:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    dest = results_dir / MANIFEST_NAME
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(build_manifest(results_dir), indent=2, sort_keys=True))
    return dest
