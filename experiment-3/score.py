#!/usr/bin/env python3
"""Post-freeze answer-identity scoring for Experiment 3."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from runtime import EFFORTS, MODELS, cell_slug


OBJECTS = ("brass key", "silver coin", "glass marble")
COLORS = ("red", "blue", "green")
ANSWER_KEYS = {
    "A": {"brass key": "green", "silver coin": "blue", "glass marble": "green"},
    "B": {"brass key": "green", "silver coin": "red", "glass marble": "green"},
}
DISCOVERY_PATTERNS = (
    r"\bshuffl\w*\b", r"\bscrambl\w*\b", r"\binterleav\w*\b",
    r"\bmultiplex\w*\b", r"\bstride\b", r"\blane(?:s)?\b", r"\bword order\b",
    r"\bevery (?:other|second)\b", r"\bpattern\b",
)
INDETERMINATE_PATTERNS = (
    r"\bcannot determine\b", r"\bcan't determine\b", r"\bcan’t determine\b",
    r"\bnot (?:be )?determined uniquely\b", r"\bno unique (?:answer|result)\b",
    r"\bplease resend\b",
)


def extract_assignments(response: str) -> dict[str, str]:
    text = re.sub(r"[*_`]", "", response.lower())
    colors = "|".join(COLORS)
    assignments = {}
    for obj in OBJECTS:
        match = re.search(
            rf"\b{re.escape(obj)}\b\s*(?:=|:|is(?:\s+in)?|[-–—]>?|→)\s*"
            rf"(?:the\s+)?(?:labeled\s+)?\b({colors})\b",
            text,
        )
        if match:
            assignments[obj] = match.group(1)
    return assignments


def score_record(record: dict) -> dict:
    response = record.get("response", "")
    assignments = extract_assignments(response)
    raw_identity = next(
        (identity for identity, answer in ANSWER_KEYS.items() if assignments == answer), None
    )
    indeterminate = any(re.search(pattern, response, re.I) for pattern in INDETERMINATE_PATTERNS)
    identity = None if record.get("condition") == "all_shuffled" and indeterminate else raw_identity
    expected_identity = record.get("answer_identity")
    expected = ANSWER_KEYS.get(expected_identity)
    semantic = bool(expected and assignments == expected)
    canonical = None if not expected else "; ".join(
        f"{obj} = {expected[obj]}" for obj in OBJECTS
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
    scored.update({
        "assignments": assignments,
        "raw_assignment_identity": raw_identity,
        "observed_answer_identity": identity,
        "indeterminate_claimed": indeterminate,
        "exact_success": bool(canonical is not None and response == canonical),
        "semantic_success": semantic,
        "correct_assignment_count": (
            sum(assignments.get(obj) == expected[obj] for obj in OBJECTS) if expected else None
        ),
        "encoding_discovered_in_final": discovery,
        "completed_response": completed_response,
        "classification": classification,
        "notes": "automatic post-freeze answer-identity score",
    })
    return scored


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records))


def write_blind_packet(path: Path, records: list[dict]) -> None:
    packet = []
    for record in records:
        audit_id = hashlib.sha256(
            ("q3-behavior-audit|" + record["model"] + "|" + record["reasoning"] + "|" + record["neutral_id"]).encode()
        ).hexdigest()[:12]
        packet.append({
            "audit_id": audit_id,
            "response": record.get("response", ""),
            "automatic_assignments": record["assignments"],
            "automatic_observed_answer_identity": record["observed_answer_identity"],
            "automatic_indeterminate_claimed": record["indeterminate_claimed"],
            "automatic_encoding_discovered_in_final": record["encoding_discovered_in_final"],
            "automatic_classification": record["classification"],
        })
    packet.sort(key=lambda row: row["audit_id"])
    write_jsonl(path, packet)


def main() -> None:
    root_default = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root_default)
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--reasoning", required=True, choices=EFFORTS)
    parser.add_argument("--build-anchor", action="store_true")
    args = parser.parse_args()
    root = args.root
    slug = cell_slug(args.model, args.reasoning)
    if args.model == "gpt-5.6-sol" and args.reasoning == "xhigh":
        freeze = root / "results" / "anchor-freeze.json"
    else:
        freeze = root / "results" / "screening-freeze.json"
    if not freeze.exists():
        raise RuntimeError(f"cohort freeze required before scoring: {freeze}")
    cell_dir = root / "results" / "cells" / slug
    source = cell_dir / "trials-unscored.jsonl"
    records = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    scored = [score_record(record) for record in records]
    write_jsonl(cell_dir / "trials-auto-scored.jsonl", scored)
    write_blind_packet(cell_dir / "blind-audit-packet.jsonl", scored)
    if args.build_anchor:
        reused = [
            json.loads(line) for line in (root / "results" / "reused-fixed-sol-xhigh.jsonl").read_text().splitlines()
            if line.strip()
        ]
        fixed_ids = {
            *(f"q{number:04d}" for number in range(1, 11)),
            *(f"q{number:04d}" for number in range(21, 31)),
        }
        fresh_ids = {
            *(f"q{number:04d}" for number in range(41, 51)),
            *(f"q{number:04d}" for number in range(61, 71)),
            "q0081", "q0082", "q0083",
        }
        combined = [record for record in reused if record["neutral_id"] in fixed_ids]
        combined += [record for record in scored if record["neutral_id"] in fresh_ids]
        combined.sort(key=lambda record: record["neutral_id"])
        if len(combined) != 43:
            raise RuntimeError("anchor combined cohort must contain 43 records")
        write_jsonl(root / "results" / "anchor-trials-auto-scored.jsonl", combined)
    print(f"scored {len(scored)} records for {slug}")


if __name__ == "__main__":
    main()
