#!/usr/bin/env python3
"""Merge variant-blind review decisions into scored trials by hashed audit ID."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REVIEW_FIELDS = (
    "exact_success",
    "semantic_success",
    "correct_assignment_count",
    "malformed_object_substitutions",
    "encoding_discovered",
    "classification",
)


def audit_id(neutral_id: str) -> str:
    return hashlib.sha256(("q1b-audit|" + neutral_id).encode("utf-8")).hexdigest()[:12]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trials = read_jsonl(args.trials)
    decisions_list = read_jsonl(args.decisions)
    decisions = {record["audit_id"]: record for record in decisions_list}
    if len(decisions) != len(decisions_list):
        raise ValueError("duplicate blind-audit decision IDs")
    expected = {audit_id(record["neutral_id"]) for record in trials}
    if set(decisions) != expected:
        raise ValueError("blind-audit decisions do not exactly cover scored trials")
    output = []
    overrides = 0
    for trial in trials:
        decision = decisions[audit_id(trial["neutral_id"])]
        merged = dict(trial)
        changed = []
        for field in REVIEW_FIELDS:
            reviewed = decision[f"reviewed_{field}"]
            if reviewed != merged[field]:
                changed.append(field)
            merged[field] = reviewed
        if changed:
            overrides += 1
        note = decision.get("auditor_notes", "").strip()
        merged["notes"] = (
            "independent variant-blind audit applied"
            + (f"; overrides: {', '.join(changed)}" if changed else "; automatic score confirmed")
            + (f"; {note}" if note else "")
        )
        output.append(merged)
    args.output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in output),
        encoding="utf-8",
    )
    print(f"merged {len(output)} blind decisions; records with overrides={overrides}")


if __name__ == "__main__":
    main()
