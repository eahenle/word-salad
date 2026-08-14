#!/usr/bin/env python3
"""Write the final immutable evidence manifest for the negative 4B pilot."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    integrity = json.loads((ROOT / "results/integrity-audit.json").read_text())
    summary = json.loads((ROOT / "development/results/summary.json").read_text())
    if not integrity.get("passed") or summary.get("development_gate_passed") is not False:
        raise RuntimeError("passed integrity audit and failed development gate required")
    files = ("results/stimulus-freeze.json", "results/stimulus-validation.json",
             "results/isolation-validation.json", "results/integrity-audit.json",
             "results/analysis.md", "development/results/execution-freeze.json",
             "development/results/trials-unscored.jsonl", "development/results/trials.jsonl",
             "development/results/summary.json")
    record = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
              "intended_git_tag": "experiment-4b-harmless-canary-negative-pilot",
              "status": "development_gate_failed_heldout_not_run",
              "development_trials": 4, "expected_marker_calls": 0,
              "complete_pairs": 0, "heldout_trials_run": 0,
              "direct_api_used": False,
              "file_hashes": {name: sha256(ROOT / name) for name in files}}
    path = ROOT / "results/experiment-freeze.json"
    if path.exists(): raise RuntimeError("pilot freeze already exists")
    path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
