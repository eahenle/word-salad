#!/usr/bin/env python3
"""Generate immutable fixed, balanced-jitter, and all-shuffled stimuli."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from carrier import (
    GENERATOR_VERSION,
    balanced_jitter_mask,
    fixed_mask,
    minimal_period,
    order_indices,
    render,
    runs,
    shuffled_indices,
    signal_intervals,
    signal_positions,
)


SEEDS = tuple(range(1, 21))
CONTROL_SEEDS = (1, 2, 3)
PINNED_PAYLOAD_HASHES = {
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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode())


def payloads(root: Path) -> dict[str, list[str]]:
    result = {}
    for identity in ("A", "B"):
        path = root / f"payload_{identity.lower()}.txt"
        if sha256_bytes(path.read_bytes()) != PINNED_PAYLOAD_HASHES[identity]:
            raise RuntimeError(f"payload {identity} differs from frozen Experiment 2")
        result[identity] = path.read_text(encoding="utf-8").split()
    if Counter(result["A"]) != Counter(result["B"]):
        raise RuntimeError("frozen payload A/B bags differ")
    return result


def experiment2_fixed(root: Path, identity: str, seed: int) -> tuple[str, dict]:
    experiment2 = root.parent / "experiment-2"
    number = 40 + seed if identity == "A" else 60 + seed
    source_id = f"r{number:04}"
    prompt = (experiment2 / "prompts" / "constrained" / f"{source_id}.txt").read_text(
        encoding="utf-8"
    )
    metadata = json.loads(
        (experiment2 / "metadata" / "constrained" / f"{source_id}.json").read_text()
    )
    if metadata["prompt_sha256"] != sha256_text(prompt):
        raise RuntimeError(f"frozen Experiment 2 prompt hash mismatch: {source_id}")
    return prompt, metadata


def coordinates() -> list[tuple[str, str | None, int]]:
    output = []
    for carrier in ("fixed", "jitter"):
        for identity in ("A", "B"):
            for seed in SEEDS:
                output.append((carrier, identity, seed))
    for seed in CONTROL_SEEDS:
        output.append(("all-shuffled", None, seed))
    return output


def build_tasks(root: Path) -> list[Task]:
    words = payloads(root)
    canonical = words["A"]
    orders = {identity: order_indices(canonical, value) for identity, value in words.items()}
    forbidden = {tuple(orders["A"]), tuple(orders["B"])}
    tasks = []
    for index, (carrier, identity, seed) in enumerate(coordinates(), start=1):
        source_identity = identity or "A"
        fixed_prompt, source = experiment2_fixed(root, source_identity, seed)
        phase = source["signal_phase"]
        fixed_words = fixed_prompt.split()
        fixed = fixed_mask(len(canonical), phase)
        distractor = [word for marker, word in zip(fixed, fixed_words) if marker == "D"]
        distractor_indices = source["permutations"][1 - phase]
        if distractor != [canonical[position] for position in distractor_indices]:
            raise RuntimeError(f"Experiment 2 distractor extraction mismatch for seed {seed}")

        source_stream_indices = orders.get(identity) if identity else shuffled_indices(
            len(canonical), seed, "all-shuffled-signal", forbidden
        )
        source_stream = [canonical[position] for position in source_stream_indices]
        if carrier == "fixed":
            mask = fixed
            serialized = fixed_words
            condition = "signal"
        else:
            mask = balanced_jitter_mask(len(canonical), seed, phase)
            serialized = render(mask, source_stream, distractor)
            condition = "signal" if carrier == "jitter" else "all_shuffled"
        prompt = " ".join(serialized)
        mask_text = "".join(mask)
        metadata = {
            "neutral_id": f"q{index:04d}",
            "carrier": carrier,
            "condition": condition,
            "payload_identity": identity,
            "answer_identity": identity if condition == "signal" else None,
            "seed": seed,
            "lanes": 2,
            "signal_phase": phase if condition == "signal" else None,
            "nominal_phase": phase,
            "prompt_words": len(serialized),
            "payload_words": len(canonical),
            "signal_word_count": mask.count("S"),
            "distractor_word_count": mask.count("D"),
            "prompt_sha256": sha256_text(prompt),
            "carrier_mask": mask_text,
            "carrier_sha256": sha256_text(mask_text),
            "carrier_minimal_period": minimal_period(mask),
            "first_signal_position": signal_positions(mask)[0],
            "last_signal_position": signal_positions(mask)[-1],
            "signal_interval_counts": dict(sorted(Counter(signal_intervals(mask)).items())),
            "max_signal_run": max(length for marker, length in runs(mask) if marker == "S"),
            "max_distractor_run": max(length for marker, length in runs(mask) if marker == "D"),
            "signal_source_indices": source_stream_indices,
            "distractor_source_indices": distractor_indices,
            "source_experiment2_trial": source["neutral_id"] if carrier == "fixed" else None,
            "source_experiment2_prompt_sha256": source["prompt_sha256"],
            "generator_version": GENERATOR_VERSION,
        }
        tasks.append(Task(
            neutral_id=f"q{index:04d}", carrier=carrier, condition=condition,
            payload_identity=identity, answer_identity=metadata["answer_identity"],
            seed=seed, prompt=prompt, metadata=metadata,
        ))
    return tasks


def write_tasks(root: Path, tasks: Sequence[Task]) -> None:
    frozen = (root / "results" / "prompt-freeze.json").exists()
    executed = any((root / "completed").glob("**/*.json")) if (root / "completed").exists() else False
    for task in tasks:
        prompt = root / "prompts" / task.carrier / f"{task.neutral_id}.txt"
        metadata = root / "metadata" / f"{task.neutral_id}.json"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        metadata.parent.mkdir(parents=True, exist_ok=True)
        rendered_metadata = json.dumps(task.metadata, indent=2) + "\n"
        if prompt.exists() and prompt.read_text(encoding="utf-8") != task.prompt:
            raise FileExistsError(f"refusing to overwrite mismatched prompt {prompt}")
        if metadata.exists() and metadata.read_text(encoding="utf-8") != rendered_metadata:
            if frozen or executed:
                raise FileExistsError(f"refusing to overwrite frozen/executed metadata {metadata}")
        prompt.write_text(task.prompt, encoding="utf-8")
        metadata.write_text(rendered_metadata, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    tasks = build_tasks(args.root)
    write_tasks(args.root, tasks)
    print(f"wrote or verified {len(tasks)} Experiment 3 stimuli")


if __name__ == "__main__":
    main()
