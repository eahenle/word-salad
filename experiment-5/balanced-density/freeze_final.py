#!/usr/bin/env python3
"""Create the final content manifest after every ladder stage is scored."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from generate import ROOT, STAGES
from runtime import atomic_json


OUTPUT = ROOT / "results/final-freeze.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
    ).strip()


def relative_hashes(paths: list[Path]) -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): sha256(path)
        for path in sorted(paths)
        if path.is_file() and path != OUTPUT
    }


def main() -> None:
    stage_files: list[Path] = []
    stage_summary = {}
    for stage in STAGES:
        stage_root = ROOT / "stages" / stage
        execution = stage_root / "results/execution-freeze.json"
        trials = stage_root / "results/trials.jsonl"
        if not execution.exists() or not trials.exists():
            raise RuntimeError(f"stage is not frozen and scored: {stage}")
        frozen = json.loads(execution.read_text())
        scored = [json.loads(line) for line in trials.read_text().splitlines() if line.strip()]
        if frozen["completed"] != 9 or len(scored) != 9:
            raise RuntimeError(f"unexpected trial count: {stage}")
        stage_summary[stage] = {
            "completed_trials": len(scored),
            "runner_errors": sum(row["runner"]["error"] is not None for row in scored),
            "timeouts": sum(row["runner"]["timed_out"] for row in scored),
            "trace_hashes": {
                row["trial_id"]: row["runner"]["trace_sha256"] for row in scored
            },
        }
        for directory in ("attempts", "completed", "metadata", "prompts", "results", "stderr", "traces"):
            candidate = stage_root / directory
            if candidate.exists():
                stage_files.extend(path for path in candidate.rglob("*") if path.is_file())

    source_files = [ROOT / "README.md"] + sorted(ROOT.glob("*.py"))
    result_files = [
        path for path in (ROOT / "results").glob("*")
        if path.is_file() and path != OUTPUT
    ]
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_commit_before_final_freeze": git("rev-parse", "HEAD"),
        "intended_tag": "experiment-5-balanced-density-frozen",
        "completed_stages": list(STAGES),
        "stage_summary": stage_summary,
        "source_hashes": relative_hashes(source_files),
        "result_hashes": relative_hashes(result_files),
        "stage_artifact_hashes": relative_hashes(stage_files),
        "invalidated_attempts_preserved": 2,
        "invalidated_attempt_reason": "pre-response authentication refresh failure",
        "direct_api_used": False,
        "secret_values_present": False,
    }
    atomic_json(OUTPUT, manifest)
    print(json.dumps({
        "completed_stages": manifest["completed_stages"],
        "stage_artifacts": len(manifest["stage_artifact_hashes"]),
        "source_commit_before_final_freeze": manifest["source_commit_before_final_freeze"],
    }, indent=2))


if __name__ == "__main__":
    main()
