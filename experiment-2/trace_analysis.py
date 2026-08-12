#!/usr/bin/env python3
"""Classify only observable Codex trace behavior after a trial slate completes."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

PATTERNS = {
    "explicit_shuffled_text": (r"\bshuffl\w*\b", r"\bscrambl\w*\b", r"\bword salad\b"),
    "fixed_stride_hypothesis": (
        r"\bstride\b", r"\binterleav\w*\b", r"\bmultiplex\w*\b",
        r"\bevery (?:second|third|fourth|\d+(?:st|nd|rd|th))\b", r"\blane(?:s)?\b",
        r"\bmod\s+\d+\b", r"\[\s*\w*\s*::\s*\d+\s*\]",
    ),
    "candidate_stride_testing": (
        r"\b(?:test|try|check)(?:ing|ed)?\b.{0,80}\bstride\b",
        r"\bfor\b.{0,60}\b(?:stride|step)\b", r"\bmod\s+[2348]\b",
        r"range\([^\n]{0,80}(?:stride|step)",
    ),
    "lexical_reconstruction": (
        r"\breconstruct\w*\b", r"\breorder\w*\b", r"\bword multiset\b",
        r"\bdisentangl\w*\b", r"\bseparat\w*\b.{0,60}\bstream",
    ),
}


def analyze(path: Path) -> dict:
    raw = path.read_bytes()
    events, non_json = [], 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except (json.JSONDecodeError, UnicodeDecodeError):
            non_json += 1
    event_counts = Counter(str(event.get("type", "unknown")) for event in events)
    items = [
        event.get("item", {}) for event in events
        if event.get("type") == "item.completed" and isinstance(event.get("item"), dict)
    ]
    item_counts = Counter(str(item.get("type", "unknown")) for item in items)
    chunks = []
    for event in events:
        item = event.get("item", {})
        if isinstance(item, dict):
            for key in ("text", "command", "aggregated_output", "query"):
                if isinstance(item.get(key), str):
                    chunks.append(item[key])
    observable = "\n".join(chunks)
    flags = {
        name: any(re.search(pattern, observable, re.I | re.S) for pattern in patterns)
        for name, patterns in PATTERNS.items()
    }
    tool_calls = sum(
        count for kind, count in item_counts.items() if kind not in {"agent_message", "reasoning"}
    )
    flags["shell_or_tool_assisted"] = tool_calls > 0
    flags["repeated_reanalysis"] = item_counts.get("reasoning", 0) >= 3 or tool_calls >= 3
    flags["direct_one_pass"] = tool_calls == 0 and event_counts.get("turn.started", 0) <= 1
    if flags["candidate_stride_testing"]:
        strategy = "explicit_testing_of_candidate_strides"
    elif flags["fixed_stride_hypothesis"]:
        strategy = "explicit_fixed_stride_hypothesis"
    elif flags["shell_or_tool_assisted"]:
        strategy = "shell_or_tool_assisted_reconstruction"
    elif flags["lexical_reconstruction"]:
        strategy = "apparent_lexical_reconstruction"
    elif flags["explicit_shuffled_text"]:
        strategy = "explicit_recognition_of_shuffled_text"
    elif flags["direct_one_pass"]:
        strategy = "direct_one_pass_response"
    else:
        strategy = "indeterminate"
    usage = next(
        (event.get("usage") for event in reversed(events) if event.get("type") == "turn.completed"),
        {},
    ) or {}
    return {
        "trace_bytes": len(raw), "trace_lines": len(raw.splitlines()),
        "parsed_events": len(events), "non_json_lines": non_json,
        "model_turns": event_counts.get("turn.started", 0),
        "reasoning_items": item_counts.get("reasoning", 0), "tool_calls": tool_calls,
        "shell_invocations": item_counts.get("command_execution", 0),
        "web_searches": item_counts.get("web_search", 0), "strategy": strategy,
        "strategy_flags": flags, "input_tokens": usage.get("input_tokens"),
        "cached_input_tokens": usage.get("cached_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_tokens": usage.get("reasoning_output_tokens"),
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--trials", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    trials = args.trials or args.root / "results" / "trials.jsonl"
    output = args.output or args.root / "results" / "trace-metrics.jsonl"
    records = [json.loads(line) for line in trials.read_text().splitlines() if line.strip()]
    metrics = []
    for record in records:
        metrics.append({
            "neutral_id": record["neutral_id"], "arm": record["arm"],
            "condition": record["condition"], "payload_identity": record["payload_identity"],
            "lanes": record["lanes"], "seed": record["seed"],
            "observed_answer_identity": record["observed_answer_identity"],
            "semantic_success": record["semantic_success"],
            "elapsed_seconds": record["runner"]["elapsed_seconds"],
            "timed_out": record["runner"]["timed_out"],
            **analyze(args.root / record["trace_file"]),
        })
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in metrics),
        encoding="utf-8",
    )
    print(f"analyzed {len(metrics)} observable traces")


if __name__ == "__main__":
    main()
