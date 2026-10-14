"""Regenerate every reproducibility artifact, then write results/manifest.json.

Owner B reproducibility harness. Runs each runner as a subprocess (so a crash in one
step does not hide the rest), then records the cost-model hash, environment and a
SHA-256 per artifact.

Usage (from apps/api):
    python scripts/run_all.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repro import ARTIFACTS, command_str, write_manifest  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent


def main() -> int:
    failures = []
    for _name, argv in ARTIFACTS:
        print(f"\n=== {command_str(argv)} ===", flush=True)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / argv[0]), *argv[1:]],
            check=False,
        )
        if result.returncode != 0:
            failures.append(command_str(argv))
            print(f"  !! exited with code {result.returncode}", flush=True)

    dest = write_manifest()
    print(f"\nmanifest written to: {dest}")
    if failures:
        print("FAILED steps:\n  - " + "\n  - ".join(failures))
        return 1
    print("all artifacts regenerated cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
