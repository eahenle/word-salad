#!/usr/bin/env python3
"""Analyze the exact matched 4C coherent versus 4C.1 decohered contrast."""

from __future__ import annotations

import json
import statistics
from collections import Counter

from runtime import ROOT, atomic_bytes, atomic_json


SOURCE_ROOT = ROOT.parent


def label(row: dict) -> str:
    if row.get("semantic_success"):
        return f"{row['selected_target']} (expected)"
    if row.get("selected_target"):
        return f"{row['selected_target']} ({row['classification'].replace('_', ' ')})"
    return row["classification"].replace("_", " ")


def main() -> None:
    gate = json.loads((ROOT / "results/development-gate.json").read_text())
    current = [json.loads(line) for line in (ROOT / "results/trials.jsonl").read_text().splitlines()]
    coherent = [json.loads(line) for line in (SOURCE_ROOT / "results/trials.jsonl").read_text().splitlines()]
    current_by = {(row["topic"], row["condition"]): row for row in current}
    coherent_by = {(row["topic"], row["condition"]): row for row in coherent}
    lines = ["# Experiment 4C.1 foreground-coherence ablation", "", "## Direct matched comparison", "",
        "| Topic | 4C coherent A | 4C coherent B | 4C.1 decohered A | 4C.1 decohered B | Decohered scrambled |",
        "| --- | --- | --- | --- | --- | --- |"]
    for topic in ("harbor", "ceramics", "garden"):
        lines.append(f"| {topic} | {label(coherent_by[(topic, 'hidden_a')])} | "
                     f"{label(coherent_by[(topic, 'hidden_b')])} | {label(current_by[(topic, 'hidden_a')])} | "
                     f"{label(current_by[(topic, 'hidden_b')])} | {label(current_by[(topic, 'scrambled')])} |")
    signals = [row for row in current if row["expected_answer"]]
    controls = [row for row in current if row["condition"] == "scrambled"]
    lines += ["", "## Aggregate", "",
        "- 4C coherent expected individuals: 0/6.",
        "- 4C coherent complete pairs: 0/3.",
        f"- 4C.1 decohered expected individuals: {gate['expected_hidden_answers']}/6.",
        f"- 4C.1 decohered complete pairs: {gate['complete_ab_pairs']}/3.",
        f"- Decohered scrambled target selections: {gate['scrambled_control_target_selections']}/3.",
        f"- Counterpart errors: {gate['counterpart_errors']}.", "", "## Preregistered interpretation", ""]
    interpretations = {
        "outcome_1_recovery_after_decoherence": "Recovery crossed the preregistered gate after foreground decoherence with clean controls. At this development scale, foreground coherence materially suppressed the fixed 7.4% sparse stream.",
        "outcome_2_no_recovery_after_decoherence": "Destroying foreground coherence did not restore any expected hidden answer. Foreground coherence is therefore not sufficient to explain the 4C failure; low signal density becomes the leading next variable.",
        "outcome_3_control_contamination": "Target answers appeared in decohered scrambled controls, so lexical visibility or another control failure contaminates answer identity. This is not evidence of sparse-order recovery.",
        "outcome_4_partial_recovery": "The initial cohort showed partial recovery without meeting the gate. This is descriptive and does not authorize tuning these prompts.",
    }
    lines.append(interpretations[gate["outcome"]])
    elapsed = [row["runner"]["elapsed_seconds"] for row in current]
    reasoning = [(row["runner"].get("aggregate_usage") or {}).get("reasoning_output_tokens", 0) for row in current]
    lines += ["", "## Observable behavior", "",
        f"- Explicit structural-analysis language: {sum(row['explicit_structure_language'] for row in current)}/9.",
        f"- Explicit hidden/encoded-content mentions: {sum(row['explicit_hidden_or_encoded_mention'] for row in current)}/9.",
        f"- Clarification requests: {sum(row['clarification_request'] for row in current)}/9.",
        f"- Timeouts: {sum(row['runner']['timed_out'] for row in current)}/9.",
        f"- Median elapsed time: {statistics.median(elapsed):.3f} seconds.",
        f"- Median reasoning-output tokens: {statistics.median(reasoning):.1f}.", "",
        "These three topics form a controlled mechanistic ablation, not a population sample. The experiment does not identify a private reasoning process or transformer mechanism.", "",
        "## Integrity", "",
        "Every decohered document retains the frozen 4C signal words at the exact same 19 indices, the exact document length, and the exact complete whitespace-word multiset. Only nonsignal assignment changed. The model, reasoning effort, framing, clean image, no-tool configuration, and ten-minute timeout were unchanged."]
    atomic_bytes(ROOT / "results/analysis.md", ("\n".join(lines) + "\n").encode())
    atomic_json(ROOT / "results/strategy-summary.json", {
        "trials": 9, "classification_counts": dict(sorted(Counter(row["classification"] for row in current).items())),
        "explicit_structure_trial_ids": [row["trial_id"] for row in current if row["explicit_structure_language"]],
        "explicit_hidden_or_encoded_trial_ids": [row["trial_id"] for row in current if row["explicit_hidden_or_encoded_mention"]],
        "clarification_request_trial_ids": [row["trial_id"] for row in current if row["clarification_request"]],
        "private_chain_of_thought_claimed": False,
    })
    print(json.dumps({"gate_passed": gate["passed"], "outcome": gate["outcome"]}, indent=2))


if __name__ == "__main__":
    main()

