#!/usr/bin/env python3
"""Post-slate observable trace metrics and strategy classification."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

STRATEGY_PATTERNS = {
    "explicit_shuffled_text": (
        r"\bshuffl\w*\b",
        r"\bscrambl\w*\b",
        r"\bword salad\b",
        r"\bpermut\w*\b",
    ),
    "fixed_stride_hypothesis": (
        r"\bstride\b",
        r"\binterleav\w*\b",
        r"\bmultiplex\w*\b",
        r"\bevery (?:second|third|fourth|\d+(?:st|nd|rd|th))\b",
        r"\blane(?:s)?\b",
    ),
    "candidate_stride_testing": (
        r"\b(?:test|try|check)(?:ing|ed)?\b.{0,80}\bstride",
        r"\bfor\b.{0,60}\b(?:stride|step)\b",
        r"\[\s*\w*\s*::\s*\w+\s*\]",
        r"range\([^\n]{0,80}(?:stride|step)",
    ),
    "lexical_reconstruction": (
        r"\breconstruct\w*\b",
        r"\breorder\w*\b",
        r"\bword multiset\b",
        r"\bsequence\b.{0,60}\boperations?\b",
    ),
}


def _event_text(event: dict) -> str:
    item = event.get("item")
    values = []
    if isinstance(item, dict):
        for key in ("text", "command", "aggregated_output", "path", "query"):
            value = item.get(key)
            if isinstance(value, str):
                values.append(value)
        if item.get("type") == "mcp_tool_call":
            values.append(json.dumps(item, ensure_ascii=False))
    if event.get("type") == "error":
        values.append(json.dumps(event, ensure_ascii=False))
    return "\n".join(values)


def analyze_trace(trace_path: Path) -> dict:
    raw = trace_path.read_bytes()
    events = []
    non_json_lines = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except (json.JSONDecodeError, UnicodeDecodeError):
            non_json_lines += 1
    event_counts = Counter(str(event.get("type", "unknown")) for event in events)
    completed_items = [
        event.get("item", {})
        for event in events
        if event.get("type") == "item.completed" and isinstance(event.get("item"), dict)
    ]
    item_counts = Counter(str(item.get("type", "unknown")) for item in completed_items)
    observable_text = "\n".join(_event_text(event) for event in events)
    flags = {
        name: any(re.search(pattern, observable_text, re.IGNORECASE | re.DOTALL) for pattern in patterns)
        for name, patterns in STRATEGY_PATTERNS.items()
    }
    shell_invocations = item_counts.get("command_execution", 0)
    noncontent_items = {"agent_message", "reasoning"}
    tool_calls = sum(
        count for item_type, count in item_counts.items() if item_type not in noncontent_items
    )
    reasoning_items = item_counts.get("reasoning", 0)
    model_turns = event_counts.get("turn.started", 0)
    flags["shell_or_tool_assisted"] = tool_calls > 0
    flags["repeated_reanalysis"] = reasoning_items >= 3 or tool_calls >= 3
    flags["direct_one_pass"] = (
        tool_calls == 0
        and model_turns <= 1
        and reasoning_items <= 1
        and not any(
            flags[name]
            for name in (
                "explicit_shuffled_text",
                "fixed_stride_hypothesis",
                "candidate_stride_testing",
                "lexical_reconstruction",
            )
        )
    )

    if flags["candidate_stride_testing"]:
        primary = "explicit_testing_of_candidate_strides"
    elif flags["fixed_stride_hypothesis"]:
        primary = "explicit_fixed_stride_hypothesis"
    elif flags["shell_or_tool_assisted"]:
        primary = "shell_or_tool_assisted_reconstruction"
    elif flags["lexical_reconstruction"]:
        primary = "apparent_lexical_reconstruction"
    elif flags["explicit_shuffled_text"]:
        primary = "explicit_recognition_of_shuffled_text"
    elif flags["repeated_reanalysis"]:
        primary = "repeated_self_reanalysis"
    elif flags["direct_one_pass"]:
        primary = "direct_one_pass_response"
    else:
        primary = "indeterminate"

    usage = None
    for event in events:
        if event.get("type") == "turn.completed":
            usage = event.get("usage")
    usage = usage or {}
    return {
        "trace_bytes": len(raw),
        "trace_lines": len(raw.splitlines()),
        "parsed_events": len(events),
        "non_json_lines": non_json_lines,
        "model_turns": model_turns,
        "reasoning_items": reasoning_items,
        "tool_calls": tool_calls,
        "shell_invocations": shell_invocations,
        "event_type_counts": dict(sorted(event_counts.items())),
        "item_type_counts": dict(sorted(item_counts.items())),
        "input_tokens": usage.get("input_tokens"),
        "cached_input_tokens": usage.get("cached_input_tokens"),
        "cache_write_input_tokens": usage.get("cache_write_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_tokens": usage.get("reasoning_output_tokens"),
        "strategy": primary,
        "strategy_flags": flags,
    }


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--trials", type=Path, default=root / "results" / "trials.jsonl")
    parser.add_argument("--output", type=Path, default=root / "results" / "trace-metrics.jsonl")
    return parser


def main() -> None:
    args = _parser().parse_args()
    records = [
        json.loads(line)
        for line in args.trials.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    output = []
    for record in records:
        metrics = analyze_trace(args.root / record["trace_file"])
        output.append(
            {
                "neutral_id": record["neutral_id"],
                "variant": record["variant"],
                "condition": record["condition"],
                "lanes": record["lanes"],
                "seed": record["seed"],
                "semantic_success": record["semantic_success"],
                "elapsed_seconds": record["runner"]["elapsed_seconds"],
                "timed_out": record["runner"]["timed_out"],
                **metrics,
            }
        )
    args.output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in output),
        encoding="utf-8",
    )
    print(f"analyzed {len(output)} complete observable traces")


if __name__ == "__main__":
    main()
