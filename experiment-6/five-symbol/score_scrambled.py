#!/usr/bin/env python3
"""Score frozen N=1 scrambled controls and freeze the instrument gate."""

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
    clean_gate = json.loads((ROOT / "results/clean-gate.json").read_text())
    if not clean_gate.get("gate_passed"):
        raise RuntimeError("clean gate did not pass")
    root = ROOT / "cohorts/scrambled"
    execution = json.loads((root / "results/execution-freeze.json").read_text())
    if execution.get("completed") != 10:
        raise RuntimeError("all 10 scrambled responses must freeze before scoring")
    records = []
    for line in (root / "results/trials-unscored.jsonl").read_text().splitlines():
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
    pass_gate = targets == 0
    gate = {
        "cohort": "scrambled",
        "target_sequence_selections": targets,
        "controls": 10,
        "gate_passed": pass_gate,
        "instrument_validated": pass_gate,
        "advance_buried_signal_authorized": pass_gate,
        "failure_action": None if pass_gate else "freeze instrument as control-contaminated and stop",
    }
    atomic_bytes(root / "results/trials.jsonl", "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in records
    ).encode())
    atomic_json(ROOT / "results/scrambled-gate.json", gate)
    atomic_bytes(root / "results/analysis.md", (
        "# Scrambled N=1 control\n\n"
        f"- target A/B full-state sequences: {targets}/10\n"
        f"- instrument gate passed: {str(pass_gate).lower()}\n"
    ).encode())
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
