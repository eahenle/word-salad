#!/usr/bin/env python3
"""Score one frozen stage using complete three-symbol answer identity."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re

from generate import ROOT, STAGES
from hidden_tasks import ANSWERS
from runtime import atomic_bytes, atomic_json
from validate import validate


ORDER = list(STAGES)
TARGETS = {identity: tuple(token.casefold() for token in answer) for identity, answer in ANSWERS.items()}


def words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z]+", text.casefold()))


def contains(sequence: tuple[str, ...], target: tuple[str, ...]) -> bool:
    length = len(target)
    return any(sequence[index:index + length] == target for index in range(len(sequence) - length + 1))


def score(record: dict) -> dict:
    sequence = words(record["response"])
    hits = [identity for identity, target in TARGETS.items() if contains(sequence, target)]
    selected = hits[0] if len(hits) == 1 else "both" if len(hits) > 1 else None
    expected = record["hidden_identity"]
    expected_text = " ".join(ANSWERS[expected]) if expected else None
    strict = bool(expected_text and record["response"].strip() == expected_text)
    normalized_exact = bool(expected and sequence == TARGETS[expected])
    semantic = bool(expected and selected == expected)
    counterpart = bool(expected and selected in TARGETS and selected != expected)
    control_target = bool(expected is None and selected in TARGETS)
    if semantic:
        classification = "expected_full_state"
    elif counterpart:
        classification = "counterpart_full_state"
    elif control_target:
        classification = "control_target_full_state"
    elif selected == "both":
        classification = "both_target_states"
    elif record["runner"]["timed_out"]:
        classification = "timeout"
    elif record["runner"]["error"]:
        classification = "runner_error"
    else:
        classification = "no_target_full_state"
    return {
        **record,
        "strict_exact_success": strict,
        "normalized_exact_success": normalized_exact,
        "semantic_success": semantic,
        "selected_answer_identity": selected,
        "target_sequences_present": hits,
        "counterpart_error": counterpart,
        "control_target_selection": control_target,
        "classification": classification,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=ORDER)
    args = parser.parse_args()
    validate(require_freeze=True)
    stage_root = ROOT / "stages" / args.stage
    execution = json.loads((stage_root / "results/execution-freeze.json").read_text())
    if execution.get("completed") != 9:
        raise RuntimeError("all nine responses must freeze before scoring")
    records = [score(json.loads(line)) for line in
               (stage_root / "results/trials-unscored.jsonl").read_text().splitlines() if line.strip()]
    if len(records) != 9:
        raise RuntimeError("expected nine records")
    atomic_bytes(stage_root / "results/trials.jsonl", "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    ).encode())
    pairs = []
    for seed in (1, 2, 3):
        a = next(row for row in records if row["seed"] == seed and row["condition"] == "hidden_a")
        b = next(row for row in records if row["seed"] == seed and row["condition"] == "hidden_b")
        pairs.append({"seed": seed, "a_success": a["semantic_success"],
                      "b_success": b["semantic_success"],
                      "complete_pair": a["semantic_success"] and b["semantic_success"]})
    complete_pairs = sum(row["complete_pair"] for row in pairs)
    expected_individuals = sum(row["semantic_success"] for row in records if row["hidden_identity"])
    control_targets = sum(row["control_target_selection"] for row in records)
    counterpart_errors = sum(row["counterpart_error"] for row in records)
    recovery_pass = complete_pairs >= 2 and control_targets == 0
    index = ORDER.index(args.stage)
    next_stage = ORDER[index + 1] if index + 1 < len(ORDER) else None
    advance = bool(control_targets == 0 and not recovery_pass and next_stage)
    gate = {
        "stage": args.stage,
        "expected_individuals": expected_individuals,
        "signal_trials": 6,
        "complete_ab_pairs": complete_pairs,
        "total_pairs": 3,
        "scrambled_target_selections": control_targets,
        "scrambled_controls": 3,
        "counterpart_errors": counterpart_errors,
        "recovery_gate_passed": recovery_pass,
        "control_gate_clean": control_targets == 0,
        "advance_authorized": advance,
        "next_stage": next_stage if advance else None,
        "stopping_reason": (
            "full-state recovery boundary reached" if recovery_pass else
            "scrambled control contamination; audit before proceeding" if control_targets else
            "no recovery at this density; advance to next frozen stage" if next_stage else
            "no recovery through highest frozen density"
        ),
        "pairs": pairs,
    }
    atomic_json(stage_root / "results/development-gate.json", gate)
    fields = ["trial_id", "seed", "condition", "hidden_identity", "expected_answer",
              "response", "selected_answer_identity", "semantic_success", "counterpart_error",
              "control_target_selection", "classification"]
    stream = io.StringIO(); writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader(); writer.writerows({key: row.get(key) for key in fields} for row in records)
    atomic_bytes(stage_root / "results/answer-identity.csv", stream.getvalue().encode())
    analysis = f"""# {args.stage} balanced-density result

- expected full-state answers: {expected_individuals}/6
- complete A/B pairs: {complete_pairs}/3
- scrambled full-target selections: {control_targets}/3
- counterpart full-state errors: {counterpart_errors}
- recovery gate passed: {str(recovery_pass).lower()}
- next stage authorized: {gate['next_stage'] or 'none'}

{gate['stopping_reason']}.
"""
    atomic_bytes(stage_root / "results/analysis.md", analysis.encode())
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
