#!/usr/bin/env python3
"""Summarize available frozen density stages and the inferred boundary."""

from __future__ import annotations

import json
import statistics

from generate import ROOT
from runtime import atomic_bytes


def label(row):
    if row["semantic_success"]: return f"{row['selected_target']} expected"
    if row["selected_target"]: return f"{row['selected_target']} {row['classification']}"
    return row["classification"]


def main() -> None:
    stages={}
    for density in ("d125","d250"):
        path=ROOT/"development"/density/"results/trials.jsonl"
        if path.exists(): stages[density]=[json.loads(line) for line in path.read_text().splitlines()]
    coherent=json.loads((ROOT.parent/"results/development-gate.json").read_text())
    decoherent=json.loads((ROOT.parent/"foreground-ablation/results/development-gate.json").read_text())
    lines=["# Experiment 4C.2 incoherent density ladder","","## Outcomes","",
        "| Density | Expected individuals | Complete A/B pairs | Scrambled target selections | Outcome |",
        "| ---: | ---: | ---: | ---: | --- |",
        f"| 7.4% coherent (4C) | {coherent['expected_hidden_answers']}/6 | {coherent['complete_ab_pairs']}/3 | — | frozen null |",
        f"| 7.4% incoherent (4C.1) | {decoherent['expected_hidden_answers']}/6 | {decoherent['complete_ab_pairs']}/3 | {decoherent['scrambled_control_target_selections']}/3 | frozen null |"]
    for density,rows in stages.items():
        gate=json.loads((ROOT/"development"/density/"results/development-gate.json").read_text())
        pct="12.5%" if density=="d125" else "25%"
        lines.append(f"| {pct} incoherent | {gate['expected_hidden_answers']}/6 | {gate['complete_ab_pairs']}/3 | {gate['scrambled_target_selections']}/3 | {gate['outcome'].replace('_',' ')} |")
    lines += ["","## Paired answer identity",""]
    for density,rows in stages.items():
        lines += [f"### {density}","","| Topic | Hidden A | Hidden B | Scrambled | Complete pair |","| --- | --- | --- | --- | ---: |"]
        for topic in ("harbor","ceramics","garden"):
            cells={row["condition"]:row for row in rows if row["topic"]==topic}; complete=cells["hidden_a"]["semantic_success"] and cells["hidden_b"]["semantic_success"]
            lines.append(f"| {topic} | {label(cells['hidden_a'])} | {label(cells['hidden_b'])} | {label(cells['scrambled'])} | {'yes' if complete else 'no'} |")
        lines.append("")
    lines += ["## Interpretation",""]
    if "d250" not in stages:
        gate=json.loads((ROOT/"development/d125/results/development-gate.json").read_text())
        lines.append("The frozen decision rule stopped after 12.5%; no claim is made about 25%." if not gate["next_stage_authorized"] else "The authorized 25% stage has not yet been executed.")
    else:
        g125=json.loads((ROOT/"development/d125/results/development-gate.json").read_text()); g250=json.loads((ROOT/"development/d250/results/development-gate.json").read_text())
        if g125["expected_hidden_answers"]==0 and g250["gate_passed"]:
            lines.append("Recovery crossed the preregistered gate at 25% after a complete 12.5% null, placing the observed boundary between those densities for these fixed topics and prompts.")
        elif g250["expected_hidden_answers"]==0:
            lines.append("Neither 12.5% nor 25% restored recovery. The next boundary probe, if separately frozen, is 50%; it was not authorized in this initial ladder.")
        else: lines.append("The 25% stage produced partial recovery. This is descriptive and calls for independent replication rather than prompt tuning.")
    all_rows=[row for rows in stages.values() for row in rows]
    lines += ["","## Effort",""]
    for density,rows in stages.items():
        elapsed=[row["runner"]["elapsed_seconds"] for row in rows]; reasoning=[(row["runner"].get("aggregate_usage") or {}).get("reasoning_output_tokens",0) for row in rows]
        lines.append(f"- {density}: median {statistics.median(elapsed):.3f}s, median {statistics.median(reasoning):.1f} reasoning-output tokens, {sum(row['runner']['timed_out'] for row in rows)} timeouts.")
    lines += ["","This staged three-topic experiment maps a mechanistic boundary; it is not a population sample. Density changes total prompt length as an unavoidable design limitation with a fixed 19-word signal."]
    atomic_bytes(ROOT/"results/analysis.md",("\n".join(lines)+"\n").encode()); print(json.dumps({"stages":list(stages)},indent=2))


if __name__ == "__main__": main()

