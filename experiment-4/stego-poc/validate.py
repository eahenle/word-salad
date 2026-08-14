#!/usr/bin/env python3
"""Fail-closed mechanical validation for Experiment 4B stimuli."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from cover_generator import DEFENSES, PAYLOADS, build, normalized_tokens, subsequence_positions


EXPECTED = {"development": 4, "heldout": 20}


def contains(tokens: list[str], payload: list[str]) -> bool:
    try:
        subsequence_positions(tokens, payload)
        return True
    except ValueError:
        return False


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_set(root: Path, set_name: str) -> dict:
    expected = build(set_name)
    assert len(expected) == EXPECTED[set_name]
    assert len({item.neutral_id for item in expected}) == len(expected)
    manifest_path = root / set_name / "manifest.json"
    assert manifest_path.exists(), f"missing {manifest_path}"
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest) == len(expected)
    records = []
    for item in expected:
        document_path = root / set_name / "documents" / f"{item.neutral_id}.txt"
        prompt_path = root / set_name / "prompts" / f"{item.neutral_id}.txt"
        metadata_path = root / set_name / "metadata" / f"{item.neutral_id}.json"
        assert document_path.read_text() == item.document
        assert prompt_path.read_text() == item.prompt
        metadata = json.loads(metadata_path.read_text())
        assert metadata == item.metadata
        assert sha256(document_path) == metadata["document_sha256"]
        assert sha256(prompt_path) == metadata["prompt_sha256"]
        tokens = normalized_tokens(item.document)
        if item.condition.startswith("hidden_"):
            identity = item.hidden_identity
            positions = metadata["signal_positions"]
            assert [tokens[position] for position in positions] == PAYLOADS[identity]
        elif item.condition in {"benign", "scrambled"}:
            assert not contains(tokens, PAYLOADS["A"]), (item.neutral_id, "accidental A subsequence")
            assert not contains(tokens, PAYLOADS["B"]), (item.neutral_id, "accidental B subsequence")
        if item.condition == "scrambled":
            stream = metadata["shuffled_designated_stream"]
            assert Counter(stream) == Counter(PAYLOADS["A"])
            assert stream not in PAYLOADS.values()
            order = metadata["shuffled_sentence_order"]
            assert len(order) > 1 and order != list(range(len(order)))
        records.append({"neutral_id": item.neutral_id, "condition": item.condition,
                        "defense": item.defense, "document_sha256": sha256(document_path),
                        "prompt_sha256": sha256(prompt_path)})
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for item in expected:
        grouped.setdefault((item.topic_id, item.defense), {})[item.condition] = item
    paired_checks = 0
    for key, conditions in grouped.items():
        a = conditions.get("hidden_A"); b = conditions.get("hidden_B")
        if a and b:
            assert Counter(normalized_tokens(a.document)) == Counter(normalized_tokens(b.document)), key
            paired_checks += 1
    return {"set": set_name, "stimuli": len(expected), "paired_equal_bag_checks": paired_checks,
            "manifest_sha256": sha256(manifest_path), "records": records}


def validate(root: Path) -> dict:
    assert Counter(PAYLOADS["A"]) == Counter(PAYLOADS["B"])
    assert PAYLOADS["A"] != PAYLOADS["B"]
    result = {"passed": True, "payload_word_count": len(PAYLOADS["A"]),
              "payload_bag_equal": True, "sets": [validate_set(root, name) for name in EXPECTED]}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = validate(args.root.resolve())
    output = args.root / "results/stimulus-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "sets": [{"set": item["set"], "stimuli": item["stimuli"],
                      "paired_equal_bag_checks": item["paired_equal_bag_checks"]} for item in result["sets"]]}, indent=2))


if __name__ == "__main__":
    main()
