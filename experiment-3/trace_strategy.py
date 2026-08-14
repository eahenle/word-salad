#!/usr/bin/env python3
"""Extract observable effort metrics and evidence-based trace strategies."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


STRIDE_TEST = re.compile(
    r"candidate\s+strides?|test(?:ing|ed)?\s+(?:all\s+)?(?:possible\s+)?strides?|"
    r"for\s+\w*stride\w*\s+in\s+range|stride\w*\s+in\s+range|"
    r"for\s+\w+\s+in\s+range\([^\n)]*\).*?\[\w*::\w+\]",
    re.I | re.S,
)
FIXED_STRIDE = re.compile(
    r"every[ -](?:other|second)\s+(?:word|token)|\bparit(?:y|ies)\b|"
    r"\bodd\s+(?:and|/|or)\s+even\b|\beven\s+(?:and|/|or)\s+odd\b|"
    r"\[[^\]\n]{0,30}::\s*2\s*\]|\[(?:0|1)\s*::\s*2\]|"
    r"\bstride\s*(?:=|of|:)\s*2\b|\bresidue\s+class",
    re.I,
)
JITTER = re.compile(
    r"\bjitter(?:ed|ing)?\b|\bnon[ -]?periodic\b|\bvariable\s+(?:gap|spacing)|"
    r"\birregular\s+(?:gap|spacing|interval)|\badjacent\s+signal|"
    r"\bintervals?\s+of\s+(?:1|one)\s+(?:and|or)\s+(?:3|three)\b|"
    r"\bshort\s+and\s+long\s+(?:gap|spacing|interval)",
    re.I,
)
LEXICAL = re.compile(
    r"\breconstruct|\bdisentangl|\brecover(?:ed|ing)?\b|\bunshuffl|\bdecod|"
    r"\binterleav|\bmultiplex|\bordered\s+subsequence|\bword\s+salad",
    re.I,
)
GENERIC = re.compile(
    r"\bgarbl|\bcorrupt|\bscrambl|\bjumbled|\bincoherent|\bmalformed|"
    r"\btoo\s+(?:mixed|ambiguous)|\bcan(?:not|'t|’t)\s+reliably",
    re.I,
)


def _events(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def analyze_trace(path: Path, record: dict) -> dict:
    events = _events(path)
    event_types = Counter(str(event.get("type", "unknown")) for event in events)
    item_types: Counter[str] = Counter()
    agent_messages: list[str] = []
    commands: list[str] = []
    command_outputs: list[str] = []
    searches: list[str] = []
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        item_type = str(item.get("type", "unknown"))
        item_types[item_type] += 1
        if item_type == "agent_message":
            agent_messages.append(str(item.get("text", "")))
        elif item_type == "command_execution":
            commands.append(str(item.get("command", "")))
            command_outputs.append(str(item.get("aggregated_output", "")))
        elif item_type == "web_search":
            query = str(item.get("query", ""))
            action = item.get("action", {})
            searches.append(query + " " + json.dumps(action, ensure_ascii=False))
    observable = "\n".join(agent_messages + commands + searches)
    tool_calls = sum(
        count for kind, count in item_types.items()
        if kind not in {"agent_message", "reasoning"}
    )
    decoder_command = re.compile(
        r"\.split\(|\bCounter\(|\bparit(?:y|ies)\b|\bstride\b|::\s*\w+|"
        r"candidate\s+(?:lane|subsequence)|dynamic\s+program|beam\s+search",
        re.I,
    )
    decoder_tool_calls = sum(
        len(command) >= 1000 or bool(decoder_command.search(command))
        for command in commands
    ) + sum(bool(search.strip()) for search in searches)
    flags = {
        "explicit_stride_testing": bool(STRIDE_TEST.search(observable)),
        "fixed_stride_hypothesis": bool(FIXED_STRIDE.search(observable)),
        "jitter_pattern_hypothesis": bool(JITTER.search(observable)),
        "lexical_reconstruction_language": bool(LEXICAL.search(observable)),
        "generic_corruption_language": bool(GENERIC.search(observable)),
        "used_any_tool": tool_calls > 0,
        "used_shell": bool(commands),
        "used_web_search": bool(searches),
        "tool_assisted_decoder": decoder_tool_calls > 0,
        "repeated_attempts": decoder_tool_calls >= 2 or (
            len(agent_messages) >= 3 and bool(LEXICAL.search(observable))
        ),
    }
    if flags["explicit_stride_testing"]:
        strategy = "explicit_stride_testing"
    elif flags["fixed_stride_hypothesis"]:
        strategy = "explicit_fixed_stride_recognition"
    elif flags["jitter_pattern_hypothesis"]:
        strategy = "jitter_pattern_recognition"
    elif flags["repeated_attempts"] and flags["tool_assisted_decoder"]:
        strategy = "repeated_reconstruction"
    elif flags["tool_assisted_decoder"]:
        strategy = "shell_or_tool_assisted_decoder"
    elif flags["lexical_reconstruction_language"]:
        strategy = "lexical_reconstruction_without_stride"
    elif flags["generic_corruption_language"]:
        strategy = "generic_corruption_detection"
    elif len(agent_messages) == 1:
        strategy = "direct_one_pass_tool_free"
    else:
        strategy = "indeterminate"
    usage = record.get("runner", {}).get("aggregate_usage") or {}
    evidence = {
        "explicit_stride_testing": (STRIDE_TEST.search(observable) or [None])[0],
        "fixed_stride_hypothesis": (FIXED_STRIDE.search(observable) or [None])[0],
        "jitter_pattern_hypothesis": (JITTER.search(observable) or [None])[0],
        "lexical_reconstruction_language": (LEXICAL.search(observable) or [None])[0],
        "generic_corruption_language": (GENERIC.search(observable) or [None])[0],
    }
    return {
        "strategy": strategy,
        "flags": flags,
        "evidence": evidence,
        "model_turns": event_types.get("turn.started", 0),
        "agent_messages": len(agent_messages),
        "tool_calls": tool_calls,
        "decoder_tool_calls": decoder_tool_calls,
        "shell_calls": len(commands),
        "web_search_calls": len(searches),
        "event_count": sum(event_types.values()),
        "trace_bytes": path.stat().st_size,
        "input_tokens": usage.get("input_tokens"),
        "cached_input_tokens": usage.get("cached_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_tokens": usage.get("reasoning_output_tokens"),
    }
