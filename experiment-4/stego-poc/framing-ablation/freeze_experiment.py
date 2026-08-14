#!/usr/bin/env python3
"""Freeze the completed negative Arm A gate and all evidence hashes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from validate import ROOT


def sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    gate = json.loads((ROOT / "results/development-gate.json").read_text())
    integrity = json.loads((ROOT / "results/integrity-audit.json").read_text())
    if gate.get("development_gate_passed") is not False or not integrity.get("passed"):
        raise RuntimeError("failed raw gate and passed integrity audit required")
    files = ("frozen-references.json", "tool-schema.json", "results/protocol-freeze.json",
             "results/reference-validation.json", "results/isolation-validation.json",
             "results/development-gate.json", "results/framing-comparison.csv",
             "results/arm-summary.csv", "results/analysis.md", "results/integrity-audit.json",
             "development/raw/results/execution-freeze.json",
             "development/raw/results/trials-unscored.jsonl",
             "development/raw/results/trials.jsonl")
    record = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
              "intended_git_tag": "experiment-4b1-framing-ablation-raw-gate",
              "status": "raw_gate_failed_after_one_expected_marker",
              "raw_trials": 4, "expected_markers": 1, "complete_pairs": 0,
              "counterpart_errors": 0, "arm_b_trials": 0, "heldout_trials": 0,
              "direct_api_used": False,
              "file_hashes": {name: sha256(ROOT / name) for name in files},
              "trace_hashes": {path.stem: sha256(path) for path in sorted((ROOT / "development/raw/traces").glob("*.jsonl"))},
              "marker_log_hashes": {path.stem: sha256(path) for path in sorted((ROOT / "development/raw/marker-logs").glob("*.json"))}}
    path = ROOT / "results/experiment-freeze.json"
    if path.exists(): raise RuntimeError("experiment freeze already exists")
    path.write_text(json.dumps(record, indent=2) + "\n"); print(json.dumps(record, indent=2))


if __name__ == "__main__": main()
