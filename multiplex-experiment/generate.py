#!/usr/bin/env python3
"""Deterministic word-level lane construction and invariant checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

GENERATOR_VERSION = "q781-v1"
SUPPORTED_CONDITIONS = (
    "signal",
    "all_shuffled",
    "corrupt_signal",
    "contiguous_shuffled",
)


@dataclass(frozen=True)
class GeneratedTrial:
    prompt: str
    metadata: dict


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


def _corrupt_indices(length: int, fraction: float, *seed_parts: object) -> list[int]:
    if not 0 < fraction <= 1:
        raise ValueError("corrupt_signal requires 0 < corruption_fraction <= 1")
    if length < 2:
        raise ValueError("signal corruption requires at least two words")
    original = list(range(length))
    rng = random.Random(_derived_seed(*seed_parts))
    count = max(2, min(length, round(length * fraction)))
    positions = sorted(rng.sample(range(length), count))
    values = [original[position] for position in positions]
    shuffled = values.copy()
    while shuffled == values:
        rng.shuffle(shuffled)
    corrupted = original.copy()
    for position, value in zip(positions, shuffled):
        corrupted[position] = value
    return corrupted


def generate_trial(
    payload: str,
    *,
    condition: str,
    lanes: int,
    seed: int,
    corruption_fraction: float = 0.0,
) -> GeneratedTrial:
    if condition not in SUPPORTED_CONDITIONS:
        raise ValueError(f"unsupported condition: {condition}")
    if lanes < 1:
        raise ValueError("lanes must be positive")
    if condition == "contiguous_shuffled" and lanes != 1:
        raise ValueError("contiguous_shuffled requires lanes=1")

    words = payload.split()
    if not words:
        raise ValueError("payload is empty")
    original = list(range(len(words)))
    signal_phase = None
    if condition in {"signal", "corrupt_signal"}:
        signal_phase = random.Random(_derived_seed("phase", lanes, seed)).randrange(lanes)

    permutations: list[list[int]] = []
    for lane_index in range(lanes):
        if condition == "signal" and lane_index == signal_phase:
            permutation = original.copy()
        elif condition == "corrupt_signal" and lane_index == signal_phase:
            permutation = _corrupt_indices(
                len(words),
                corruption_fraction,
                "corrupt",
                lanes,
                seed,
                lane_index,
            )
        else:
            permutation = _shuffled_indices(
                len(words), condition, lanes, seed, lane_index
            )
        permutations.append(permutation)

    serialized_words = [
        words[permutations[lane_index][position]]
        for position in range(len(words))
        for lane_index in range(lanes)
    ]
    _validate(
        words=words,
        serialized_words=serialized_words,
        permutations=permutations,
        condition=condition,
        lanes=lanes,
        signal_phase=signal_phase,
    )
    prompt = " ".join(serialized_words)
    metadata = {
        "generator_version": GENERATOR_VERSION,
        "condition": condition,
        "lanes": lanes,
        "seed": seed,
        "signal_phase": signal_phase,
        "corruption_fraction": (
            corruption_fraction if condition == "corrupt_signal" else None
        ),
        "payload_words": len(words),
        "prompt_words": len(serialized_words),
        "permutations": permutations,
    }
    return GeneratedTrial(prompt=prompt, metadata=metadata)


def _validate(
    *,
    words: Sequence[str],
    serialized_words: Sequence[str],
    permutations: Sequence[Sequence[int]],
    condition: str,
    lanes: int,
    signal_phase: int | None,
) -> None:
    original = list(range(len(words)))
    expected = Counter(words)
    for lane in permutations:
        if Counter(words[index] for index in lane) != expected:
            raise AssertionError("lane word multiset differs from payload")

    intact = [index for index, lane in enumerate(permutations) if list(lane) == original]
    if condition == "signal" and intact != [signal_phase]:
        raise AssertionError(f"expected one intact lane at {signal_phase}, got {intact}")
    if condition in {"all_shuffled", "contiguous_shuffled", "corrupt_signal"} and intact:
        raise AssertionError(f"condition {condition} unexpectedly has intact lanes {intact}")

    aggregate = Counter({word: count * lanes for word, count in expected.items()})
    if Counter(serialized_words) != aggregate:
        raise AssertionError("aggregate word multiset differs from N payload copies")
    if condition == "signal":
        if signal_phase is None:
            raise AssertionError("signal phase is missing")
        if list(serialized_words[signal_phase::lanes]) != list(words):
            raise AssertionError("phase extraction does not reproduce the payload")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, default=Path(__file__).with_name("payload.txt"))
    parser.add_argument("--condition", choices=SUPPORTED_CONDITIONS, default="signal")
    parser.add_argument("--lanes", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--corruption-fraction", type=float, default=0.0)
    parser.add_argument("--prompt-out", type=Path)
    parser.add_argument("--metadata-out", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    generated = generate_trial(
        args.payload.read_text(encoding="utf-8").strip(),
        condition=args.condition,
        lanes=args.lanes,
        seed=args.seed,
        corruption_fraction=args.corruption_fraction,
    )
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(generated.prompt, encoding="utf-8")
    else:
        print(generated.prompt)
    if args.metadata_out:
        args.metadata_out.parent.mkdir(parents=True, exist_ok=True)
        args.metadata_out.write_text(
            json.dumps(generated.metadata, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
