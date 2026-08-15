#!/usr/bin/env python3
"""Audit observable strategy and effort after the complete ladder freezes."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import statistics
from collections import Counter

from generate import ROOT, STAGES
from hidden_tasks import SYMBOLS
from runtime import atomic_bytes, atomic_json


STRUCTURE = re.compile(
    r"\b(hidden|embedded|interleav\w*|reconstruct\w*|decod\w*|"
    r"word[- ]order\w*|transpos\w*|positional clues?)\b", re.I
)


def messages(trace_path) -> list[str]:
    output = []
    for line in trace_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            output.append(str(item.get("text", "")))
    return output


def first_symbol_order(text: str) -> list[str]:
    found = []
    for token in re.findall(r"[A-Za-z]+", text):
        for symbol in SYMBOLS:
            if token.casefold() == symbol.casefold() and symbol not in found:
                found.append(symbol)
    return found


def median(values: list[float | int | None]) -> float | None:
    clean = [value for value in values if isinstance(value, (int, float))]
    return round(float(statistics.median(clean)), 3) if clean else None


def write_csv(path, rows: list[dict]) -> None:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_bytes(path, stream.getvalue().encode())


def main() -> None:
    audited = []
    effort = []
    strategy = []
    for stage in STAGES:
        trials_path = ROOT / "stages" / stage / "results/trials.jsonl"
        if not trials_path.exists():
            continue
        rows = [json.loads(line) for line in trials_path.read_text().splitlines() if line.strip()]
        for row in rows:
            trace_path = ROOT / row["trace_file"]
            actual_hash = hashlib.sha256(trace_path.read_bytes()).hexdigest()
            if actual_hash != row["runner"]["trace_sha256"]:
                raise RuntimeError(f"trace hash mismatch: {row['trial_id']}")
            agent_messages = messages(trace_path)
            observable = "\n".join(agent_messages)
            terms = [match.group(0).lower() for match in STRUCTURE.finditer(observable)]
            if terms:
                category = "explicit_structure_analysis"
            elif len(agent_messages) <= 1:
                category = "direct_or_one_pass"
            else:
                category = "multi_message_without_specific_structure_term"
            symbol_order = first_symbol_order(row["response"])
            audited.append({
                "trial_id": row["trial_id"], "stage": stage, "seed": row["seed"],
                "condition": row["condition"], "hidden_identity": row["hidden_identity"],
                "semantic_success": row["semantic_success"],
                "selected_answer_identity": row["selected_answer_identity"],
                "classification": row["classification"], "strategy": category,
                "structure_terms": terms, "agent_message_count": len(agent_messages),
                "response_first_occurrence_symbol_order": symbol_order,
                "response_mentions_all_three_symbols": len(symbol_order) == 3,
                "response_mentions_swap": bool(re.search(r"\bswap", row["response"], re.I)),
                "response_mentions_rotate": bool(re.search(r"\brotat", row["response"], re.I)),
                "trace_sha256": actual_hash,
                "observable_evidence": agent_messages,
            })
        for condition in ("hidden_a", "hidden_b", "scrambled"):
            selected = [row for row in rows if row["condition"] == condition]
            usages = [(row["runner"].get("aggregate_usage") or {}) for row in selected]
            effort.append({
                "stage": stage, "condition": condition, "trials": len(selected),
                "median_elapsed_seconds": median([row["runner"]["elapsed_seconds"] for row in selected]),
                "median_input_tokens": median([usage.get("input_tokens") for usage in usages]),
                "median_cached_input_tokens": median([usage.get("cached_input_tokens") for usage in usages]),
                "median_output_tokens": median([usage.get("output_tokens") for usage in usages]),
                "median_reasoning_tokens": median([usage.get("reasoning_output_tokens") for usage in usages]),
                "timeouts": sum(row["runner"]["timed_out"] for row in selected),
                "runner_errors": sum(row["runner"]["error"] is not None for row in selected),
            })
        stage_audit = [row for row in audited if row["stage"] == stage]
        counts = Counter(row["strategy"] for row in stage_audit)
        strategy.append({
            "stage": stage, "trials": len(stage_audit),
            "explicit_structure_analysis": counts["explicit_structure_analysis"],
            "direct_or_one_pass": counts["direct_or_one_pass"],
            "multi_message_without_specific_structure_term": counts["multi_message_without_specific_structure_term"],
            "responses_mentioning_all_three_symbols": sum(row["response_mentions_all_three_symbols"] for row in stage_audit),
            "responses_mentioning_both_operations": sum(row["response_mentions_swap"] and row["response_mentions_rotate"] for row in stage_audit),
        })
    atomic_bytes(ROOT / "results/trace-audit.jsonl", "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in audited
    ).encode())
    write_csv(ROOT / "results/effort-summary.csv", effort)
    write_csv(ROOT / "results/strategy-summary.csv", strategy)
    atomic_json(ROOT / "results/posthoc-audit-summary.json", {
        "trials_audited": len(audited),
        "observable_only": True,
        "private_chain_of_thought_available": False,
        "tool_calls_exposed": False,
        "strategy_by_stage": strategy,
        "invalidated_auth_attempts_excluded": 2,
    })
    print(json.dumps({"trials_audited": len(audited), "strategy_by_stage": strategy}, indent=2))


if __name__ == "__main__":
    main()
