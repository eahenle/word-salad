#!/usr/bin/env python3
"""Score one frozen density stage and apply its preregistered decision rule."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re

from generate import ROOT
from runtime import atomic_bytes, atomic_json


TARGETS = ("Rowan", "Mira")


def response_words(text): return re.findall(r"[A-Za-z]+", text.lower())


def selected(text):
    tokens = response_words(text); present = [target for target in TARGETS if target.lower() in tokens]
    return (present[0] if len(present) == 1 else None), present


def score(row):
    choice, present = selected(row["response"]); expected = row["expected_answer"]
    semantic = expected is not None and choice == expected
    counterpart = expected is not None and choice in TARGETS and choice != expected
    if row["runner"]["error"]: classification = "timeout" if row["runner"]["timed_out"] else "runner_error"
    elif semantic: classification = "expected_answer"
    elif counterpart: classification = "counterpart_answer"
    elif len(present) == 2: classification = "both_target_names"
    else: classification = "neither_target"
    output = dict(row); output.update({"selected_target": choice, "target_names_present": present,
        "semantic_success": semantic, "counterpart_error": counterpart,
        "control_target_selection": expected is None and choice in TARGETS,
        "strict_exact_success": expected is not None and row["response"] == expected,
        "normalized_exact_success": expected is not None and " ".join(response_words(row["response"])) == expected.lower(),
        "classification": classification})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("density", choices=("d125", "d250"))
    density_id = parser.parse_args().density; stage = ROOT / "development" / density_id
    execution = json.loads((stage / "results/execution-freeze.json").read_text())
    if execution["completed"] != 9: raise RuntimeError("stage is not frozen")
    rows = [score(json.loads(line)) for line in (stage / "results/trials-unscored.jsonl").read_text().splitlines()]
    by_topic = {topic: {row["condition"]: row for row in rows if row["topic"] == topic}
                for topic in sorted({row["topic"] for row in rows})}
    pairs = [topic for topic,cells in by_topic.items() if cells["hidden_a"]["semantic_success"] and cells["hidden_b"]["semantic_success"]]
    controls = [row for row in rows if row["condition"] == "scrambled" and row["control_target_selection"]]
    expected = sum(row["semantic_success"] for row in rows if row["expected_answer"])
    counterparts = sum(row["counterpart_error"] for row in rows)
    if controls: outcome, next_stage = "control_contamination", False
    elif len(pairs) >= 2: outcome, next_stage = "clean_gate_pass", False
    elif expected == 0 and counterparts == 0: outcome, next_stage = "clean_complete_null", density_id == "d125"
    else: outcome, next_stage = "partial_recovery", False
    decision = {"density_id": density_id, "outcome": outcome, "gate_passed": outcome == "clean_gate_pass",
        "expected_hidden_answers": expected, "hidden_signal_trials": 6,
        "complete_ab_pairs": len(pairs), "complete_ab_pair_topics": pairs,
        "scrambled_target_selections": len(controls), "scrambled_target_trial_ids": [row["trial_id"] for row in controls],
        "counterpart_errors": counterparts,
        "next_stage_authorized": next_stage,
        "next_stage": "d250" if next_stage else None}
    atomic_bytes(stage / "results/trials.jsonl", "".join(json.dumps(row, ensure_ascii=False)+"\n" for row in rows).encode())
    atomic_json(stage / "results/development-gate.json", decision)
    output = io.StringIO(); fields = ["topic","condition","expected_answer","selected_target","semantic_success",
        "counterpart_error","control_target_selection","classification","elapsed_seconds","input_tokens","output_tokens","reasoning_output_tokens"]
    writer=csv.DictWriter(output,fields,lineterminator="\n"); writer.writeheader()
    for row in rows:
        usage=row["runner"].get("aggregate_usage") or {}; writer.writerow({"topic":row["topic"],"condition":row["condition"],
            "expected_answer":row["expected_answer"],"selected_target":row["selected_target"],"semantic_success":row["semantic_success"],
            "counterpart_error":row["counterpart_error"],"control_target_selection":row["control_target_selection"],
            "classification":row["classification"],"elapsed_seconds":row["runner"]["elapsed_seconds"],
            "input_tokens":usage.get("input_tokens"),"output_tokens":usage.get("output_tokens"),
            "reasoning_output_tokens":usage.get("reasoning_output_tokens")})
    atomic_bytes(stage / "results/answer-identity.csv", output.getvalue().encode()); print(json.dumps(decision,indent=2))


if __name__ == "__main__": main()
