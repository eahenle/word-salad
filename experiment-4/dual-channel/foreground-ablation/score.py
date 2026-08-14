#!/usr/bin/env python3
"""Score frozen 4C.1 responses by preregistered answer identity."""

from __future__ import annotations

import csv
import io
import json
import re

from runtime import ROOT, atomic_bytes, atomic_json


TARGETS = ("Rowan", "Mira")
STRUCTURE_TERMS = ("hidden", "encoded", "encoding", "interleav", "subsequence", "every nth",
                   "sparse", "scrambl", "shuffl", "word salad", "random order", "jumbled")


def words(response: str) -> list[str]:
    return re.findall(r"[A-Za-z]+", response.lower())


def select_target(response: str) -> tuple[str | None, list[str]]:
    tokens = words(response); present = [target for target in TARGETS if target.lower() in tokens]
    return (present[0] if len(present) == 1 else None), present


def score_one(record: dict) -> dict:
    response = record["response"]; selected, present = select_target(response)
    expected = record["expected_answer"]; error = record["runner"]["error"]
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
        classification = "neither_target"
    lower = response.lower()
    scored = dict(record); scored.update({
        "strict_exact_success": expected is not None and response == expected,
        "normalized_exact_success": expected is not None and " ".join(words(response)) == expected.lower(),
        "semantic_success": semantic, "selected_target": selected, "target_names_present": present,
        "counterpart_error": counterpart,
        "control_target_selection": expected is None and selected in TARGETS,
        "classification": classification,
        "clarification_request": any(phrase in lower for phrase in ("what would you like", "please provide", "could you clarify")),
        "explicit_structure_language": any(term in lower for term in STRUCTURE_TERMS),
        "explicit_hidden_or_encoded_mention": any(term in lower for term in ("hidden", "encoded", "encoding")),
    })
    return scored


def main() -> None:
    execution = json.loads((ROOT / "development/results/execution-freeze.json").read_text())
    if execution.get("completed") != 9:
        raise RuntimeError("all nine responses must be frozen before scoring")
    records = [json.loads(line) for line in (ROOT / "development/results/trials-unscored.jsonl").read_text().splitlines()]
    if len(records) != 9:
        raise RuntimeError("unscored cohort is incomplete")
    scored = [score_one(record) for record in records]
    by_topic = {topic: {row["condition"]: row for row in scored if row["topic"] == topic}
                for topic in sorted({row["topic"] for row in scored})}
    complete_topics = [topic for topic, cells in by_topic.items()
                       if cells["hidden_a"]["semantic_success"] and cells["hidden_b"]["semantic_success"]]
    controls = [row for row in scored if row["condition"] == "scrambled"]
    control_targets = [row["trial_id"] for row in controls if row["control_target_selection"]]
    gate_passed = len(complete_topics) >= 2 and not control_targets
    expected_individuals = sum(row["semantic_success"] for row in scored if row["expected_answer"])
    if control_targets:
        outcome = "outcome_3_control_contamination"
    elif gate_passed:
        outcome = "outcome_1_recovery_after_decoherence"
    elif expected_individuals == 0:
        outcome = "outcome_2_no_recovery_after_decoherence"
    else:
        outcome = "outcome_4_partial_recovery"
    gate = {
        "passed": gate_passed, "outcome": outcome,
        "expected_hidden_answers": expected_individuals, "hidden_signal_trials": 6,
        "complete_ab_pairs": len(complete_topics), "complete_ab_pair_topics": complete_topics,
        "required_complete_ab_pairs": 2,
        "scrambled_control_target_selections": len(control_targets),
        "scrambled_control_target_trial_ids": control_targets,
        "required_scrambled_control_target_selections": 0,
        "counterpart_errors": sum(row["counterpart_error"] for row in scored),
        "additional_permutation_replication_preregistered": False,
        "decision": "freeze_initial_cohort_before_any_replication",
    }
    atomic_bytes(ROOT / "results/trials.jsonl", "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in scored).encode())
    atomic_json(ROOT / "results/development-gate.json", gate)
    output = io.StringIO(); fields = ["topic", "condition", "expected_answer", "selected_target",
        "semantic_success", "counterpart_error", "control_target_selection", "classification",
        "clarification_request", "explicit_structure_language", "explicit_hidden_or_encoded_mention",
        "elapsed_seconds", "input_tokens", "output_tokens", "reasoning_output_tokens"]
    writer = csv.DictWriter(output, fields, lineterminator="\n"); writer.writeheader()
    for row in scored:
        usage = row["runner"].get("aggregate_usage") or {}
        writer.writerow({"topic": row["topic"], "condition": row["condition"],
            "expected_answer": row["expected_answer"], "selected_target": row["selected_target"],
            "semantic_success": row["semantic_success"], "counterpart_error": row["counterpart_error"],
            "control_target_selection": row["control_target_selection"], "classification": row["classification"],
            "clarification_request": row["clarification_request"],
            "explicit_structure_language": row["explicit_structure_language"],
            "explicit_hidden_or_encoded_mention": row["explicit_hidden_or_encoded_mention"],
            "elapsed_seconds": row["runner"]["elapsed_seconds"],
            "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
            "reasoning_output_tokens": usage.get("reasoning_output_tokens")})
    atomic_bytes(ROOT / "results/answer-identity.csv", output.getvalue().encode())
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()

