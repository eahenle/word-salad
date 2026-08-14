#!/usr/bin/env python3
"""Freeze the completed Experiment 3 datasets and analysis artifacts by hash."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from runtime import atomic_json


FILES = (
    "prompt-manifest.json",
    "capability-probe.json",
    "isolation-validation.json",
    "anchor-freeze.json",
    "screening-freeze.json",
    "confirmation-plan.json",
    "confirmation-freeze.json",
    "integrity-audit.json",
    "trials.jsonl",
    "model-reasoning-matrix.csv",
    "matched-tests.json",
    "analysis.md",
    "confirmation-trials.jsonl",
    "confirmation-combined-trials.jsonl",
    "confirmation-summary.csv",
    "confirmation-matched-tests.json",
    "confirmation-analysis.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    output = root / "results/experiment-freeze.json"
    if output.exists():
        raise RuntimeError(f"refusing to overwrite frozen manifest: {output}")
    integrity = json.loads((root / "results/integrity-audit.json").read_text())
    if not integrity.get("passed"):
        raise RuntimeError("passed integrity audit required")
    missing = [name for name in FILES if not (root / "results" / name).is_file()]
    if missing:
        raise RuntimeError(f"missing freeze inputs: {missing}")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root.parent,
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    result = {
        "experiment": "experiment-3-frequency-jitter-and-capability-scaling",
        "status": "frozen_after_targeted_confirmation",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_checkpoint_commit": head,
        "intended_immutable_git_tag": "experiment-3-frequency-jitter-scaling",
        "direct_api_calls": 0,
        "new_docker_codex_trials": 616,
        "screening_matrix_trials": 516,
        "targeted_confirmation_trials": 120,
        "artifact_sha256": {name: sha(root / "results" / name) for name in FILES},
        "nested_trace_hash_manifests": [
            "anchor-freeze.json", "screening-freeze.json", "confirmation-freeze.json"
        ],
        "note": "The immutable git tag, rather than this pre-commit field, records the final repository commit.",
    }
    atomic_json(output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
