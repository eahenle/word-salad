#!/usr/bin/env python3
"""Create the frozen Experiment 4C development analysis."""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

from runtime import atomic_bytes, atomic_json
from validate import ROOT


def cell(record: dict) -> str:
    if record["semantic_success"]:
        return f"{record['selected_target']} (expected)"
    if record["selected_target"]:
        return f"{record['selected_target']} ({record['classification']})"
    return record["classification"].replace("_", " ")


def main() -> None:
    gate = json.loads((ROOT / "results/development-gate.json").read_text())
    records = [json.loads(line) for line in (ROOT / "results/trials.jsonl").read_text().splitlines()]
    by_topic = {topic: {record["condition"]: record for record in records if record["topic"] == topic}
                for topic in sorted({record["topic"] for record in records})}
    lines = [
        "# Experiment 4C development analysis", "",
        "## Outcome", "",
        ("The preregistered development gate passed." if gate["passed"]
         else "The preregistered development gate did not pass; no held-out or optimized follow-up was run."),
        "", "The result is a twelve-trial development gate, not a population estimate.", "",
        "## Answer identity", "",
        "| Topic | Hidden A (Rowan) | Hidden B (Mira) | Scrambled | Cover only | Complete A/B pair |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    for topic, records_by_condition in by_topic.items():
        complete = records_by_condition["hidden_a"]["semantic_success"] and records_by_condition["hidden_b"]["semantic_success"]
        lines.append(f"| {topic} | {cell(records_by_condition['hidden_a'])} | {cell(records_by_condition['hidden_b'])} | "
                     f"{cell(records_by_condition['scrambled'])} | {cell(records_by_condition['cover_only'])} | "
                     f"{'yes' if complete else 'no'} |")
    signal = [record for record in records if record["condition"].startswith("hidden_")]
    controls = [record for record in records if record["condition"] in {"scrambled", "cover_only"}]
    lines += [
        "", "## Gate metrics", "",
        f"- Expected hidden answers: {sum(record['semantic_success'] for record in signal)}/{len(signal)}.",
        f"- Complete A/B pairs: {gate['complete_ab_pairs']}/3 (required: at least 2).",
        f"- Control target-answer selections: {gate['control_target_answer_selections']}/{len(controls)} (required: 0).",
        f"- Counterpart-answer errors: {gate['counterpart_errors']}.",
        "", "## Observable execution", "",
    ]
    tool_trials = [record["trial_id"] for record in records if record["runner"]["observable_non_message_items"]]
    hidden_mentions = [record["trial_id"] for record in records if record["explicit_hidden_structure_mention"]]
    elapsed = [record["runner"]["elapsed_seconds"] for record in records]
    reasoning = [(record["runner"].get("aggregate_usage") or {}).get("reasoning_output_tokens", 0) for record in records]
    lines += [
        f"- Observable non-message/tool items: {len(tool_trials)} trials{': ' + ', '.join(tool_trials) if tool_trials else ''}.",
        f"- Explicit hidden/encoded-structure mentions: {len(hidden_mentions)} trials{': ' + ', '.join(hidden_mentions) if hidden_mentions else ''}.",
        f"- Timeouts: {sum(record['runner']['timed_out'] for record in records)}.",
        f"- Median elapsed time: {statistics.median(elapsed):.3f} seconds.",
        f"- Median reasoning-output tokens: {statistics.median(reasoning):.1f}.",
        "", "## Interpretation boundary", "",
    ]
    if gate["passed"]:
        lines.append("At development scale, answer identity tracked the intact orthogonal sparse stream strongly enough to justify the separately frozen held-out cohort. This does not identify a transformer mechanism.")
    else:
        lines.append("These covers do not establish dual-channel recovery. The negative gate cannot distinguish coherent-foreground suppression, low signal density, grammar-constrained carrier difficulty, and neutral-framing effects. The protocol forbids rewriting these covers to optimize toward success.")
    lines += [
        "", "The local Docker audit found no observable baked-in project context, but did not rule out every possible upstream or account-level context.",
        "", "## Data integrity", "",
        "Hidden A, Hidden B, and scrambled documents have exactly equal complete whitespace-word bags within each topic. Every consecutive selected signal position is separated far enough that no visible 2-6 word window contains two selected signal words. Subjects received no tool schema or project mount.",
    ]
    atomic_bytes(ROOT / "results/analysis.md", ("\n".join(lines) + "\n").encode())
    strategy = {
        "trials": len(records), "classification_counts": dict(sorted(Counter(record["classification"] for record in records).items())),
        "explicit_hidden_structure_trial_ids": hidden_mentions,
        "observable_non_message_item_trial_ids": tool_trials,
        "private_chain_of_thought_claimed": False,
    }
    atomic_json(ROOT / "results/strategy-summary.json", strategy)
    print(json.dumps({"gate_passed": gate["passed"], "analysis": "results/analysis.md"}, indent=2))


if __name__ == "__main__":
    main()

