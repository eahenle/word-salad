#!/usr/bin/env python3
"""Score v2 clean responses against the frozen exact-output gate."""

from __future__ import annotations

import json
import re

from hidden_tasks import ANSWERS
from runtime import ROOT, atomic_bytes, atomic_json


TARGETS = {key: tuple(word.casefold() for word in value) for key, value in ANSWERS.items()}


def words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z]+", text.casefold()))


def main() -> None:
    root = ROOT / "cohorts/clean/results"
    execution = json.loads((root / "execution-freeze.json").read_text())
    if execution.get("completed") != 40:
        raise RuntimeError("all 40 responses must freeze before scoring")
    records = []
    for line in (root / "trials-unscored.jsonl").read_text().splitlines():
        row = json.loads(line)
        sequence = words(row["response"])
        target = TARGETS[row["payload_identity"]]
        records.append({
            **row,
            "normalized_exact_success": sequence == target,
            "response_words_normalized": list(sequence),
        })
    exact = {
        identity: sum(
            row["normalized_exact_success"]
            for row in records if row["payload_identity"] == identity
        )
        for identity in ("A", "B")
    }
    passed = exact["A"] >= 18 and exact["B"] >= 18
    gate = {
        "cohort": "clean-v2",
        "A_normalized_exact": exact["A"],
        "A_trials": 20,
        "B_normalized_exact": exact["B"],
        "B_trials": 20,
        "aggregate_normalized_exact": exact["A"] + exact["B"],
        "aggregate_trials": 40,
        "gate_passed": passed,
        "advance_scrambled_authorized": passed,
        "failure_action": None if passed else "freeze task v2 and stop task development",
    }
    atomic_bytes(root / "trials.jsonl", "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in records
    ).encode())
    atomic_json(ROOT / "results/clean-gate.json", gate)
    atomic_bytes(root / "analysis.md", (
        "# Five-symbol task v2 clean validation\n\n"
        f"- A normalized exact: {exact['A']}/20\n"
        f"- B normalized exact: {exact['B']}/20\n"
        f"- aggregate: {exact['A'] + exact['B']}/40\n"
        f"- clean gate passed: {str(passed).lower()}\n"
    ).encode())
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
