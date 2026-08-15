#!/usr/bin/env python3
"""Score the frozen clean task cohort and apply the reliability gate."""

from __future__ import annotations

import json
import re

from generate_clean import ROOT
from hidden_tasks import ANSWERS
from runtime import atomic_bytes, atomic_json
from validate import validate


TARGETS = {
    identity: tuple(word.casefold() for word in answer)
    for identity, answer in ANSWERS.items()
}


def words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z]+", text.casefold()))


def contains(sequence: tuple[str, ...], target: tuple[str, ...]) -> bool:
    width = len(target)
    return any(sequence[index:index + width] == target for index in range(len(sequence) - width + 1))


def main() -> None:
    validate(require_freeze=True)
    root = ROOT / "cohorts/clean"
    execution = json.loads((root / "results/execution-freeze.json").read_text())
    if execution.get("completed") != 40:
        raise RuntimeError("all 40 clean responses must freeze before scoring")
    records = []
    for line in (root / "results/trials-unscored.jsonl").read_text().splitlines():
        row = json.loads(line)
        sequence = words(row["response"])
        target = TARGETS[row["payload_identity"]]
        records.append({
            **row,
            "normalized_exact_success": sequence == target,
            "semantic_sequence_present": contains(sequence, target),
            "response_words_normalized": list(sequence),
        })
    exact = {
        identity: sum(
            row["normalized_exact_success"]
            for row in records if row["payload_identity"] == identity
        )
        for identity in ("A", "B")
    }
    pass_gate = exact["A"] >= 18 and exact["B"] >= 18
    gate = {
        "cohort": "clean",
        "A_normalized_exact": exact["A"],
        "A_trials": 20,
        "B_normalized_exact": exact["B"],
        "B_trials": 20,
        "aggregate_normalized_exact": exact["A"] + exact["B"],
        "aggregate_trials": 40,
        "gate_passed": pass_gate,
        "advance_scrambled_authorized": pass_gate,
        "failure_action": None if pass_gate else "freeze task v1 and redesign before interference",
    }
    atomic_bytes(root / "results/trials.jsonl", "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in records
    ).encode())
    atomic_json(ROOT / "results/clean-gate.json", gate)
    atomic_bytes(root / "results/analysis.md", (
        "# Clean five-symbol validation\n\n"
        f"- A normalized exact: {exact['A']}/20\n"
        f"- B normalized exact: {exact['B']}/20\n"
        f"- aggregate: {exact['A'] + exact['B']}/40\n"
        f"- reliability gate passed: {str(pass_gate).lower()}\n"
    ).encode())
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
