#!/usr/bin/env python3
"""Deterministically build and simulate equal-multiset Experiment 2 payloads."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


OBJECTS = ("brass key", "silver coin", "glass marble")


def load_protocol(root: Path) -> tuple[str, dict, dict]:
    template = (root / "payload_common.txt").read_text(encoding="utf-8").strip()
    operations = json.loads((root / "operations.json").read_text(encoding="utf-8"))
    orders = json.loads((root / "orders.json").read_text(encoding="utf-8"))
    if template.count("OPERATION_BLOCK") != 1:
        raise ValueError("payload_common.txt must contain one OPERATION_BLOCK marker")
    return template, operations, orders


def build_payload(template: str, operations: dict, order: list[str]) -> str:
    sentences = [
        f"{index}. {operations[name]['sentence']}"
        for index, name in enumerate(order, start=1)
    ]
    return template.replace("OPERATION_BLOCK", " ".join(sentences))


def simulate(operations: dict, order: list[str]) -> dict[str, str]:
    labels = {"red": "physical-red", "blue": "physical-blue", "green": "physical-green"}
    contents = {
        "physical-red": {"brass key"},
        "physical-blue": {"silver coin"},
        "physical-green": {"glass marble"},
    }

    def physical_box(object_name: str) -> str:
        matches = [box for box, objects in contents.items() if object_name in objects]
        if len(matches) != 1:
            raise AssertionError(f"object location invariant failed for {object_name}")
        return matches[0]

    for name in order:
        kind, first, second = operations[name]["operation"]
        if kind == "move_to_object":
            source = physical_box(first)
            target = physical_box(second)
            contents[source].remove(first)
            contents[target].add(first)
        elif kind == "move_to_label":
            source = physical_box(first)
            target = labels[second]
            contents[source].remove(first)
            contents[target].add(first)
        elif kind == "swap_contents":
            first_box, second_box = labels[first], labels[second]
            contents[first_box], contents[second_box] = (
                contents[second_box],
                contents[first_box],
            )
        elif kind == "swap_labels":
            labels[first], labels[second] = labels[second], labels[first]
        else:
            raise ValueError(f"unknown operation kind: {kind}")
        if Counter(obj for objects in contents.values() for obj in objects) != Counter(OBJECTS):
            raise AssertionError(f"object conservation failed after {name}")

    visible_label = {physical: label for label, physical in labels.items()}
    return {obj: visible_label[physical_box(obj)] for obj in OBJECTS}


def validate_and_write(root: Path) -> dict:
    template, operations, orders = load_protocol(root)
    payloads = {
        identity: build_payload(template, operations, order)
        for identity, order in orders.items()
    }
    if Counter(payloads["A"].split()) != Counter(payloads["B"].split()):
        raise AssertionError("A/B whitespace-delimited word multisets differ")
    answers = {
        identity: simulate(operations, order) for identity, order in orders.items()
    }
    if answers["A"] == answers["B"]:
        raise AssertionError("A/B answer keys are not distinct")
    for identity, payload in payloads.items():
        (root / f"payload_{identity.lower()}.txt").write_text(
            payload + "\n", encoding="utf-8"
        )
    report = {
        "word_multisets_equal": True,
        "word_count": len(payloads["A"].split()),
        "payloads_distinct": payloads["A"] != payloads["B"],
        "answers_distinct": True,
        "answers": answers,
    }
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "simulation-validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    report = validate_and_write(args.root)
    print(
        f"validated equal multiset ({report['word_count']} words) and distinct answers"
    )


if __name__ == "__main__":
    main()
