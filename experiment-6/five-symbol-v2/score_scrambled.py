#!/usr/bin/env python3
"""Score frozen v2 scrambled controls for either target sequence."""

from __future__ import annotations

import json
import re

from hidden_tasks import ANSWERS
from runtime import ROOT, atomic_bytes, atomic_json


TARGETS = {key: tuple(word.casefold() for word in value) for key, value in ANSWERS.items()}


def words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z]+", text.casefold()))


def contains(sequence: tuple[str, ...], target: tuple[str, ...]) -> bool:
    width = len(target)
    return any(sequence[index:index + width] == target for index in range(len(sequence) - width + 1))


def main() -> None:
    root = ROOT / "cohorts/scrambled/results"
    if json.loads((root / "execution-freeze.json").read_text()).get("completed") != 10:
        raise RuntimeError("all scrambled responses must freeze before scoring")
    records = []
    for line in (root / "trials-unscored.jsonl").read_text().splitlines():
        row = json.loads(line)
        sequence = words(row["response"])
        hits = [identity for identity, target in TARGETS.items() if contains(sequence, target)]
        records.append({
            **row,
            "target_sequences_present": hits,
            "control_target_selection": bool(hits),
            "response_words_normalized": list(sequence),
        })
    targets = sum(row["control_target_selection"] for row in records)
    passed = targets == 0
    gate = {
        "cohort": "scrambled-v2",
        "target_sequence_selections": targets,
        "controls": 10,
        "gate_passed": passed,
        "instrument_validated": passed,
        "advance_buried_signal_authorized": passed,
        "failure_action": None if passed else "freeze task as control-contaminated and stop",
    }
    atomic_bytes(root / "trials.jsonl", "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in records
    ).encode())
    atomic_json(ROOT / "results/scrambled-gate.json", gate)
    atomic_bytes(root / "analysis.md", (
        "# Five-symbol v2 scrambled controls\n\n"
        f"- complete target A/B sequences: {targets}/10\n"
        f"- instrument validated: {str(passed).lower()}\n"
    ).encode())
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
