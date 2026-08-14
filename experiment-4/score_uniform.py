#!/usr/bin/env python3
"""Post-freeze answer-identity scoring for Experiment 4A."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from runtime import CELLS, cell_slug


OBJECTS = ("brass key", "silver coin", "glass marble")
COLORS = ("red", "blue", "green")
ANSWER_KEYS = {
    "A": {"brass key": "green", "silver coin": "blue", "glass marble": "green"},
    "B": {"brass key": "green", "silver coin": "red", "glass marble": "green"},
}
DISCOVERY = (r"\bshuffl\w*\b", r"\bscrambl\w*\b", r"\binterleav\w*\b", r"\bmultiplex\w*\b",
             r"\bstride\b", r"\blane(?:s)?\b", r"\bword order\b", r"\bevery (?:other|second)\b", r"\bpattern\b")
INDETERMINATE = (r"\bcannot determine\b", r"\bcan't determine\b", r"\bcan’t determine\b",
                 r"\bnot (?:be )?determined uniquely\b", r"\bno unique (?:answer|result)\b", r"\bplease resend\b")


def extract_assignments(response: str) -> dict[str, str]:
    text = re.sub(r"[*_`]", "", response.lower())
    colors = "|".join(COLORS)
    assignments: dict[str, str] = {}
    for obj in OBJECTS:
        matches = list(re.finditer(rf"\b{re.escape(obj)}\b\s*(?:=|:|is(?:\s+in)?|[-–—]>?|→)\s*(?:the\s+)?(?:labeled\s+)?\b({colors})\b", text))
        if matches:
            assignments[obj] = matches[-1].group(1)
    box_pattern = re.compile(rf"(?:^|[;\n])\s*(?:[-+]\s*)?\b({colors})\b(?:\s+box)?\s*(?:=|:)\s*(.*?)(?=(?:[;\n]\s*(?:[-+]\s*)?\b(?:{colors})\b(?:\s+box)?\s*(?:=|:))|\Z)", re.I | re.M | re.S)
    candidates = {obj: set() for obj in OBJECTS}
    for match in box_pattern.finditer(text):
        visible, contents = match.group(1).lower(), match.group(2).strip()
        relabel = re.match(rf"^\b({colors})\b\s*;", contents, re.I)
        if relabel:
            visible, contents = relabel.group(1).lower(), contents[relabel.end():]
        for obj in OBJECTS:
            if re.search(rf"\b{re.escape(obj)}\b", contents):
                candidates[obj].add(visible)
    for obj, values in candidates.items():
        if obj not in assignments and len(values) == 1:
            assignments[obj] = next(iter(values))
    for obj in OBJECTS:
        matches = list(re.finditer(rf"\b{re.escape(obj)}\b[ \t]+(?:is[ \t]+)?(?:in[ \t]+)?(?:the[ \t]+)?\b({colors})\b", text))
        if matches and obj not in assignments:
            assignments[obj] = matches[-1].group(1)
    return assignments


def score(record: dict) -> dict:
    response = record.get("response", "")
    assignments = extract_assignments(response)
    raw_identity = next((identity for identity, answer in ANSWER_KEYS.items() if assignments == answer), None)
    indeterminate = any(re.search(pattern, response, re.I) for pattern in INDETERMINATE)
    identity = None if record["condition"] == "all_shuffled" and indeterminate else raw_identity
    expected_identity = record.get("answer_identity")
    expected = ANSWER_KEYS.get(expected_identity)
    semantic = bool(expected and assignments == expected)
    canonical = None if not expected else "; ".join(f"{obj} = {expected[obj]}" for obj in OBJECTS)
    completed = bool(response) and not record["runner"]["timed_out"] and bool(record["runner"].get("event_type_counts", {}).get("turn.completed"))
    discovery = any(re.search(pattern, response, re.I) for pattern in DISCOVERY)
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
    output = dict(record)
    output.update({"assignments": assignments, "raw_assignment_identity": raw_identity,
                   "observed_answer_identity": identity, "indeterminate_claimed": indeterminate,
                   "exact_success": bool(canonical is not None and response == canonical),
                   "semantic_success": semantic,
                   "correct_assignment_count": sum(assignments.get(obj) == expected[obj] for obj in OBJECTS) if expected else None,
                   "encoding_discovered_in_final": discovery, "completed_response": completed,
                   "classification": classification, "notes": "automatic post-freeze answer-identity score"})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning", required=True)
    args = parser.parse_args()
    if (args.model, args.reasoning) not in CELLS:
        raise RuntimeError("exact preregistered cell required")
    if not (args.root / "uniform/results/execution-freeze.json").exists():
        raise RuntimeError("execution freeze required")
    directory = args.root / "uniform/results/cells" / cell_slug(args.model, args.reasoning)
    records = [json.loads(line) for line in (directory / "trials-unscored.jsonl").read_text().splitlines() if line.strip()]
    scored = [score(record) for record in records]
    (directory / "trials-auto-scored.jsonl").write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in scored))
    print(f"scored {len(scored)} records for {cell_slug(args.model, args.reasoning)}")


if __name__ == "__main__":
    main()
