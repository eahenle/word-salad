#!/usr/bin/env python3
"""Carrier-mask and source-index primitives for Experiment 3."""

from __future__ import annotations

import hashlib
import random
from collections import Counter, defaultdict
from typing import Iterable, Sequence


GENERATOR_VERSION = "q3-balanced-jitter-v1"


def derived_seed(*parts: object) -> int:
    material = GENERATOR_VERSION + "|" + "|".join(str(part) for part in parts)
    return int.from_bytes(hashlib.sha256(material.encode()).digest()[:16], "big")


def occurrence_ids(words: Sequence[str]) -> list[tuple[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    result = []
    for word in words:
        result.append((word, counts[word]))
        counts[word] += 1
    return result


def order_indices(canonical_words: Sequence[str], ordered_words: Sequence[str]) -> list[int]:
    canonical = occurrence_ids(canonical_words)
    index = {occurrence: position for position, occurrence in enumerate(canonical)}
    return [index[occurrence] for occurrence in occurrence_ids(ordered_words)]


def fixed_mask(word_count: int, phase: int) -> tuple[str, ...]:
    if phase not in (0, 1):
        raise ValueError("N=2 phase must be zero or one")
    return tuple("S" if position % 2 == phase else "D" for position in range(2 * word_count))


def balanced_jitter_mask(word_count: int, seed: int, phase: int) -> tuple[str, ...]:
    """Return a boundary-matched 50%-density nonperiodic mask.

    The frozen payload has 161 words, hence 160 intervals. Equal numbers of
    length-1 and length-3 gaps span 320 positions and leave the same final
    distractor boundary as an alternating phase-0 mask. Phase 1 is the mirror.
    """
    if word_count % 2 != 1:
        raise ValueError("balanced boundary-matched construction requires odd word count")
    if phase not in (0, 1):
        raise ValueError("N=2 phase must be zero or one")
    intervals = [1] * ((word_count - 1) // 2) + [3] * ((word_count - 1) // 2)
    random.Random(derived_seed("intervals", seed)).shuffle(intervals)
    signal_positions = [0]
    for interval in intervals:
        signal_positions.append(signal_positions[-1] + interval)
    if signal_positions[-1] != 2 * word_count - 2:
        raise AssertionError("jitter endpoint mismatch")
    mask = ["D"] * (2 * word_count)
    for position in signal_positions:
        mask[position] = "S"
    if phase == 1:
        mask.reverse()
    return tuple(mask)


def signal_positions(mask: Sequence[str]) -> list[int]:
    return [index for index, value in enumerate(mask) if value == "S"]


def signal_intervals(mask: Sequence[str]) -> list[int]:
    positions = signal_positions(mask)
    return [right - left for left, right in zip(positions, positions[1:])]


def runs(mask: Sequence[str]) -> list[tuple[str, int]]:
    output: list[tuple[str, int]] = []
    for value in mask:
        if output and output[-1][0] == value:
            output[-1] = (value, output[-1][1] + 1)
        else:
            output.append((value, 1))
    return output


def minimal_period(mask: Sequence[str]) -> int:
    for period in range(1, len(mask)):
        if len(mask) % period:
            continue
        if all(mask[index] == mask[index % period] for index in range(len(mask))):
            return period
    return len(mask)


def render(mask: Sequence[str], signal: Sequence[str], distractor: Sequence[str]) -> list[str]:
    if Counter(mask) != Counter({"S": len(signal), "D": len(distractor)}):
        raise ValueError("mask and stream sizes differ")
    signal_iter: Iterable[str] = iter(signal)
    distractor_iter: Iterable[str] = iter(distractor)
    return [next(signal_iter) if value == "S" else next(distractor_iter) for value in mask]


def shuffled_indices(word_count: int, seed: int, purpose: str, forbidden: set[tuple[int, ...]]) -> list[int]:
    base = list(range(word_count))
    attempt = 0
    while True:
        candidate = base.copy()
        random.Random(derived_seed(purpose, seed, attempt)).shuffle(candidate)
        if tuple(candidate) not in forbidden:
            return candidate
        attempt += 1
