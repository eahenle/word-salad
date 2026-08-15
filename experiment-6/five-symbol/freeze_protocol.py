#!/usr/bin/env python3
"""Freeze task, prompts, gates, runtime, and query order before inference."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone

from generate_clean import ROOT
from runtime import DISABLED_FEATURES, EFFORT, IMAGE, MODEL
from validate import validate


SOURCE_FILES = (
    "README.md", "hidden_tasks.py", "runtime.py", "generate_clean.py", "validate.py",
    "freeze_protocol.py", "validate_isolation.py", "run_cohort.py", "score_clean.py",
    "score_scrambled.py",
)


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    output = ROOT / "results/protocol-freeze.json"
    if output.exists():
        raise RuntimeError("protocol already frozen")
    result = validate(require_freeze=False)
    manifests = {
        cohort: json.loads((ROOT / "cohorts" / cohort / "manifest.json").read_text())
        for cohort in ("clean", "scrambled")
    }
    freeze = {
        "schema_version": 1,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "6A-five-symbol-instrument-v1",
        "repository_commit_before_experiment_changes": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "model": MODEL,
        "reasoning": EFFORT,
        "image": IMAGE,
        "python_version": platform.python_version(),
        "task_validation": result["task"],
        "prompt_hashes": result["prompt_hashes"],
        "query_orders": {key: value["query_order"] for key, value in manifests.items()},
        "clean_gate": {
            "A_normalized_exact_at_least": 18,
            "B_normalized_exact_at_least": 18,
            "scheduled_per_identity": 20,
            "timeouts_are_failures": True,
        },
        "scrambled_gate": {
            "scheduled": 10,
            "complete_A_or_B_target_sequences_exactly": 0,
        },
        "retry_policy": "only archived pre-response runner, transport, or authentication failure",
        "timeout_seconds": 600,
        "workers": 3,
        "score_only_after_complete_cohort_freeze": True,
        "direct_api_used": False,
        "disabled_features": list(DISABLED_FEATURES),
        "source_hashes": {name: sha256(ROOT / name) for name in SOURCE_FILES},
    }
    output.write_text(json.dumps(freeze, indent=2) + "\n")
    print(json.dumps(freeze, indent=2))


if __name__ == "__main__":
    main()
