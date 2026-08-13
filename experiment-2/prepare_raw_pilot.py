#!/usr/bin/env python3
"""Extract final API text and build the frozen tool-less pilot scoring input."""

from __future__ import annotations

import json
from pathlib import Path

from generate import build_tasks


def final_text(response: dict) -> str:
    chunks = []
    for item in response.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                chunks.append(str(content.get("text") or ""))
    return "\n".join(chunks)


def main() -> None:
    root = Path(__file__).resolve().parent
    freeze = json.loads((root / "results" / "raw-model-pilot-freeze.json").read_text())
    first, last = freeze["included_trial_range"]
    low, high = int(first[1:]), int(last[1:])
    tasks = {
        task.neutral_id: task for task in build_tasks(root)
        if low <= int(task.neutral_id[1:]) <= high
    }
    records = []
    for trial_id, task in sorted(tasks.items()):
        outcome_path = root / "raw-model" / "outcomes" / f"{trial_id}.json"
        timeout_path = root / "raw-model" / "timeouts" / f"{trial_id}.json"
        if outcome_path.exists() == timeout_path.exists():
            raise RuntimeError(f"{trial_id}: expected exactly one response or timeout")
        if outcome_path.exists():
            outcome = json.loads(outcome_path.read_text())
            response = json.loads((root / outcome["response_file"]).read_text())
            text = final_text(response)
            runner = {
                "method": "responses_api_single_request_no_tools",
                "timed_out": False,
                "error": None,
                "elapsed_seconds": outcome.get("elapsed_seconds"),
                "aggregate_usage": outcome["summary"].get("usage"),
                "response_sha256": outcome["response_sha256"],
                "response_bytes": outcome["response_bytes"],
                "event_type_counts": {"turn.completed": 1},
            }
            completed_response = True
        else:
            timeout = json.loads(timeout_path.read_text())
            text = ""
            runner = {
                "method": "responses_api_single_request_no_tools",
                "timed_out": True,
                "error": {"type": "timeout_nonresponse", "timeout_seconds": 600},
                "elapsed_seconds": timeout["observed_elapsed_seconds"],
                "aggregate_usage": None,
                "response_sha256": None,
                "response_bytes": 0,
                "event_type_counts": {},
            }
            completed_response = False
        records.append({
            "trial_id": trial_id,
            "neutral_id": trial_id,
            "regime": "tool_less_responses_api",
            "arm": task.arm,
            "condition": task.condition,
            "payload_identity": task.payload_identity,
            "answer_identity": task.metadata["answer_identity"],
            "lanes": task.lanes,
            "seed": task.seed,
            "signal_phase": task.metadata["signal_phase"],
            "model": "gpt-5.6-sol",
            "reasoning": "xhigh",
            "tools": [],
            "store": False,
            "prompt_words": task.metadata["prompt_words"],
            "prompt_sha256": task.metadata["prompt_sha256"],
            "response": text,
            "runner": runner,
            "completed_response": completed_response,
        })
    if len(records) != freeze["frozen_pilot_trials"]:
        raise RuntimeError("frozen pilot count mismatch")
    output = root / "results" / "raw-model-pilot-unscored.jsonl"
    output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    )
    print(f"prepared {len(records)} frozen tool-less pilot records")


if __name__ == "__main__":
    main()
