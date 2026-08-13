#!/usr/bin/env python3
"""Post-hoc behavioral scoring for the paired equal-multiset experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from simulate import OBJECTS, load_protocol, simulate

COLORS = ("red", "blue", "green")
DISCOVERY_PATTERNS = (
    r"\bshuffl\w*\b", r"\bscrambl\w*\b", r"\binterleav\w*\b",
    r"\bmultiplex\w*\b", r"\bstride\b", r"\blane(?:s)?\b",
    r"\bglobally shuffled\b", r"\bword order\b",
)
INDETERMINATE_PATTERNS = (
    r"\bcannot determine\b", r"\bcan't determine\b", r"\bcan’t determine\b",
    r"\bnot (?:be )?determined uniquely\b", r"\bno unique (?:answer|result)\b",
    r"\bunique result cannot\b", r"\bplease resend\b",
)


def extract_assignments(response: str) -> dict[str, str]:
    text = re.sub(r"[*_`]", "", response.lower())
    colors = "|".join(COLORS)
    assignments: dict[str, str] = {}
    for obj in OBJECTS:
        match = re.search(
            rf"\b{re.escape(obj)}\b\s*(?:=|:|is(?:\s+in)?|[-–—]>?|→)\s*"
            rf"(?:the\s+)?(?:labeled\s+)?\b({colors})\b",
            text,
        )
        if match:
            assignments[obj] = match.group(1)
    return assignments


def keys(root: Path) -> dict[str, dict[str, str]]:
    _, operations, orders = load_protocol(root)
    return {identity: simulate(operations, order) for identity, order in orders.items()}


def score_record(record: dict, answer_keys: dict[str, dict[str, str]]) -> dict:
    response = record.get("response", "")
    assignments = extract_assignments(response)
    raw_identity = next(
        (name for name, mapping in answer_keys.items() if assignments == mapping), None
    )
    indeterminate = any(re.search(pattern, response, re.I) for pattern in INDETERMINATE_PATTERNS)
    # Controls sometimes illustrate ambiguity with complete hypothetical examples.
    # Those examples are not an asserted behavioral answer.
    identity = None if record.get("condition") == "all_shuffled" and indeterminate else raw_identity
    expected_identity = record.get("answer_identity")
    expected = answer_keys.get(expected_identity)
    semantic = bool(expected and assignments == expected)
    canonical = None
    if expected_identity:
        canonical = "; ".join(
            f"{obj} = {answer_keys[expected_identity][obj]}" for obj in OBJECTS
        )
    exact = bool(canonical is not None and response == canonical)
    correct_count = (
        sum(assignments.get(obj) == expected[obj] for obj in OBJECTS)
        if expected else None
    )
    runner = record.get("runner", {})
    completed_response = bool(response) and not runner.get("timed_out") and bool(
        runner.get("event_type_counts", {}).get("turn.completed", 0)
    )
    discovery = any(re.search(pattern, response, re.I) for pattern in DISCOVERY_PATTERNS)
    if semantic:
        classification = "expected_answer_success"
    elif identity:
        classification = f"answer_{identity.lower()}"
    elif not response:
        classification = "nonresponse"
    elif indeterminate:
        classification = "indeterminate_or_refusal"
    elif discovery and not assignments:
        classification = "encoding_discovery_without_answer"
    elif assignments:
        classification = "other_assignment"
    else:
        classification = "indeterminate_or_refusal"
    scored = dict(record)
    scored.update(
        {
            "assignments": assignments,
            "raw_assignment_identity": raw_identity,
            "observed_answer_identity": identity,
            "indeterminate_claimed": indeterminate,
            "exact_success": exact,
            "semantic_success": semantic,
            "correct_assignment_count": correct_count,
            "encoding_discovered_in_final": discovery,
            "completed_response": completed_response,
            "classification": classification,
            "notes": "automatic answer-identity score; observable strategy scored separately",
        }
    )
    return scored


def write_blind_packet(records: list[dict], path: Path) -> None:
    packet = []
    for record in records:
        audit_id = hashlib.sha256(
            ("q2-blind-audit|" + record["neutral_id"]).encode()
        ).hexdigest()[:12]
        packet.append({
            "audit_id": audit_id,
            "response": record.get("response", ""),
            "assignments": record["assignments"],
            "raw_assignment_identity": record["raw_assignment_identity"],
            "observed_answer_identity": record["observed_answer_identity"],
            "indeterminate_claimed": record["indeterminate_claimed"],
            "encoding_discovered_in_final": record["encoding_discovered_in_final"],
            "classification": record["classification"],
            "auditor_notes": "",
        })
    packet.sort(key=lambda record: record["audit_id"])
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in packet),
        encoding="utf-8",
    )


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audit-packet", type=Path)
    args = parser.parse_args()
    source = args.input or args.root / "results" / "trials-unscored.jsonl"
    destination = args.output or args.root / "results" / "trials.jsonl"
    records = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    answer_keys = keys(args.root)
    scored = [score_record(record, answer_keys) for record in records]
    destination.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in scored),
        encoding="utf-8",
    )
    audit_packet = args.audit_packet or args.root / "results" / "blind-audit-packet.jsonl"
    write_blind_packet(scored, audit_packet)
    print(f"scored {len(scored)} records by observed A/B answer identity")


if __name__ == "__main__":
    main()
