#!/usr/bin/env python3
"""Generate the immutable Experiment 4A uniform-random prompt cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from carrier import (
    GENERATOR_VERSION, minimal_period, order_indices, positions, render, runs,
    shuffled_indices, uniform_mask,
)


SEEDS = tuple(range(1, 21))
CONTROL_SEEDS = tuple(range(1, 6))
PINNED_HASHES = {
    "A": "73bdc92d16b10f7093dfcccb1f49bf43b0f32e7f28f75dc4e6a629ae3b792dbb",
    "B": "7ce6324b1e3661703fa3cd762df0a3628070771b8459eeae9975732c69029ce0",
}


@dataclass(frozen=True)
class Task:
    neutral_id: str
    carrier: str
    condition: str
    payload_identity: str | None
    answer_identity: str | None
    seed: int
    prompt: str
    metadata: dict


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_text(value: str) -> str:
    return sha_bytes(value.encode())


def payloads(root: Path) -> dict[str, list[str]]:
    output = {}
    for identity in ("A", "B"):
        path = root.parent / "experiment-3" / f"payload_{identity.lower()}.txt"
        if sha_bytes(path.read_bytes()) != PINNED_HASHES[identity]:
            raise RuntimeError(f"frozen payload {identity} hash mismatch")
        output[identity] = path.read_text().split()
    if len(output["A"]) != 161 or Counter(output["A"]) != Counter(output["B"]):
        raise RuntimeError("frozen payload length/bag invariant failed")
    return output


def source_metadata(root: Path, identity: str, seed: int) -> dict:
    number = seed if identity == "A" else 20 + seed
    return json.loads((root.parent / "experiment-3" / "metadata" / f"q{number:04d}.json").read_text())


def coordinates() -> list[tuple[str | None, int]]:
    return [(identity, seed) for identity in ("A", "B") for seed in SEEDS] + [
        (None, seed) for seed in CONTROL_SEEDS
    ]


def build_tasks(root: Path) -> list[Task]:
    words = payloads(root)
    canonical = words["A"]
    orders = {identity: order_indices(canonical, ordered) for identity, ordered in words.items()}
    forbidden = {tuple(orders["A"]), tuple(orders["B"])}
    tasks = []
    for number, (identity, seed) in enumerate(coordinates(), 1):
        source = source_metadata(root, identity or "A", seed)
        distractor_indices = source["distractor_source_indices"]
        distractor = [canonical[index] for index in distractor_indices]
        signal_indices = orders[identity] if identity else shuffled_indices(
            len(canonical), seed, "control-signal", forbidden
        )
        signal = [canonical[index] for index in signal_indices]
        mask = uniform_mask(len(canonical), seed)
        serialized = render(mask, signal, distractor)
        prompt = " ".join(serialized)
        signal_positions = positions(mask)
        gaps = [right - left for left, right in zip(signal_positions, signal_positions[1:])]
        run_lengths = runs(mask)
        condition = "signal" if identity else "all_shuffled"
        neutral_id = f"q{number:04d}"
        metadata = {
            "neutral_id": neutral_id,
            "carrier": "uniform",
            "condition": condition,
            "payload_identity": identity,
            "answer_identity": identity if identity else None,
            "seed": seed,
            "lanes": 2,
            "prompt_words": len(serialized),
            "payload_words": len(canonical),
            "signal_word_count": mask.count("S"),
            "distractor_word_count": mask.count("D"),
            "prompt_sha256": sha_text(prompt),
            "carrier_mask": "".join(mask),
            "carrier_sha256": sha_text("".join(mask)),
            "signal_positions": signal_positions,
            "carrier_minimal_period": minimal_period(mask),
            "first_signal_position": signal_positions[0],
            "last_signal_position": signal_positions[-1],
            "adjacent_signal_pairs": sum(gap == 1 for gap in gaps),
            "mean_signal_gap": statistics.fmean(gaps),
            "variance_signal_gap": statistics.pvariance(gaps),
            "max_signal_run": max(length for marker, length in run_lengths if marker == "S"),
            "max_distractor_run": max(length for marker, length in run_lengths if marker == "D"),
            "signal_source_indices": signal_indices,
            "distractor_source_indices": distractor_indices,
            "matched_experiment3_seed": seed,
            "generator_version": GENERATOR_VERSION,
            "mask_rejection_performed": False,
        }
        tasks.append(Task(neutral_id, "uniform", condition, identity, metadata["answer_identity"], seed, prompt, metadata))
    return tasks


def write_tasks(root: Path, tasks: list[Task]) -> None:
    frozen = (root / "results/prompt-freeze.json").exists()
    executed = any((root / "completed").glob("**/*.json")) if (root / "completed").exists() else False
    for task in tasks:
        prompt = root / "uniform/prompts" / f"{task.neutral_id}.txt"
        metadata = root / "uniform/metadata" / f"{task.neutral_id}.json"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        metadata.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(task.metadata, indent=2) + "\n"
        if prompt.exists() and prompt.read_text() != task.prompt:
            raise FileExistsError(f"refusing to overwrite mismatched prompt {prompt}")
        if metadata.exists() and metadata.read_text() != rendered and (frozen or executed):
            raise FileExistsError(f"refusing to overwrite frozen metadata {metadata}")
        prompt.write_text(task.prompt)
        metadata.write_text(rendered)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    tasks = build_tasks(args.root)
    write_tasks(args.root, tasks)
    print(f"wrote or verified {len(tasks)} Experiment 4A prompts")


if __name__ == "__main__":
    main()
