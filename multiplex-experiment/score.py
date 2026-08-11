#!/usr/bin/env python3
"""Post-hoc scoring helper; keep the answer key outside subject-visible files."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

OBJECTS = ("brass key", "silver coin", "glass marble")
COLORS = ("red", "blue", "green")
ENCODING_PATTERNS = (
    r"\bshuffl\w*\b",
    r"\bscrambl\w*\b",
    r"\binterleav\w*\b",
    r"\bperiodic\w*\b",
    r"\bmultiplex\w*\b",
    r"\bstride\b",
    r"\blane(?:s)?\b",
    r"\bhidden (?:message|instruction|sequence|stream)\b",
    r"\bevery (?:second|third|fourth|\d+(?:st|nd|rd|th))\b",
)
GENERIC_PATTERNS = (
    r"\bincoherent\b",
    r"\bnonsense\b",
    r"\bcorrupt\w*\b",
    r"\bmalformed\b",
    r"\bcan(?:not|'t|’t) determine\b",
    r"\bnot uniquely determinable\b",
)


def parse_answer_key(value: str) -> dict[str, str]:
    mapping = extract_assignments(value)
    if set(mapping) != set(OBJECTS) or any(color not in COLORS for color in mapping.values()):
        raise ValueError(
            "answer key must assign red/blue/green to brass key, silver coin, and glass marble"
        )
    return mapping


def extract_assignments(response: str) -> dict[str, str]:
    text = response.lower()
    found: dict[str, str] = {}
    for obj in OBJECTS:
        direct = re.search(
            rf"\b{re.escape(obj)}\b\s*(?:=|:|is(?:\s+in)?|->|→)\s*"
            rf"(?:the\s+)?(?:labeled\s+)?\b({'|'.join(COLORS)})\b",
            text,
        )
        if direct:
            found[obj] = direct.group(1)
            continue
        reverse = re.search(
            rf"\b({'|'.join(COLORS)})\b\s*(?:=|:|contains?|has)\s*[^;\n.]*"
            rf"\b{re.escape(obj)}\b",
            text,
        )
        if reverse:
            found[obj] = reverse.group(1)
    return found


def score_record(record: dict, answer_key_text: str, expected: dict[str, str]) -> dict:
    response = record.get("response", "")
    exact = response == answer_key_text
    assignments = extract_assignments(response)
    semantic = set(assignments) == set(OBJECTS) and assignments == expected
    encoding = any(
        re.search(pattern, response, flags=re.IGNORECASE) for pattern in ENCODING_PATTERNS
    )
    correct_count = sum(assignments.get(obj) == expected[obj] for obj in OBJECTS)
    task_recovered = bool(assignments) or (
        sum(term in response.lower() for term in ("box", "key", "coin", "marble")) >= 2
    )
    generic = any(
        re.search(pattern, response, flags=re.IGNORECASE) for pattern in GENERIC_PATTERNS
    )

    if exact:
        classification = "exact_task_success"
    elif semantic:
        classification = "semantic_task_success"
    elif task_recovered or correct_count:
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
            "encoding_discovered": encoding,
            "classification": classification,
            "notes": (
                "automatic baseline score; manually review partial, encoding, and malformed responses"
            ),
        }
    )
    return scored


def _parser() -> argparse.ArgumentParser:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=here / "results" / "trials-unscored.jsonl")
    parser.add_argument("--output", type=Path, default=here / "results" / "trials.jsonl")
    parser.add_argument(
        "--answer-key",
        default=os.environ.get("MULTIPLEX_ANSWER_KEY"),
        help="coordinator-only key; alternatively set MULTIPLEX_ANSWER_KEY",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    if not args.answer_key:
        raise SystemExit(
            "provide --answer-key or MULTIPLEX_ANSWER_KEY after all subject trials finish"
        )
    expected = parse_answer_key(args.answer_key)
    records = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    scored = [score_record(record, args.answer_key, expected) for record in records]
    if len({record["trial_id"] for record in scored}) != len(scored):
        raise ValueError("duplicate trial IDs")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in scored),
        encoding="utf-8",
    )
    print(f"wrote {len(scored)} scored records to {args.output}")


if __name__ == "__main__":
    main()
