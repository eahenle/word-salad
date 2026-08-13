#!/usr/bin/env python3
"""Merge condition-blind Experiment 2 review and recompute hidden-key outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from score import keys

REVIEW_FIELDS = (
    "assignments",
    "raw_assignment_identity",
    "observed_answer_identity",
    "indeterminate_claimed",
    "encoding_discovered_in_final",
    "classification",
)


def audit_id(neutral_id: str) -> str:
    return hashlib.sha256(("q2-blind-audit|" + neutral_id).encode()).hexdigest()[:12]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--trials", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trials, decisions_list = read_jsonl(args.trials), read_jsonl(args.decisions)
    decisions = {record["audit_id"]: record for record in decisions_list}
    if len(decisions) != len(decisions_list):
        raise ValueError("duplicate blind-audit IDs")
    expected_ids = {audit_id(record["neutral_id"]) for record in trials}
    if set(decisions) != expected_ids:
        raise ValueError("blind-audit decisions do not exactly cover scored trials")
    answer_keys = keys(args.root)
    output, override_count = [], 0
    for trial in trials:
        decision = decisions[audit_id(trial["neutral_id"])]
        merged, changed = dict(trial), []
        for field in REVIEW_FIELDS:
            reviewed = decision[f"reviewed_{field}"]
            if reviewed != merged[field]:
                changed.append(field)
            merged[field] = reviewed
        expected_identity = merged.get("answer_identity")
        expected = answer_keys.get(expected_identity)
        assignments = merged["assignments"] or {}
        merged["assignments"] = assignments
        merged["semantic_success"] = bool(expected and assignments == expected)
        merged["correct_assignment_count"] = (
            sum(assignments.get(obj) == color for obj, color in expected.items())
            if expected else None
        )
        if merged["semantic_success"]:
            merged["classification"] = "expected_answer_success"
        elif merged["observed_answer_identity"]:
            merged["classification"] = f"answer_{merged['observed_answer_identity'].lower()}"
        if changed:
            override_count += 1
        note = decision.get("auditor_notes", "").strip()
        merged["notes"] = (
            "independent condition-blind audit applied"
            + (f"; overrides: {', '.join(changed)}" if changed else "; automatic score confirmed")
            + (f"; {note}" if note else "")
        )
        output.append(merged)
    args.output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in output)
    )
    print(f"merged {len(output)} blind decisions; records with overrides={override_count}")


if __name__ == "__main__":
    main()
