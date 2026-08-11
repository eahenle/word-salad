#!/usr/bin/env python3
"""Paired, deterministic prompt generation for Experiment 1A-R and 1B."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from normalize import NORMALIZATION_VERSION, VARIANTS, normalize_words

GENERATOR_VERSION = "q781-v1"
EXPERIMENT_GENERATOR_VERSION = "q1b-generator-v1"
CONDITIONS = ("signal", "all_shuffled")
LANE_COUNTS = (1, 2, 4, 8)
SEEDS = tuple(range(1, 11))
VARIANT_ORDER = ("original", "lower", "nopunct", "lower_nopunct")


@dataclass(frozen=True)
class GeneratedTask:
    neutral_id: str
    trial_id: str
    variant: str
    condition: str
    lanes: int
    seed: int
    prompt: str
    metadata: dict


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _derived_seed(*parts: object) -> int:
    material = GENERATOR_VERSION + "|" + "|".join(str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return int.from_bytes(digest[:16], "big")


def _shuffled_indices(length: int, *seed_parts: object) -> list[int]:
    if length < 2:
        raise ValueError("a shuffled non-intact lane requires at least two words")
    original = list(range(length))
    permutation = original.copy()
    rng = random.Random(_derived_seed(*seed_parts))
    while permutation == original:
        rng.shuffle(permutation)
    return permutation


def geometry(payload_word_count: int, condition: str, lanes: int, seed: int) -> tuple[int | None, list[list[int]]]:
    if condition not in CONDITIONS:
        raise ValueError(f"unsupported condition: {condition}")
    if lanes not in LANE_COUNTS:
        raise ValueError(f"unsupported lane count: {lanes}")
    original = list(range(payload_word_count))
    signal_phase = None
    if condition == "signal":
        signal_phase = random.Random(_derived_seed("phase", lanes, seed)).randrange(lanes)
    permutations = []
    for lane_index in range(lanes):
        if condition == "signal" and lane_index == signal_phase:
            permutation = original.copy()
        else:
            permutation = _shuffled_indices(
                payload_word_count, condition, lanes, seed, lane_index
            )
        permutations.append(permutation)
    return signal_phase, permutations


def _validate_rendering(
    *,
    source_words: Sequence[str],
    rendered_words: Sequence[str],
    serialized_words: Sequence[str],
    permutations: Sequence[Sequence[int]],
    condition: str,
    lanes: int,
    signal_phase: int | None,
) -> list[int]:
    original_indices = list(range(len(source_words)))
    normalized_payload = list(rendered_words)
    expected = Counter(normalized_payload)
    rendered_equivalent_lanes = []
    for lane_index, permutation in enumerate(permutations):
        lane_words = [rendered_words[index] for index in permutation]
        if Counter(lane_words) != expected:
            raise AssertionError("normalized lane multiset differs from payload")
        if lane_words == normalized_payload and list(permutation) != original_indices:
            rendered_equivalent_lanes.append(lane_index)

    intact_indices = [
        lane_index
        for lane_index, permutation in enumerate(permutations)
        if list(permutation) == original_indices
    ]
    if condition == "signal" and intact_indices != [signal_phase]:
        raise AssertionError(
            f"expected one intact source-index lane at {signal_phase}, got {intact_indices}"
        )
    if condition == "all_shuffled" and intact_indices:
        raise AssertionError(f"all-shuffled trial has intact lanes {intact_indices}")
    if condition == "all_shuffled" and rendered_equivalent_lanes:
        raise AssertionError(
            "normalization made shuffled control lanes render identically to the payload: "
            + ", ".join(str(index) for index in rendered_equivalent_lanes)
        )

    aggregate = Counter(
        {word: count * lanes for word, count in Counter(normalized_payload).items()}
    )
    if Counter(serialized_words) != aggregate:
        raise AssertionError("aggregate normalized word multiset is incorrect")
    if condition == "signal":
        if signal_phase is None:
            raise AssertionError("signal phase is missing")
        extracted = list(serialized_words[signal_phase::lanes])
        if extracted != normalized_payload:
            raise AssertionError("normalized signal extraction differs from payload")
    return rendered_equivalent_lanes


def task_index(variant: str, condition: str, lanes: int, seed: int) -> int:
    if variant not in VARIANT_ORDER:
        raise ValueError(f"unknown variant: {variant}")
    if condition not in CONDITIONS or lanes not in LANE_COUNTS or seed not in SEEDS:
        raise ValueError("trial coordinates are outside the fixed Experiment 1B slate")
    variant_offset = VARIANT_ORDER.index(variant) * len(CONDITIONS) * len(LANE_COUNTS) * len(SEEDS)
    condition_offset = CONDITIONS.index(condition) * len(LANE_COUNTS) * len(SEEDS)
    lane_offset = LANE_COUNTS.index(lanes) * len(SEEDS)
    return variant_offset + condition_offset + lane_offset + SEEDS.index(seed) + 1


def generate_task(
    payload: str, *, variant: str, condition: str, lanes: int, seed: int
) -> GeneratedTask:
    source_words = payload.split()
    if not source_words:
        raise ValueError("payload is empty")
    rendered_words = normalize_words(source_words, variant)
    signal_phase, permutations = geometry(len(source_words), condition, lanes, seed)
    serialized_words = [
        rendered_words[permutations[lane_index][position]]
        for position in range(len(source_words))
        for lane_index in range(lanes)
    ]
    rendered_equivalent_lanes = _validate_rendering(
        source_words=source_words,
        rendered_words=rendered_words,
        serialized_words=serialized_words,
        permutations=permutations,
        condition=condition,
        lanes=lanes,
        signal_phase=signal_phase,
    )
    prompt = " ".join(serialized_words)
    normalized_payload = " ".join(rendered_words)
    index = task_index(variant, condition, lanes, seed)
    neutral_id = f"q{index:04d}"
    trial_id = f"{neutral_id}"
    geometry_hash = sha256_text(json.dumps(permutations, separators=(",", ":")))
    metadata = {
        "neutral_id": neutral_id,
        "trial_id": trial_id,
        "variant": variant,
        "condition": condition,
        "lanes": lanes,
        "seed": seed,
        "signal_phase": signal_phase,
        "intact_lane_index": signal_phase,
        "payload_words": len(source_words),
        "prompt_words": len(serialized_words),
        "source_payload_sha256": sha256_text(payload),
        "normalized_payload_sha256": sha256_text(normalized_payload),
        "prompt_sha256": sha256_text(prompt),
        "geometry_sha256": geometry_hash,
        "permutations": permutations,
        "rendered_equivalent_nonintact_lanes": rendered_equivalent_lanes,
        "generator_version": GENERATOR_VERSION,
        "experiment_generator_version": EXPERIMENT_GENERATOR_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
    }
    return GeneratedTask(
        neutral_id=neutral_id,
        trial_id=trial_id,
        variant=variant,
        condition=condition,
        lanes=lanes,
        seed=seed,
        prompt=prompt,
        metadata=metadata,
    )


def build_tasks(payload: str, variants: Sequence[str] = VARIANT_ORDER) -> list[GeneratedTask]:
    return [
        generate_task(
            payload,
            variant=variant,
            condition=condition,
            lanes=lanes,
            seed=seed,
        )
        for variant in variants
        for condition in CONDITIONS
        for lanes in LANE_COUNTS
        for seed in SEEDS
    ]


def write_tasks(root: Path, tasks: Sequence[GeneratedTask]) -> None:
    for task in tasks:
        prompt_dir = root / "prompts" / task.variant
        metadata_dir = root / "metadata" / task.variant
        prompt_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = prompt_dir / f"{task.neutral_id}.txt"
        metadata_path = metadata_dir / f"{task.neutral_id}.json"
        expected_metadata = json.dumps(task.metadata, indent=2) + "\n"
        if prompt_path.exists() and prompt_path.read_text(encoding="utf-8") != task.prompt:
            raise FileExistsError(f"refusing to replace mismatched prompt: {prompt_path}")
        if metadata_path.exists() and metadata_path.read_text(encoding="utf-8") != expected_metadata:
            raise FileExistsError(f"refusing to replace mismatched metadata: {metadata_path}")
        prompt_path.write_text(task.prompt, encoding="utf-8")
        metadata_path.write_text(expected_metadata, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, default=root / "payload.txt")
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument(
        "--variants", nargs="+", choices=VARIANT_ORDER, default=list(VARIANT_ORDER)
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    payload = args.payload.read_text(encoding="utf-8").strip()
    tasks = build_tasks(payload, args.variants)
    write_tasks(args.root, tasks)
    print(f"wrote or verified {len(tasks)} paired prompts")


if __name__ == "__main__":
    main()
