#!/usr/bin/env python3
"""Preregistered answer-identity scoring for frozen Experiment 4C responses."""

from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from pathlib import Path

from runtime import atomic_bytes, atomic_json
from validate import ROOT


TARGETS = ("Rowan", "Mira")
DISCOVERY_TERMS = ("hidden", "encoded", "encoding", "interleav", "subsequence", "every nth", "sparse")


def response_words(response: str) -> list[str]:
    return re.findall(r"[A-Za-z]+", response.lower())


def selected_target(response: str) -> tuple[str | None, list[str]]:
    words = response_words(response)
    present = [target for target in TARGETS if target.lower() in words]
    return (present[0] if len(present) == 1 else None), present


def score_record(record: dict) -> dict:
    response = record["response"]; selected, present = selected_target(response)
    expected = record["expected_answer"]; error = record["runner"]["error"]
    strict_exact = expected is not None and response == expected
    normalized_exact = expected is not None and " ".join(response_words(response)) == expected.lower()
    semantic = expected is not None and selected == expected
    counterpart = expected is not None and selected in TARGETS and selected != expected
    if error:
        classification = "timeout" if record["runner"]["timed_out"] else "runner_error"
    elif not response.strip():
        classification = "nonresponse"
    elif semantic:
        classification = "expected_answer"
    elif counterpart:
        classification = "counterpart_answer"
    elif len(present) == 2:
        classification = "both_target_names"
    else:
        classification = "no_target_answer"
    lower = response.lower()
    scored = dict(record)
    scored.update({
        "strict_exact_success": strict_exact, "normalized_exact_success": normalized_exact,
        "semantic_success": semantic, "selected_target": selected,
        "target_names_present": present, "counterpart_error": counterpart,
        "control_target_selection": expected is None and selected in TARGETS,
        "classification": classification,
        "explicit_hidden_structure_mention": any(term in lower for term in DISCOVERY_TERMS),
    })
    return scored


def main() -> None:
    execution = json.loads((ROOT / "development/results/execution-freeze.json").read_text())
    if execution.get("completed") != 12:
        raise RuntimeError("all twelve responses must be frozen before scoring")
    records = [json.loads(line) for line in (ROOT / "development/results/trials-unscored.jsonl").read_text().splitlines()]
    if len(records) != 12:
        raise RuntimeError("unscored cohort is incomplete")
    scored = [score_record(record) for record in records]
    by_topic: dict[str, dict[str, dict]] = {}
    for record in scored:
        by_topic.setdefault(record["topic"], {})[record["condition"]] = record
    complete_pairs = [topic for topic, cells in by_topic.items()
                      if cells["hidden_a"]["semantic_success"] and cells["hidden_b"]["semantic_success"]]
    controls = [record for record in scored if record["condition"] in {"scrambled", "cover_only"}]
    control_targets = [record["trial_id"] for record in controls if record["control_target_selection"]]
    gate_passed = len(complete_pairs) >= 2 and len(control_targets) == 0
    gate = {
        "passed": gate_passed, "complete_ab_pairs": len(complete_pairs),
        "complete_ab_pair_topics": complete_pairs, "required_complete_ab_pairs": 2,
        "expected_hidden_answers": sum(record["semantic_success"] for record in scored),
        "hidden_signal_trials": 6,
        "control_target_answer_selections": len(control_targets),
        "control_target_trial_ids": control_targets,
        "required_control_target_answer_selections": 0,
        "counterpart_errors": sum(record["counterpart_error"] for record in scored),
        "heldout_authorized": gate_passed,
        "decision": "advance_to_frozen_heldout" if gate_passed else "stop_without_optimization",
    }
    result_dir = ROOT / "results"
    atomic_bytes(result_dir / "trials.jsonl", "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in scored).encode())
    atomic_json(result_dir / "development-gate.json", gate)
    output = io.StringIO(); fields = ["topic", "condition", "expected_answer", "selected_target",
        "semantic_success", "counterpart_error", "control_target_selection", "classification",
        "explicit_hidden_structure_mention", "elapsed_seconds", "input_tokens", "output_tokens",
        "reasoning_output_tokens"]
    writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader()
    for record in scored:
        usage = record["runner"].get("aggregate_usage") or {}
        writer.writerow({
            "topic": record["topic"], "condition": record["condition"],
            "expected_answer": record["expected_answer"], "selected_target": record["selected_target"],
            "semantic_success": record["semantic_success"], "counterpart_error": record["counterpart_error"],
            "control_target_selection": record["control_target_selection"],
            "classification": record["classification"],
            "explicit_hidden_structure_mention": record["explicit_hidden_structure_mention"],
            "elapsed_seconds": record["runner"]["elapsed_seconds"],
            "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
            "reasoning_output_tokens": usage.get("reasoning_output_tokens"),
        })
    atomic_bytes(result_dir / "answer-identity.csv", output.getvalue().encode())
    control_counts = Counter(record["classification"] for record in controls)
    atomic_json(result_dir / "control-summary.json", {
        "controls": len(controls), "classification_counts": dict(sorted(control_counts.items())),
        "target_answer_selections": len(control_targets), "target_answer_trial_ids": control_targets,
    })
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()

