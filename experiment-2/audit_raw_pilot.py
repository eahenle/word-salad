#!/usr/bin/env python3
"""Audit the frozen, scored, cost-truncated tool-less pilot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apply_blind_audit import audit_id
from generate import build_tasks
from run_raw_experiment import request_body
from score import keys


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    results = root / "results"
    freeze = json.loads((results / "raw-model-pilot-freeze.json").read_text())
    tasks = {task.neutral_id: task for task in build_tasks(root)}
    unscored = read_jsonl(results / "raw-model-pilot-unscored.jsonl")
    auto = read_jsonl(results / "raw-model-pilot-auto-scored.jsonl")
    packet = read_jsonl(results / "raw-model-pilot-blind-packet.jsonl")
    decisions = read_jsonl(results / "raw-model-pilot-blind-decisions.jsonl")
    trials = read_jsonl(results / "raw-model-pilot-trials.jsonl")
    codex = {record["neutral_id"]: record for record in read_jsonl(results / "trials.jsonl")}
    expected_ids = [f"r{number:04}" for number in range(1, 95)]
    failures: list[str] = []

    for name, records, id_field in (
        ("unscored", unscored, "neutral_id"),
        ("auto", auto, "neutral_id"),
        ("trials", trials, "neutral_id"),
    ):
        ids = [record[id_field] for record in records]
        if ids != expected_ids:
            failures.append(f"{name}: ID sequence differs from r0001:r0094")
        if len(ids) != len(set(ids)):
            failures.append(f"{name}: duplicate IDs")
    expected_audit_ids = {audit_id(trial_id) for trial_id in expected_ids}
    for name, records in (("packet", packet), ("decisions", decisions)):
        ids = [record["audit_id"] for record in records]
        if set(ids) != expected_audit_ids or len(ids) != len(expected_audit_ids):
            failures.append(f"{name}: blind ID coverage differs")

    packet_forbidden = {
        "condition", "lanes", "seed", "signal_phase", "payload_identity",
        "answer_identity", "semantic_success", "trial_id", "neutral_id",
    }
    for record in packet:
        leaked = packet_forbidden & set(record)
        if leaked:
            failures.append(f"packet {record['audit_id']}: forbidden metadata {sorted(leaked)}")

    answer_keys = keys(root)
    completed, timeouts = 0, 0
    request_schema_verified = True
    for record in trials:
        trial_id = record["neutral_id"]
        task = tasks[trial_id]
        if record["prompt_sha256"] != task.metadata["prompt_sha256"]:
            failures.append(f"{trial_id}: generated prompt hash mismatch")
        if record["prompt_sha256"] != codex[trial_id]["prompt_sha256"]:
            failures.append(f"{trial_id}: Codex prompt hash mismatch")
        body = json.loads(request_body(task))
        if (
            set(body) != {"model", "input", "reasoning", "tools", "store"}
            or body["input"] != task.prompt
            or body["tools"] != []
            or body["store"] is not False
            or body["reasoning"] != {"effort": "xhigh"}
            or body["model"] != "gpt-5.6-sol"
        ):
            request_schema_verified = False
            failures.append(f"{trial_id}: tool-less request isolation mismatch")
        expected = answer_keys.get(record.get("answer_identity"))
        should_succeed = bool(expected and record["assignments"] == expected)
        if record["semantic_success"] != should_succeed:
            failures.append(f"{trial_id}: semantic score mismatch")
        outcome = root / "raw-model" / "outcomes" / f"{trial_id}.json"
        timeout = root / "raw-model" / "timeouts" / f"{trial_id}.json"
        if outcome.exists() == timeout.exists():
            failures.append(f"{trial_id}: expected exactly one completed/timeout artifact")
        elif outcome.exists():
            completed += 1
            outcome_record = json.loads(outcome.read_text())
            response = root / outcome_record["response_file"]
            if sha256(response) != outcome_record["response_sha256"]:
                failures.append(f"{trial_id}: raw response hash mismatch")
            if record["runner"]["timed_out"] or not record["completed_response"]:
                failures.append(f"{trial_id}: completed-state mismatch")
        else:
            timeouts += 1
            if not record["runner"]["timed_out"] or record["completed_response"]:
                failures.append(f"{trial_id}: timeout-state mismatch")

    observed_cells = {}
    for record in trials:
        key = (record["arm"], record["condition"], record["lanes"], record.get("payload_identity"))
        observed_cells[key] = observed_cells.get(key, 0) + 1
    expected_cells = {
        ("constrained", "clean", 1, "A"): 20,
        ("constrained", "clean", 1, "B"): 20,
        ("constrained", "signal", 2, "A"): 20,
        ("constrained", "signal", 2, "B"): 20,
        ("constrained", "all_shuffled", 2, None): 14,
    }
    if observed_cells != expected_cells:
        failures.append("frozen cohort cell structure mismatch")
    if completed != freeze["completed_responses"] or timeouts != freeze["timeout_nonresponses"]:
        failures.append("freeze terminal counts mismatch")
    if freeze["scoring_had_started_at_freeze"] or freeze["response_text_had_been_inspected_at_freeze"]:
        failures.append("pre-scoring freeze declaration changed")
    if freeze["additional_api_calls_authorized"]:
        failures.append("additional API calls unexpectedly authorized")

    report = {
        "passed": not failures,
        "frozen_trial_range": ["r0001", "r0094"],
        "scheduled_trials": len(trials),
        "completed_responses": completed,
        "timeout_nonresponses": timeouts,
        "blind_packet_records": len(packet),
        "blind_decision_records": len(decisions),
        "prompt_hashes_match_codex_by_neutral_id": not any(
            "Codex prompt hash" in failure for failure in failures
        ),
        "raw_response_hashes_verified": not any(
            "raw response hash" in failure for failure in failures
        ),
        "semantic_scores_recomputed": not any(
            "semantic score" in failure for failure in failures
        ),
        "blind_packet_forbidden_metadata_absent": not any(
            failure.startswith("packet ") for failure in failures
        ),
        "request_schema_verified": request_schema_verified,
        "request_has_instructions_field": False,
        "request_has_previous_response_id": False,
        "request_tools": [],
        "request_store": False,
        "prompt_is_sole_input": request_schema_verified,
        "first_excluded_trial": freeze["first_excluded_trial"],
        "additional_api_calls_authorized": freeze["additional_api_calls_authorized"],
        "failures": failures,
    }
    (results / "raw-model-pilot-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
