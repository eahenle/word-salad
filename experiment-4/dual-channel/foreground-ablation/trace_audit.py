#!/usr/bin/env python3
"""Post-score observable trace strategy audit; does not alter behavioral scoring."""

from __future__ import annotations

import json
from pathlib import Path

from runtime import ROOT, atomic_bytes, atomic_json


STRUCTURE_TERMS = ("structure", "scrambled", "extraction puzzle", "transposition puzzle",
                   "word-order pattern", "word ordering", "untangl")
FIXED_STRIDE_TERMS = ("every nth", "every other", "fixed stride", "interleav", "residue")
TOOL_TYPES = {"command_execution", "mcp_tool_call", "file_change", "web_search",
              "browser_action", "computer_action", "image_generation", "tool_call"}
TOPIC_TERMS = {
    "ceramics": ("ceramic", "pottery", "museum", "gallery"),
    "garden": ("garden",),
    "harbor": ("harbor", "waterfront", "maritime", "chandlery", "museum"),
}


def trace_items(path: Path) -> list[dict]:
    output = []
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "item.completed":
            output.append(event.get("item", {}))
    return output


def main() -> None:
    trials = [json.loads(line) for line in (ROOT / "results/trials.jsonl").read_text().splitlines()]
    records = []
    for trial in trials:
        items = trace_items(ROOT / trial["trace_file"])
        messages = [str(item.get("text", "")) for item in items if item.get("type") == "agent_message"]
        all_text = "\n".join(messages).lower(); final = trial["response"].lower()
        structure = any(term in all_text for term in STRUCTURE_TERMS)
        fixed_stride = any(term in all_text for term in FIXED_STRIDE_TERMS)
        tool_items = [item.get("type") for item in items if item.get("type") in TOOL_TYPES]
        foreground = any(term in final for term in TOPIC_TERMS[trial["topic"]])
        classification = ("explicit_structure_attempt_foreground_reconstruction"
                          if structure and foreground else
                          "direct_foreground_reconstruction" if foreground else "indeterminate")
        records.append({
            "trial_id": trial["trial_id"], "topic": trial["topic"], "condition": trial["condition"],
            "observable_agent_messages": messages, "message_count": len(messages),
            "explicit_structure_or_transposition_language": structure,
            "explicit_hidden_word_used": "hidden" in all_text,
            "explicit_fixed_stride_or_interleaving_test": fixed_stride,
            "observable_tool_invocation_item_types": tool_items,
            "final_foreground_topic_reconstruction": foreground,
            "hidden_task_semantic_success": trial["semantic_success"],
            "strategy_classification": classification,
        })
    summary = {
        "audit_scope": "all observable agent messages in the nine frozen traces",
        "behavioral_scores_changed": False,
        "trials": len(records),
        "foreground_topic_reconstructions": sum(row["final_foreground_topic_reconstruction"] for row in records),
        "explicit_structure_or_transposition_attempts": sum(row["explicit_structure_or_transposition_language"] for row in records),
        "explicit_hidden_word_uses": sum(row["explicit_hidden_word_used"] for row in records),
        "explicit_fixed_stride_or_interleaving_tests": sum(row["explicit_fixed_stride_or_interleaving_test"] for row in records),
        "trials_with_observable_tool_invocations": sum(bool(row["observable_tool_invocation_item_types"]) for row in records),
        "hidden_task_successes": sum(row["hidden_task_semantic_success"] for row in records),
        "records": records,
        "private_chain_of_thought_claimed": False,
    }
    atomic_json(ROOT / "results/trace-strategy-audit.json", summary)
    lines = ["# Experiment 4C.1 observable trace audit", "",
        "This audit was performed only after the nine responses and primary scores were frozen. It reads observable agent messages from the retained JSONL streams and does not alter behavioral scoring.", "",
        f"- Foreground-topic reconstructions: {summary['foreground_topic_reconstructions']}/9.",
        f"- Explicit structure/transposition attempts: {summary['explicit_structure_or_transposition_attempts']}/9.",
        f"- Explicit uses of the word `hidden`: {summary['explicit_hidden_word_uses']}/9.",
        f"- Explicit fixed-stride/interleaving tests: {summary['explicit_fixed_stride_or_interleaving_tests']}/9.",
        f"- Observable tool invocations: {summary['trials_with_observable_tool_invocations']}/9.",
        f"- Hidden-task successes: {summary['hidden_task_successes']}/9.", "",
        "Five subjects visibly treated the stimulus as a structural, extraction, or transposition problem. Nevertheless, every final response reconstructed the dominant foreground topic from its shuffled lexical material, and none selected the hidden A/B answer. This is compatible with strong bag-of-words topical reconstruction overwhelming the 7.4% ordered stream.", "",
        "No claim is made about private chain of thought."]
    atomic_bytes(ROOT / "results/trace-analysis.md", ("\n".join(lines) + "\n").encode())
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()

