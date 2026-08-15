#!/usr/bin/env python3
"""Freeze all task, carrier, prompt, and gate choices before inference."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from generate import ROOT, SEEDS, STAGES
from runtime import EFFORT, IMAGE, MODEL, atomic_json
from validate import validate


EXPECTED_PARENT = "10f5c8c"
SOURCE_FILES = (
    "README.md", "hidden_tasks.py", "simulate.py", "generate.py", "validate.py",
    "runtime.py", "validate_isolation.py", "freeze_protocol.py", "run_stage.py",
    "score_stage.py", "analyze.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    output = ROOT / "results/protocol-freeze.json"
    if output.exists():
        raise RuntimeError("protocol is already frozen")
    short = subprocess.run(["git", "rev-parse", "--short=7", "HEAD"], cwd=ROOT,
                           text=True, capture_output=True, check=True).stdout.strip()
    if short != EXPECTED_PARENT:
        raise RuntimeError(f"expected parent {EXPECTED_PARENT}, found {short}")
    validation = validate(require_freeze=False)
    full_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                               text=True, capture_output=True, check=True).stdout.strip()
    freeze = {
        "schema_version": 1,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "git_commit_before_protocol": full_head,
        "cloud_context_audit_tag": "experiment-5-cloud-context-audit-negative",
        "trace_awareness_audit_tag": "experiment-5-trace-awareness-audit",
        "model": MODEL, "reasoning": EFFORT, "image": IMAGE,
        "frame": "Read the following text and give the answer implied by it.",
        "stages": STAGES, "seeds": list(SEEDS),
        "scheduled_prompts": validation["scheduled_prompts"],
        "task_validation": validation["task"],
        "prompt_hashes": validation["prompt_hashes"],
        "primary_endpoint": "complete full-state A/B discrimination",
        "stage_recovery_gate": "at least 2/3 complete A/B pairs and zero scrambled full-target selections",
        "advancement_rule": "advance upward only while controls are clean and the recovery gate has not yet passed",
        "timeout_seconds": 600, "worker_count": 3,
        "timeouts_are_outcomes": True,
        "retry_only_demonstrated_transport_failure": True,
        "density_covaries_with_prompt_length": True,
        "all_prompts_frozen_before_inference": True,
        "source_hashes": {name: sha256(ROOT / name) for name in SOURCE_FILES},
    }
    atomic_json(output, freeze)
    print(json.dumps(freeze, indent=2))


if __name__ == "__main__":
    main()
