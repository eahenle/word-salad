#!/usr/bin/env python3
"""Mechanically validate Experiment 2 prompt pairing and lane invariants."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from generate import ARMS, build_tasks, occurrence_ids, payloads_for_arm, sha256_text, write_tasks


def validate(root: Path) -> dict:
    tasks = build_tasks(root)
    write_tasks(root, tasks)
    by_coordinate = {
        (task.arm, task.condition, task.payload_identity, task.lanes, task.seed): task
        for task in tasks
    }
    paired = 0
    for arm in ARMS:
        payloads, _ = payloads_for_arm(root, arm)
        words = {identity: payload.split() for identity, payload in payloads.items()}
        if Counter(words["A"]) != Counter(words["B"]):
            raise AssertionError(f"{arm} payload bags differ")
        canonical = occurrence_ids(words["A"])
        canonical_words = [word for word, _ in canonical]
        ids = {identity: occurrence_ids(value) for identity, value in words.items()}
        canonical_index = {occ: position for position, occ in enumerate(canonical)}
        order = {
            identity: [canonical_index[occ] for occ in occurrences]
            for identity, occurrences in ids.items()
        }
        coherent_strings = {tuple(words["A"]), tuple(words["B"])}
        for task in [candidate for candidate in tasks if candidate.arm == arm]:
            stored = (root / "prompts" / arm / f"{task.neutral_id}.txt").read_text(
                encoding="utf-8"
            )
            if stored != task.prompt or sha256_text(stored) != task.metadata["prompt_sha256"]:
                raise AssertionError(f"stored prompt mismatch: {task.neutral_id}")
            if Counter(task.prompt.split()) != Counter(
                {word: count * task.lanes for word, count in Counter(words["A"]).items()}
            ):
                raise AssertionError(f"aggregate bag mismatch: {task.neutral_id}")
            lanes = [task.prompt.split()[phase::task.lanes] for phase in range(task.lanes)]
            if task.condition == "clean":
                if lanes[0] != words[task.payload_identity]:
                    raise AssertionError(f"clean payload mismatch: {task.neutral_id}")
            elif task.condition == "signal":
                phase = task.metadata["signal_phase"]
                if lanes[phase] != words[task.payload_identity]:
                    raise AssertionError(f"signal extraction mismatch: {task.neutral_id}")
                other = "B" if task.payload_identity == "A" else "A"
                mate = by_coordinate[(arm, "signal", other, task.lanes, task.seed)]
                mate_lanes = [mate.prompt.split()[p::task.lanes] for p in range(task.lanes)]
                for lane in range(task.lanes):
                    if lane != phase and lanes[lane] != mate_lanes[lane]:
                        raise AssertionError(
                            f"paired distractor differs: {task.neutral_id} lane {lane}"
                        )
                if Counter(task.prompt.split()) != Counter(mate.prompt.split()):
                    raise AssertionError(f"paired signal bags differ: {task.neutral_id}")
                paired += task.payload_identity == "A"
            else:
                if any(tuple(lane) in coherent_strings for lane in lanes):
                    raise AssertionError(f"coherent lane in all-shuffled: {task.neutral_id}")
                if any(Counter(lane) != Counter(canonical_words) for lane in lanes):
                    raise AssertionError(f"lane bag mismatch: {task.neutral_id}")
    report = {
        "trials_validated": len(tasks),
        "arms": list(ARMS),
        "paired_signal_stimulus_pairs": paired,
        "payload_word_multiset_equal": True,
        "aggregate_word_multiset_equal_within_pairs": True,
        "paired_distractor_lanes_byte_equal": True,
        "signal_extraction_valid": True,
        "all_shuffled_contains_no_a_or_b_lane": True,
        "stored_prompt_hashes_valid": True,
    }
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "prompt-validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    report = validate(args.root)
    print(
        f"validated {report['trials_validated']} prompts and "
        f"{report['paired_signal_stimulus_pairs']} exact A/B pairs"
    )


if __name__ == "__main__":
    main()
