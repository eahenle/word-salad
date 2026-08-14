#!/usr/bin/env python3
"""Deterministic tests for Experiment 3 response-surface scoring."""

from score import ANSWER_KEYS, extract_assignments


CASES = (
    (
        "brass key = green; silver coin = blue; glass marble = green",
        ANSWER_KEYS["A"],
    ),
    (
        "red = empty; blue = silver coin; green = brass key, glass marble",
        ANSWER_KEYS["A"],
    ),
    (
        "red = silver coin; blue = empty; green = brass key and glass marble",
        ANSWER_KEYS["B"],
    ),
    (
        "blue = green; contains brass key and glass marble\n"
        "red = red; contains nothing\n"
        "green = blue; contains silver coin",
        ANSWER_KEYS["A"],
    ),
    (
        "red: blue; glass marble\nblue: green; brass key\n"
        "green: red; silver coin",
        {"brass key": "green", "silver coin": "red", "glass marble": "blue"},
    ),
    (
        "brass key green; silver coin red; glass marble green",
        ANSWER_KEYS["B"],
    ),
    (
        "red = empty; blue = silver coin; green = brass key, silver coin, glass marble",
        {"brass key": "green", "glass marble": "green"},
    ),
)


def main() -> None:
    for response, expected in CASES:
        actual = extract_assignments(response)
        if actual != expected:
            raise AssertionError(f"{response!r}: {actual!r} != {expected!r}")
    print(f"score surface tests passed: {len(CASES)}")


if __name__ == "__main__":
    main()
