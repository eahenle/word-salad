#!/usr/bin/env python3
"""Frequency-balanced, equal-word-bag hidden tasks."""

from __future__ import annotations

from collections import Counter, defaultdict, deque


SYMBOLS = ("Kestrel", "Juniper", "Orchid")
PREFIX = "Kestrel Juniper Orchid begin in that order".split()
SWAP = "swap the first and second positions".split()
ROTATE = "rotate the sequence left".split()
BRIDGE = ["afterward"]
SUFFIX = "output the complete sequence".split()

PAYLOAD_A = PREFIX + SWAP + BRIDGE + ROTATE + SUFFIX
PAYLOAD_B = PREFIX + ROTATE + BRIDGE + SWAP + SUFFIX
PLANS = {"A": ("swap", "rotate"), "B": ("rotate", "swap")}


def simulate(plan: tuple[str, ...]) -> tuple[str, ...]:
    state = list(SYMBOLS)
    for operation in plan:
        if operation == "swap":
            state[0], state[1] = state[1], state[0]
        elif operation == "rotate":
            state = state[1:] + state[:1]
        else:
            raise ValueError(operation)
    return tuple(state)


ANSWERS = {identity: simulate(plan) for identity, plan in PLANS.items()}


def source_indices(rendered: list[str]) -> list[int]:
    """Map a same-bag rendering to stable occurrence indices in payload A."""
    queues: dict[str, deque[int]] = defaultdict(deque)
    for index, token in enumerate(PAYLOAD_A):
        queues[token].append(index)
    indices = []
    for token in rendered:
        if not queues[token]:
            raise ValueError(f"rendered task is not a permutation of payload A: {token}")
        indices.append(queues[token].popleft())
    if any(queues.values()):
        raise ValueError("rendered task omitted source occurrences")
    return indices


PAYLOAD_INDICES = {
    "A": list(range(len(PAYLOAD_A))),
    "B": source_indices(PAYLOAD_B),
}


def validate_tasks() -> dict:
    if Counter(PAYLOAD_A) != Counter(PAYLOAD_B):
        raise RuntimeError("A/B payload word bags differ")
    symbol_counts = {
        identity: {symbol: payload.count(symbol) for symbol in SYMBOLS}
        for identity, payload in {"A": PAYLOAD_A, "B": PAYLOAD_B}.items()
    }
    if any(count != 1 for counts in symbol_counts.values() for count in counts.values()):
        raise RuntimeError("candidate symbols must occur exactly once")
    if ANSWERS["A"] == ANSWERS["B"]:
        raise RuntimeError("A/B answers must differ")
    if len(PAYLOAD_A) != 22:
        raise RuntimeError("the frozen hidden task must contain 22 words")
    return {
        "payload_words": len(PAYLOAD_A),
        "word_bags_equal": True,
        "symbol_counts": symbol_counts,
        "answers": {key: " ".join(value) for key, value in ANSWERS.items()},
        "source_indices": PAYLOAD_INDICES,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(validate_tasks(), indent=2))
