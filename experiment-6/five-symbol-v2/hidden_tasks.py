#!/usr/bin/env python3
"""Unambiguous equal-bag task using two overlapping positional swaps."""

from __future__ import annotations

from collections import Counter, defaultdict, deque


SYMBOLS = ("Aster", "Birch", "Cobalt", "Dune", "Ember")
PREFIX = (
    "Aster Birch Cobalt Dune Ember begin in this left-to-right order. Position one "
    "is the leftmost position. After each swap, count positions again from the left. "
    "Perform these swaps in the stated order:"
).split()
FIRST = ["First,"]
THEN = ["Then,"]
SWAP_14 = "swap the items at positions one and four.".split()
SWAP_12 = "swap the items at positions one and two.".split()
SUFFIX = (
    "Reply with exactly the five names in final left-to-right order and no other words."
).split()

PAYLOAD_A = PREFIX + FIRST + SWAP_14 + THEN + SWAP_12 + SUFFIX
PAYLOAD_B = PREFIX + FIRST + SWAP_12 + THEN + SWAP_14 + SUFFIX
PLANS = {"A": ("swap14", "swap12"), "B": ("swap12", "swap14")}


def simulate(plan: tuple[str, ...]) -> tuple[str, ...]:
    state = list(SYMBOLS)
    for operation in plan:
        if operation == "swap14":
            state[0], state[3] = state[3], state[0]
        elif operation == "swap12":
            state[0], state[1] = state[1], state[0]
        else:
            raise ValueError(operation)
    return tuple(state)


ANSWERS = {identity: simulate(plan) for identity, plan in PLANS.items()}


def source_indices(rendered: list[str]) -> list[int]:
    queues: dict[str, deque[int]] = defaultdict(deque)
    for index, token in enumerate(PAYLOAD_A):
        queues[token].append(index)
    indices = []
    for token in rendered:
        if not queues[token]:
            raise ValueError(f"not a permutation of payload A: {token}")
        indices.append(queues[token].popleft())
    if any(queues.values()):
        raise ValueError("rendered task omitted source occurrences")
    return indices


PAYLOAD_INDICES = {"A": list(range(len(PAYLOAD_A))), "B": source_indices(PAYLOAD_B)}


def validate_tasks() -> dict:
    if Counter(PAYLOAD_A) != Counter(PAYLOAD_B):
        raise RuntimeError("A/B word bags differ")
    counts = {
        identity: {symbol: payload.count(symbol) for symbol in SYMBOLS}
        for identity, payload in {"A": PAYLOAD_A, "B": PAYLOAD_B}.items()
    }
    if any(count != 1 for values in counts.values() for count in values.values()):
        raise RuntimeError("candidate symbols must occur once")
    if ANSWERS["A"] == ANSWERS["B"]:
        raise RuntimeError("A/B answers must differ")
    return {
        "payload_words": len(PAYLOAD_A),
        "word_bags_equal": True,
        "symbols": list(SYMBOLS),
        "symbol_counts": counts,
        "plans": {key: list(value) for key, value in PLANS.items()},
        "answers": {key: " ".join(value) for key, value in ANSWERS.items()},
        "target_space_size": 120,
        "preregistered_target_fraction": 2 / 120,
        "source_indices": PAYLOAD_INDICES,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate_tasks(), indent=2))
