#!/usr/bin/env python3
"""Freeze the public C1 protocol before any cloud association is created."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from runtime import atomic_json
from validate import ROOT, validate


SOURCE_FILES = (
    "README.md", "protocol.md", "public-labels.json",
    "CLOUD-PLACEMENT-INSTRUCTIONS.md", "IMPORTANT-NO-SECRET-VALUES-IN-GIT.md",
    "runtime.py", "validate.py", "validate_isolation.py", "freeze_protocol.py",
    "run.py", "score_after_unblinding.py",
)
EXPECTED_PARENT = "e81926adc710a7630e8b7c92c1ff71b6433930bc"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    output = ROOT / "results/freeze.json"
    if output.exists():
        raise RuntimeError("protocol is already frozen; do not overwrite it")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    if head != EXPECTED_PARENT:
        raise RuntimeError(f"expected frozen Experiment 4 parent {EXPECTED_PARENT}, found {head}")
    result = validate(require_freeze=False)
    result.update({
        "schema_version": 1,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "git_commit_before_protocol": head,
        "experiment_4_tag": "experiment-4c2-density-125-control-stop",
        "timeout_seconds": 600,
        "worker_count": 1,
        "query_template_frozen": True,
        "query_order_frozen": True,
        "allocations_frozen": True,
        "expected_values_present_locally": False,
        "response_inspection_before_execution_freeze": False,
        "source_hashes": {name: sha256(ROOT / name) for name in SOURCE_FILES},
    })
    atomic_json(output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
