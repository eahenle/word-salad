#!/usr/bin/env python3
"""Audit raw-model responses, accepted timeouts, and unresolved failures."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from generate import build_tasks
from run_raw_experiment import MODEL, REASONING, request_body, validate_response


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    tasks = {task.neutral_id: task for task in build_tasks(root)}
    failures: list[str] = []
    outcomes = {}
    for path in sorted((root / "raw-model" / "outcomes").glob("r*.json")):
        record = json.loads(path.read_text())
        trial_id = record["neutral_id"]
        task = tasks[trial_id]
        response = root / record["response_file"]
        try:
            summary = validate_response(response.read_bytes())
        except Exception as exc:
            failures.append(f"{trial_id}: response validation: {exc}")
            continue
        checks = {
            "prompt_hash": record["prompt_sha256"] == task.metadata["prompt_sha256"],
            "request_hash": record["request_sha256"] == hashlib.sha256(request_body(task)).hexdigest(),
            "response_hash": record["response_sha256"] == digest(response),
            "response_bytes": record["response_bytes"] == response.stat().st_size,
            "summary": record["summary"] == summary,
            "model": record["model"] == MODEL,
            "reasoning": record["reasoning_effort"] == REASONING,
            "tools": record["tools"] == [],
            "store": record["store"] is False,
        }
        failures.extend(f"{trial_id}: {name}" for name, passed in checks.items() if not passed)
        outcomes[trial_id] = record
    timeouts = {}
    for path in sorted((root / "raw-model" / "timeouts").glob("r*.json")):
        record = json.loads(path.read_text())
        trial_id = record["neutral_id"]
        task = tasks[trial_id]
        source = root / record["source_attempt"]
        attempt = json.loads(source.read_text())
        checks = {
            "prompt_hash": record["prompt_sha256"] == task.metadata["prompt_sha256"],
            "source_hash": record["source_attempt_sha256"] == digest(source),
            "source_id": attempt["neutral_id"] == trial_id,
            "zero_bytes": attempt["response_bytes"] == record["response_bytes"] == 0,
            "no_http_status": attempt["http_status"] is None,
            "remote_disconnect": "RemoteDisconnected" in (attempt.get("exception") or ""),
            "elapsed_window": 590 <= attempt["elapsed_seconds"] <= 660,
            "no_retry": record["retry"] is False,
        }
        failures.extend(f"{trial_id}: timeout {name}" for name, passed in checks.items() if not passed)
        timeouts[trial_id] = record
    overlap = set(outcomes) & set(timeouts)
    if overlap:
        failures.append(f"completed/timeout overlap: {sorted(overlap)}")
    unresolved = []
    terminal = set(outcomes) | set(timeouts)
    archived_attempts = []
    for path in sorted(
        (root / "raw-model" / "infrastructure-failures").glob("r*/attempt-*/attempt.json")
    ):
        attempt = json.loads(path.read_text())
        archived_attempts.append(attempt)
        if attempt["neutral_id"] not in terminal:
            unresolved.append(attempt)
    report = {
        "passed": not failures,
        "model": MODEL,
        "reasoning_effort": REASONING,
        "tools": [],
        "store": False,
        "scheduled_trials": len(tasks),
        "scheduled_outcomes": len(terminal),
        "completed_responses": len(outcomes),
        "timeout_nonresponses": len(timeouts),
        "untouched_trials": len(tasks) - len(terminal),
        "archived_attempts": len(archived_attempts),
        "unresolved_infrastructure_failures": len(unresolved),
        "unresolved_trial_ids": sorted({record["neutral_id"] for record in unresolved}),
        "response_statuses": dict(sorted(Counter(
            record["summary"]["status"] for record in outcomes.values()
        ).items())),
        "terminal_ids_unique": len(terminal),
        "failures": failures,
    }
    output = root / "results" / "raw-model-integrity-audit.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
