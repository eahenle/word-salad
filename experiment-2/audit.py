#!/usr/bin/env python3
"""Verify Experiment 2 stored artifacts, hashes, trace framing, and runner outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from generate import build_tasks
from validate import validate


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--expected", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    prompt_report = validate(args.root)
    tasks = {task.neutral_id: task for task in build_tasks(args.root)}
    records = [
        json.loads(path.read_text()) for path in sorted((args.root / "completed").glob("r*.json"))
    ]
    failures = []
    active_by_id = {record["neutral_id"]: record for record in records}
    for record in records:
        trial_id = record["neutral_id"]
        task = tasks.get(trial_id)
        if task is None:
            failures.append(f"unknown completed ID {trial_id}")
            continue
        trace = (args.root / record["trace_file"]).read_bytes()
        stderr = (args.root / record["stderr_file"]).read_bytes()
        runner = record["runner"]
        checks = {
            "prompt": record["prompt_sha256"] == task.metadata["prompt_sha256"],
            "trace_hash": digest(trace) == runner["trace_sha256"],
            "trace_bytes": len(trace) == runner["trace_bytes"],
            "stderr_hash": digest(stderr) == runner["stderr_sha256"],
            "stderr_bytes": len(stderr) == runner["stderr_bytes"],
        }
        failures.extend(f"{trial_id}: {name}" for name, passed in checks.items() if not passed)
    archived_quota_attempts = []
    for decision_path in sorted(
        (args.root / "invalidated-attempts").glob("r*/attempt-*/retry-decision.json")
    ):
        decision = json.loads(decision_path.read_text())
        trial_id = decision["neutral_id"]
        archived_quota_attempts.append(trial_id)
        active = active_by_id.get(trial_id)
        if active is None:
            failures.append(f"{trial_id}: archived retry has no active outcome")
        elif active["prompt_sha256"] != decision["prompt_sha256"]:
            failures.append(f"{trial_id}: retry prompt hash differs from archived attempt")
        archive = decision_path.parent
        for name, expected in decision["original_artifacts"].items():
            path = archive / name
            if not path.is_file():
                failures.append(f"{trial_id}: missing archived {name}")
            elif digest(path.read_bytes()) != expected["sha256"]:
                failures.append(f"{trial_id}: archived {name} hash mismatch")
    if args.expected is not None and len(records) != args.expected:
        failures.append(f"expected {args.expected} records, found {len(records)}")
    report = {
        "passed": not failures, "completed_records": len(records),
        "unique_completed_ids": len({record["neutral_id"] for record in records}),
        "conditions": dict(sorted(Counter(record["condition"] for record in records).items())),
        "arms": dict(sorted(Counter(record["arm"] for record in records).items())),
        "runner_errors": dict(sorted(Counter(
            (record["runner"].get("error") or {}).get("type", "none") for record in records
        ).items())),
        "nonempty_stderr": sum(record["runner"]["stderr_bytes"] > 0 for record in records),
        "archived_quota_attempts": len(archived_quota_attempts),
        "archived_quota_retry_ids": archived_quota_attempts,
        "archived_retry_prompt_hashes_match_active": not any(
            "retry prompt hash" in failure for failure in failures
        ),
        "prompt_validation": prompt_report, "failures": failures,
    }
    output = args.output or args.root / "results" / "integrity-audit.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
