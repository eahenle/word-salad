#!/usr/bin/env python3
"""Deterministic state simulator for the paired hidden tasks."""

from __future__ import annotations

from hidden_tasks import EXPECTED_ANSWERS, PAYLOADS, PREFIX, SUFFIX


def simulate(words: tuple[str, ...] | list[str]) -> str:
    words = tuple(words)
    if words[: len(PREFIX)] != PREFIX or words[-len(SUFFIX) :] != SUFFIX:
        raise ValueError("invalid task frame")
    operations = words[len(PREFIX) : -len(SUFFIX)]
    try:
        divider = operations.index("afterward")
    except ValueError as exc:
        raise ValueError("missing operation divider") from exc
    chunks = (operations[:divider], operations[divider + 1 :])
    state = list(PREFIX[:3])
    for operation in chunks:
        if len(operation) == 4 and operation[0] == "exchange" and operation[2] == "and":
            left, right = operation[1], operation[3]
            left_index, right_index = state.index(left), state.index(right)
            state[left_index], state[right_index] = state[right_index], state[left_index]
        elif len(operation) == 4 and operation[0] == "relocate" and operation[2] == "beyond":
            item, reference = operation[1], operation[3]
            state.remove(item)
            state.insert(state.index(reference) + 1, item)
        else:
            raise ValueError(f"unknown operation: {operation!r}")
    return state[len(state) // 2]


def validate_answers() -> None:
    observed = {identity: simulate(payload) for identity, payload in PAYLOADS.items()}
    if observed != EXPECTED_ANSWERS:
        raise AssertionError(f"answer-key mismatch: {observed!r}")
    if len(set(observed.values())) != 2:
        raise AssertionError("paired tasks do not have distinct answers")


if __name__ == "__main__":
    validate_answers()
    for identity, payload in PAYLOADS.items():
        print(identity, simulate(payload), " ".join(payload))

