#!/usr/bin/env python3
"""Uniform-carrier and source-index primitives for Experiment 4A."""

from __future__ import annotations

import hashlib
import random
from collections import Counter, defaultdict
from typing import Iterable, Sequence


GENERATOR_VERSION = "q4-uniform-random-v1"


def derived_seed(*parts: object) -> int:
    material = GENERATOR_VERSION + "|" + "|".join(str(part) for part in parts)
    return int.from_bytes(hashlib.sha256(material.encode()).digest()[:16], "big")


def uniform_mask(word_count: int, seed: int) -> tuple[str, ...]:
    """Sample exactly word_count of 2*word_count positions without rejection."""
    positions = set(random.Random(derived_seed("uniform-mask", seed)).sample(
        range(2 * word_count), word_count
    ))
    return tuple("S" if position in positions else "D" for position in range(2 * word_count))


def occurrence_ids(words: Sequence[str]) -> list[tuple[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    output = []
    for word in words:
        output.append((word, counts[word]))
        counts[word] += 1
    return output


def order_indices(canonical_words: Sequence[str], ordered_words: Sequence[str]) -> list[int]:
    index = {occurrence: position for position, occurrence in enumerate(occurrence_ids(canonical_words))}
    return [index[occurrence] for occurrence in occurrence_ids(ordered_words)]


def shuffled_indices(word_count: int, seed: int, purpose: str, forbidden: set[tuple[int, ...]]) -> list[int]:
    base = list(range(word_count))
    attempt = 0
    while True:
        candidate = base.copy()
        random.Random(derived_seed(purpose, seed, attempt)).shuffle(candidate)
        if tuple(candidate) not in forbidden:
            return candidate
        attempt += 1


def render(mask: Sequence[str], signal: Sequence[str], distractor: Sequence[str]) -> list[str]:
    if Counter(mask) != Counter({"S": len(signal), "D": len(distractor)}):
        raise ValueError("mask and stream sizes differ")
    signal_iter: Iterable[str] = iter(signal)
    distractor_iter: Iterable[str] = iter(distractor)
    return [next(signal_iter) if marker == "S" else next(distractor_iter) for marker in mask]


def positions(mask: Sequence[str], marker: str = "S") -> list[int]:
    return [index for index, value in enumerate(mask) if value == marker]


def runs(mask: Sequence[str]) -> list[tuple[str, int]]:
    output: list[tuple[str, int]] = []
    for marker in mask:
        if output and output[-1][0] == marker:
            output[-1] = (marker, output[-1][1] + 1)
        else:
            output.append((marker, 1))
    return output


def minimal_period(mask: Sequence[str]) -> int:
    for period in range(1, len(mask)):
        if len(mask) % period == 0 and all(mask[i] == mask[i % period] for i in range(len(mask))):
            return period
    return len(mask)
