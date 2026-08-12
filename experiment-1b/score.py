#!/usr/bin/env python3
"""Variant-agnostic post-hoc behavioral scoring for Experiment 1A-R/1B."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

OBJECTS = ("brass key", "silver coin", "glass marble")
COLORS = ("red", "blue", "green")
ENCODING_PATTERNS = (
    r"\bshuffl\w*\b",
    r"\b(?:un)?scrambl\w*\b",
    r"\binterleav\w*\b",
    r"\bperiodic\w*\b",
    r"\bmultiplex\w*\b",
    r"\bstride\b",
    r"\blane(?:s)?\b",
    r"\btranspos\w*\b",
    r"\bhidden (?:message|instruction|sequence|stream)\b",
    r"\bevery (?:second|third|fourth|\d+(?:st|nd|rd|th))\b",
    r"\brandomi[sz]\w* word order\b",
    r"\bword order (?:is |was |has been )?(?:corrupt\w*|destroy\w*|lost|randomi[sz]\w*)\b",
    r"\bword order\b.{0,80}\b(?:corrupt\w*|destroy\w*|lost|randomi[sz]\w*)\b",
    r"\b(?:duplicated|repeated) (?:word|instruction|fragment|vocabular|inventory|stream|clause)\w*\b",
)
GENERIC_PATTERNS = (
    r"\bincoherent\b",
    r"\bnonsense\b",
    r"\bcorrupt\w*\b",
    r"\bmalformed\b",
    r"\bcan(?:not|'t|’t) determine\b",
    r"\bnot uniquely determinable\b",
)


def extract_assignments(response: str) -> dict[str, str]:
    text = response.lower()
    found = {}
    colors = "|".join(COLORS)
    for obj in OBJECTS:
        direct = re.search(
            rf"\b{re.escape(obj)}\b\s*(?:=|:|is(?:\s+in)?|->|→)\s*"
            rf"(?:the\s+)?(?:labeled\s+)?\b({colors})\b",
            text,
        )
        if direct:
            found[obj] = direct.group(1)
            continue
        reverse = re.search(
            rf"\b({colors})\b\s*(?:=|:|contains?|has)\s*[^;\n.]*"
            rf"\b{re.escape(obj)}\b",
            text,
        )
        if reverse:
            found[obj] = reverse.group(1)
    return found


def malformed_substitutions(response: str) -> list[str]:
    text = response.lower()
    canonical = set(OBJECTS)
    candidates = set(
        re.findall(r"\b(?:brass|silver|glass)\s+(?:key|coin|marble)\b", text)
    )
    return sorted(candidates - canonical)


def parse_answer_key(value: str) -> dict[str, str]:
    mapping = extract_assignments(value)
    if set(mapping) != set(OBJECTS) or any(color not in COLORS for color in mapping.values()):
        raise ValueError("answer key must assign a valid color to all three canonical objects")
    return mapping


def score_record(record: dict, answer_key_text: str, expected: dict[str, str]) -> dict:
    response = record.get("response", "")
    assignments = extract_assignments(response)
    substitutions = malformed_substitutions(response)
    correct_count = sum(assignments.get(obj) == expected[obj] for obj in OBJECTS)
    exact = response == answer_key_text
    semantic = assignments == expected and set(assignments) == set(OBJECTS)
    encoding = any(re.search(pattern, response, re.IGNORECASE) for pattern in ENCODING_PATTERNS)
    generic = any(re.search(pattern, response, re.IGNORECASE) for pattern in GENERIC_PATTERNS)
    response_lower = response.lower()
    task_recovered = (
        bool(assignments)
        or sum(term in response_lower for term in ("box", "key", "coin", "marble")) >= 2
        or sum(term in response_lower for term in ("brass", "silver", "glass")) >= 2
        or bool(
            re.search(
                r"\b(?:state[- ]tracking|operations?|ordered moves|initial box contents)\b",
                response_lower,
            )
        )
    )
    nonresponse = not bool(response)
    turn_completed = bool(
        record.get("runner", {}).get("event_type_counts", {}).get("turn.completed", 0)
    )
    completed_response = bool(response) and turn_completed and not bool(
        record.get("runner", {}).get("timed_out")
    )

    if exact:
        classification = "exact_task_success"
    elif semantic:
        classification = "semantic_task_success"
    elif nonresponse:
        classification = "nonresponse"
    elif task_recovered or correct_count or substitutions:
        classification = "partial_recovery"
    elif encoding:
        classification = "encoding_discovery_without_task_completion"
    elif generic:
        classification = "generic_response_to_nonsense"
    else:
        classification = "other"

    scored = dict(record)
    scored.update(
        {
            "exact_success": exact,
            "semantic_success": semantic,
            "correct_assignment_count": correct_count,
            "malformed_object_substitutions": substitutions,
            "encoding_discovered": encoding,
            "nonresponse": nonresponse,
            "turn_completed": turn_completed,
            "completed_response": completed_response,
            "classification": classification,
            "notes": "automatic variant-agnostic score; preserve manual audit separately",
        }
    )
    return scored


def write_blind_audit_packet(records: list[dict], path: Path) -> None:
    packet = []
    for record in records:
        audit_id = hashlib.sha256(
            ("q1b-audit|" + record["neutral_id"]).encode("utf-8")
        ).hexdigest()[:12]
        packet.append(
            {
                "audit_id": audit_id,
                "response": record.get("response", ""),
                "exact_success": record["exact_success"],
                "semantic_success": record["semantic_success"],
                "correct_assignment_count": record["correct_assignment_count"],
                "malformed_object_substitutions": record["malformed_object_substitutions"],
                "encoding_discovered": record["encoding_discovered"],
                "classification": record["classification"],
                "auditor_notes": "",
            }
        )
    packet.sort(key=lambda item: item["audit_id"])
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in packet),
        encoding="utf-8",
    )


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=root / "results" / "trials-unscored.jsonl")
    parser.add_argument("--output", type=Path, default=root / "results" / "trials.jsonl")
    parser.add_argument(
        "--audit-packet", type=Path, default=root / "results" / "blind-audit-packet.jsonl"
    )
    parser.add_argument(
        "--answer-key",
        default=os.environ.get("MULTIPLEX_ANSWER_KEY"),
        help="coordinator-only key; alternatively set MULTIPLEX_ANSWER_KEY",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    if not args.answer_key:
        raise SystemExit("provide --answer-key or MULTIPLEX_ANSWER_KEY after subjects finish")
    expected = parse_answer_key(args.answer_key)
    records = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len({record["neutral_id"] for record in records}) != len(records):
        raise ValueError("duplicate neutral IDs")
    scored = [score_record(record, args.answer_key, expected) for record in records]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in scored),
        encoding="utf-8",
    )
    write_blind_audit_packet(scored, args.audit_packet)
    print(f"scored {len(scored)} records and wrote a variant-blind audit packet")


if __name__ == "__main__":
    main()
