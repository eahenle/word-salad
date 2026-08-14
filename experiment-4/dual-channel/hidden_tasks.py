#!/usr/bin/env python3
"""Frozen paired hidden tasks for Experiment 4C."""

from __future__ import annotations

from collections import Counter


PREFIX = ("Rowan", "Mira", "Tavi", "are", "initially", "ordered")
EXCHANGE = ("exchange", "Rowan", "and", "Tavi")
RELOCATE = ("relocate", "Mira", "beyond", "Rowan")
SUFFIX = ("output", "the", "central", "name")

PAYLOADS = {
    "A": PREFIX + EXCHANGE + ("afterward",) + RELOCATE + SUFFIX,
    "B": PREFIX + RELOCATE + ("afterward",) + EXCHANGE + SUFFIX,
}

EXPECTED_ANSWERS = {"A": "Rowan", "B": "Mira"}


def validate_payloads() -> None:
    if Counter(PAYLOADS["A"]) != Counter(PAYLOADS["B"]):
        raise AssertionError("paired payloads do not have identical word multisets")
    if len(PAYLOADS["A"]) != 19:
        raise AssertionError("unexpected payload length")


validate_payloads()

