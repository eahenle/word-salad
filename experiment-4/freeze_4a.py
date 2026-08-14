#!/usr/bin/env python3
"""Freeze completed Experiment 4A data and analysis artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from runtime import atomic_json


FILES = (
    "prompt-manifest.json", "prompt-validation.json", "prompt-freeze.json",
    "isolation-validation.json", "capability-probe.json", "execution-freeze.json",
    "integrity-audit.json", "trials.jsonl", "carrier-comparison.csv",
    "effort-summary.csv", "mask-outcomes.csv", "matched-tests.json", "analysis.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    results = root / "uniform/results"
    output = results / "experiment-freeze.json"
    if output.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    integrity = json.loads((results / "integrity-audit.json").read_text())
    if not integrity.get("passed"):
        raise RuntimeError("passed integrity audit required")
    missing = [name for name in FILES if not (results / name).is_file()]
    if missing:
        raise RuntimeError(f"missing freeze inputs: {missing}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root.parent, check=True,
                          capture_output=True, text=True).stdout.strip()
    record = {
        "experiment": "experiment-4a-uniform-random-carrier",
        "status": "frozen_after_scoring_and_analysis",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_base_commit": head,
        "intended_immutable_git_tag": "experiment-4a-uniform-random",
        "fresh_docker_trials": 90,
        "direct_api_calls": 0,
        "artifact_sha256": {name: sha(results / name) for name in FILES},
        "trace_hash_manifest": "execution-freeze.json",
        "note": "The immutable git tag records the final repository commit.",
    }
    atomic_json(output, record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
